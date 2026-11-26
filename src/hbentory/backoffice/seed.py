import os
import random

import requests
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from hbentory.backoffice.db import (
    Base,
    Branches,
    Roles,
    Stock,
    Users,
)
from hbentory.backoffice.security import hash_password

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB", "hbentory")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin_secret_123")
COMMON_PASSWORD = os.getenv("COMMON_PASSWORD", "common_secret_123")
PRODUCT_API_URL = os.getenv("PRODUCT_API_URL", "http://127.0.0.1:5000")

product_ids = list(range(1, 31))


def get_engine() -> Engine:
    database_url = os.getenv(
        "DATABASE_URL",
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@127.0.0.1:5432/{POSTGRES_DB}",
    )
    return create_engine(database_url)

def create_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("DB Schema created")

def update_stock(
    session: Session,
    branch_id: int,
    product_id: int,
    quantity: int,
    operation: str = "add",
    check_api: bool = True,
) -> Stock:
    if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
        raise ValueError("Product ID must be a positive integer")

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Quantity must be a positive integer")

    if operation not in ("add", "remove"):
        raise ValueError("Operation must be 'add' or 'remove'")

    if session.get(Branches, branch_id) is None:
        raise ValueError("Invalid branch")

    if check_api:
        try:
            response = requests.get(
                f"{PRODUCT_API_URL}/api/v1/products/{product_id}",
                timeout=3,
            )
        except requests.RequestException as exc:
            raise ValueError("Product API unavailable") from exc
        if response.status_code != 200:
            raise ValueError("Invalid external product_id")

    stock = session.scalar(
        select(Stock).where(
            Stock.branch_id == branch_id,
            Stock.product_id == product_id,
        )
    )
    current_quantity = stock.quantity if stock is not None else 0
    delta = quantity if operation == "add" else -quantity
    new_quantity = current_quantity + delta
    if new_quantity < 0:
        raise ValueError("Stock quantity cannot become negative")

    if stock is None:
        stock = Stock(branch_id=branch_id, product_id=product_id, quantity=new_quantity)
        session.add(stock)
    else:
        stock.quantity = new_quantity

    return stock


def insert_data() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if session.scalar(select(Roles.role_id).limit(1)) is not None:
            return

        admin_role = Roles(name="admin", description="System administrator")
        common_role = Roles(name="common", description="Branch operator")
        sucursal_norte = Branches(name="Sucursal Norte", location="Calle 40")
        sucursal_centro = Branches(name="Sucursal Centro", location="Avenida 10")
        admin_user = Users(
            username="admin_user",
            password_hash=hash_password(ADMIN_PASSWORD),
            status="active",
            role=admin_role,
            branch=None,
        )
        common_norte = Users(
            username="common_norte",
            password_hash=hash_password(COMMON_PASSWORD),
            status="active",
            role=common_role,
            branch=sucursal_norte,
        )
        common_centro = Users(
            username="common_centro",
            password_hash=hash_password(COMMON_PASSWORD),
            status="active",
            role=common_role,
            branch=sucursal_centro,
        )
        stock_items = [
            Stock(
                product_id=pid,
                quantity=random.randint(1, 50),
                branch=sucursal_norte,
            )
            for pid in product_ids[:15]
        ] + [
            Stock(
                product_id=pid,
                quantity=random.randint(1, 50),
                branch=sucursal_centro,
            )
            for pid in product_ids[15:]
        ]

        session.add_all(
            [
                admin_role,
                common_role,
                sucursal_norte,
                sucursal_centro,
                admin_user,
                common_norte,
                common_centro,
                *stock_items,
            ]
        )
        session.commit()


def test_data() -> None:
    engine = get_engine()
    with Session(engine) as session:
        query = (
            select(Stock)
            .where(Stock.branch_id == 1)
            .where(Stock.quantity > 0)
        )
        items = session.scalars(query).all()
        for item in items:
            print(f"Producto ID {item.product_id} - Quantity: {item.quantity}")


if __name__ == "__main__":
    create_db()
    insert_data()
    test_data()
