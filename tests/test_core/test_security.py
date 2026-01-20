"""
Tests for core security functions.

Tests password hashing, verification, and JWT token creation.
"""
from datetime import timedelta, datetime, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_hash(self):
        """Test that get_password_hash returns a bcrypt hash."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_get_password_hash_different_each_time(self):
        """Test that hashing the same password produces different results (salt)."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts produce different hashes

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword456"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test password verification with empty password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False

    def test_hash_empty_password(self):
        """Test that empty passwords can be hashed (validation should be elsewhere)."""
        hashed = get_password_hash("")
        assert hashed is not None
        assert verify_password("", hashed) is True


class TestJWTTokens:
    """Tests for JWT token creation."""

    def test_create_access_token_returns_string(self):
        """Test that create_access_token returns a JWT string."""
        token = create_access_token(
            subject="test-user-id",
            expires_delta=timedelta(minutes=30),
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_subject(self):
        """Test that the token contains the correct subject."""
        subject = "test-user-id-12345"
        token = create_access_token(
            subject=subject,
            expires_delta=timedelta(minutes=30),
        )

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == subject

    def test_create_access_token_contains_expiration(self):
        """Test that the token contains expiration time."""
        token = create_access_token(
            subject="test-user",
            expires_delta=timedelta(minutes=30),
        )

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

        # Verify expiration is approximately 30 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp_time - now

        # Should be close to 30 minutes (allow 1 minute tolerance)
        assert 29 <= delta.total_seconds() / 60 <= 31

    def test_create_access_token_different_durations(self):
        """Test tokens with different expiration durations."""
        token_short = create_access_token(
            subject="user",
            expires_delta=timedelta(minutes=5),
        )
        token_long = create_access_token(
            subject="user",
            expires_delta=timedelta(hours=24),
        )

        payload_short = jwt.decode(token_short, settings.SECRET_KEY, algorithms=[ALGORITHM])
        payload_long = jwt.decode(token_long, settings.SECRET_KEY, algorithms=[ALGORITHM])

        # Long token should expire later
        assert payload_long["exp"] > payload_short["exp"]

    def test_create_access_token_subject_conversion(self):
        """Test that non-string subjects are converted to string."""
        import uuid

        user_id = uuid.uuid4()
        token = create_access_token(
            subject=user_id,
            expires_delta=timedelta(minutes=30),
        )

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == str(user_id)

    def test_token_invalid_with_wrong_secret(self):
        """Test that token cannot be decoded with wrong secret."""
        token = create_access_token(
            subject="test-user",
            expires_delta=timedelta(minutes=30),
        )

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret-key", algorithms=[ALGORITHM])

    def test_expired_token_raises_error(self):
        """Test that expired tokens raise an error when decoded."""
        # Create a token that expired 1 minute ago
        token = create_access_token(
            subject="test-user",
            expires_delta=timedelta(minutes=-1),
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
