#!/bin/bash

# Agentic CLI Installation Script

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
echo "   Agentic System CLI Installation"
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

# Check if in virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
    log_info "Using virtual environment: $VIRTUAL_ENV"
else
    log_warning "No virtual environment detected"
    if command -v uv >/dev/null 2>&1; then
        log_info "Creating virtual environment with UV..."
        uv venv agentic-env
        source agentic-env/bin/activate
        export PATH="$PWD/agentic-env/bin:$PATH"
    else
        log_info "Creating virtual environment with Python..."
        python3 -m venv agentic-env
        source agentic-env/bin/activate
        export PATH="$PWD/agentic-env/bin:$PATH"
    fi
fi

# Install dependencies
log_info "Installing dependencies..."

if command -v uv >/dev/null 2>&1; then
    log_info "Using UV for fast installation..."
    uv pip install -e .
else
    log_info "Using pip for installation..."
    pip install --upgrade pip
    pip install -e .
fi

# Create CLI symlink in PATH
CLI_SCRIPT="agentic_cli.py"
if [[ -f "$CLI_SCRIPT" ]]; then
    chmod +x "$CLI_SCRIPT"
    
    # Try to install in user bin directory
    USER_BIN="$HOME/.local/bin"
    if [[ ! -d "$USER_BIN" ]]; then
        mkdir -p "$USER_BIN"
    fi
    
    # Create wrapper script
    cat > "$USER_BIN/agentic" << 'SCRIPT'
#!/bin/bash
# Agentic CLI wrapper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTIC_DIR="$(dirname "$SCRIPT_DIR")"

# Try to find the CLI script
if [[ -f "$AGENTIC_DIR/agentic_cli.py" ]]; then
    exec python3 "$AGENTIC_DIR/agentic_cli.py" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -c "from agentic_cli import app; app()" "$@"
else
    echo "Error: Cannot find agentic CLI script"
    exit 1
fi
SCRIPT
    
    chmod +x "$USER_BIN/agentic"
    
    # Check if user bin is in PATH
    if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
        log_warning "Please add $USER_BIN to your PATH:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "  # Add this to your ~/.bashrc or ~/.zshrc"
    fi
    
    log_success "CLI installed to $USER_BIN/agentic"
else
    log_error "CLI script not found: $CLI_SCRIPT"
    exit 1
fi

# Test installation
log_info "Testing CLI installation..."
if command -v agentic >/dev/null 2>&1; then
    log_success "CLI installation successful!"
    echo ""
    log_info "Try these commands:"
    echo "  agentic --help"
    echo "  agentic start"
    echo "  agentic agents list"
    echo "  agentic monitor"
else
    log_warning "CLI command not found in PATH"
    log_info "You can run the CLI directly with:"
    echo "  python3 agentic_cli.py --help"
fi

log_success "Installation completed!"
