#!/bin/bash

# Setup shell completion for Agentic CLI

echo "🔧 Setting up shell completion for Agentic CLI..."

# Detect shell
if [[ -n "$ZSH_VERSION" ]]; then
    SHELL_TYPE="zsh"
    RC_FILE="$HOME/.zshrc"
    COMPLETION_DIR="$HOME/.zsh/completions"
elif [[ -n "$BASH_VERSION" ]]; then
    SHELL_TYPE="bash"
    RC_FILE="$HOME/.bashrc"
    COMPLETION_DIR="$HOME/.bash_completions"
else
    echo "❌ Unsupported shell. Only bash and zsh are supported."
    exit 1
fi

echo "Detected shell: $SHELL_TYPE"

# Create completion directory
mkdir -p "$COMPLETION_DIR"

# Generate completion script
if command -v agentic >/dev/null 2>&1; then
    echo "📝 Generating completion script..."
    
    if [[ "$SHELL_TYPE" == "zsh" ]]; then
        agentic --install-completion zsh > "$COMPLETION_DIR/_agentic"
        
        # Add to .zshrc if not already there
        if ! grep -q "autoload -U compinit" "$RC_FILE" 2>/dev/null; then
            echo "" >> "$RC_FILE"
            echo "# Shell completion" >> "$RC_FILE"
            echo "autoload -U compinit" >> "$RC_FILE"
            echo "compinit" >> "$RC_FILE"
        fi
        
        if ! grep -q "$COMPLETION_DIR" "$RC_FILE" 2>/dev/null; then
            echo "fpath=($COMPLETION_DIR \$fpath)" >> "$RC_FILE"
        fi
        
    elif [[ "$SHELL_TYPE" == "bash" ]]; then
        agentic --install-completion bash > "$COMPLETION_DIR/agentic"
        
        # Add to .bashrc if not already there
        if ! grep -q "source $COMPLETION_DIR/agentic" "$RC_FILE" 2>/dev/null; then
            echo "" >> "$RC_FILE"
            echo "# Agentic CLI completion" >> "$RC_FILE"
            echo "source $COMPLETION_DIR/agentic" >> "$RC_FILE"
        fi
    fi
    
    echo "✅ Completion setup complete!"
    echo "🔄 Restart your shell or run: source $RC_FILE"
else
    echo "❌ Agentic CLI not found. Please install it first."
    exit 1
fi
