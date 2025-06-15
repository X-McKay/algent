#!/bin/bash

# Fixed Agentic CLI Installation Script

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${PURPLE}"
echo "========================================="
echo "   Algent CLI Installation (Fixed)"
echo "   Python 3.13.5 + Typer + Rich"
echo "========================================="
echo -e "${NC}"

# Check Python version
log_info "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
major_version=$(echo "$python_version" | cut -d. -f1)
minor_version=$(echo "$python_version" | cut -d. -f2)

if [[ $major_version -lt 3 ]] || [[ $major_version -eq 3 && $minor_version -lt 11 ]]; then
    log_error "Python 3.11+ is required. Found: $python_version"
    exit 1
fi

log_success "Python version: $python_version"

# Check if pyproject.toml exists
if [[ ! -f "pyproject.toml" ]]; then
    log_error "pyproject.toml not found. Make sure you're in the project directory."
    exit 1
fi

# Check if src/cli.py exists
if [[ ! -f "src/cli.py" ]]; then
    log_error "src/cli.py not found. The CLI structure may not be set up correctly."
    exit 1
fi

log_success "Found project files"

# Check if in virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
    log_info "Using virtual environment: $VIRTUAL_ENV"
else
    log_warning "No virtual environment detected"
    if command -v uv >/dev/null 2>&1; then
        log_info "Creating virtual environment with UV..."
        uv venv algent-env
        source algent-env/bin/activate
        export PATH="$PWD/algent-env/bin:$PATH"
    else
        log_info "Creating virtual environment with Python..."
        python3 -m venv algent-env
        source algent-env/bin/activate
        export PATH="$PWD/algent-env/bin:$PATH"
    fi
fi

# Install dependencies
log_info "Installing Algent package..."

if command -v uv >/dev/null 2>&1; then
    log_info "Using UV for fast installation..."
    uv pip install -e .
else
    log_info "Using pip for installation..."
    pip install --upgrade pip
    pip install -e .
fi

# Test the installation
log_info "Testing CLI installation..."

if command -v agentic >/dev/null 2>&1; then
    log_success "CLI 'agentic' command installed successfully!"
    agentic --version
else
    log_warning "Command 'agentic' not found in PATH"
fi

if command -v algent >/dev/null 2>&1; then
    log_success "CLI 'algent' command installed successfully!"
    algent --version
else
    log_warning "Command 'algent' not found in PATH"
fi

# Test direct Python import
log_info "Testing Python module import..."
if python3 -c "from src.cli import app; print('✅ CLI module import successful')" 2>/dev/null; then
    log_success "Python module import works"
else
    log_error "Python module import failed"
    exit 1
fi

log_success "Installation completed!"
echo ""
log_info "Available commands:"
echo "  agentic --help    # Original command name"
echo "  algent --help     # Short command name"
echo ""
log_info "Example usage:"
echo "  algent start"
echo "  algent agents list"
echo "  algent monitor"
