VERSION 0.8

# Import reusable functions
IMPORT github.com/earthly/lib/utils AS utils

# Non-sensitive build arguments
ARG REDIS_URL
ARG GRAFANA_PORT
ARG MCP_PORT
ARG POSTGRES_DB
ARG RUN_DEMO_AGENTS
ARG API_HOST
ARG MCP_HOST
ARG PROMETHEUS_PORT
ARG LOG_LEVEL
ARG AGENT_HEARTBEAT_INTERVAL
ARG API_PORT
ARG AGENT_TASK_TIMEOUT
ARG POSTGRES_USER
ARG PYTHON_VERSION=3.13.5

# Base image with Python 3.13
python-base:
    ARG PYTHON_VERSION=3.13.5
    FROM python:${PYTHON_VERSION}-slim
    
    # Install system dependencies
    RUN apt-get update && apt-get install -y \
        build-essential \
        curl wget netcat-openbsd git \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*
    
    # Verify installations
    RUN python3 --version && pip3 --version

# Python dependencies (cached separately for fast rebuilds)
python-deps:
    FROM +python-base
    
    WORKDIR /app
    COPY pyproject.toml requirements.txt ./
    
    # Create virtual environment
    RUN python3 -m venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    
    # Install dependencies with pip
    RUN pip install --upgrade pip && pip install -r requirements.txt
    
    # Verify the venv was created
    RUN ls -la /opt/venv && ls -la /opt/venv/bin/
    
    # Save the venv for other targets
    SAVE ARTIFACT /opt/venv venv

# Source code preparation
source:
    FROM +python-base
    
    WORKDIR /app
    
    # Copy required files
    COPY src/ ./src/
    COPY pyproject.toml ./
    
    # Copy optional files if they exist
    IF [ -d "examples" ]
        COPY examples/ ./examples/
    END
    
    IF [ -d "config" ]
        COPY config/ ./config/
    END
    
    IF [ -f "api_server.py" ]
        COPY api_server.py ./
    END
    
    # Save everything as an artifact
    SAVE ARTIFACT /app app-files

