#  Code and Test Crew - Web Application

Web-based interface for the Code and Test Crew multi-agent system.

##  Quick Start
```bash
# From project root - make sure Ollama is running
./start.sh

# Run webapp
cd webapp
source ../genai/bin/activate
python app.py
```

Open: **http://localhost:5001**

##  Features

- Matrix dark green theme
- Real-time agent status with colored dots
- Prompt refinement with user choice
- Syntax-highlighted code output
- Version history (all attempts)
- Run code online (opens compiler with code copied)
- Keyboard shortcuts (Ctrl+Enter to start, Escape to stop)

##  Structure
```
webapp/
├── app.py                    # Flask + WebSocket backend
├── requirements-web.txt      # Dependencies
├── templates/index.html      # UI
└── static/
    ├── css/style.css         # Styling
    └── js/main.js            # Frontend logic
```

## 🐳 Docker (Optional)
```bash
# If Ollama already running locally
docker-compose -f webapp/docker-compose.webapp.yml up -d webapp

# Or run everything in Docker
docker stop ollama-server && docker rm ollama-server
docker-compose -f webapp/docker-compose.webapp.yml up -d
```

## 🔧 How It Works

The webapp imports the **same agents** as the desktop GUI:
```python
from agents.coder import generate_code
from agents.reviewer import review_code
from agents.tester import run_tests
from agents.refiner import refine_prompt
```

Same code, same performance - just different UI!

---

Made with ❤️ by the Code Generation Crew Team