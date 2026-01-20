# Socratic AI Backend

AI-powered educational question generation backend with PDF parsing, similarity-based generation, and interactive Canvas-style refinement.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Architecture](#architecture)
- [License](#license)

---

## Overview

Socratic AI is a backend service that generates high-quality educational assessment questions using large language models. It supports three core workflows:

1. **Document-Based Generation**: Upload PDFs or provide text content to automatically generate multiple-choice and open-ended questions with detailed explanations.

2. **Similarity Generation**: Analyze an existing question and generate similar variations that test the same concepts while using different values, contexts, or scenarios.

3. **Interactive Refinement**: Use natural language instructions to modify questions in a Canvas-like editing flow with multi-turn conversation support.

The API uses OpenRouter as a unified gateway to access various LLM models (Gemini, Claude, GPT-4, etc.) and leverages the `instructor` library for type-safe structured outputs.

---

## Features

### Question Generation
- Generate questions from PDF documents or plain text
- Support for Multiple Choice Questions (MCQ) with 4 options
- Support for Open-Ended questions with model answers
- Configurable difficulty levels (easy, medium, hard, mixed)
- Topic-focused generation
- Confidence scores for question quality
- Detailed explanations for each question

### Similarity Analysis
- Deep analysis of question structure and concepts
- Identification of topic, difficulty, and format style
- Mathematical operations detection for math questions
- Automatic variation suggestions
- Batch processing for creating question banks

### Interactive Refinement (Canvas Flow)
- Natural language instructions for modifications
- Multi-turn conversation support
- Change correct answers, adjust difficulty, modify distractors
- Refinement history tracking
- Persistent question updates in database

### Authentication and Security
- JWT-based authentication
- Optional auth for generation endpoints (works without login)
- Rate limiting per endpoint category
- CORS configuration
- Security headers middleware

### Database
- SQLite for local development (auto-enabled)
- PostgreSQL for production
- Alembic migrations
- SQLModel ORM with Pydantic validation

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Framework | FastAPI 0.115+ |
| Database | PostgreSQL 16 / SQLite |
| ORM | SQLModel |
| Migrations | Alembic |
| LLM Integration | OpenRouter API (OpenAI-compatible) |
| Structured Outputs | instructor library |
| PDF Processing | PyMuPDF, pypdf |
| Authentication | JWT (PyJWT), bcrypt |
| Rate Limiting | SlowAPI |
| Validation | Pydantic 2.9+ |
| HTTP Client | httpx |
| Monitoring | Sentry SDK |

---

## Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 16+ (optional, SQLite used by default for local development)
- An OpenRouter API key (or Google API key for direct Gemini access)

### Quick Start

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/socratic_ai_backend.git
cd socratic_ai_backend
```

2. **Create and activate virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

Using pip:
```bash
pip install -e ".[dev]"
```

Using uv (recommended for faster installation):
```bash
pip install uv
uv pip install -e ".[dev]"
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Run database migrations**

```bash
alembic upgrade head
```

6. **Start the development server**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/api/v1/docs`.

### Docker Installation

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f api
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Application
PROJECT_NAME="Socratic AI"
ENVIRONMENT=local                    # local, staging, production
SECRET_KEY=your-secret-key-here      # Change in production
API_V1_STR=/api/v1

# CORS (comma-separated origins)
BACKEND_CORS_ORIGINS="http://localhost:3000,http://localhost:5173"

# Database - PostgreSQL (leave POSTGRES_PASSWORD empty for SQLite)
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=                   # Empty = use SQLite
POSTGRES_DB=socratic_ai

# AI Providers
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Optional: Direct Google Gemini access
GOOGLE_API_KEY=your_google_api_key

# Model Configuration
DEFAULT_MODEL=google/gemini-2.0-flash-exp:free
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=4096

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_GENERATION=20/minute

# First Superuser
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis
```

### Available Models via OpenRouter

- `google/gemini-2.0-flash-exp:free` (default, free tier)
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4o`
- `openai/gpt-4o-mini`
- `meta-llama/llama-3-70b-instruct`

See [OpenRouter Models](https://openrouter.ai/models) for the complete list.

---

## API Reference

### Base URL

```
http://localhost:8000/api/v1
```

### Authentication

Most generation endpoints work without authentication. For saving questions to your account, use JWT authentication:

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=your@email.com&password=yourpassword"

# Use token in requests
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/questions/
```

### Endpoints

#### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | OAuth2 token login |
| POST | `/api/v1/auth/register` | Register new user |
| GET | `/api/v1/auth/me` | Get current user info |

#### Document-Based Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/generate/from-text` | Generate questions from text |
| POST | `/api/v1/generate/from-pdf` | Generate questions from PDF |
| GET | `/api/v1/generate/session/{id}` | Get generation session |

#### Similarity Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/similar/analyze` | Analyze a question |
| POST | `/api/v1/similar/generate` | Generate similar questions |
| POST | `/api/v1/similar/batch` | Batch generation (max 5) |

#### Interactive Refinement

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/refine/refine` | Refine a question |
| GET | `/api/v1/refine/conversation/{id}` | Get conversation history |
| POST | `/api/v1/refine/conversation/{id}/reset` | Reset conversation |
| GET | `/api/v1/refine/question/{id}/history` | Get refinement history |

#### Question Management (Requires Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/questions/` | List user's questions |
| GET | `/api/v1/questions/{id}` | Get specific question |
| PATCH | `/api/v1/questions/{id}` | Update question |
| DELETE | `/api/v1/questions/{id}` | Delete question |
| POST | `/api/v1/questions/bulk-delete` | Delete multiple questions |

---

## Usage Examples

### Generate Questions from Text

```bash
curl -X POST http://localhost:8000/api/v1/generate/from-text \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Photosynthesis is the process by which plants convert light energy into chemical energy. During this process, plants absorb carbon dioxide from the air and water from the soil. Using sunlight, they convert these raw materials into glucose and oxygen.",
    "num_questions": 3,
    "question_types": ["mcq", "open_ended"],
    "difficulty": "medium",
    "topic_focus": "Photosynthesis"
  }'
```

### Generate Questions from PDF

```bash
curl -X POST http://localhost:8000/api/v1/generate/from-pdf \
  -F "file=@document.pdf" \
  -F "num_questions=5" \
  -F "difficulty=mixed" \
  -F "question_types=mcq,open_ended"
```

### Analyze and Generate Similar Questions

```bash
# Analyze a question
curl -X POST http://localhost:8000/api/v1/similar/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "question_text": "A store sells apples for $2 each. If Maria buys 5 apples, how much does she pay?",
    "options": [
      {"label": "A", "text": "$7", "is_correct": false},
      {"label": "B", "text": "$10", "is_correct": true},
      {"label": "C", "text": "$12", "is_correct": false},
      {"label": "D", "text": "$15", "is_correct": false}
    ]
  }'

# Generate similar questions
curl -X POST http://localhost:8000/api/v1/similar/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question_text": "A store sells apples for $2 each. If Maria buys 5 apples, how much does she pay?",
    "options": [
      {"label": "A", "text": "$7", "is_correct": false},
      {"label": "B", "text": "$10", "is_correct": true},
      {"label": "C", "text": "$12", "is_correct": false},
      {"label": "D", "text": "$15", "is_correct": false}
    ],
    "num_similar": 3
  }'
```

### Refine a Question (Canvas Flow)

```bash
# Initial refinement
curl -X POST http://localhost:8000/api/v1/refine/refine \
  -H "Content-Type: application/json" \
  -d '{
    "question_state": {
      "question_text": "What is the capital of France?",
      "question_type": "mcq",
      "difficulty": "easy",
      "options": [
        {"label": "A", "text": "Paris", "is_correct": true},
        {"label": "B", "text": "London", "is_correct": false},
        {"label": "C", "text": "Berlin", "is_correct": false},
        {"label": "D", "text": "Madrid", "is_correct": false}
      ],
      "correct_answer": "A",
      "explanation": "Paris is the capital of France."
    },
    "instruction": "Make the distractors more challenging by using other European capitals"
  }'

# Continue refinement with conversation ID
curl -X POST http://localhost:8000/api/v1/refine/refine \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conversation-uuid-from-previous-response",
    "instruction": "Now increase the difficulty to hard"
  }'
```

### Python SDK Example

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000/api/v1")

# Generate questions
response = client.post("/generate/from-text", json={
    "content": "Your educational content here...",
    "num_questions": 5,
    "difficulty": "medium"
})
questions = response.json()

# Refine a question
response = client.post("/refine/refine", json={
    "question_state": questions["questions"][0],
    "instruction": "Make this question easier for beginners"
})
refined = response.json()
```

---

## Development

### Project Structure

```
socratic_ai_backend/
├── app/
│   ├── api/
│   │   ├── routes/          # API endpoints
│   │   │   ├── auth.py      # Authentication
│   │   │   ├── generation.py # Document generation
│   │   │   ├── similarity.py # Similarity generation
│   │   │   ├── refinement.py # Canvas flow
│   │   │   └── questions.py  # Question CRUD
│   │   ├── deps.py          # Dependencies (DB, auth)
│   │   └── main.py          # Router aggregation
│   ├── core/
│   │   ├── config.py        # Settings management
│   │   ├── db.py            # Database connection
│   │   ├── security.py      # JWT handling
│   │   ├── middleware.py    # Security middleware
│   │   └── rate_limit.py    # Rate limiting
│   ├── services/
│   │   ├── llm_client.py    # LLM integration
│   │   ├── question_generator.py  # AI logic
│   │   └── pdf_parser.py    # PDF processing
│   ├── schemas/
│   │   └── questions.py     # LLM output schemas
│   ├── models.py            # SQLModel entities
│   ├── crud.py              # Database operations
│   └── main.py              # Application entry point
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
├── pyproject.toml           # Dependencies
└── docker-compose.yml       # Docker configuration
```

### Common Commands

```bash
# Start development server with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Create new database migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Lint code
ruff check .

# Format code
ruff format .

# Type checking
mypy app
```

---

## Testing

The test suite uses pytest with SQLite in-memory database and mocked LLM responses.

### Test Coverage

| Module | Coverage | Description |
|--------|----------|-------------|
| `app/api/routes/*` | 100% | All API endpoints fully tested |
| `app/crud.py` | 100% | All CRUD operations tested |
| `app/models.py` | 100% | All database models tested |
| `app/services/*` | 97-100% | LLM client, PDF parser, question generator |
| `app/core/security.py` | 100% | Password hashing, JWT creation |
| `app/api/deps.py` | 90% | Authentication dependencies |
| **Overall** | **96%** | **170 tests passing** |

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run with HTML coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_generation.py

# Run specific test class
pytest tests/test_api/test_auth.py::TestLogin

# Run tests matching pattern
pytest -k "test_auth"

# Verbose output with short traceback
pytest -v --tb=short

# Run only failed tests from last run
pytest --lf
```

### Test Structure

```
tests/
├── conftest.py                    # Fixtures and test configuration
├── test_api/                      # API endpoint tests (65 tests)
│   ├── test_auth.py               # 18 tests - login, registration, tokens
│   ├── test_generation.py         # 13 tests - text/PDF generation
│   ├── test_questions.py          # 11 tests - CRUD operations
│   ├── test_refinement.py         # 12 tests - Canvas flow, conversations
│   └── test_similarity.py         # 11 tests - analysis, similar generation
├── test_core/                     # Core module tests (5 tests)
│   └── test_security.py           # Password hashing, JWT creation
├── test_crud/                     # Database operation tests (26 tests)
│   └── test_crud.py               # User, session, question CRUD
└── test_services/                 # Service layer tests (74 tests)
    ├── test_llm_client.py         # 5 tests - structured output
    ├── test_pdf_parser.py         # 38 tests - PDF extraction
    └── test_question_generator.py # 31 tests - all AI workflows
```

### Key Test Fixtures

| Fixture | Description |
|---------|-------------|
| `client` | TestClient for unauthenticated API requests |
| `authenticated_client` | Client with JWT auth (user dependencies overridden) |
| `session` | SQLite in-memory database session |
| `test_user` | Sample user created in database |
| `test_superuser` | Superuser for admin endpoint tests |
| `auth_headers` | Authorization headers with valid JWT |
| `mock_llm_client` | Mocked LLM client with deterministic responses |
| `mock_generated_questions` | Mock response for question generation |
| `mock_refined_question` | Mock response for question refinement |
| `test_question` | Sample question fixture in database |
| `test_generation_session` | Sample generation session fixture |
| `sample_pdf_content` | Valid PDF bytes for upload tests |
| `sample_text_content` | Educational text for generation tests |

### Test Categories

#### API Tests
- **Authentication**: Login, registration, token validation, edge cases (invalid UUID, nonexistent user, inactive user)
- **Generation**: Text-based generation, PDF upload, session retrieval, validation errors
- **Similarity**: Question analysis, similar question generation, batch processing
- **Refinement**: Canvas flow, conversation continuation, history tracking
- **Questions**: CRUD operations, pagination, authorization

#### Service Tests
- **LLM Client**: Structured output generation, text generation
- **PDF Parser**: Text extraction, encrypted PDF handling, edge cases
- **Question Generator**: Document generation, similarity analysis, refinement workflows

#### Security Tests
- **Password Hashing**: Bcrypt hashing and verification
- **JWT Tokens**: Creation and validation
- **Authentication Edge Cases**: Invalid tokens, expired tokens, missing users

### Writing New Tests

```python
# Example: Testing a new endpoint
import pytest
from fastapi.testclient import TestClient

class TestNewFeature:
    """Tests for the new feature endpoint."""

    def test_feature_success(
        self,
        client: TestClient,
        mock_generated_questions,  # Use existing fixtures
    ):
        """Test successful feature operation."""
        with patch("app.api.routes.feature.get_service") as mock:
            mock.return_value.process.return_value = expected_result

            response = client.post("/api/v1/feature/action", json={...})

            assert response.status_code == 200
            assert response.json()["key"] == expected_value

    def test_feature_requires_auth(self, client: TestClient):
        """Test that feature requires authentication."""
        response = client.get("/api/v1/feature/protected")
        assert response.status_code == 401

    def test_feature_with_auth(self, authenticated_client: TestClient):
        """Test feature with authenticated user."""
        response = authenticated_client.get("/api/v1/feature/protected")
        assert response.status_code == 200
```

### Mocking Strategy

The test suite uses extensive mocking to avoid external dependencies:

1. **Database**: SQLite in-memory database with fresh schema per test session
2. **LLM Calls**: Mocked `get_question_generator()` returns deterministic responses
3. **PDF Parsing**: Mocked `extract_text_from_pdf()` for predictable content
4. **Authentication**: Dependency overrides for `get_current_user` and `get_optional_user`

---

## Deployment

### Docker Deployment

```bash
# Production build
docker build -t socratic-ai-backend .

# Run container
docker run -d \
  -p 8000:8000 \
  -e OPENROUTER_API_KEY=your_key \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  socratic-ai-backend
```

### Docker Compose (with PostgreSQL)

```bash
# Set environment variables
export OPENROUTER_API_KEY=your_key
export SECRET_KEY=your_secret

# Start services
docker-compose up -d
```

### Fly.io Deployment

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
fly deploy

# Set secrets
fly secrets set OPENROUTER_API_KEY=your_key
fly secrets set SECRET_KEY=your_secret
fly secrets set DATABASE_URL=your_postgres_url
```

### Render Deployment

The project includes `render.yaml` for automatic deployment on Render:

1. Connect your GitHub repository to Render
2. Render will automatically detect the configuration
3. Set environment variables in the Render dashboard

### Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set up rate limiting with Redis storage
- [ ] Enable Sentry for error monitoring
- [ ] Configure CORS origins for your frontend
- [ ] Use HTTPS in production

---

## Architecture

### Request Flow

```
Client Request
     │
     ▼
┌─────────────────┐
│   FastAPI App   │
│   (Middleware)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Routes     │
│  (Validation)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│    Services     │────▶│   LLM Client    │
│ (Business Logic)│     │  (OpenRouter)   │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│    CRUD Layer   │
│   (SQLModel)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Database     │
│ (PostgreSQL/    │
│    SQLite)      │
└─────────────────┘
```

### LLM Integration

The system uses the `instructor` library to enforce structured outputs from LLMs:

```python
from instructor import from_openai
from pydantic import BaseModel

class GeneratedQuestions(BaseModel):
    questions: list[Question]
    summary: str

# Instructor wraps the OpenAI client for structured outputs
client = from_openai(openai_client)
result = client.chat.completions.create(
    response_model=GeneratedQuestions,
    messages=[...],
)
# result is type-safe GeneratedQuestions instance
```

### Key Design Decisions

1. **OpenRouter as LLM Gateway**: Single API for multiple models (Gemini, Claude, GPT-4), easy model switching via configuration.

2. **SQLModel**: Unified ORM and Pydantic validation, reducing code duplication between database models and API schemas.

3. **Optional Authentication**: Generation endpoints work without auth for quick testing, but save to user accounts when authenticated.

4. **Canvas Flow**: Multi-turn refinement conversations stored in memory (demo) or database (production) for iterative question editing.

5. **Structured Outputs**: Using instructor library ensures LLM responses match expected Pydantic schemas, providing type safety and validation.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linting (`ruff check . && ruff format .`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## Support

For questions or issues:
- Open an issue on GitHub
- Check the API documentation at `/api/v1/docs`
- Review the OpenAPI schema at `/api/v1/openapi.json`
