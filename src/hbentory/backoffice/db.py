from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Roles(Base):
    __tablename__ = "roles"

    role_id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(20), unique=True, nullable=False)
    description = mapped_column(String(50), nullable=False)

    users = relationship("Users", back_populates="role")


class Branches(Base):
    __tablename__ = "branches"

    branch_id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(50), unique=True, nullable=False)
    location = mapped_column(String(50), unique=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    users = relationship("Users", back_populates="branch")
    stocks = relationship("Stock", back_populates="branch")


class Stock(Base):
    __tablename__ = "stock"

    stock_id = mapped_column(Integer, primary_key=True)
    branch_id = mapped_column(ForeignKey("branches.branch_id"), nullable=False)
    product_id = mapped_column(Integer, nullable=False)
    quantity = mapped_column(Integer, nullable=False)
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    branch = relationship("Branches", back_populates="stocks")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_stock_positive"),
        UniqueConstraint("branch_id", "product_id", name="uq_branch_product"),
    )


class Users(Base):
    __tablename__ = "users"

    user_id = mapped_column(Integer, primary_key=True)
    username = mapped_column(String(50), unique=True, nullable=False)
    password_hash = mapped_column(String(256), nullable=False)
    role_id = mapped_column(ForeignKey("roles.role_id"), nullable=False)
    branch_id = mapped_column(ForeignKey("branches.branch_id"), nullable=True)
    status = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    role = relationship("Roles", back_populates="users")
    branch = relationship("Branches", back_populates="users")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'deleted')", name="ck_users_status"),
    )
