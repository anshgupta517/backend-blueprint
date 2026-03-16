# Backend boilerplate

db      → PostgreSQL
redis   → broker + cache + rate limit counters
app     → FastAPI (4 uvicorn workers)
worker  → Celery task executor
flower  → job monitoring dashboard