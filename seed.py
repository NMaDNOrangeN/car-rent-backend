import models
import datetime
from security import get_password_hash

models.db.create_db_and_tables()

with models.db.Session(models.db.engine) as s:
    #Посев типов пользователей
    s.add(models.UserType(name="admin"))
    s.add(models.UserType(name="manager"))
    s.add(models.UserType(name="client"))

    #Посев статусов аренды
    s.add(models.RentalStatus(name="active"))
    s.add(models.RentalStatus(name="completed"))

    #Посев статусов авто
    s.add(models.AutoStatus(name="available"))
    s.add(models.AutoStatus(name="rented"))

    #Посев для типов авто
    s.add(models.AutoType(name="Sedan"))
    s.add(models.AutoType(name="Hatchback"))
    s.add(models.AutoType(name="SUV"))
    s.add(models.AutoType(name="Coupe"))
    s.add(models.AutoType(name="Minivan"))
    s.add(models.AutoType(name="Pickup"))
    s.add(models.AutoType(name="Crossover"))
    s.add(models.AutoType(name="Sportcar"))

    #Посев для проверки работоспособности API
    s.add(models.AutoBrand(name="Toyota"))
    s.add(models.AutoModel(name="Camry", brand_id=1))
    s.add(models.Auto(brand_id=1, model_id=1, year=2020, type_id=1, price_per_day=100.0, status_id=1))

    s.add(models.User(username="admin", email="admin@example.com", password=get_password_hash("admin123"), type_id=1))
    s.add(models.User(username="manager", email="manager@example.com", password=get_password_hash("manager123"), type_id=2))
    s.add(models.User(username="client", email="client@example.com", password=get_password_hash("client123"), type_id=3))

    s.add(models.Rental(user_id=3, auto_id=1, date_of_beginning_rental=datetime.datetime.now(), date_of_end_rental=datetime.datetime.now() + datetime.timedelta(days=1), total_price=100.0, status_id=1))

    s.add(models.Rate(auto_id=1, user_id=3, rating=5, comment="Great car!"))

    s.commit()