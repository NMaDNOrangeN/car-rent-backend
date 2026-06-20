from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship, Column, DateTime
from pydantic import BaseModel, field_validator, StringConstraints
from typing_extensions import Annotated
import db

#Для валидации Email, пароля и номера телефона
EmailStrType = Annotated[str, StringConstraints(pattern=r"^([a-z0-9_\.-]+)@([a-z0-9_\.-]+)\.([a-z\.]{2,6})$")]
PhoneNumberType = Annotated[str, StringConstraints(pattern=r"^\+?[0-9]{10,15}$")]
PasswordStrType = Annotated[str, StringConstraints(pattern=r"^([A-Za-z\d]{8,})$")]

#Основные таблицы
class CarBrand(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))

    models: list["CarModel"] = Relationship(back_populates="brand", cascade_delete=True)

class CarModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    brand_id: int = Field(foreign_key="carbrand.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))

    brand: CarBrand = Relationship(back_populates="models")

    cars: list["Car"] = Relationship(back_populates="model")

class CarType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    cars: list["Car"] = Relationship(back_populates="type")

class CarStatus(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    cars: list["Car"] = Relationship(back_populates="status")

class Car(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    model_id: int | None = Field(default=None, foreign_key="carmodel.id", ondelete="SET NULL")
    year: int
    type_id: int = Field(foreign_key="cartype.id")
    price_per_day: float
    status_id: int = Field(foreign_key="carstatus.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))

    model: CarModel = Relationship(back_populates="cars")
    type: CarType = Relationship(back_populates="cars")
    status: CarStatus = Relationship(back_populates="cars")
    
    rentals: list["Rental"] = Relationship(back_populates="car", cascade_delete=True)

class UserType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    users: list["User"] = Relationship(back_populates="type")

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    phone_number: PhoneNumberType | None = Field(default=None, unique=True)
    email: EmailStrType = Field(unique=True)
    password: PasswordStrType = Field(min_length=8, max_length=100)
    type_id: int = Field(foreign_key="usertype.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))
    
    type: UserType = Relationship(back_populates="users")
    
    rentals: list["Rental"] = Relationship(back_populates="user", cascade_delete=True)

class RentalStatus(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    rentals: list["Rental"] = Relationship(back_populates="status")

class Rental(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    car_id: int = Field(foreign_key="car.id", ondelete="CASCADE")
    date_of_beginning_rental: datetime
    date_of_end_rental: datetime
    total_price: float = Field(default=0.0)
    status_id: int = Field(foreign_key="rentalstatus.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))
    
    user: User = Relationship(back_populates="rentals")
    car: Car = Relationship(back_populates="rentals")
    status: RentalStatus = Relationship(back_populates="rentals")

    rates: list["Rate"] = Relationship (back_populates="rental", cascade_delete=True)

class Rate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rental_id: int = Field(unique=True, foreign_key="rental.id", ondelete="CASCADE")
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))

    rental: Rental = Relationship(back_populates="rates")


#Таблицы для CRUD
#Админ-таблицы
class UserCreate(BaseModel):
    username: str
    phone_number: PhoneNumberType | None = None
    email: EmailStrType
    password: PasswordStrType
    type_id: int

class UserRead(BaseModel):
    id: int
    username: str
    phone_number: PhoneNumberType | None = None
    email: EmailStrType
    type_id: int

class UserUpdate(BaseModel):
    username: str | None = None
    phone_number: PhoneNumberType | None = None
    email: EmailStrType | None = None
    password: PasswordStrType | None = None
    type_id: int | None = None

class UserTypeRead(BaseModel):
    id: int
    name: str

#Менеджер-таблицы
class CarBrandCreate(BaseModel):
    name: str

class CarBrandRead(BaseModel):
    id: int
    name: str

class CarBrandUpdate(BaseModel):
    name: str | None = None

class CarModelCreate(BaseModel):
    name: str
    brand_id: int

class CarModelRead(BaseModel):
    id: int
    name: str
    brand_id: int

class CarModelUpdate(BaseModel):
    name: str | None = None
    brand_id: int | None = None

class CarTypeRead(BaseModel):
    id: int
    name: str

class CarStatusRead(BaseModel):
    id: int
    name: str

class CarCreate(BaseModel):
    model_id: int | None = None
    year: int
    type_id: int
    price_per_day: float

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        current_year = datetime.now().year
        if not (1900 <= value <= current_year):
            raise ValueError(f"Year must be between 1900 and {current_year}")
        return value

class CarRead(BaseModel):
    id: int
    model_id: int | None = None
    year: int
    type_id: int
    price_per_day: float
    status_id: int

class CarUpdate(BaseModel):
    model_id: int | None = None
    year: int | None = None
    type_id: int | None = None
    price_per_day: float | None = None
    status_id: int | None = None

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        current_year = datetime.now().year
        if not (1900 <= value <= current_year):
            raise ValueError(f"Year must be between 1900 and {current_year}")
        return value

class RentalStatusRead(BaseModel):
    id: int
    name: str

class RentalCreate(BaseModel):
    user_id: int
    car_id: int
    date_of_beginning_rental: datetime
    date_of_end_rental: datetime
    total_price: float

class RentalRead(BaseModel):
    id: int
    user_id: int
    car_id: int
    date_of_beginning_rental: datetime
    date_of_end_rental: datetime
    total_price: float
    status_id: int

class RentalUpdate(BaseModel):
    car_id: int | None = None
    date_of_beginning_rental: datetime | None = None
    date_of_end_rental: datetime | None = None
    total_price: float | None = None
    status_id: int | None = None

class RateRead(BaseModel):
    id: int
    rental_id: int
    rating: int
    comment: str | None = None

#Клиент-таблицы
class RentalClientCreate(BaseModel):
    car_id: int
    date_of_beginning_rental: datetime
    date_of_end_rental: datetime

class RateCreate(BaseModel):
    rental_id: int
    rating: int
    comment: str | None = None

class RateUpdate(BaseModel):
    rating: int
    comment: str | None = None