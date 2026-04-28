#!/bin/bash

# Build script for Docker deployment

set -e

echo "Building Webreel Backend Docker Image..."

cd "$(dirname "$0")/.."

docker build \
  -f webreel-ai-agent/Dockerfile.backend \
  -t webreel-backend:latest \
  --progress=plain \
  .

echo "Build complete!"
echo ""
echo "To run the application:"
echo "  cd webreel-ai-agent"
echo "  docker-compose -f docker-compose.backend.yml up"
