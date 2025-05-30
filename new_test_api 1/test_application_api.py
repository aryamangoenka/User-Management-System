import pytest
import asyncio
import uuid
from decimal import Decimal
from httpx import AsyncClient
from app.main import app
from app.models.models import User, Application, PdfLog, NormalisedData
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


# Helper to create test application
async def create_test_application(db):
    application = Application(
        defi_app_number=f"DEFI{uuid.uuid4().hex[:8].upper()}",
        first_name="John",
        last_name="Doe",
        dealership_name="Test Dealership",
        vin="1HGBH41JXMN109186",
        year="2023",
        make="Honda",
        model="Civic",
        trim="LX",
        allowance=Decimal("15000.00"),
        payoff=Decimal("12000.00"),
        status="pending"
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


# Helper to create test PDF log
async def create_test_pdf_log(db, application_id):
    pdf_log = PdfLog(
        pdf_name="test_document.pdf",
        status="completed",
        reason=None,
        application_id=application_id,
        source="dealertrack",
        lender_name="Test Lender"
    )
    db.add(pdf_log)
    await db.commit()
    await db.refresh(pdf_log)
    return pdf_log


# Helper to create normalized data
async def create_test_normalized_data(db, application_id, pdf_log_id):
    normalized_data = NormalisedData(
        defi_app_number="DEFI12345",
        application_id=application_id,
        pdf_log_id=pdf_log_id,
        first_name="John",
        last_name="Doe",
        dealership_name="Test Dealership",
        vin="1HGBH41JXMN109186",
        year="2023",
        make="Honda",
        model="Civic",
        trim="LX",
        gap=500.0,
        svc_contract=1200.0,
        external_backend=300.0,
        amount_financed=25000.0,
        cash_down=5000.0,
        term=60.0,
        buy_rate=4.5,
        apr=5.2,
        bank_fee=500.0,
        discount_percent=2.0,
        flat=100.0,
        rebate=1000.0,
        net_trade=3000.0,
        split_percent=50.0,
        reserve_method="percentage"
    )
    db.add(normalized_data)
    await db.commit()
    await db.refresh(normalized_data)
    return normalized_data


@pytest.mark.anyio
async def test_get_applications_success():
    """Test successfully retrieving all applications"""
    email = f"app_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        # Create user with permissions
        await create_test_user_with_permissions(db, email, password, ["view_applications"])
        
        # Create test application
        await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/applications/get_applications",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get applications failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert "applications" in data
    assert isinstance(data["applications"], dict)


@pytest.mark.anyio
async def test_get_applications_unauthorized():
    """Test getting applications without proper authentication"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/applications/get_applications")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_application_details_success():
    """Test successfully retrieving specific application details"""
    email = f"app_detail_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        # Create user with permissions
        await create_test_user_with_permissions(db, email, password, ["view_applications"])
        
        # Create test application
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/applications/{application.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get application details failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Application retrieved successfully."
    assert "data" in data
    assert data["data"]["id"] == str(application.id)
    assert data["data"]["first_name"] == "John"
    assert data["data"]["last_name"] == "Doe"


@pytest.mark.anyio
async def test_get_application_details_not_found():
    """Test getting details for non-existent application"""
    email = f"app_notfound_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_applications"])
        break

    token = await login_and_get_token(email, password)
    fake_uuid = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/applications/{fake_uuid}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "Application not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_application_success():
    """Test successfully deleting an application"""
    email = f"app_delete_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        # Create user with permissions
        await create_test_user_with_permissions(db, email, password, ["delete_applications"])
        
        # Create test application
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/applications/{application.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Delete application failed: {response.text}"
    data = response.json()
    assert data["message"] == "Application deleted successfully."

    # Verify application is deleted
    async for db in get_db():
        stmt = select(Application).where(Application.id == application.id)
        result = await db.execute(stmt)
        deleted_app = result.scalars().first()
        assert deleted_app is None
        break


@pytest.mark.anyio
async def test_delete_application_not_found():
    """Test deleting non-existent application"""
    email = f"app_delete_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["delete_applications"])
        break

    token = await login_and_get_token(email, password)
    fake_uuid = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/applications/{fake_uuid}",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "Application not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_pdf_status_log_success():
    """Test successfully retrieving PDF status logs for an application"""
    email = f"app_logs_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        # Create user with permissions
        await create_test_user_with_permissions(db, email, password, ["view_applications"])
        
        # Create test application and PDF log
        application = await create_test_application(db)
        pdf_log = await create_test_pdf_log(db, application.id)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/applications/{application.id}/application_logs",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get PDF logs failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert data["application_id"] == str(application.id)
    assert "pdf_status" in data
    assert len(data["pdf_status"]) > 0
    assert data["pdf_status"][0]["pdf_name"] == "test_document.pdf"
    assert data["pdf_status"][0]["status"] == "completed"


@pytest.mark.anyio
async def test_get_pdf_status_log_no_logs():
    """Test getting PDF logs for application with no logs"""
    email = f"app_nologs_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        # Create user with permissions
        await create_test_user_with_permissions(db, email, password, ["view_applications"])
        
        # Create test application but no PDF logs
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/applications/{application.id}/application_logs",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "No PDF logs found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_normalized_data_success():
    """Test successfully retrieving normalized data for a PDF log"""
    email = f"normalized_user_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        # Create user with permissions
        await create_test_user_with_permissions(db, email, password, ["view_applications"])
        
        # Create test data
        application = await create_test_application(db)
        pdf_log = await create_test_pdf_log(db, application.id)
        normalized_data = await create_test_normalized_data(db, application.id, pdf_log.id)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/applications/{pdf_log.id}/get_normalized_data",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Get normalized data failed: {response.text}"
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["vin"] == "1HGBH41JXMN109186"
    assert data["amount_financed"] == 25000.0
    assert data["apr"] == 5.2


@pytest.mark.anyio
async def test_get_normalized_data_not_found():
    """Test getting normalized data for non-existent PDF log"""
    email = f"normalized_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_applications"])
        break

    token = await login_and_get_token(email, password)
    fake_uuid = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/applications/{fake_uuid}/get_normalized_data",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_application_endpoints_require_authentication():
    """Test that all application endpoints require authentication"""
    fake_uuid = str(uuid.uuid4())
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test all endpoints without authentication
        endpoints = [
            ("GET", "/applications/get_applications"),
            ("GET", f"/applications/{fake_uuid}"),
            ("DELETE", f"/applications/{fake_uuid}"),
            ("GET", f"/applications/{fake_uuid}/application_logs"),
            ("GET", f"/applications/{fake_uuid}/get_normalized_data"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "DELETE":
                response = await client.delete(endpoint)
            
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication" 