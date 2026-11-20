from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship
from sqlalchemy import (
    ForeignKey,
    String,
    UniqueConstraint,
    CheckConstraint,
    Integer,
    DateTime,
    func
)

class Base(DeclarativeBase):
    pass

class Roles(Base):
    __tablename__ = 'roles'
    role_id = mapped_column(primary_key=True)
    name = mapped_column(String(20), unique=True, nullable=False)
    description = mapped_column(String(50), nullable=False)
    users = relationship(
        back_populates='role'
    )
    __table_args__ = (
        UniqueConstraint('name', 'role_id', name= 'uq_branch_product')
    )


class Branches(Base):
    __tablename__ = 'branches'
    branch_id = mapped_column(primary_key=True)
    name = mapped_column(String(50), unique=True, nullable=False)
    location = mapped_column(String(50), unique=True, nullable=False)
    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    users = relationship(
        back_populates='branch'
    )
    stocks = relationship(
        back_populates='branch'
    )
    __table_args__ = (
        UniqueConstraint('name', 'branch_id', name= 'uq_branch_product')
    )

class Stock(Base):
    __tablename__ = 'stock'
    stock_id = mapped_column(primary_key=True)
    branch_id = mapped_column(ForeignKey('branches.branch_id'))
    product = mapped_column()
    quantity = mapped_column(Integer) # verificar que esto es correcto
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    branches = relationship(
        back_populates='stocks'
    )
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='check positive stock'),
        UniqueConstraint('stock_id', 'branch_id', name= 'uq_branch_product')
    )


class Users(Base):
    __tablename__ = 'users'
    user_id = mapped_column(primary_key=True)
    username = mapped_column(String(50), unique=True, nullable=False)
    password_hash = mapped_column(String(256))
    role_id = mapped_column(ForeignKey('roles.role_id'))
    branch_id = mapped_column(ForeignKey('branches.branch_id'))
    status = mapped_column(String(50), nullable=False)
    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    role = relationship(
        back_populates='users'
    )
    branch = relationship(
        back_populates='users'
    )
