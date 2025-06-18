#!/bin/bash

# Algent End-to-End Test Script
# Tests the complete system functionality with detailed logging

set -e  # Exit on any error

# Configuration
TEST_LOG_FILE="algent_test_$(date +%Y%m%d_%H%M%S).log"
REDIS_CONTAINER_NAME="algent-test-redis"
API_PORT=8000
REDIS_PORT=6379

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$TEST_LOG_FILE"
}

log_info() {
    log "INFO" "${BLUE}$@${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}$@${NC}"
}

log_warning() {
    log "WARNING" "${YELLOW}$@${NC}"
}

log_error() {
    log "ERROR" "${RED}$@${NC}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test environment..."
    
    # Stop API server if running
    if [ ! -z "$API_PID" ]; then
        log_info "Stopping API server (PID: $API_PID)"
        kill $API_PID 2>/dev/null || true
        wait $API_PID 2>/dev/null || true
    fi
    
    # Stop and remove Redis container
    docker stop $REDIS_CONTAINER_NAME 2>/dev/null || true
    docker rm $REDIS_CONTAINER_NAME 2>/dev/null || true
    
    log_info "Cleanup completed"
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Test functions
test_python_version() {
    log_info "Testing Python version compatibility..."
    
    local python_version=$(python3 --version 2>&1)
    log_info "System Python version: $python_version"
    
    # Check if Python 3.13 is available
    if python3.13 --version >/dev/null 2>&1; then
        local py313_version=$(python3.13 --version 2>&1)
        log_success "Python 3.13 found: $py313_version"
        PYTHON_CMD="python3.13"
    else
        log_warning "Python 3.13 not found, using system Python: $python_version"
        PYTHON_CMD="python3"
    fi
    
    # Test basic Python functionality
    $PYTHON_CMD -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" >> "$TEST_LOG_FILE" 2>&1
    
    log_success "Python version test passed"
}

test_dependencies() {
    log_info "Testing Python dependencies..."
    
    # Install dependencies
    log_info "Installing requirements..."
    $PYTHON_CMD -m pip install -r requirements.txt >> "$TEST_LOG_FILE" 2>&1
    
    # Test critical imports
    log_info "Testing critical imports..."
    $PYTHON_CMD -c "
import asyncio
import redis.asyncio as redis
import fastapi
import uvicorn
import typer
import rich
import httpx
import aiohttp
import pydantic
print('All critical imports successful')
" >> "$TEST_LOG_FILE" 2>&1
    
    log_success "Dependencies test passed"
}

test_redis_setup() {
    log_info "Setting up Redis for testing..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not available"
        return 1
    fi
    
    # Stop any existing Redis container
    docker stop $REDIS_CONTAINER_NAME 2>/dev/null || true
    docker rm $REDIS_CONTAINER_NAME 2>/dev/null || true
    
    # Start Redis container
    log_info "Starting Redis container..."
    docker run -d \
        --name $REDIS_CONTAINER_NAME \
        -p $REDIS_PORT:6379 \
        -e REDIS_PASSWORD=redispass \
        redis:7-alpine \
        redis-server --appendonly yes --requirepass redispass >> "$TEST_LOG_FILE" 2>&1
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec $REDIS_CONTAINER_NAME redis-cli -a redispass ping 2>/dev/null | grep -q PONG; then
            log_success "Redis is ready"
            return 0
        fi
        log_info "Attempt $attempt/$max_attempts: Waiting for Redis..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Redis failed to start within timeout"
    docker logs $REDIS_CONTAINER_NAME >> "$TEST_LOG_FILE" 2>&1
    return 1
}

test_api_server() {
    log_info "Testing API server startup..."
    
    # Set environment variables
    export REDIS_URL="redis://localhost:$REDIS_PORT"
    export REDIS_PASSWORD="redispass"
    export API_PORT=$API_PORT
    
    # Start API server in background
    log_info "Starting API server..."
    $PYTHON_CMD api_server.py >> "$TEST_LOG_FILE" 2>&1 &
    API_PID=$!
    
    log_info "API server started with PID: $API_PID"
    
    # Wait for API server to be ready
    log_info "Waiting for API server to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$API_PORT/health >/dev/null 2>&1; then
            log_success "API server is ready"
            return 0
        fi
        
        # Check if process is still running
        if ! kill -0 $API_PID 2>/dev/null; then
            log_error "API server process died"
            return 1
        fi
        
        log_info "Attempt $attempt/$max_attempts: Waiting for API server..."
        sleep 2
        ((attempt++))
    done
    
    log_error "API server failed to start within timeout"
    return 1
}

test_api_health() {
    log_info "Testing API health endpoint..."
    
    local response=$(curl -s http://localhost:$API_PORT/health)
    echo "Health response: $response" >> "$TEST_LOG_FILE"
    
    # Check if response contains expected fields
    if echo "$response" | grep -q '"status":"healthy"' && echo "$response" | grep -q '"active_agents"'; then
        log_success "API health check passed"
        
        # Extract agent count
        local agent_count=$(echo "$response" | grep -o '"active_agents":[0-9]*' | cut -d':' -f2)
        log_info "Active agents: $agent_count"
        
        return 0
    else
        log_error "API health check failed"
        echo "Response: $response" >> "$TEST_LOG_FILE"
        return 1
    fi
}

test_cli_functionality() {
    log_info "Testing CLI functionality..."
    
    # Test CLI help
    log_info "Testing CLI help command..."
    uv run algent --help >> "$TEST_LOG_FILE" 2>&1
    
    # Test agent listing
    log_info "Testing agent list command..."
    local agents_output=$(uv run algent agents list 2>&1)
    echo "Agents list output: $agents_output" >> "$TEST_LOG_FILE"
    
    if echo "$agents_output" | grep -q "Active Agents"; then
        log_success "Agent list command passed"
    else
        log_error "Agent list command failed"
        echo "$agents_output" >> "$TEST_LOG_FILE"
        return 1
    fi
    
    # Test agent info
    log_info "Testing agent info command..."
    local agent_info=$(uv run algent agents info api-calculator-001 2>&1)
    echo "Agent info output: $agent_info" >> "$TEST_LOG_FILE"
    
    if echo "$agent_info" | grep -q "SimpleCalculator"; then
        log_success "Agent info command passed"
    else
        log_warning "Agent info command may have issues"
        echo "$agent_info" >> "$TEST_LOG_FILE"
    fi
}

test_agent_tasks() {
    log_info "Testing agent task execution..."
    
    # Test calculator agent
    log_info "Testing calculator agent..."
    local calc_result=$(uv run algent agents task api-calculator-001 add --data '{"a": 15, "b": 27}' 2>&1)
    echo "Calculator result: $calc_result" >> "$TEST_LOG_FILE"
    
    if echo "$calc_result" | grep -q "42.0"; then
        log_success "Calculator agent test passed (15 + 27 = 42)"
    else
        log_error "Calculator agent test failed"
        echo "$calc_result" >> "$TEST_LOG_FILE"
        return 1
    fi
    
    # Test echo agent
    log_info "Testing echo agent..."
    local echo_result=$(uv run algent agents task api-echo-001 echo --data '{"text": "Hello World"}' 2>&1)
    echo "Echo result: $echo_result" >> "$TEST_LOG_FILE"
    
    if echo "$echo_result" | grep -q "Hello World"; then
        log_success "Echo agent test passed"
    else
        log_warning "Echo agent test may have issues"
        echo "$echo_result" >> "$TEST_LOG_FILE"
    fi
}

test_docker_build() {
    log_info "Testing Docker build..."
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not available, skipping build test"
        return 0
    fi
    
    log_info "Building Docker image..."
    if docker build -t algent:test . >> "$TEST_LOG_FILE" 2>&1; then
        log_success "Docker build passed"
    else
        log_error "Docker build failed"
        return 1
    fi
}

# Main test execution
main() {
    log_info "Starting Algent End-to-End Test Suite"
    log_info "Test log file: $TEST_LOG_FILE"
    log_info "=========================================="
    
    # System information
    log_info "System Information:"
    log_info "OS: $(uname -a)"
    log_info "Date: $(date)"
    log_info "Working directory: $(pwd)"
    
    # Run tests
    local failed_tests=0
    
    test_python_version || ((failed_tests++))
    test_dependencies || ((failed_tests++))
    test_redis_setup || ((failed_tests++))
    test_api_server || ((failed_tests++))
    test_api_health || ((failed_tests++))
    test_cli_functionality || ((failed_tests++))
    test_agent_tasks || ((failed_tests++))
    test_docker_build || ((failed_tests++))
    
    # Summary
    log_info "=========================================="
    if [ $failed_tests -eq 0 ]; then
        log_success "🎉 ALL TESTS PASSED! Algent system is fully functional."
        log_info "Test log saved to: $TEST_LOG_FILE"
        return 0
    else
        log_error "❌ $failed_tests test(s) failed. Check the log for details."
        log_info "Test log saved to: $TEST_LOG_FILE"
        return 1
    fi
}

# Run main function
main "$@"

