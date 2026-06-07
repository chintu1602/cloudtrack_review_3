"""
NutriAI Health Portal - Document Model
Medical document uploads with OCR processing status.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    """Medical document uploaded by a patient for OCR processing."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(
        Enum("lab_report", "prescription", "other", name="document_type_enum"),
        default="other",
        nullable=False,
    )
    original_filename = Column(String(500), nullable=False)
    blob_name = Column(String(500), nullable=False, unique=True)
    blob_url = Column(String(1000), nullable=False)
    ocr_content = Column(Text, nullable=True)
    ocr_status = Column(
        Enum("pending", "processing", "completed", "failed", name="ocr_status_enum"),
        default="pending",
        nullable=False,
    )
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="documents")
