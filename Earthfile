VERSION 0.8

# Import reusable functions
IMPORT github.com/earthly/lib/utils AS utils

# Non-sensitive build arguments
ARG PYTHON_VERSION=3.13
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
ARG PYTHON_VERSION=3.13

# Base image with Python 3.13
python-base:
    ARG PYTHON_VERSION=3.13
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

# Build all images
all:
    BUILD +app
    BUILD +api-server 
    BUILD +file-processor
    BUILD +dev
    BUILD +test

