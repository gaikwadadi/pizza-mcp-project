from pydantic import BaseModel, validator
from typing import List, Optional

class MenuItem(BaseModel):
    id: int
    name: str
    price: float
    sizes: List[str]
    description: str

class MenuItemCreate(BaseModel):
    name: str
    price: float
    sizes: List[str]
    description: Optional[str] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        if v > 999.99:
            raise ValueError('Price cannot exceed $999.99')
        # Round to 2 decimal places
        return round(v, 2)
    
    @validator('sizes')
    def sizes_must_not_be_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one size must be provided')
        # Remove empty strings and duplicates
        clean_sizes = list(set([size.strip() for size in v if size.strip()]))
        if not clean_sizes:
            raise ValueError('At least one valid size must be provided')
        return clean_sizes

class OrderItem(BaseModel):
    pizza: str
    size: str
    quantity: int = 1
    price: float = 0

class OrderRequest(BaseModel):
    items: List[OrderItem]
    customer_email: Optional[str] = None

class OrderResponse(BaseModel):
    order_id: str
    items: List[OrderItem]
    total_amount: float
    status: str
    prep_time: str

class OrderStatus(BaseModel):
    order_id: str
    customer_email: Optional[str] = None
    items: List[OrderItem]
    total_amount: float
    status: str
    prep_time: str
    created_at: str
