"""Login, logout, and current-session API routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models import User
from app.schemas.auth import AuthenticatedUserRead, LoginRequest, PasswordChangeRequest
from app.services.auth_service import (
    AuthenticationError,
    LoginRateLimitError,
    authenticate_user,
    change_password,
    login_attempt_limiter,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _user_response(user: User) -> AuthenticatedUserRead:
    return AuthenticatedUserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        must_change_password=user.must_change_password,
    )


@router.post("/login", response_model=AuthenticatedUserRead)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> AuthenticatedUserRead:
    """Authenticate credentials and establish a signed HTTP-only browser session."""
    settings = get_settings()
    client_key = request.client.host if request.client else "unknown"
    try:
        login_attempt_limiter.check(client_key, window_seconds=settings.login_attempt_window_seconds)
        user = authenticate_user(db, identifier=payload.identifier, password=payload.password)
    except LoginRateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        ) from error
    except AuthenticationError as error:
        login_attempt_limiter.record_failure(
            client_key,
            max_attempts=settings.login_max_attempts,
            window_seconds=settings.login_attempt_window_seconds,
            lockout_seconds=settings.login_lockout_seconds,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        ) from error

    login_attempt_limiter.record_success(client_key)
    request.session.clear()
    request.session["user_id"] = user.id
    return _user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, _: User = Depends(get_current_user)) -> Response:
    """Clear the current signed browser session."""
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AuthenticatedUserRead)
def current_user(user: User = Depends(get_current_user)) -> AuthenticatedUserRead:
    """Return the safe profile of the account represented by this session."""
    return _user_response(user)


@router.post("/change-password", response_model=AuthenticatedUserRead)
def update_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuthenticatedUserRead:
    """Replace the current password and clear the first-login requirement."""
    settings = get_settings()
    try:
        changed_user = change_password(
            db,
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            rounds=settings.password_hash_rounds,
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return _user_response(changed_user)
