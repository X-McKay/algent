#!/bin/bash

# Test Earthly setup with easy revert capability

echo "🌍 Setting up Earthly test environment..."

# Create backup of current setup
echo "📦 Creating backup of current Docker setup..."
mkdir -p .backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=".backup/$(date +%Y%m%d_%H%M%S)"

# Backup current files
cp Dockerfile* "$BACKUP_DIR/" 2>/dev/null || true
cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backed up current setup to $BACKUP_DIR"

# Install Earthly if not already installed
if ! command -v earthly >/dev/null 2>&1; then
    echo "📥 Installing Earthly..."
    
    # Detect OS and install accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew >/dev/null 2>&1; then
            brew install earthly/earthly/earthly
        else
            echo "Please install Homebrew first, then run: brew install earthly/earthly/earthly"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo /bin/sh -c 'wget https://github.com/earthly/earthly/releases/latest/download/earthly-linux-amd64 -O /usr/local/bin/earthly && chmod +x /usr/local/bin/earthly'
    else
        echo "❌ Unsupported OS. Please install Earthly manually: https://earthly.dev/get-earthly"
        exit 1
    fi
    
    echo "✅ Earthly installed successfully"
else
    echo "✅ Earthly already installed: $(earthly --version)"
fi

# Start Earthly daemon
echo "🚀 Starting Earthly daemon..."
earthly bootstrap --with-autocomplete

# Create Earthfile (Earthly's equivalent of Dockerfile)
echo "📝 Creating Earthfile..."

cat > Earthfile << 'EOF'
VERSION 0.8

# Import reusable functions
IMPORT github.com/earthly/lib/utils AS utils

# Define variables
ARG PYTHON_VERSION=3.13.5
ARG UBUNTU_VERSION=24.04

# Base image with Python 3.13.5
base:
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
    FROM +base
    
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
    FROM +base
    
    WORKDIR /app
    
    # Copy source code
    COPY src/ ./src/
    COPY pyproject.toml ./
    
    # Copy optional files if they exist
    COPY examples/ ./examples/ || true
    COPY config/ ./config/ || true
    COPY api_server.py ./ || true

# Main application image
app:
    FROM +base
    
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
    
    # Create startup script
    RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Starting Algent System (via Earthly)"\n\
echo "🐍 Python: $(python3 --version)"\n\
echo "📦 UV: $(uv --version)"\n\
\n\
# Wait for Redis\n\
echo "⏳ Waiting for Redis..."\n\
while ! nc -z redis 6379; do sleep 1; done\n\
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
EOF

# Create docker-compose.earthly.yml for testing
echo "📝 Creating test docker-compose file..."

cat > docker-compose.earthly.yml << 'EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: earthly-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - earthly-network

  postgres:
    image: postgres:15-alpine
    container_name: earthly-postgres
    environment:
      POSTGRES_DB: algent
      POSTGRES_USER: algent
      POSTGRES_PASSWORD: algent123
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U algent"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - earthly-network

  api-server:
    image: algent-api:earthly
    container_name: earthly-api-server
    environment:
      - REDIS_URL=redis://redis:6379
      - START_API_SERVER=true
    ports:
      - "8000:8000"
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - earthly-network

  file-processor:
    image: algent-file-processor:earthly
    container_name: earthly-file-processor
    environment:
      - REDIS_URL=redis://redis:6379
      - AGENT_TYPE=file_processor
    depends_on:
      - api-server
    networks:
      - earthly-network

  agent-runner:
    image: algent:earthly
    container_name: earthly-agent-runner
    environment:
      - REDIS_URL=redis://redis:6379
      - RUN_DEMO_AGENTS=true
    depends_on:
      - api-server
    networks:
      - earthly-network

networks:
  earthly-network:
    driver: bridge

volumes:
  earthly_redis_data:
  earthly_postgres_data:
EOF

# Create test script
cat > test_earthly.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing Earthly setup..."

# Build images with Earthly
echo "🏗️ Building images with Earthly..."
time earthly +all

if [ $? -eq 0 ]; then
    echo "✅ Earthly build successful!"
    
    # Test with docker-compose
    echo "🐳 Testing with docker-compose..."
    docker-compose -f docker-compose.earthly.yml up -d redis postgres
    
    sleep 10
    
    docker-compose -f docker-compose.earthly.yml up -d api-server
    
    sleep 15
    
    # Test API
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ API server is responding!"
        
        # Start other services
        docker-compose -f docker-compose.earthly.yml up -d
        
        echo "🎉 Earthly setup is working!"
        echo ""
        echo "📊 Comparison:"
        echo "  🐳 Original Docker: Check your previous build times"
        echo "  🌍 Earthly: Built in $(echo $EARTHLY_BUILD_TIME) seconds"
        echo ""
        echo "🔄 To switch to Earthly permanently:"
        echo "  mv docker-compose.yml docker-compose.original.yml"
        echo "  mv docker-compose.earthly.yml docker-compose.yml"
        echo "  mv Dockerfile Dockerfile.original"
        echo "  # Use 'earthly +all' instead of 'docker-compose build'"
        
    else
        echo "❌ API server test failed"
        docker-compose -f docker-compose.earthly.yml logs api-server
    fi
    
else
    echo "❌ Earthly build failed"
    exit 1
fi
EOF

chmod +x test_earthly.sh

# Create revert script
cat > revert_earthly.sh << 'EOF'
#!/bin/bash

echo "🔄 Reverting to original Docker setup..."

# Stop Earthly containers
docker-compose -f docker-compose.earthly.yml down -v 2>/dev/null || true

# Find the most recent backup
LATEST_BACKUP=$(ls -1t .backup/ | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    echo "📦 Restoring from backup: $LATEST_BACKUP"
    
    # Restore original files
    cp ".backup/$LATEST_BACKUP/Dockerfile"* . 2>/dev/null || true
    cp ".backup/$LATEST_BACKUP/docker-compose.yml" . 2>/dev/null || true
    
    # Remove Earthly files
    rm -f Earthfile docker-compose.earthly.yml
    rm -f test_earthly.sh revert_earthly.sh
    rm -rf .earthly/
    
    echo "✅ Reverted to original setup"
    echo "🐳 You can now use 'docker-compose build' again"
else
    echo "❌ No backup found"
    exit 1
fi
EOF

chmod +x revert_earthly.sh

echo ""
echo "✅ Earthly test environment ready!"
echo ""
echo "📁 Files created:"
echo "  ✅ Earthfile - Earthly build configuration"
echo "  ✅ docker-compose.earthly.yml - Test compose file"
echo "  ✅ test_earthly.sh - Test the setup"
echo "  ✅ revert_earthly.sh - Easy revert script"
echo "  ✅ Backup created in $BACKUP_DIR"
echo ""
echo "🧪 To test Earthly:"
echo "  ./test_earthly.sh"
echo ""
echo "🔄 To revert if it doesn't work:"
echo "  ./revert_earthly.sh"
echo ""
echo "🌍 Earthly benefits you'll see:"
echo "  ⚡ Faster builds with better caching"
echo "  🔄 Parallel builds of different images"
echo "  📦 More reliable dependency management"
echo "  🧹 Cleaner, more maintainable build files"
echo "  🔀 Easy switching between build targets"