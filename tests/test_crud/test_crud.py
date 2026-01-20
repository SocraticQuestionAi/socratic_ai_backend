"""
Tests for CRUD operations.

Tests User, Question, and GenerationSession CRUD functions.
"""
import uuid

import pytest
from sqlmodel import Session

from app import crud
from app.models import (
    GenerationSessionCreate,
    GenerationSource,
    Question,
    QuestionCreate,
    QuestionType,
    User,
    UserCreate,
    UserUpdate,
)


class TestUserCRUD:
    """Tests for User CRUD operations."""

    def test_create_user(self, session: Session):
        """Test creating a new user."""
        user_create = UserCreate(
            email="newuser@example.com",
            password="securepassword123",
            full_name="New User",
        )

        user = crud.create_user(session=session, user_create=user_create)

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.hashed_password != "securepassword123"  # Password should be hashed

    def test_create_user_minimal(self, session: Session):
        """Test creating a user with minimal fields."""
        user_create = UserCreate(
            email="minimal@example.com",
            password="password123",
        )

        user = crud.create_user(session=session, user_create=user_create)

        assert user.email == "minimal@example.com"
        assert user.full_name is None

    def test_get_user_by_email_exists(self, session: Session, test_user: User):
        """Test getting a user by email that exists."""
        found_user = crud.get_user_by_email(session=session, email=test_user.email)

        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.email == test_user.email

    def test_get_user_by_email_not_exists(self, session: Session):
        """Test getting a user by email that doesn't exist."""
        found_user = crud.get_user_by_email(session=session, email="nonexistent@example.com")

        assert found_user is None

    def test_update_user_email(self, session: Session, test_user: User):
        """Test updating a user's email."""
        update_data = UserUpdate(email="updated@example.com")

        updated_user = crud.update_user(session=session, db_user=test_user, user_in=update_data)

        assert updated_user.email == "updated@example.com"
        assert updated_user.full_name == test_user.full_name  # Unchanged

    def test_update_user_password(self, session: Session, test_user: User):
        """Test updating a user's password."""
        old_hash = test_user.hashed_password
        update_data = UserUpdate(password="newpassword456")

        updated_user = crud.update_user(session=session, db_user=test_user, user_in=update_data)

        assert updated_user.hashed_password != old_hash
        assert updated_user.hashed_password != "newpassword456"  # Should be hashed

    def test_update_user_multiple_fields(self, session: Session, test_user: User):
        """Test updating multiple user fields at once."""
        update_data = UserUpdate(
            full_name="Updated Name",
            is_active=False,
        )

        updated_user = crud.update_user(session=session, db_user=test_user, user_in=update_data)

        assert updated_user.full_name == "Updated Name"
        assert updated_user.is_active is False

    def test_authenticate_valid_credentials(self, session: Session, test_user: User):
        """Test authentication with valid credentials."""
        # test_user fixture has password "testpassword123"
        authenticated = crud.authenticate(
            session=session,
            email=test_user.email,
            password="testpassword123",
        )

        assert authenticated is not None
        assert authenticated.id == test_user.id

    def test_authenticate_invalid_password(self, session: Session, test_user: User):
        """Test authentication with invalid password."""
        authenticated = crud.authenticate(
            session=session,
            email=test_user.email,
            password="wrongpassword",
        )

        assert authenticated is None

    def test_authenticate_invalid_email(self, session: Session):
        """Test authentication with non-existent email."""
        authenticated = crud.authenticate(
            session=session,
            email="nonexistent@example.com",
            password="anypassword",
        )

        assert authenticated is None

    def test_authenticate_user_alias(self, session: Session, test_user: User):
        """Test that authenticate_user is an alias for authenticate."""
        # Both should work identically
        result1 = crud.authenticate(
            session=session,
            email=test_user.email,
            password="testpassword123",
        )
        result2 = crud.authenticate_user(
            session=session,
            email=test_user.email,
            password="testpassword123",
        )

        assert result1.id == result2.id


