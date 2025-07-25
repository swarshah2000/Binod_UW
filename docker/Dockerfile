# TT FIX Order Adapter Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY FIX_SCHEMA/ ./FIX_SCHEMA/
COPY main.py .

# Copy certificates (will be mounted in production)
COPY *.crt ./
COPY *.key ./

# Create data directories
RUN mkdir -p data/logs data/fix_store

# Set Python path
ENV PYTHONPATH=/app/src

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose ports
EXPOSE 5555 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# Default command
CMD ["python", "main.py"]
