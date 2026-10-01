# ============================================================================
# Python Dockerfile — Smart entrypoint with auto-detection
# ============================================================================

FROM python:3.12-slim

# Install system dependencies commonly needed by Python projects
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONHTTPSVERIFY=0 \
    CURL_CA_BUNDLE="" \
    REQUESTS_CA_BUNDLE="" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY requirements*.txt Pipfile* pyproject.toml* setup.py* setup.cfg* ./

# Install dependencies based on what's available
RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    elif [ -f Pipfile ]; then \
      pip install --no-cache-dir pipenv && pipenv install --system --deploy; \
    elif [ -f pyproject.toml ]; then \
      pip install --no-cache-dir .; \
    elif [ -f setup.py ]; then \
      pip install --no-cache-dir .; \
    fi

# Copy the rest of the application source
COPY . .

# Re-run install in case COPY . . brought in additional package data
RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    elif [ -f pyproject.toml ] && [ ! -f Pipfile ]; then \
      pip install --no-cache-dir .; \
    fi

EXPOSE 8000

# Create the smart entrypoint script
RUN echo '#!/bin/sh' > /app/docker-entrypoint.sh && \
    echo 'set -e' >> /app/docker-entrypoint.sh && \
    echo 'echo "🚀 LocalDeploy — Python container starting..."' >> /app/docker-entrypoint.sh && \
    echo 'APP_PORT="${PORT:-8000}"' >> /app/docker-entrypoint.sh && \
    echo 'if [ -f init_setup.py ]; then' >> /app/docker-entrypoint.sh && \
    echo '  echo "▶️ Running init_setup.py..."' >> /app/docker-entrypoint.sh && \
    echo '  python init_setup.py || true' >> /app/docker-entrypoint.sh && \
    echo 'fi' >> /app/docker-entrypoint.sh && \
    echo 'if [ -f manage.py ]; then' >> /app/docker-entrypoint.sh && \
    echo '  echo "▶️ Running migrations..."' >> /app/docker-entrypoint.sh && \
    echo '  python manage.py migrate --noinput || true' >> /app/docker-entrypoint.sh && \
    echo '  echo "▶️ Starting via: python manage.py runserver"' >> /app/docker-entrypoint.sh && \
    echo '  exec python manage.py runserver "0.0.0.0:${APP_PORT}"' >> /app/docker-entrypoint.sh && \
    echo 'fi' >> /app/docker-entrypoint.sh && \
    echo 'if command -v gunicorn >/dev/null 2>&1 && [ -f wsgi.py ]; then' >> /app/docker-entrypoint.sh && \
    echo '  exec gunicorn wsgi:application --bind "0.0.0.0:${APP_PORT}" --workers 4' >> /app/docker-entrypoint.sh && \
    echo 'fi' >> /app/docker-entrypoint.sh && \
    echo 'for entry in main.py app.py server.py run.py src/main.py src/app.py; do' >> /app/docker-entrypoint.sh && \
    echo '  if [ -f "$entry" ]; then' >> /app/docker-entrypoint.sh && \
    echo '    exec python "$entry"' >> /app/docker-entrypoint.sh && \
    echo '  fi' >> /app/docker-entrypoint.sh && \
    echo 'done' >> /app/docker-entrypoint.sh && \
    echo 'echo "❌ No start command or entry point found!"' >> /app/docker-entrypoint.sh && \
    echo 'exit 1' >> /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
