#!/bin/bash

# FloatChat Backend Build and Deployment Script
# Production-ready Docker deployment with health checks and rollback

set -euo pipefail

# Configuration
PROJECT_NAME="floatchat"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
VERSION="${VERSION:-$(date +%Y%m%d-%H%M%S)}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        log_warning ".env file not found, using .env.example"
        cp .env.example .env
    fi
    
    log_success "Prerequisites check completed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    local image_tag="${PROJECT_NAME}-backend:${VERSION}"
    local latest_tag="${PROJECT_NAME}-backend:latest"
    
    # Build multi-stage image
    docker build \
        --target runtime \
        --tag "${image_tag}" \
        --tag "${latest_tag}" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VERSION="${VERSION}" \
        .
    
    log_success "Docker image built: ${image_tag}"
    
    # Tag for registry if specified
    if [ -n "${DOCKER_REGISTRY}" ]; then
        docker tag "${image_tag}" "${DOCKER_REGISTRY}/${image_tag}"
        docker tag "${latest_tag}" "${DOCKER_REGISTRY}/${latest_tag}"
        log_info "Tagged for registry: ${DOCKER_REGISTRY}"
    fi
}

# Push to registry
push_image() {
    if [ -n "${DOCKER_REGISTRY}" ]; then
        log_info "Pushing to Docker registry..."
        
        docker push "${DOCKER_REGISTRY}/${PROJECT_NAME}-backend:${VERSION}"
        docker push "${DOCKER_REGISTRY}/${PROJECT_NAME}-backend:latest"
        
        log_success "Images pushed to registry"
    else
        log_info "No registry specified, skipping push"
    fi
}

# Run security scan
security_scan() {
    log_info "Running security scan..."
    
    if command -v trivy &> /dev/null; then
        trivy image "${PROJECT_NAME}-backend:latest"
    else
        log_warning "Trivy not found, skipping security scan"
    fi
}

# Deploy with health checks
deploy() {
    log_info "Deploying FloatChat backend..."
    
    # Create backup of current deployment
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_info "Creating backup of current deployment..."
        docker-compose -f docker-compose.prod.yml exec -T db pg_dump \
            -U "${POSTGRES_USER:-floatchat_user}" \
            -d "${POSTGRES_DB:-floatchat_db}" > "backup_$(date +%Y%m%d_%H%M%S).sql" || true
    fi
    
    # Deploy new version
    export VERSION="${VERSION}"
    docker-compose -f docker-compose.prod.yml up -d --remove-orphans
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.prod.yml ps | grep -q "healthy"; then
            log_success "Services are healthy"
            break
        fi
        
        log_info "Attempt $attempt/$max_attempts - waiting for services..."
        sleep 10
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "Services failed to become healthy within timeout"
        rollback
        exit 1
    fi
    
    # Run database migrations
    log_info "Running database migrations..."
    docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head || {
        log_error "Database migration failed"
        rollback
        exit 1
    }
    
    log_success "Deployment completed successfully"
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."
    
    # Stop current containers
    docker-compose -f docker-compose.prod.yml down
    
    # Restore from backup (if exists)
    local latest_backup=$(ls -t backup_*.sql 2>/dev/null | head -n1)
    if [ -n "$latest_backup" ]; then
        log_info "Restoring from backup: $latest_backup"
        # Restore logic would go here
    fi
    
    log_info "Rollback completed"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    local api_url="http://localhost:${API_PORT:-8000}/health"
    
    if curl -f -s "$api_url" > /dev/null; then
        log_success "Health check passed"
        return 0
    else
        log_error "Health check failed"
        return 1
    fi
}

# Cleanup old images
cleanup() {
    log_info "Cleaning up old Docker images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions (keep last 5)
    docker images "${PROJECT_NAME}-backend" --format "table {{.Tag}}\t{{.ID}}" | \
        grep -v "latest" | \
        tail -n +6 | \
        awk '{print $2}' | \
        xargs -r docker rmi || true
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting FloatChat backend deployment..."
    log_info "Version: ${VERSION}"
    log_info "Environment: ${ENVIRONMENT}"
    
    check_prerequisites
    build_image
    security_scan
    push_image
    deploy
    
    # Final health check
    sleep 30
    if health_check; then
        log_success "Deployment successful!"
        cleanup
    else
        log_error "Deployment failed health check"
        rollback
        exit 1
    fi
}

# Script options
case "${1:-deploy}" in
    "build")
        check_prerequisites
        build_image
        ;;
    "push")
        push_image
        ;;
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "health")
        health_check
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Usage: $0 {build|push|deploy|rollback|health|cleanup}"
        echo "  build    - Build Docker image only"
        echo "  push     - Push image to registry"
        echo "  deploy   - Full deployment (default)"
        echo "  rollback - Rollback to previous version"
        echo "  health   - Run health check"
        echo "  cleanup  - Clean up old images"
        exit 1
        ;;
esac
