# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (Windows compatible)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 scanner && chown -R scanner:scanner /app
USER scanner

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV SELENIUM_GRID_ENABLED=true

# Run the application
CMD ["python", "main.py"]