class TestGenerationSessionCRUD:
    """Tests for GenerationSession CRUD operations."""

    def test_create_generation_session(self, session: Session, test_user: User):
        """Test creating a generation session."""
        session_create = GenerationSessionCreate(
            source_type="text",
            source_content="Test content for generation",
        )

        gen_session = crud.create_generation_session(
            session=session,
            session_in=session_create,
            user_id=test_user.id,
        )

        assert gen_session.id is not None
        assert gen_session.source_type == "text"
        assert gen_session.source_content == "Test content for generation"
        assert gen_session.user_id == test_user.id

    def test_get_generation_session_exists(
        self, session: Session, test_user: User, test_generation_session
    ):
        """Test getting a generation session that exists."""
        found = crud.get_generation_session(
            session=session,
            session_id=test_generation_session.id,
        )

        assert found is not None
        assert found.id == test_generation_session.id

    def test_get_generation_session_not_exists(self, session: Session):
        """Test getting a generation session that doesn't exist."""
        fake_id = uuid.uuid4()
        found = crud.get_generation_session(session=session, session_id=fake_id)

        assert found is None

    def test_get_sessions_by_user(self, session: Session, test_user: User):
        """Test getting all sessions for a user."""
        # Create multiple sessions
        for i in range(3):
            session_create = GenerationSessionCreate(
                source_type="text",
                source_content=f"Content {i}",
            )
            crud.create_generation_session(
                session=session,
                session_in=session_create,
                user_id=test_user.id,
            )

        sessions = crud.get_sessions_by_user(session=session, user_id=test_user.id)

        assert len(sessions) == 3

    def test_get_sessions_by_user_with_pagination(self, session: Session, test_user: User):
        """Test pagination for user sessions."""
        # Create 5 sessions
        for i in range(5):
            session_create = GenerationSessionCreate(
                source_type="text",
                source_content=f"Content {i}",
            )
            crud.create_generation_session(
                session=session,
                session_in=session_create,
                user_id=test_user.id,
            )

        # Get first 2
        first_page = crud.get_sessions_by_user(
            session=session, user_id=test_user.id, skip=0, limit=2
        )
        assert len(first_page) == 2

        # Get next 2
        second_page = crud.get_sessions_by_user(
            session=session, user_id=test_user.id, skip=2, limit=2
        )
        assert len(second_page) == 2

        # Get last one
        third_page = crud.get_sessions_by_user(
            session=session, user_id=test_user.id, skip=4, limit=2
        )
        assert len(third_page) == 1

    def test_get_sessions_by_user_empty(self, session: Session, test_user: User):
        """Test getting sessions for user with no sessions."""
        # test_user has no sessions yet in this test
        other_user_id = uuid.uuid4()
        sessions = crud.get_sessions_by_user(session=session, user_id=other_user_id)

        assert sessions == []


