# 🤖 Algent CLI

**A beautiful, powerful command-line interface for managing your AI agent infrastructure**

[![Python](https://img.shields.io/badge/Python-3.13.5-blue)](https://python.org)
[![Typer](https://img.shields.io/badge/CLI-Typer-green)](https://typer.tiangolo.com/)
[![Rich](https://img.shields.io/badge/UI-Rich-purple)](https://rich.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Algent CLI is a modern, type-safe command-line interface built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) for managing distributed AI agent systems with A2A (Agent-to-Agent) communication and MCP (Model Context Protocol) integration.

## ✨ Features

- 🎨 **Beautiful Interface** - Rich terminal UI with colors, tables, and progress bars
- ⚡ **Fast & Modern** - Built with Typer for type safety and performance
- 🐳 **Docker Integration** - Complete container lifecycle management
- 🤖 **Agent Management** - Create, deploy, and monitor AI agents
- 📊 **Real-time Monitoring** - Live dashboard with system metrics
- 🔧 **Configuration** - Persistent settings and environment management
- 🧪 **Health Checks** - Built-in testing and diagnostics
- 🔄 **Auto-completion** - Shell completion for bash/zsh
- 📋 **Comprehensive Logging** - Detailed logs and debugging tools

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/aldmckay/algent.git
cd algent

# Install the CLI
./install_cli_fixed.sh

# Verify installation
algent --version
```

### First Run

```bash
# Start the system
algent start

# Monitor in real-time
algent monitor

# List active agents
algent agents list

# Run health checks
algent test
```

## 📖 Command Reference

### System Management

| Command | Description | Example |
|---------|-------------|---------|
| `algent start` | Start all services | `algent start --build` |
| `algent stop` | Stop all services | `algent stop --volumes` |
| `algent restart` | Restart services | `algent restart api-server` |
| `algent monitor` | Real-time dashboard | `algent monitor --refresh 5` |
| `algent test` | Run health checks | `algent test` |
| `algent ps` | Show service status | `algent ps` |

### Docker Operations

| Command | Description | Example |
|---------|-------------|---------|
| `algent docker build` | Build images | `algent docker build --clean` |
| `algent docker start` | Start containers | `algent docker start --detach` |
| `algent docker stop` | Stop containers | `algent docker stop --volumes` |
| `algent docker logs` | View logs | `algent docker logs api-server -f` |
| `algent docker status` | Service status | `algent docker status` |

### Agent Management

| Command | Description | Example |
|---------|-------------|---------|
| `algent agents list` | List all agents | `algent agents list` |
| `algent agents create` | Create new agent | `algent agents create calculator` |
| `algent agents info` | Agent details | `algent agents info calc-001` |
| `algent agents task` | Send task to agent | `algent agents task calc-001 multiply` |
| `algent agents delete` | Remove agent | `algent agents delete calc-001 --force` |

### Configuration

| Command | Description | Example |
|---------|-------------|---------|
| `algent config` | Show all config | `algent config --list` |
| `algent config <key>` | Get config value | `algent config api_url` |
| `algent config <key> <value>` | Set config value | `algent config timeout 60` |

### Maintenance

| Command | Description | Example |
|---------|-------------|---------|
| `algent logs` | View system logs | `algent logs api-server --follow` |
| `algent shell` | Container shell | `algent shell api-server` |
| `algent clean` | Clean resources | `algent clean --all` |
| `algent update` | Update system | `algent update` |

## 🎯 Common Workflows

### Development Setup

```bash
# Initial setup
git clone https://github.com/aldmckay/algent.git
cd algent
./install_cli_fixed.sh

# Start development environment
algent start --build
algent test

# Monitor while developing
algent monitor
```

### Agent Development

```bash
# Create a new agent
algent agents create file_processor --agent-id my-processor

# Test the agent
algent agents task my-processor count_words -d '{"text":"Hello world"}'

# Monitor agent performance
algent agents info my-processor
```

### Production Deployment

```bash
# Configure for production
algent config api_url https://api.production.com
algent config timeout 120

# Deploy and verify
algent start
algent test
algent monitor
```

### System Maintenance

```bash
# Check system health
algent test

# View service logs
algent logs --follow

# Clean up old resources
algent clean --all

# Update to latest version
algent update
```

## 🎨 Interface Examples

### Dashboard (algent monitor)
```
┌─────────────────────────────────────────┐
│           🤖 Agentic System Monitor     │
│              Real-time Dashboard        │
└─────────────────────────────────────────┘

┌─────────────────┬─────────────────────────┐
│ 🤖 Active Agents│     🎯 Recent Tasks     │
├─────────────────┼─────────────────────────┤
│ Calculator   🟢 │ calc-001    multiply ✅ │
│ FileProcessor🟢 │ file-001    read     ✅ │
│ Echo         🟢 │ echo-001    uppercase✅ │
└─────────────────┴─────────────────────────┘

System: 🟢 Healthy | Active Agents: 3 | Press Ctrl+C to exit
```

### Agent List (algent agents list)
```
                           🤖 Active Agents
┌──────────────────┬──────────────┬────────┬─────────────────┬──────────────┐
│ Agent ID         │ Name         │ Status │ Capabilities    │ Active Tasks │
├──────────────────┼──────────────┼────────┼─────────────────┼──────────────┤
│ api-calc-001     │ Calculator   │   🟢   │ add, multiply   │      0       │
│ api-file-001     │ FileProcessor│   🟢   │ read_file, ...  │      2       │
│ api-echo-001     │ Echo         │   🟢   │ echo, uppercase │      0       │
└──────────────────┴──────────────┴────────┴─────────────────┴──────────────┘
```

### Build Progress (algent docker build)
```
🏗️ Building Agentic System Images
Ubuntu 24.04 • Python 3.13.5 • UV Package Manager

🔨 Building images... ████████████████████ 100%
✅ Build completed successfully!
```

## ⚙️ Configuration

### Default Configuration

```json
{
  "api_url": "http://localhost:8000",
  "mcp_url": "http://localhost:8080", 
  "timeout": 30,
  "auto_start": false,
  "preferred_editor": "nano",
  "log_level": "INFO"
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALGENT_API_URL` | API server URL | `http://localhost:8000` |
| `ALGENT_MCP_URL` | MCP server URL | `http://localhost:8080` |
| `ALGENT_TIMEOUT` | Request timeout | `30` |
| `ALGENT_LOG_LEVEL` | Log level | `INFO` |

### Configuration File

The CLI stores configuration in `~/.algent/config.json`. You can edit this manually or use the `algent config` commands.

## 🧪 Testing

### Built-in Health Checks

```bash
# Run all health tests
algent test

# Test output example:
🧪 Running System Health Tests
Testing API endpoints, agent communication, and service health

✅ API health check passed
✅ Agents endpoint accessible (3 agents)
✅ MCP server accessible  
✅ Docker services running (5 services)
✅ Task submission successful

🎉 All tests passed! (5/5)
Your agentic system is fully operational.
```

### Manual Testing

```bash
# Test specific components
curl $(algent config api_url)/health
algent agents task calc-001 add -d '{"a":2,"b":3}'
algent docker logs api-server --tail 10
```

## 🐚 Shell Completion

### Setup Auto-completion

```bash
# For bash
algent --install-completion bash
source ~/.bashrc

# For zsh  
algent --install-completion zsh
source ~/.zshrc

# Or use the setup script
./setup_completion.sh
```

### Completion Features

- Command completion: `algent <TAB>`
- Option completion: `algent agents <TAB>`
- Agent ID completion: `algent agents info <TAB>`
- File path completion: `algent docker logs <TAB>`

## 🔍 Troubleshooting

### Common Issues

#### CLI Not Found After Installation
```bash
# Check if installed correctly
which algent
echo $PATH

# Reinstall if needed
./install_cli_fixed.sh

# Add to PATH manually
export PATH="$HOME/.local/bin:$PATH"
```

#### Docker Connection Issues
```bash
# Check Docker status
docker info
algent docker status

# Restart Docker service
sudo systemctl restart docker
algent start
```

#### API Server Not Responding
```bash
# Check service status
algent ps
algent docker logs api-server

# Restart API server
algent restart api-server
algent test
```

#### Agent Communication Failures
```bash
# Check Redis connection
algent docker logs redis
algent shell redis

# Test agent endpoints
algent agents list
algent test
```

### Debug Mode

```bash
# Enable debug logging
algent config log_level DEBUG

# View detailed logs
algent logs --follow --tail 100

# Test with verbose output
algent test --verbose
```

### Getting Help

```bash
# General help
algent --help

# Command-specific help
algent agents --help
algent docker build --help

# Configuration help
algent config --help
```

## 🚀 Advanced Usage

### Scripting with Algent CLI

```bash
#!/bin/bash
# Automated deployment script

set -e

# Configure environment
algent config api_url "https://prod-api.example.com"
algent config timeout 120

# Deploy system
algent start --build

# Wait for services
sleep 30

# Verify deployment
if algent test; then
    echo "✅ Deployment successful"
    
    # Create production agents
    algent agents create calculator --agent-id prod-calc-01
    algent agents create file_processor --agent-id prod-file-01
    
    # Run smoke tests
    algent agents task prod-calc-01 add -d '{"a":1,"b":1}'
    
else
    echo "❌ Deployment failed"
    exit 1
fi
```

### Monitoring Integration

```bash
# Export metrics for external monitoring
while true; do
    # Get system stats
    AGENTS=$(algent agents list --format json 2>/dev/null | jq length)
    
    # Send to monitoring system
    curl -X POST "$METRICS_ENDPOINT" \
        -d "algent.agents.count $AGENTS $(date +%s)"
    
    sleep 60
done
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test Algent System

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Algent CLI
        run: ./install_cli_fixed.sh
        
      - name: Start system
        run: algent start --build
        
      - name: Run tests
        run: algent test
        
      - name: Test agent communication
        run: |
          algent agents create calculator
          algent agents task calculator-* add -d '{"a":2,"b":3}'
        
      - name: Cleanup
        run: algent clean --all --force
```

## 📊 Performance Tips

### Faster Builds
```bash
# Use parallel building
algent docker build --parallel

# Cache dependencies with UV
export UV_CACHE_DIR=/tmp/uv-cache
algent docker build
```

### Efficient Monitoring
```bash
# Adjust refresh rate based on needs
algent monitor --refresh 10  # Less CPU usage
algent monitor --refresh 1   # Real-time updates
```

### Batch Operations
```bash
# Process multiple agents efficiently
for agent in calc-{01..05}; do
    algent agents create calculator --agent-id "$agent" &
done
wait  # Wait for all creations to complete
```

## 🔗 Integration

### With Other Tools

#### Kubernetes
```bash
# Export to Kubernetes
algent docker build
docker save algent:latest | gzip > algent.tar.gz
kubectl create configmap algent-config --from-file=config/
```

#### Terraform
```hcl
resource "docker_container" "algent" {
  image = "algent:latest"
  name  = "algent-system"
  
  command = ["algent", "start", "--detach"]
  
  ports {
    internal = 8000
    external = 8000
  }
}
```

#### Ansible
```yaml
- name: Deploy Algent System
  shell: |
    cd /opt/algent
    algent start --build
    algent test
```

## 📚 API Reference

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Docker not available |
| 4 | API server unreachable |
| 5 | Agent operation failed |

### Output Formats

```bash
# JSON output for scripting
algent agents list --format json
algent config --format json

# Table output for humans (default)
algent agents list
algent docker status
```

## 🤝 Contributing

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/aldmckay/algent.git
cd algent
./dev_setup.sh

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Code Style

```bash
# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/cli.py

# Linting
pre-commit run --all-files
```

### Adding Commands

1. Add command function to `src/cli.py`
2. Use proper Typer annotations
3. Add Rich formatting for output
4. Include help text and examples
5. Add tests in `tests/`

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Typer](https://typer.tiangolo.com/) - Modern CLI framework
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal output
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [Docker](https://docker.com/) - Containerization
- [Python](https://python.org/) - Programming language

---