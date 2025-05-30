# app/api/tests/test_role_api.py

import uuid
import pytest
import asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy import select
from app.main import app
from app.models.models import User, Role
from app.utils.hashing import hash_password
from app.utils.auth_crud import create_role, add_permission_to_role


async def create_test_user_with_permissions(db, email, password, permissions):
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

    hashed_pwd = await asyncio.to_thread(hash_password, password)
    user = User(
        first_name="Test",
        last_name="User",
        email=email,
        role=role_name,
        hashed_password=hashed_pwd,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, role.id


async def login_and_get_token(email, password):
    transport = ASGITransport(app=app)  
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        response = await client.post(
            "/auth_api/login",
            data={"username": email, "password": password}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]


@pytest.mark.anyio
async def test_create_role(db_session):  
    email = f"user_{uuid.uuid4()}@example.com"
    password = "rolepass123"

    await create_test_user_with_permissions(db_session, email, password, ["create_role"])
    token = await login_and_get_token(email, password)

    role_name = f"sample_role_{uuid.uuid4().hex[:6]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth_api/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role_name": role_name}
        )

    assert response.status_code == 200, f"Role creation failed: {response.text}"


@pytest.mark.anyio
async def test_add_permission_to_role(db_session):  
    email = f"user_{uuid.uuid4()}@example.com"
    password = "permissionpass123"

    user, _ = await create_test_user_with_permissions(db_session, email, password, ["add_permission_to_role"])

    result = await db_session.execute(select(Role).where(Role.role == user.role))
    role = result.scalar_one()
    role_id = role.id

    token = await login_and_get_token(email, password)
    new_permission = "test_permission"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        response = await client.post(
            "/auth_api/role/permission",
            headers={"Authorization": f"Bearer {token}"},
            json={"role_id": str(role_id), "permission": new_permission}
        )

    assert response.status_code == 200, f"Permission addition failed: {response.text}"
    assert f"Permission '{new_permission}' added to role ID {role_id}" in response.json()["message"]
