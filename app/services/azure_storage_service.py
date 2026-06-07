"""
NutriAI Health Portal - Azure Blob Storage Service
Handles document upload, download URL generation with SAS tokens, and deletion.
"""

import logging
import uuid
from datetime import datetime, timedelta

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_blob_service_client() -> BlobServiceClient:
    """Create a BlobServiceClient from connection string."""
    return BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)


def upload_document(file_content: bytes, original_filename: str, content_type: str) -> dict:
    """
    Upload a document to Azure Blob Storage.
    
    Args:
        file_content: Raw bytes of the file
        original_filename: Original name of the uploaded file
        content_type: MIME type of the file
        
    Returns:
        dict with blob_name and blob_url
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(settings.AZURE_STORAGE_CONTAINER_NAME)

        # Generate unique blob name
        file_extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
        blob_name = f"{uuid.uuid4()}.{file_extension}"

        # Upload blob
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            file_content,
            content_settings={
                "content_type": content_type,
            },
            overwrite=True,
        )

        blob_url = blob_client.url
        logger.info(f"Document uploaded successfully: {blob_name}")

        return {
            "blob_name": blob_name,
            "blob_url": blob_url,
        }

    except Exception as e:
        logger.error(f"Error uploading document to Azure Storage: {e}")
        raise


def get_document_url(blob_name: str) -> str:
    """
    Generate a SAS URL for a blob with 1-hour expiry.
    
    Args:
        blob_name: Name of the blob in storage
        
    Returns:
        SAS URL string with read permissions valid for 1 hour
    """
    try:
        blob_service_client = get_blob_service_client()
        account_name = blob_service_client.account_name
        account_key = blob_service_client.credential.account_key

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=settings.AZURE_STORAGE_CONTAINER_NAME,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1),
        )

        sas_url = f"https://{account_name}.blob.core.windows.net/{settings.AZURE_STORAGE_CONTAINER_NAME}/{blob_name}?{sas_token}"
        return sas_url

    except Exception as e:
        logger.error(f"Error generating SAS URL for blob {blob_name}: {e}")
        raise


def delete_document(blob_name: str) -> bool:
    """
    Delete a blob from Azure Storage.
    
    Args:
        blob_name: Name of the blob to delete
        
    Returns:
        True if deleted successfully
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(settings.AZURE_STORAGE_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        logger.info(f"Document deleted successfully: {blob_name}")
        return True

    except Exception as e:
        logger.error(f"Error deleting document from Azure Storage: {e}")
        raise


def download_document(blob_name: str) -> bytes:
    """
    Download a blob's content from Azure Storage.
    
    Args:
        blob_name: Name of the blob to download
        
    Returns:
        Raw bytes of the blob content
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(settings.AZURE_STORAGE_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(blob_name)
        download_stream = blob_client.download_blob()
        content = download_stream.readall()
        logger.info(f"Document downloaded successfully: {blob_name}")
        return content

    except Exception as e:
        logger.error(f"Error downloading document from Azure Storage: {e}")
        raise
