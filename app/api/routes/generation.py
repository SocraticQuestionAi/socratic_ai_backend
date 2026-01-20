"""
Document-Based Question Generation Routes.

Workflow 1: PDF/text content -> AI-generated questions
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, OptionalUser, SessionDep
from app.models import (
    GenerationSession,
    GenerationSource,
    Question,
    QuestionCreate,
    QuestionPublic,
    QuestionType,
)
from app.schemas.questions import GeneratedQuestions
from app.services.pdf_parser import PDFParserError, extract_text_from_pdf, get_pdf_info
from app.services.question_generator import get_question_generator

router = APIRouter()


# Request/Response schemas for this route
from pydantic import BaseModel, Field


class TextGenerationRequest(BaseModel):
    """Request schema for text-based generation."""

    content: str = Field(min_length=50, description="Source text content (min 50 chars)")
    num_questions: int = Field(default=5, ge=1, le=20, description="Number of questions")
    question_types: list[str] | None = Field(
        default=None, description="Question types: 'mcq', 'open_ended', or both"
    )
    difficulty: str = Field(default="mixed", description="easy, medium, hard, or mixed")
    topic_focus: str | None = Field(default=None, description="Specific topic to focus on")


class GenerationResponse(BaseModel):
    """Response schema for question generation."""

    session_id: uuid.UUID
    questions: list[QuestionPublic]
    generation_summary: str
    source_type: str
    page_count: int | None = None


@router.post("/from-text", response_model=GenerationResponse)
async def generate_from_text(
    request: TextGenerationRequest,
    session: SessionDep,
    current_user: OptionalUser,
) -> GenerationResponse:
    """
    Generate questions from text content.

    - Accepts plain text or markdown content
    - Returns AI-generated questions with explanations
    - Optionally saves to database if user is authenticated
    """
    generator = get_question_generator()

    # Parse question types
    q_types = None
    if request.question_types:
        q_types = [
            QuestionType.MCQ if t.lower() == "mcq" else QuestionType.OPEN_ENDED
            for t in request.question_types
        ]

    # Generate questions
    result: GeneratedQuestions = generator.generate_from_document(
        content=request.content,
        num_questions=request.num_questions,
        question_types=q_types,
        difficulty=request.difficulty,
        topic_focus=request.topic_focus,
    )

    # Create session and questions in database
    gen_session = GenerationSession(
        source_type=GenerationSource.TEXT,
        source_content=request.content[:1000],  # Store preview
        num_questions_requested=request.num_questions,
        owner_id=current_user.id if current_user else None,
    )
    session.add(gen_session)
    session.flush()

    # Convert and store questions
    questions = []
    for q in result.questions:
        question = Question(
            question_text=q.question_text,
            question_type=QuestionType.MCQ if q.question_type == "mcq" else QuestionType.OPEN_ENDED,
            difficulty=q.difficulty,
            topic=q.topic,
            explanation=q.explanation,
            correct_answer=q.correct_answer,
            options=[opt.model_dump() for opt in q.options] if q.options else None,
            confidence_score=q.confidence_score,
            session_id=gen_session.id,
            owner_id=current_user.id if current_user else None,
        )
        session.add(question)
        questions.append(question)

    session.commit()

    # Refresh to get IDs
    session.refresh(gen_session)
    for q in questions:
        session.refresh(q)

    return GenerationResponse(
        session_id=gen_session.id,
        questions=[QuestionPublic.model_validate(q) for q in questions],
        generation_summary=result.generation_summary,
        source_type="text",
    )


@router.post("/from-pdf", response_model=GenerationResponse)
async def generate_from_pdf(
    file: Annotated[UploadFile, File(description="PDF file to process")],
    session: SessionDep,
    current_user: OptionalUser,
    num_questions: Annotated[int, Form(ge=1, le=20)] = 5,
    question_types: Annotated[str | None, Form()] = None,
    difficulty: Annotated[str, Form()] = "mixed",
    topic_focus: Annotated[str | None, Form()] = None,
) -> GenerationResponse:
    """
    Generate questions from a PDF document.

    - Extracts text from PDF using PyMuPDF (with pypdf fallback)
    - Supports multi-page documents
    - Returns AI-generated questions with explanations
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF document",
        )

    # Read and parse PDF
    try:
        pdf_content = await file.read()
        text_content = extract_text_from_pdf(pdf_content)
        pdf_info = get_pdf_info(pdf_content)
    except PDFParserError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse PDF: {str(e)}",
        )

    if not text_content or len(text_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF contains insufficient text content for question generation",
        )

    # Parse question types from form data
    q_types = None
    if question_types:
        q_types = [
            QuestionType.MCQ if t.strip().lower() == "mcq" else QuestionType.OPEN_ENDED
            for t in question_types.split(",")
        ]

    # Generate questions
    generator = get_question_generator()
    result: GeneratedQuestions = generator.generate_from_document(
        content=text_content,
        num_questions=num_questions,
        question_types=q_types,
        difficulty=difficulty,
        topic_focus=topic_focus,
    )

    # Create session
    gen_session = GenerationSession(
        source_type=GenerationSource.PDF,
        source_content=f"PDF: {file.filename}",
        num_questions_requested=num_questions,
        owner_id=current_user.id if current_user else None,
    )
    session.add(gen_session)
    session.flush()

    # Store questions
    questions = []
    for q in result.questions:
        question = Question(
            question_text=q.question_text,
            question_type=QuestionType.MCQ if q.question_type == "mcq" else QuestionType.OPEN_ENDED,
            difficulty=q.difficulty,
            topic=q.topic,
            explanation=q.explanation,
            correct_answer=q.correct_answer,
            options=[opt.model_dump() for opt in q.options] if q.options else None,
            confidence_score=q.confidence_score,
            session_id=gen_session.id,
            owner_id=current_user.id if current_user else None,
        )
        session.add(question)
        questions.append(question)

    session.commit()

    session.refresh(gen_session)
    for q in questions:
        session.refresh(q)

    return GenerationResponse(
        session_id=gen_session.id,
        questions=[QuestionPublic.model_validate(q) for q in questions],
        generation_summary=result.generation_summary,
        source_type="pdf",
        page_count=pdf_info.get("page_count"),
    )


@router.get("/session/{session_id}", response_model=GenerationResponse)
async def get_generation_session(
    session_id: uuid.UUID,
    session: SessionDep,
    current_user: OptionalUser,
) -> GenerationResponse:
    """Retrieve a previous generation session with its questions."""
    gen_session = session.get(GenerationSession, session_id)

    if not gen_session:
        raise HTTPException(status_code=404, detail="Generation session not found")

    # Check ownership if session has owner
    if gen_session.owner_id and (not current_user or gen_session.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    return GenerationResponse(
        session_id=gen_session.id,
        questions=[QuestionPublic.model_validate(q) for q in gen_session.questions],
        generation_summary=f"Retrieved {len(gen_session.questions)} questions",
        source_type=gen_session.source_type.value,
    )
