"""
extractor.py — Extract text content from PDF and DOCX resume files.
"""

import os
from PyPDF2 import PdfReader
from docx import Document
from utils import logger


def extract_text_from_pdf(filepath: str) -> str:
    """Extract all text from a PDF file."""
    logger.info("Extracting text from PDF: %s", filepath)
    try:
        reader = PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error("PDF extraction failed for %s: %s", filepath, e)
        raise


def extract_text_from_docx(filepath: str) -> str:
    """Extract all text from a DOCX file."""
    logger.info("Extracting text from DOCX: %s", filepath)
    try:
        doc = Document(filepath)
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception as e:
        logger.error("DOCX extraction failed for %s: %s", filepath, e)
        raise


def extract_text(filepath: str) -> str:
    """Dispatch to the correct extractor based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext == ".docx":
        return extract_text_from_docx(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
