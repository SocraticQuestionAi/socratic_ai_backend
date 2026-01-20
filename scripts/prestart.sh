#!/bin/bash
# Prestart script - run before the application starts

set -e

echo "Running database migrations..."
alembic upgrade head

echo "Prestart complete!"
