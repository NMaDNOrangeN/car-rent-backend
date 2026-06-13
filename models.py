from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel
import db

#Основные таблицы
class AutoBrand(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    models: list["AutoModel"] = Relationship(back_populates="brand")
    autos: list["Auto"] = Relationship(back_populates="brand")

class AutoModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    brand_id: int = Field(foreign_key="autobrand.id")

    brand: AutoBrand = Relationship(back_populates="models")

    autos: list["Auto"] = Relationship(back_populates="model")

class AutoYear(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    year: int

    autos: list["Auto"] = Relationship(back_populates="year")

class AutoType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    autos: list["Auto"] = Relationship(back_populates="type")

class AutoStatus(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    autos: list["Auto"] = Relationship(back_populates="status")

class Auto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    brand_id: int = Field(foreign_key="autobrand.id")
    model_id: int = Field(foreign_key="automodel.id")
    year_id: int = Field(foreign_key="autoyear.id")
    type_id: int = Field(foreign_key="autotype.id")
    price_per_day: float
    status_id: int = Field(foreign_key="autostatus.id")

    brand: AutoBrand = Relationship(back_populates="autos")
    model: AutoModel = Relationship(back_populates="autos")
    year: AutoYear = Relationship(back_populates="autos")
    type: AutoType = Relationship(back_populates="autos")
    status: AutoStatus = Relationship(back_populates="autos")
    
    rentals: list["Rental"] = Relationship(back_populates="auto")
    rates: list["Rate"] = Relationship(back_populates="auto")

class UserType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    users: list["User"] = Relationship(back_populates="type")

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    phone_number: str | None = Field(default=None, unique=True)
    email: str = Field(unique=True, schema_extra={"pattern": r'^([a-z0-9_\.-]+)@([a-z0-9_\.-]+)\.([a-z\.]{2,6})$'})
    password: str = Field(min_length=8, max_length=100, schema_extra={"pattern": r'^([A-Za-z\d]{8,})$'})
    type_id: int = Field(foreign_key="usertype.id")

    type: UserType = Relationship(back_populates="users")
    
    rentals: list["Rental"] = Relationship(back_populates="user")
    rates: list["Rate"] = Relationship(back_populates="user")

class RentalStatus(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    rentals: list["Rental"] = Relationship(back_populates="status")

class Rental(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    auto_id: int = Field(foreign_key="auto.id")
    date_of_beginning_rental: datetime
    date_of_end_rental: datetime
    total_price: float = Field(default=0.0)
    status_id: int = Field(foreign_key="rentalstatus.id")

    user: User = Relationship(back_populates="rentals")
    auto: Auto = Relationship(back_populates="rentals")
    status: RentalStatus = Relationship(back_populates="rentals")

class Rate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    auto_id: int = Field(foreign_key="auto.id")
    user_id: int = Field(foreign_key="user.id")
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=200)

    auto: Auto = Relationship(back_populates="rates")
    user: User = Relationship(back_populates="rates")


#Таблицы для CRUD
