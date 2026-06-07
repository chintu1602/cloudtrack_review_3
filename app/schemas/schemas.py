"""
NutriAI Health Portal - Pydantic Schemas
Request/response validation models for all API endpoints.
"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============================================================
# Auth Schemas
# ============================================================

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: str = Field(..., max_length=255)
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., max_length=255)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = Field(None, max_length=20)
    weight: Optional[float] = Field(None, ge=1, le=500)
    height: Optional[float] = Field(None, ge=30, le=300)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""
    id: UUID
    email: str
    username: str
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    auth_type: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Profile Schemas
# ============================================================

class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, max_length=255)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[str] = Field(None, max_length=20)
    weight: Optional[float] = Field(None, ge=1, le=500)
    height: Optional[float] = Field(None, ge=30, le=300)
    blood_type: Optional[str] = Field(None, max_length=10)
    emergency_contact: Optional[str] = Field(None, max_length=255)


class MedicalUpdate(BaseModel):
    """Schema for updating medical conditions and dietary preferences."""
    medical_conditions: List[str] = []
    dietary_preferences: List[str] = []


class AllergyCreate(BaseModel):
    """Schema for adding a food allergy."""
    allergen_name: str = Field(..., max_length=255)
    severity: str = Field(..., pattern="^(mild|moderate|severe)$")
    notes: Optional[str] = None


# ============================================================
# Document Schemas
# ============================================================

class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: UUID
    document_type: str
    original_filename: str
    blob_url: str
    ocr_status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DocumentStatusResponse(BaseModel):
    """Schema for document OCR status polling."""
    id: UUID
    ocr_status: str


# ============================================================
# Diet Plan Schemas
# ============================================================

class DietPlanGenerateRequest(BaseModel):
    """Schema for generating a diet plan."""
    document_ids: List[str]
    additional_notes: Optional[str] = None


class FoodItem(BaseModel):
    """Individual food item in diet plan."""
    food_name: str
    reason: str
    portion_size: Optional[str] = None
    timing: Optional[str] = None
    frequency: Optional[str] = None


class FoodToAvoid(BaseModel):
    """Food to avoid in diet plan."""
    food_name: str
    reason: str
    risk_level: Optional[str] = None


class NutritionalGuidelines(BaseModel):
    """Nutritional guidelines from diet plan."""
    daily_calories: Optional[int] = None
    protein_grams: Optional[int] = None
    carbs_grams: Optional[int] = None
    fats_grams: Optional[int] = None
    fiber_grams: Optional[int] = None
    water_liters: Optional[float] = None


class DietPlanResponse(BaseModel):
    """Schema for diet plan response."""
    id: UUID
    plan_title: str
    plan_summary: Optional[str] = None
    foods_to_eat: list = []
    foods_to_avoid: list = []
    weekly_meal_plan: dict = {}
    nutritional_guidelines: dict = {}
    allergy_notes: list = []
    additional_recommendations: list = []
    generated_at: datetime
    is_active: bool
    document_ids: list = []

    class Config:
        from_attributes = True


# ============================================================
# Health Tracker Schemas
# ============================================================

class HealthLogCreate(BaseModel):
    """Schema for creating a health log entry."""
    log_date: date
    weight: Optional[float] = Field(None, ge=1, le=500)
    blood_sugar_fasting: Optional[float] = Field(None, ge=0, le=1000)
    blood_sugar_postprandial: Optional[float] = Field(None, ge=0, le=1000)
    blood_pressure_systolic: Optional[int] = Field(None, ge=0, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=0, le=300)
    notes: Optional[str] = None


class MealLogCreate(BaseModel):
    """Schema for creating a meal log entry."""
    meal_date: date
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    food_items: List[str] = []
    calories_estimate: Optional[int] = Field(None, ge=0, le=10000)
    notes: Optional[str] = None


class HealthLogResponse(BaseModel):
    """Schema for health log response."""
    id: UUID
    log_date: date
    weight: Optional[float] = None
    blood_sugar_fasting: Optional[float] = None
    blood_sugar_postprandial: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# Notification Schema
# ============================================================

class NotificationItem(BaseModel):
    """Schema for a notification item."""
    id: str
    message: str
    type: str = "info"
    is_read: bool = False
    created_at: datetime
