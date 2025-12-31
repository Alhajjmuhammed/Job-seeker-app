# Worker Connect API - Dockerfile
# Multi-stage build for production deployment

# =============================================================================
# Stage 1: Base Python image with dependencies
# =============================================================================
FROM python:3.11-slim as base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # pip
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # poetry
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for PostgreSQL
    libpq-dev \
    # Required for building Python packages
    gcc \
    python3-dev \
    # Required for WeasyPrint (PDF generation)
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Stage 2: Builder - Install Python dependencies
# =============================================================================
FROM base as builder

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 3: Production image
# =============================================================================
FROM base as production

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appgroup . .

# Create directories for static files, media, and logs
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R appuser:appgroup /app/staticfiles /app/media /app/logs

# Switch to non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Default command - use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "worker_connect.wsgi:application"]

# =============================================================================
# Stage 4: Development image (optional)
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    debugpy \
    django-debug-toolbar \
    ipython

USER appuser

# Use Django's development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
