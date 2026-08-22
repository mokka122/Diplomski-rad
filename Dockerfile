FROM python:3.14-slim

WORKDIR /app

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first for better Docker cache usage
COPY backend/requirements.txt /app/backend/requirements.txt

RUN pip install --no-cache-dir \
    -r /app/backend/requirements.txt

# Copy backend application
COPY backend /app/backend

# Copy production ML artifacts
COPY ml/models/traffic_classifier_multi_area_tuned.joblib \
     /app/ml/models/traffic_classifier_multi_area_tuned.joblib

COPY ml/models/traffic_classifier_multi_area_tuned_metadata.json \
     /app/ml/models/traffic_classifier_multi_area_tuned_metadata.json

# Runtime directory
WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]