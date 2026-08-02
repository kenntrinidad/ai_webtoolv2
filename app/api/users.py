"""User management HTTP routes for admin users."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_management_service

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")


def _require_user(db: Session, user_id: str) -> User:
    user = user_management_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    _require_admin(current_user)
    try:
        return user_management_service.create_user(db, payload)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists") from error


@router.get("", response_model=list[UserRead])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[UserRead]:
    _require_admin(current_user)
    return user_management_service.list_users(db)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    _require_admin(current_user)
    return _require_user(db, user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: str, payload: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    _require_admin(current_user)
    user = _require_user(db, user_id)
    try:
        return user_management_service.update_user(db, user, payload)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists") from error


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    _require_admin(current_user)
    user = _require_user(db, user_id)
    user_management_service.delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
