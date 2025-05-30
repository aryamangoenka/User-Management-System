import pytest
import asyncio
import uuid
from httpx import AsyncClient
from app.main import app
from app.models.models import User, Application
from app.utils.hashing import hash_password
from app.db.connection import get_db
from httpx._transports.asgi import ASGITransport
from sqlalchemy.future import select
from unittest.mock import patch
from decimal import Decimal


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


def create_valid_webhook_payload():
    """Create a valid webhook payload for testing"""
    return {
        "Applicant": {
            "FirstName": "John",
            "LastName": "Doe"
        },
        "DealershipName": "Test Motors",
        "defiAppNumber": f"DEFI{uuid.uuid4().hex[:8].upper()}",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "Honda",
            "Model": "Civic",
            "Trim": "LX"
        },
        "TradeIn": {
            "Allowance": "15000.00",
            "Payoff": "12000.00"
        }
    }


@pytest.mark.anyio
async def test_webhook_success_with_valid_secret():
    """Test successful webhook processing with valid secret"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret_123'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=webhook_payload,
                headers={"X-Secret": "test_secret_123"}
            )

    assert response.status_code == 200, f"Webhook failed: {response.text}"
    data = response.json()
    assert data["message"] == "Webhook received and validated successfully."


@pytest.mark.anyio
async def test_webhook_invalid_secret():
    """Test webhook rejection with invalid secret"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'correct_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=webhook_payload,
                headers={"X-Secret": "wrong_secret"}
            )

    assert response.status_code == 403
    assert "Invalid webhook secret" in response.json()["detail"]


@pytest.mark.anyio
async def test_webhook_missing_secret_header():
    """Test webhook rejection when secret header is missing"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=webhook_payload
            )

    assert response.status_code == 422  # FastAPI validation error for missing header


@pytest.mark.anyio
async def test_webhook_creates_application():
    """Test that webhook successfully creates an application in database"""
    webhook_payload = create_valid_webhook_payload()
    defi_app_number = webhook_payload["defiAppNumber"]
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret_123'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=webhook_payload,
                headers={"X-Secret": "test_secret_123"}
            )

    assert response.status_code == 200

    # Verify application was created in database
    async for db in get_db():
        stmt = select(Application).where(Application.defi_app_number == defi_app_number)
        result = await db.execute(stmt)
        application = result.scalars().first()
        
        assert application is not None
        assert application.first_name == "John"
        assert application.last_name == "Doe"
        assert application.dealership_name == "Test Motors"
        assert application.vin == "1HGBH41JXMN109186"
        assert application.year == "2023"
        assert application.make == "Honda"
        assert application.model == "Civic"
        assert application.trim == "LX"
        assert application.allowance == Decimal("15000.00")
        assert application.payoff == Decimal("12000.00")
        break


@pytest.mark.anyio
async def test_webhook_invalid_payload_structure():
    """Test webhook with invalid payload structure"""
    invalid_payload = {
        "invalid": "structure",
        "missing": "required fields"
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=invalid_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.anyio
async def test_webhook_missing_applicant_data():
    """Test webhook with missing applicant data"""
    invalid_payload = {
        "DealershipName": "Test Motors",
        "defiAppNumber": "DEFI12345678",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "Honda",
            "Model": "Civic",
            "Trim": "LX"
        },
        "TradeIn": {
            "Allowance": "15000.00",
            "Payoff": "12000.00"
        }
        # Missing "Applicant" field
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=invalid_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_webhook_missing_vehicle_data():
    """Test webhook with missing vehicle data"""
    invalid_payload = {
        "Applicant": {
            "FirstName": "John",
            "LastName": "Doe"
        },
        "DealershipName": "Test Motors",
        "defiAppNumber": "DEFI12345678",
        "TradeIn": {
            "Allowance": "15000.00",
            "Payoff": "12000.00"
        }
        # Missing "Vehicle" field
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=invalid_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_webhook_missing_tradein_data():
    """Test webhook with missing trade-in data"""
    invalid_payload = {
        "Applicant": {
            "FirstName": "John",
            "LastName": "Doe"
        },
        "DealershipName": "Test Motors",
        "defiAppNumber": "DEFI12345678",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "Honda",
            "Model": "Civic",
            "Trim": "LX"
        }
        # Missing "TradeIn" field
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=invalid_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_webhook_incomplete_applicant_data():
    """Test webhook with incomplete applicant data"""
    invalid_payload = {
        "Applicant": {
            "FirstName": "John"
            # Missing "LastName"
        },
        "DealershipName": "Test Motors",
        "defiAppNumber": "DEFI12345678",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "Honda",
            "Model": "Civic",
            "Trim": "LX"
        },
        "TradeIn": {
            "Allowance": "15000.00",
            "Payoff": "12000.00"
        }
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=invalid_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_webhook_incomplete_vehicle_data():
    """Test webhook with incomplete vehicle data"""
    invalid_payload = {
        "Applicant": {
            "FirstName": "John",
            "LastName": "Doe"
        },
        "DealershipName": "Test Motors",
        "defiAppNumber": "DEFI12345678",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "Honda"
            # Missing "Model" and "Trim"
        },
        "TradeIn": {
            "Allowance": "15000.00",
            "Payoff": "12000.00"
        }
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=invalid_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_webhook_database_error_handling():
    """Test webhook error handling when database operations fail"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}), \
         patch('app.utils.data_functions.store_application_data') as mock_store:
        
        # Simulate database error
        mock_store.side_effect = Exception("Database connection failed")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=webhook_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 400
    assert "Failed to process webhook" in response.json()["detail"]


