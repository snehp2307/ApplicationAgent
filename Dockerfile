# ============================================
# BULK AI JOB OUTREACH BOT - Dockerfile
# ============================================
# Containerized Python app using LangChain +
# LangGraph + Mistral AI for bulk job outreach.
#
# Build:  docker-compose up --build
# ============================================

# --- Stage: Base image ---
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
# so container logs show print() statements in real-time
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# --- Stage: Install dependencies first (Docker layer cache) ---
# Copying requirements.txt separately means Docker will only
# re-install packages when requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --- Stage: Copy project source code ---
COPY . .

# --- Stage: Create required directories ---
# These directories will be overridden by volume mounts at runtime,
# but we create them here so the app doesn't crash if volumes
# are not mounted.
RUN mkdir -p /app/output /app/resume

# --- Entry point ---
# Run the main script. stdin_open + tty in docker-compose
# allow interactive input (job role, location, confirmation).
CMD ["python", "main.py"]
