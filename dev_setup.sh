#!/bin/bash

# Development setup for Agentic CLI

echo "🛠️ Setting up development environment..."

# Check if in git repo
if [[ ! -d ".git" ]]; then
    echo "Initializing git repository..."
    git init
    
    # Create .gitignore
    cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
.venv/
env/
.env
agentic-env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Data
data/
uploads/

# SSL
ssl/*.key
ssl/*.crt

# Config
config/keys/
.agentic/
GITIGNORE
fi

# Install development dependencies
echo "📦 Installing development dependencies..."

if command -v uv >/dev/null 2>&1; then
    uv pip install -e ".[dev]"
else
    pip install -e ".[dev]"
fi

# Setup pre-commit hooks
if command -v pre-commit >/dev/null 2>&1; then
    echo "🪝 Setting up pre-commit hooks..."
    
    cat > .pre-commit-config.yaml << 'PRECOMMIT'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
PRECOMMIT
    
    pre-commit install
    echo "✅ Pre-commit hooks installed"
fi

# Create test structure
mkdir -p tests
cat > tests/test_cli.py << 'PYTEST'
"""
Tests for the Agentic CLI
"""

import pytest
from typer.testing import CliRunner
from agentic_cli import app

runner = CliRunner()

def test_cli_help():
    """Test CLI help command"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Agentic System CLI" in result.stdout

def test_cli_version():
    """Test CLI version command"""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Version: 1.0.0" in result.stdout

def test_config_list():
    """Test config list command"""
    result = runner.invoke(app, ["config", "--list"])
    assert result.exit_code == 0

# Add more tests as needed
PYTEST

echo "🧪 Created test structure"

echo "✅ Development environment setup complete!"
echo ""
echo "🚀 Quick start:"
echo "  python3 agentic_cli.py --help"
echo "  python3 agentic_cli.py start"
echo "  python3 agentic_cli.py monitor"
echo ""
echo "🧪 Run tests:"
echo "  pytest tests/"
echo ""
echo "🔍 Code quality:"
echo "  black ."
echo "  isort ."
echo "  mypy agentic_cli.py"
