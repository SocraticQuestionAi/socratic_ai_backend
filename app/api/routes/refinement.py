"""
Interactive Question Refinement Routes (Canvas Flow).

Workflow 3: Question + natural language instruction -> refined question
Supports multi-turn conversation for iterative refinement.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, OptionalUser, SessionDep
from app.models import (
    Question,
    QuestionPublic,
    QuestionType,
    RefinementEntry,
)
from app.schemas.questions import RefinedQuestion
from app.services.question_generator import get_question_generator

router = APIRouter()


class QuestionState(BaseModel):
    """Current state of a question for refinement."""

    question_text: str
    question_type: str = "mcq"
    difficulty: str = "medium"
    topic: str | None = None
    explanation: str = ""
    correct_answer: str = ""
    options: list[dict] | None = None


class RefinementRequest(BaseModel):
    """Request schema for question refinement."""

    question_id: uuid.UUID | None = Field(
        default=None, description="Existing question ID to refine"
    )
    question_state: QuestionState | None = Field(
        default=None, description="Direct question state (if not using question_id)"
    )
    instruction: str = Field(
        min_length=5, description="Natural language refinement instruction"
    )
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Continue existing refinement conversation"
    )


class RefinementResponse(BaseModel):
    """Response schema for refinement."""

    conversation_id: uuid.UUID
    refined_question: QuestionPublic
    changes_made: str
    confidence_score: float
    turn_number: int


class ConversationHistory(BaseModel):
    """Refinement conversation history."""

    conversation_id: uuid.UUID
    question_id: uuid.UUID
    turns: list[dict]
    current_state: QuestionState


# In-memory conversation store (for demo; use Redis/DB in production)
_conversations: dict[uuid.UUID, dict] = {}


@router.post("/refine", response_model=RefinementResponse)
async def refine_question(
    request: RefinementRequest,
    session: SessionDep,
    current_user: OptionalUser,
) -> RefinementResponse:
    """
    Refine a question using natural language instructions.

    This implements a Canvas-like editing flow where you can:
    - Change the correct answer
    - Adjust difficulty
    - Modify distractors (make more/less confusing)
    - Change numerical values
    - Improve wording clarity
    - Convert between question types

    Examples:
    - "Change the correct answer to B"
    - "Make the distractors more challenging"
    - "Simplify the question for younger students"
    - "Change the numbers but keep the same concept"
    - "Add more context to the question stem"
    """
    # Get question state
    if request.question_id:
        question = session.get(Question, request.question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        question_state = {
            "question_text": question.question_text,
            "question_type": question.question_type.value,
            "difficulty": question.difficulty,
            "topic": question.topic,
            "explanation": question.explanation,
            "correct_answer": question.correct_answer,
            "options": question.options,
        }
        question_id = question.id
    elif request.question_state:
        question_state = request.question_state.model_dump()
        question_id = None
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either question_id or question_state",
        )

    # Handle conversation continuity
    conversation_history = []
    turn_number = 1

    if request.conversation_id:
        conv = _conversations.get(request.conversation_id)
        if conv:
            conversation_history = conv.get("history", [])
            question_state = conv.get("current_state", question_state)
            turn_number = len(conversation_history) // 2 + 1

    # Generate refinement
    generator = get_question_generator()
    result: RefinedQuestion = generator.refine_question(
        question_state=question_state,
        instruction=request.instruction,
        conversation_history=conversation_history if conversation_history else None,
    )

    # Create or update conversation
    conversation_id = request.conversation_id or uuid.uuid4()

    new_state = {
        "question_text": result.question_text,
        "question_type": result.question_type,
        "difficulty": result.difficulty,
        "topic": result.topic or question_state.get("topic"),
        "explanation": result.explanation,
        "correct_answer": result.correct_answer,
        "options": [opt.model_dump() for opt in result.options] if result.options else None,
    }

    # Update conversation store
    if conversation_id not in _conversations:
        _conversations[conversation_id] = {
            "question_id": question_id,
            "history": [],
            "current_state": new_state,
            "created_at": datetime.utcnow(),
        }

    _conversations[conversation_id]["history"].extend([
        {"role": "user", "content": request.instruction},
        {"role": "assistant", "content": f"Changes: {result.changes_made}"},
    ])
    _conversations[conversation_id]["current_state"] = new_state

    # Save refinement to database if we have a question
    if question_id and current_user:
        refinement = RefinementEntry(
            question_id=question_id,
            instruction=request.instruction,
            changes_made=result.changes_made,
            previous_state=question_state,
            new_state=new_state,
        )
        session.add(refinement)

        # Update the question with new state
        question = session.get(Question, question_id)
        if question:
            question.question_text = result.question_text
            question.difficulty = result.difficulty
            question.explanation = result.explanation
            question.correct_answer = result.correct_answer
            question.options = new_state["options"]
            if result.topic:
                question.topic = result.topic
            session.add(question)

        session.commit()

    # Build response question
    response_question = QuestionPublic(
        id=question_id or uuid.uuid4(),
        question_text=result.question_text,
        question_type=QuestionType.MCQ if result.question_type == "mcq" else QuestionType.OPEN_ENDED,
        difficulty=result.difficulty,
        topic=result.topic or question_state.get("topic", ""),
        explanation=result.explanation,
        correct_answer=result.correct_answer,
        options=new_state["options"],
        confidence_score=result.confidence_score,
    )

    return RefinementResponse(
        conversation_id=conversation_id,
        refined_question=response_question,
        changes_made=result.changes_made,
        confidence_score=result.confidence_score,
        turn_number=turn_number,
    )


@router.get("/conversation/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(
    conversation_id: uuid.UUID,
) -> ConversationHistory:
    """Get the history of a refinement conversation."""
    conv = _conversations.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationHistory(
        conversation_id=conversation_id,
        question_id=conv.get("question_id") or uuid.uuid4(),
        turns=conv.get("history", []),
        current_state=QuestionState(**conv.get("current_state", {})),
    )


@router.post("/conversation/{conversation_id}/reset")
async def reset_conversation(
    conversation_id: uuid.UUID,
) -> dict:
    """Reset a refinement conversation (start over)."""
    if conversation_id in _conversations:
        del _conversations[conversation_id]
        return {"status": "reset", "conversation_id": str(conversation_id)}

    raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/question/{question_id}/history")
async def get_refinement_history(
    question_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[dict]:
    """Get the refinement history for a specific question."""
    question = session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return [
        {
            "id": str(entry.id),
            "instruction": entry.instruction,
            "changes_made": entry.changes_made,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
        for entry in question.refinement_history
    ]
