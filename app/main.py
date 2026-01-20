"""
Socratic AI Backend - FastAPI Application Entry Point.

AI-powered educational question generation with three core workflows:
1. Document-Based Generation: PDF/text -> questions
2. Similarity Generation: Question -> similar questions
3. Interactive Refinement: Canvas-like question editing
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs on startup and shutdown."""
    # Startup: Create database tables
    SQLModel.metadata.create_all(engine)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
## Socratic AI Backend

AI-powered question generation for educational content.

### Core Workflows

1. **Document-Based Generation** (`/api/v1/generate`)
   - Upload PDF or provide text content
   - Generate MCQ and open-ended questions
   - Includes explanations and confidence scores

2. **Similarity Generation** (`/api/v1/similar`)
   - Analyze existing questions
   - Generate similar questions with same difficulty/format
   - Useful for creating question banks

3. **Interactive Refinement** (`/api/v1/refine`)
   - Canvas-like editing flow
   - Natural language instructions to modify questions
   - Multi-turn conversation support

### Authentication

Optional JWT authentication for saving questions to database.
Most endpoints work without authentication for quick testing.
    """,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "docs": f"{settings.API_V1_STR}/docs",
        "workflows": {
            "generation": f"{settings.API_V1_STR}/generate",
            "similarity": f"{settings.API_V1_STR}/similar",
            "refinement": f"{settings.API_V1_STR}/refine",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy"}
