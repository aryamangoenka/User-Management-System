"""
Test configuration and fixtures
"""

import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from databases import Database
import tempfile
import os

from ..main import app
from ..database import metadata, database
from ..config import settings
from ..dependencies import hash_password


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_fastapi.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db():
    """Create test database"""
    # Use synchronous SQLite for table creation
    sync_url = TEST_DATABASE_URL.replace('+aiosqlite', '')
    engine = create_engine(sync_url, echo=False)
    
    # Create tables
    metadata.create_all(engine)
    engine.dispose()
    
    # Create async database connection
    database = Database(TEST_DATABASE_URL)
    await database.connect()
    
    yield database
    
    await database.disconnect()
    
    # Clean up test database file
    db_file = "./test_fastapi.db"
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client"""
    # Override database dependency
    app.dependency_overrides[database] = lambda: test_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(test_db):
    """Create a test user"""
    from ..models import users
    from sqlalchemy import insert
    
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": hash_password("testpassword"),
        "is_active": True,
        "is_superuser": False
    }
    
    query = insert(users).values(**user_data)
    user_id = await test_db.execute(query)
    
    # Return user data with ID
    user_data["id"] = user_id
    return user_data


@pytest_asyncio.fixture
async def test_superuser(test_db):
    """Create a test superuser"""
    from ..models import users
    from sqlalchemy import insert
    
    user_data = {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "hashed_password": hash_password("adminpassword"),
        "is_active": True,
        "is_superuser": True
    }
    
    query = insert(users).values(**user_data)
    user_id = await test_db.execute(query)
    
    # Return user data with ID
    user_data["id"] = user_id
    return user_data


@pytest_asyncio.fixture
async def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    login_data = {
        "username": test_user["username"],
        "password": "testpassword"
    }
    
    response = await client.post("/api/auth/login-json", json=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client, test_superuser):
    """Get authentication headers for admin user"""
    login_data = {
        "username": test_superuser["username"],
        "password": "adminpassword"
    }
    
    response = await client.post("/api/auth/login-json", json=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_product(test_db, test_user):
    """Create a test product"""
    from ..models import products
    from sqlalchemy import insert
    
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 99.99,
        "category": "Electronics",
        "stock_quantity": 10,
        "created_by": test_user["id"],
        "is_active": True
    }
    
    query = insert(products).values(**product_data)
    product_id = await test_db.execute(query)
    
    # Return product data with ID
    product_data["id"] = product_id
    return product_data


@pytest.fixture
def test_file():
    """Create a temporary test file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("This is a test file content")
        f.flush()
        
        yield f.name
        
        # Clean up
        if os.path.exists(f.name):
            os.remove(f.name) 