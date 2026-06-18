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
    s.add(models.CarStatus(name="available"))
    s.add(models.CarStatus(name="rented"))

    #Посев для типов авто
    s.add(models.CarType(name="Sedan"))
    s.add(models.CarType(name="Hatchback"))
    s.add(models.CarType(name="SUV"))
    s.add(models.CarType(name="Coupe"))
    s.add(models.CarType(name="Minivan"))
    s.add(models.CarType(name="Pickup"))
    s.add(models.CarType(name="Crossover"))
    s.add(models.CarType(name="Sportcar"))

    #Посев для проверки работоспособности API
    #Бренды
    s.add(models.CarBrand(name="Toyota"))
    s.add(models.CarBrand(name="BMW"))
    s.add(models.CarBrand(name="Audi"))
    s.add(models.CarBrand(name="Mercedes"))
    s.add(models.CarBrand(name="Honda"))

    #Модели
    s.add(models.CarModel(name="Camry", brand_id=1))
    s.add(models.CarModel(name="Corolla", brand_id=1))

    s.add(models.CarModel(name="X5", brand_id=2))
    s.add(models.CarModel(name="M3", brand_id=2))

    s.add(models.CarModel(name="A4", brand_id=3))
    s.add(models.CarModel(name="Q7", brand_id=3))

    s.add(models.CarModel(name="C-Class", brand_id=4))
    s.add(models.CarModel(name="GLE", brand_id=4))

    s.add(models.CarModel(name="Civic", brand_id=5))
    s.add(models.CarModel(name="CR-V", brand_id=5))

    #Пользователи
    s.add(models.User(
        username="admin",
        email="admin@example.com",
        phone_number="+10000000001",
        password=get_password_hash("admin123"),
        type_id=1
    ))

    s.add(models.User(
        username="manager",
        email="manager@example.com",
        phone_number="+10000000002",
        password=get_password_hash("manager123"),
        type_id=2
    ))

    s.add(models.User(
        username="client1",
        email="client1@example.com",
        phone_number="+10000000003",
        password=get_password_hash("client123"),
        type_id=3
    ))

    s.add(models.User(
        username="client2",
        email="client2@example.com",
        phone_number="+10000000004",
        password=get_password_hash("client123"),
        type_id=3
    ))

    s.add(models.User(
        username="client3",
        email="client3@example.com",
        phone_number="+10000000005",
        password=get_password_hash("client123"),
        type_id=3
    ))

    #Автомобили
    cars = [
        models.Car(model_id=1, year=2020, type_id=1, price_per_day=100, status_id=1),
        models.Car(model_id=2, year=2022, type_id=2, price_per_day=90, status_id=1),

        models.Car(model_id=3, year=2021, type_id=3, price_per_day=180, status_id=2),
        models.Car(model_id=4, year=2023, type_id=8, price_per_day=300, status_id=1),

        models.Car(model_id=5, year=2019, type_id=1, price_per_day=130, status_id=1),
        models.Car(model_id=6, year=2022, type_id=3, price_per_day=220, status_id=2),

        models.Car(model_id=7, year=2020, type_id=1, price_per_day=170, status_id=1),
        models.Car(model_id=8, year=2023, type_id=7, price_per_day=250, status_id=1),

        models.Car(model_id=9, year=2021, type_id=2, price_per_day=95, status_id=1),
        models.Car(model_id=10, year=2024, type_id=7, price_per_day=160, status_id=1),
    ]

    for car in cars:
        s.add(car)

    #Аренды
    now = datetime.datetime.now()

    rentals = [
        models.Rental(
            user_id=3,
            car_id=3,
            date_of_beginning_rental=now,
            date_of_end_rental=now + datetime.timedelta(days=3),
            total_price=540,
            status_id=1
        ),
        models.Rental(
            user_id=4,
            car_id=6,
            date_of_beginning_rental=now - datetime.timedelta(days=10),
            date_of_end_rental=now - datetime.timedelta(days=5),
            total_price=1100,
            status_id=2
        ),
        models.Rental(
            user_id=5,
            car_id=1,
            date_of_beginning_rental=now - datetime.timedelta(days=20),
            date_of_end_rental=now - datetime.timedelta(days=15),
            total_price=500,
            status_id=2
        )
    ]

    for rental in rentals:
        s.add(rental)

    #Отзывы
    reviews = [
        models.Rate(rental_id=2, rating=4,
                    comment="Comfortable and clean"),
        models.Rate(rental_id=3, rating=3,
                    comment="Average experience")
    ]

    for review in reviews:
        s.add(review)

    s.commit()