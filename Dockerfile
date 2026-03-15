# ── Stage 1: Builder ──────────────────────────────────────────────────────────
# We use a separate build stage so the final image doesn't contain
# build tools, compilers, or cache — keeps it small and secure
FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml .

RUN pip install uv && \
    uv pip install --system -e ".[dev]"


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
# Start fresh from slim — copy only what we need from builder
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# The entrypoint script handles migrations + server startup
# We use a script rather than inline commands for readability and flexibility
ENTRYPOINT ["sh", "scripts/start.sh"]