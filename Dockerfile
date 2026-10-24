# ==========================================
# Stage 1: Build React Production Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Python FastAPI Production Server
# ==========================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

# Install runtime and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces expects non-root user with UID 1000
RUN useradd -m -u 1000 user
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Backend Application
COPY backend/ ./

# Copy compiled frontend into static directory for FastAPI SPA serving
COPY --from=frontend-builder --chown=user:user /app/frontend/dist ./static

# Ensure user permissions on uploads and backups directories
RUN mkdir -p uploads backups static && chown -R user:user /app
USER user

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
