#!/bin/bash

# Algent Docker Deployment Script
# Starts the complete Algent system using Docker containers

set -e  # Exit on any error

# Configuration
NETWORK_NAME="algent-network"
REDIS_PASSWORD="redispass"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $@"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $@"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $@"
}

# Cleanup function
cleanup() {
    log_info "Stopping all Algent containers..."
    sudo docker stop algent-api-server algent-redis 2>/dev/null || true
    sudo docker rm algent-api-server algent-redis 2>/dev/null || true
    log_info "Cleanup completed"
}

# Build image
build_image() {
    log_info "Building Algent Docker image..."
    if sudo docker build -t algent:latest . >/dev/null 2>&1; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        return 1
    fi
}

# Start services
start_services() {
    log_info "Creating Docker network..."
    sudo docker network create $NETWORK_NAME 2>/dev/null || true
    
    log_info "Starting Redis container..."
    sudo docker run -d \
        --name algent-redis \
        --network $NETWORK_NAME \
        -p 6379:6379 \
        -e REDIS_PASSWORD=$REDIS_PASSWORD \
        redis:7-alpine \
        redis-server --appendonly yes --requirepass $REDIS_PASSWORD
    
    log_info "Waiting for Redis to be ready..."
    sleep 5
    
    log_info "Starting API server container..."
    sudo docker run -d \
        --name algent-api-server \
        --network $NETWORK_NAME \
        -p 8000:8000 \
        -e REDIS_URL="redis://:${REDIS_PASSWORD}@algent-redis:6379" \
        -e REDIS_PASSWORD="$REDIS_PASSWORD" \
        algent:latest \
        python3 api_server.py
    
    log_info "Waiting for API server to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            log_success "API server is ready"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: Waiting for API server..."
        sleep 2
        ((attempt++))
    done
    
    log_error "API server failed to start within timeout"
    return 1
}

# Test deployment
test_deployment() {
    log_info "Testing deployment..."
    
    # Test health endpoint
    local health_response=$(curl -s http://localhost:8000/health)
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        local agent_count=$(echo "$health_response" | grep -o '"active_agents":[0-9]*' | cut -d':' -f2)
        log_success "API server healthy with $agent_count active agents"
    else
        log_error "API server health check failed"
        return 1
    fi
    
    # Test CLI
    log_info "Testing CLI functionality..."
    if uv run algent agents list >/dev/null 2>&1; then
        log_success "CLI working correctly"
    else
        log_warning "CLI may have issues"
    fi
}

# Show status
show_status() {
    log_info "Deployment Status:"
    echo "===================="
    echo "🐳 Docker Containers:"
    sudo docker ps --filter "name=algent-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "🌐 API Endpoints:"
    echo "  Health: http://localhost:8000/health"
    echo "  Agents: http://localhost:8000/agents"
    echo "  Docs:   http://localhost:8000/docs"
    echo ""
    echo "🎮 CLI Commands:"
    echo "  List agents:    uv run algent agents list"
    echo "  Agent info:     uv run algent agents info <agent-id>"
    echo "  Run task:       uv run algent agents task <agent-id> <task> --data '{...}'"
    echo ""
    echo "🛑 To stop:"
    echo "  $0 stop"
}

# Main function
main() {
    case "${1:-start}" in
        "start")
            log_info "Starting Algent Docker deployment..."
            cleanup
            build_image
            start_services
            test_deployment
            show_status
            log_success "🎉 Algent system is running!"
            ;;
        "stop")
            cleanup
            log_success "Algent system stopped"
            ;;
        "status")
            show_status
            ;;
        "restart")
            log_info "Restarting Algent system..."
            cleanup
            build_image
            start_services
            test_deployment
            show_status
            log_success "🎉 Algent system restarted!"
            ;;
        *)
            echo "Usage: $0 {start|stop|status|restart}"
            echo ""
            echo "Commands:"
            echo "  start    - Build and start all services"
            echo "  stop     - Stop and remove all containers"
            echo "  status   - Show current deployment status"
            echo "  restart  - Stop and restart all services"
            exit 1
            ;;
    esac
}

main "$@"

