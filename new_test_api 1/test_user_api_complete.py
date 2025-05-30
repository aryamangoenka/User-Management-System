import pytest
import asyncio
import uuid
from httpx import AsyncClient
from app.main import app
from app.models.models import User
from app.utils.hashing import hash_password
from app.db.connection import get_db
from httpx._transports.asgi import ASGITransport
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta


# Helper to create test user with role and permissions
async def create_test_user_with_permissions(db, email, password, permissions):
    from app.utils.auth_crud import create_role, add_permission_to_role
    from app.models.models import Role

    role_name = "admin"
    result = await db.execute(select(Role).where(Role.role == role_name))
    role = result.scalar_one_or_none()
    if not role:
        role = await create_role(db, role_name=role_name)

    for perm in permissions:
        try:
            await add_permission_to_role(db, role.id, perm)
        except Exception:
            pass

    user = User(
        first_name="Test",
        last_name="User",
        email=email,
        role=role_name,
        hashed_password=await asyncio.to_thread(hash_password, password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# Login helper
async def login_and_get_token(email, password):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/auth_api/login", data={"username": email, "password": password})
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]


# Helper to create basic test user
async def create_basic_user(db, email=None, password="testpass123"):
    if email is None:
        email = f"user_{uuid.uuid4()}@example.com"
    
    user = User(
        first_name="Test",
        last_name="User",
        email=email,
        role="executive",
        hashed_password=await asyncio.to_thread(hash_password, password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.anyio
async def test_get_user_by_id_success():
    """Test successfully getting user by ID"""
    email = f"get_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        target_user = await create_basic_user(db, f"target_{uuid.uuid4()}@example.com")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/users/get_user?user_id={target_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get user by ID failed: {response.text}"
    data = response.json()
    assert data["message"] == "User retrieved"
    assert data["data"]["email"] == target_user.email
    assert data["data"]["first_name"] == target_user.first_name


@pytest.mark.anyio
async def test_get_user_by_email_success():
    """Test successfully getting user by email"""
    email = f"get_user_email_{uuid.uuid4()}@example.com"
    password = "testpass123"
    target_email = f"target_email_{uuid.uuid4()}@example.com"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        target_user = await create_basic_user(db, target_email)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/users/get_user?email={target_email}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get user by email failed: {response.text}"
    data = response.json()
    assert data["message"] == "User retrieved"
    assert data["data"]["email"] == target_email


@pytest.mark.anyio
async def test_get_user_by_name_success():
    """Test successfully getting user by first and last name"""
    email = f"get_user_name_{uuid.uuid4()}@example.com"
    password = "testpass123"
    target_email = f"target_name_{uuid.uuid4()}@example.com"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        target_user = await create_basic_user(db, target_email)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/users/get_user?first_name={target_user.first_name}&last_name={target_user.last_name}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get user by name failed: {response.text}"
    data = response.json()
    assert data["message"] == "User retrieved"
    assert data["data"]["first_name"] == target_user.first_name
    assert data["data"]["last_name"] == target_user.last_name


@pytest.mark.anyio
async def test_get_user_not_found():
    """Test getting non-existent user"""
    email = f"get_user_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        break

    token = await login_and_get_token(email, password)
    fake_user_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/users/get_user?user_id={fake_user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_user_unauthorized():
    """Test getting user without proper permissions"""
    email = f"get_user_unauth_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_user"])  # Wrong permission
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/users/get_user?user_id={uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_update_user_success():
    """Test successfully updating a user"""
    email = f"update_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["update_user"])
        target_user = await create_basic_user(db, f"target_update_{uuid.uuid4()}@example.com")
        break

    token = await login_and_get_token(email, password)

    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "role": "admin"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/users/update_user/{target_user.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Update user failed: {response.text}"
    data = response.json()
    assert data["message"] == "User updated"
    assert data["data"]["first_name"] == "Updated"
    assert data["data"]["last_name"] == "Name"
    assert data["data"]["role"] == "admin"

    # Verify update in database
    async for db in get_db():
        stmt = select(User).where(User.id == target_user.id)
        result = await db.execute(stmt)
        updated_user = result.scalars().first()
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.role == "admin"
        break


@pytest.mark.anyio
async def test_update_user_not_found():
    """Test updating non-existent user"""
    email = f"update_user_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["update_user"])
        break

    token = await login_and_get_token(email, password)
    fake_user_id = str(uuid.uuid4())

    update_data = {
        "first_name": "Updated",
        "last_name": "Name"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/users/update_user/{fake_user_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_user_unauthorized():
    """Test updating user without proper permissions"""
    email = f"update_user_unauth_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])  # Wrong permission
        target_user = await create_basic_user(db)
        break

    token = await login_and_get_token(email, password)

    update_data = {
        "first_name": "Unauthorized",
        "last_name": "Update"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/users/update_user/{target_user.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_delete_user_success():
    """Test successfully deleting a user"""
    email = f"delete_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["delete_user"])
        target_user = await create_basic_user(db, f"target_delete_{uuid.uuid4()}@example.com")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/users/delete_user/{target_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Delete user failed: {response.text}"
    data = response.json()
    assert data["message"] == "User deleted"

    # Verify user was deleted from database
    async for db in get_db():
        stmt = select(User).where(User.id == target_user.id)
        result = await db.execute(stmt)
        deleted_user = result.scalars().first()
        assert deleted_user is None
        break


@pytest.mark.anyio
async def test_delete_user_not_found():
    """Test deleting non-existent user"""
    email = f"delete_user_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["delete_user"])
        break

    token = await login_and_get_token(email, password)
    fake_user_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/users/delete_user/{fake_user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_user_unauthorized():
    """Test deleting user without proper permissions"""
    email = f"delete_user_unauth_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])  # Wrong permission
        target_user = await create_basic_user(db)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/users/delete_user/{target_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_reset_password_success():
    """Test successfully resetting password with valid token"""
    email = f"reset_password_{uuid.uuid4()}@example.com"
    password = "oldpass123"

    async for db in get_db():
        user = await create_basic_user(db, email, password)
        
        # Set reset token and expiry
        user.reset_token = "valid_reset_token_123"
        user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()
        break

    new_password = "newpass456"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/users/reset-password?token=valid_reset_token_123&new_password={new_password}"
        )

    assert response.status_code == 200, f"Reset password failed: {response.text}"
    data = response.json()
    assert data["message"] == "Password reset successful"

    # Verify password was changed and reset token cleared
    async for db in get_db():
        stmt = select(User).where(User.id == user.id)
        result = await db.execute(stmt)
        updated_user = result.scalars().first()
        assert updated_user.reset_token is None
        assert updated_user.reset_token_expiry is None
        # Verify new password works by attempting login
        break

    # Test login with new password
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post("/auth_api/login", data={
            "username": email,
            "password": new_password
        })
    assert login_response.status_code == 200


@pytest.mark.anyio
async def test_reset_password_invalid_token():
    """Test resetting password with invalid token"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/users/reset-password?token=invalid_token&new_password=newpass123"
        )

    assert response.status_code == 400
    assert "Invalid or expired token" in response.json()["detail"]


@pytest.mark.anyio
async def test_reset_password_expired_token():
    """Test resetting password with expired token"""
    email = f"reset_expired_{uuid.uuid4()}@example.com"
    password = "oldpass123"

    async for db in get_db():
        user = await create_basic_user(db, email, password)
        
        # Set expired reset token
        user.reset_token = "expired_reset_token_123"
        user.reset_token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        await db.commit()
        break

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/users/reset-password?token=expired_reset_token_123&new_password=newpass123"
        )

    assert response.status_code == 400
    assert "Invalid or expired token" in response.json()["detail"]


@pytest.mark.anyio
async def test_user_endpoints_require_authentication():
    """Test that user endpoints require authentication"""
    fake_user_id = str(uuid.uuid4())
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test endpoints without authentication
        endpoints = [
            ("GET", f"/users/get_user?user_id={fake_user_id}"),
            ("PUT", f"/users/update_user/{fake_user_id}", {"first_name": "Test"}),
            ("DELETE", f"/users/delete_user/{fake_user_id}"),
        ]
        
        for method, endpoint, *payload in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "PUT":
                response = await client.put(endpoint, json=payload[0] if payload else {})
            elif method == "DELETE":
                response = await client.delete(endpoint)
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"


@pytest.mark.anyio
async def test_user_crud_workflow():
    """Test complete CRUD workflow for user management"""
    email = f"user_crud_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, [
            "create_user", "view_users", "update_user", "delete_user"
        ])
        break

    token = await login_and_get_token(email, password)
    
    # 1. Create user
    new_user_email = f"crud_new_{uuid.uuid4()}@example.com"
    create_data = {
        "first_name": "CRUD",
        "last_name": "Test",
        "email": new_user_email,
        "role": "executive",
        "password": "crudpass123"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create
        create_response = await client.post(
            "/users/create_user",
            json=create_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_response.status_code == 200
        created_user_id = create_response.json()["data"]["id"]

        # 2. Read the created user
        get_response = await client.get(
            f"/users/get_user?user_id={created_user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        retrieved_user = get_response.json()["data"]
        assert retrieved_user["email"] == new_user_email

        # 3. Update the user
        update_data = {
            "first_name": "Updated CRUD",
            "last_name": "Updated Test",
            "role": "admin"
        }
        update_response = await client.put(
            f"/users/update_user/{created_user_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200
        updated_user = update_response.json()["data"]
        assert updated_user["first_name"] == "Updated CRUD"

        # 4. Delete the user
        delete_response = await client.delete(
            f"/users/delete_user/{created_user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_response.status_code == 200

        # 5. Verify user is deleted
        final_get_response = await client.get(
            f"/users/get_user?user_id={created_user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert final_get_response.status_code == 404


@pytest.mark.anyio
async def test_get_user_with_multiple_parameters():
    """Test getting user with multiple search parameters"""
    email = f"multi_param_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        target_user = await create_basic_user(db, f"multi_target_{uuid.uuid4()}@example.com")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/users/get_user?first_name={target_user.first_name}&last_name={target_user.last_name}&email={target_user.email}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get user with multiple params failed: {response.text}"
    data = response.json()
    assert data["data"]["email"] == target_user.email
    assert data["data"]["first_name"] == target_user.first_name
    assert data["data"]["last_name"] == target_user.last_name 