#!/bin/bash
set -e

# Start Ollama in background
ollama serve &
sleep 5

# Default model (always pulled)
echo "Pulling default model: deepseek-coder:6.7b"
ollama pull deepseek-coder:6.7b

# Optional models (controlled by environment variables)
if [ "$PULL_CODELLAMA" = "true" ]; then
    echo "Pulling CodeLlama 7B..."
    ollama pull codellama:7b-instruct-q4_0
fi

if [ "$PULL_QWEN" = "true" ]; then
    echo "Pulling Qwen 32B..."
    ollama pull qwen2.5-coder:32b
fi

echo "Models ready!"
python main.py