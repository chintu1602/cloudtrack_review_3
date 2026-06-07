"""
NutriAI Health Portal - Health Tracker Router
Handles health log entries, meal logging, and chart data.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.health_log import HealthLog, MealLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health-tracker", tags=["Health Tracker"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def tracker_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the health tracker page with forms and chart data."""
    # Get recent health logs (30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    health_logs = (
        db.query(HealthLog)
        .filter(
            HealthLog.user_id == current_user.id,
            HealthLog.log_date >= thirty_days_ago,
        )
        .order_by(HealthLog.log_date.asc())
        .all()
    )

    # Get recent meal logs
    meal_logs = (
        db.query(MealLog)
        .filter(
            MealLog.user_id == current_user.id,
            MealLog.meal_date >= thirty_days_ago,
        )
        .order_by(MealLog.meal_date.desc(), MealLog.created_at.desc())
        .limit(20)
        .all()
    )

    # Prepare chart data
    chart_data = {
        "labels": [log.log_date.strftime("%m/%d") for log in health_logs],
        "weight": [log.weight for log in health_logs],
        "blood_sugar_fasting": [log.blood_sugar_fasting for log in health_logs],
        "blood_sugar_postprandial": [log.blood_sugar_postprandial for log in health_logs],
        "bp_systolic": [log.blood_pressure_systolic for log in health_logs],
        "bp_diastolic": [log.blood_pressure_diastolic for log in health_logs],
    }

    return templates.TemplateResponse("health_tracker/index.html", {
        "request": request,
        "user": current_user,
        "health_logs": health_logs,
        "meal_logs": meal_logs,
        "chart_data": chart_data,
        "today": date.today().isoformat(),
    })


@router.post("/log")
async def add_health_log(
    request: Request,
    log_date: str = Form(...),
    weight: float = Form(None),
    blood_sugar_fasting: float = Form(None),
    blood_sugar_postprandial: float = Form(None),
    blood_pressure_systolic: int = Form(None),
    blood_pressure_diastolic: int = Form(None),
    notes: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a health log entry."""
    try:
        parsed_date = date.fromisoformat(log_date)

        health_log = HealthLog(
            user_id=current_user.id,
            log_date=parsed_date,
            weight=weight,
            blood_sugar_fasting=blood_sugar_fasting,
            blood_sugar_postprandial=blood_sugar_postprandial,
            blood_pressure_systolic=blood_pressure_systolic,
            blood_pressure_diastolic=blood_pressure_diastolic,
            notes=notes,
        )
        db.add(health_log)
        db.commit()

        return JSONResponse(content={"message": "Health log saved successfully!"})

    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": "Invalid date format."})
    except Exception as e:
        logger.error(f"Error saving health log: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": "Failed to save health log."})


@router.post("/meal")
async def add_meal_log(
    request: Request,
    meal_date: str = Form(...),
    meal_type: str = Form(...),
    food_items: str = Form(""),
    calories_estimate: int = Form(None),
    notes: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a meal log entry."""
    try:
        parsed_date = date.fromisoformat(meal_date)

        # Parse food items from comma-separated string
        food_list = [item.strip() for item in food_items.split(",") if item.strip()]

        if meal_type not in ("breakfast", "lunch", "dinner", "snack"):
            return JSONResponse(status_code=400, content={"error": "Invalid meal type."})

        meal_log = MealLog(
            user_id=current_user.id,
            meal_date=parsed_date,
            meal_type=meal_type,
            food_items=food_list,
            calories_estimate=calories_estimate,
            notes=notes,
        )
        db.add(meal_log)
        db.commit()

        return JSONResponse(content={"message": "Meal log saved successfully!"})

    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid date format."})
    except Exception as e:
        logger.error(f"Error saving meal log: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": "Failed to save meal log."})


@router.get("/data")
async def chart_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """JSON endpoint for chart data (30 days)."""
    thirty_days_ago = date.today() - timedelta(days=30)
    health_logs = (
        db.query(HealthLog)
        .filter(
            HealthLog.user_id == current_user.id,
            HealthLog.log_date >= thirty_days_ago,
        )
        .order_by(HealthLog.log_date.asc())
        .all()
    )

    return JSONResponse(content={
        "labels": [log.log_date.isoformat() for log in health_logs],
        "weight": [log.weight for log in health_logs],
        "blood_sugar_fasting": [log.blood_sugar_fasting for log in health_logs],
        "blood_sugar_postprandial": [log.blood_sugar_postprandial for log in health_logs],
        "bp_systolic": [log.blood_pressure_systolic for log in health_logs],
        "bp_diastolic": [log.blood_pressure_diastolic for log in health_logs],
    })
