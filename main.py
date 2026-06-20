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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

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
    with Session(db.engine) as session:
        admin_type = session.exec(select(m.UserType).where(m.UserType.name == "admin")).first()
        if not current_user.type_id == admin_type.id:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        return current_user

def get_current_manager_user(current_user: m.User = Depends(get_current_user)) -> m.User:
    with Session(db.engine) as session:
        manager_type = session.exec(select(m.UserType).where(m.UserType.name == "manager")).first()
        if not current_user.type_id == manager_type.id:
            raise HTTPException(status_code=403, detail="Manager privileges required")
        return current_user

#Функция для рассчёта стоимости аренды (включая скидки за длительную аренду)
def calculate_rental_price(price_per_day: float, days: int) -> float:
    if days >= 20:
        discount = 0.2
    elif days >= 10:
        discount = 0.1
    elif days >= 5:
        discount = 0.05
    else:
        discount = 0.0
    return round((price_per_day * days) * (1 - discount), 2)

#Эндпоинты для аутентификации
@app.post("/api/login", tags=["Authentication Check"])
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
@app.get("/api/admin/users/{user_id}", response_model=m.UserRead, tags=["Admin - Users"])
async def read_admin_user(user_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

@app.get("/api/admin/users/", response_model=list[m.UserRead], tags=["Admin - Users"])
async def read_admin_users(current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        users = session.exec(select(m.User)).all()
        return users
    
@app.get("/api/admin/users/types/{type_id}", response_model=m.UserTypeRead, tags=["Admin - User Types"])
async def read_admin_user_type(type_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user_type = session.get(m.UserType, type_id)
        if not user_type:
            raise HTTPException(status_code=404, detail="User type not found")
        return user_type
    
@app.get("/api/admin/users/types/", response_model=list[m.UserTypeRead], tags=["Admin - User Types"])
async def read_admin_user_types(current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user_types = session.exec(select(m.UserType)).all()
        return user_types
    
@app.post("/api/admin/users/", response_model=m.UserRead, tags=["Admin - Users"])
async def create_admin_user(user: m.UserCreate, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        if not session.get(m.UserType, user.type_id):
            raise HTTPException(status_code=400, detail="User type does not exist")
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
    
@app.put("/api/admin/users/{user_id}", response_model=m.UserRead, tags=["Admin - Users"])
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
        if user.type_id and not session.get(m.UserType, user.type_id):
            raise HTTPException(status_code=400, detail="User type does not exist")

        update_data = user.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["password"] = get_password_hash(update_data["password"])
        for key, value in update_data.items():
            setattr(existing_user, key, value)
            
        session.add(existing_user)
        session.commit()
        session.refresh(existing_user)
        return existing_user
    
@app.delete("/api/admin/users/{user_id}", tags=["Admin - Users"])
async def delete_admin_user(user_id: int, current_user: Annotated[m.User, Depends(get_current_admin_user)]):
    with Session(db.engine) as session:
        user = session.get(m.User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
        return user
    
#Эндпоинты для менеджера
@app.get("/api/manager/cars/{car_id}", response_model=m.CarRead, tags=["Manager - Cars"])
async def read_manager_car(car_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        car = session.get(m.Car, car_id)
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        return car

@app.get("/api/manager/cars/", response_model=list[m.CarRead], tags=["Manager - Cars"])
async def read_manager_cars(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        cars = session.exec(select(m.Car)).all()
        return cars
    
@app.get("/api/manager/cars/brands/{brand_id}", response_model=m.CarBrandRead, tags=["Manager - Brands"])
async def read_manager_car_brand(brand_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        brand = session.get(m.CarBrand, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        return brand
    
@app.get("/api/manager/cars/brands/", response_model=list[m.CarBrandRead], tags=["Manager - Brands"])
async def read_manager_car_brands(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        brands = session.exec(select(m.CarBrand)).all()
        return brands
    
@app.get("/api/manager/cars/brands/models/{model_id}", response_model=m.CarModelRead, tags=["Manager - Models"])
async def read_manager_car_brand_model(model_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        model = session.get(m.CarModel, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    
@app.get("/api/manager/cars/brands/models", response_model=list[m.CarModelRead], tags=["Manager - Models"])
async def read_manager_car_brand_models(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        models = session.exec(select(m.CarModel)).all()
        return models
    
@app.get("/api/manager/cars/types/{type_id}", response_model=m.CarTypeRead, tags=["Manager - Car Types"])
async def read_manager_car_type(type_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        car_type = session.get(m.CarType, type_id)
        if not car_type:
            raise HTTPException(status_code=404, detail="Car type not found")
        return car_type
    
@app.get("/api/manager/cars/types", response_model=list[m.CarTypeRead], tags=["Manager - Car Types"])
async def read_manager_car_types(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        car_types = session.exec(select(m.CarType)).all()
        return car_types
    
@app.get("/api/manager/cars/statuses/{status_id}", response_model=m.CarStatusRead, tags=["Manager - Car Statuses"])
async def read_manager_car_status(status_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        car_status = session.get(m.CarStatus, status_id)
        if not car_status:
            raise HTTPException(status_code=404, detail="Car status not found")
        return car_status
    
@app.get("/api/manager/cars/statuses", response_model=list[m.CarStatusRead], tags=["Manager - Car Statuses"])
async def read_manager_car_statuses(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        car_statuses = session.exec(select(m.CarStatus)).all()
        return car_statuses
    
@app.get("/api/manager/rentals/{rental_id}", response_model=m.RentalRead, tags=["Manager - Rentals"])
async def read_manager_rental(rental_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental = session.get(m.Rental, rental_id)
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        return rental
    
@app.get("/api/manager/rentals", response_model=list[m.RentalRead], tags=["Manager - Rentals"])
async def read_manager_rentals(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rentals = session.exec(select(m.Rental)).all()
        return rentals
    
@app.get("/api/manager/rentals/statuses/{status_id}", response_model=m.RentalStatusRead, tags=["Manager - Rental Statuses"])
async def read_manager_rental_status(status_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental_status = session.get(m.RentalStatus, status_id)
        if not rental_status:
            raise HTTPException(status_code=404, detail="Rental status not found")
        return rental_status
    
@app.get("/api/manager/rentals/statuses", response_model=list[m.RentalStatusRead], tags=["Manager - Rental Statuses"])
async def read_manager_rental_statuses(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental_statuses = session.exec(select(m.RentalStatus)).all()
        return rental_statuses
    
@app.get("/api/manager/rates/{rate_id}", response_model=m.RateRead, tags=["Manager - Rates"])
async def read_manager_rate(rate_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rate = session.get(m.Rate, rate_id)
        if not rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        return rate
    
@app.get("/api/manager/rates", response_model=list[m.RateRead], tags=["Manager - Rates"])
async def read_manager_rates(current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rates = session.exec(select(m.Rate)).all()
        return rates
    
@app.post("/api/manager/cars/brands/", response_model=m.CarBrandRead, tags=["Manager - Brands"])
async def create_manager_car_brand(brand: m.CarBrandCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        if session.exec(select(m.CarBrand).where(m.CarBrand.name == brand.name)).first():
            raise HTTPException(status_code=400, detail="Brand with that name already exists")
        db_brand = m.CarBrand(
            name=brand.name,
        )
        session.add(db_brand)
        session.commit()
        session.refresh(db_brand)
        return db_brand
    
@app.put("/api/manager/cars/brands/{brand_id}", response_model=m.CarBrandRead, tags=["Manager - Brands"])
async def update_manager_car_brand(brand_id: int, brand: m.CarBrandUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_brand = session.get(m.CarBrand, brand_id)
        if not existing_brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        if brand.name and brand.name != existing_brand.name:
            if session.exec(select(m.CarBrand).where(m.CarBrand.name == brand.name)).first():
                raise HTTPException(status_code=400, detail="Brand name already exists")
            
        update_data = brand.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_brand, key, value)
            
        session.add(existing_brand)
        session.commit()
        session.refresh(existing_brand)
        return existing_brand
    
@app.delete("/api/manager/cars/brands/{brand_id}", tags=["Manager - Brands"])
async def delete_manager_car_brand(brand_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        brand = session.get(m.CarBrand, brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        session.delete(brand)
        session.commit()
        return brand
    
@app.post("/api/manager/cars/brands/models/", response_model=m.CarModelRead, tags=["Manager - Models"])
async def create_manager_car_brand_model(model: m.CarModelCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        if not session.get(m.CarBrand, model.brand_id):
            raise HTTPException(status_code=400, detail="Brand does not exist")
        if session.exec(select(m.CarModel).where(m.CarModel.name == model.name)).first():
            raise HTTPException(status_code=400, detail="Model with that name already exists")
        db_model = m.CarModel(
            name=model.name,
            brand_id=model.brand_id,
        )
        session.add(db_model)
        session.commit()
        session.refresh(db_model)
        return db_model
    
@app.put("/api/manager/cars/brands/models/{model_id}", response_model=m.CarModelRead, tags=["Manager - Models"])
async def update_manager_car_brand_model(model_id: int, model: m.CarModelUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_model = session.get(m.CarModel, model_id)
        if not existing_model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.name and model.name != existing_model.name:
            if session.exec(select(m.CarModel).where(m.CarModel.name == model.name)).first():
                raise HTTPException(status_code=400, detail="Model name already exists")
        if model.brand_id and not session.get(m.CarBrand, model.brand_id):
            raise HTTPException(status_code=400, detail="Brand does not exist")
            
        update_data = model.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_model, key, value)
            
        session.add(existing_model)
        session.commit()
        session.refresh(existing_model)
        return existing_model
    
@app.delete("/api/manager/cars/brands/models/{model_id}", tags=["Manager - Models"])
async def delete_manager_car_brand_model(model_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        model = session.get(m.CarModel, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        session.delete(model)
        session.commit()
        return model
    
@app.post("/api/manager/cars/", response_model=m.CarRead, tags=["Manager - Cars"])
async def create_manager_car(car: m.CarCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        if car.model_id is not None and not session.get(m.CarModel, car.model_id):
            raise HTTPException(status_code=400, detail="Car model does not exist")
        if not session.get(m.CarType, car.type_id):
            raise HTTPException(status_code=400, detail="Car type does not exist")
        available_car_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "available")).first()
        db_car = m.Car(
            model_id=car.model_id,
            year=car.year,
            type_id=car.type_id,
            price_per_day=car.price_per_day,
            status_id=available_car_status.id,
        )
        session.add(db_car)
        session.commit()
        session.refresh(db_car)
        return db_car
    
@app.put("/api/manager/cars/{car_id}", response_model=m.CarRead, tags=["Manager - Cars"])
async def update_manager_car(car_id: int, car: m.CarUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_car = session.get(m.Car, car_id)
        if not existing_car:
            raise HTTPException(status_code=404, detail="Car not found")
        if car.model_id is not None and not session.get(m.CarModel, car.model_id):
            raise HTTPException(status_code=400, detail="Car model does not exist")
        if car.type_id is not None and not session.get(m.CarType, car.type_id):
            raise HTTPException(status_code=400, detail="Car type does not exist")
        if car.status_id is not None and not session.get(m.CarStatus, car.status_id):
            raise HTTPException(status_code=400, detail="Car status does not exist")
            
        update_data = car.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_car, key, value)
            
        session.add(existing_car)
        session.commit()
        session.refresh(existing_car)
        return existing_car
    
@app.delete("/api/manager/cars/{car_id}", tags=["Manager - Cars"])
async def delete_manager_car(car_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        car = session.get(m.Car, car_id)
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        session.delete(car)
        session.commit()
        return car
    
@app.post("/api/manager/rentals/", response_model=m.RentalRead, tags=["Manager - Rentals"])
async def create_manager_rental(rental: m.RentalCreate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        car = session.get(m.Car, rental.car_id)
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        if not session.get(m.User, rental.user_id):
            raise HTTPException(status_code=404, detail="User not found")
        available_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "available")).first()
        if not available_status or car.status_id != available_status.id:
            raise HTTPException(status_code=400, detail="This car is already rented")
        rental_days = (rental.date_of_end_rental - rental.date_of_beginning_rental).days
        if rental_days < 0:
            raise HTTPException(status_code=400, detail="Rental end date must be later than beginning")
        if rental_days == 0:
            rental_days = 1
        rental_price = calculate_rental_price(car.price_per_day, rental_days)
        rented_status = session.exec(select(m.RentalStatus).where(m.RentalStatus.name == "active")).first()
        db_rental = m.Rental(
            user_id=rental.user_id,
            car_id=rental.car_id,
            date_of_beginning_rental=rental.date_of_beginning_rental,
            date_of_end_rental=rental.date_of_end_rental,
            total_price=rental_price,
            status_id=rented_status.id,
        )
        session.add(db_rental)
        rented_car_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "rented")).first()
        car.status_id = rented_car_status.id
        session.add(car)
        session.commit()
        session.refresh(db_rental)
        return db_rental
    
@app.put("/api/manager/rentals/{rental_id}", response_model=m.RentalRead, tags=["Manager - Rentals"])
async def update_manager_rental(rental_id: int, rental: m.RentalUpdate, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        existing_rental = session.get(m.Rental, rental_id)
        if not existing_rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        if rental.car_id is not None:
            target_car_id = rental.car_id
        else: 
            target_car_id = existing_rental.car_id
        if not session.get(m.Car, target_car_id):
            raise HTTPException(status_code=404, detail="Car not found")
        if rental.status_id is not None and not session.get(m.RentalStatus, rental.status_id):
            raise HTTPException(status_code=400, detail="Rental status does not exist")
        active_status = session.exec(select(m.RentalStatus).where(m.RentalStatus.name == "active")).first()
        if session.exec(select(m.Rental).where((m.Rental.car_id == target_car_id) & (m.Rental.status_id == active_status.id) & (m.Rental.id != existing_rental.id))).first():
            raise HTTPException(status_code=400, detail="This car is already rented")
        if rental.status_id is not None:
            completed_status = session.exec(select(m.RentalStatus).where(m.RentalStatus.name == "completed")).first()
            available_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "available")).first()
            rented_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "rented")).first()
            car = session.get(m.Car, existing_rental.car_id)
            if rental.status_id == completed_status.id:
                if car:
                    car.status_id = available_status.id
                    session.add(car)
            elif (existing_rental.status_id == completed_status.id and rental.status_id != completed_status.id):
                if car:
                    car.status_id = rented_status.id
                    session.add(car)
                    
        update_data = rental.model_dump(exclude_unset=True)

        if "total_price" not in update_data and ("date_of_beginning_rental" in update_data or "date_of_end_rental" in update_data or "car_id" in update_data):
            target_car = session.get(m.Car, target_car_id)
            begin = update_data.get("date_of_beginning_rental", existing_rental.date_of_beginning_rental)
            end = update_data.get("date_of_end_rental", existing_rental.date_of_end_rental)
            rental_days = (end - begin).days
            if rental_days < 0:
                raise HTTPException(status_code=400, detail="Rental end date must be later than beginning")
            if rental_days == 0:
                rental_days = 1
            update_data["total_price"] = calculate_rental_price(target_car.price_per_day, rental_days)

        if "car_id" in update_data and update_data["car_id"] != existing_rental.car_id:
            available_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "available")).first()
            rented_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "rented")).first()
            old_car = session.get(m.Car, existing_rental.car_id)
            new_car = session.get(m.Car, update_data["car_id"])
            if old_car:
                old_car.status_id = available_status.id
                session.add(old_car)
            if new_car:
                new_car.status_id = rented_status.id
                session.add(new_car)

        for key, value in update_data.items():
            setattr(existing_rental, key, value)
            
        session.add(existing_rental)
        session.commit()
        session.refresh(existing_rental)
        return existing_rental
    
@app.delete("/api/manager/rentals/{rental_id}", tags=["Manager - Rentals"])
async def delete_manager_rental(rental_id: int, current_user: Annotated[m.User, Depends(get_current_manager_user)]):
    with Session(db.engine) as session:
        rental = session.get(m.Rental, rental_id)
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        car = session.get(m.Car, rental.car_id)
        available_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "available")).first()
        if car and available_status:
            car.status_id = available_status.id
            session.add(car)
        session.delete(rental)
        session.commit()
        return rental
    
#Эндпоинты для клиента
@app.get("/api/cars/{car_id}", response_model=m.CarRead, tags=["Client - Cars"])
async def read_car(car_id: int, current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        car = session.get(m.Car, car_id)
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        return car
    
@app.get("/api/cars/", response_model=list[m.CarRead], tags=["Client - Cars"])
async def read_cars(current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        cars = session.exec(select(m.Car)).all()
        return cars
    
@app.get("/api/rentals/{rental_id}", response_model=m.RentalRead, tags=["Client - Rentals"])
async def read_rental(rental_id: int, current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        rental = session.get(m.Rental, rental_id)
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        if rental.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="This rental is not yours")
        return rental
    
@app.get("/api/rentals/", response_model=list[m.RentalRead], tags=["Client - Rentals"])
async def read_rentals(current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        rentals = session.exec(select(m.Rental).where(m.Rental.user_id == current_user.id)).all()
        return rentals
    
@app.get("/api/rates/{rate_id}", response_model=m.RateRead, tags=["Client - Rates"])
async def read_rate(rate_id: int, current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        rate = session.exec(select(m.Rate).join(m.Rental).where((m.Rate.id == rate_id) & (m.Rental.user_id == current_user.id))).first()
        if not rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        return rate
    
@app.get("/api/rates/", response_model=list[m.RateRead], tags=["Client - Rates"])
async def read_rates(current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        rates = session.exec(select(m.Rate).join(m.Rental).where(m.Rental.user_id == current_user.id)).all()
        return rates
    
@app.post("/api/rentals/", response_model=m.RentalRead, tags=["Client - Rentals"])
async def create_rental(rental: m.RentalClientCreate, current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        car = session.get(m.Car, rental.car_id)
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        available_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "available")).first()
        if not available_status or car.status_id != available_status.id:
            raise HTTPException(status_code=400, detail="This car is already rented")
        rental_days = (rental.date_of_end_rental - rental.date_of_beginning_rental).days
        if rental_days < 0:
            raise HTTPException(status_code=400, detail="Rental end date must be later than beginning")
        if rental_days == 0:
            rental_days = 1
        rental_price = calculate_rental_price(car.price_per_day, rental_days)
        active_status = session.exec(select(m.RentalStatus).where(m.RentalStatus.name == "active")).first()
        db_rental = m.Rental(
            user_id=current_user.id,
            car_id=rental.car_id,
            date_of_beginning_rental=rental.date_of_beginning_rental,
            date_of_end_rental=rental.date_of_end_rental,
            total_price=rental_price,
            status_id=active_status.id
        )
        session.add(db_rental)
        rented_status = session.exec(select(m.CarStatus).where(m.CarStatus.name == "rented")).first()
        car.status_id = rented_status.id
        session.add(car)
        session.commit()
        session.refresh(db_rental)
        return db_rental
    
@app.post("/api/rates/", response_model=m.RateRead, tags=["Client - Rates"])
async def create_rate(rate: m.RateCreate, current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        rental = session.exec(select(m.Rental).where((m.Rental.id == rate.rental_id) & (m.Rental.user_id == current_user.id))).first()
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        rental_end_status = session.exec(select(m.RentalStatus).where(m.RentalStatus.name == "completed")).first()
        if rental.status_id != rental_end_status.id:
            raise HTTPException(status_code=400, detail="This rental is not completed")
        if session.exec(select(m.Rate).where(m.Rate.rental_id == rate.rental_id)).first():
            raise HTTPException(status_code=400, detail="This rate is already exists")
        db_rate = m.Rate(
            rental_id=rate.rental_id,
            rating=rate.rating,
            comment=rate.comment
        )
        session.add(db_rate)
        session.commit()
        session.refresh(db_rate)
        return db_rate
    
@app.put("/api/rates/{rate_id}", response_model=m.RateRead, tags=["Client - Rates"])
async def update_rate(rate_id: int, rate: m.RateUpdate, current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        existing_rate = session.get(m.Rate, rate_id)
        if not existing_rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        rental = session.get(m.Rental, existing_rate.rental_id)
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        if rental.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="This rental is not yours")
        rental_end_status = session.exec(select(m.RentalStatus).where(m.RentalStatus.name == "completed")).first()
        if rental.status_id != rental_end_status.id:
            raise HTTPException(status_code=400, detail="This rental is not completed")

        update_data = rate.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_rate, key, value)
            
        session.add(existing_rate)
        session.commit()
        session.refresh(existing_rate)
        return existing_rate
    
@app.delete("/api/rates/{rate_id}", tags=["Client - Rates"])
async def delete_rate(rate_id: int, current_user: Annotated[m.User, Depends(get_current_user)]):
    with Session(db.engine) as session:
        rate = session.get(m.Rate, rate_id)
        if not rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        rental = session.get(m.Rental, rate.rental_id)
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        if rental.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="This rental is not yours")
        rental_end_status = session.exec(select(m.RentalStatus).where(m.RentalStatus.name == "completed")).first()
        if rental.status_id != rental_end_status.id:
            raise HTTPException(status_code=400, detail="This rental is not completed")
        session.delete(rate)
        session.commit()
        return rate