import pytest
import asyncio
import uuid
from httpx import AsyncClient
from app.main import app
from app.models.models import User, Lenders
from app.utils.hashing import hash_password
from app.db.connection import get_db
from httpx._transports.asgi import ASGITransport
from sqlalchemy.future import select
from datetime import datetime, timezone


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


# Helper to create test lender
async def create_test_lender(db, lender_name=None, source="dealertrack"):
    if lender_name is None:
        lender_name = f"Test Lender {uuid.uuid4().hex[:8]}"
    
    lender = Lenders(
        lender_name=lender_name,
        source=source,
        status="active",
        config={
            "field_mappings": {
                "first_name": "applicant_first_name",
                "last_name": "applicant_last_name",
                "vin": "vehicle_vin"
            },
            "rules": {
                "min_amount": 5000,
                "max_amount": 100000
            }
        }
    )
    db.add(lender)
    await db.commit()
    await db.refresh(lender)
    return lender


@pytest.mark.anyio
async def test_create_lender_success():
    """Test successfully creating a new lender"""
    email = f"lender_create_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_user"])
        break

    token = await login_and_get_token(email, password)

    lender_data = {
        "lender_name": f"New Lender {uuid.uuid4().hex[:8]}",
        "source": "dealertrack",
        "config": {
            "field_mappings": {
                "first_name": "applicant_first_name",
                "last_name": "applicant_last_name"
            },
            "processing_rules": {
                "min_amount": 1000,
                "max_amount": 50000
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/lenders/",
            json=lender_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 201, f"Create lender failed: {response.text}"
    data = response.json()
    assert data["lender_name"] == lender_data["lender_name"]
    assert data["source"] == lender_data["source"]
    assert data["status"] == "active"
    assert data["config"] == lender_data["config"]
    assert "id" in data


@pytest.mark.anyio
async def test_create_lender_unauthorized():
    """Test creating lender without proper permissions"""
    email = f"lender_unauth_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])  # Wrong permission
        break

    token = await login_and_get_token(email, password)

    lender_data = {
        "lender_name": "Unauthorized Lender",
        "source": "dealertrack"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/lenders/",
            json=lender_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_lender_missing_fields():
    """Test creating lender with missing required fields"""
    email = f"lender_missing_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_user"])
        break

    token = await login_and_get_token(email, password)

    # Missing 'source' field
    lender_data = {
        "lender_name": "Incomplete Lender"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/lenders/",
            json=lender_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.anyio
async def test_update_lender_success():
    """Test successfully updating a lender"""
    email = f"lender_update_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["update_user"])
        lender = await create_test_lender(db)
        break

    token = await login_and_get_token(email, password)

    update_data = {
        "lender_name": "Updated Lender Name",
        "config": {
            "field_mappings": {
                "first_name": "updated_first_name",
                "last_name": "updated_last_name",
                "email": "contact_email"
            },
            "processing_rules": {
                "min_amount": 2000,
                "max_amount": 75000
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/lenders/{lender.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Update lender failed: {response.text}"
    data = response.json()
    assert data["lender_name"] == update_data["lender_name"]
    assert data["config"] == update_data["config"]


@pytest.mark.anyio
async def test_update_lender_not_found():
    """Test updating non-existent lender"""
    email = f"lender_update_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["update_user"])
        break

    token = await login_and_get_token(email, password)
    fake_uuid = str(uuid.uuid4())

    update_data = {
        "lender_name": "Updated Lender"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/lenders/{fake_uuid}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_lender_by_id_success():
    """Test successfully retrieving a lender by ID"""
    email = f"lender_get_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        lender = await create_test_lender(db, "Specific Test Lender")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/lenders/id/{lender.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get lender failed: {response.text}"
    data = response.json()
    assert data["id"] == str(lender.id)
    assert data["lender_name"] == "Specific Test Lender"
    assert data["source"] == "dealertrack"
    assert data["status"] == "active"


@pytest.mark.anyio
async def test_get_lender_by_id_not_found():
    """Test getting non-existent lender by ID"""
    email = f"lender_get_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        break

    token = await login_and_get_token(email, password)
    fake_uuid = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/lenders/id/{fake_uuid}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_all_lenders_success():
    """Test successfully retrieving all lenders"""
    email = f"lender_getall_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        
        # Create multiple test lenders
        lender1 = await create_test_lender(db, "Lender One", "dealertrack")
        lender2 = await create_test_lender(db, "Lender Two", "routeone")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/lenders/",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get all lenders failed: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # At least our two test lenders

    # Check that our test lenders are in the response
    lender_names = [lender["lender_name"] for lender in data]
    assert "Lender One" in lender_names
    assert "Lender Two" in lender_names


@pytest.mark.anyio
async def test_get_all_lenders_empty():
    """Test getting all lenders when none exist"""
    email = f"lender_empty_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        
        # Clean up any existing lenders for this test
        result = await db.execute(select(Lenders))
        existing_lenders = result.scalars().all()
        for lender in existing_lenders:
            await db.delete(lender)
        await db.commit()
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/lenders/",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get all lenders failed: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.anyio
async def test_get_lender_attributes_success():
    """Test successfully retrieving lender attributes"""
    email = f"lender_attrs_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/lenders/attributes",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get lender attributes failed: {response.text}"
    data = response.json()
    assert "attributes" in data
    assert isinstance(data["attributes"], list)


@pytest.mark.anyio
async def test_lender_endpoints_require_authentication():
    """Test that all lender endpoints require authentication"""
    fake_uuid = str(uuid.uuid4())
    lender_data = {"lender_name": "Test", "source": "dealertrack"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test all endpoints without authentication
        endpoints_and_methods = [
            ("POST", "/lenders/", lender_data),
            ("PUT", f"/lenders/{fake_uuid}", lender_data),
            ("GET", f"/lenders/id/{fake_uuid}", None),
            ("GET", "/lenders/", None),
            ("GET", "/lenders/attributes", None),
        ]
        
        for method, endpoint, payload in endpoints_and_methods:
            if method == "POST":
                response = await client.post(endpoint, json=payload)
            elif method == "PUT":
                response = await client.put(endpoint, json=payload)
            elif method == "GET":
                response = await client.get(endpoint)
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"


@pytest.mark.anyio
async def test_lender_crud_workflow():
    """Test complete CRUD workflow for lenders"""
    email = f"lender_crud_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_user", "update_user", "view_users"])
        break

    token = await login_and_get_token(email, password)

    # 1. Create a lender
    lender_data = {
        "lender_name": "CRUD Test Lender",
        "source": "dealertrack",
        "config": {
            "initial": "config"
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create
        create_response = await client.post(
            "/lenders/",
            json=lender_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_response.status_code == 201
        created_lender = create_response.json()
        lender_id = created_lender["id"]

        # 2. Read the created lender
        get_response = await client.get(
            f"/lenders/id/{lender_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        retrieved_lender = get_response.json()
        assert retrieved_lender["lender_name"] == "CRUD Test Lender"

        # 3. Update the lender
        update_data = {
            "lender_name": "Updated CRUD Lender",
            "config": {
                "updated": "config"
            }
        }
        update_response = await client.put(
            f"/lenders/{lender_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200
        updated_lender = update_response.json()
        assert updated_lender["lender_name"] == "Updated CRUD Lender"

        # 4. Verify the update by reading again
        final_get_response = await client.get(
            f"/lenders/id/{lender_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert final_get_response.status_code == 200
        final_lender = final_get_response.json()
        assert final_lender["lender_name"] == "Updated CRUD Lender"
        assert final_lender["config"]["updated"] == "config"


@pytest.mark.anyio
async def test_lender_config_validation():
    """Test that lender config accepts various JSON structures"""
    email = f"lender_config_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["create_user"])
        break

    token = await login_and_get_token(email, password)

    # Test with complex config structure
    complex_config = {
        "field_mappings": {
            "personal_info": {
                "first_name": "applicant_first_name",
                "last_name": "applicant_last_name",
                "email": "contact_email"
            },
            "vehicle_info": {
                "vin": "vehicle_identification_number",
                "year": "model_year",
                "make": "manufacturer",
                "model": "vehicle_model"
            }
        },
        "business_rules": {
            "minimum_credit_score": 600,
            "maximum_loan_amount": 100000,
            "allowed_vehicle_years": [2018, 2019, 2020, 2021, 2022, 2023, 2024]
        },
        "processing_options": {
            "auto_approve_threshold": 25000,
            "require_manual_review": True,
            "notification_settings": {
                "email_notifications": True,
                "sms_notifications": False
            }
        }
    }

    lender_data = {
        "lender_name": "Complex Config Lender",
        "source": "routeone",
        "config": complex_config
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/lenders/",
            json=lender_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 201, f"Create lender with complex config failed: {response.text}"
    data = response.json()
    assert data["config"] == complex_config 