"""
PDF Parser Service - Extract text from PDF documents.

Supports multiple extraction methods for reliability.
"""
import io
from pathlib import Path

import fitz  # PyMuPDF
from pypdf import PdfReader


class PDFParserError(Exception):
    """Exception raised for PDF parsing errors."""

    pass


def extract_text_pymupdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF using PyMuPDF (fitz).

    This is the primary method - faster and handles more PDF types.

    Args:
        pdf_content: Raw PDF bytes

    Returns:
        Extracted text content
    """
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

        doc.close()
        return "\n\n".join(text_parts)
    except Exception as e:
        raise PDFParserError(f"PyMuPDF extraction failed: {e}")


def extract_text_pypdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF using pypdf.

    Fallback method for compatibility.

    Args:
        pdf_content: Raw PDF bytes

    Returns:
        Extracted text content
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_content))
        text_parts = []

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

        return "\n\n".join(text_parts)
    except Exception as e:
        raise PDFParserError(f"pypdf extraction failed: {e}")


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF with automatic fallback.

    Tries PyMuPDF first, falls back to pypdf if needed.

    Args:
        pdf_content: Raw PDF bytes

    Returns:
        Extracted text content

    Raises:
        PDFParserError: If all extraction methods fail
    """
    # Try PyMuPDF first (better quality)
    try:
        text = extract_text_pymupdf(pdf_content)
        if text.strip():
            return text
    except PDFParserError:
        pass

    # Fallback to pypdf
    try:
        text = extract_text_pypdf(pdf_content)
        if text.strip():
            return text
    except PDFParserError:
        pass

    raise PDFParserError("Failed to extract text from PDF using all available methods")


def get_pdf_info(pdf_content: bytes) -> dict:
    """
    Get metadata about a PDF document.

    Args:
        pdf_content: Raw PDF bytes

    Returns:
        Dictionary with PDF metadata
    """
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        info = {
            "page_count": len(doc),
            "metadata": doc.metadata,
            "is_encrypted": doc.is_encrypted,
        }
        doc.close()
        return info
    except Exception as e:
        return {"error": str(e)}


def chunk_text(text: str, max_chunk_size: int = 4000, overlap: int = 200) -> list[str]:
    """
    Split text into chunks for processing within context limits.

    Args:
        text: Full text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Character overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chunk_size

        # Try to break at paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + max_chunk_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                for sep in [". ", ".\n", "! ", "? "]:
                    sent_break = text.rfind(sep, start, end)
                    if sent_break > start + max_chunk_size // 2:
                        end = sent_break + len(sep)
                        break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return chunks
