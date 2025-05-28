from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field,field_validator


# Base User Schema
class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True


# Schema for creating a user
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    password_confirm: str

    @field_validator('password')
    def password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v
    
   


# Schema for updating a user
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    
    @field_validator('password')
    def password_strength(cls, v):
        """Validate password strength if provided"""
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v


# Schema for user login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Schema for user in response
class UserInDB(UserBase):
    id: int
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


# Schema for user in response (without sensitive info)
class UserRead(UserInDB):
    pass


# Schema for token response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Schema for token data
class TokenData(BaseModel):
    user_id: Optional[int] = None

