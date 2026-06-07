"""
NutriAI Health Portal - Azure Document Intelligence Service
Handles OCR processing of medical documents using the prebuilt-read model.
"""

import logging

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_document_analysis_client() -> DocumentAnalysisClient:
    """Create a Document Intelligence analysis client."""
    return DocumentAnalysisClient(
        endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY),
    )


def analyze_document(document_content: bytes) -> str:
    """
    Run OCR on a document using Azure Document Intelligence prebuilt-read model.
    
    Args:
        document_content: Raw bytes of the document
        
    Returns:
        Extracted text content from the document
    """
    try:
        client = get_document_analysis_client()

        poller = client.begin_analyze_document(
            model_id="prebuilt-read",
            document=document_content,
        )
        result = poller.result()

        # Extract all text content from the document
        extracted_text = ""
        for page in result.pages:
            for line in page.lines:
                extracted_text += line.content + "\n"
            extracted_text += "\n"

        # Also extract any key-value pairs and tables
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

        logger.info(f"Document analysis completed. Extracted {len(extracted_text)} characters.")
        return extracted_text.strip()

    except Exception as e:
        logger.error(f"Error analyzing document with Document Intelligence: {e}")
        raise


def analyze_document_from_url(document_url: str) -> str:
    """
    Run OCR on a document from a URL using Azure Document Intelligence.
    
    Args:
        document_url: URL of the document to analyze
        
    Returns:
        Extracted text content from the document
    """
    try:
        client = get_document_analysis_client()

        poller = client.begin_analyze_document_from_url(
            model_id="prebuilt-read",
            document_url=document_url,
        )
        result = poller.result()

        extracted_text = ""
        for page in result.pages:
            for line in page.lines:
                extracted_text += line.content + "\n"
            extracted_text += "\n"

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

        logger.info(f"Document analysis from URL completed. Extracted {len(extracted_text)} characters.")
        return extracted_text.strip()

    except Exception as e:
        logger.error(f"Error analyzing document from URL: {e}")
        raise
