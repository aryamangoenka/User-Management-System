import pytest
import asyncio
import uuid
from httpx import AsyncClient
from app.main import app
from app.models.models import User, Role
from app.utils.hashing import hash_password
from app.db.connection import get_db
from httpx._transports.asgi import ASGITransport
from sqlalchemy.future import select


# Helper to create test user with role and permissions
async def create_test_user_with_permissions(db, email, password, permissions):
    from app.utils.auth_crud import create_role, add_permission_to_role

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


@pytest.mark.anyio
async def test_create_role_success():
    """Test successfully creating a new role"""
    email = f"role_create_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_role"])
        break

    token = await login_and_get_token(email, password)
    role_name = f"test_role_{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth_api/role",
            json={"role_name": role_name},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Create role failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert role_name in data["message"]

    # Verify role was created in database
    async for db in get_db():
        stmt = select(Role).where(Role.role == role_name)
        result = await db.execute(stmt)
        created_role = result.scalars().first()
        assert created_role is not None
        assert created_role.role == role_name
        break


@pytest.mark.anyio
async def test_create_role_unauthorized():
    """Test creating role without proper permissions"""
    email = f"role_unauth_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])  # Wrong permission
        break

    token = await login_and_get_token(email, password)
    role_name = f"unauthorized_role_{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth_api/role",
            json={"role_name": role_name},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_role_duplicate():
    """Test creating role with duplicate name"""
    email = f"role_duplicate_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_role"])
        break

    token = await login_and_get_token(email, password)
    role_name = f"duplicate_role_{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create role first time
        response1 = await client.post(
            "/auth_api/role",
            json={"role_name": role_name},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response1.status_code == 200

        # Try to create same role again
        response2 = await client.post(
            "/auth_api/role",
            json={"role_name": role_name},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response2.status_code == 400


@pytest.mark.anyio
async def test_update_role_success():
    """Test successfully updating a role"""
    email = f"role_update_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["update_role"])
        
        # Create a role to update
        from app.utils.auth_crud import create_role
        role = await create_role(db, role_name=f"update_test_{uuid.uuid4().hex[:8]}")
        break

    token = await login_and_get_token(email, password)
    new_role_name = f"updated_role_{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            "/auth_api/role",
            json={"role_id": str(role.id), "new_role_name": new_role_name},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Update role failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert new_role_name in data["message"]

    # Verify role was updated in database
    async for db in get_db():
        stmt = select(Role).where(Role.id == role.id)
        result = await db.execute(stmt)
        updated_role = result.scalars().first()
        assert updated_role.role == new_role_name
        break


@pytest.mark.anyio
async def test_update_role_not_found():
    """Test updating non-existent role"""
    email = f"role_update_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["update_role"])
        break

    token = await login_and_get_token(email, password)
    fake_role_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            "/auth_api/role",
            json={"role_id": fake_role_id, "new_role_name": "nonexistent"},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_role_success():
    """Test successfully deleting a role"""
    email = f"role_delete_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["delete_role"])
        
        # Create a role to delete
        from app.utils.auth_crud import create_role
        role = await create_role(db, role_name=f"delete_test_{uuid.uuid4().hex[:8]}")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/auth_api/role",
            json={"role_name": role.role},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Delete role failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert role.role in data["message"]

    # Verify role was deleted from database
    async for db in get_db():
        stmt = select(Role).where(Role.id == role.id)
        result = await db.execute(stmt)
        deleted_role = result.scalars().first()
        assert deleted_role is None
        break


@pytest.mark.anyio
async def test_delete_role_not_found():
    """Test deleting non-existent role"""
    email = f"role_delete_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["delete_role"])
        break

    token = await login_and_get_token(email, password)
    fake_role_name = f"nonexistent_role_{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/auth_api/role",
            json={"role_name": fake_role_name},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_add_permission_to_role_success():
    """Test successfully adding permission to role"""
    email = f"perm_add_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["add_permission_to_role"])
        
        # Create a role to add permission to
        from app.utils.auth_crud import create_role
        role = await create_role(db, role_name=f"perm_test_{uuid.uuid4().hex[:8]}")
        break

    token = await login_and_get_token(email, password)
    permission = "test_permission"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth_api/role/permission",
            json={"role_id": str(role.id), "permission": permission},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Add permission failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert permission in data["message"]


@pytest.mark.anyio
async def test_add_permission_to_role_invalid_role():
    """Test adding permission to non-existent role"""
    email = f"perm_add_invalid_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["add_permission_to_role"])
        break

    token = await login_and_get_token(email, password)
    fake_role_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth_api/role/permission",
            json={"role_id": fake_role_id, "permission": "test_permission"},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_permission_from_role_success():
    """Test successfully deleting permission from role"""
    email = f"perm_delete_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["delete_permission_from_role"])
        
        # Create a role and add permission to it
        from app.utils.auth_crud import create_role, add_permission_to_role
        role = await create_role(db, role_name=f"perm_delete_test_{uuid.uuid4().hex[:8]}")
        permission = "delete_test_permission"
        await add_permission_to_role(db, role.id, permission)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/auth_api/role/permission",
            json={"role_id": str(role.id), "permission": permission},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Delete permission failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert permission in data["message"]


@pytest.mark.anyio
async def test_delete_permission_from_role_not_found():
    """Test deleting non-existent permission from role"""
    email = f"perm_delete_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["delete_permission_from_role"])
        
        # Create a role without the permission
        from app.utils.auth_crud import create_role
        role = await create_role(db, role_name=f"perm_delete_notfound_{uuid.uuid4().hex[:8]}")
        break

    token = await login_and_get_token(email, password)
    nonexistent_permission = "nonexistent_permission"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/auth_api/role/permission",
            json={"role_id": str(role.id), "permission": nonexistent_permission},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_role_management_requires_authentication():
    """Test that all role management endpoints require authentication"""
    fake_role_id = str(uuid.uuid4())
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test all endpoints without authentication
        endpoints = [
            ("POST", "/auth_api/role", {"role_name": "test"}),
            ("PUT", "/auth_api/role", {"role_id": fake_role_id, "new_role_name": "test"}),
            ("DELETE", "/auth_api/role", {"role_name": "test"}),
            ("POST", "/auth_api/role/permission", {"role_id": fake_role_id, "permission": "test"}),
            ("DELETE", "/auth_api/role/permission", {"role_id": fake_role_id, "permission": "test"}),
        ]
        
        for method, endpoint, payload in endpoints:
            if method == "POST":
                response = await client.post(endpoint, json=payload)
            elif method == "PUT":
                response = await client.put(endpoint, json=payload)
            elif method == "DELETE":
                response = await client.delete(endpoint, json=payload)
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"


@pytest.mark.anyio
async def test_role_crud_workflow():
    """Test complete CRUD workflow for role management"""
    email = f"role_crud_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, [
            "create_role", "update_role", "delete_role", "add_permission_to_role", "delete_permission_from_role"
        ])
        break

    token = await login_and_get_token(email, password)
    role_name = f"crud_test_role_{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create role
        create_response = await client.post(
            "/auth_api/role",
            json={"role_name": role_name},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_response.status_code == 200

        # Get the created role ID
        async for db in get_db():
            stmt = select(Role).where(Role.role == role_name)
            result = await db.execute(stmt)
            created_role = result.scalars().first()
            role_id = str(created_role.id)
            break

        # 2. Add permission to role
        perm_response = await client.post(
            "/auth_api/role/permission",
            json={"role_id": role_id, "permission": "test_permission"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert perm_response.status_code == 200

        # 3. Update role name
        updated_role_name = f"updated_{role_name}"
        update_response = await client.put(
            "/auth_api/role",
            json={"role_id": role_id, "new_role_name": updated_role_name},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200

        # 4. Remove permission from role
        del_perm_response = await client.delete(
            "/auth_api/role/permission",
            json={"role_id": role_id, "permission": "test_permission"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert del_perm_response.status_code == 200

        # 5. Delete role
        delete_response = await client.delete(
            "/auth_api/role",
            json={"role_name": updated_role_name},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_response.status_code == 200

        # 6. Verify role is deleted
        async for db in get_db():
            stmt = select(Role).where(Role.id == created_role.id)
            result = await db.execute(stmt)
            deleted_role = result.scalars().first()
            assert deleted_role is None
            break 