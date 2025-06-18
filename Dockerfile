# Multi-stage build for the agent system with Python 3.13
FROM python:3.13-slim AS base

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Add metadata
LABEL maintainer="algent-system" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="algent-system" \
      org.label-schema.description="Scalable Agent-to-Agent communication system with MCP" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    # Network tools
    curl \
    wget \
    netcat-openbsd \
    # Git for version control
    git \
    # Additional utilities
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN python3 --version && \
    pip3 --version

# Builder stage
FROM base AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Production stage
FROM base AS production

# Create non-root user
RUN groupadd -r agentic && useradd -r -g agentic agentic

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=agentic:agentic src/ ./src/
COPY --chown=agentic:agentic pyproject.toml .

# Copy build context to temp for conditional copying
COPY . /tmp/build/

# Copy optional files if they exist (using shell commands)
RUN if [ -d "/tmp/build/examples" ]; then cp -r /tmp/build/examples ./; fi && \
    if [ -d "/tmp/build/config" ]; then cp -r /tmp/build/config ./; fi && \
    if [ -f "/tmp/build/api_server.py" ]; then cp /tmp/build/api_server.py ./; fi && \
    rm -rf /tmp/build

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R agentic:agentic /app

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Starting Algent System Agent Runner"\n\
echo "🐍 Python version: $(python3 --version)"\n\
\n\
# Wait for dependencies\n\
echo "⏳ Waiting for Redis..."\n\
while ! nc -z redis 6379; do \n\
    echo "Waiting for Redis..."\n\
    sleep 1\n\
done\n\
echo "✅ Redis is ready"\n\
\n\
# Check what'\''s available and start accordingly\n\
if [ "$RUN_DEMO_AGENTS" = "true" ] && [ -f "examples/simple_agent.py" ]; then\n\
    echo "🤖 Starting demo agents..."\n\
    exec python3 examples/simple_agent.py --mode demo\n\
elif [ -f "src/cli.py" ]; then\n\
    echo "🎮 CLI available - starting in standby mode"\n\
    echo "Use '\''algent'\'' commands to interact with the system"\n\
    while true; do sleep 60; done\n\
else\n\
    echo "💤 Agent runner in standby mode"\n\
    echo "Container is ready for manual interaction"\n\
    while true; do sleep 60; done\n\
fi' > /app/start_runner.sh

RUN chmod +x /app/start_runner.sh && chown agentic:agentic /app/start_runner.sh

# Switch to non-root user
USER agentic

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD pgrep -f python3 || exit 1

# Expose port
EXPOSE 8000

# Start the runner
CMD ["/app/start_runner.sh"]

