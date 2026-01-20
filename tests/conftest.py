"""
Pytest configuration and fixtures for Socratic AI Backend tests.

Provides:
- SQLite in-memory database for isolated tests
- Test client with dependency overrides
- Mock LLM client with deterministic responses
- Sample data fixtures
"""
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.api.deps import get_db, get_current_user, get_optional_user
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import (
    GenerationSession,
    GenerationSource,
    MCQOption,
    Question,
    QuestionType,
    RefinementEntry,
    User,
)
from app.schemas.questions import (
    GeneratedQuestion,
    GeneratedQuestions,
    MCQOptionSchema,
    QuestionAnalysis,
    RefinedQuestion,
    SimilarityAnalysis,
)


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""

    def get_session_override():
        yield session

    app.dependency_overrides[get_db] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_superuser")
def test_superuser_fixture(session: Session) -> User:
    """Create a test superuser."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="inactive_user")
def inactive_user_fixture(session: Session) -> User:
    """Create an inactive test user."""
    user = User(
        email="inactive@example.com",
        hashed_password=get_password_hash("inactivepassword123"),
        full_name="Inactive User",
        is_active=False,
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_token")
def auth_token_fixture(test_user: User) -> str:
    """Create an authentication token for test user."""
    return create_access_token(
        subject=str(test_user.id),
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture(name="superuser_token")
def superuser_token_fixture(test_superuser: User) -> str:
    """Create an authentication token for superuser."""
    return create_access_token(
        subject=str(test_superuser.id),
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(auth_token: str) -> dict[str, str]:
    """Create authorization headers for requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(name="superuser_headers")
