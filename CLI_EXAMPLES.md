# 🤖 Agentic CLI Examples

## Basic Commands

### System Management
```bash
# Start the entire system
agentic start

# Start with build
agentic start --build

# Stop everything
agentic stop

# Stop and remove volumes
agentic stop --volumes

# Restart specific service
agentic restart api-server

# Monitor system in real-time
agentic monitor

# Run health tests
agentic test
```

### Docker Operations
```bash
# Build all images
agentic docker build

# Build with clean slate
agentic docker build --clean

# Start services in detached mode
agentic docker start --detach

# View logs for specific service
agentic docker logs api-server

# Follow logs in real-time
agentic docker logs api-server --follow

# Show service status
agentic docker status

# Restart a service
agentic docker restart redis
```

### Agent Management
```bash
# List all active agents
agentic agents list

# Get detailed info about an agent
agentic agents info api-calculator-001

# Create a new agent
agentic agents create calculator

# Create agent with custom ID
agentic agents create file_processor --agent-id my-file-agent

# Delete an agent
agentic agents delete my-file-agent

# Force delete without confirmation
agentic agents delete my-file-agent --force
```

### Task Operations
```bash
# Send a simple task with interactive prompts
agentic agents task api-calculator-001 add

# Send task with JSON data
agentic agents task api-fileprocessor-001 count_words -d '{"text":"Hello world"}'

# Send task with custom timeout
agentic agents task api-echo-001 uppercase --timeout 60 -d '{"message":"hello"}'

# Example tasks for different agent types
agentic agents task calc-001 multiply -d '{"a": 15, "b": 23}'
agentic agents task echo-001 echo -d '{"message": "Hello AI!"}'
agentic agents task file-001 read_file -d '{"file_path": "./data/test.txt"}'
```

### Configuration Management
```bash
# List all configuration
agentic config --list

# Get specific config value
agentic config api_url

# Set configuration value
agentic config api_url http://localhost:9000

# Set timeout
agentic config timeout 60

# Set log level
agentic config log_level DEBUG
```

### System Maintenance
```bash
# View system logs
agentic logs

# View logs for specific service
agentic logs api-server

# Show running processes
agentic ps

# Open shell in container
agentic shell api-server

# Clean up old containers and images
agentic clean

# Clean everything including volumes
agentic clean --all

# Force clean without confirmation
agentic clean --all --force

# Update system
agentic update
```

## Advanced Examples

### Complex Workflows
```bash
# 1. Start system and wait for readiness
agentic start --build
sleep 30

# 2. Create multiple agents
agentic agents create calculator --agent-id calc-primary
agentic agents create file_processor --agent-id file-primary
agentic agents create echo --agent-id echo-primary

# 3. Run a series of tasks
agentic agents task calc-primary multiply -d '{"a": 42, "b": 13}'
agentic agents task file-primary count_words -d '{"text": "The quick brown fox jumps over the lazy dog"}'
agentic agents task echo-primary uppercase -d '{"message": "task completed successfully"}'

# 4. Monitor results
agentic monitor
```

### File Processing Workflow
```bash
# Create file processor agent
agentic agents create file_processor --agent-id file-worker

# Write a file
agentic agents task file-worker write_file -d '{
  "file_path": "./data/report.txt",
  "content": "Sales Report\n============\nQ4 Results: $1,250,000"
}'

# Read it back
agentic agents task file-worker read_file -d '{"file_path": "./data/report.txt"}'

# Analyze word count
agentic agents task file-worker count_words -d '{"text": "Sales Report Q4 Results"}'

# List directory contents
agentic agents task file-worker list_directory -d '{"directory_path": "./data"}'
```

### CSV Analysis Workflow
```bash
# Prepare CSV data
CSV_DATA='name,age,salary,department
John Doe,30,75000,Engineering
Jane Smith,28,68000,Marketing
Bob Johnson,35,82000,Engineering
Alice Brown,32,71000,Sales'

# Analyze the CSV
agentic agents task file-worker analyze_csv -d "{\"csv_content\": \"$CSV_DATA\"}"
```

### Monitoring and Debugging
```bash
# Start monitoring in background
agentic monitor &
MONITOR_PID=$!

# Run some tasks
agentic agents task calc-001 add -d '{"a": 100, "b": 200}'
agentic agents task echo-001 reverse -d '{"message": "Hello World"}'

# Check health
agentic test

# Stop monitoring
kill $MONITOR_PID
```

