"""
NutriAI Health Portal - Documents Router
Handles document upload, listing, status polling, preview, and deletion.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.services.azure_storage_service import upload_document, get_document_url, delete_document, download_document
from app.services.document_intelligence_service import analyze_document

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/documents", tags=["Documents"])
templates = Jinja2Templates(directory="app/templates")

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_openai_client():
    if not settings.AZURE_OPENAI_KEY or not settings.AZURE_OPENAI_ENDPOINT:
        return None
    try:
        from openai import AzureOpenAI
        return AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return None


def fallback_validate_document(ocr_content: str, filename: str) -> dict:
    content_lower = (ocr_content or "").lower() + " " + (filename or "").lower()
    
    # Lab report keywords
    lab_keywords = ["lab", "report", "test", "result", "blood", "urine", "panel", "cholesterol", "glucose", "hemoglobin", "vitamin", "bpm", "mmhg", "patient health metrics"]
    # Prescription keywords
    rx_keywords = ["prescription", "rx", "medication", "mg", "tablet", "capsule", "take", "dosage", "doctor", "signature", "recipe", "pharmacy", "sig:"]
    
    is_lab = any(kw in content_lower for kw in lab_keywords)
    is_rx = any(kw in content_lower for kw in rx_keywords)
    
    if is_lab:
        return {"is_valid": True, "document_type": "lab_report", "error_message": ""}
    elif is_rx:
        return {"is_valid": True, "document_type": "prescription", "error_message": ""}
    else:
        return {
            "is_valid": False,
            "document_type": "other",
            "error_message": "Invalid document. The uploaded file does not appear to be a medical lab report or a doctor's prescription. Please upload a valid document."
        }


def validate_document_with_ai(ocr_content: str, original_filename: str) -> dict:
    import json
    client = get_openai_client()
    
    is_mock = (
        not settings.AZURE_OPENAI_KEY
        or settings.AZURE_OPENAI_KEY == ""
        or "your-" in settings.AZURE_OPENAI_KEY
        or settings.AZURE_OPENAI_KEY.startswith("<")
        or not settings.AZURE_OPENAI_ENDPOINT
        or settings.AZURE_OPENAI_ENDPOINT == ""
        or "your-" in settings.AZURE_OPENAI_ENDPOINT
        or settings.AZURE_OPENAI_ENDPOINT.startswith("<")
    )
    
    if is_mock or not client:
        logger.warning("Azure OpenAI is not configured/configured as mock. Using rule-based validation fallback.")
        return fallback_validate_document(ocr_content, original_filename)
        
    try:
        system_prompt = (
            "You are an AI assistant designed to classify and validate uploaded medical documents for a health portal.\n"
            "Your job is to determine if the document is either:\n"
            "1. A Lab Report (containing lab test results, blood tests, panel results, medical metrics, etc.)\n"
            "2. A Prescription (containing doctor's prescriptions, list of medications, medical instructions, dosage, doctor sign-offs, etc.)\n"
            "3. Irrelevant or invalid (anything else, such as restaurant receipts, personal photos, general articles, books, food recipes, IDs, invoices, etc.)\n\n"
            "You MUST respond with valid JSON in the following exact structure:\n"
            "{\n"
            "    \"is_valid\": true/false,\n"
            "    \"document_type\": \"lab_report\"/\"prescription\"/\"other\",\n"
            "    \"error_message\": \"If not valid, a user-friendly soft error message explaining that the document is invalid and only lab reports or prescriptions are accepted. Otherwise, empty string.\"\n"
            "}"
        )
        
        user_message = (
            f"Filename: {original_filename}\n\n"
            f"Extracted Document Text:\n{ocr_content[:4000]}"
        )
        
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=500,
        )
        
        result = json.loads(response.choices[0].message.content)
        if "is_valid" in result and "document_type" in result:
            return {
                "is_valid": bool(result.get("is_valid")),
                "document_type": result.get("document_type"),
                "error_message": result.get("error_message", "")
            }
    except Exception as e:
        logger.error(f"AI document validation error: {e}. Falling back to rule-based validation.")
        
    return fallback_validate_document(ocr_content, original_filename)


def process_document_ocr(document_id: str, blob_name: str):
    """
    Background task: download blob, run OCR, update database.
    Uses its own DB session since background tasks run outside the request lifecycle.
    """
    from app.database import SessionLocal
    import uuid

    db = SessionLocal()
    try:
        # Download blob content
        document_content = download_document(blob_name)
        logger.info(f"Downloaded blob {blob_name}: {len(document_content)} bytes")

        # Run OCR
        extracted_text = analyze_document(document_content)
        logger.info(f"OCR completed for {document_id}: {len(extracted_text)} characters extracted")

        # Update document record with results
        from app.models.document import Document
        doc_uuid = uuid.UUID(document_id) if isinstance(document_id, str) else document_id
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if document:
            validation = validate_document_with_ai(extracted_text, document.original_filename)
            if validation["is_valid"]:
                document.ocr_content = extracted_text
                document.ocr_status = "completed"
                document.document_type = validation["document_type"]
            else:
                document.ocr_content = validation["error_message"]
                document.ocr_status = "failed"
                document.document_type = "other"
            db.commit()
            logger.info(f"Document {document_id} OCR and validation completed with status: {document.ocr_status}")

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        try:
            from app.models.document import Document
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.ocr_status = "failed"
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


@router.get("", response_class=HTMLResponse)
async def documents_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render the documents management page."""
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return templates.TemplateResponse("documents/index.html", {
        "request": request,
        "user": current_user,
        "documents": documents,
    })


