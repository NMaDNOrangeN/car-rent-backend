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

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# def get_current_user(session: Session = Depends(db.get_session), token: str = Depends(oauth2_scheme)) -> m.User:
#     payload = decode_access_token(token)
#     if payload is None:
#         raise HTTPException(status_code=401, detail="Invalid token")
#     user_id = payload.get("sub")
#     if user_id is None:
#         raise HTTPException(status_code=401, detail="Token missing user id")
#     user = session.get(m.User, int(user_id))
#     if user is None:
#         raise HTTPException(status_code=401, detail="User not found")
#     return user

# def get_current_admin_user(current_user: m.User = Depends(get_current_user)) -> m.User:
#     if not current_user.status == m.UserStatus.ADMIN:
#         raise HTTPException(status_code=403, detail="Admin privileges required")
#     return current_user

# @app.get("/users/me", tags=["Users"])
# async def read_users_me(current_user: Annotated[m.User, Depends(get_current_user)]):
#     return current_user

# @app.get("admin/users/{user_id}", tags=["Admin"])
# async def read_admin_user(user_id: int):
#     with Session(db.engine) as session:
#         user = session.get(m.User, user_id)
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
#         return user

# @app.get("admin/users/", tags=["Admin"])
# async def read_admin_users():
#     with Session(db.engine) as session:
#         users = session.exec(select(m.User)).all()
#         return users