"""
NutriAI Health Portal - Admin Router
Admin dashboard with system stats, user management, and document overview.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.models.document import Document
from app.models.diet_plan import DietPlan
from app.models.health_log import HealthLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Render the admin dashboard with system stats and user management."""
    # System stats
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_documents = db.query(func.count(Document.id)).scalar()
    total_diet_plans = db.query(func.count(DietPlan.id)).scalar()
    total_health_logs = db.query(func.count(HealthLog.id)).scalar()

    # Document stats by status
    pending_docs = db.query(func.count(Document.id)).filter(Document.ocr_status == "pending").scalar()
    processing_docs = db.query(func.count(Document.id)).filter(Document.ocr_status == "processing").scalar()
    completed_docs = db.query(func.count(Document.id)).filter(Document.ocr_status == "completed").scalar()
    failed_docs = db.query(func.count(Document.id)).filter(Document.ocr_status == "failed").scalar()

    # All users
    users = db.query(User).order_by(User.created_at.desc()).all()

    # Recent documents
    recent_documents = (
        db.query(Document)
        .order_by(Document.uploaded_at.desc())
        .limit(20)
        .all()
    )

    # Get usernames for documents
    user_map = {str(u.id): u.username for u in db.query(User).all()}

    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "user": current_user,
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "total_documents": total_documents,
            "total_diet_plans": total_diet_plans,
            "total_health_logs": total_health_logs,
            "pending_docs": pending_docs,
            "processing_docs": processing_docs,
            "completed_docs": completed_docs,
            "failed_docs": failed_docs,
        },
        "users": users,
        "recent_documents": recent_documents,
        "user_map": user_map,
    })


@router.post("/users/{user_id}/toggle")
async def toggle_user_status(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle a user's active status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found."})

    if str(user.id) == str(current_user.id):
        return JSONResponse(status_code=400, content={"error": "Cannot deactivate your own account."})

    try:
        user.is_active = not user.is_active
        db.commit()
        return JSONResponse(content={
            "message": f"User {'activated' if user.is_active else 'deactivated'} successfully.",
            "is_active": user.is_active,
        })
    except Exception as e:
        logger.error(f"Error toggling user status: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": "Failed to update user status."})
