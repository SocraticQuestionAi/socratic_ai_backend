#!/bin/bash
# Development server startup script

set -e

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your API keys"
    exit 1
fi

# Run with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
