"""
Question CRUD Routes.

Manage saved questions - list, update, delete operations.
"""
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.models import Question, QuestionPublic, QuestionType, QuestionUpdate

router = APIRouter()


class QuestionsListResponse(BaseModel):
    """Paginated questions list response."""

    questions: list[QuestionPublic]
    total: int
    page: int
    per_page: int


@router.get("/", response_model=QuestionsListResponse)
async def list_questions(
    session: SessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    question_type: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    topic: str | None = Query(default=None),
) -> QuestionsListResponse:
    """
    List questions owned by the current user.

    Supports filtering by type, difficulty, and topic.
    """
    from sqlmodel import select, func

    # Build query
    query = select(Question).where(Question.owner_id == current_user.id)

    if question_type:
        q_type = QuestionType.MCQ if question_type.lower() == "mcq" else QuestionType.OPEN_ENDED
        query = query.where(Question.question_type == q_type)

    if difficulty:
        query = query.where(Question.difficulty == difficulty)

    if topic:
        query = query.where(Question.topic.ilike(f"%{topic}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Question.created_at.desc())

    questions = session.exec(query).all()

    return QuestionsListResponse(
        questions=[QuestionPublic.model_validate(q) for q in questions],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{question_id}", response_model=QuestionPublic)
async def get_question(
    question_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> QuestionPublic:
    """Get a specific question by ID."""
    question = session.get(Question, question_id)

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return QuestionPublic.model_validate(question)


@router.patch("/{question_id}", response_model=QuestionPublic)
async def update_question(
    question_id: uuid.UUID,
    question_in: QuestionUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> QuestionPublic:
    """
    Update a question manually.

    Use this for direct edits (not AI-assisted refinement).
    """
    question = session.get(Question, question_id)

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update fields
    update_data = question_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    session.add(question)
    session.commit()
    session.refresh(question)

    return QuestionPublic.model_validate(question)


@router.delete("/{question_id}")
async def delete_question(
    question_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """Delete a question."""
    question = session.get(Question, question_id)

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    session.delete(question)
    session.commit()

    return {"status": "deleted", "question_id": str(question_id)}


@router.post("/bulk-delete")
async def bulk_delete_questions(
    question_ids: list[uuid.UUID],
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """Delete multiple questions at once."""
    deleted = 0

    for qid in question_ids:
        question = session.get(Question, qid)
        if question and question.owner_id == current_user.id:
            session.delete(question)
            deleted += 1

    session.commit()

    return {"status": "deleted", "count": deleted}
