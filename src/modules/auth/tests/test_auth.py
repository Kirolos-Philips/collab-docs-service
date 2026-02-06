"""Tests for auth module."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

# We use the async_client fixture from tests/conftest.py


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
    }


class TestAuthRegister:
    """Test user registration."""

    @pytest.mark.asyncio
    async def test_register_success(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test successful registration (initiates verification)."""
        response = await async_client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert "Registration initiated" in data["message"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test registration with duplicate email fails."""
        # First registration and verification
        await async_client.post("/auth/register", json=test_user_data)
        await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )

        # Second registration with same email should now fail
        response = await async_client.post("/auth/register", json=test_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(self, async_client: AsyncClient):
        """Test registration with short password fails."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "short",
            },
        )
        assert response.status_code == 422


class TestAuthVerify:
    """Test email verification."""

    @pytest.mark.asyncio
    async def test_verify_success(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test successful email verification."""
        await async_client.post("/auth/register", json=test_user_data)

        response = await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )
        assert response.status_code == 200
        assert "verified successfully" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_verify_wrong_otp(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test verification with wrong OTP fails."""
        await async_client.post("/auth/register", json=test_user_data)

        response = await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "000000"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_too_many_attempts(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test verification stops after 3 failed attempts."""
        await async_client.post("/auth/register", json=test_user_data)

        # 3 failed attempts
        for _ in range(3):
            response = await async_client.post(
                "/auth/verify-email",
                json={"email": test_user_data["email"], "otp": "000000"},
            )
            assert response.status_code == 400

        # 4th attempt with CORRECT OTP should fail because trials exhausted
        response = await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )
        assert response.status_code == 400


class TestAuthLogin:
    """Test user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user_data: dict):
        """Test successful login."""
        # Register and verify first
        await async_client.post("/auth/register", json=test_user_data)
        await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )

        # Login
        response = await async_client.post(
            "/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_unverified_fails(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test login fails if user is not verified."""
        await async_client.post("/auth/register", json=test_user_data)

        response = await async_client.post(
            "/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        assert response.status_code == 401
        assert "not verified" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test login with wrong password fails."""
        # Register and verify
        await async_client.post("/auth/register", json=test_user_data)
        await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )

        # Login with wrong password
        response = await async_client.post(
            "/auth/login",
            data={
                "username": test_user_data["email"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with nonexistent user fails."""
        response = await async_client.post(
            "/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401


class TestAuthMe:
    """Test current user endpoint."""

    @pytest.mark.asyncio
    async def test_me_success(self, async_client: AsyncClient, test_user_data: dict):
        """Test getting current user."""
        # Register and verify
        await async_client.post("/auth/register", json=test_user_data)
        await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )

        # Login
        login_response = await async_client.post(
            "/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["is_verified"] is True

    @pytest.mark.asyncio
    async def test_me_no_token(self, async_client: AsyncClient):
        """Test getting current user without token fails."""
        response = await async_client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestAuthUpdateMe:
    """Test updating current user profile."""

    @pytest.mark.asyncio
    async def test_update_me_success(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test updating current user profile."""
        # 1. Register, verify, and login to get token
        await async_client.post("/auth/register", json=test_user_data)
        await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )
        login_response = await async_client.post(
            "/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        token = login_response.json()["access_token"]

        # 2. Update username
        new_username = "new_cool_name"
        response = await async_client.patch(
            "/auth/me",
            json={"username": new_username},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == new_username

        # 3. Verify it's actually in DB by calling /me
        me_response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.json()["username"] == new_username


class TestAuthAvatarUpload:
    """Test avatar upload."""

    @pytest.mark.asyncio
    async def test_avatar_upload_success(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test successful avatar upload."""
        # 1. Register, verify, and login
        await async_client.post("/auth/register", json=test_user_data)
        await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )
        login_response = await async_client.post(
            "/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        token = login_response.json()["access_token"]

        # 2. Upload avatar
        import io

        from PIL import Image

        img = Image.new("RGB", (100, 100), color="blue")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        files = {"file": ("avatar.png", img_byte_arr.getvalue(), "image/png")}

        response = await async_client.post(
            "/auth/me/profile-picture",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "avatar_url" in data
        assert "/static/uploads/avatars/" in data["avatar_url"]
        assert "medium.webp" in data["avatar_url"]


class TestAuthPasswordReset:
    """Test password reset flow."""

    @pytest.mark.asyncio
    async def test_password_reset_success(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """Test successful password reset."""
        # Register and verify
        await async_client.post("/auth/register", json=test_user_data)
        await async_client.post(
            "/auth/verify-email",
            json={"email": test_user_data["email"], "otp": "123456"},
        )

        # Forgot password
        await async_client.post(
            "/auth/forgot-password", json={"email": test_user_data["email"]}
        )

        # Reset password
        response = await async_client.post(
            "/auth/reset-password",
            json={
                "email": test_user_data["email"],
                "otp": "123456",
                "new_password": "newsecretpassword",
            },
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

        # Try login with new password
        response = await async_client.post(
            "/auth/login",
            data={
                "username": test_user_data["email"],
                "password": "newsecretpassword",
            },
        )
        assert response.status_code == 200
