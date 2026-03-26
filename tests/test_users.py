import pytest
from httpx import AsyncClient


class TestCreateUser:
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
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data
        assert "hashed_password" not in data
        assert "password" not in data

    async def test_create_user_duplicate_email(self, client: AsyncClient):
        payload = {
            "name": "Alice",
            "email": "alice@test.com",
            "password": "password123",
        }
        await client.post("/api/v1/users", json=payload)

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

    async def test_create_user_publishes_event(
        self, client: AsyncClient, mock_event_bus
    ):
        await client.post(
            "/api/v1/users",
            json={
                "name": "Alice",
                "email": "alice@test.com",
                "password": "password123",
            },
        )
        mock_event_bus.assert_called_once()
        event = mock_event_bus.call_args[0][0]
        assert event.email == "alice@test.com"
        assert event.via_google is False


class TestGetUser:
    async def test_get_user_success_for_same_user(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        user_id = test_user["id"]
        response = await client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == test_user["email"]

    async def test_get_user_requires_auth(self, client: AsyncClient, test_user: dict):
        response = await client.get(f"/api/v1/users/{test_user['id']}")
        assert response.status_code in (401, 403)

    async def test_get_user_forbidden_for_different_user(
        self,
        client: AsyncClient,
        test_user: dict,
        another_user_auth_headers: dict,
    ):
        response = await client.get(
            f"/api/v1/users/{test_user['id']}",
            headers=another_user_auth_headers,
        )
        assert response.status_code == 403
        assert "only access your own account" in response.json()["detail"].lower()

    async def test_get_user_unknown_id_is_forbidden_before_lookup(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/users/99999", headers=auth_headers)
        assert response.status_code == 403
        assert "only access your own account" in response.json()["detail"].lower()

    async def test_list_users_requires_admin(
        self, client: AsyncClient, auth_headers: dict, test_user: dict
    ):
        response = await client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 403
        assert "required role" in response.json()["detail"].lower()

    async def test_list_users_success_for_admin(
        self,
        client: AsyncClient,
        test_user: dict,
        another_user: dict,
        admin_auth_headers: dict,
    ):
        response = await client.get("/api/v1/users", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        assert data["total"] == 3
        assert data["page"] == 1
        assert len(data["items"]) == 3


class TestUpdateUser:
    async def test_update_user_name_for_same_user(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        user_id = test_user["id"]
        response = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["email"] == test_user["email"]

    async def test_update_user_success_for_admin(
        self, client: AsyncClient, test_user: dict, admin_auth_headers: dict
    ):
        response = await client.patch(
            f"/api/v1/users/{test_user['id']}",
            json={"name": "Admin Updated"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Admin Updated"

    async def test_update_user_forbidden_for_different_non_admin(
        self,
        client: AsyncClient,
        test_user: dict,
        another_user_auth_headers: dict,
    ):
        response = await client.patch(
            f"/api/v1/users/{test_user['id']}",
            json={"name": "Blocked Update"},
            headers=another_user_auth_headers,
        )
        assert response.status_code == 403
        assert "only update your own account" in response.json()["detail"].lower()

    async def test_update_user_not_found(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        response = await client.patch(
            "/api/v1/users/99999",
            json={"name": "Updated"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404


class TestDeleteUser:
    async def test_delete_requires_auth(self, client: AsyncClient, test_user: dict):
        response = await client.delete(f"/api/v1/users/{test_user['id']}")
        assert response.status_code in (401, 403)

    async def test_delete_requires_admin(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        response = await client.delete(
            f"/api/v1/users/{test_user['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "required role" in response.json()["detail"].lower()

    async def test_delete_user_success_for_admin(
        self,
        client: AsyncClient,
        test_user: dict,
        admin_auth_headers: dict,
    ):
        user_id = test_user["id"]
        response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

        response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    async def test_delete_user_not_found(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
    ):
        response = await client.delete(
            "/api/v1/users/99999",
            headers=admin_auth_headers,
        )
        assert response.status_code == 404
