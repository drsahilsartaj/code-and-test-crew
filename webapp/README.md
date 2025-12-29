# 🌐 Code and Test Crew - Web Application

Web-based interface for the Code and Test Crew multi-agent system.

## 🚀 Quick Start
```bash
# From project root
./start.sh                              # Start Ollama
source genai/bin/activate               # Activate environment
pip3 install -r webapp/requirements-web.txt  # First time only
cd webapp
python3 app.py
```

Open: **http://localhost:5001**

## 📁 Structure
```
webapp/
├── app.py                    # Flask + WebSocket backend
├── requirements-web.txt      # Dependencies
├── docker-compose.webapp.yml # Docker deployment
├── Dockerfile                # Container build
├── templates/
│   └── index.html            # UI + JavaScript
└── static/
    └── css/style.css         # Matrix dark theme
```

## ✨ Features

- 🎨 Matrix dark green theme
- 🤖 Real-time agent status & logs
- 📊 Prompt refinement workflow
- 💻 Syntax-highlighted code
- 🔄 Version history
- ▶️ Run code online (one-click)
- ⌨️ Keyboard shortcuts (Ctrl+Enter, Escape)

## 🐳 Docker (Optional)
```bash
# From project root
docker-compose -f webapp/docker-compose.webapp.yml up -d webapp

# Open browser
open http://localhost:5001
```

## 📝 Usage

1. Select a model from dropdown
2. Enter your coding prompt
3. Click **Start** (or Ctrl+Enter)
4. Choose: Use Original, Use Refined, or Refine Again
5. Watch agents work in real-time
6. Click **Run Online** to test code

---

Made with ❤️ by [Sahil Sartaj](https://www.linkedin.com/in/sssahilsartaj/)
