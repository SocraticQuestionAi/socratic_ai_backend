"""Initial schema - users, questions, sessions, refinements.

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-01-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    # Generation sessions table
    op.create_table(
        "generationsession",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_content", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("num_questions_requested", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Questions table
    op.create_table(
        "question",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("question_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("difficulty", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("topic", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("explanation", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("correct_answer", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["generationsession.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Refinement entries table
    op.create_table(
        "refinemententry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("instruction", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("changes_made", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["question_id"], ["question.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("refinemententry")
    op.drop_table("question")
    op.drop_table("generationsession")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
