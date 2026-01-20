"""
Authentication Routes.

JWT-based authentication for API access.
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.crud import authenticate_user, create_user, get_user_by_email
from app.models import Token, UserCreate, UserPublic

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    OAuth2 compatible token login.

    Returns JWT access token for API authentication.
    """
    user = authenticate_user(
        session=session,
        email=form_data.username,
        password=form_data.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
        )
    )


@router.post("/register", response_model=UserPublic)
async def register(
    session: SessionDep,
    user_in: UserCreate,
) -> UserPublic:
    """
    Register a new user.

    Returns the created user (without password).
    """
    existing = get_user_by_email(session=session, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user = create_user(session=session, user_create=user_in)
    return UserPublic.model_validate(user)


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserPublic:
    """Get current authenticated user info."""
    return UserPublic.model_validate(current_user)


@router.post("/test-token", response_model=UserPublic)
async def test_token(current_user: CurrentUser) -> UserPublic:
    """Test if access token is valid."""
    return UserPublic.model_validate(current_user)