def superuser_headers_fixture(superuser_token: str) -> dict[str, str]:
    """Create authorization headers for superuser requests."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest.fixture(name="authenticated_client")
def authenticated_client_fixture(
    session: Session, test_user: User
) -> Generator[TestClient, None, None]:
    """Create a test client with authenticated user."""

    def get_session_override():
        yield session

    def get_current_user_override():
        return test_user

    def get_optional_user_override():
        return test_user

    app.dependency_overrides[get_db] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[get_optional_user] = get_optional_user_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# =============================================================================
# Question Fixtures
# =============================================================================


@pytest.fixture(name="sample_mcq_options")
def sample_mcq_options_fixture() -> list[dict[str, Any]]:
    """Sample MCQ options."""
    return [
        {"label": "A", "text": "Photosynthesis", "is_correct": True},
        {"label": "B", "text": "Respiration", "is_correct": False},
        {"label": "C", "text": "Fermentation", "is_correct": False},
        {"label": "D", "text": "Digestion", "is_correct": False},
    ]


@pytest.fixture(name="test_question")
def test_question_fixture(
    session: Session, test_user: User, sample_mcq_options: list[dict]
) -> Question:
    """Create a test question."""
    question = Question(
        question_text="What is the process by which plants convert sunlight to food?",
        question_type=QuestionType.MCQ,
        difficulty="medium",
        topic="Biology",
        explanation="Photosynthesis is the process plants use to convert light energy.",
        correct_answer="A",
        options=sample_mcq_options,
        confidence_score=0.95,
        owner_id=test_user.id,
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


@pytest.fixture(name="test_generation_session")
def test_generation_session_fixture(session: Session, test_user: User) -> GenerationSession:
    """Create a test generation session."""
    gen_session = GenerationSession(
        source_type=GenerationSource.TEXT,
        source_content="Sample educational content about photosynthesis.",
        num_questions_requested=5,
        user_id=test_user.id,
    )
    session.add(gen_session)
    session.commit()
    session.refresh(gen_session)
    return gen_session


@pytest.fixture(name="test_question_with_session")
def test_question_with_session_fixture(
    session: Session,
    test_user: User,
    test_generation_session: GenerationSession,
    sample_mcq_options: list[dict],
) -> Question:
    """Create a test question linked to a session."""
    question = Question(
        question_text="What is chlorophyll?",
        question_type=QuestionType.MCQ,
        difficulty="easy",
        topic="Biology",
        explanation="Chlorophyll is the green pigment in plants.",
        correct_answer="B",
        options=sample_mcq_options,
        confidence_score=0.90,
        session_id=test_generation_session.id,
        owner_id=test_user.id,
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


# =============================================================================
# Mock LLM Responses
# =============================================================================


@pytest.fixture(name="mock_generated_questions")
def mock_generated_questions_fixture() -> GeneratedQuestions:
    """Mock response for question generation."""
    return GeneratedQuestions(
        questions=[
            GeneratedQuestion(
                question_text="What is the primary function of chlorophyll?",
                question_type="mcq",
                difficulty="medium",
                topic="Biology",
                explanation="Chlorophyll captures light energy for photosynthesis.",
                options=[
                    MCQOptionSchema(label="A", text="Absorb water", is_correct=False),
                    MCQOptionSchema(label="B", text="Capture light energy", is_correct=True),
                    MCQOptionSchema(label="C", text="Release oxygen", is_correct=False),
                    MCQOptionSchema(label="D", text="Store glucose", is_correct=False),
                ],
                correct_answer="B",
                confidence_score=0.92,
            ),
            GeneratedQuestion(
                question_text="Explain the process of photosynthesis.",
                question_type="open_ended",
                difficulty="medium",
                topic="Biology",
                explanation="Photosynthesis converts CO2 and water to glucose and oxygen.",
                options=None,
                correct_answer="Plants use sunlight to convert CO2 and water into glucose.",
                confidence_score=0.88,
            ),
        ],
        generation_summary="Generated 2 questions on Biology at medium difficulty.",
    )


@pytest.fixture(name="mock_similarity_analysis")
def mock_similarity_analysis_fixture() -> SimilarityAnalysis:
    """Mock response for similarity analysis."""
    return SimilarityAnalysis(
        analysis=QuestionAnalysis(
            topic="Mathematics",
            subtopic="Arithmetic - Multiplication",
            difficulty="easy",
            question_type="mcq",
            key_concepts=["multiplication", "unit price", "total cost"],
            mathematical_operations=["multiplication"],
            format_style="word_problem",
        ),
        variation_suggestions=[
            "Change the items being purchased",
            "Vary the unit price",
            "Use different quantities",
        ],
    )


@pytest.fixture(name="mock_refined_question")
def mock_refined_question_fixture() -> RefinedQuestion:
    """Mock response for question refinement."""
    return RefinedQuestion(
        question_text="What is the main function of chlorophyll in plants?",
        question_type="mcq",
        difficulty="medium",
        topic="Biology",
        explanation="Chlorophyll is essential for capturing light energy.",
        options=[
            MCQOptionSchema(label="A", text="Water absorption", is_correct=False),
            MCQOptionSchema(label="B", text="Light energy capture", is_correct=True),
            MCQOptionSchema(label="C", text="Oxygen release", is_correct=False),
            MCQOptionSchema(label="D", text="Glucose storage", is_correct=False),
        ],
        correct_answer="B",
        changes_made="Rephrased question for clarity",
        confidence_score=0.94,
    )


@pytest.fixture(name="mock_llm_client")
def mock_llm_client_fixture(
    mock_generated_questions: GeneratedQuestions,
    mock_similarity_analysis: SimilarityAnalysis,
    mock_refined_question: RefinedQuestion,
):
    """Create a mock LLM client."""
    mock_client = MagicMock()

    def generate_structured_side_effect(response_model, **kwargs):
        if response_model == GeneratedQuestions:
            return mock_generated_questions
        elif response_model == SimilarityAnalysis:
            return mock_similarity_analysis
        elif response_model == RefinedQuestion:
            return mock_refined_question
        return MagicMock()

    mock_client.generate_structured.side_effect = generate_structured_side_effect
    mock_client.generate_structured_with_context.return_value = mock_refined_question
    mock_client.generate_text.return_value = "Generated text response"

    return mock_client


# =============================================================================
# PDF Fixtures
# =============================================================================


@pytest.fixture(name="sample_pdf_content")
def sample_pdf_content_fixture() -> bytes:
    """Create sample PDF bytes for testing."""
    # Minimal valid PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Photosynthesis is the process by which plants convert light energy into chemical energy. This process occurs in the chloroplasts of plant cells and is essential for life on Earth.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
308
%%EOF"""


@pytest.fixture(name="sample_text_content")
def sample_text_content_fixture() -> str:
    """Sample educational text for question generation."""
    return """
    Photosynthesis is the process by which plants convert light energy into chemical energy.
    During this process, plants absorb carbon dioxide from the air and water from the soil.
    Using sunlight, they convert these raw materials into glucose and oxygen.
    The glucose is used as food by the plant, while oxygen is released as a byproduct.
    Chlorophyll, the green pigment in leaves, plays a crucial role in capturing light energy.
    This process is essential for life on Earth as it produces the oxygen we breathe
    and forms the base of most food chains.
    """


# =============================================================================
# Test Data Helpers
# =============================================================================


@pytest.fixture(name="valid_user_data")
def valid_user_data_fixture() -> dict[str, Any]:
    """Valid user registration data."""
    return {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "full_name": "New User",
    }


@pytest.fixture(name="valid_question_data")
def valid_question_data_fixture() -> dict[str, Any]:
    """Valid question creation data."""
    return {
        "question_text": "What is photosynthesis?",
        "question_type": "mcq",
        "difficulty": "medium",
        "topic": "Biology",
        "explanation": "Photosynthesis is the process plants use to make food.",
        "correct_answer": "A",
        "options": [
            {"label": "A", "text": "Process of making food", "is_correct": True},
            {"label": "B", "text": "Process of breathing", "is_correct": False},
            {"label": "C", "text": "Process of growing", "is_correct": False},
            {"label": "D", "text": "Process of moving", "is_correct": False},
        ],
    }
