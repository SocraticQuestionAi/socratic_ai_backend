from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings

# SQLite needs special handling for FastAPI's async nature
connect_args = {}
if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def init_db(session: Session) -> None:
    """Initialize database with first superuser if not exists."""
    from app import crud
    from app.models import User, UserCreate

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        crud.create_user(session=session, user_create=user_in)