class TestQuestionCRUD:
    """Tests for Question CRUD operations."""

    def test_create_question(self, session: Session):
        """Test creating a question."""
        question_create = QuestionCreate(
            question_text="What is the capital of France?",
            question_type=QuestionType.MCQ,
            difficulty="easy",
            topic="Geography",
            explanation="Paris is the capital city of France.",
            correct_answer="A",
            options=[
                {"label": "A", "text": "Paris", "is_correct": True},
                {"label": "B", "text": "London", "is_correct": False},
                {"label": "C", "text": "Berlin", "is_correct": False},
                {"label": "D", "text": "Madrid", "is_correct": False},
            ],
        )

        question = crud.create_question(session=session, question_in=question_create)

        assert question.id is not None
        assert question.question_text == "What is the capital of France?"
        assert question.question_type == QuestionType.MCQ
        assert question.correct_answer == "A"

    def test_create_question_with_session(
        self, session: Session, test_generation_session
    ):
        """Test creating a question linked to a session."""
        question_create = QuestionCreate(
            question_text="What is 2+2?",
            question_type=QuestionType.MCQ,
            difficulty="easy",
            topic="Math",
            explanation="Basic addition",
            correct_answer="B",
        )

        question = crud.create_question(
            session=session,
            question_in=question_create,
            session_id=test_generation_session.id,
        )

        assert question.session_id == test_generation_session.id

    def test_create_question_open_ended(self, session: Session):
        """Test creating an open-ended question."""
        question_create = QuestionCreate(
            question_text="Explain photosynthesis in your own words.",
            question_type=QuestionType.OPEN_ENDED,
            difficulty="medium",
            topic="Biology",
            explanation="Photosynthesis is the process by which plants convert sunlight...",
            correct_answer="Plants use sunlight to convert CO2 and water into glucose.",
        )

        question = crud.create_question(session=session, question_in=question_create)

        assert question.question_type == QuestionType.OPEN_ENDED
        assert question.options is None

    def test_create_questions_bulk(self, session: Session, test_generation_session):
        """Test bulk question creation."""
        questions_data = [
            QuestionCreate(
                question_text=f"Question {i}",
                question_type=QuestionType.MCQ,
                difficulty="easy",
                topic="Test",
                explanation=f"Explanation {i}",
                correct_answer="A",
            )
            for i in range(5)
        ]

        questions = crud.create_questions_bulk(
            session=session,
            questions_in=questions_data,
            session_id=test_generation_session.id,
        )

        assert len(questions) == 5
        for q in questions:
            assert q.session_id == test_generation_session.id

    def test_get_question_exists(self, session: Session, test_question: Question):
        """Test getting a question that exists."""
        found = crud.get_question(session=session, question_id=test_question.id)

        assert found is not None
        assert found.id == test_question.id
        assert found.question_text == test_question.question_text

    def test_get_question_not_exists(self, session: Session):
        """Test getting a question that doesn't exist."""
        fake_id = uuid.uuid4()
        found = crud.get_question(session=session, question_id=fake_id)

        assert found is None

    def test_get_questions_by_session(
        self, session: Session, test_generation_session, test_question_with_session
    ):
        """Test getting all questions for a session."""
        questions = crud.get_questions_by_session(
            session=session,
            session_id=test_generation_session.id,
        )

        assert len(questions) >= 1
        assert any(q.id == test_question_with_session.id for q in questions)

    def test_get_questions_by_session_empty(self, session: Session):
        """Test getting questions for a session with no questions."""
        fake_session_id = uuid.uuid4()
        questions = crud.get_questions_by_session(
            session=session,
            session_id=fake_session_id,
        )

        assert questions == []

    def test_update_question(self, session: Session, test_question: Question):
        """Test updating a question."""
        update_data = {
            "question_text": "Updated question text?",
            "difficulty": "hard",
        }

        updated = crud.update_question(
            session=session,
            db_question=test_question,
            update_data=update_data,
        )

        assert updated.question_text == "Updated question text?"
        assert updated.difficulty == "hard"
        assert updated.topic == test_question.topic  # Unchanged

    def test_update_question_options(self, session: Session, test_question: Question):
        """Test updating question options."""
        new_options = [
            {"label": "A", "text": "New option A", "is_correct": False},
            {"label": "B", "text": "New option B", "is_correct": True},
        ]

        updated = crud.update_question(
            session=session,
            db_question=test_question,
            update_data={"options": new_options, "correct_answer": "B"},
        )

        assert updated.options == new_options
        assert updated.correct_answer == "B"

    def test_delete_question_exists(self, session: Session, test_question: Question):
        """Test deleting a question that exists."""
        question_id = test_question.id

        result = crud.delete_question(session=session, question_id=question_id)

        assert result is True

        # Verify it's deleted
        found = crud.get_question(session=session, question_id=question_id)
        assert found is None

    def test_delete_question_not_exists(self, session: Session):
        """Test deleting a question that doesn't exist."""
        fake_id = uuid.uuid4()

        result = crud.delete_question(session=session, question_id=fake_id)

        assert result is False
