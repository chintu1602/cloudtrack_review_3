"""
NutriAI Health Portal - Diet Plan Model
AI-generated diet plans with structured nutritional data.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DietPlan(Base):
    """AI-generated diet plan for a patient based on their medical documents."""

    __tablename__ = "diet_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_ids = Column(JSON, default=list)
    plan_title = Column(String(500), nullable=False)
    plan_summary = Column(Text, nullable=True)
    foods_to_eat = Column(JSON, default=list)
    foods_to_avoid = Column(JSON, default=list)
    weekly_meal_plan = Column(JSON, default=dict)
    nutritional_guidelines = Column(JSON, default=dict)
    allergy_notes = Column(JSON, default=list)
    additional_recommendations = Column(JSON, default=list)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="diet_plans")
