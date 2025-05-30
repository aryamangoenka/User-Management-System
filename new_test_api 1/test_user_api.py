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


@pytest.mark.anyio
async def test_create_user():
    email = f"admin_{uuid.uuid4()}@example.com"
    password = "adminpass"
    new_user_email = f"new_{uuid.uuid4()}@example.com"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_user"])
        break

    token = await login_and_get_token(email, password)

    payload = {
        "first_name": "New",
        "last_name": "User",
        "email": new_user_email,
        "role": "executive",
        "password": "newpass123"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/users/create_user", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200, res.text
    assert res.json()["message"] == "User created"


@pytest.mark.anyio
async def test_get_all_users():
    email = f"user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, permissions=["view_users"])
        break

    access_token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/users/get_all_users/",
            headers={"Authorization": f"Bearer {access_token}"}
        )

    assert response.status_code == 200, f"Get all users failed: {response.text}"
    assert "users" in response.json()["data"]



@pytest.mark.anyio
async def test_forgot_password():
    email = f"forgot_{uuid.uuid4()}@example.com"
    password = "forgotpass"

    async for db in get_db():
        user = User(
            first_name="Forgot",
            last_name="User",
            email=email,
            role="executive",
            hashed_password=await asyncio.to_thread(hash_password, password)
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        break

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/users/forgot-password", params={"email": email})

    assert res.status_code == 200
    assert "reset_token" in res.json()["data"]
