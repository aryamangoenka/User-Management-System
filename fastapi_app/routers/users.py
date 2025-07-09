"""
Users router with async CRUD operations, pagination, and filtering
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, insert, update, delete, func, and_, or_
from databases import Database
from typing import Optional, Dict, Any

from ..database import database
from ..models import users
from ..schemas import (
    UserResponse, 
    UserCreate, 
    UserUpdate, 
    UserList,
    PaginationParams
)
from ..dependencies import (
    get_database,
    get_current_active_user,
    get_current_superuser,
    get_pagination_params,
    get_user_filters,
    calculate_pagination,
    hash_password
)

router = APIRouter()


@router.get("/", response_model=UserList)
async def list_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    filters: Dict[str, Any] = Depends(get_user_filters),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """List users with pagination and filtering"""
    
    # Build base query
    query = select(users)
    conditions = []
    
    # Apply filters
    if filters.get("username"):
        conditions.append(users.c.username.ilike(f"%{filters['username']}%"))
    
    if filters.get("email"):
        conditions.append(users.c.email.ilike(f"%{filters['email']}%"))
    
    if filters.get("is_active") is not None:
        conditions.append(users.c.is_active == filters["is_active"])
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(users.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return UserList(
        users=[UserResponse(**user) for user in results],
        **pagination_meta
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Get a specific user by ID"""
    
    query = select(users).where(users.c.id == user_id)
    user = await db.fetch_one(query)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: UserResponse = Depends(get_current_superuser),
    db: Database = Depends(get_database)
):
    """Create a new user (admin only)"""
    
    # Check if username already exists
    query = select(users).where(users.c.username == user_data.username)
    existing_user = await db.fetch_one(query)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    query = select(users).where(users.c.email == user_data.email)
    existing_email = await db.fetch_one(query)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
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


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Update a user (own profile or admin)"""
    
    # Check if user exists
    query = select(users).where(users.c.id == user_id)
    existing_user = await db.fetch_one(query)
    
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions (users can only update their own profile, admins can update any)
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Prepare update data
    update_data = {}
    if user_data.username is not None:
        # Check username uniqueness
        query = select(users).where(
            and_(users.c.username == user_data.username, users.c.id != user_id)
        )
        if await db.fetch_one(query):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        update_data["username"] = user_data.username
    
    if user_data.email is not None:
        # Check email uniqueness
        query = select(users).where(
            and_(users.c.email == user_data.email, users.c.id != user_id)
        )
        if await db.fetch_one(query):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        update_data["email"] = user_data.email
    
    if user_data.full_name is not None:
        update_data["full_name"] = user_data.full_name
    
    # Only superusers can change is_active
    if user_data.is_active is not None and current_user.is_superuser:
        update_data["is_active"] = user_data.is_active
    
    if not update_data:
        # Nothing to update
        return UserResponse(**existing_user)
    
    # Update user
    query = update(users).where(users.c.id == user_id).values(**update_data)
    await db.execute(query)
    
    # Fetch updated user
    query = select(users).where(users.c.id == user_id)
    updated_user = await db.fetch_one(query)
    
    return UserResponse(**updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: UserResponse = Depends(get_current_superuser),
    db: Database = Depends(get_database)
):
    """Delete a user (admin only)"""
    
    # Check if user exists
    query = select(users).where(users.c.id == user_id)
    user = await db.fetch_one(query)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Delete user
    query = delete(users).where(users.c.id == user_id)
    await db.execute(query)


@router.get("/search/", response_model=UserList)
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Search users by username, email, or full name"""
    
    # Build search query
    search_conditions = or_(
        users.c.username.ilike(f"%{q}%"),
        users.c.email.ilike(f"%{q}%"),
        users.c.full_name.ilike(f"%{q}%")
    )
    
    query = select(users).where(search_conditions)
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(users.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return UserList(
        users=[UserResponse(**user) for user in results],
        **pagination_meta
    ) 