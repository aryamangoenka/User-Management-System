"""
Tests for authentication endpoints
"""

import pytest
from httpx import AsyncClient


class TestAuth:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        """Test user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "newpassword123"
        }
        
        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        """Test registering with duplicate username"""
        user_data = {
            "username": test_user["username"],
            "email": "different@example.com",
            "full_name": "Different User",
            "password": "password123"
        }
        
        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registering with duplicate email"""
        user_data = {
            "username": "differentuser",
            "email": test_user["email"],
            "full_name": "Different User",
            "password": "password123"
        }
        
        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_with_form_data(self, client: AsyncClient, test_user):
        """Test login with form data"""
        login_data = {
            "username": test_user["username"],
            "password": "testpassword"
        }
        
        response = await client.post("/api/auth/login", data=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_with_json(self, client: AsyncClient, test_user):
        """Test login with JSON data"""
        login_data = {
            "username": test_user["username"],
            "password": "testpassword"
        }
        
        response = await client.post("/api/auth/login-json", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, test_user):
        """Test login with invalid credentials"""
        login_data = {
            "username": test_user["username"],
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/auth/login-json", json=login_data)
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        login_data = {
            "username": "nonexistent",
            "password": "password"
        }
        
        response = await client.post("/api/auth/login-json", json=login_data)
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """Test getting current user information"""
        response = await client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication"""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, auth_headers):
        """Test token refresh"""
        response = await client.post("/api/auth/refresh", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_unauthorized(self, client: AsyncClient):
        """Test token refresh without authentication"""
        response = await client.post("/api/auth/refresh")
        assert response.status_code == 401 