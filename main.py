from fastapi import FastAPI, HTTPException, Depends, Query
from typing_extensions import Annotated
from sqlmodel import Session, select

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from security import (
    decode_access_token,
    get_password_hash, 
    verify_password, 
    create_access_token, 
)

import models as m
from enum import Enum
import db
import re


app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(session: Session = Depends(db.get_session), token: str = Depends(oauth2_scheme)) -> m.User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token missing user id")
    user = session.get(m.User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_current_admin_user(current_user: m.User = Depends(get_current_user)) -> m.User:
    if not current_user.type_id == 1:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@app.post("/login", tags=["Authentication Check"])
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    with Session(db.engine) as session:
        user = session.exec(select(m.User).where(m.User.username == form_data.username)).first()
        if not user or not verify_password(form_data.password, user.password):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", tags=["My User"])
async def read_users_me(current_user: Annotated[m.User, Depends(get_current_user)]):
    return current_user

#Эндпоинты для админа
@app.get("/admin/users/{user_id}", response_model=m.UserRead, tags=["Admin"])
async def read_admin_user(user_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

@app.get("/admin/users/", response_model=list[m.UserRead], tags=["Admin"])
async def read_admin_users(current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        users = session.exec(select(m.User)).all()
        return users
    
@app.post("/admin/users/", response_model=m.UserRead, tags=["Admin"])
async def create_admin_user(user: m.UserCreate, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        if session.exec(select(m.User).where((m.User.username == user.username) 
                                             | (m.User.email == user.email) 
                                             | (m.User.phone_number == user.phone_number))).first():
            raise HTTPException(status_code=400, detail="User with that parameters already exists")
        db_user = m.User(
            username=user.username,
            phone_number=user.phone_number,
            email=user.email,
            password=get_password_hash(user.password),
            type_id=user.type_id,
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    
@app.put("/admin/users/{user_id}", response_model=m.UserRead, tags=["Admin"])
async def update_admin_user(user_id: int, user: m.UserUpdate, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        existing_user = session.get(m.User, user_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.username and user.username != existing_user.username:
            if session.exec(select(m.User).where(m.User.username == user.username)).first():
                raise HTTPException(status_code=400, detail="Username already exists")
        if user.email and user.email != existing_user.email:
            if session.exec(select(m.User).where(m.User.email == user.email)).first():
                raise HTTPException(status_code=400, detail="Email already exists")
        if user.phone_number and user.phone_number != existing_user.phone_number:
            if session.exec(select(m.User).where(m.User.phone_number == user.phone_number)).first():
                raise HTTPException(status_code=400, detail="Phone number already exists")
            
        update_data = user.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_user, key, value)
            
        session.add(existing_user)
        session.commit()
        session.refresh(existing_user)
        return existing_user
    
@app.delete("/admin/users/{user_id}", tags=["Admin"])
async def delete_admin_user(user_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
        return user
    
#Эндпоинты для менеджера