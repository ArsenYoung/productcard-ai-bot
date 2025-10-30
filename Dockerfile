FROM python:3.11-slim

# Environment hygiene and faster, cleaner installs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

# Run as non-root user for safety
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# The bot uses long polling; no ports need to be exposed
CMD ["python", "-m", "bot.main"]