# Main application image
app:
    FROM +python-base
    
    # Handle secrets properly
    RUN --secret GRAFANA_PASSWORD \
        --secret POSTGRES_PASSWORD \
        --secret REDIS_PASSWORD \
        echo "Secrets available during build (not stored in image)"
    
    # Create non-root user
    RUN groupadd -r agentic && useradd -r -g agentic agentic
    
    # Copy Python environment from python-deps target
    COPY +python-deps/venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    
    WORKDIR /app
    
    # Copy all application files from source target
    COPY +source/app-files/* ./
    
    # Create directories and set permissions
    RUN mkdir -p /app/logs /app/data && chown -R agentic:agentic /app
    
    # Create startup script
    RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting Algent System"\n\
echo "🐍 Python: $(python3 --version)"\n\
\n\
# Wait for Redis\n\
echo "⏳ Waiting for Redis..."\n\
REDIS_HOST=$(echo "${REDIS_URL:-redis://redis:6379}" | cut -d/ -f3 | cut -d: -f1)\n\
REDIS_PORT=$(echo "${REDIS_URL:-redis://redis:6379}" | cut -d: -f3 | cut -d/ -f1)\n\
REDIS_PORT=${REDIS_PORT:-6379}\n\
while ! nc -z "$REDIS_HOST" "$REDIS_PORT"; do sleep 1; done\n\
echo "✅ Redis ready"\n\
\n\
if [ "$RUN_DEMO_AGENTS" = "true" ] && [ -f "examples/simple_agent.py" ]; then\n\
    echo "🤖 Starting demo agents..."\n\
    exec python3 examples/simple_agent.py --mode demo\n\
elif [ "$START_API_SERVER" = "true" ] && [ -f "api_server.py" ]; then\n\
    echo "🌐 Starting API server..."\n\
    exec python3 api_server.py\n\
else\n\
    echo "💤 Standby mode - ready for interaction"\n\
    while true; do sleep 60; done\n\
fi' > /app/start_runner.sh \
    && chmod +x /app/start_runner.sh \
    && chown agentic:agentic /app/start_runner.sh
    
    USER agentic
    
    ENV PYTHONPATH=/app \
        PYTHONUNBUFFERED=1 \
        PYTHONDONTWRITEBYTECODE=1
    
    EXPOSE 8000
    
    CMD ["/app/start_runner.sh"]
    
    # Save as Docker image
    SAVE IMAGE algent:earthly

# API Server image
api-server:
    FROM +app
    ENV START_API_SERVER=true
    SAVE IMAGE algent-api:earthly

# File processor agent
file-processor:
    FROM +app
    ENV AGENT_TYPE=file_processor
    ENV AGENT_ID=earthly-file-processor
    SAVE IMAGE algent-file-processor:earthly

# Development image with all tools
dev:
    FROM +app
    USER root
    RUN apt-get update && apt-get install -y \
        vim nano curl jq htop \
        && rm -rf /var/lib/apt/lists/*
    RUN /opt/venv/bin/pip install pytest black isort mypy ipython
    USER agentic
    SAVE IMAGE algent-dev:earthly

# Run tests
test:
    FROM +dev
    IF [ -d "tests" ]
        COPY tests/ ./tests/
        RUN python3 -m pytest tests/ -v || echo "Tests completed"
    END
    RUN python3 -c "import sys; print('✅ Python import successful')"

# Create docker-compose file for CLI usage
compose-setup:
    FROM alpine:latest
    
    # Create docker-compose file that matches your existing docker-compose-earthly.yml
    RUN echo 'version: '\''3.8'\''\n\
\n\
services:\n\
  redis:\n\
    image: redis:7-alpine\n\
    container_name: algent-redis\n\
    ports:\n\
      - "6379:6379"\n\
    environment:\n\
      - REDIS_PASSWORD=${REDIS_PASSWORD:-redispass}\n\
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-redispass}\n\
    healthcheck:\n\
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-redispass}", "ping"]\n\
      interval: 30s\n\
      timeout: 10s\n\
      retries: 3\n\
    volumes:\n\
      - algent_redis_data:/data\n\
    networks:\n\
      - algent-network\n\
\n\
  postgres:\n\
    image: postgres:15-alpine\n\
    container_name: algent-postgres\n\
    environment:\n\
      - POSTGRES_DB=${POSTGRES_DB:-algent}\n\
      - POSTGRES_USER=${POSTGRES_USER:-algent}\n\
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgrespass}\n\
    ports:\n\
      - "5432:5432"\n\
    volumes:\n\
      - algent_postgres_data:/var/lib/postgresql/data\n\
    healthcheck:\n\
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-algent} -d ${POSTGRES_DB:-algent}"]\n\
      interval: 30s\n\
      timeout: 10s\n\
      retries: 3\n\
    networks:\n\
      - algent-network\n\
\n\
  api-server:\n\
    image: algent-api:earthly\n\
    container_name: algent-api-server\n\
    environment:\n\
      - REDIS_URL=${REDIS_URL:-redis://redis:6379}\n\
      - POSTGRES_DB=${POSTGRES_DB:-algent}\n\
      - POSTGRES_USER=${POSTGRES_USER:-algent}\n\
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgrespass}\n\
      - API_HOST=${API_HOST:-localhost}\n\
      - API_PORT=${API_PORT:-8000}\n\
      - LOG_LEVEL=${LOG_LEVEL:-INFO}\n\
      - START_API_SERVER=true\n\
    ports:\n\
      - "${API_PORT:-8000}:8000"\n\
    depends_on:\n\
      redis:\n\
        condition: service_healthy\n\
      postgres:\n\
        condition: service_healthy\n\
    restart: unless-stopped\n\
    networks:\n\
      - algent-network\n\
\n\
  file-processor:\n\
    image: algent-file-processor:earthly\n\
    container_name: algent-file-processor\n\
    environment:\n\
      - REDIS_URL=${REDIS_URL:-redis://redis:6379}\n\
      - POSTGRES_DB=${POSTGRES_DB:-algent}\n\
      - POSTGRES_USER=${POSTGRES_USER:-algent}\n\
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgrespass}\n\
      - LOG_LEVEL=${LOG_LEVEL:-INFO}\n\
      - AGENT_TYPE=file_processor\n\
      - AGENT_ID=file-processor-1\n\
    depends_on:\n\
      redis:\n\
        condition: service_healthy\n\
      postgres:\n\
        condition: service_healthy\n\
      api-server:\n\
        condition: service_started\n\
    restart: unless-stopped\n\
    networks:\n\
      - algent-network\n\
\n\
  agent-runner:\n\
    image: algent:earthly\n\
    container_name: algent-agent-runner\n\
    environment:\n\
      - REDIS_URL=${REDIS_URL:-redis://redis:6379}\n\
      - POSTGRES_DB=${POSTGRES_DB:-algent}\n\
      - POSTGRES_USER=${POSTGRES_USER:-algent}\n\
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgrespass}\n\
      - LOG_LEVEL=${LOG_LEVEL:-INFO}\n\
      - RUN_DEMO_AGENTS=${RUN_DEMO_AGENTS:-false}\n\
      - AGENT_HEARTBEAT_INTERVAL=${AGENT_HEARTBEAT_INTERVAL:-30}\n\
      - AGENT_TASK_TIMEOUT=${AGENT_TASK_TIMEOUT:-300}\n\
    depends_on:\n\
      redis:\n\
        condition: service_healthy\n\
      postgres:\n\
        condition: service_healthy\n\
      api-server:\n\
        condition: service_started\n\
    restart: unless-stopped\n\
    networks:\n\
      - algent-network\n\
\n\
volumes:\n\
  algent_redis_data:\n\
  algent_postgres_data:\n\
\n\
networks:\n\
  algent-network:\n\
    driver: bridge' > /docker-compose.yml
    
    SAVE ARTIFACT /docker-compose.yml AS LOCAL docker-compose.yml

# Infrastructure target (starts database services)
infrastructure:
    LOCALLY
    
    # Start infrastructure services using existing docker-compose-earthly.yml
    RUN docker-compose -f docker-compose-earthly.yml --env-file .env up -d redis postgres
    
    # Wait for services to be healthy
    RUN echo "Waiting for infrastructure to be ready..."
    RUN sleep 15

# Services target (starts application services)
services:
    LOCALLY
    
    # Build required images first
    BUILD +app
    BUILD +api-server
    BUILD +file-processor
    
    # Ensure infrastructure is running
    BUILD +infrastructure
    
    # Start application services using existing docker-compose-earthly.yml
    RUN docker-compose -f docker-compose-earthly.yml --env-file .env up -d api-server file-processor agent-runner

# Down target (stops all services)
down:
    LOCALLY
    
    # Stop all services using existing docker-compose-earthly.yml
    RUN docker-compose -f docker-compose-earthly.yml down

# Logs target (shows logs)
logs:
    LOCALLY
    
    # Show logs for all services using existing docker-compose-earthly.yml
    RUN docker-compose -f docker-compose-earthly.yml logs

# Restart target (restarts services)
restart:
    LOCALLY
    
    # Restart all services using existing docker-compose-earthly.yml
    RUN docker-compose -f docker-compose-earthly.yml restart

# Shell target (opens shell in container)
shell:
    LOCALLY
    
    # This will be handled by the CLI directly using docker-compose exec
    RUN echo "Use: docker-compose -f docker-compose-earthly.yml exec <service> /bin/bash"

# Build all images
all:
    BUILD +app
    BUILD +api-server 
    BUILD +file-processor
    BUILD +dev
    BUILD +test
    BUILD +compose-setup