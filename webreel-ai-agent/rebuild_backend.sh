#!/bin/bash
# Rebuild backend container to apply file upload endpoint changes

echo "🔨 Rebuilding backend container..."
docker-compose -f docker-compose.prod.yml up -d --build api

echo ""
echo "✅ Backend rebuilt successfully!"
echo ""
echo "📊 Checking container status..."
docker-compose -f docker-compose.prod.yml ps api

echo ""
echo "📝 Checking backend logs (last 20 lines)..."
docker-compose -f docker-compose.prod.yml logs --tail=20 api

echo ""
echo "🎯 Ready to test file upload endpoint!"
echo "   Run: python test_file_upload_docker.py"
