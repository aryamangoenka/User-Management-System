import uuid
import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from app.main import app
from app.db.connection import get_db
from app.models.models import User
from app.utils.hashing import hash_password
import asyncio


@pytest.mark.anyio
async def test_login_success():
    email = f"user_{uuid.uuid4()}@example.com"
    password = "testpass123"
    hashed_pwd = await asyncio.to_thread(hash_password, password)

    # user into DB
    async for db in get_db():
        user = User(
            first_name="Test",
            last_name="Login",
            email=email,
            role="executive",
            hashed_password=hashed_pwd
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        break

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth_api/login", data={
            "username": email,
            "password": password
        })

    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.anyio
async def test_refresh_token_success():
    email = f"user_{uuid.uuid4()}@example.com"
    password = "refreshpass"
    hashed_pwd = await asyncio.to_thread(hash_password, password)

    # Insert the user into DB
    async for db in get_db():
        user = User(
            first_name="Refresh",
            last_name="User",
            email=email,
            role="executive",
            hashed_password=hashed_pwd
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        break

    # Login and get the access and refresh token
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post("/auth_api/login", data={
            "username": email,
            "password": password
        })

    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    tokens = login_resp.json()

    # Extract refresh token returned by API
    refresh_token = tokens["refresh_token"]
    assert refresh_token is not None

    # Send refresh token to refresh API
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        refresh_resp = await client.post("/auth_api/refresh", json={
            "refresh_token": refresh_token
        })

    # Assert refresh was successful
    assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
    refreshed_data = refresh_resp.json()
    assert "access_token" in refreshed_data


