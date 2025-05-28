from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


# Base Event Schema
class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    location: str
    start_date: datetime
    end_date: datetime
    image_url: Optional[str] = None
    total_capacity: int
    ticket_price: float
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        """Validate that end date is after start date"""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('total_capacity')
    def capacity_must_be_positive(cls, v):
        """Validate that capacity is positive"""
        if v <= 0:
            raise ValueError('Total capacity must be greater than zero')
        return v
    
    @validator('ticket_price')
    def price_must_be_positive(cls, v):
        """Validate that price is positive"""
        if v < 0:
            raise ValueError('Ticket price cannot be negative')
        return v


# Schema for creating an event
class EventCreate(EventBase):
    is_published: bool = False


# Schema for updating an event
class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    image_url: Optional[str] = None
    total_capacity: Optional[int] = None
    ticket_price: Optional[float] = None
    is_published: Optional[bool] = None
    is_canceled: Optional[bool] = None
    
    @validator('total_capacity')
    def capacity_must_be_positive(cls, v):
        """Validate that capacity is positive if provided"""
        if v is not None and v <= 0:
            raise ValueError('Total capacity must be greater than zero')
        return v
    
    @validator('ticket_price')
    def price_must_be_positive(cls, v):
        """Validate that price is positive if provided"""
        if v is not None and v < 0:
            raise ValueError('Ticket price cannot be negative')
        return v


# Schema for event in response
class EventInDB(EventBase):
    id: int
    available_tickets: int
    is_published: bool
    is_canceled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


# Schema for event in response (public view)
class EventRead(EventInDB):
    pass


# Schema for event list (simplified view)
class EventList(BaseModel):
    id: int
    title: str
    location: str
    start_date: datetime
    ticket_price: float
    available_tickets: int
    is_canceled: bool
    
    class Config:
        orm_mode = True

