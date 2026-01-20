# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered question generation backend for educational content. Three core workflows:
1. **Document-Based Generation**: PDF/text → questions
2. **Similarity Generation**: Question → similar questions
3. **Interactive Refinement**: Canvas-like question editing via natural language

## Commands

```bash
# Development server (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head              # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Testing
pytest                            # Run all tests
pytest tests/test_api/            # Run API tests only
pytest -k "test_auth"             # Run tests matching pattern
pytest --cov=app                  # With coverage

# Linting & Type Checking
ruff check .                      # Lint
ruff format .                     # Format
mypy app                          # Type check
```

## Architecture

### Request Flow
```
Routes (app/api/routes/) → Services (app/services/) → LLM Client → OpenRouter API
                        ↘ CRUD (app/crud.py) → SQLModel → Database
```

### Key Layers

**Services** (`app/services/`):
- `llm_client.py`: Unified LLM interface using OpenRouter (OpenAI-compatible). Uses `instructor` library for structured JSON Schema outputs from Pydantic models.
- `question_generator.py`: Core AI logic. Contains system prompts and orchestrates the three workflows.
- `pdf_parser.py`: PDF text extraction.

**Models** (`app/models.py`):
- Uses SQLModel for unified ORM + Pydantic validation
- Main entities: `User`, `Question`, `GenerationSession`, `RefinementEntry`
- Schemas for structured LLM outputs are in `app/schemas/questions.py`

**Dependencies** (`app/api/deps.py`):
- `SessionDep`: Database session injection
- `CurrentUser` / `OptionalUser`: JWT auth dependencies
- Most generation endpoints work without auth for quick testing

### Database

- **Local**: SQLite (auto-enabled when `POSTGRES_PASSWORD` is empty)
- **Production**: PostgreSQL via `psycopg`
- Migrations in `alembic/versions/`

### LLM Integration

Uses OpenRouter as a unified gateway to multiple models. Default model configurable via `DEFAULT_MODEL` env var. The `instructor` library wraps responses into Pydantic models for type-safe structured outputs.

```python
# Example structured generation
result = llm.generate_structured(
    response_model=GeneratedQuestions,
    system_prompt="...",
    user_prompt="...",
)
```

## Testing

Tests use SQLite in-memory database with pytest fixtures. Mock LLM responses defined in `tests/conftest.py`. Test structure mirrors `app/` layout.

Key fixtures: `client`, `authenticated_client`, `test_user`, `mock_llm_client`, `test_question`

## Environment

Copy `.env.example` to `.env`. Required for LLM features: `OPENROUTER_API_KEY`
