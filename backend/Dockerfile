FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for submissions and tests
RUN mkdir -p /app/submissions /app/tests

# Cloud Run injects $PORT (8080); local Docker Compose pins it via ENV for the 8000:8000 mapping.
ENV PORT=8000
EXPOSE 8000

CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} 