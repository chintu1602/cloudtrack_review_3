"""
NutriAI Health Portal - Diet Plans Router
Handles diet plan generation, history, detail view, and PDF download.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, FoodAllergy
from app.models.document import Document
from app.models.diet_plan import DietPlan
from app.services.diet_plan_service import create_diet_plan, get_diet_plans, get_diet_plan_detail, generate_diet_plan_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diet-plan", tags=["Diet Plans"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def generate_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the diet plan generation page."""
    # Get completed documents for selection
    documents = (
        db.query(Document)
        .filter(
            Document.user_id == current_user.id,
            Document.ocr_status == "completed",
        )
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    # Get user's allergies for reminder
    allergies = db.query(FoodAllergy).filter(FoodAllergy.user_id == current_user.id).all()

    return templates.TemplateResponse("diet_plan/generate.html", {
        "request": request,
        "user": current_user,
        "documents": documents,
        "allergies": allergies,
    })


@router.post("/generate")
async def generate_plan(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a diet plan from selected documents."""
    form_data = await request.form()
    document_ids = form_data.getlist("document_ids")
    additional_notes = form_data.get("additional_notes", "")

    if not document_ids:
        return JSONResponse(
            status_code=400,
            content={"error": "Please select at least one document."},
        )

    try:
        plan = create_diet_plan(
            db=db,
            user=current_user,
            document_ids=document_ids,
            additional_notes=additional_notes,
        )

        if not plan:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to generate diet plan. Please try again."},
            )

        return JSONResponse(content={
            "message": "Diet plan generated successfully!",
            "plan_id": str(plan.id),
            "plan_title": plan.plan_title,
            "plan_summary": plan.plan_summary,
            "foods_to_eat": plan.foods_to_eat,
            "foods_to_avoid": plan.foods_to_avoid,
            "weekly_meal_plan": plan.weekly_meal_plan,
            "nutritional_guidelines": plan.nutritional_guidelines,
            "allergy_notes": plan.allergy_notes,
            "additional_recommendations": plan.additional_recommendations or [],
        })

    except Exception as e:
        logger.error(f"Error generating diet plan: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "An error occurred while generating the diet plan."},
        )


@router.get("/history", response_class=HTMLResponse)
async def history_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the diet plan history page."""
    plans = get_diet_plans(db, current_user.id)
    return templates.TemplateResponse("diet_plan/history.html", {
        "request": request,
        "user": current_user,
        "plans": plans,
    })


@router.get("/{plan_id}", response_class=HTMLResponse)
async def plan_detail(
    plan_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View a specific diet plan detail."""
    plan = get_diet_plan_detail(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found.")

    return templates.TemplateResponse("diet_plan/generate.html", {
        "request": request,
        "user": current_user,
        "documents": [],
        "allergies": [],
        "existing_plan": plan,
    })


@router.get("/{plan_id}/pdf")
async def download_pdf(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and download a diet plan as PDF."""
    plan = get_diet_plan_detail(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Diet plan not found.")

    try:
        pdf_bytes = generate_diet_plan_pdf(plan)
        filename = f"diet_plan_{plan.generated_at.strftime('%Y%m%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF.")
