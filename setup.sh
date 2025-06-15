#!/bin/bash

# Setup script for local development using uv

echo "🚀 Setting up Algent..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📍 Python version: $python_version"

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create and activate virtual environment
echo "🐍 Creating Python virtual environment..."
uv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
uv pip install -e ".[dev]"

# Create directories
echo "📁 Creating directories..."
mkdir -p logs data config/keys

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Activate the virtual environment: source .venv/bin/activate"
echo "2. Start Redis: redis-server (or docker run -d -p 6379:6379 redis:7-alpine)"
echo "3. Run the demo: python examples/simple_agent.py --mode demo"
echo "4. Or use Docker: docker-compose up"
