# tests/test_users.py
import pytest
from httpx import AsyncClient


class TestCreateUser:
    """Group related tests in classes — keeps the file organized."""

    async def test_create_user_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users",
            json={
                "name": "Alice",
                "email": "alice@test.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Alice"
        assert data["email"] == "alice@test.com"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        # Most important security check — never expose hashed password
        assert "hashed_password" not in data
        assert "password" not in data

    async def test_create_user_duplicate_email(self, client: AsyncClient):
        payload = {
            "name": "Alice",
            "email": "alice@test.com",
            "password": "password123",
        }
        # First creation should succeed
        await client.post("/api/v1/users", json=payload)

        # Second creation with same email should fail
        response = await client.post("/api/v1/users", json=payload)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    async def test_create_user_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users",
            json={
                "name": "Alice",
                "email": "notanemail",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    async def test_create_user_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users",
            json={
                "name": "Alice",
                "email": "alice@test.com",
                "password": "short",
            },
        )
        assert response.status_code == 422

    async def test_create_user_blank_name(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users",
            json={
                "name": "   ",
                "email": "alice@test.com",
                "password": "password123",
            },
        )
        assert response.status_code == 422


class TestGetUser:

    async def test_get_user_success(self, client: AsyncClient, test_user: dict):
        user_id = test_user["id"]
        response = await client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]

    async def test_get_user_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/users/99999")
        assert response.status_code == 404
        # Verify our consistent error shape
        data = response.json()
        assert "status_code" in data
        assert "error" in data
        assert "request_id" in data

    async def test_list_users(self, client: AsyncClient, test_user: dict):
        response = await client.get("/api/v1/users")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1


class TestUpdateUser:

    async def test_update_user_name(self, client: AsyncClient, test_user: dict):
        user_id = test_user["id"]
        response = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        # Email should be unchanged — partial update
        assert response.json()["email"] == test_user["email"]

    async def test_update_user_not_found(self, client: AsyncClient):
        response = await client.patch(
            "/api/v1/users/99999",
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteUser:

    async def test_delete_requires_auth(self, client: AsyncClient, test_user: dict):
        """Delete without token should be rejected."""
        user_id = test_user["id"]
        response = await client.delete(f"/api/v1/users/{user_id}")
        assert response.status_code == 401  # Authorization header missing

    async def test_delete_user_success(
        self,
        client: AsyncClient,
        test_user: dict,
        auth_headers: dict,
    ):
        user_id = test_user["id"]
        response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify the user is actually gone
        response = await client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 404

    async def test_delete_user_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.delete(
            "/api/v1/users/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404
