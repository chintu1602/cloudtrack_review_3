"""
NutriAI Health Portal - Main Application Entry Point
FastAPI application with Jinja2 templates, static files, and all routers.
"""

import logging
from datetime import date, timedelta

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import get_settings
from app.database import engine, Base, get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models.user import User, FoodAllergy
from app.models.document import Document
from app.models.diet_plan import DietPlan
from app.models.health_log import HealthLog

# Import all models to register with Base
from app.models import *

from app.routers import auth, documents, diet_plans, health_tracker, profile, notifications, admin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered diet planning system for patients",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(diet_plans.router)
app.include_router(health_tracker.router)
app.include_router(profile.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    logger.info("Starting NutriAI Health Portal...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down NutriAI Health Portal...")


# ============================================================
# Landing Page
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request, current_user=Depends(get_current_user_optional)):
    """Render the landing page."""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "user": None,
    })


# ============================================================
# Dashboard
# ============================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the dashboard with user statistics and recent activity."""
    # Stats
    total_documents = db.query(func.count(Document.id)).filter(
        Document.user_id == current_user.id
    ).scalar()

    total_diet_plans = db.query(func.count(DietPlan.id)).filter(
        DietPlan.user_id == current_user.id
    ).scalar()

    total_health_logs = db.query(func.count(HealthLog.id)).filter(
        HealthLog.user_id == current_user.id
    ).scalar()

    total_allergies = db.query(func.count(FoodAllergy.id)).filter(
        FoodAllergy.user_id == current_user.id
    ).scalar()

    # Recent diet plan
    recent_plan = (
        db.query(DietPlan)
        .filter(DietPlan.user_id == current_user.id)
        .order_by(DietPlan.generated_at.desc())
        .first()
    )

    # Recent documents
    recent_documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .limit(5)
        .all()
    )

    # Notification count
    pending_docs = db.query(func.count(Document.id)).filter(
        Document.user_id == current_user.id,
        Document.ocr_status.in_(["pending", "processing", "failed"]),
    ).scalar()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "stats": {
            "total_documents": total_documents,
            "total_diet_plans": total_diet_plans,
            "total_health_logs": total_health_logs,
            "total_allergies": total_allergies,
        },
        "recent_plan": recent_plan,
        "recent_documents": recent_documents,
        "notification_count": pending_docs,
    })


# ============================================================
# Help Page
# ============================================================

@app.get("/help", response_class=HTMLResponse)
async def help_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
):
    """Render the help page."""
    return templates.TemplateResponse("help.html", {
        "request": request,
        "user": current_user,
    })
