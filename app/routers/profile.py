"""
NutriAI Health Portal - Profile Router
Handles user profile updates, medical conditions, and food allergy management.
"""

import logging

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, PatientProfile, FoodAllergy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Profile"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the profile page with user info, medical conditions, and allergies."""
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    allergies = db.query(FoodAllergy).filter(FoodAllergy.user_id == current_user.id).all()

    return templates.TemplateResponse("profile/index.html", {
        "request": request,
        "user": current_user,
        "profile": profile,
        "allergies": allergies,
    })


@router.post("/update")
async def update_profile(
    request: Request,
    full_name: str = Form(...),
    age: int = Form(None),
    gender: str = Form(None),
    weight: float = Form(None),
    height: float = Form(None),
    blood_type: str = Form(None),
    emergency_contact: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update personal information."""
    try:
        current_user.full_name = full_name
        if age:
            current_user.age = age
        if gender:
            current_user.gender = gender
        if weight:
            current_user.weight = weight
        if height:
            current_user.height = height

        # Update or create patient profile
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not profile:
            profile = PatientProfile(
                user_id=current_user.id,
                medical_conditions=[],
                dietary_preferences=[],
            )
            db.add(profile)

        if blood_type:
            profile.blood_type = blood_type
        if emergency_contact:
            profile.emergency_contact = emergency_contact

        db.commit()
        return RedirectResponse(url="/profile?success=profile_updated", status_code=302)

    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        db.rollback()
        return RedirectResponse(url="/profile?error=update_failed", status_code=302)


@router.post("/medical")
async def update_medical(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update medical conditions and dietary preferences."""
    try:
        form_data = await request.form()
        medical_conditions = form_data.getlist("medical_conditions")
        dietary_preferences = form_data.getlist("dietary_preferences")

        profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not profile:
            profile = PatientProfile(
                user_id=current_user.id,
                medical_conditions=[],
                dietary_preferences=[],
            )
            db.add(profile)

        profile.medical_conditions = list(medical_conditions)
        profile.dietary_preferences = list(dietary_preferences)

        db.commit()
        return RedirectResponse(url="/profile?success=medical_updated", status_code=302)

    except Exception as e:
        logger.error(f"Error updating medical info: {e}")
        db.rollback()
        return RedirectResponse(url="/profile?error=update_failed", status_code=302)


@router.post("/allergy")
async def add_allergy(
    allergen_name: str = Form(...),
    severity: str = Form("moderate"),
    notes: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new food allergy."""
    try:
        if severity not in ("mild", "moderate", "severe"):
            return RedirectResponse(url="/profile?error=invalid_severity", status_code=302)

        allergy = FoodAllergy(
            user_id=current_user.id,
            allergen_name=allergen_name.strip(),
            severity=severity,
            notes=notes.strip() if notes else None,
        )
        db.add(allergy)
        db.commit()
        return RedirectResponse(url="/profile?success=allergy_added", status_code=302)

    except Exception as e:
        logger.error(f"Error adding allergy: {e}")
        db.rollback()
        return RedirectResponse(url="/profile?error=add_failed", status_code=302)


@router.delete("/allergy/{allergy_id}")
async def delete_allergy(
    allergy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a food allergy with ownership verification."""
    allergy = db.query(FoodAllergy).filter(
        FoodAllergy.id == allergy_id,
        FoodAllergy.user_id == current_user.id,
    ).first()

    if not allergy:
        return JSONResponse(status_code=404, content={"error": "Allergy not found."})

    try:
        db.delete(allergy)
        db.commit()
        return JSONResponse(content={"message": "Allergy removed successfully."})
    except Exception as e:
        logger.error(f"Error deleting allergy: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": "Failed to remove allergy."})
