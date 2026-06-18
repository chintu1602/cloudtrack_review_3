"""
NutriAI Health Portal - Shared Dependencies
Authentication dependencies, database session provider, and role checks.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import uuid

from app.database import get_db
from app.config import get_settings
from app.models.user import User

settings = get_settings()


def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    """Get current user from JWT cookie if present, otherwise return None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            return None
        return user
    except JWTError:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current user from JWT cookie. Raises 401 if not authenticated."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"},
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": "/auth/login"},
            )
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": "/auth/login"},
            )
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": "/auth/login"},
            )
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"},
        )


def require_admin(current_user: User = Depends(get_current_user)):
    """Require the current user to have admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required.",
        )
    return current_user
