"""
Tests for authentication routes.

Tests login, registration, and token validation endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.models import User


class TestLogin:
    """Tests for the login endpoint."""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with incorrect password."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@example.com", "password": "anypassword"},
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_inactive_user(self, client: TestClient, inactive_user: User):
        """Test login with inactive user account."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": inactive_user.email, "password": "inactivepassword123"},
        )

        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]


class TestRegister:
    """Tests for the registration endpoint."""

    def test_register_success(self, client: TestClient, valid_user_data: dict):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json=valid_user_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == valid_user_data["email"]
        assert data["full_name"] == valid_user_data["full_name"]
        assert "id" in data
        # Password should not be in response
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with existing email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "newpassword123",
                "full_name": "Another User",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_short_password(self, client: TestClient):
        """Test registration with too short password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpass@example.com",
                "password": "short",
                "full_name": "Short Pass User",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "validpassword123",
                "full_name": "Invalid Email User",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_register_minimal_fields(self, client: TestClient):
        """Test registration with only required fields."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "minimal@example.com",
                "password": "minimalpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "minimal@example.com"
        assert data["full_name"] is None


class TestGetCurrentUser:
    """Tests for getting current user info."""

    def test_get_me_authenticated(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """Test getting current user with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    def test_get_me_no_token(self, client: TestClient):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 403


class TestTestToken:
    """Tests for token validation endpoint."""

    def test_test_token_valid(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """Test token validation with valid token."""
        response = client.post("/api/v1/auth/test-token", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email

    def test_test_token_invalid(self, client: TestClient):
        """Test token validation with invalid token."""
        response = client.post(
            "/api/v1/auth/test-token",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 403
