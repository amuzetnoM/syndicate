# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
#
# Multi-stage Dockerfile for production deployment
# Build: docker build -t syndicate .
# Run:   docker run -d --name syndicate syndicate
#
# ══════════════════════════════════════════════════════════════════════════════

# =============================================================================
# Stage 1: Builder - Install dependencies and compile
# =============================================================================
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.12-slim as runtime

# Labels for GitHub Container Registry
LABEL org.opencontainers.image.source="https://github.com/amuzetnoM/gold_standard"
LABEL org.opencontainers.image.description="Syndicate - Autonomous Precious Metals Intelligence System"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.title="Syndicate"
LABEL org.opencontainers.image.vendor="SIRIUS Alpha"
LABEL org.opencontainers.image.version="3.7.0"

# Security: Run as non-root user
RUN groupadd -r goldstandard && useradd -r -g goldstandard goldstandard

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=goldstandard:goldstandard . .

# Create necessary directories
RUN mkdir -p /app/data /app/output /app/output/reports /app/output/charts /app/output/research \
    && chown -R goldstandard:goldstandard /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    TZ=UTC

# Health check - verifies the system can import and run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from db_manager import get_db; db = get_db(); print('healthy')" || exit 1

# Switch to non-root user
USER goldstandard

# Default command: Run daemon with 5-minute intervals
CMD ["python", "run.py", "--interval-min", "5"]

# =============================================================================
# Stage 3: Development - Full dev environment with extras
# =============================================================================
FROM runtime as development

USER root

# Install dev dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    less \
    && rm -rf /var/lib/apt/lists/*

# Install dev Python packages
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

USER goldstandard

# Override for development: interactive mode
CMD ["python", "run.py", "--interactive"]
