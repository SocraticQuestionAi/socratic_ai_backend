"""
Similarity-Based Question Generation Routes.

Workflow 2: Input question -> analyze -> generate similar questions
"""
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import OptionalUser, SessionDep
from app.models import (
    GenerationSession,
    GenerationSource,
    Question,
    QuestionPublic,
    QuestionType,
)
from app.schemas.questions import GeneratedQuestions, SimilarityAnalysis
from app.services.question_generator import get_question_generator

router = APIRouter()


class SimilarityRequest(BaseModel):
    """Request schema for similarity-based generation."""

    question_text: str = Field(min_length=10, description="The source question text")
    options: list[dict] | None = Field(
        default=None,
        description="MCQ options if applicable: [{label: 'A', text: '...', is_correct: bool}]",
    )
    num_similar: int = Field(default=3, ge=1, le=10, description="Number of similar questions")


class AnalysisResponse(BaseModel):
    """Response schema for question analysis."""

    topic: str
    subtopic: str
    difficulty: str
    question_type: str
    key_concepts: list[str]
    mathematical_operations: list[str] | None
    format_style: str
    variation_suggestions: list[str]


class SimilarityResponse(BaseModel):
    """Response schema for similarity generation."""

    session_id: uuid.UUID
    original_analysis: AnalysisResponse
    similar_questions: list[QuestionPublic]
    generation_summary: str


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_question(
    request: SimilarityRequest,
) -> AnalysisResponse:
    """
    Analyze a question for similarity generation.

    Returns detailed analysis including:
    - Topic and difficulty classification
    - Key concepts being tested
    - Format style identification
    - Suggestions for creating variations
    """
    generator = get_question_generator()

    analysis: SimilarityAnalysis = generator.analyze_question(
        question_text=request.question_text,
        options=request.options,
    )

    return AnalysisResponse(
        topic=analysis.analysis.topic,
        subtopic=analysis.analysis.subtopic,
        difficulty=analysis.analysis.difficulty,
        question_type=analysis.analysis.question_type,
        key_concepts=analysis.analysis.key_concepts,
        mathematical_operations=analysis.analysis.mathematical_operations,
        format_style=analysis.analysis.format_style,
        variation_suggestions=analysis.variation_suggestions,
    )


@router.post("/generate", response_model=SimilarityResponse)
async def generate_similar_questions(
    request: SimilarityRequest,
    session: SessionDep,
    current_user: OptionalUser,
) -> SimilarityResponse:
    """
    Generate questions similar to the input question.

    This is a two-step process:
    1. Analyze the input question (topic, difficulty, format, concepts)
    2. Generate N similar questions maintaining the same characteristics

    For math questions: Numbers change but answers remain "clean"
    For conceptual questions: Context/scenario changes while testing same understanding
    """
    generator = get_question_generator()

    # Step 1: Analyze the input question
    analysis: SimilarityAnalysis = generator.analyze_question(
        question_text=request.question_text,
        options=request.options,
    )

    # Step 2: Generate similar questions based on analysis
    result: GeneratedQuestions = generator.generate_similar(
        original_question=request.question_text,
        analysis=analysis,
        num_questions=request.num_similar,
        options=request.options,
    )

    # Create session for tracking
    gen_session = GenerationSession(
        source_type=GenerationSource.SIMILARITY,
        source_content=request.question_text[:500],
        num_questions_requested=request.num_similar,
        owner_id=current_user.id if current_user else None,
    )
    session.add(gen_session)
    session.flush()

    # Store generated questions
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

    return SimilarityResponse(
        session_id=gen_session.id,
        original_analysis=AnalysisResponse(
            topic=analysis.analysis.topic,
            subtopic=analysis.analysis.subtopic,
            difficulty=analysis.analysis.difficulty,
            question_type=analysis.analysis.question_type,
            key_concepts=analysis.analysis.key_concepts,
            mathematical_operations=analysis.analysis.mathematical_operations,
            format_style=analysis.analysis.format_style,
            variation_suggestions=analysis.variation_suggestions,
        ),
        similar_questions=[QuestionPublic.model_validate(q) for q in questions],
        generation_summary=result.generation_summary,
    )


@router.post("/batch", response_model=list[SimilarityResponse])
async def generate_similar_batch(
    questions: list[SimilarityRequest],
    session: SessionDep,
    current_user: OptionalUser,
) -> list[SimilarityResponse]:
    """
    Generate similar questions for multiple input questions.

    Useful for creating question banks with variations.
    Limited to 5 questions per batch to manage API costs.
    """
    if len(questions) > 5:
        raise HTTPException(
            status_code=400,
            detail="Batch limited to 5 questions. Submit multiple requests for larger batches.",
        )

    results = []
    for req in questions:
        # Reuse the single generation endpoint logic
        response = await generate_similar_questions(
            request=req,
            session=session,
            current_user=current_user,
        )
        results.append(response)

    return results
