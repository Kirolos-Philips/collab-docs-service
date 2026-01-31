"""Auth router - API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.database import get_database
from src.modules.auth.dependencies import get_current_active_user
from src.modules.auth.models import UserInDB
from src.modules.auth.schemas import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserResponse,
    VerifyEmailRequest,
)
from src.modules.auth.security import create_access_token
from src.modules.auth.services import (
    authenticate_user,
    get_user_by_email,
    get_user_by_username,
    initiate_password_reset,
    initiate_registration,
    reset_password,
    verify_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Register a new user (initiates email verification)."""
    # Check if email already exists
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
    if await get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    await initiate_registration(db, user_data)
    return {
        "message": "Registration initiated. Please verify your email with the OTP sent."
    }


@router.post("/verify-email")
async def verify_user_email(
    request: VerifyEmailRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Verify user's email with OTP."""
    success = await verify_email(db, request.email, request.otp)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP, or too many attempts.",
        )
    return {"message": "Email verified successfully"}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Token:
    """Login and get access token.

    Uses OAuth2 password flow (username field contains email).
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password, or user not verified.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserResponse:
    """Get current authenticated user."""
    return UserResponse(**current_user.model_dump())


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Initiate password reset."""
    await initiate_password_reset(db, request.email)
    # Always return success to avoid user enumeration
    return {"message": "If the email exists, an OTP has been sent."}


@router.post("/reset-password")
async def reset_user_password(
    request: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Reset password with OTP."""
    success = await reset_password(db, request.email, request.otp, request.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP, or too many attempts.",
        )
    return {"message": "Password reset successfully"}
