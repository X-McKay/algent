#!/bin/bash

echo "🧪 Testing Earthly setup..."

# Build images with Earthly
echo "🏗️ Building images with Earthly..."
time earthly +all

if [ $? -eq 0 ]; then
    echo "✅ Earthly build successful!"
    
    # Test with docker-compose
    echo "🐳 Testing with docker-compose..."
    docker-compose -f docker-compose.earthly.yml up -d redis postgres
    
    sleep 10
    
    docker-compose -f docker-compose.earthly.yml up -d api-server
    
    sleep 15
    
    # Test API
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ API server is responding!"
        
        # Start other services
        docker-compose -f docker-compose.earthly.yml up -d
        
        echo "🎉 Earthly setup is working!"
        echo ""
        echo "📊 Comparison:"
        echo "  🐳 Original Docker: Check your previous build times"
        echo "  🌍 Earthly: Built in $(echo $EARTHLY_BUILD_TIME) seconds"
        echo ""
        echo "🔄 To switch to Earthly permanently:"
        echo "  mv docker-compose.yml docker-compose.original.yml"
        echo "  mv docker-compose.earthly.yml docker-compose.yml"
        echo "  mv Dockerfile Dockerfile.original"
        echo "  # Use 'earthly +all' instead of 'docker-compose build'"
        
    else
        echo "❌ API server test failed"
        docker-compose -f docker-compose.earthly.yml logs api-server
    fi
    
else
    echo "❌ Earthly build failed"
    exit 1
fi
