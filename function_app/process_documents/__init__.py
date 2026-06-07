"""
NutriAI Health Portal - Process Documents Azure Function
HTTP-triggered function that performs OCR on uploaded medical documents
using Azure Document Intelligence, then updates the database record.
"""

import logging
import os
import json

import azure.functions as func
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from sqlalchemy import create_engine, Column, String, Text, Enum
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL", "")
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "health-documents")
AZURE_DOC_INTELLIGENCE_ENDPOINT = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
AZURE_DOC_INTELLIGENCE_KEY = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")

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


def get_db_session():
    """Create a database session."""
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def download_blob(blob_name: str) -> bytes:
    """Download a blob's content from Azure Storage."""
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
    blob_client = container_client.get_blob_client(blob_name)
    download_stream = blob_client.download_blob()
    return download_stream.readall()


def run_ocr(document_content: bytes) -> str:
    """Run Azure Document Intelligence OCR on document content."""
    client = DocumentAnalysisClient(
        endpoint=AZURE_DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DOC_INTELLIGENCE_KEY),
    )

    poller = client.begin_analyze_document(
        model_id="prebuilt-read",
        document=document_content,
    )
    result = poller.result()

    # Extract all text content
    extracted_text = ""
    for page in result.pages:
        for line in page.lines:
            extracted_text += line.content + "\n"
        extracted_text += "\n"

    # Extract tables
    if result.tables:
        extracted_text += "\n--- Tables ---\n"
        for table_idx, table in enumerate(result.tables):
            extracted_text += f"\nTable {table_idx + 1}:\n"
            current_row = -1
            row_data = []
            for cell in table.cells:
                if cell.row_index != current_row:
                    if row_data:
                        extracted_text += " | ".join(row_data) + "\n"
                    row_data = []
                    current_row = cell.row_index
                row_data.append(cell.content)
            if row_data:
                extracted_text += " | ".join(row_data) + "\n"

    return extracted_text.strip()


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Process a document: download from Blob Storage, run OCR, update database.

    Expected JSON body:
        {
            "document_id": "uuid-string",
            "blob_name": "uuid.pdf"
        }
    """
    logger.info("Process Documents function triggered.")

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    document_id = req_body.get("document_id")
    blob_name = req_body.get("blob_name")

    if not document_id or not blob_name:
        return func.HttpResponse(
            json.dumps({"error": "Missing document_id or blob_name"}),
            status_code=400,
            mimetype="application/json",
        )

    db = get_db_session()
    try:
        # Find the document record
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return func.HttpResponse(
                json.dumps({"error": "Document not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Update status to processing
        document.ocr_status = "processing"
        db.commit()
        logger.info(f"Processing document {document_id}: {blob_name}")

        # Download blob content
        document_content = download_blob(blob_name)
        logger.info(f"Downloaded blob {blob_name}: {len(document_content)} bytes")

        # Run OCR
        extracted_text = run_ocr(document_content)
        logger.info(f"OCR completed for {document_id}: {len(extracted_text)} characters extracted")

        # Update document record with results
        document.ocr_content = extracted_text
        document.ocr_status = "completed"
        db.commit()

        return func.HttpResponse(
            json.dumps({
                "status": "completed",
                "document_id": document_id,
                "characters_extracted": len(extracted_text),
            }),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        # Mark as failed in database
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.ocr_status = "failed"
                db.commit()
        except Exception:
            db.rollback()

        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

    finally:
        db.close()
