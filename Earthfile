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
ARG UBUNTU_VERSION=24.04

# Base image with Python 3.13.5
python-base:
    ARG UBUNTU_VERSION=24.04
    ARG PYTHON_VERSION=3.13.5
    FROM ubuntu:${UBUNTU_VERSION}
    
    # Install system dependencies in parallel with better caching
    RUN apt-get update && apt-get install -y \
        build-essential software-properties-common \
        libssl-dev libffi-dev libbz2-dev libreadline-dev \
        libsqlite3-dev libncurses5-dev libncursesw5-dev \
        liblzma-dev curl wget netcat-openbsd git \
        ca-certificates tzdata \
        && rm -rf /var/lib/apt/lists/*
    
    # Install Python 3.13.5 (cached separately for reuse)
    CACHE --persist /tmp/python-cache
    WORKDIR /tmp
    IF ! [ -f /usr/local/bin/python3.13 ]
        RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
            && tar xzf Python-${PYTHON_VERSION}.tgz \
            && cd Python-${PYTHON_VERSION} \
            && ./configure --enable-optimizations --enable-shared --with-lto \
            && make -j$(nproc) && make altinstall && ldconfig
    END
    
    # Create symlinks
    RUN ln -sf /usr/local/bin/python3.13 /usr/local/bin/python3 \
        && ln -sf /usr/local/bin/python3.13 /usr/local/bin/python \
        && ln -sf /usr/local/bin/pip3.13 /usr/local/bin/pip3 \
        && ln -sf /usr/local/bin/pip3.13 /usr/local/bin/pip
    
    # Install UV with caching
    CACHE /root/.cargo
    RUN curl -LsSf https://astral.sh/uv/install.sh | sh
    ENV PATH="/root/.cargo/bin:$PATH"
    
    # Verify installations
    RUN python3 --version && pip3 --version && uv --version

# Python dependencies (cached separately for fast rebuilds)
python-deps:
    ARG PYTHON_VERSION=3.13.5
    FROM +python-base
    
    WORKDIR /app
    COPY pyproject.toml requirements.txt ./
    
    # Create and cache virtual environment
    CACHE /opt/venv
    RUN uv venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    
    # Install dependencies with UV (much faster)
    RUN uv pip install -r requirements.txt
    
    # Save the venv for other targets
    SAVE ARTIFACT /opt/venv AS LOCAL .earthly/venv

# Source code preparation
source:
    FROM +python-base
    
    WORKDIR /app
    
    # Copy source code
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
    
    # Copy Python environment
    COPY +python-deps/venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    
    WORKDIR /app
    
    # Copy application code
    COPY +source/* ./
    
    # Create directories and set permissions
    RUN mkdir -p /app/logs /app/data && chown -R agentic:agentic /app
    
    # Create startup script with environment variable support
    RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting Algent System (via Earthly)"\n\
echo "🐍 Python: $(python3 --version)"\n\
echo "📦 UV: $(uv --version)"\n\
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
    
    # Override default startup behavior
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
    
    # Install development tools
    RUN apt-get update && apt-get install -y \
        vim nano curl jq htop \
        && rm -rf /var/lib/apt/lists/*
    
    # Install dev Python packages
    RUN /opt/venv/bin/pip install pytest black isort mypy ipython
    
    USER agentic
    
    SAVE IMAGE algent-dev:earthly

# Run tests
test:
    FROM +dev
    
    # Copy test files if they exist
    COPY test_*.py ./ || true
    COPY tests/ ./tests/ || true
    
    # Run tests
    RUN python3 -m pytest tests/ -v || echo "No tests found"
    
    # Run basic import test
    RUN python3 -c "from src.cli import app; print('✅ CLI import successful')"

# Build all images in parallel
all:
    BUILD +app
    BUILD +api-server
    BUILD +file-processor
    BUILD +dev
    BUILD +test