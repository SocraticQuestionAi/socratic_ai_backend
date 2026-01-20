"""
Structured Output Schemas for AI Question Generation.

These Pydantic models enforce JSON Schema validation on LLM outputs,
ensuring consistent, well-formed responses.
"""
from pydantic import BaseModel, Field


class MCQOptionSchema(BaseModel):
    """Schema for MCQ option in structured output."""

    label: str = Field(description="Option label (A, B, C, or D)")
    text: str = Field(description="The option text content")
    is_correct: bool = Field(description="Whether this option is the correct answer")


class GeneratedQuestion(BaseModel):
    """Schema for a single generated question (structured output)."""

    question_text: str = Field(description="The complete question text")
    question_type: str = Field(
        description="Type of question: 'mcq' or 'open_ended'"
    )
    difficulty: str = Field(
        description="Difficulty level: 'easy', 'medium', or 'hard'"
    )
    topic: str = Field(description="The topic or subject area of the question")
    explanation: str = Field(
        description="Detailed step-by-step solution and explanation"
    )

    # MCQ-specific fields (null for open-ended)
    options: list[MCQOptionSchema] | None = Field(
        default=None,
        description="List of 4 options for MCQ questions. Null for open-ended questions."
    )
    correct_answer: str = Field(
        description="The correct answer. For MCQ: the label (A/B/C/D). For open-ended: model answer."
    )

    # Quality metadata
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="AI confidence in question quality (0.0 to 1.0)"
    )


class GeneratedQuestions(BaseModel):
    """Schema for batch question generation (structured output)."""

    questions: list[GeneratedQuestion] = Field(
        description="List of generated questions"
    )
    generation_summary: str = Field(
        description="Brief summary of the generation (topics covered, difficulty distribution)"
    )


class QuestionAnalysis(BaseModel):
    """Schema for analyzing an input question (for similarity generation)."""

    topic: str = Field(description="The main topic/subject of the question")
    subtopic: str = Field(description="More specific subtopic if applicable")
    difficulty: str = Field(description="Estimated difficulty: easy, medium, hard")
    question_type: str = Field(description="Type: mcq or open_ended")
    key_concepts: list[str] = Field(
        description="List of key concepts tested by this question"
    )
    mathematical_operations: list[str] | None = Field(
        default=None,
        description="Mathematical operations involved (if applicable)"
    )
    format_style: str = Field(
        description="Description of the question format/style"
    )


class SimilarityAnalysis(BaseModel):
    """Schema for analyzing a question before generating similar ones."""

    analysis: QuestionAnalysis = Field(description="Analysis of the input question")
    variation_suggestions: list[str] = Field(
        description="Suggestions for how to create variations"
    )


class RefinedQuestion(BaseModel):
    """Schema for refined question output (Canvas flow)."""

    question_text: str = Field(description="The refined question text")
    question_type: str = Field(description="Type: mcq or open_ended")
    difficulty: str = Field(description="Difficulty level")
    topic: str | None = Field(default=None, description="Topic if changed")
    explanation: str = Field(description="Updated explanation")

    # MCQ-specific
    options: list[MCQOptionSchema] | None = Field(
        default=None,
        description="Updated options for MCQ"
    )
    correct_answer: str = Field(description="The correct answer")

    # Refinement metadata
    changes_made: str = Field(
        description="Summary of what was changed based on the instruction"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="AI confidence in the refinement quality"
    )
