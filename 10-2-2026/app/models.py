"""Request and response contracts: the fields customers can send and receive."""

from pydantic import BaseModel, ConfigDict, Field


class OrderRequest(BaseModel):
    # Forbid extra fields so clients cannot silently send their own price.
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(min_length=1, max_length=50)
    # strict=True rejects booleans and strings such as "2", which JSON otherwise
    # allows and some validators helpfully convert into numbers.
    quantity: int = Field(strict=True, ge=1, le=10)


class Product(BaseModel):
    id: str
    name: str
    price_cents: int
    stock: int


class Order(BaseModel):
    id: str
    product_id: str
    quantity: int
    subtotal_cents: int
    shipping_cents: int
    total_cents: int
