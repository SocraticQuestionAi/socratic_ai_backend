"""
Database models and Pydantic schemas for Socratic AI.

Uses SQLModel for unified ORM and validation.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

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
    options: list[MCQOption] | None = Field(
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

    # Relationships
    session: "GenerationSession | None" = Relationship(back_populates="questions")
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


class QuestionsPublic(SQLModel):
    """Paginated list of questions."""

    data: list[QuestionPublic]
    count: int


# =============================================================================
# Generation Session Models
# =============================================================================


class GenerationSessionBase(SQLModel):
    """A session for generating questions (groups related questions)."""

    title: str | None = Field(default=None, max_length=255)
    source_type: str = Field(description="pdf, text, image, similarity")
    source_content: str | None = Field(default=None, description="Original input text/context")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)


class GenerationSession(GenerationSessionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Foreign keys
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")

    # Relationships
    user: User = Relationship(back_populates="sessions")
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
    user_id: uuid.UUID


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

    # Snapshot before refinement
    previous_state: dict[str, Any] = Field(
        sa_column=Column(JSON), description="Question state before refinement"
    )

    # Foreign keys
    question_id: uuid.UUID = Field(foreign_key="question.id", ondelete="CASCADE")

    # Relationships
    question: Question = Relationship(back_populates="refinement_history")


class RefinementRequest(SQLModel):
    """Request to refine a question."""

    instruction: str = Field(
        description="Natural language instruction for refinement",
        examples=[
            "Change the correct answer to B",
            "Make the distractors more confusing",
            "Change the numbers to create an integer result",
        ],
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


class TokenPayload(SQLModel):
    sub: str | None = None


class Message(SQLModel):
    message: str
