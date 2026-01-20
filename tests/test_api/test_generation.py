"""
Tests for document-based question generation routes.

Tests text and PDF generation endpoints.
"""
import io
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.questions import GeneratedQuestions


class TestGenerateFromText:
    """Tests for text-based generation."""

    def test_generate_from_text_success(
        self,
        client: TestClient,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test successful text generation."""
        with patch(
            "app.api.routes.generation.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.generate_from_document.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/generate/from-text",
                json={
                    "content": sample_text_content,
                    "num_questions": 3,
                    "difficulty": "medium",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "questions" in data
            assert len(data["questions"]) > 0
            assert data["source_type"] == "text"

    def test_generate_from_text_with_types(
        self,
        client: TestClient,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test text generation with specific question types."""
        with patch(
            "app.api.routes.generation.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.generate_from_document.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/generate/from-text",
                json={
                    "content": sample_text_content,
                    "num_questions": 2,
                    "question_types": ["mcq"],
                    "difficulty": "easy",
                },
            )

            assert response.status_code == 200

    def test_generate_from_text_with_topic_focus(
        self,
        client: TestClient,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test text generation with topic focus."""
        with patch(
            "app.api.routes.generation.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.generate_from_document.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/generate/from-text",
                json={
                    "content": sample_text_content,
                    "num_questions": 2,
                    "topic_focus": "Chlorophyll",
                },
            )

            assert response.status_code == 200

    def test_generate_from_text_too_short(self, client: TestClient):
        """Test that content too short is rejected."""
        response = client.post(
            "/api/v1/generate/from-text",
            json={
                "content": "Too short",
                "num_questions": 3,
            },
        )

        assert response.status_code == 422  # Validation error

    def test_generate_from_text_too_many_questions(
        self, client: TestClient, sample_text_content: str
    ):
        """Test that too many questions is rejected."""
        response = client.post(
            "/api/v1/generate/from-text",
            json={
                "content": sample_text_content,
                "num_questions": 100,  # More than max (20)
            },
        )

        assert response.status_code == 422

    def test_generate_from_text_authenticated(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test authenticated text generation saves user_id."""
        with patch(
            "app.api.routes.generation.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.generate_from_document.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/generate/from-text",
                json={
                    "content": sample_text_content,
                    "num_questions": 2,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestGenerateFromPDF:
    """Tests for PDF-based generation."""

    def test_generate_from_pdf_success(
        self,
        client: TestClient,
        mock_generated_questions: GeneratedQuestions,
        sample_pdf_content: bytes,
    ):
        """Test successful PDF generation."""
        with patch(
            "app.api.routes.generation.get_question_generator"
        ) as mock_get_generator, patch(
            "app.api.routes.generation.extract_text_from_pdf"
        ) as mock_extract, patch(
            "app.api.routes.generation.get_pdf_info"
        ) as mock_info:
            mock_generator = MagicMock()
            mock_generator.generate_from_document.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            mock_extract.return_value = "Extracted PDF content about photosynthesis and chlorophyll."
            mock_info.return_value = {"page_count": 3, "is_encrypted": False}

            files = {"file": ("test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
            data = {"num_questions": 3, "difficulty": "medium"}

            response = client.post(
                "/api/v1/generate/from-pdf",
                files=files,
                data=data,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["source_type"] == "pdf"
            assert result["page_count"] == 3

    def test_generate_from_pdf_wrong_file_type(self, client: TestClient):
        """Test that non-PDF files are rejected."""
        files = {"file": ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")}
        data = {"num_questions": 3}

        response = client.post(
            "/api/v1/generate/from-pdf",
            files=files,
            data=data,
        )

        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_generate_from_pdf_invalid_content(
        self, client: TestClient
    ):
        """Test that invalid PDF content is handled."""
        with patch(
            "app.api.routes.generation.extract_text_from_pdf"
        ) as mock_extract:
            from app.services.pdf_parser import PDFParserError
            mock_extract.side_effect = PDFParserError("Cannot parse PDF")

            files = {"file": ("bad.pdf", io.BytesIO(b"Invalid PDF content"), "application/pdf")}
            data = {"num_questions": 3}

            response = client.post(
                "/api/v1/generate/from-pdf",
                files=files,
                data=data,
            )

            assert response.status_code == 422
            assert "Failed to parse PDF" in response.json()["detail"]

    def test_generate_from_pdf_insufficient_text(
        self, client: TestClient, sample_pdf_content: bytes
    ):
        """Test PDF with too little extractable text."""
        with patch(
            "app.api.routes.generation.extract_text_from_pdf"
        ) as mock_extract:
            mock_extract.return_value = "Too short"  # Less than 50 chars

            files = {"file": ("test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
            data = {"num_questions": 3}

            response = client.post(
                "/api/v1/generate/from-pdf",
                files=files,
                data=data,
            )

            assert response.status_code == 422
            assert "insufficient text" in response.json()["detail"].lower()


class TestGetGenerationSession:
    """Tests for retrieving generation sessions."""

    def test_get_session_success(
        self,
        authenticated_client: TestClient,
        test_generation_session,
        test_question_with_session,
    ):
        """Test getting a generation session by ID."""
        response = authenticated_client.get(
            f"/api/v1/generate/session/{test_generation_session.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == str(test_generation_session.id)
        assert len(data["questions"]) >= 1

    def test_get_session_not_found(self, authenticated_client: TestClient):
        """Test getting non-existent session."""
        import uuid
        fake_id = uuid.uuid4()

        response = authenticated_client.get(f"/api/v1/generate/session/{fake_id}")

        assert response.status_code == 404

    def test_get_session_unauthorized(
        self,
        client: TestClient,
        test_generation_session,
        superuser_headers: dict,
    ):
        """Test accessing session owned by another user."""
        response = client.get(
            f"/api/v1/generate/session/{test_generation_session.id}",
            headers=superuser_headers,
        )

        assert response.status_code == 403
