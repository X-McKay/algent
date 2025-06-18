#!/bin/bash

# Algent Docker Compose End-to-End Test Script
# Tests the complete system using docker-compose deployment

set -e  # Exit on any error

# Configuration
TEST_LOG_FILE="algent_docker_test_$(date +%Y%m%d_%H%M%S).log"
COMPOSE_FILE="docker-compose-simple.yml"
API_PORT=8000

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
    
    # Stop docker-compose services
    sudo docker-compose -f $COMPOSE_FILE down -v 2>/dev/null || true
    
    # Remove any test containers
    sudo docker rm -f algent-test-* 2>/dev/null || true
    
    log_info "Cleanup completed"
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Test functions
test_docker_availability() {
    log_info "Testing Docker availability..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not available"
        return 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not available"
        return 1
    fi
    
    # Test Docker daemon
    if ! sudo docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    log_success "Docker and docker-compose are available"
}

test_build_image() {
    log_info "Building Docker image..."
    
    # Build the image
    if sudo docker build -t algent:latest . >> "$TEST_LOG_FILE" 2>&1; then
        log_success "Docker image built successfully"
    else
        log_error "Docker image build failed"
        return 1
    fi
}

test_compose_up() {
    log_info "Starting services with docker-compose..."
    
    # Start services
    if sudo docker-compose -f $COMPOSE_FILE up -d >> "$TEST_LOG_FILE" 2>&1; then
        log_success "Docker-compose services started"
    else
        log_error "Failed to start docker-compose services"
        sudo docker-compose -f $COMPOSE_FILE logs >> "$TEST_LOG_FILE" 2>&1
        return 1
    fi
}

test_services_health() {
    log_info "Waiting for services to be healthy..."
    
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Check Redis health
        if sudo docker-compose -f $COMPOSE_FILE exec -T redis redis-cli -a redispass ping 2>/dev/null | grep -q PONG; then
            log_success "Redis is healthy"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "Redis failed to become healthy within timeout"
            sudo docker-compose -f $COMPOSE_FILE logs redis >> "$TEST_LOG_FILE" 2>&1
            return 1
        fi
        
        log_info "Attempt $attempt/$max_attempts: Waiting for Redis..."
        sleep 2
        ((attempt++))
    done
    
    # Wait for API server
    log_info "Waiting for API server to be ready..."
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$API_PORT/health >/dev/null 2>&1; then
            log_success "API server is ready"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "API server failed to start within timeout"
            sudo docker-compose -f $COMPOSE_FILE logs api-server >> "$TEST_LOG_FILE" 2>&1
            return 1
        fi
        
        log_info "Attempt $attempt/$max_attempts: Waiting for API server..."
        sleep 2
        ((attempt++))
    done
}

test_api_functionality() {
    log_info "Testing API functionality..."
    
    # Test health endpoint
    local health_response=$(curl -s http://localhost:$API_PORT/health)
    echo "Health response: $health_response" >> "$TEST_LOG_FILE"
    
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        log_success "API health check passed"
        
        # Extract agent count
        local agent_count=$(echo "$health_response" | grep -o '"active_agents":[0-9]*' | cut -d':' -f2)
        log_info "Active agents: $agent_count"
    else
        log_error "API health check failed"
        echo "Response: $health_response" >> "$TEST_LOG_FILE"
        return 1
    fi
    
    # Test agents endpoint
    local agents_response=$(curl -s http://localhost:$API_PORT/agents)
    echo "Agents response: $agents_response" >> "$TEST_LOG_FILE"
    
    if echo "$agents_response" | grep -q "api-calculator-001"; then
        log_success "Agents endpoint working"
    else
        log_warning "Agents endpoint may have issues"
        echo "Agents response: $agents_response" >> "$TEST_LOG_FILE"
    fi
}

test_cli_with_docker() {
    log_info "Testing CLI functionality with docker-compose deployment..."
    
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
}

test_agent_tasks() {
    log_info "Testing agent task execution..."
    
    # Test calculator agent
    log_info "Testing calculator agent..."
    local calc_result=$(uv run algent agents task api-calculator-001 add --data '{"a": 20, "b": 22}' 2>&1)
    echo "Calculator result: $calc_result" >> "$TEST_LOG_FILE"
    
    if echo "$calc_result" | grep -q "42.0"; then
        log_success "Calculator agent test passed (20 + 22 = 42)"
    else
        log_error "Calculator agent test failed"
        echo "$calc_result" >> "$TEST_LOG_FILE"
        return 1
    fi
}

test_container_logs() {
    log_info "Checking container logs for errors..."
    
    # Check API server logs
    local api_logs=$(sudo docker-compose -f $COMPOSE_FILE logs api-server 2>&1)
    echo "API Server logs:" >> "$TEST_LOG_FILE"
    echo "$api_logs" >> "$TEST_LOG_FILE"
    
    if echo "$api_logs" | grep -q "ERROR"; then
        log_warning "Found errors in API server logs"
    else
        log_success "No errors found in API server logs"
    fi
}

# Main test execution
main() {
    log_info "Starting Algent Docker-Compose End-to-End Test Suite"
    log_info "Test log file: $TEST_LOG_FILE"
    log_info "Compose file: $COMPOSE_FILE"
    log_info "=========================================="
    
    # System information
    log_info "System Information:"
    log_info "OS: $(uname -a)"
    log_info "Date: $(date)"
    log_info "Working directory: $(pwd)"
    log_info "Docker version: $(sudo docker --version)"
    log_info "Docker-compose version: $(sudo docker-compose --version)"
    
    # Run tests
    local failed_tests=0
    
    test_docker_availability || ((failed_tests++))
    test_build_image || ((failed_tests++))
    test_compose_up || ((failed_tests++))
    test_services_health || ((failed_tests++))
    test_api_functionality || ((failed_tests++))
    test_cli_with_docker || ((failed_tests++))
    test_agent_tasks || ((failed_tests++))
    test_container_logs || ((failed_tests++))
    
    # Summary
    log_info "=========================================="
    if [ $failed_tests -eq 0 ]; then
        log_success "🎉 ALL TESTS PASSED! Algent docker-compose deployment is fully functional."
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

