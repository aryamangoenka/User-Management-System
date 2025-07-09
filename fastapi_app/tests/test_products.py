"""
Tests for product management endpoints
"""

import pytest
from httpx import AsyncClient


class TestProducts:
    """Test product management endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_products_public(self, client: AsyncClient, test_product):
        """Test listing active products (public endpoint)"""
        response = await client.get("/api/products/")
        assert response.status_code == 200
        
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["total"] >= 1
        assert len(data["products"]) >= 1
    
    @pytest.mark.asyncio
    async def test_list_products_with_filters(self, client: AsyncClient, test_product):
        """Test listing products with filters"""
        response = await client.get(f"/api/products/?category={test_product['category']}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert any(p["category"] == test_product["category"] for p in data["products"])
    
    @pytest.mark.asyncio
    async def test_list_products_price_filter(self, client: AsyncClient, test_product):
        """Test listing products with price filters"""
        response = await client.get("/api/products/?min_price=50&max_price=150")
        assert response.status_code == 200
        
        data = response.json()
        for product in data["products"]:
            assert 50 <= product["price"] <= 150
    
    @pytest.mark.asyncio
    async def test_list_products_admin(self, client: AsyncClient, admin_headers, test_product):
        """Test listing all products including inactive (admin only)"""
        response = await client.get("/api/products/admin/", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "products" in data
        assert data["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_list_products_admin_unauthorized(self, client: AsyncClient, auth_headers):
        """Test that regular users can't access admin product list"""
        response = await client.get("/api/products/admin/", headers=auth_headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_product_public(self, client: AsyncClient, test_product):
        """Test getting a specific product (public endpoint)"""
        response = await client.get(f"/api/products/{test_product['id']}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_product["id"]
        assert data["name"] == test_product["name"]
        assert data["price"] == test_product["price"]
    
    @pytest.mark.asyncio
    async def test_get_product_not_found(self, client: AsyncClient):
        """Test getting a non-existent product"""
        response = await client.get("/api/products/999999")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_product(self, client: AsyncClient, auth_headers):
        """Test creating a product"""
        product_data = {
            "name": "New Product",
            "description": "A new product",
            "price": 199.99,
            "category": "Electronics",
            "stock_quantity": 5
        }
        
        response = await client.post("/api/products/", json=product_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == product_data["name"]
        assert data["description"] == product_data["description"]
        assert data["price"] == product_data["price"]
        assert data["category"] == product_data["category"]
        assert data["stock_quantity"] == product_data["stock_quantity"]
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_create_product_unauthorized(self, client: AsyncClient):
        """Test creating a product without authentication"""
        product_data = {
            "name": "Unauthorized Product",
            "price": 100.0
        }
        
        response = await client.post("/api/products/", json=product_data)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_own_product(self, client: AsyncClient, auth_headers, test_product):
        """Test updating own product"""
        update_data = {
            "name": "Updated Product Name",
            "price": 149.99
        }
        
        response = await client.put(
            f"/api/products/{test_product['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]
    
    @pytest.mark.asyncio
    async def test_update_product_not_found(self, client: AsyncClient, auth_headers):
        """Test updating a non-existent product"""
        update_data = {
            "name": "Non-existent Product"
        }
        
        response = await client.put("/api/products/999999", json=update_data, headers=auth_headers)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_own_product(self, client: AsyncClient, auth_headers, test_product):
        """Test deleting own product"""
        response = await client.delete(f"/api/products/{test_product['id']}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify product is deleted
        response = await client.get(f"/api/products/{test_product['id']}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_product_not_found(self, client: AsyncClient, auth_headers):
        """Test deleting a non-existent product"""
        response = await client.delete("/api/products/999999", headers=auth_headers)
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_search_products(self, client: AsyncClient, test_product):
        """Test searching products"""
        response = await client.get(f"/api/products/search/?q={test_product['name'][:4]}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert any(test_product["name"][:4].lower() in p["name"].lower() for p in data["products"])
    
    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient, test_product):
        """Test getting product categories"""
        response = await client.get("/api/products/categories/")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert test_product["category"] in data
    
    @pytest.mark.asyncio
    async def test_get_my_products(self, client: AsyncClient, auth_headers, test_product):
        """Test getting current user's products"""
        response = await client.get("/api/products/my/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "products" in data
        assert data["total"] >= 1
        assert any(p["id"] == test_product["id"] for p in data["products"])
    
    @pytest.mark.asyncio
    async def test_get_my_products_unauthorized(self, client: AsyncClient):
        """Test getting my products without authentication"""
        response = await client.get("/api/products/my/")
        assert response.status_code == 401 