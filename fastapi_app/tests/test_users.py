"""
Tests for user management endpoints
"""

import pytest
from httpx import AsyncClient


class TestUsers:
    """Test user management endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, auth_headers, test_user):
        """Test listing users"""
        response = await client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["total"] >= 1
        assert len(data["users"]) >= 1
    
    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, client: AsyncClient, auth_headers):
        """Test listing users with pagination"""
        response = await client.get("/api/users/?page=1&size=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5
    
    @pytest.mark.asyncio
    async def test_list_users_with_filters(self, client: AsyncClient, auth_headers, test_user):
        """Test listing users with filters"""
        response = await client.get(
            f"/api/users/?username={test_user['username']}", 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert any(u["username"] == test_user["username"] for u in data["users"])
    
    @pytest.mark.asyncio
    async def test_get_user(self, client: AsyncClient, auth_headers, test_user):
        """Test getting a specific user"""
        response = await client.get(f"/api/users/{test_user['id']}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_user["id"]
        assert data["username"] == test_user["username"]
        assert data["email"] == test_user["email"]
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient, auth_headers):
        """Test getting a non-existent user"""
        response = await client.get("/api/users/999999", headers=auth_headers)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_user_admin_only(self, client: AsyncClient, admin_headers):
        """Test creating a user (admin only)"""
        user_data = {
            "username": "createduser",
            "email": "created@example.com",
            "full_name": "Created User",
            "password": "password123"
        }
        
        response = await client.post("/api/users/", json=user_data, headers=admin_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_superuser"] is False
    
    @pytest.mark.asyncio
    async def test_create_user_forbidden_for_regular_user(self, client: AsyncClient, auth_headers):
        """Test that regular users can't create other users"""
        user_data = {
            "username": "forbiddenuser",
            "email": "forbidden@example.com",
            "full_name": "Forbidden User",
            "password": "password123"
        }
        
        response = await client.post("/api/users/", json=user_data, headers=auth_headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_update_own_profile(self, client: AsyncClient, auth_headers, test_user):
        """Test updating own profile"""
        update_data = {
            "full_name": "Updated Full Name",
            "email": "updated@example.com"
        }
        
        response = await client.put(
            f"/api/users/{test_user['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["email"] == update_data["email"]
    
    @pytest.mark.asyncio
    async def test_update_other_user_forbidden(self, client: AsyncClient, auth_headers, test_superuser):
        """Test that regular users can't update other users"""
        update_data = {
            "full_name": "Forbidden Update"
        }
        
        response = await client.put(
            f"/api/users/{test_superuser['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_admin_update_any_user(self, client: AsyncClient, admin_headers, test_user):
        """Test that admins can update any user"""
        update_data = {
            "full_name": "Admin Updated",
            "is_active": False
        }
        
        response = await client.put(
            f"/api/users/{test_user['id']}", 
            json=update_data, 
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["is_active"] == update_data["is_active"]
    
    @pytest.mark.asyncio
    async def test_delete_user_admin_only(self, client: AsyncClient, admin_headers, test_user):
        """Test deleting a user (admin only)"""
        response = await client.delete(f"/api/users/{test_user['id']}", headers=admin_headers)
        assert response.status_code == 204
        
        # Verify user is deleted
        response = await client.get(f"/api/users/{test_user['id']}", headers=admin_headers)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_user_forbidden_for_regular_user(self, client: AsyncClient, auth_headers, test_superuser):
        """Test that regular users can't delete users"""
        response = await client.delete(f"/api/users/{test_superuser['id']}", headers=auth_headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_search_users(self, client: AsyncClient, auth_headers, test_user):
        """Test searching users"""
        response = await client.get(
            f"/api/users/search/?q={test_user['username'][:4]}", 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert any(test_user["username"] in u["username"] for u in data["users"])
    
    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self, client: AsyncClient):
        """Test listing users without authentication"""
        response = await client.get("/api/users/")
        assert response.status_code == 401 