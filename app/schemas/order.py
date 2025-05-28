from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from app.models.order import OrderStatus


# Base Order Schema
class OrderBase(BaseModel):
    event_id: int
    quantity: int = Field(..., gt=0)
    
    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        """Validate that quantity is positive"""
        if v <= 0:
            raise ValueError('Quantity must be greater than zero')
        return v


# Schema for creating an order
class OrderCreate(OrderBase):
    payment_method: str


# Schema for updating an order
class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_id: Optional[str] = None
    payment_method: Optional[str] = None


# Schema for order in response
class OrderInDB(OrderBase):
    id: int
    user_id: int
    unit_price: float
    total_amount: float
    status: OrderStatus
    payment_id: Optional[str] = None
    payment_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


# Schema for order in response (with event details)
class OrderRead(OrderInDB):
    event_title: str
    event_date: datetime
    
    class Config:
        orm_mode = True


# Schema for payment processing
class PaymentProcess(BaseModel):
    order_id: int
    payment_method: str
    card_number: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    card_cvc: Optional[str] = None


# Schema for payment response
class PaymentResponse(BaseModel):
    order_id: int
    status: OrderStatus
    payment_id: Optional[str] = None
    message: str

