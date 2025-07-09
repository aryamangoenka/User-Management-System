"""
Tests for file upload endpoints
"""

import pytest
import tempfile
import os
from httpx import AsyncClient
from pathlib import Path


class TestFiles:
    """Test file upload endpoints"""
    
    @pytest.mark.asyncio
    async def test_upload_file(self, client: AsyncClient, auth_headers):
        """Test uploading a file"""
        # Create a test file
        content = b"This is test file content"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(content)
            tmp.flush()
            
            try:
                with open(tmp.name, 'rb') as f:
                    files = {"file": ("test.txt", f, "text/plain")}
                    response = await client.post("/api/files/upload", files=files, headers=auth_headers)
                
                assert response.status_code == 201
                
                data = response.json()
                assert data["original_filename"] == "test.txt"
                assert data["content_type"] == "text/plain"
                assert data["file_size"] == len(content)
                assert "id" in data
                assert "filename" in data
                assert "file_path" in data
                
            finally:
                os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_upload_file_unauthorized(self, client: AsyncClient):
        """Test uploading a file without authentication"""
        content = b"Unauthorized content"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(content)
            tmp.flush()
            
            try:
                with open(tmp.name, 'rb') as f:
                    files = {"file": ("test.txt", f, "text/plain")}
                    response = await client.post("/api/files/upload", files=files)
                
                assert response.status_code == 401
                
            finally:
                os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_upload_multiple_files(self, client: AsyncClient, auth_headers):
        """Test uploading multiple files"""
        files_to_upload = []
        temp_files = []
        
        try:
            # Create multiple test files
            for i in range(3):
                content = f"Test file {i} content".encode()
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f'_{i}.txt')
                tmp.write(content)
                tmp.flush()
                temp_files.append(tmp.name)
                
                files_to_upload.append(("files_list", (f"test_{i}.txt", open(tmp.name, 'rb'), "text/plain")))
            
            response = await client.post("/api/files/upload-multiple", files=files_to_upload, headers=auth_headers)
            
            # Close file handles
            for _, (_, f, _) in files_to_upload:
                f.close()
            
            assert response.status_code == 201
            
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 3
            
            for i, file_data in enumerate(data):
                assert file_data["original_filename"] == f"test_{i}.txt"
                assert file_data["content_type"] == "text/plain"
                
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, client: AsyncClient, auth_headers):
        """Test uploading a file that's too large"""
        # Create a large file (assuming max size is 10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(large_content)
            tmp.flush()
            
            try:
                with open(tmp.name, 'rb') as f:
                    files = {"file": ("large.txt", f, "text/plain")}
                    response = await client.post("/api/files/upload", files=files, headers=auth_headers)
                
                assert response.status_code == 413
                assert "File size too large" in response.json()["detail"]
                
            finally:
                os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client: AsyncClient, auth_headers):
        """Test uploading an invalid file type"""
        content = b"Invalid file content"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp:
            tmp.write(content)
            tmp.flush()
            
            try:
                with open(tmp.name, 'rb') as f:
                    files = {"file": ("malware.exe", f, "application/x-executable")}
                    response = await client.post("/api/files/upload", files=files, headers=auth_headers)
                
                assert response.status_code == 400
                assert "File type not allowed" in response.json()["detail"]
                
            finally:
                os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_list_files(self, client: AsyncClient, auth_headers):
        """Test listing user's files"""
        response = await client.get("/api/files/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "files" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
    
    @pytest.mark.asyncio
    async def test_list_files_with_filter(self, client: AsyncClient, auth_headers):
        """Test listing files with content type filter"""
        response = await client.get("/api/files/?content_type=text", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for file_data in data["files"]:
            assert "text" in file_data["content_type"]
    
    @pytest.mark.asyncio
    async def test_list_all_files_admin(self, client: AsyncClient, admin_headers):
        """Test listing all files (admin only)"""
        response = await client.get("/api/files/admin/", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "files" in data
    
    @pytest.mark.asyncio
    async def test_list_all_files_forbidden(self, client: AsyncClient, auth_headers):
        """Test that regular users can't access admin file list"""
        response = await client.get("/api/files/admin/", headers=auth_headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_file_info(self, client: AsyncClient, auth_headers):
        """Test getting file information"""
        # First upload a file
        content = b"File info test content"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(content)
            tmp.flush()
            
            try:
                with open(tmp.name, 'rb') as f:
                    files = {"file": ("info_test.txt", f, "text/plain")}
                    upload_response = await client.post("/api/files/upload", files=files, headers=auth_headers)
                
                assert upload_response.status_code == 201
                file_id = upload_response.json()["id"]
                
                # Get file info
                response = await client.get(f"/api/files/{file_id}", headers=auth_headers)
                assert response.status_code == 200
                
                data = response.json()
                assert data["id"] == file_id
                assert data["original_filename"] == "info_test.txt"
                
            finally:
                os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_get_file_stats(self, client: AsyncClient, auth_headers):
        """Test getting file statistics"""
        response = await client.get("/api/files/stats/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_files" in data
        assert "total_size_bytes" in data
        assert "total_size_mb" in data
        assert "files_by_type" in data
    
    @pytest.mark.asyncio
    async def test_get_admin_file_stats(self, client: AsyncClient, admin_headers):
        """Test getting admin file statistics"""
        response = await client.get("/api/files/admin/stats/", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_files" in data
        assert "total_size_bytes" in data
        assert "files_by_type" in data
        assert "files_by_user" in data
    
    @pytest.mark.asyncio
    async def test_delete_file(self, client: AsyncClient, auth_headers):
        """Test deleting a file"""
        # First upload a file
        content = b"Delete test content"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(content)
            tmp.flush()
            
            try:
                with open(tmp.name, 'rb') as f:
                    files = {"file": ("delete_test.txt", f, "text/plain")}
                    upload_response = await client.post("/api/files/upload", files=files, headers=auth_headers)
                
                assert upload_response.status_code == 201
                file_id = upload_response.json()["id"]
                
                # Delete file
                response = await client.delete(f"/api/files/{file_id}", headers=auth_headers)
                assert response.status_code == 204
                
                # Verify file is deleted
                response = await client.get(f"/api/files/{file_id}", headers=auth_headers)
                assert response.status_code == 404
                
            finally:
                os.unlink(tmp.name) 