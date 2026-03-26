FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r backend/requirements.txt

# Copy application code
COPY backend ./backend
COPY reference_data ./reference_data
COPY memory ./memory

# Expose the port Cloud Run will send traffic to
EXPOSE 8080

# Start the FastAPI app via uvicorn
# Cloud Run sets $PORT; default to 8080 for local runs.
CMD ["sh", "-c", "uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8080}"]

