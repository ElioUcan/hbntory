from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductSummary(BaseModel):
    """Compact catalog representation returned when listing products."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)
    sku: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    unit_price: float = Field(gt=0)
    currency: str = Field(min_length=1)
    discontinued: bool


class ProductDetail(ProductSummary):
    """Full catalog metadata returned when inspecting a single product."""

    description: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    supplier_name: str = Field(min_length=1)
    weight_kg: float | None = Field(default=None, gt=0)
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime


class ProductListOutput(BaseModel):
    """Paginated product catalog listing returned by list_products."""

    model_config = ConfigDict(extra="ignore")

    count: int = Field(ge=0)
    limit: int = Field(ge=0)
    offset: int = Field(ge=0)
    results: list[ProductSummary]
