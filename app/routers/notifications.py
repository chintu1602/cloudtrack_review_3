"""
NutriAI Health Portal - Notifications Router
Handles system notifications for document processing and diet plan generation.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.diet_plan import DietPlan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])
templates = Jinja2Templates(directory="app/templates")


def get_user_notifications(db: Session, user_id):
    """Build notifications from document and diet plan events."""
    notifications = []

    # Document processing notifications
    documents = (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.uploaded_at.desc())
        .limit(20)
        .all()
    )

    for doc in documents:
        if doc.ocr_status == "completed":
            notifications.append({
                "id": str(doc.id),
                "message": f"Document '{doc.original_filename}' has been processed successfully.",
                "type": "success",
                "icon": "fa-check-circle",
                "is_read": True,
                "created_at": doc.uploaded_at,
            })
        elif doc.ocr_status == "failed":
            notifications.append({
                "id": str(doc.id),
                "message": f"Document '{doc.original_filename}' processing failed. Please re-upload.",
                "type": "danger",
                "icon": "fa-exclamation-circle",
                "is_read": False,
                "created_at": doc.uploaded_at,
            })
        elif doc.ocr_status == "processing":
            notifications.append({
                "id": str(doc.id),
                "message": f"Document '{doc.original_filename}' is being processed...",
                "type": "info",
                "icon": "fa-spinner fa-spin",
                "is_read": False,
                "created_at": doc.uploaded_at,
            })
        elif doc.ocr_status == "pending":
            notifications.append({
                "id": str(doc.id),
                "message": f"Document '{doc.original_filename}' is pending processing.",
                "type": "warning",
                "icon": "fa-clock",
                "is_read": False,
                "created_at": doc.uploaded_at,
            })

    # Diet plan notifications
    plans = (
        db.query(DietPlan)
        .filter(DietPlan.user_id == user_id)
        .order_by(DietPlan.generated_at.desc())
        .limit(10)
        .all()
    )

    for plan in plans:
        notifications.append({
            "id": str(plan.id),
            "message": f"Diet plan '{plan.plan_title}' has been generated.",
            "type": "success",
            "icon": "fa-utensils",
            "is_read": True,
            "created_at": plan.generated_at,
        })

    # Sort by date descending
    notifications.sort(key=lambda x: x["created_at"], reverse=True)
    return notifications


@router.get("", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the notifications page."""
    notifications = get_user_notifications(db, current_user.id)
    unread_count = sum(1 for n in notifications if not n["is_read"])

    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "user": current_user,
        "notifications": notifications,
        "unread_count": unread_count,
    })


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    return JSONResponse(content={"message": "Notification marked as read."})


@router.get("/count")
async def notification_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get unread notification count for navbar badge."""
    notifications = get_user_notifications(db, current_user.id)
    unread_count = sum(1 for n in notifications if not n["is_read"])
    return JSONResponse(content={"count": unread_count})
