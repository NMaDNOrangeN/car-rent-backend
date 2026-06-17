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

#Функции для получения текущего пользователя и его прав
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

def get_current_manager_user(current_user: m.User = Depends(get_current_user)) -> m.User:
    if not current_user.type_id == 2:
        raise HTTPException(status_code=403, detail="Manager privileges required")
    return current_user

#Эндпоинты для аутентификации
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
@app.get("/admin/users/{user_id}", response_model=m.UserRead, tags=["Admin - Users"])
async def read_admin_user(user_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

@app.get("/admin/users/", response_model=list[m.UserRead], tags=["Admin - Users"])
async def read_admin_users(current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        users = session.exec(select(m.User)).all()
        return users
    
@app.get("/admin/users/types/{type_id}", response_model=m.UserTypeRead, tags=["Admin - User Types"])
async def read_admin_user_type(type_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user_type = session.get(m.UserType, type_id)
        if not user_type:
            raise HTTPException(status_code=404, detail="User type not found")
        return user_type
    
@app.get("/admin/users/types/", response_model=list[m.UserTypeRead], tags=["Admin - User Types"])
async def read_admin_user_types(current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user_types = session.exec(select(m.UserType)).all()
        return user_types
    
@app.post("/admin/users/", response_model=m.UserRead, tags=["Admin - Users"])
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
    
@app.put("/admin/users/{user_id}", response_model=m.UserRead, tags=["Admin - Users"])
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
    
@app.delete("/admin/users/{user_id}", tags=["Admin - Users"])
async def delete_admin_user(user_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
        return user
    
#Эндпоинты для менеджера
@app.get("/manager/autos/{auto_id}", response_model=m.AutoRead, tags=["Manager - Autos"])
async def read_manager_auto(auto_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        auto = session.get(m.Auto, auto_id)
        if not auto:
            raise HTTPException(status_code=404, detail="Auto not found")
        return auto

@app.get("/manager/autos/", response_model=list[m.AutoRead], tags=["Manager - Autos"])
async def read_manager_autos(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        autos = session.exec(select(m.Auto)).all()
        return autos
    
@app.get("/manager/autos/brands/{brand_id}", response_model=m.AutoBrandRead, tags=["Manager - Brands"])
async def read_manager_auto_brand(brand_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        brand = session.get(m.AutoBrand, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        return brand
    
@app.get("/manager/autos/brands/", response_model=list[m.AutoBrandRead], tags=["Manager - Brands"])
async def read_manager_auto_brands(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        brands = session.exec(select(m.AutoBrand)).all()
        return brands
    
@app.get("/manager/autos/brands/models/{model_id}", response_model=m.AutoModelRead, tags=["Manager - Models"])
async def read_manager_auto_brand_model(model_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        model = session.get(m.AutoModel, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    
@app.get("/manager/autos/brands/models", response_model=list[m.AutoModelRead], tags=["Manager - Models"])
async def read_manager_auto_brand_models(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        models = session.exec(select(m.AutoModel)).all()
        return models
    
@app.get("/manager/autos/types/{type_id}", response_model=m.AutoTypeRead, tags=["Manager - Auto Types"])
async def read_manager_auto_type(type_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        auto_type = session.get(m.AutoType, type_id)
        if not auto_type:
            raise HTTPException(status_code=404, detail="Auto type not found")
        return auto_type
    
@app.get("/manager/autos/types", response_model=list[m.AutoTypeRead], tags=["Manager - Auto Types"])
async def read_manager_auto_types(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        auto_types = session.exec(select(m.AutoType)).all()
        return auto_types
    
@app.get("/manager/autos/statuses/{status_id}", response_model=m.AutoStatusRead, tags=["Manager - Auto Statuses"])
async def read_manager_auto_status(status_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        auto_status = session.get(m.AutoStatus, status_id)
        if not auto_status:
            raise HTTPException(status_code=404, detail="Auto status not found")
        return auto_status
    
@app.get("/manager/autos/statuses", response_model=list[m.AutoStatusRead], tags=["Manager - Auto Statuses"])
async def read_manager_auto_statuses(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        auto_statuses = session.exec(select(m.AutoStatus)).all()
        return auto_statuses
    
@app.get("/manager/rentals/{rental_id}", response_model=m.RentalRead, tags=["Manager - Rentals"])
async def read_manager_rental(rental_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental = session.get(m.Rental, rental_id)
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        return rental
    
@app.get("/manager/rentals", response_model=list[m.RentalRead], tags=["Manager - Rentals"])
async def read_manager_rentals(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rentals = session.exec(select(m.Rental)).all()
        return rentals
    
@app.get("/manager/rentals/statuses/{status_id}", response_model=m.RentalStatusRead, tags=["Manager - Rental Statuses"])
async def read_manager_rental_status(rental_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental_status = session.get(m.RentalStatus, rental_id)
        if not rental_status:
            raise HTTPException(status_code=404, detail="Rental status not found")
        return rental_status
    
@app.get("/manager/rentals/statuses", response_model=list[m.RentalStatusRead], tags=["Manager - Rental Statuses"])
async def read_manager_rental_statuses(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental_statuses = session.exec(select(m.RentalStatus)).all()
        return rental_statuses
    
@app.get("/manager/rates/{rate_id}", response_model=m.RateRead, tags=["Manager - Rates"])
async def read_manager_rate(rate_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rate = session.get(m.Rate, rate_id)
        if not rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        return rate
    
@app.get("/manager/rates", response_model=list[m.RateRead], tags=["Manager - Rates"])
async def read_manager_rates(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rates = session.exec(select(m.Rate)).all()
        return rates
    
@app.post("/manager/autos/brands/", response_model=m.AutoBrandRead, tags=["Manager - Brands"])
async def create_manager_auto_brand(brand: m.AutoBrandCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        if session.exec(select(m.AutoBrand).where(m.AutoBrand.name == brand.name)).first():
            raise HTTPException(status_code=400, detail="Brand with that name already exists")
        db_brand = m.AutoBrand(
            name=brand.name,
        )
        session.add(db_brand)
        session.commit()
        session.refresh(db_brand)
        return db_brand
    
@app.put("/manager/autos/brands/{brand_id}", response_model=m.AutoBrandRead, tags=["Manager - Brands"])
async def update_manager_auto_brand(brand_id: int, brand: m.AutoBrandUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_brand = session.get(m.AutoBrand, brand_id)
        if not existing_brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        if brand.name and brand.name != existing_brand.name:
            if session.exec(select(m.AutoBrand).where(m.AutoBrand.name == brand.name)).first():
                raise HTTPException(status_code=400, detail="Brand name already exists")
            
        update_data = brand.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_brand, key, value)
            
        session.add(existing_brand)
        session.commit()
        session.refresh(existing_brand)
        return existing_brand
    
@app.delete("/manager/autos/brands/{brand_id}", tags=["Manager - Brands"])
async def delete_manager_auto_brand(brand_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        brand = session.get(m.AutoBrand, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        session.delete(brand)
        session.commit()
        return brand
    
@app.post("/manager/autos/brands/models/", response_model=m.AutoModelRead, tags=["Manager - Models"])
async def create_manager_auto_brand_model(model: m.AutoModelCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        if session.exec(select(m.AutoModel).where(m.AutoModel.name == model.name)).first():
            raise HTTPException(status_code=400, detail="Model with that name already exists")
        db_model = m.AutoModel(
            name=model.name,
            brand_id=model.brand_id,
        )
        session.add(db_model)
        session.commit()
        session.refresh(db_model)
        return db_model
    
@app.put("/manager/autos/brands/models/{model_id}", response_model=m.AutoModelRead, tags=["Manager - Models"])
async def update_manager_auto_brand_model(model_id: int, model: m.AutoModelUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_model = session.get(m.AutoModel, model_id)
        if not existing_model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.name and model.name != existing_model.name:
            if session.exec(select(m.AutoModel).where(m.AutoModel.name == model.name)).first():
                raise HTTPException(status_code=400, detail="Model name already exists")
            
        update_data = model.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_model, key, value)
            
        session.add(existing_model)
        session.commit()
        session.refresh(existing_model)
        return existing_model
    
@app.delete("/manager/autos/brands/models/{model_id}", tags=["Manager - Models"])
async def delete_manager_auto_brand_model(model_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        model = session.get(m.AutoModel, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        session.delete(model)
        session.commit()
        return model
    
@app.post("/manager/autos/", response_model=m.AutoRead, tags=["Manager - Autos"])
async def create_manager_auto(auto: m.AutoCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        db_auto = m.Auto(
            brand_id=auto.brand_id,
            model_id=auto.model_id,
            year=auto.year,
            type_id=auto.type_id,
            price_per_day=auto.price_per_day,
            status_id=1,
        )
        session.add(db_auto)
        session.commit()
        session.refresh(db_auto)
        return db_auto
    
@app.put("/manager/autos/{auto_id}", response_model=m.AutoRead, tags=["Manager - Autos"])
async def update_manager_auto(auto_id: int, auto: m.AutoUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_auto = session.get(m.Auto, auto_id)
        if not existing_auto:
            raise HTTPException(status_code=404, detail="Auto not found")
            
        update_data = auto.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_auto, key, value)
            
        session.add(existing_auto)
        session.commit()
        session.refresh(existing_auto)
        return existing_auto
    
@app.delete("/manager/autos/{auto_id}", tags=["Manager - Autos"])
async def delete_manager_auto(auto_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        auto = session.get(m.Auto, auto_id)
        if not auto:
            raise HTTPException(status_code=404, detail="Auto not found")
        session.delete(auto)
        session.commit()
        return auto
    
@app.post("/manager/rentals/", response_model=m.RentalRead, tags=["Manager - Rentals"])
async def create_manager_rental(rental: m.RentalCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        if session.exec(select(m.Rental).where((m.Rental.auto_id == rental.auto_id) & (m.Rental.status_id == 1))).first():
            raise HTTPException(status_code=400, detail="This auto is already rented")
        db_rental = m.Rental(
            user_id=rental.user_id,
            auto_id=rental.auto_id,
            date_of_beginning_rental=rental.date_of_beginning_rental,
            date_of_end_rental=rental.date_of_end_rental,
            total_price=rental.total_price,
            status_id=1,
        )
        session.add(db_rental)
        session.commit()
        session.refresh(db_rental)
        return db_rental
    
@app.put("/manager/rentals/{rental_id}", response_model=m.RentalRead, tags=["Manager - Rentals"])
async def update_manager_rental(rental_id: int, rental: m.RentalUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_rental = session.get(m.Rental, rental_id)
        if not existing_rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        if session.exec(select(m.Rental).where((m.Rental.auto_id == rental.auto_id) & (m.Rental.status_id == 1) & (m.Rental.id != existing_rental.id))).first():
            raise HTTPException(status_code=400, detail="This auto is already rented")

        update_data = rental.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_rental, key, value)
            
        session.add(existing_rental)
        session.commit()
        session.refresh(existing_rental)
        return existing_rental
    
@app.delete("/manager/rentals/{rental_id}", tags=["Manager - Rentals"])
async def delete_manager_rental(rental_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental = session.get(m.Rental, rental_id)
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        session.delete(rental)
        session.commit()
        return rental
    
#Эндпоинты для клиента