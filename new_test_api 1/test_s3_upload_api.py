import pytest
import asyncio
import uuid
import io
from httpx import AsyncClient
from app.main import app
from app.models.models import User, Application, PdfLog
from app.utils.hashing import hash_password
from app.db.connection import get_db
from httpx._transports.asgi import ASGITransport
from sqlalchemy.future import select
from decimal import Decimal
from unittest.mock import patch, MagicMock


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


# Helper to create a mock PDF file
def create_mock_pdf_content():
    """Create a simple PDF-like content for testing"""
    # This is a minimal PDF structure for testing
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000136 00000 n 
0000000229 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
324
%%EOF"""
    return pdf_content


@pytest.mark.anyio
async def test_upload_single_pdf_success():
    """Test successfully uploading a single PDF file"""
    email = f"s3_upload_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    # Create mock PDF content
    pdf_content = create_mock_pdf_content()
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue:
        
        mock_s3_client.return_value.upload_fileobj = MagicMock()
        mock_bucket_name.return_value = "test-bucket"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files={"files": ("test_document.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    assert data["application_id"] == str(application.id)
    assert data["message"] == "Upload completed"
    assert len(data["files"]) == 1
    assert data["files"][0]["file_name"] == "test_document.pdf"
    assert data["files"][0]["status"] == "Success"
    assert "file_url" in data["files"][0]


@pytest.mark.anyio
async def test_upload_multiple_pdfs_success():
    """Test successfully uploading multiple PDF files"""
    email = f"s3_multi_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    # Create mock PDF content
    pdf_content = create_mock_pdf_content()
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue:
        
        mock_s3_client.return_value.upload_fileobj = MagicMock()
        mock_bucket_name.return_value = "test-bucket"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = [
                ("files", ("document1.pdf", io.BytesIO(pdf_content), "application/pdf")),
                ("files", ("document2.pdf", io.BytesIO(pdf_content), "application/pdf")),
                ("files", ("document3.pdf", io.BytesIO(pdf_content), "application/pdf"))
            ]
            
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files=files,
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 200, f"Multiple upload failed: {response.text}"
    data = response.json()
    assert data["application_id"] == str(application.id)
    assert len(data["files"]) == 3
    
    file_names = [file["file_name"] for file in data["files"]]
    assert "document1.pdf" in file_names
    assert "document2.pdf" in file_names
    assert "document3.pdf" in file_names
    
    for file_data in data["files"]:
        assert file_data["status"] == "Success"


@pytest.mark.anyio
async def test_upload_non_pdf_file_rejection():
    """Test that non-PDF files are rejected"""
    email = f"s3_nonpdf_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    # Create a text file instead of PDF
    text_content = b"This is not a PDF file"
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue:
        
        mock_s3_client.return_value.upload_fileobj = MagicMock()
        mock_bucket_name.return_value = "test-bucket"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files={"files": ("not_a_pdf.txt", io.BytesIO(text_content), "text/plain")},
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 200  # Request succeeds but file is rejected
    data = response.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["file_name"] == "not_a_pdf.txt"
    assert data["files"][0]["status"] == "Failed"
    assert data["files"][0]["reason"] == "Not a PDF file."


@pytest.mark.anyio
async def test_upload_mixed_file_types():
    """Test uploading a mix of PDF and non-PDF files"""
    email = f"s3_mixed_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    pdf_content = create_mock_pdf_content()
    text_content = b"This is not a PDF"
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue:
        
        mock_s3_client.return_value.upload_fileobj = MagicMock()
        mock_bucket_name.return_value = "test-bucket"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = [
                ("files", ("valid.pdf", io.BytesIO(pdf_content), "application/pdf")),
                ("files", ("invalid.txt", io.BytesIO(text_content), "text/plain")),
                ("files", ("another_valid.pdf", io.BytesIO(pdf_content), "application/pdf"))
            ]
            
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files=files,
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 3
    
    # Check results for each file
    results_by_name = {file["file_name"]: file for file in data["files"]}
    
    assert results_by_name["valid.pdf"]["status"] == "Success"
    assert results_by_name["invalid.txt"]["status"] == "Failed"
    assert results_by_name["invalid.txt"]["reason"] == "Not a PDF file."
    assert results_by_name["another_valid.pdf"]["status"] == "Success"


@pytest.mark.anyio
async def test_upload_no_files_provided():
    """Test uploading with no files provided"""
    email = f"s3_nofiles_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/s3/upload-multiple-pdfs/",
            data={"application_id": str(application.id)},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 400
    assert "No files provided" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_invalid_application_id():
    """Test uploading with invalid application ID"""
    email = f"s3_invalid_app_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        break

    token = await login_and_get_token(email, password)
    pdf_content = create_mock_pdf_content()
    
    # Use a valid UUID format but non-existent application
    fake_app_id = str(uuid.uuid4())
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue:
        
        mock_s3_client.return_value.upload_fileobj = MagicMock()
        mock_bucket_name.return_value = "test-bucket"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": fake_app_id},
                files={"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"}
            )

    # The API should still accept the upload (it doesn't validate application existence)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_upload_s3_error_handling():
    """Test handling of S3 upload errors"""
    email = f"s3_error_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)
    pdf_content = create_mock_pdf_content()
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue:
        
        # Simulate S3 upload error
        mock_s3_client.return_value.upload_fileobj.side_effect = Exception("S3 upload failed")
        mock_bucket_name.return_value = "test-bucket"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files={"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 200  # Request succeeds but file upload fails
    data = response.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["status"] == "Failed"
    assert "S3 upload failed" in data["files"][0]["reason"]


@pytest.mark.anyio
async def test_upload_missing_aws_credentials():
    """Test upload when AWS credentials are missing"""
    email = f"s3_no_creds_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)
    pdf_content = create_mock_pdf_content()
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client:
        # Simulate missing AWS credentials
        mock_s3_client.side_effect = ValueError("Missing AWS credentials environment variables.")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files={"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 500


@pytest.mark.anyio
async def test_upload_missing_bucket_name():
    """Test upload when S3 bucket name is missing"""
    email = f"s3_no_bucket_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)
    pdf_content = create_mock_pdf_content()
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name:
        
        mock_s3_client.return_value = MagicMock()
        mock_bucket_name.side_effect = ValueError("Missing S3_BUCKET environment variable.")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files={"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 500


@pytest.mark.anyio
async def test_upload_creates_pdf_logs():
    """Test that successful uploads create PDF log entries"""
    email = f"s3_logs_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)
    pdf_content = create_mock_pdf_content()
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue:
        
        mock_s3_client.return_value.upload_fileobj = MagicMock()
        mock_bucket_name.return_value = "test-bucket"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files={"files": ("test_document.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 200

    # Check that PDF log was created
    async for db in get_db():
        stmt = select(PdfLog).where(PdfLog.application_id == application.id)
        result = await db.execute(stmt)
        pdf_logs = result.scalars().all()
        
        assert len(pdf_logs) > 0
        assert pdf_logs[0].pdf_name == "test_document.pdf"
        assert pdf_logs[0].status == "not started"
        break


@pytest.mark.anyio
async def test_upload_requires_authentication():
    """Test that upload endpoint requires authentication"""
    async for db in get_db():
        application = await create_test_application(db)
        break

    pdf_content = create_mock_pdf_content()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/s3/upload-multiple-pdfs/",
            data={"application_id": str(application.id)},
            files={"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_upload_file_url_generation():
    """Test that successful uploads generate correct file URLs"""
    email = f"s3_url_{uuid.uuid4()}@example.com"
    password = "testpass123"

    async for db in get_db():
        await create_test_user_with_permissions(db, email, password, ["upload_files"])
        application = await create_test_application(db)
        break

    token = await login_and_get_token(email, password)
    pdf_content = create_mock_pdf_content()
    
    with patch('app.api.upload_pdf_s3.get_s3_client') as mock_s3_client, \
         patch('app.api.upload_pdf_s3.get_bucket_name') as mock_bucket_name, \
         patch('app.services.queue_manager.QueueManager.push_application') as mock_queue, \
         patch.dict('os.environ', {'AWS_REGION': 'us-west-2'}):
        
        mock_s3_client.return_value.upload_fileobj = MagicMock()
        mock_bucket_name.return_value = "test-bucket-name"
        mock_queue.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/s3/upload-multiple-pdfs/",
                data={"application_id": str(application.id)},
                files={"files": ("my_document.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"}
            )

    assert response.status_code == 200
    data = response.json()
    file_url = data["files"][0]["file_url"]
    
    expected_url_pattern = "https://test-bucket-name.s3.us-west-2.amazonaws.com/my_document.pdf"
    assert file_url == expected_url_pattern 