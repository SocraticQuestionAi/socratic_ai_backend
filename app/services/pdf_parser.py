"""
PDF Parser Service - Extract text from PDF documents.

Supports multiple extraction methods for reliability.
Also supports converting PDF pages to images for direct LLM processing.
"""
import base64
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
    errors = []

    # Try PyMuPDF first (better quality)
    try:
        text = extract_text_pymupdf(pdf_content)
        if text.strip():
            return text
        errors.append("PyMuPDF: extracted but no text content (possibly scanned/image PDF)")
    except PDFParserError as e:
        errors.append(str(e))

    # Fallback to pypdf
    try:
        text = extract_text_pypdf(pdf_content)
        if text.strip():
            return text
        errors.append("pypdf: extracted but no text content (possibly scanned/image PDF)")
    except PDFParserError as e:
        errors.append(str(e))

    # Check if it's likely a scanned PDF
    error_detail = "; ".join(errors)
    if "no text content" in error_detail:
        raise PDFParserError(
            "PDF appears to be scanned or image-based. Please use a PDF with selectable text, "
            "or use the text input option instead."
        )

    raise PDFParserError(f"Failed to extract text: {error_detail}")


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


def pdf_to_images(pdf_content: bytes, max_pages: int = 10, dpi: int = 150) -> list[dict]:
    """
    Convert PDF pages to base64-encoded images for direct LLM processing.

    Args:
        pdf_content: Raw PDF bytes
        max_pages: Maximum number of pages to convert (to manage token limits)
        dpi: Resolution for rendering (higher = better quality but larger size)

    Returns:
        List of dicts with 'page', 'base64', and 'mime_type' keys

    Raises:
        PDFParserError: If conversion fails
    """
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        images = []

        # Limit pages to prevent token overflow
        num_pages = min(len(doc), max_pages)

        for page_num in range(num_pages):
            page = doc[page_num]

            # Render page to image
            # Matrix for scaling: 150 DPI = 150/72 = ~2.08x zoom
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")

            # Encode to base64
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")

            images.append({
                "page": page_num + 1,
                "base64": img_base64,
                "mime_type": "image/png",
            })

        doc.close()

        if not images:
            raise PDFParserError("PDF has no pages")

        return images

    except Exception as e:
        if isinstance(e, PDFParserError):
            raise
        raise PDFParserError(f"Failed to convert PDF to images: {e}")
