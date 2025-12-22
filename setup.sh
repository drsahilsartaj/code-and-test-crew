#!/bin/bash

echo "=========================================="
echo "  Code Generation Crew - Setup"
echo "=========================================="

OLLAMA_URL="http://localhost:11434"
CONTAINER_NAME="ollama-server"

if curl -s $OLLAMA_URL/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama already running at $OLLAMA_URL"
    OLLAMA_CMD="ollama"
else
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker not found and Ollama not running."
        echo "Install Ollama or Docker first."
        exit 1
    fi

    echo "[1/3] Starting Ollama container..."
    docker compose up -d

    echo "[2/3] Waiting for Ollama..."
    until curl -s $OLLAMA_URL/api/tags > /dev/null 2>&1; do
        sleep 2
    done
    echo "✓ Ollama is ready!"
    OLLAMA_CMD="docker exec $CONTAINER_NAME ollama"
fi

echo "[3/3] Checking for deepseek-coder:6.7b..."
if $OLLAMA_CMD list | grep -q "deepseek-coder:6.7b"; then
    echo "✓ Model already installed"
else
    echo "Pulling deepseek-coder:6.7b..."
    $OLLAMA_CMD pull deepseek-coder:6.7b
fi

echo ""
echo "Optional models:"
echo "  $OLLAMA_CMD pull codellama:7b"
echo "  $OLLAMA_CMD pull qwen:7b"
echo ""
echo "Next:"
echo "  python3 -m venv genai"
echo "  source genai/bin/activate"
echo "  pip install -r requirements.txt"
echo "  python main.py"
