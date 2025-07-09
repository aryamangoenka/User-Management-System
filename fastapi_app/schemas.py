"""
Pydantic schemas for request/response models
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserList(BaseSchema):
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


# Product schemas
class ProductBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    category: Optional[str] = Field(None, max_length=50)
    stock_quantity: Optional[int] = Field(0, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, max_length=50)
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime


class ProductList(BaseSchema):
    products: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


# File schemas
class FileResponse(BaseSchema):
    id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    content_type: str
    uploaded_by: int
    created_at: datetime


class FileList(BaseSchema):
    files: List[FileResponse]
    total: int
    page: int
    size: int
    pages: int


# Authentication schemas
class Token(BaseSchema):
    access_token: str
    token_type: str


class TokenData(BaseSchema):
    username: Optional[str] = None


class LoginRequest(BaseSchema):
    username: str
    password: str


# Pagination schemas
class PaginationParams(BaseSchema):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


# Filter schemas
class UserFilter(BaseSchema):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class ProductFilter(BaseSchema):
    name: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None 