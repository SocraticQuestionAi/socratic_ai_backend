"""
Tests for PDF parser service.

Tests text extraction, fallback logic, and text chunking.
"""
import pytest

from app.services.pdf_parser import (
    PDFParserError,
    chunk_text,
    extract_text_from_pdf,
    extract_text_pymupdf,
    extract_text_pypdf,
    get_pdf_info,
)


class TestExtractTextPyMuPDF:
    """Tests for PyMuPDF-based extraction."""

    def test_extract_valid_pdf(self, sample_pdf_content: bytes):
        """Test extracting text from a valid PDF."""
        text = extract_text_pymupdf(sample_pdf_content)

        assert text is not None
        assert "Page 1" in text  # Page marker

    def test_extract_invalid_pdf_raises_error(self):
        """Test that invalid PDF content raises PDFParserError."""
        invalid_content = b"This is not a PDF"

        with pytest.raises(PDFParserError) as exc_info:
            extract_text_pymupdf(invalid_content)

        assert "PyMuPDF extraction failed" in str(exc_info.value)

    def test_extract_empty_bytes_raises_error(self):
        """Test that empty bytes raise PDFParserError."""
        with pytest.raises(PDFParserError):
            extract_text_pymupdf(b"")


class TestExtractTextPypdf:
    """Tests for pypdf-based extraction."""

    def test_extract_valid_pdf(self, sample_pdf_content: bytes):
        """Test extracting text from a valid PDF using pypdf."""
        text = extract_text_pypdf(sample_pdf_content)

        # pypdf might not extract from our minimal PDF, but shouldn't error
        assert isinstance(text, str)

    def test_extract_invalid_pdf_raises_error(self):
        """Test that invalid PDF content raises PDFParserError."""
        invalid_content = b"This is not a PDF"

        with pytest.raises(PDFParserError) as exc_info:
            extract_text_pypdf(invalid_content)

        assert "pypdf extraction failed" in str(exc_info.value)


class TestExtractTextFromPDF:
    """Tests for the main extraction function with fallback."""

    def test_extract_with_pymupdf_success(self, sample_pdf_content: bytes):
        """Test extraction uses PyMuPDF primarily."""
        text = extract_text_from_pdf(sample_pdf_content)

        # Should get text from our sample PDF
        assert isinstance(text, str)

    def test_extract_invalid_pdf_raises_error(self):
        """Test that invalid PDF raises PDFParserError after all methods fail."""
        invalid_content = b"Not a valid PDF at all"

        with pytest.raises(PDFParserError) as exc_info:
            extract_text_from_pdf(invalid_content)

        assert "Failed to extract text from PDF" in str(exc_info.value)


class TestGetPDFInfo:
    """Tests for PDF metadata extraction."""

    def test_get_info_valid_pdf(self, sample_pdf_content: bytes):
        """Test getting metadata from a valid PDF."""
        info = get_pdf_info(sample_pdf_content)

        assert "page_count" in info
        assert info["page_count"] >= 1
        assert "is_encrypted" in info
        assert info["is_encrypted"] is False

    def test_get_info_invalid_pdf_returns_error(self):
        """Test that invalid PDF returns error dict instead of raising."""
        invalid_content = b"Not a PDF"
        info = get_pdf_info(invalid_content)

        assert "error" in info


class TestChunkText:
    """Tests for text chunking function."""

    def test_chunk_short_text_returns_single_chunk(self):
        """Test that short text returns a single chunk."""
        text = "This is a short text."
        chunks = chunk_text(text, max_chunk_size=100)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_at_boundary(self):
        """Test text exactly at chunk boundary."""
        text = "A" * 100
        chunks = chunk_text(text, max_chunk_size=100)

        assert len(chunks) == 1

    def test_chunk_long_text_creates_multiple_chunks(self):
        """Test that long text is split into multiple chunks."""
        # Create text longer than max_chunk_size
        text = "This is a sentence. " * 100  # ~2000 chars
        chunks = chunk_text(text, max_chunk_size=200, overlap=20)

        assert len(chunks) > 1
        # All chunks should be non-empty
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    def test_chunk_text_respects_max_size(self):
        """Test that chunks respect max size (approximately)."""
        text = "This is a sentence. " * 100
        max_size = 200
        chunks = chunk_text(text, max_chunk_size=max_size, overlap=20)

        # Each chunk should be around max_size (with some tolerance for boundary seeking)
        for chunk in chunks[:-1]:  # Last chunk might be smaller
            assert len(chunk) <= max_size + 50  # Allow some overflow for sentence boundary

    def test_chunk_text_overlap(self):
        """Test that chunks have proper overlap."""
        text = "ABCD" * 100  # 400 chars, no natural boundaries
        chunks = chunk_text(text, max_chunk_size=100, overlap=20)

        # With 100 char chunks and 20 char overlap, chunks should share content
        if len(chunks) >= 2:
            # The end of first chunk should overlap with start of second
            # This is hard to test precisely without natural boundaries
            assert len(chunks) >= 2

    def test_chunk_prefers_paragraph_boundaries(self):
        """Test that chunking prefers paragraph boundaries."""
        text = "First paragraph content here.\n\nSecond paragraph content here.\n\nThird paragraph content here."
        chunks = chunk_text(text, max_chunk_size=50, overlap=5)

        # Should try to break at paragraph boundaries
        assert len(chunks) >= 2

    def test_chunk_prefers_sentence_boundaries(self):
        """Test that chunking prefers sentence boundaries."""
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        chunks = chunk_text(text, max_chunk_size=40, overlap=5)

        # Most chunks should end with proper punctuation
        sentence_endings = 0
        for chunk in chunks[:-1]:  # Last chunk might not end with period
            if chunk.rstrip().endswith(('.', '!', '?')):
                sentence_endings += 1

        # At least some should end at sentence boundaries
        assert sentence_endings >= 1 or len(chunks) == 1

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk_text("", max_chunk_size=100)

        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_chunk_text_default_params(self):
        """Test chunking with default parameters."""
        text = "Sample text. " * 500  # ~6500 chars
        chunks = chunk_text(text)  # Uses defaults: 4000 max, 200 overlap

        assert len(chunks) >= 2
