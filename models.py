from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship, Column, DateTime
from pydantic import BaseModel, field_validator
import db

#Основные таблицы
class AutoBrand(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))

    models: list["AutoModel"] = Relationship(back_populates="brand", cascade_delete=True)
    autos: list["Auto"] = Relationship(back_populates="brand", cascade_delete=True)

class AutoModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    brand_id: int = Field(foreign_key="autobrand.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))

    brand: AutoBrand = Relationship(back_populates="models")

    autos: list["Auto"] = Relationship(back_populates="model")

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
    brand_id: int = Field(foreign_key="autobrand.id", ondelete="CASCADE")
    model_id: int | None = Field(default=None, foreign_key="automodel.id", ondelete="SET NULL")
    year: int
    type_id: int = Field(foreign_key="autotype.id")
    price_per_day: float
    status_id: int = Field(foreign_key="autostatus.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))

    brand: AutoBrand = Relationship(back_populates="autos")
    model: AutoModel = Relationship(back_populates="autos")
    type: AutoType = Relationship(back_populates="autos")
    status: AutoStatus = Relationship(back_populates="autos")
    
    rentals: list["Rental"] = Relationship(back_populates="auto", cascade_delete=True)
    rates: list["Rate"] = Relationship(back_populates="auto", cascade_delete=True)

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        current_year = datetime.now().year
        if not (1900 <= value <= current_year):
            raise ValueError(f"Year must be between 1900 and {current_year}")
        return value

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
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))
    
    type: UserType = Relationship(back_populates="users")
    
    rentals: list["Rental"] = Relationship(back_populates="user", cascade_delete=True)
    rates: list["Rate"] = Relationship(back_populates="user", cascade_delete=True)

class RentalStatus(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

    rentals: list["Rental"] = Relationship(back_populates="status")

class Rental(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    auto_id: int = Field(foreign_key="auto.id", ondelete="CASCADE")
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
    auto: Auto = Relationship(back_populates="rentals")
    status: RentalStatus = Relationship(back_populates="rentals")

class Rate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    auto_id: int = Field(foreign_key="auto.id", ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, 
                                 sa_column=Column(DateTime, 
                                                  default=datetime.now, 
                                                  onupdate=datetime.now))
    auto: Auto = Relationship(back_populates="rates")
    user: User = Relationship(back_populates="rates")


#Таблицы для CRUD
#Админ-таблицы
class UserCreate(BaseModel):
    username: str
    phone_number: str | None = None
    email: str
    password: str
    type_id: int

class UserRead(BaseModel):
    id: int
    username: str
    phone_number: str | None = None
    email: str
    type_id: int

class UserUpdate(BaseModel):
    username: str | None = None
    phone_number: str | None = None
    email: str | None = None
    password: str | None = None
    type_id: int | None = None

class UserTypeRead(BaseModel):
    id: int
    name: str

#Менеджер-таблицы
class AutoBrandCreate(BaseModel):
    name: str

class AutoBrandRead(BaseModel):
    id: int
    name: str

class AutoBrandUpdate(BaseModel):
    name: str | None = None

class AutoModelCreate(BaseModel):
    name: str
    brand_id: int

class AutoModelRead(BaseModel):
    id: int
    name: str
    brand_id: int

class AutoModelUpdate(BaseModel):
    name: str | None = None
    brand_id: int | None = None

class AutoTypeRead(BaseModel):
    id: int
    name: str

class AutoStatusRead(BaseModel):
    id: int
    name: str

class AutoCreate(BaseModel):
    brand_id: int
    model_id: int | None = None
    year: int
    type_id: int
    price_per_day: float

class AutoRead(BaseModel):
    id: int
    brand_id: int
    model_id: int | None = None
    year: int
    type_id: int
    price_per_day: float
    status_id: int

class AutoUpdate(BaseModel):
    brand_id: int | None = None
    model_id: int | None = None
    year: int | None = None
    type_id: int | None = None
    price_per_day: float | None = None
    status_id: int | None = None

class RentalStatusRead(BaseModel):
    id: int
    name: str

class RentalCreate(BaseModel):
    user_id: int
    auto_id: int
    date_of_beginning_rental: datetime
    date_of_end_rental: datetime
    total_price: float

class RentalRead(BaseModel):
    id: int
    user_id: int
    auto_id: int
    date_of_beginning_rental: datetime
    date_of_end_rental: datetime
    total_price: float
    status_id: int

class RentalUpdate(BaseModel):
    auto_id: int | None = None
    date_of_beginning_rental: datetime | None = None
    date_of_end_rental: datetime | None = None
    total_price: float | None = None
    status_id: int | None = None

class RateRead(BaseModel):
    id: int
    auto_id: int
    user_id: int
    rating: int
    comment: str | None = None

#Клиент-таблицы