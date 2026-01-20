"""
Main API Router - Aggregates all route modules.
"""
from fastapi import APIRouter

from app.api.routes import (
    auth_router,
    generation_router,
    refinement_router,
    similarity_router,
)

api_router = APIRouter()

# Authentication
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Core Workflows
api_router.include_router(generation_router, prefix="/generate", tags=["Question Generation"])
api_router.include_router(similarity_router, prefix="/similar", tags=["Similarity Generation"])
api_router.include_router(refinement_router, prefix="/refine", tags=["Interactive Refinement"])
