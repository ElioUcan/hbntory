
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token : str
    token_type: str = "bearer"
    model_config = ConfigDict(
        extra='forbid'
    )

class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8)
    branch_id: int = Field(gt=0)
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True
    )

class UserUpdate(BaseModel):
    username: str | None = Field(min_length=1, max_length=50, default=None)
    password: str | None = Field(min_length=8,default=None)
    branch_id: int | None = Field(gt=0,default=None)
    status: Literal['active', 'deleted'] | None = Field(default=None)
    model_config = ConfigDict(
        extra='forbid'
    )
class UserResponse(BaseModel):
    user_id: int = Field(gt=0)
    username: str = Field(min_length=1, max_length=50)
    role_id: int =Field(gt=0)
    branch_id: int | None = Field(gt=0)
    status: Literal['active', 'deleted']
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True
    )

class StockUpdate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    operation: Literal['add', 'remove']

    model_config = ConfigDict(
        extra='forbid'
    )

class StockResponse(BaseModel):
    stock_id: int = Field(gt=0)
    branch_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=0)
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )

class BranchResponse(BaseModel):
    branch_id: int  = Field(gt=0)
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    model_config = ConfigDict(
        from_attributes=True
    )


class MeResponse(UserResponse):
    role_name: str = Field(min_length=1)
    branch: BranchResponse | None = None
    model_config = ConfigDict(
        from_attributes=True
    )
