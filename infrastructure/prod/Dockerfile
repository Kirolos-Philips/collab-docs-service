# Production Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install production dependencies only
RUN uv sync --frozen --extra prod --no-dev || uv sync --extra prod --no-dev


# Stage 2: Production image
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy uv and virtual environment from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appgroup src/ ./src/

# Set ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production command with gunicorn + uvicorn workers
CMD ["/app/.venv/bin/gunicorn", "src.main:app", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
