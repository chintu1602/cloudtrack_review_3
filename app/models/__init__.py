"""
NutriAI Health Portal - Models Package
Import all models to ensure they are registered with SQLAlchemy Base.
"""

from app.models.user import User, PatientProfile, FoodAllergy
from app.models.document import Document
from app.models.diet_plan import DietPlan
from app.models.health_log import HealthLog, MealLog

__all__ = [
    "User",
    "PatientProfile",
    "FoodAllergy",
    "Document",
    "DietPlan",
    "HealthLog",
    "MealLog",
]
