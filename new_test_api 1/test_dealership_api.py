import uuid
import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.models import Dealership, Lenders, LenderDealershipMap
from app.db.connection import get_db

@pytest.mark.anyio
async def test_create_dealership_success():
    name = f"Test Dealer {uuid.uuid4()}"
    transport = ASGITransport(app=app)

    with patch("app.api.dealership_api.verify_token", new=AsyncMock(return_value={"status": "valid"})):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/dealerships/create",
                json={"name": name},
                headers={"Authorization": "Bearer fake-token"}
            )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert "id" in data


@pytest.mark.anyio
async def test_get_dealerships_list():
    name = f"Dealer {uuid.uuid4()}"
    async for db in get_db():
        dealer = Dealership(name=name)
        db.add(dealer)
        await db.commit()
        await db.refresh(dealer)
        break

    with patch("app.api.dealership_api.verify_token", new=AsyncMock(return_value={"status": "valid"})):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/dealerships/list",
                headers={"Authorization": "Bearer fake-token"}
            )

    assert response.status_code == 200
    data = response.json()
    assert any(d["name"] == name for d in data)


@pytest.mark.anyio
async def test_assign_dealership_to_lender_success():
    async for db in get_db():
        dealership = Dealership(id=uuid.uuid4(), name=f"Dealer {uuid.uuid4()}")
        lender = Lenders(id=uuid.uuid4(), lender_name=f"Lender {uuid.uuid4()}", source="manual")

        db.add_all([dealership, lender])
        await db.commit()
        await db.refresh(dealership)
        await db.refresh(lender)
        break

    payload = {
        "lender_id": str(lender.id),
        "dealership_id": str(dealership.id),
        "ratio": "70"
    }

    with patch("app.api.dealership_api.verify_token", new=AsyncMock(return_value={"status": "valid"})):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/dealerships/mapping/assign",
                json=payload,
                headers={"Authorization": "Bearer fake-token"}
            )

    assert response.status_code == 200
    data = response.json()
    assert data["lender_id"] == payload["lender_id"]
    assert data["dealership_id"] == payload["dealership_id"]
    assert data["ratio"] == payload["ratio"]


@pytest.mark.anyio
async def test_get_dealerships_for_lender_success():
    async for db in get_db():
        dealership = Dealership(id=uuid.uuid4(), name=f"Dealer X {uuid.uuid4()}")
        lender = Lenders(id=uuid.uuid4(), lender_name=f"Lender X {uuid.uuid4()}", source="manual")

        db.add_all([dealership, lender])
        await db.commit()
        await db.refresh(dealership)
        await db.refresh(lender)

        mapping = LenderDealershipMap(
            lender_id=lender.id,
            dealership_id=dealership.id,
            ratio="50"
        )
        db.add(mapping)
        await db.commit()
        break

    with patch("app.api.dealership_api.verify_token", new=AsyncMock(return_value={"status": "valid"})):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/dealerships/lender/{lender.id}",
                headers={"Authorization": "Bearer fake-token"}
            )

    assert response.status_code == 200
    data = response.json()
    assert any(item["dealership_id"] == str(dealership.id) for item in data)
