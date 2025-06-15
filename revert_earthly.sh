#!/bin/bash

echo "🔄 Reverting to original Docker setup..."

# Stop Earthly containers
docker-compose -f docker-compose.earthly.yml down -v 2>/dev/null || true

# Find the most recent backup
LATEST_BACKUP=$(ls -1t .backup/ | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    echo "📦 Restoring from backup: $LATEST_BACKUP"
    
    # Restore original files
    cp ".backup/$LATEST_BACKUP/Dockerfile"* . 2>/dev/null || true
    cp ".backup/$LATEST_BACKUP/docker-compose.yml" . 2>/dev/null || true
    
    # Remove Earthly files
    rm -f Earthfile docker-compose.earthly.yml
    rm -f test_earthly.sh revert_earthly.sh
    rm -rf .earthly/
    
    echo "✅ Reverted to original setup"
    echo "🐳 You can now use 'docker-compose build' again"
else
    echo "❌ No backup found"
    exit 1
fi
