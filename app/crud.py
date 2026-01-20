"""
CRUD operations for Socratic AI.
"""
import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    GenerationSession,
    GenerationSessionCreate,
    Question,
    QuestionCreate,
    User,
    UserCreate,
    UserUpdate,
)


# =============================================================================
# User CRUD
# =============================================================================


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> User:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


# Alias for compatibility
authenticate_user = authenticate


# =============================================================================
# Generation Session CRUD
# =============================================================================


def create_generation_session(
    *, session: Session, session_in: GenerationSessionCreate, user_id: uuid.UUID
) -> GenerationSession:
    db_obj = GenerationSession.model_validate(session_in, update={"user_id": user_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_generation_session(
    *, session: Session, session_id: uuid.UUID
) -> GenerationSession | None:
    return session.get(GenerationSession, session_id)


def get_sessions_by_user(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[GenerationSession]:
    statement = (
        select(GenerationSession)
        .where(GenerationSession.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(GenerationSession.created_at.desc())
    )
    return list(session.exec(statement).all())


# =============================================================================
# Question CRUD
# =============================================================================


def create_question(
    *, session: Session, question_in: QuestionCreate, session_id: uuid.UUID | None = None
) -> Question:
    db_obj = Question.model_validate(question_in, update={"session_id": session_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_questions_bulk(
    *, session: Session, questions_in: list[QuestionCreate], session_id: uuid.UUID
) -> list[Question]:
    db_objs = [
        Question.model_validate(q, update={"session_id": session_id})
        for q in questions_in
    ]
    session.add_all(db_objs)
    session.commit()
    for obj in db_objs:
        session.refresh(obj)
    return db_objs


def get_question(*, session: Session, question_id: uuid.UUID) -> Question | None:
    return session.get(Question, question_id)


def get_questions_by_session(
    *, session: Session, session_id: uuid.UUID
) -> list[Question]:
    statement = (
        select(Question)
        .where(Question.session_id == session_id)
        .order_by(Question.created_at)
    )
    return list(session.exec(statement).all())


def update_question(
    *, session: Session, db_question: Question, update_data: dict[str, Any]
) -> Question:
    db_question.sqlmodel_update(update_data)
    session.add(db_question)
    session.commit()
    session.refresh(db_question)
    return db_question


def delete_question(*, session: Session, question_id: uuid.UUID) -> bool:
    question = session.get(Question, question_id)
    if question:
        session.delete(question)
        session.commit()
        return True
    return False
