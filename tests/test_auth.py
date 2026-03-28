from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.models.user import User


class TestLogin:

    async def test_login_success(self, client: AsyncClient, test_user: dict):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Token should be a non-empty string
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    async def test_login_wrong_password(self, client: AsyncClient, test_user: dict):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    async def test_login_nonexistent_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@test.com",
                "password": "password123",
            },
        )
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
        wrong_email = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@test.com",
                "password": "testpassword123",
            },
        )
        wrong_password = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )
        assert wrong_email.json()["detail"] == wrong_password.json()["detail"]

    async def test_login_rejects_deactivated_user(
        self,
        client: AsyncClient,
        db_session,
        test_user: dict,
    ):
        user = await db_session.get(User, test_user["id"])
        user.is_active = False
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"


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

    async def test_get_me_rejects_logged_out_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        blocked_tokens = set()
        token = auth_headers["Authorization"].split(" ", 1)[1]

        async def fake_add_token_to_blocklist(raw_token: str, expires_in: int):
            blocked_tokens.add(raw_token)

        async def fake_is_token_blocked(raw_token: str) -> bool:
            return raw_token in blocked_tokens

        with (
            patch(
                "app.core.security.add_token_to_blocklist",
                new=AsyncMock(side_effect=fake_add_token_to_blocklist),
            ),
            patch(
                "app.core.dependencies.is_token_blocked",
                new=AsyncMock(side_effect=fake_is_token_blocked),
            ),
        ):
            logout_response = await client.post(
                "/api/v1/auth/logout",
                headers=auth_headers,
            )
            assert logout_response.status_code == 200
            assert token in blocked_tokens

            response = await client.get("/api/v1/auth/me", headers=auth_headers)
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
        old_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        assert old_login.status_code == 401

        # Verify new password works
        new_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "newpassword456",
            },
        )
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
            return_value="https://accounts.google.com/o/oauth2/v2/auth?...",
        ):
            response = await client.get(
                "/api/v1/auth/google",
                follow_redirects=False,  # don't follow, just check redirect
            )
            assert response.status_code == 307  # temporary redirect
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
            response = await client.get("/api/v1/auth/google/callback?code=fake_code")
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
            response = await client.get("/api/v1/auth/google/callback?code=fake_code")
            assert response.status_code == 200
            assert response.json()["is_new_user"] is False


class TestRefreshToken:

    async def test_refresh_requires_cookie(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 401
        assert response.json()["detail"] == "No refresh token"

    async def test_refresh_rejects_invalid_cookie(self, client: AsyncClient):
        client.cookies.set("refresh_token", "not-a-real-token")
        try:
            response = await client.post("/api/v1/auth/refresh")
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid refresh token"
        finally:
            client.cookies.clear()
