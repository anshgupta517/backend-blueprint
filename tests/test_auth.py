from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


class TestLogin:

    async def test_login_success(self, client: AsyncClient, test_user: dict):
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Token should be a non-empty string
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    async def test_login_wrong_password(self, client: AsyncClient, test_user: dict):
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"
        
    async def test_login_nonexistent_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    async def test_login_wrong_email_same_message_as_wrong_password(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """
        Security test — wrong email and wrong password must return
        identical error messages. If they differ, attackers can enumerate
        which emails are registered.
        """
        wrong_email = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "testpassword123",
        })
        wrong_password = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert wrong_email.json()["detail"] == wrong_password.json()["detail"]


class TestMe:

    async def test_get_me_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "hashed_password" not in data

    async def test_get_me_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)  # Depends on how auth is implemented

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer completelyfaketoken"},
        )
        assert response.status_code == 401


class TestChangePassword:

    async def test_change_password_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        # Change the password
        response = await client.patch(
            "/api/v1/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify old password no longer works
        old_login = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        assert old_login.status_code == 401

        # Verify new password works
        new_login = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "newpassword456",
        })
        assert new_login.status_code == 200

    async def test_change_password_wrong_current(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        response = await client.patch(
            "/api/v1/auth/change-password",
            json={
                "current_password": "wrongcurrentpassword",
                "new_password": "newpassword456",
            },
            headers=auth_headers,
        )
        assert response.status_code == 401

class TestGoogleOAuth:

    async def test_google_login_redirects(self, client: AsyncClient):
        """Should redirect to Google when OAuth is configured."""
        with patch(
            "app.services.auth.AuthService.get_google_auth_url",
            new_callable=AsyncMock,
            return_value="https://accounts.google.com/o/oauth2/v2/auth?..."
        ):
            response = await client.get(
                "/api/v1/auth/google",
                follow_redirects=False,   # don't follow, just check redirect
            )
            assert response.status_code == 307   # temporary redirect
            assert "accounts.google.com" in response.headers["location"]

    async def test_google_callback_new_user(self, client: AsyncClient):
        """New Google user should get a JWT and is_new_user=True."""
        mock_result = {
            "access_token": "test.jwt.token",
            "token_type": "bearer",
            "is_new_user": True,
        }
        with patch(
            "app.services.auth.AuthService.handle_google_callback",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await client.get(
                "/api/v1/auth/google/callback?code=fake_code"
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["is_new_user"] is True

    async def test_google_callback_existing_user(
        self, client: AsyncClient, test_user: dict
    ):
        """Existing email/password user should be linked, is_new_user=False."""
        mock_result = {
            "access_token": "test.jwt.token",
            "token_type": "bearer",
            "is_new_user": False,
        }
        with patch(
            "app.services.auth.AuthService.handle_google_callback",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await client.get(
                "/api/v1/auth/google/callback?code=fake_code"
            )
            assert response.status_code == 200
            assert response.json()["is_new_user"] is False