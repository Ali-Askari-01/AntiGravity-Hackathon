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

# Seed the database at build time
RUN cd /app && python -c "from backend.database import engine, Base; from backend import models; Base.metadata.create_all(bind=engine)" || true
RUN cd /app && python backend/seed_providers.py || true

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]