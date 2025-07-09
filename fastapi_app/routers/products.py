"""
Products router with async CRUD operations, pagination, and filtering
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, insert, update, delete, func, and_, or_
from databases import Database
from typing import Optional, Dict, Any

from ..database import database
from ..models import products, users
from ..schemas import (
    ProductResponse, 
    ProductCreate, 
    ProductUpdate, 
    ProductList,
    PaginationParams,
    UserResponse
)
from ..dependencies import (
    get_database,
    get_current_active_user,
    get_current_superuser,
    get_pagination_params,
    get_product_filters,
    calculate_pagination
)

router = APIRouter()


@router.get("/", response_model=ProductList)
async def list_products(
    pagination: PaginationParams = Depends(get_pagination_params),
    filters: Dict[str, Any] = Depends(get_product_filters),
    db: Database = Depends(get_database)
):
    """List products with pagination and filtering (public endpoint)"""
    
    # Build base query
    query = select(products).where(products.c.is_active == True)
    conditions = [products.c.is_active == True]
    
    # Apply filters
    if filters.get("name"):
        conditions.append(products.c.name.ilike(f"%{filters['name']}%"))
    
    if filters.get("category"):
        conditions.append(products.c.category.ilike(f"%{filters['category']}%"))
    
    if filters.get("min_price") is not None:
        conditions.append(products.c.price >= filters["min_price"])
    
    if filters.get("max_price") is not None:
        conditions.append(products.c.price <= filters["max_price"])
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(products.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return ProductList(
        products=[ProductResponse(**product) for product in results],
        **pagination_meta
    )


@router.get("/admin/", response_model=ProductList)
async def list_all_products(
    pagination: PaginationParams = Depends(get_pagination_params),
    filters: Dict[str, Any] = Depends(get_product_filters),
    current_user: UserResponse = Depends(get_current_superuser),
    db: Database = Depends(get_database)
):
    """List all products including inactive ones (admin only)"""
    
    # Build base query
    query = select(products)
    conditions = []
    
    # Apply filters
    if filters.get("name"):
        conditions.append(products.c.name.ilike(f"%{filters['name']}%"))
    
    if filters.get("category"):
        conditions.append(products.c.category.ilike(f"%{filters['category']}%"))
    
    if filters.get("min_price") is not None:
        conditions.append(products.c.price >= filters["min_price"])
    
    if filters.get("max_price") is not None:
        conditions.append(products.c.price <= filters["max_price"])
    
    if filters.get("is_active") is not None:
        conditions.append(products.c.is_active == filters["is_active"])
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(products.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return ProductList(
        products=[ProductResponse(**product) for product in results],
        **pagination_meta
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Database = Depends(get_database)
):
    """Get a specific product by ID (public endpoint)"""
    
    query = select(products).where(
        and_(products.c.id == product_id, products.c.is_active == True)
    )
    product = await db.fetch_one(query)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return ProductResponse(**product)


@router.get("/admin/{product_id}", response_model=ProductResponse)
async def get_product_admin(
    product_id: int,
    current_user: UserResponse = Depends(get_current_superuser),
    db: Database = Depends(get_database)
):
    """Get a specific product by ID including inactive (admin only)"""
    
    query = select(products).where(products.c.id == product_id)
    product = await db.fetch_one(query)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return ProductResponse(**product)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Create a new product"""
    
    # Create product
    query = insert(products).values(
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        category=product_data.category,
        stock_quantity=product_data.stock_quantity,
        created_by=current_user.id,
        is_active=True
    )
    
    product_id = await db.execute(query)
    
    # Fetch created product
    query = select(products).where(products.c.id == product_id)
    product = await db.fetch_one(query)
    
    return ProductResponse(**product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Update a product (owner or admin)"""
    
    # Check if product exists
    query = select(products).where(products.c.id == product_id)
    existing_product = await db.fetch_one(query)
    
    if not existing_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check permissions (product owner or admin)
    if existing_product["created_by"] != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Prepare update data
    update_data = {}
    if product_data.name is not None:
        update_data["name"] = product_data.name
    
    if product_data.description is not None:
        update_data["description"] = product_data.description
    
    if product_data.price is not None:
        update_data["price"] = product_data.price
    
    if product_data.category is not None:
        update_data["category"] = product_data.category
    
    if product_data.stock_quantity is not None:
        update_data["stock_quantity"] = product_data.stock_quantity
    
    # Only superusers can change is_active
    if product_data.is_active is not None and current_user.is_superuser:
        update_data["is_active"] = product_data.is_active
    
    if not update_data:
        # Nothing to update
        return ProductResponse(**existing_product)
    
    # Update product
    query = update(products).where(products.c.id == product_id).values(**update_data)
    await db.execute(query)
    
    # Fetch updated product
    query = select(products).where(products.c.id == product_id)
    updated_product = await db.fetch_one(query)
    
    return ProductResponse(**updated_product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Delete a product (owner or admin)"""
    
    # Check if product exists
    query = select(products).where(products.c.id == product_id)
    product = await db.fetch_one(query)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check permissions (product owner or admin)
    if product["created_by"] != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Delete product
    query = delete(products).where(products.c.id == product_id)
    await db.execute(query)


@router.get("/search/", response_model=ProductList)
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Database = Depends(get_database)
):
    """Search products by name, description, or category"""
    
    # Build search query
    search_conditions = and_(
        products.c.is_active == True,
        or_(
            products.c.name.ilike(f"%{q}%"),
            products.c.description.ilike(f"%{q}%"),
            products.c.category.ilike(f"%{q}%")
        )
    )
    
    query = select(products).where(search_conditions)
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(products.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return ProductList(
        products=[ProductResponse(**product) for product in results],
        **pagination_meta
    )


@router.get("/categories/", response_model=list[str])
async def get_categories(
    db: Database = Depends(get_database)
):
    """Get all product categories"""
    
    query = select(products.c.category).where(
        and_(products.c.is_active == True, products.c.category.isnot(None))
    ).distinct()
    
    results = await db.fetch_all(query)
    categories = [row["category"] for row in results if row["category"]]
    
    return sorted(categories)


@router.get("/my/", response_model=ProductList)
async def get_my_products(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Database = Depends(get_database)
):
    """Get products created by current user"""
    
    query = select(products).where(products.c.created_by == current_user.id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total = await db.fetch_val(count_query)
    
    # Apply pagination
    offset = (pagination.page - 1) * pagination.size
    query = query.offset(offset).limit(pagination.size).order_by(products.c.created_at.desc())
    
    # Execute query
    results = await db.fetch_all(query)
    
    # Calculate pagination metadata
    pagination_meta = calculate_pagination(total, pagination.page, pagination.size)
    
    return ProductList(
        products=[ProductResponse(**product) for product in results],
        **pagination_meta
    ) 