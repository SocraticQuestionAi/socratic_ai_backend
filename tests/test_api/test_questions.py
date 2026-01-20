"""
Tests for question CRUD routes.

Tests listing, getting, updating, and deleting questions.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.models import Question, User


class TestListQuestions:
    """Tests for listing questions."""

    def test_list_questions_empty(self, authenticated_client: TestClient):
        """Test listing questions when user has none."""
        response = authenticated_client.get("/api/v1/questions/")

        assert response.status_code == 200
        data = response.json()
        assert data["questions"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    def test_list_questions_with_data(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test listing questions with existing data."""
        response = authenticated_client.get("/api/v1/questions/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) >= 1
        assert data["total"] >= 1

    def test_list_questions_pagination(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test pagination parameters."""
        response = authenticated_client.get(
            "/api/v1/questions/",
            params={"page": 1, "per_page": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10

    def test_list_questions_filter_by_type(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test filtering by question type."""
        response = authenticated_client.get(
            "/api/v1/questions/",
            params={"question_type": "mcq"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned questions should be MCQ
        for q in data["questions"]:
            assert q["question_type"] == "mcq"

    def test_list_questions_filter_by_difficulty(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test filtering by difficulty."""
        response = authenticated_client.get(
            "/api/v1/questions/",
            params={"difficulty": "medium"},
        )

        assert response.status_code == 200
        data = response.json()
        for q in data["questions"]:
            assert q["difficulty"] == "medium"

    def test_list_questions_filter_by_topic(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test filtering by topic."""
        response = authenticated_client.get(
            "/api/v1/questions/",
            params={"topic": "Biology"},
        )

        assert response.status_code == 200
        # Should return questions with "Biology" in topic

    def test_list_questions_requires_auth(self, client: TestClient):
        """Test that listing requires authentication."""
        response = client.get("/api/v1/questions/")

        assert response.status_code == 401


class TestGetQuestion:
    """Tests for getting a single question."""

    def test_get_question_success(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test getting a question by ID."""
        response = authenticated_client.get(f"/api/v1/questions/{test_question.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_question.id)
        assert data["question_text"] == test_question.question_text

    def test_get_question_not_found(self, authenticated_client: TestClient):
        """Test getting a non-existent question."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f"/api/v1/questions/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_question_unauthorized(
        self, client: TestClient, test_question: Question
    ):
        """Test getting question without authentication."""
        response = client.get(f"/api/v1/questions/{test_question.id}")

        assert response.status_code == 401

    def test_get_question_wrong_owner(
        self, client: TestClient, test_question: Question, superuser_headers: dict
    ):
        """Test getting question owned by another user."""
        # Superuser trying to access another user's question
        response = client.get(
            f"/api/v1/questions/{test_question.id}",
            headers=superuser_headers,
        )

        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]


class TestUpdateQuestion:
    """Tests for updating questions."""

    def test_update_question_success(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test updating a question."""
        update_data = {
            "question_text": "Updated question text?",
            "difficulty": "hard",
        }

        response = authenticated_client.patch(
            f"/api/v1/questions/{test_question.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question_text"] == "Updated question text?"
        assert data["difficulty"] == "hard"

    def test_update_question_options(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test updating question options."""
        new_options = [
            {"label": "A", "text": "New A", "is_correct": False},
            {"label": "B", "text": "New B", "is_correct": True},
            {"label": "C", "text": "New C", "is_correct": False},
            {"label": "D", "text": "New D", "is_correct": False},
        ]

        response = authenticated_client.patch(
            f"/api/v1/questions/{test_question.id}",
            json={"options": new_options, "correct_answer": "B"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["correct_answer"] == "B"

    def test_update_question_not_found(self, authenticated_client: TestClient):
        """Test updating non-existent question."""
        fake_id = uuid.uuid4()
        response = authenticated_client.patch(
            f"/api/v1/questions/{fake_id}",
            json={"question_text": "Updated"},
        )

        assert response.status_code == 404

    def test_update_question_unauthorized(
        self, client: TestClient, test_question: Question, superuser_headers: dict
    ):
        """Test updating question owned by another user."""
        response = client.patch(
            f"/api/v1/questions/{test_question.id}",
            json={"question_text": "Hacked!"},
            headers=superuser_headers,
        )

        assert response.status_code == 403


class TestDeleteQuestion:
    """Tests for deleting questions."""

    def test_delete_question_success(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test deleting a question."""
        response = authenticated_client.delete(
            f"/api/v1/questions/{test_question.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["question_id"] == str(test_question.id)

        # Verify it's actually deleted
        get_response = authenticated_client.get(
            f"/api/v1/questions/{test_question.id}"
        )
        assert get_response.status_code == 404

    def test_delete_question_not_found(self, authenticated_client: TestClient):
        """Test deleting non-existent question."""
        fake_id = uuid.uuid4()
        response = authenticated_client.delete(f"/api/v1/questions/{fake_id}")

        assert response.status_code == 404

    def test_delete_question_unauthorized(
        self, client: TestClient, test_question: Question, superuser_headers: dict
    ):
        """Test deleting question owned by another user."""
        response = client.delete(
            f"/api/v1/questions/{test_question.id}",
            headers=superuser_headers,
        )

        assert response.status_code == 403


class TestBulkDelete:
    """Tests for bulk delete endpoint."""

    def test_bulk_delete_success(
        self, authenticated_client: TestClient, test_question: Question
    ):
        """Test bulk deleting questions."""
        response = authenticated_client.post(
            "/api/v1/questions/bulk-delete",
            json=[str(test_question.id)],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["count"] == 1

    def test_bulk_delete_nonexistent_ids(self, authenticated_client: TestClient):
        """Test bulk delete with non-existent IDs."""
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        response = authenticated_client.post(
            "/api/v1/questions/bulk-delete",
            json=fake_ids,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0  # No questions deleted

    def test_bulk_delete_empty_list(self, authenticated_client: TestClient):
        """Test bulk delete with empty list."""
        response = authenticated_client.post(
            "/api/v1/questions/bulk-delete",
            json=[],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0

    def test_bulk_delete_mixed_ownership(
        self,
        authenticated_client: TestClient,
        test_question: Question,
    ):
        """Test bulk delete with some owned and some not owned."""
        # One owned, one fake
        response = authenticated_client.post(
            "/api/v1/questions/bulk-delete",
            json=[str(test_question.id), str(uuid.uuid4())],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1  # Only owned one deleted
