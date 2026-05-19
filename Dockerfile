FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the entire project
COPY . /app/

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8000

# Use shell form to allow env var expansion
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
