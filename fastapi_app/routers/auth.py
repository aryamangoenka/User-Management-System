"""
Authentication router with async operations and Django integration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, insert
from databases import Database
from typing import Optional

from ..database import database
from ..models import users
from ..schemas import UserCreate, UserResponse, Token, LoginRequest
from ..dependencies import (
    get_database, 
    hash_password, 
    verify_password, 
    create_access_token,
    get_current_user,
    get_current_active_user,
    get_django_user,
    DJANGO_INTEGRATION_AVAILABLE
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Database = Depends(get_database)
):
    """Register a new user"""
    
    # Check if username already exists
    query = select(users).where(users.c.username == user_data.username)
    existing_user = await db.fetch_one(query)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    query = select(users).where(users.c.email == user_data.email)
    existing_email = await db.fetch_one(query)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    
    query = insert(users).values(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False
    )
    
    user_id = await db.execute(query)
    
    # Fetch created user
    query = select(users).where(users.c.id == user_id)
    user = await db.fetch_one(query)
    
    return UserResponse(**user)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Database = Depends(get_database)
):
    """Login with username and password"""
    
    # Find user by username
    query = select(users).where(users.c.username == form_data.username)
    user = await db.fetch_one(query)
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user["username"]})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-json", response_model=Token)
async def login_json(
    login_data: LoginRequest,
    db: Database = Depends(get_database)
):
    """Login with JSON payload"""
    
    # Find user by username
    query = select(users).where(users.c.username == login_data.username)
    user = await db.fetch_one(query)
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user["username"]})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: UserResponse = Depends(get_current_user)
):
    """Refresh access token"""
    access_token = create_access_token(data={"sub": current_user.username})
    return {"access_token": access_token, "token_type": "bearer"} 

# Django Integration Endpoints
if DJANGO_INTEGRATION_AVAILABLE:
    
    @router.post("/django-login", response_model=Token)
    async def login_with_django_token(
        django_token: str,
        db: Database = Depends(get_database)
    ):
        """Login using Django authentication token and get FastAPI token"""
        from ..integration import get_django_user_from_token, create_unified_token
        
        # Validate Django token
        user_data = get_django_user_from_token(django_token)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Django token"
            )
        
        # Create unified token that works for both systems
        unified_token = create_unified_token(django_token)
        if not unified_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create unified token"
            )
        
        return {"access_token": unified_token, "token_type": "bearer"}
    
    
    @router.post("/sync-from-django", response_model=UserResponse)
    async def sync_user_from_django(
        django_user_id: int,
        current_user: UserResponse = Depends(get_current_active_user),
        db: Database = Depends(get_database)
    ):
        """Sync a Django user to FastAPI database (admin only)"""
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can sync users"
            )
        
        from ..integration import sync_user_from_django
        
        # Get Django user data
        django_user_data = sync_user_from_django(django_user_id)
        if not django_user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Django user not found"
            )
        
        # Check if user already exists in FastAPI
        query = select(users).where(users.c.username == django_user_data["username"])
        existing_user = await db.fetch_one(query)
        
        if existing_user:
            # Update existing user
            update_query = users.update().where(
                users.c.username == django_user_data["username"]
            ).values(
                email=django_user_data["email"],
                full_name=django_user_data["full_name"],
                is_active=django_user_data["is_active"],
                is_superuser=django_user_data["is_superuser"]
            )
            await db.execute(update_query)
            
            # Fetch updated user
            user = await db.fetch_one(query)
            return UserResponse(**user)
        else:
            # Create new user
            # Generate a random password since Django handles authentication
            import secrets
            random_password = secrets.token_urlsafe(32)
            
            query = insert(users).values(
                username=django_user_data["username"],
                email=django_user_data["email"],
                full_name=django_user_data["full_name"],
                hashed_password=hash_password(random_password),
                is_active=django_user_data["is_active"],
                is_superuser=django_user_data["is_superuser"]
            )
            
            user_id = await db.execute(query)
            
            # Fetch created user
            query = select(users).where(users.c.id == user_id)
            user = await db.fetch_one(query)
            
            return UserResponse(**user)
    
    
    @router.get("/django-status")
    async def get_django_integration_status():
        """Get Django integration status"""
        return {
            "django_integration_enabled": True,
            "available_endpoints": [
                "/django-login",
                "/sync-from-django",
                "/django-status"
            ],
            "description": "Django integration is active"
        }

else:
    @router.get("/django-status")
    async def get_django_integration_status():
        """Get Django integration status when not available"""
        return {
            "django_integration_enabled": False,
            "error": "Django integration not available",
            "suggestion": "Make sure Django is properly configured"
        } 