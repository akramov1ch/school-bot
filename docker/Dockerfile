FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Make sure /app is on import path so Alembic (and anything executed as a script) can import "app"
ENV PYTHONPATH=/app

# System deps (build tools for some wheels + curl for health/debug)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    ca-certificates \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

# Timezone (Uzbekistan)
ENV TZ=Asia/Tashkent

WORKDIR /app

# Install python deps first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r /app/requirements.txt

# Copy project code
COPY . /app

# (Optional but recommended) create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose FastAPI port (bot uses polling outbound only)
EXPOSE 8000

# Entrypoint runs migrations then starts bot+api
ENTRYPOINT ["bash", "docker/entrypoint.sh"]