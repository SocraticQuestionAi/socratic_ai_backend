"""
Tests for interactive question refinement routes (Canvas flow).

Tests refinement and conversation management endpoints.
"""
import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models import Question, User
from app.schemas.questions import RefinedQuestion, MCQOptionSchema


class TestRefineQuestion:
    """Tests for the refine endpoint."""

    def test_refine_with_question_state(
        self,
        client: TestClient,
        mock_refined_question: RefinedQuestion,
    ):
        """Test refinement with direct question state."""
        with patch(
            "app.api.routes.refinement.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.refine_question.return_value = mock_refined_question
            mock_get_generator.return_value = mock_generator

            response = client.post(
                "/api/v1/refine/refine",
                json={
                    "question_state": {
                        "question_text": "What is photosynthesis?",
                        "question_type": "mcq",
                        "difficulty": "medium",
                        "topic": "Biology",
                        "explanation": "Photosynthesis is how plants make food.",
                        "correct_answer": "A",
                        "options": [
                            {"label": "A", "text": "Making food", "is_correct": True},
                            {"label": "B", "text": "Breathing", "is_correct": False},
                        ],
                    },
                    "instruction": "Make the question easier",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "conversation_id" in data
            assert "refined_question" in data
            assert "changes_made" in data
            assert "turn_number" in data
            assert data["turn_number"] == 1

    def test_refine_with_question_id(
        self,
        authenticated_client: TestClient,
        test_question: Question,
        mock_refined_question: RefinedQuestion,
    ):
        """Test refinement with existing question ID."""
        with patch(
            "app.api.routes.refinement.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.refine_question.return_value = mock_refined_question
            mock_get_generator.return_value = mock_generator

            response = authenticated_client.post(
                "/api/v1/refine/refine",
                json={
                    "question_id": str(test_question.id),
                    "instruction": "Change the difficulty to hard",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "conversation_id" in data

    def test_refine_question_not_found(
        self,
        client: TestClient,
    ):
        """Test refinement with non-existent question ID."""
        fake_id = str(uuid.uuid4())

        response = client.post(
            "/api/v1/refine/refine",
            json={
                "question_id": fake_id,
                "instruction": "Make it easier",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_refine_no_question_provided(self, client: TestClient):
        """Test refinement without question_id or question_state."""
        response = client.post(
            "/api/v1/refine/refine",
            json={
                "instruction": "Make it easier",
            },
        )

        assert response.status_code == 400
        assert "Provide either" in response.json()["detail"]

    def test_refine_instruction_too_short(self, client: TestClient):
        """Test refinement with too short instruction."""
        response = client.post(
            "/api/v1/refine/refine",
            json={
                "question_state": {
                    "question_text": "Test question?",
                    "question_type": "mcq",
                    "difficulty": "easy",
                    "explanation": "Test",
                    "correct_answer": "A",
                },
                "instruction": "ok",  # Too short (< 5 chars)
            },
        )

        assert response.status_code == 422

    def test_refine_continue_conversation(
        self,
        client: TestClient,
        mock_refined_question: RefinedQuestion,
    ):
        """Test continuing a refinement conversation."""
        with patch(
            "app.api.routes.refinement.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.refine_question.return_value = mock_refined_question
            mock_get_generator.return_value = mock_generator

            # First refinement
            response1 = client.post(
                "/api/v1/refine/refine",
                json={
                    "question_state": {
                        "question_text": "What is 2+2?",
                        "question_type": "mcq",
                        "difficulty": "easy",
                        "explanation": "Basic math",
                        "correct_answer": "B",
                        "options": [
                            {"label": "A", "text": "3", "is_correct": False},
                            {"label": "B", "text": "4", "is_correct": True},
                        ],
                    },
                    "instruction": "Make harder",
                },
            )

            conversation_id = response1.json()["conversation_id"]

            # Continue conversation
            response2 = client.post(
                "/api/v1/refine/refine",
                json={
                    "conversation_id": conversation_id,
                    "instruction": "Now make it even harder",
                },
            )

            assert response2.status_code == 200
            data = response2.json()
            assert data["conversation_id"] == conversation_id
            assert data["turn_number"] == 2


class TestGetConversation:
    """Tests for getting conversation history."""

    def test_get_conversation_success(
        self,
        client: TestClient,
        mock_refined_question: RefinedQuestion,
    ):
        """Test getting conversation history."""
        with patch(
            "app.api.routes.refinement.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.refine_question.return_value = mock_refined_question
            mock_get_generator.return_value = mock_generator

            # Create a conversation first
            response = client.post(
                "/api/v1/refine/refine",
                json={
                    "question_state": {
                        "question_text": "Test question text here?",
                        "question_type": "mcq",
                        "difficulty": "medium",
                        "explanation": "Test explanation",
                        "correct_answer": "A",
                    },
                    "instruction": "Improve this question",
                },
            )

            conversation_id = response.json()["conversation_id"]

            # Get the conversation
            response = client.get(f"/api/v1/refine/conversation/{conversation_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == conversation_id
            assert "turns" in data
            assert "current_state" in data

    def test_get_conversation_not_found(self, client: TestClient):
        """Test getting non-existent conversation."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/refine/conversation/{fake_id}")

        assert response.status_code == 404


class TestResetConversation:
    """Tests for resetting conversations."""

    def test_reset_conversation_success(
        self,
        client: TestClient,
        mock_refined_question: RefinedQuestion,
    ):
        """Test resetting a conversation."""
        with patch(
            "app.api.routes.refinement.get_question_generator"
        ) as mock_get_generator:
            mock_generator = MagicMock()
            mock_generator.refine_question.return_value = mock_refined_question
            mock_get_generator.return_value = mock_generator

            # Create a conversation
            response = client.post(
                "/api/v1/refine/refine",
                json={
                    "question_state": {
                        "question_text": "Test question for reset?",
                        "question_type": "mcq",
                        "difficulty": "easy",
                        "explanation": "Test",
                        "correct_answer": "A",
                    },
                    "instruction": "Refine this",
                },
            )

            conversation_id = response.json()["conversation_id"]

            # Reset it
            response = client.post(
                f"/api/v1/refine/conversation/{conversation_id}/reset"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "reset"

            # Verify it's deleted
            get_response = client.get(
                f"/api/v1/refine/conversation/{conversation_id}"
            )
            assert get_response.status_code == 404

    def test_reset_conversation_not_found(self, client: TestClient):
        """Test resetting non-existent conversation."""
        fake_id = uuid.uuid4()

        response = client.post(f"/api/v1/refine/conversation/{fake_id}/reset")

        assert response.status_code == 404


class TestGetRefinementHistory:
    """Tests for getting question refinement history."""

    def test_get_history_success(
        self,
        authenticated_client: TestClient,
        test_question: Question,
    ):
        """Test getting refinement history for a question."""
        response = authenticated_client.get(
            f"/api/v1/refine/question/{test_question.id}/history"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_history_question_not_found(
        self, authenticated_client: TestClient
    ):
        """Test getting history for non-existent question."""
        fake_id = uuid.uuid4()

        response = authenticated_client.get(
            f"/api/v1/refine/question/{fake_id}/history"
        )

        assert response.status_code == 404

    def test_get_history_unauthorized(
        self,
        client: TestClient,
        test_question: Question,
        superuser_headers: dict,
    ):
        """Test getting history for question owned by another user."""
        response = client.get(
            f"/api/v1/refine/question/{test_question.id}/history",
            headers=superuser_headers,
        )

        assert response.status_code == 403

    def test_get_history_requires_auth(
        self, client: TestClient, test_question: Question
    ):
        """Test that getting history requires authentication."""
        response = client.get(
            f"/api/v1/refine/question/{test_question.id}/history"
        )

        assert response.status_code == 401
