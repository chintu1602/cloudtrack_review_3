"""
NutriAI Health Portal - Documents Router
Handles document upload, listing, status polling, preview, and deletion.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.services.azure_storage_service import upload_document, get_document_url, delete_document

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/documents", tags=["Documents"])
templates = Jinja2Templates(directory="app/templates")

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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

        # Trigger Function App for OCR processing
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.FUNCTION_APP_URL}/api/process-document",
                    json={
                        "document_id": str(document.id),
                        "blob_name": document.blob_name,
                    },
                    headers={"x-functions-key": settings.FUNCTION_APP_KEY},
                    timeout=10.0,
                )
            # Update status to processing
            document.ocr_status = "processing"
            db.commit()
        except Exception as e:
            logger.warning(f"Could not trigger Function App for OCR: {e}. Document will remain pending.")

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
    document_id: str,
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
    document_id: str,
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
    document_id: str,
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