@router.post("/upload")
async def upload_doc(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str = Form("other"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document to Azure Blob Storage and create DB record."""
    # Validate file extension
    file_extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_extension not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
        )

    # Read file content and validate size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        return JSONResponse(
            status_code=400,
            content={"error": "File size exceeds 10MB limit."},
        )

    if len(file_content) == 0:
        return JSONResponse(
            status_code=400,
            content={"error": "File is empty."},
        )

    try:
        # Upload to Azure Blob Storage
        blob_result = upload_document(
            file_content=file_content,
            original_filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )

        # Create document record in database
        document = Document(
            user_id=current_user.id,
            document_type=document_type,
            original_filename=file.filename,
            blob_name=blob_result["blob_name"],
            blob_url=blob_result["blob_url"],
            ocr_status="pending",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        # Run OCR processing in background
        document.ocr_status = "processing"
        db.commit()
        background_tasks.add_task(process_document_ocr, str(document.id), document.blob_name)

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document uploaded successfully.",
                "document_id": str(document.id),
                "status": document.ocr_status,
            },
        )

    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to upload document. Please try again."},
        )


@router.get("/{document_id}/status")
async def document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """JSON endpoint for polling OCR status."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        return JSONResponse(status_code=404, content={"error": "Document not found."})

    return JSONResponse(content={
        "id": str(document.id),
        "ocr_status": document.ocr_status,
    })


@router.get("/{document_id}/preview")
async def document_preview(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Redirect to SAS URL for document preview."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        sas_url = get_document_url(document.blob_name)
        return RedirectResponse(url=sas_url)
    except Exception as e:
        logger.error(f"Error generating preview URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview URL.")


@router.delete("/{document_id}")
async def delete_doc(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document from Blob Storage and database."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        return JSONResponse(status_code=404, content={"error": "Document not found."})

    try:
        # Delete from Azure Blob Storage
        try:
            delete_document(document.blob_name)
        except Exception as e:
            logger.warning(f"Could not delete blob {document.blob_name}: {e}")

        # Delete from database
        db.delete(document)
        db.commit()

        return JSONResponse(content={"message": "Document deleted successfully."})

    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": "Failed to delete document."})
