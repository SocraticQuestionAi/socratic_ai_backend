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


class TestAuthEdgeCases:
    """Tests for authentication edge cases and error handling."""

    def test_token_with_invalid_uuid_subject(self, client: TestClient):
        """Test token with non-UUID subject returns 403."""
        import jwt
        from app.core.config import settings
        from app.core.security import ALGORITHM

        # Create a token with invalid UUID as subject
        token = jwt.encode(
            {"sub": "not-a-valid-uuid", "exp": 9999999999},
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "Could not validate credentials" in response.json()["detail"]

    def test_token_with_nonexistent_user_id(self, client: TestClient):
        """Test token with valid UUID but nonexistent user returns 404."""
        import uuid
        import jwt
        from app.core.config import settings
        from app.core.security import ALGORITHM

        # Create a token with a valid UUID that doesn't exist in DB
        fake_user_id = str(uuid.uuid4())
        token = jwt.encode(
            {"sub": fake_user_id, "exp": 9999999999},
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_token_for_inactive_user(self, client: TestClient, inactive_user: User):
        """Test that accessing protected route with inactive user token returns 400."""
        from datetime import timedelta
        from app.core.security import create_access_token

        token = create_access_token(
            subject=str(inactive_user.id),
            expires_delta=timedelta(minutes=30),
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]

    def test_optional_auth_with_invalid_token(
        self, client: TestClient, sample_text_content: str
    ):
        """Test optional auth endpoint with invalid token doesn't fail."""
        from unittest.mock import patch, MagicMock

        with patch(
            "app.api.routes.generation.get_question_generator"
        ) as mock_get_generator:
            from app.schemas.questions import GeneratedQuestions, GeneratedQuestion, MCQOptionSchema

            mock_generator = MagicMock()
            mock_generator.generate_from_document.return_value = GeneratedQuestions(
                questions=[
                    GeneratedQuestion(
                        question_text="Test question?",
                        question_type="mcq",
                        difficulty="easy",
                        topic="Test",
                        explanation="Test explanation",
                        options=[
                            MCQOptionSchema(label="A", text="Answer A", is_correct=True),
                            MCQOptionSchema(label="B", text="Answer B", is_correct=False),
                        ],
                        correct_answer="A",
                        confidence_score=0.9,
                    ),
                ],
                generation_summary="Generated 1 question",
            )
            mock_get_generator.return_value = mock_generator

            # Should still work with invalid token (optional auth)
            response = client.post(
                "/api/v1/generate/from-text",
                json={"content": sample_text_content, "num_questions": 1},
                headers={"Authorization": "Bearer invalid-token"},
            )

            # Optional auth should allow the request
            assert response.status_code == 200
