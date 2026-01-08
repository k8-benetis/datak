"""Authentication routes."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, CurrentUser
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    Token,
)
from app.models.user import User
from app.models.audit import AuditLog, AuditAction

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class UserResponse(BaseModel):
    """User information response."""

    id: int
    username: str
    email: str | None
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    body: LoginRequest,
    db: DbSession,
) -> Token:
    """
    Authenticate user and return JWT token.
    """
    # Find user
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        # Log failed attempt
        await db.execute(
            AuditLog.__table__.insert().values(
                action=AuditAction.LOGIN_FAILED.value,
                details=f"Failed login for: {body.username}",
                ip_address=request.client.host if request.client else None,
            )
        )
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create token
    token = create_access_token(data={"sub": user.username, "role": user.role})

    # Log successful login
    db.add(
        AuditLog(
            user_id=user.id,
            action=AuditAction.LOGIN.value,
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.commit()

    return token


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: CurrentUser) -> User:
    """Get current authenticated user information."""
    return user


@router.post("/logout")
async def logout(
    request: Request,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """
    Logout current user (for audit logging).

    Note: With JWT, actual logout happens client-side by discarding the token.
    """
    db.add(
        AuditLog(
            user_id=user.id,
            action=AuditAction.LOGOUT.value,
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.commit()

    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    user: CurrentUser,
    db: DbSession,
    current_password: str,
    new_password: str,
) -> dict[str, str]:
    """Change password for current user."""
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    user.password_hash = hash_password(new_password)
    await db.commit()

    return {"message": "Password changed successfully"}
