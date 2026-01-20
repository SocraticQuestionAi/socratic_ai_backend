"""
API Routes Package.

Contains all route modules for the Socratic AI API.
"""
from app.api.routes.auth import router as auth_router
from app.api.routes.generation import router as generation_router
from app.api.routes.refinement import router as refinement_router
from app.api.routes.similarity import router as similarity_router

__all__ = [
    "auth_router",
    "generation_router",
    "similarity_router",
    "refinement_router",
]
