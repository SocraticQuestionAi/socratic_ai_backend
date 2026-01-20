"""
Database models and Pydantic schemas for Socratic AI.

Uses SQLModel for unified ORM and validation.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import EmailStr
from sqlmodel import JSON, Column, Field, Relationship, SQLModel


# =============================================================================
# Enums
# =============================================================================


class QuestionType(str, Enum):
    MCQ = "mcq"
    OPEN_ENDED = "open_ended"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GenerationSource(str, Enum):
    PDF = "pdf"
    TEXT = "text"
    SIMILARITY = "similarity"


# =============================================================================
# User Models
# =============================================================================


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "student@university.edu",
                    "password": "securePassword123!",
                    "full_name": "John Student",
                    "is_active": True,
                    "is_superuser": False
                }
            ]
        }
    }


class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str

    # Relationships
    sessions: list["GenerationSession"] = Relationship(
        back_populates="user", cascade_delete=True
    )


class UserPublic(UserBase):
    id: uuid.UUID

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "email": "student@university.edu",
                    "full_name": "John Student",
                    "is_active": True,
                    "is_superuser": False
                }
            ]
        }
    }


# =============================================================================
# Question Models (Structured Output Schemas)
# =============================================================================


class MCQOption(SQLModel):
    """A single option for an MCQ question."""

    label: str = Field(description="Option label (A, B, C, D)")
    text: str = Field(description="Option text content")
    is_correct: bool = Field(default=False, description="Whether this is the correct answer")


class QuestionBase(SQLModel):
    """Base question schema - used for both MCQ and Open-ended."""

    question_text: str = Field(description="The question content")
    question_type: QuestionType = Field(description="Type: mcq or open_ended")
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    topic: str | None = Field(default=None, description="Topic/subject area")
    explanation: str = Field(description="Detailed solution/explanation")

    # MCQ specific (nullable for open-ended)
    options: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="MCQ options (null for open-ended)"
    )
    correct_answer: str | None = Field(
        default=None,
        description="Correct answer label for MCQ, or model answer for open-ended"
    )

    # Metadata
    source_context: str | None = Field(
        default=None, description="Source text this question was generated from"
    )
    confidence_score: float | None = Field(
        default=None, description="AI confidence in the question quality (0-1)"
    )


class Question(QuestionBase, table=True):
    """Database model for questions."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Foreign keys
    session_id: uuid.UUID | None = Field(
        default=None, foreign_key="generationsession.id", ondelete="CASCADE"
    )
    owner_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )

    # Relationships
    session: Optional["GenerationSession"] = Relationship(back_populates="questions")
    refinement_history: list["RefinementEntry"] = Relationship(
        back_populates="question", cascade_delete=True
    )


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""

    pass


class QuestionPublic(QuestionBase):
    """Schema for returning a question via API."""

    id: uuid.UUID
    created_at: datetime
    session_id: uuid.UUID | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "question_text": "What is the primary function of chlorophyll in photosynthesis?",
                    "question_type": "mcq",
                    "difficulty": "medium",
                    "topic": "Biology - Photosynthesis",
                    "explanation": "Chlorophyll is the green pigment in plant cells that captures light energy from the sun. This energy is essential for converting carbon dioxide and water into glucose during photosynthesis.",
                    "correct_answer": "B",
                    "options": [
                        {"label": "A", "text": "To absorb water from the soil", "is_correct": False},
                        {"label": "B", "text": "To capture light energy from the sun", "is_correct": True},
                        {"label": "C", "text": "To release oxygen into the air", "is_correct": False},
                        {"label": "D", "text": "To store glucose in the leaves", "is_correct": False}
                    ],
                    "source_context": "Photosynthesis chapter excerpt...",
                    "confidence_score": 0.92,
                    "created_at": "2024-01-15T10:30:00Z",
                    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                }
            ]
        }
    }


class QuestionsPublic(SQLModel):
    """Paginated list of questions."""

    data: list[QuestionPublic]
    count: int


class QuestionUpdate(SQLModel):
    """Schema for updating a question."""

    question_text: str | None = None
    question_type: QuestionType | None = None
    difficulty: str | None = None
    topic: str | None = None
    explanation: str | None = None
    correct_answer: str | None = None
    options: list[dict] | None = None
    confidence_score: float | None = None


# =============================================================================
# Generation Session Models
# =============================================================================


class GenerationSessionBase(SQLModel):
    """A session for generating questions (groups related questions)."""

    title: str | None = Field(default=None, max_length=255)
    source_type: GenerationSource = Field(description="pdf, text, image, similarity")
    source_content: str | None = Field(default=None, description="Original input text/context")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    num_questions_requested: int | None = Field(default=None, description="Number of questions requested")


class GenerationSession(GenerationSessionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Foreign keys (optional for anonymous users)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")

    # Relationships
    user: Optional[User] = Relationship(back_populates="sessions")
    questions: list[Question] = Relationship(
        back_populates="session", cascade_delete=True
    )


class GenerationSessionCreate(SQLModel):
    title: str | None = None
    source_type: str
    source_content: str | None = None


class GenerationSessionPublic(GenerationSessionBase):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None = None


class GenerationSessionWithQuestions(GenerationSessionPublic):
    questions: list[QuestionPublic] = []


# =============================================================================
# Refinement Models (Canvas Flow)
# =============================================================================


class RefinementEntry(SQLModel, table=True):
    """Tracks refinement history for a question (Canvas flow)."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # The refinement instruction
    instruction: str = Field(description="User's refinement instruction")

    # Summary of changes made
    changes_made: str = Field(default="", description="Summary of changes applied")

    # Snapshot before refinement
    previous_state: dict[str, Any] = Field(
        sa_column=Column(JSON), description="Question state before refinement"
    )

    # Snapshot after refinement
    new_state: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON), description="Question state after refinement"
    )

    # Foreign keys
    question_id: uuid.UUID = Field(foreign_key="question.id", ondelete="CASCADE")

    # Relationships
    question: Question = Relationship(back_populates="refinement_history")


class RefinementRequest(SQLModel):
    """Request to refine a question."""

    instruction: str = Field(
        description="Natural language instruction for refinement (e.g., 'Change the correct answer to B', 'Make the distractors more confusing')",
    )


class RefinementResponse(SQLModel):
    """Response after refining a question."""

    question: QuestionPublic
    changes_made: str = Field(description="Summary of changes applied")


# =============================================================================
# Auth Models
# =============================================================================


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhMWIyYzNkNC1lNWY2LTc4OTAtYWJjZC1lZjEyMzQ1Njc4OTAiLCJleHAiOjE3MDUzMTQ4MDB9.example_signature",
                    "token_type": "bearer"
                }
            ]
        }
    }


class TokenPayload(SQLModel):
    sub: str | None = None


class Message(SQLModel):
    message: str
