# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY projects/backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application source code & blockchain assets
COPY projects/backend /app/backend
COPY blockchain /app/blockchain

# Create unprivileged application user
RUN useradd -m -u 1000 pokedex && \
    mkdir -p /app/backend/data && \
    chown -R pokedex:pokedex /app

USER pokedex

# Expose HTTP port
EXPOSE 8000

# Healthcheck definition using the readiness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ready || exit 1

# Start production ASGI server with uvicorn respecting dynamic PORT
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --no-access-log"]
