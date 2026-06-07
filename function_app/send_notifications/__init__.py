"""
NutriAI Health Portal - Send Notifications Azure Function
Timer-triggered function that runs every hour to:
1. Find documents stuck in 'processing' state for >30 minutes and mark as failed.
2. Clean up any stale notification states.
"""

import logging
import os
from datetime import datetime, timedelta

import azure.functions as func
from sqlalchemy import create_engine, Column, String, Text, DateTime, Enum
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL", "")

Base = declarative_base()


class Document(Base):
    """Minimal Document model matching the web app's database schema."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    original_filename = Column(String(500), nullable=False)
    blob_name = Column(String(500), nullable=False, unique=True)
    blob_url = Column(String(1000), nullable=False)
    ocr_content = Column(Text, nullable=True)
    ocr_status = Column(
        Enum("pending", "processing", "completed", "failed", name="ocr_status_enum", create_type=False),
        default="pending",
        nullable=False,
    )
    uploaded_at = Column(DateTime, nullable=False)


def get_db_session():
    """Create a database session."""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def main(timer: func.TimerRequest) -> None:
    """
    Periodic cleanup function that runs every hour.
    
    - Finds documents stuck in 'processing' for >30 minutes and marks them as 'failed'.
    - Finds documents stuck in 'pending' for >1 hour and marks them as 'failed'.
    """
    utc_timestamp = datetime.utcnow().isoformat()

    if timer.past_due:
        logger.info("The timer is past due!")

    logger.info(f"Send Notifications function ran at {utc_timestamp}")

    db = get_db_session()
    try:
        # Find documents stuck in 'processing' for more than 30 minutes
        thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
        stuck_processing = (
            db.query(Document)
            .filter(
                Document.ocr_status == "processing",
                Document.uploaded_at < thirty_min_ago,
            )
            .all()
        )

        for doc in stuck_processing:
            logger.warning(
                f"Document {doc.id} ({doc.original_filename}) stuck in processing. "
                f"Uploaded at {doc.uploaded_at}. Marking as failed."
            )
            doc.ocr_status = "failed"

        # Find documents stuck in 'pending' for more than 1 hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stuck_pending = (
            db.query(Document)
            .filter(
                Document.ocr_status == "pending",
                Document.uploaded_at < one_hour_ago,
            )
            .all()
        )

        for doc in stuck_pending:
            logger.warning(
                f"Document {doc.id} ({doc.original_filename}) stuck in pending. "
                f"Uploaded at {doc.uploaded_at}. Marking as failed."
            )
            doc.ocr_status = "failed"

        total_updated = len(stuck_processing) + len(stuck_pending)
        if total_updated > 0:
            db.commit()
            logger.info(f"Updated {total_updated} stuck documents to 'failed' status.")
        else:
            logger.info("No stuck documents found.")

    except Exception as e:
        logger.error(f"Error in send_notifications function: {e}")
        db.rollback()

    finally:
        db.close()