### Batch Operations
```bash
#!/bin/bash
# Batch task execution script

AGENTS=("calc-001" "calc-002" "calc-003")
OPERATIONS=("add" "multiply" "subtract")

for agent in "${AGENTS[@]}"; do
    for op in "${OPERATIONS[@]}"; do
        echo "Running $op on $agent"
        agentic agents task "$agent" "$op" -d '{"a": 10, "b": 5}'
        sleep 2
    done
done
```

### Development Workflow
```bash
# Setup development environment
./dev_setup.sh

# Make changes to code...

# Test changes
python3 agentic_cli.py test

# Run specific tests
pytest tests/test_cli.py -v

# Format code
black agentic_cli.py
isort agentic_cli.py

# Type check
mypy agentic_cli.py

# Build and test Docker images
agentic docker build --clean
agentic start --build
agentic test
```

## Configuration Examples

### Custom API Endpoints
```bash
# Configure for remote deployment
agentic config api_url https://my-agentic-cluster.com:8000
agentic config mcp_url https://my-agentic-cluster.com:8080
agentic config timeout 120

# Test connection
agentic test
```

### Development vs Production
```bash
# Development setup
agentic config api_url http://localhost:8000
agentic config log_level DEBUG
agentic config timeout 30

# Production setup  
agentic config api_url https://api.production.com
agentic config log_level INFO
agentic config timeout 60
```

## Troubleshooting Commands

### Service Issues
```bash
# Check if Docker is running
docker info

# Check service status
agentic ps

# Restart problematic service
agentic restart api-server

# View recent logs
agentic logs api-server --tail 50

# Follow logs for debugging
agentic logs api-server --follow
```

### Network Issues
```bash
# Test API connectivity
curl http://localhost:8000/health

# Test with configured URL
URL=$(agentic config api_url)
curl $URL/health

# Check port conflicts
netstat -tulpn | grep :8000
```

### Reset Everything
```bash
# Complete system reset
agentic stop --volumes
agentic clean --all --force
agentic start --build

# Verify everything works
agentic test
```

## Automation Scripts

### Health Check Script
```bash
#!/bin/bash
# health_check.sh - Automated health monitoring

while true; do
    echo "$(date): Checking system health..."
    
    if agentic test > /dev/null 2>&1; then
        echo "✅ System healthy"
    else
        echo "❌ System unhealthy - attempting restart"
        agentic restart
        sleep 30
    fi
    
    sleep 300  # Check every 5 minutes
done
```

### Backup Script
```bash
#!/bin/bash
# backup.sh - Backup system state

BACKUP_DIR="/backups/agentic/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Export configuration
agentic config --list > "$BACKUP_DIR/config.txt"

# Export Docker volumes
docker run --rm -v agentic_postgres_data:/data -v "$BACKUP_DIR":/backup ubuntu tar czf /backup/postgres_data.tar.gz -C /data .
docker run --rm -v agentic_redis_data:/data -v "$BACKUP_DIR":/backup ubuntu tar czf /backup/redis_data.tar.gz -C /data .

echo "Backup completed: $BACKUP_DIR"
```

### Load Test Script
```bash
#!/bin/bash
# load_test.sh - Simple load testing

CONCURRENT_TASKS=10
TASK_COUNT=100

echo "Running load test: $TASK_COUNT tasks with $CONCURRENT_TASKS concurrent workers"

for i in $(seq 1 $TASK_COUNT); do
    (
        AGENT_ID="api-calculator-001"
        TASK_TYPE="multiply"
        DATA='{"a": '$i', "b": 2}'
        
        agentic agents task "$AGENT_ID" "$TASK_TYPE" -d "$DATA" > /dev/null 2>&1
        echo "Task $i completed"
    ) &
    
    # Limit concurrent tasks
    if (( $i % $CONCURRENT_TASKS == 0 )); then
        wait
    fi
done

wait
echo "Load test completed"
```

## Integration Examples

### With CI/CD
```yaml
# .github/workflows/test.yml
name: Test Agentic System

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Agentic CLI
        run: ./install_cli.sh
        
      - name: Start system
        run: agentic start --build
        
      - name: Run tests
        run: agentic test
        
      - name: Cleanup
        run: agentic clean --all --force
```

### With Monitoring
```bash
# Send metrics to external monitoring
while true; do
    # Get system stats
    STATS=$(agentic agents list --format json 2>/dev/null || echo '[]')
    AGENT_COUNT=$(echo "$STATS" | jq length)
    
    # Send to monitoring system
    curl -X POST "$MONITORING_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "{\"metric\": \"active_agents\", \"value\": $AGENT_COUNT, \"timestamp\": $(date +%s)}"
    
    sleep 60
done
```

This CLI provides a comprehensive interface for managing your agentic system with beautiful output, robust error handling, and powerful automation capabilities!
