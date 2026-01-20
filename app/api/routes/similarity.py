"""
Similarity-Based Question Generation Routes.

Workflow 2: Input question -> analyze -> generate similar questions
"""
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import OptionalUser, SessionDep
from app.core.config import settings
from app.core.rate_limit import limiter
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question_text": "A store sells apples for $2 each. If Maria buys 5 apples, how much does she pay in total?",
                    "options": [
                        {"label": "A", "text": "$7", "is_correct": False},
                        {"label": "B", "text": "$10", "is_correct": True},
                        {"label": "C", "text": "$12", "is_correct": False},
                        {"label": "D", "text": "$15", "is_correct": False}
                    ],
                    "num_similar": 3
                }
            ]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "topic": "Mathematics",
                    "subtopic": "Arithmetic - Multiplication",
                    "difficulty": "easy",
                    "question_type": "mcq",
                    "key_concepts": ["multiplication", "unit price", "total cost"],
                    "mathematical_operations": ["multiplication"],
                    "format_style": "word_problem",
                    "variation_suggestions": [
                        "Change the item (oranges, books, pencils)",
                        "Vary the unit price ($3, $4, $5)",
                        "Change the quantity (3, 7, 8 items)",
                        "Use different character names"
                    ]
                }
            ]
        }
    }


class SimilarityResponse(BaseModel):
    """Response schema for similarity generation."""

    session_id: uuid.UUID
    original_analysis: AnalysisResponse
    similar_questions: list[QuestionPublic]
    generation_summary: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "d4e5f6a7-b8c9-0123-def4-567890abcdef",
                    "original_analysis": {
                        "topic": "Mathematics",
                        "subtopic": "Arithmetic - Multiplication",
                        "difficulty": "easy",
                        "question_type": "mcq",
                        "key_concepts": ["multiplication", "unit price", "total cost"],
                        "mathematical_operations": ["multiplication"],
                        "format_style": "word_problem",
                        "variation_suggestions": ["Change items", "Vary prices"]
                    },
                    "similar_questions": [
                        {
                            "id": "e5f6a7b8-c9d0-1234-ef56-7890abcdef01",
                            "question_text": "A bookstore sells notebooks for $3 each. If John buys 4 notebooks, how much does he pay in total?",
                            "question_type": "mcq",
                            "difficulty": "easy",
                            "topic": "Mathematics - Multiplication",
                            "explanation": "To find the total cost, multiply the price per item by the quantity: $3 × 4 = $12",
                            "correct_answer": "C",
                            "options": [
                                {"label": "A", "text": "$7", "is_correct": False},
                                {"label": "B", "text": "$10", "is_correct": False},
                                {"label": "C", "text": "$12", "is_correct": True},
                                {"label": "D", "text": "$14", "is_correct": False}
                            ],
                            "confidence_score": 0.95,
                            "created_at": "2024-01-15T11:00:00Z",
                            "session_id": "d4e5f6a7-b8c9-0123-def4-567890abcdef"
                        }
                    ],
                    "generation_summary": "Generated 3 similar questions based on multiplication word problem pattern"
                }
            ]
        }
    }


@router.post("/analyze", response_model=AnalysisResponse)
@limiter.limit(settings.RATE_LIMIT_GENERATION)
async def analyze_question(
    request: Request,
    body: SimilarityRequest,
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
        question_text=body.question_text,
        options=body.options,
    )

    return AnalysisResponse(
        topic=analysis.topic,
        subtopic=analysis.subtopic,
        difficulty=analysis.difficulty,
        question_type=analysis.question_type,
        key_concepts=analysis.key_concepts,
        mathematical_operations=analysis.mathematical_operations,
        format_style=analysis.format_style,
        variation_suggestions=analysis.variation_suggestions,
    )


@router.post("/generate", response_model=SimilarityResponse)
@limiter.limit(settings.RATE_LIMIT_GENERATION)
async def generate_similar_questions(
    request: Request,
    body: SimilarityRequest,
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
        question_text=body.question_text,
        options=body.options,
    )

    # Step 2: Generate similar questions based on analysis
    result: GeneratedQuestions = generator.generate_similar(
        original_question=body.question_text,
        analysis=analysis,
        num_questions=body.num_similar,
        options=body.options,
    )

    # Create session for tracking
    gen_session = GenerationSession(
        source_type=GenerationSource.SIMILARITY,
        source_content=body.question_text[:500],
        num_questions_requested=body.num_similar,
        user_id=current_user.id if current_user else None,
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
            topic=analysis.topic,
            subtopic=analysis.subtopic,
            difficulty=analysis.difficulty,
            question_type=analysis.question_type,
            key_concepts=analysis.key_concepts,
            mathematical_operations=analysis.mathematical_operations,
            format_style=analysis.format_style,
            variation_suggestions=analysis.variation_suggestions,
        ),
        similar_questions=[QuestionPublic.model_validate(q) for q in questions],
        generation_summary=result.generation_summary,
    )


@router.post("/batch", response_model=list[SimilarityResponse])
@limiter.limit(settings.RATE_LIMIT_GENERATION)
async def generate_similar_batch(
    request: Request,
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
            request=request,
            body=req,
            session=session,
            current_user=current_user,
        )
        results.append(response)

    return results
