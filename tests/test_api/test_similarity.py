"""
Tests for similarity-based question generation routes.

Tests analyze and generate similar endpoints.
"""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.questions import GeneratedQuestions, SimilarityAnalysis


class TestAnalyzeQuestion:
    """Tests for the analyze endpoint."""

    def test_analyze_question_success(
        self,
        client: TestClient,
        mock_similarity_analysis: SimilarityAnalysis,
    ):
        """Test successful question analysis."""
        with patch(
            "app.api.routes.similarity.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.analyze_question.return_value = mock_similarity_analysis
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/similar/analyze",
                json={
                    "question_text": "A store sells apples for $2 each. If Maria buys 5 apples, how much does she pay?",
                    "options": [
                        {"label": "A", "text": "$7", "is_correct": False},
                        {"label": "B", "text": "$10", "is_correct": True},
                    ],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "topic" in data
            assert "subtopic" in data
            assert "key_concepts" in data
            assert "variation_suggestions" in data

    def test_analyze_question_without_options(
        self,
        client: TestClient,
        mock_similarity_analysis: SimilarityAnalysis,
    ):
        """Test analyzing an open-ended question."""
        with patch(
            "app.api.routes.similarity.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.analyze_question.return_value = mock_similarity_analysis
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/similar/analyze",
                json={
                    "question_text": "Explain how photosynthesis works in plants.",
                },
            )

            assert response.status_code == 200

    def test_analyze_question_too_short(self, client: TestClient):
        """Test that short questions are rejected."""
        response = client.post(
            "/api/v1/similar/analyze",
            json={"question_text": "Short?"},  # Less than 10 chars
        )

        assert response.status_code == 422


class TestGenerateSimilar:
    """Tests for generating similar questions."""

    def test_generate_similar_success(
        self,
        client: TestClient,
        mock_similarity_analysis: SimilarityAnalysis,
        mock_generated_questions: GeneratedQuestions,
    ):
        """Test successful similar question generation."""
        with patch(
            "app.api.routes.similarity.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.analyze_question.return_value = mock_similarity_analysis
            mock_generator.generate_similar.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/similar/generate",
                json={
                    "question_text": "A store sells apples for $2 each. If Maria buys 5 apples, how much does she pay?",
                    "num_similar": 3,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "original_analysis" in data
            assert "similar_questions" in data
            assert "generation_summary" in data

    def test_generate_similar_with_options(
        self,
        client: TestClient,
        mock_similarity_analysis: SimilarityAnalysis,
        mock_generated_questions: GeneratedQuestions,
    ):
        """Test generating similar questions with MCQ options."""
        with patch(
            "app.api.routes.similarity.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.analyze_question.return_value = mock_similarity_analysis
            mock_generator.generate_similar.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/similar/generate",
                json={
                    "question_text": "What is 2 + 2?",
                    "options": [
                        {"label": "A", "text": "3", "is_correct": False},
                        {"label": "B", "text": "4", "is_correct": True},
                    ],
                    "num_similar": 2,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["similar_questions"]) > 0

    def test_generate_similar_authenticated(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_similarity_analysis: SimilarityAnalysis,
        mock_generated_questions: GeneratedQuestions,
    ):
        """Test authenticated similar generation."""
        with patch(
            "app.api.routes.similarity.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.analyze_question.return_value = mock_similarity_analysis
            mock_generator.generate_similar.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/similar/generate",
                json={
                    "question_text": "This is a test question that is long enough.",
                    "num_similar": 2,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_generate_similar_too_many(
        self, client: TestClient
    ):
        """Test that too many similar questions is rejected."""
        response = client.post(
            "/api/v1/similar/generate",
            json={
                "question_text": "This is a test question that is long enough.",
                "num_similar": 100,  # More than max (10)
            },
        )

        assert response.status_code == 422


class TestBatchGenerate:
    """Tests for batch similarity generation."""

    def test_batch_generate_success(
        self,
        client: TestClient,
        mock_similarity_analysis: SimilarityAnalysis,
        mock_generated_questions: GeneratedQuestions,
    ):
        """Test batch generation with multiple questions."""
        with patch(
            "app.api.routes.similarity.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.analyze_question.return_value = mock_similarity_analysis
            mock_generator.generate_similar.return_value = mock_generated_questions
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/similar/batch",
                json=[
                    {
                        "question_text": "First test question that is long enough.",
                        "num_similar": 2,
                    },
                    {
                        "question_text": "Second test question that is long enough.",
                        "num_similar": 2,
                    },
                ],
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_batch_generate_too_many_questions(self, client: TestClient):
        """Test that batch is limited to 5 questions."""
        questions = [
            {
                "question_text": f"Test question {i} that is long enough for validation.",
                "num_similar": 2,
            }
            for i in range(10)  # More than 5
        ]

        response = client.post(
            "/api/v1/similar/batch",
            json=questions,
        )

        assert response.status_code == 400
        assert "limited to 5" in response.json()["detail"].lower()

    def test_batch_generate_empty(self, client: TestClient):
        """Test batch generation with empty list."""
        response = client.post(
            "/api/v1/similar/batch",
            json=[],
        )

        assert response.status_code == 200
        assert response.json() == []
