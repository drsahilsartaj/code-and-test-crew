#!/bin/bash

# Code and Test Crew - Web Application Setup
# Run from webapp folder OR project root

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║       Code and Test Crew - Web Application Setup         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Detect if we're in webapp folder or project root
if [ -f "app.py" ]; then
    WEBAPP_DIR="."
    PROJECT_ROOT=".."
elif [ -d "webapp" ]; then
    WEBAPP_DIR="webapp"
    PROJECT_ROOT="."
else
    echo -e "${RED}❌ Run this from project root or webapp folder${NC}"
    exit 1
fi

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Webapp dir: $WEBAPP_DIR"
echo ""

# Check if Ollama is already running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama already running${NC}"
    OLLAMA_RUNNING=true
else
    echo -e "${YELLOW}⚠️  Ollama not running${NC}"
    OLLAMA_RUNNING=false
    
    # Try to start with existing docker-compose
    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        echo "Starting Ollama from docker-compose..."
        cd "$PROJECT_ROOT"
        docker-compose up -d
        cd - > /dev/null
        sleep 3
    fi
fi

# Create/activate virtual environment
if [ ! -d "$PROJECT_ROOT/genai" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/genai"
fi

echo "Activating virtual environment..."
source "$PROJECT_ROOT/genai/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r "$PROJECT_ROOT/requirements.txt"
pip install -q -r "$WEBAPP_DIR/requirements-web.txt"

# Pull model if needed
if [ "$OLLAMA_RUNNING" = true ] || curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    if ! curl -s http://localhost:11434/api/tags | grep -q "deepseek-coder"; then
        echo "Pulling DeepSeek Coder model..."
        if docker ps | grep -q ollama-server; then
            docker exec ollama-server ollama pull deepseek-coder:6.7b
        else
            ollama pull deepseek-coder:6.7b 2>/dev/null || true
        fi
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo ""
echo "To run the web app:"
echo "  cd $WEBAPP_DIR"
echo "  python app.py"
echo ""
echo "Then open: http://localhost:5000"
echo ""
echo "═══════════════════════════════════════════════════════════"
