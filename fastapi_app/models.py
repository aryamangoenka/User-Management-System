"""
SQLAlchemy models for FastAPI application
"""

import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.sql import func
from .database import metadata

# Users table
users = Table(
    "fastapi_users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("username", String(50), unique=True, index=True, nullable=False),
    Column("email", String(100), unique=True, index=True, nullable=False),
    Column("full_name", String(100), nullable=True),
    Column("hashed_password", String(255), nullable=False),
    Column("is_active", Boolean, default=True),
    Column("is_superuser", Boolean, default=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)

# Products table
products = Table(
    "fastapi_products",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String(100), nullable=False, index=True),
    Column("description", Text, nullable=True),
    Column("price", Float, nullable=False),
    Column("category", String(50), nullable=True, index=True),
    Column("is_active", Boolean, default=True),
    Column("stock_quantity", Integer, default=0),
    Column("created_by", Integer, ForeignKey("fastapi_users.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)

# Files table
files = Table(
    "fastapi_files",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("filename", String(255), nullable=False),
    Column("original_filename", String(255), nullable=False),
    Column("file_path", String(500), nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("content_type", String(100), nullable=False),
    Column("uploaded_by", Integer, ForeignKey("fastapi_users.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
) 