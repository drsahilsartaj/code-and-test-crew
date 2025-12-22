#!/bin/bash

# Check if Ollama already running locally
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama already running at http://localhost:11434"
    exit 0
fi

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running."
    exit 1
fi

docker compose up -d
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama running at http://localhost:11434"