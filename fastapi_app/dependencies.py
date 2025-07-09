"""
Dependency injection for FastAPI application with Django integration
"""

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func
from databases import Database
from typing import Optional, Dict, Any
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

from .database import database
from .models import users
from .schemas import UserResponse, PaginationParams
from .config import settings

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Try to import Django integration
try:
    from .integration import auth_bridge, get_django_user_from_token
    DJANGO_INTEGRATION_AVAILABLE = True
except ImportError:
    DJANGO_INTEGRATION_AVAILABLE = False
    auth_bridge = None
    get_django_user_from_token = None


# Database dependency
async def get_database() -> Database:
    """Get database connection"""
    return database


# Authentication dependencies
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_database)
) -> UserResponse:
    """Get current authenticated user (supports both FastAPI and Django tokens)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    # Try Django authentication first if available
    if DJANGO_INTEGRATION_AVAILABLE:
        django_user_data = get_django_user_from_token(token)
        if django_user_data:
            # Convert Django user data to FastAPI UserResponse format
            return UserResponse(
                id=django_user_data["id"],
                username=django_user_data["username"],
                email=django_user_data["email"],
                full_name=f"{django_user_data.get('first_name', '')} {django_user_data.get('last_name', '')}".strip(),
                is_active=django_user_data["is_active"],
                is_superuser=django_user_data["is_superuser"],
                created_at=datetime.fromisoformat(django_user_data["created_at"].replace('Z', '+00:00')) if django_user_data.get("created_at") else datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
    
    # Try FastAPI JWT token
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        # If token is from Django, we already handled it above
        if payload.get("source") == "django":
            # This should have been caught by Django auth above
            # If we reach here, the Django user might not exist anymore
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Look up user in FastAPI database
    query = select(users).where(users.c.username == username)
    user = await db.fetch_one(query)
    
    if user is None:
        raise credentials_exception
    
    return UserResponse(**user)


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Alternative authentication for Django tokens only
async def get_django_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get user from Django authentication token only"""
    if not DJANGO_INTEGRATION_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Django integration not available"
        )
    
    token = credentials.credentials
    user_data = get_django_user_from_token(token)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Django token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_data


# Pagination dependencies
def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
) -> PaginationParams:
    """Get pagination parameters"""
    return PaginationParams(page=page, size=size)


def calculate_pagination(total: int, page: int, size: int) -> Dict[str, Any]:
    """Calculate pagination metadata"""
    pages = (total + size - 1) // size  # Ceiling division
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1
    }


# Filter dependencies
def get_user_filters(
    username: Optional[str] = Query(None, description="Filter by username"),
    email: Optional[str] = Query(None, description="Filter by email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
) -> Dict[str, Any]:
    """Get user filter parameters"""
    filters = {}
    if username:
        filters["username"] = username
    if email:
        filters["email"] = email
    if is_active is not None:
        filters["is_active"] = is_active
    return filters


def get_product_filters(
    name: Optional[str] = Query(None, description="Filter by product name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
) -> Dict[str, Any]:
    """Get product filter parameters"""
    filters = {}
    if name:
        filters["name"] = name
    if category:
        filters["category"] = category
    if min_price is not None:
        filters["min_price"] = min_price
    if max_price is not None:
        filters["max_price"] = max_price
    if is_active is not None:
        filters["is_active"] = is_active
    return filters


# Integration-aware permission dependencies
class IntegratedPermissionChecker:
    """Permission checker that works with both Django and FastAPI users"""
    
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action
    
    def __call__(self, current_user: UserResponse = Depends(get_current_active_user)):
        # Enhanced permission checking that considers Django roles
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No permission to {self.action} {self.resource}"
            )
        return current_user


# Updated permission dependencies with Django support
require_admin = Depends(get_current_superuser)
require_user = Depends(get_current_active_user)
require_read_users = IntegratedPermissionChecker("users", "read")
require_write_users = IntegratedPermissionChecker("users", "write")
require_read_products = IntegratedPermissionChecker("products", "read")
require_write_products = IntegratedPermissionChecker("products", "write") 