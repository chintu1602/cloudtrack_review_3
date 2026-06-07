"""
NutriAI Health Portal - Health Log Models
Daily health metrics and meal tracking.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, Integer, Float, Text, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class HealthLog(Base):
    """Daily health metrics log for a patient."""

    __tablename__ = "health_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date = Column(Date, default=date.today, nullable=False)
    weight = Column(Float, nullable=True)
    blood_sugar_fasting = Column(Float, nullable=True)
    blood_sugar_postprandial = Column(Float, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="health_logs")


class MealLog(Base):
    """Individual meal tracking for a patient."""

    __tablename__ = "meal_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meal_date = Column(Date, default=date.today, nullable=False)
    meal_type = Column(
        Enum("breakfast", "lunch", "dinner", "snack", name="meal_type_enum"),
        nullable=False,
    )
    food_items = Column(JSON, default=list)
    calories_estimate = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="meal_logs")
