# Build stage for frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy frontend files
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY frontend/ ./frontend/

# Create backend/static directory for build output
RUN mkdir -p backend/static

# Build frontend (outputs to backend/static)
RUN cd frontend && npm run build


# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./app

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/backend/static ./static

# Create uploads directory
RUN mkdir -p uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Railway uses dynamic PORT
EXPOSE 3000

# Run the application - use shell form to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000}
