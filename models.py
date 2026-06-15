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