# Agentic System with A2A and MCP

A scalable, secure agent-to-agent communication system with Model Context Protocol integration.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Redis (optional, can use Docker)

### 1. Setup Environment

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start Redis (if not using Docker)
redis-server
```

### 2. Run the Demo

```bash
# Run the simple agent demo
python examples/simple_agent.py --mode demo
```

### 3. Using Docker (Recommended)

```bash
# Start all services
docker-compose up

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🏗️ Architecture

The system consists of:
- **Agent Framework**: Base agent class with A2A and MCP integration
- **A2A Communication**: Redis-based message bus for agent communication
- **MCP Integration**: Context management and tool registry
- **Security Layer**: Message signing and authentication

## 📖 Examples

### Creating a Custom Agent

```python
from src.core.agent import Agent, AgentCapability
from src.core.message import A2AMessage

class MyAgent(Agent):
    def __init__(self, agent_id: str):
        capabilities = [
            AgentCapability(
                name="my_task",
                description="Performs a custom task",
                parameters={"input": {"type": "string"}}
            )
        ]
        super().__init__(agent_id, "MyAgent", capabilities)
    
    async def execute_task(self, task_type: str, task_data: dict, message: A2AMessage):
        if task_type == "my_task":
            return {"result": f"Processed: {task_data.get('input', '')}"}
        raise ValueError(f"Unknown task: {task_type}")
```

### Agent Communication

```python
# Send a task to another agent
result = await agent.send_task_to_agent(
    recipient_id="other-agent-001",
    task_type="process_data",
    task_data={"data": "example"},
    timeout=30.0
)
print(f"Result: {result}")
```

## 🔧 Configuration

Edit `config/agent_config.yaml` to customize:
- Agent capabilities and limits
- Security settings
- MCP server configuration

## 🐛 Troubleshooting

### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/algent
```

## 📚 Next Steps

1. **Extend Agents**: Add more sophisticated capabilities
2. **Add Tools**: Integrate external APIs through MCP
3. **Scale**: Deploy with Kubernetes
4. **Monitor**: Add Prometheus/Grafana dashboards

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
