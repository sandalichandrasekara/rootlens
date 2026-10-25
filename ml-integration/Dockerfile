# RootLens ML Explainer Service Dockerfile
FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools, compile Python dependencies, then remove build tools
# in a single RUN layer to keep the final image small
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY predictor_service.py .
COPY features/ ./features/

# Copy trained models
COPY results/explainers/ ./results/explainers/

# Create non-root user and transfer ownership
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

# Default to port 5000 for local/K8s; Cloud Run overrides via PORT=8080
ENV PORT=5000 \
    FLASK_DEBUG=False

EXPOSE 5000

CMD ["sh", "-c", "exec gunicorn --bind :$PORT --workers 1 --threads 2 --timeout 60 predictor_service:app"]
