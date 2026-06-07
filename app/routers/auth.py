"""
NutriAI Health Portal - Authentication Router
Handles local login/register, Microsoft Entra ID SSO, and logout.
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.dependencies import get_current_user_optional
from app.services.auth_service import (
    authenticate_user,
    create_user,
    create_access_token,
    get_auth_url,
    acquire_token_by_code,
    get_or_create_entra_user,
)
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, current_user=Depends(get_current_user_optional)):
    """Render the login page."""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "user": None,
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate user with email/password and set JWT cookie."""
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "user": None,
            "error": "Invalid email or password. Please try again.",
        })

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, current_user=Depends(get_current_user_optional)):
    """Render the registration page."""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "user": None,
    })


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str = Form(...),
    age: int = Form(None),
    gender: str = Form(None),
    weight: float = Form(None),
    height: float = Form(None),
    db: Session = Depends(get_db),
):
    """Register a new local user account."""
    errors = []

    if password != confirm_password:
        errors.append("Passwords do not match.")

    if len(password) < 6:
        errors.append("Password must be at least 6 characters.")

    if len(username) < 3:
        errors.append("Username must be at least 3 characters.")

    # Check if email already exists
    if db.query(User).filter(User.email == email).first():
        errors.append("An account with this email already exists.")

    # Check if username already exists
    if db.query(User).filter(User.username == username).first():
        errors.append("This username is already taken.")

    if errors:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "user": None,
            "errors": errors,
            "form_data": {
                "email": email,
                "username": username,
                "full_name": full_name,
                "age": age,
                "gender": gender,
                "weight": weight,
                "height": height,
            },
        })

    try:
        user = create_user(
            db=db,
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            age=age,
            gender=gender,
            weight=weight,
            height=height,
        )

        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
            secure=False,
        )
        return response

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "user": None,
            "errors": ["An error occurred during registration. Please try again."],
        })


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Render the forgot password page."""
    return templates.TemplateResponse("auth/forgot_password.html", {
        "request": request,
        "user": None,
    })


@router.get("/microsoft")
async def microsoft_login():
    """Redirect to Microsoft Entra ID for SSO authentication."""
    try:
        auth_url = get_auth_url()
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Error initiating Microsoft login: {e}")
        return RedirectResponse(url="/auth/login?error=sso_failed")


@router.get("/callback")
async def microsoft_callback(
    request: Request,
    code: str = None,
    error: str = None,
    db: Session = Depends(get_db),
):
    """Handle Microsoft Entra ID OAuth callback."""
    if error:
        logger.error(f"Entra ID callback error: {error}")
        return RedirectResponse(url="/auth/login?error=sso_denied")

    if not code:
        return RedirectResponse(url="/auth/login?error=no_code")

    try:
        token_result = acquire_token_by_code(code)
        if not token_result:
            return RedirectResponse(url="/auth/login?error=token_failed")

        user = get_or_create_entra_user(db, token_result)
        if not user:
            return RedirectResponse(url="/auth/login?error=user_creation_failed")

        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
            secure=False,
        )
        return response

    except Exception as e:
        logger.error(f"Error in Microsoft callback: {e}")
        return RedirectResponse(url="/auth/login?error=callback_failed")


@router.get("/logout")
async def logout():
    """Clear JWT cookie and redirect to landing page."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response
