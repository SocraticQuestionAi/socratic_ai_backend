#!/bin/bash
# Development server startup script

set -e

# Change to project root directory (parent of scripts/)
cd "$(dirname "$0")/.."

# Run with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
