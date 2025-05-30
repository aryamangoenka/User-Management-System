import pytest
import asyncio
import uuid
from httpx import AsyncClient
from app.main import app
from app.models.models import User, Dealership, Lenders, LenderDealershipMap
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


# Helper to create test dealership
async def create_test_dealership(db, name=None):
    if name is None:
        name = f"Test Dealership {uuid.uuid4().hex[:8]}"
    
    dealership = Dealership(
        id=uuid.uuid4(),
        name=name
    )
    db.add(dealership)
    await db.commit()
    await db.refresh(dealership)
    return dealership


# Helper to create test lender
async def create_test_lender(db, name=None, source="dealertrack"):
    if name is None:
        name = f"Test Lender {uuid.uuid4().hex[:8]}"
    
    lender = Lenders(
        id=uuid.uuid4(),
        lender_name=name,
        source=source,
        status="active"
    )
    db.add(lender)
    await db.commit()
    await db.refresh(lender)
    return lender


# Helper to create dealership-lender mapping
async def create_test_mapping(db, lender_id, dealership_id, ratio="50"):
    mapping = LenderDealershipMap(
        lender_id=lender_id,
        dealership_id=dealership_id,
        ratio=ratio
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


@pytest.mark.anyio
async def test_unassign_dealership_from_lender_success():
    """Test successfully unassigning dealership from lender"""
    email = f"unassign_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        
        # Create test data
        lender = await create_test_lender(db)
        dealership = await create_test_dealership(db)
        mapping = await create_test_mapping(db, lender.id, dealership.id, "75")
        break

    token = await login_and_get_token(email, password)

    unassign_data = {
        "lender_id": str(lender.id),
        "dealership_id": str(dealership.id)
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/dealerships/mapping/unassign",
            json=unassign_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Unassign dealership failed: {response.text}"
    data = response.json()
    assert data["message"] == "Dealership successfully unassigned from lender"

    # Verify mapping was deleted from database
    async for db in get_db():
        stmt = select(LenderDealershipMap).where(
            LenderDealershipMap.lender_id == lender.id,
            LenderDealershipMap.dealership_id == dealership.id
        )
        result = await db.execute(stmt)
        deleted_mapping = result.scalars().first()
        assert deleted_mapping is None
        break


@pytest.mark.anyio
async def test_unassign_dealership_not_found():
    """Test unassigning non-existent dealership mapping"""
    email = f"unassign_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        
        # Create lender and dealership but no mapping
        lender = await create_test_lender(db)
        dealership = await create_test_dealership(db)
        break

    token = await login_and_get_token(email, password)

    unassign_data = {
        "lender_id": str(lender.id),
        "dealership_id": str(dealership.id)
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/dealerships/mapping/unassign",
            json=unassign_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "Lender-dealership mapping not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_unassign_dealership_invalid_lender():
    """Test unassigning with invalid lender ID"""
    email = f"unassign_invalid_lender_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        dealership = await create_test_dealership(db)
        break

    token = await login_and_get_token(email, password)
    fake_lender_id = str(uuid.uuid4())

    unassign_data = {
        "lender_id": fake_lender_id,
        "dealership_id": str(dealership.id)
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/dealerships/mapping/unassign",
            json=unassign_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "Lender not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_unassign_dealership_invalid_dealership():
    """Test unassigning with invalid dealership ID"""
    email = f"unassign_invalid_dealership_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        lender = await create_test_lender(db)
        break

    token = await login_and_get_token(email, password)
    fake_dealership_id = str(uuid.uuid4())

    unassign_data = {
        "lender_id": str(lender.id),
        "dealership_id": fake_dealership_id
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/dealerships/mapping/unassign",
            json=unassign_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "Dealership not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_lender_dealership_mapping_success():
    """Test successfully updating lender-dealership mapping ratio"""
    email = f"update_mapping_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        
        # Create test data
        lender = await create_test_lender(db)
        dealership = await create_test_dealership(db)
        mapping = await create_test_mapping(db, lender.id, dealership.id, "60")
        break

    token = await login_and_get_token(email, password)
    new_ratio = "85"

    update_data = {
        "ratio": new_ratio
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/dealerships/mapping/edit?lender_id={lender.id}&dealership_id={dealership.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200, f"Update mapping failed: {response.text}"
    data = response.json()
    assert data["lender_id"] == str(lender.id)
    assert data["dealership_id"] == str(dealership.id)
    assert data["ratio"] == new_ratio

    # Verify update in database
    async for db in get_db():
        stmt = select(LenderDealershipMap).where(
            LenderDealershipMap.lender_id == lender.id,
            LenderDealershipMap.dealership_id == dealership.id
        )
        result = await db.execute(stmt)
        updated_mapping = result.scalars().first()
        assert updated_mapping.ratio == new_ratio
        break


@pytest.mark.anyio
async def test_update_mapping_not_found():
    """Test updating non-existent lender-dealership mapping"""
    email = f"update_mapping_notfound_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        
        # Create lender and dealership but no mapping
        lender = await create_test_lender(db)
        dealership = await create_test_dealership(db)
        break

    token = await login_and_get_token(email, password)

    update_data = {
        "ratio": "90"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/dealerships/mapping/edit?lender_id={lender.id}&dealership_id={dealership.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404
    assert "Lender-dealership mapping not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_mapping_invalid_lender():
    """Test updating mapping with invalid lender ID"""
    email = f"update_mapping_invalid_lender_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        dealership = await create_test_dealership(db)
        break

    token = await login_and_get_token(email, password)
    fake_lender_id = str(uuid.uuid4())

    update_data = {
        "ratio": "90"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/dealerships/mapping/edit?lender_id={fake_lender_id}&dealership_id={dealership.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_mapping_invalid_dealership():
    """Test updating mapping with invalid dealership ID"""
    email = f"update_mapping_invalid_dealership_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        lender = await create_test_lender(db)
        break

    token = await login_and_get_token(email, password)
    fake_dealership_id = str(uuid.uuid4())

    update_data = {
        "ratio": "90"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/dealerships/mapping/edit?lender_id={lender.id}&dealership_id={fake_dealership_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_mapping_invalid_ratio():
    """Test updating mapping with invalid ratio values"""
    email = f"update_mapping_invalid_ratio_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        
        # Create test data
        lender = await create_test_lender(db)
        dealership = await create_test_dealership(db)
        mapping = await create_test_mapping(db, lender.id, dealership.id, "50")
        break

    token = await login_and_get_token(email, password)

    # Test with various invalid ratio values
    invalid_ratios = ["", "abc", "-10", "150", "0"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for invalid_ratio in invalid_ratios:
            update_data = {
                "ratio": invalid_ratio
            }

            response = await client.put(
                f"/dealerships/mapping/edit?lender_id={lender.id}&dealership_id={dealership.id}",
                json=update_data,
                headers={"Authorization": f"Bearer {token}"}
            )

            # The response might be 422 (validation error) or 400 depending on implementation
            assert response.status_code in [400, 422], f"Invalid ratio {invalid_ratio} should be rejected"


@pytest.mark.anyio
async def test_dealership_mapping_endpoints_require_authentication():
    """Test that dealership mapping endpoints require authentication"""
    fake_lender_id = str(uuid.uuid4())
    fake_dealership_id = str(uuid.uuid4())
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test unassign endpoint without authentication
        unassign_response = await client.delete(
            "/dealerships/mapping/unassign",
            json={"lender_id": fake_lender_id, "dealership_id": fake_dealership_id}
        )
        assert unassign_response.status_code == 401

        # Test update mapping endpoint without authentication
        update_response = await client.put(
            f"/dealerships/mapping/edit?lender_id={fake_lender_id}&dealership_id={fake_dealership_id}",
            json={"ratio": "80"}
        )
        assert update_response.status_code == 401


@pytest.mark.anyio
async def test_dealership_mapping_unauthorized_access():
    """Test dealership mapping endpoints without proper permissions"""
    email = f"mapping_unauth_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["view_users"])  # Wrong permission
        
        lender = await create_test_lender(db)
        dealership = await create_test_dealership(db)
        mapping = await create_test_mapping(db, lender.id, dealership.id)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test unassign without proper permission
        unassign_response = await client.delete(
            "/dealerships/mapping/unassign",
            json={"lender_id": str(lender.id), "dealership_id": str(dealership.id)},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert unassign_response.status_code == 401

        # Test update without proper permission
        update_response = await client.put(
            f"/dealerships/mapping/edit?lender_id={lender.id}&dealership_id={dealership.id}",
            json={"ratio": "80"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 401


@pytest.mark.anyio
async def test_dealership_mapping_workflow():
    """Test complete dealership mapping workflow"""
    email = f"mapping_workflow_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        
        # Create test data
        lender = await create_test_lender(db, "Workflow Lender")
        dealership = await create_test_dealership(db, "Workflow Dealership")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Assign dealership to lender
        assign_data = {
            "lender_id": str(lender.id),
            "dealership_id": str(dealership.id),
            "ratio": "60"
        }
        assign_response = await client.post(
            "/dealerships/mapping/assign",
            json=assign_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert assign_response.status_code == 200

        # 2. Update the mapping ratio
        update_data = {
            "ratio": "75"
        }
        update_response = await client.put(
            f"/dealerships/mapping/edit?lender_id={lender.id}&dealership_id={dealership.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["ratio"] == "75"

        # 3. Verify the mapping exists and has correct ratio
        get_response = await client.get(
            f"/dealerships/lender/{lender.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        mappings = get_response.json()
        assert len(mappings) == 1
        assert mappings[0]["ratio"] == "75"

        # 4. Unassign the dealership from lender
        unassign_data = {
            "lender_id": str(lender.id),
            "dealership_id": str(dealership.id)
        }
        unassign_response = await client.delete(
            "/dealerships/mapping/unassign",
            json=unassign_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert unassign_response.status_code == 200

        # 5. Verify the mapping is removed
        final_get_response = await client.get(
            f"/dealerships/lender/{lender.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert final_get_response.status_code == 200
        final_mappings = final_get_response.json()
        assert len(final_mappings) == 0


@pytest.mark.anyio
async def test_multiple_dealership_mappings():
    """Test managing multiple dealership mappings for one lender"""
    email = f"multi_mapping_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["manage_dealerships"])
        
        # Create test data
        lender = await create_test_lender(db, "Multi Lender")
        dealership1 = await create_test_dealership(db, "Dealership One")
        dealership2 = await create_test_dealership(db, "Dealership Two")
        dealership3 = await create_test_dealership(db, "Dealership Three")
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Assign multiple dealerships to the same lender
        dealerships = [
            (dealership1, "30"),
            (dealership2, "40"),
            (dealership3, "30")
        ]

        for dealership, ratio in dealerships:
            assign_data = {
                "lender_id": str(lender.id),
                "dealership_id": str(dealership.id),
                "ratio": ratio
            }
            assign_response = await client.post(
                "/dealerships/mapping/assign",
                json=assign_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            assert assign_response.status_code == 200

        # Verify all mappings exist
        get_response = await client.get(
            f"/dealerships/lender/{lender.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        mappings = get_response.json()
        assert len(mappings) == 3

        # Update one mapping
        update_response = await client.put(
            f"/dealerships/mapping/edit?lender_id={lender.id}&dealership_id={dealership2.id}",
            json={"ratio": "50"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200

        # Remove one mapping
        unassign_response = await client.delete(
            "/dealerships/mapping/unassign",
            json={"lender_id": str(lender.id), "dealership_id": str(dealership3.id)},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert unassign_response.status_code == 200

        # Verify final state
        final_response = await client.get(
            f"/dealerships/lender/{lender.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert final_response.status_code == 200
        final_mappings = final_response.json()
        assert len(final_mappings) == 2

        # Check that the correct dealership was removed and ratio was updated
        remaining_ratios = {mapping["dealership_id"]: mapping["ratio"] for mapping in final_mappings}
        assert str(dealership1.id) in remaining_ratios
        assert str(dealership2.id) in remaining_ratios
        assert str(dealership3.id) not in remaining_ratios
        assert remaining_ratios[str(dealership2.id)] == "50" 