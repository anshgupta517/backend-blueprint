#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."

if [ "${APP_ENV}" = "development" ]; then
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir /app/app \
    --no-access-log
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --no-access-log