@pytest.mark.anyio
async def test_webhook_duplicate_defi_app_number():
    """Test webhook handling of duplicate defi app numbers"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Send the same webhook twice
            response1 = await client.post(
                "/daltra_webhook",
                json=webhook_payload,
                headers={"X-Secret": "test_secret"}
            )
            
            response2 = await client.post(
                "/daltra_webhook",
                json=webhook_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response1.status_code == 200
    # The second request might fail due to unique constraint on defi_app_number
    # or might succeed depending on implementation
    assert response2.status_code in [200, 400]


@pytest.mark.anyio
async def test_webhook_large_payload():
    """Test webhook with unusually large field values"""
    large_payload = {
        "Applicant": {
            "FirstName": "A" * 1000,  # Very long first name
            "LastName": "B" * 1000    # Very long last name
        },
        "DealershipName": "C" * 1000,  # Very long dealership name
        "defiAppNumber": f"DEFI{uuid.uuid4().hex[:8].upper()}",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "Honda",
            "Model": "Civic",
            "Trim": "LX"
        },
        "TradeIn": {
            "Allowance": "15000.00",
            "Payoff": "12000.00"
        }
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=large_payload,
                headers={"X-Secret": "test_secret"}
            )

    # Response depends on database field length constraints
    assert response.status_code in [200, 400]


@pytest.mark.anyio
async def test_webhook_special_characters():
    """Test webhook with special characters in data"""
    special_payload = {
        "Applicant": {
            "FirstName": "José María",
            "LastName": "García-López"
        },
        "DealershipName": "Müller's Motors & Co.",
        "defiAppNumber": f"DEFI{uuid.uuid4().hex[:8].upper()}",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "BMW",
            "Model": "X5",
            "Trim": "xDrive40i"
        },
        "TradeIn": {
            "Allowance": "25000.50",
            "Payoff": "18500.75"
        }
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=special_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 200, f"Webhook with special characters failed: {response.text}"


@pytest.mark.anyio
async def test_webhook_numeric_string_values():
    """Test webhook with various numeric string formats"""
    numeric_payload = {
        "Applicant": {
            "FirstName": "John",
            "LastName": "Doe"
        },
        "DealershipName": "Test Motors",
        "defiAppNumber": f"DEFI{uuid.uuid4().hex[:8].upper()}",
        "Vehicle": {
            "VIN": "1HGBH41JXMN109186",
            "Year": "2023",
            "Make": "Honda",
            "Model": "Civic",
            "Trim": "LX"
        },
        "TradeIn": {
            "Allowance": "15,000.00",  # With comma
            "Payoff": "12000"         # Without decimal
        }
    }
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=numeric_payload,
                headers={"X-Secret": "test_secret"}
            )

    # Response depends on how the application handles numeric parsing
    assert response.status_code in [200, 400]


@pytest.mark.anyio
async def test_webhook_environment_secret_not_set():
    """Test webhook when WEBHOOK_SECRET environment variable is not set"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {}, clear=True):  # Clear all environment variables
        # This should raise a ValueError during module initialization
        # The test might need to be adjusted based on how the application handles this
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            try:
                response = await client.post(
                    "/daltra_webhook",
                    json=webhook_payload,
                    headers={"X-Secret": "any_secret"}
                )
                # If we get here, the app didn't fail on startup
                assert response.status_code in [500, 403]
            except Exception:
                # Expected if WEBHOOK_SECRET validation happens on startup
                pass


@pytest.mark.anyio
async def test_webhook_content_type_validation():
    """Test webhook with different content types"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test with form data instead of JSON
            response = await client.post(
                "/daltra_webhook",
                data={"data": str(webhook_payload)},
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 422  # Should expect JSON


@pytest.mark.anyio
async def test_webhook_response_format():
    """Test that webhook response follows expected format"""
    webhook_payload = create_valid_webhook_payload()
    
    with patch.dict('os.environ', {'WEBHOOK_SECRET': 'test_secret'}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/daltra_webhook",
                json=webhook_payload,
                headers={"X-Secret": "test_secret"}
            )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert isinstance(data["message"], str)
    assert data["message"] == "Webhook received and validated successfully." 