# Intelligent Code Generation Crew
A multi-agent system for automated Python code generation using local LLMs via Ollama and LangGraph.

## Features
- **Multi-agent workflow**: Refiner → Coder → Reviewer → Tester → Flake8
- **Iterative refinement**: Up to 10 attempts with intelligent feedback loops
- **Local LLM support**: Multiple Ollama models (DeepSeek, Qwen, CodeLlama)
- **Dark green/black GUI**: Matrix-themed interface with syntax highlighting
- **Automated testing**: pytest integration with custom test generation
- **Code quality checks**: Flake8 linting (informational, non-blocking)
- **Session management**: Save/load workflows with full history
- **VS Code integration**: One-click code editing
- **Resizable panels**: Adjustable prompt, refined prompt, and code sections

---

## 🖥️ Desktop Shortcut

A desktop shortcut **"Code Generation Crew"** with a custom icon is included in the project folder for easy access. Simply double-click to launch the application.

## 🚀 Quick Start - Choose Your Installation Method

We offer **3 ways** to run this application:

| Method | Best For | Setup Time | Requirements |
|--------|----------|------------|--------------|
| **Option 1: Local** | Fastest model loading | 15-20 min | Ollama installed locally |
| **Option 2: Docker** | Easy setup, isolated | 20-30 min | Docker installed |
| **Option 3: Web App** | No installation needed | Instant | Just a browser |

---

## Option 1: Local Installation (Recommended for Speed)

Best if you want **fastest model performance**. Models run directly on your machine.

### Step 1: Install Ollama

| OS | Installation |
|----|--------------|
| **macOS** | `brew install ollama` or download from [ollama.com/download](https://ollama.com/download) |
| **Linux** | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **Windows** | Download from [ollama.com/download](https://ollama.com/download) |

### Step 2: Pull AI Model
```bash
# Start Ollama service (if not auto-started)
ollama serve

# Pull the default model (~3.8 GB)
ollama pull deepseek-coder:6.7b
```

**Optional models:**
```bash
ollama pull codellama:7b         # Lightweight alternative
ollama pull qwen2.5-coder:7b     # Another good option
```

### Step 3: Setup Python Environment
```bash
# Clone the project
git clone https://github.com/drsahilsartaj/code-and-test-crew.git
cd code-and-test-crew

# Create virtual environment
python3 -m venv genai
source genai/bin/activate        # On Windows: genai\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Install Tkinter (GUI dependency)
```bash
# macOS
brew install python-tk@3.12

# Linux (Ubuntu/Debian)
sudo apt install python3-tk

# Verify installation
python -c "import tkinter; print('Tkinter OK')"
```

### Step 5: Run the Application
```bash
source genai/bin/activate
python main.py
```

---

## Option 2: Docker + Hybrid Setup (Easiest Setup)

Best if you want **isolated environment** without installing Ollama system-wide.

> **How it works**: Ollama runs in Docker container, GUI runs locally.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed
- Python 3.12+ with Tkinter
- ~5 GB disk space for default model

### Quick Setup (One Command)
```bash
# Clone the project
git clone https://github.com/drsahilsartaj/code-and-test-crew.git
cd code-and-test-crew

# Run automated setup
chmod +x setup.sh
./setup.sh
```

The `setup.sh` script will:
1. ✅ Start Ollama in Docker
2. ✅ Pull the default model (deepseek-coder:6.7b)
3. ✅ Detect if Ollama is already running locally

### After Setup
```bash
# Activate environment
source genai/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Tkinter (macOS)
brew install python-tk@3.12

# Run the app
python main.py
```

### Helper Scripts

| Script | Command | Purpose |
|--------|---------|---------|
| `start.sh` | `./start.sh` | Start Ollama container |
| `stop.sh` | `./stop.sh` | Stop Ollama container |

### Pull Additional Models (Optional)
```bash
docker exec ollama-server ollama pull codellama:7b
docker exec ollama-server ollama pull qwen2.5-coder:7b
```

### Docker Commands Reference
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# View container logs
docker logs ollama-server

# List installed models
docker exec ollama-server ollama list

# Stop and remove container
docker compose down
```

---

## Option 3: Web Application (Coming Soon) 🌐

**Zero installation required** - just open in your browser!

> 🚧 **Status**: Under Development

### Features (Planned)
- Same functionality as desktop app
- No local installation needed
- Works on any device with a browser
- Cloud-hosted AI models

### How it will work
1. Visit the web app URL
2. Enter your code generation prompt
3. Watch agents work in real-time
4. Download generated code

**Stay tuned!** We're working on deploying this as a web service.

---

## 📋 System Requirements Summary

| Component | Option 1 (Local) | Option 2 (Docker) | Option 3 (Web) |
|-----------|------------------|-------------------|----------------|
| Python 3.12+ | ✅ Required | ✅ Required | ❌ Not needed |
| Tkinter | ✅ Required | ✅ Required | ❌ Not needed |
| Ollama | ✅ Install locally | ✅ Runs in Docker | ❌ Cloud-hosted |
| Docker | ❌ Not needed | ✅ Required | ❌ Not needed |
| RAM | 8 GB+ | 8 GB+ | Any |
| Disk Space | ~5 GB | ~5 GB | None |

---

## ✅ Verify Your Installation

After setup, verify everything works:

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check model is installed
ollama list   # Local installation
# OR
docker exec ollama-server ollama list   # Docker installation

# Check Python environment
source genai/bin/activate
python -c "import tkinter; import langchain; print('All dependencies OK')"

# Run the app
python main.py
```

---

## 📊 Benchmark Results

We evaluated the system using two different benchmark approaches to test different aspects of agent collaboration.

### Version 1.0 - Simple Prompts Benchmark (36 Tests)
**Methodology**: Direct, simple prompts without refinement (e.g., "create a function that adds two numbers")

- **Success Rate**: **100%** (36/36 passed)
- **Average Time**: 95.5s per test
- **Average Attempts**: 1.8

**Results by Difficulty:**
- Easy: 10/10 (100%)
- Medium: 15/15 (100%)
- Hard: 7/7 (100%)
- Very Hard: 4/4 (100%)

### Version 2.0 - Refined Prompts Benchmark (40 Tests)
**Methodology**: Complex, detailed prompts with refined specifications (e.g., "Write a function that takes height in meters and weight in kilograms, calculates BMI, and returns the category as a string. Handle edge cases for zero or negative values.")

- **Success Rate**: **92.5%** (37/40 passed)
- **Average Time**: 132s per test
- **Average Attempts**: 2.4

**Performance by Difficulty (v2.0):**
| Difficulty | Pass Rate | Tests |
|------------|-----------|-------|
| Easy       | 87.5%     | 7/8   |
| Medium     | 89.5%     | 17/19 |
| Hard       | **100%**  | 8/8 ✨|
| Very Hard  | **100%**  | 5/5 ✨|

**Key Finding**: System performs BETTER on complex tasks (100% success on Hard/Very Hard) than simple ones. Detailed specifications provide clearer guidance to agents, reducing ambiguity and improving collaboration between Refiner, Coder, Reviewer, and Tester agents.

**Run benchmarks:**
```bash
python BENCHMARK.py
```

---

## 🤖 The Four Agents

Our system uses four specialized AI agents that collaborate through feedback loops:

1. **Refiner Agent** (`agents/refiner.py`)
   - Clarifies vague user prompts into detailed technical specifications
   - Adds missing details: parameter types, return types, edge cases
   - Ensures all requirements are explicit before code generation

2. **Coder Agent** (`agents/coder.py`)
   - Generates Python code from refined specifications
   - Implements algorithms and logic
   - Iterates based on feedback from Reviewer and Tester

3. **Reviewer Agent** (`agents/reviewer.py`)
   - Validates code quality, logic, and best practices (without execution)
   - Performs static analysis to catch errors early
   - Checks for edge case handling and code structure

4. **Tester Agent** (`agents/tester.py`)
   - Creates and executes unit tests to verify correctness
   - Runs pytest on generated code
   - Reports detailed error messages for failed tests

**Key Innovation**: Multi-layer validation with feedback loops (max 3 attempts per agent).

---

## Development Environment

This project was developed and tested on two laptops:

### Laptop 1: Lenovo ThinkPad X280
- **CPU**: Intel Core i5-8th Gen vPro
- **RAM**: 8 GB DDR4
- **OS**: Linux Mint

### Laptop 2: Lenovo ThinkPad P14s Gen 5 AMD
- **CPU**: AMD Ryzen 7 PRO 8840HS
- **RAM**: 32 GB DDR5
- **OS**: Linux Mint 22

### Software Requirements
- Python 3.12+
- Tkinter (for GUI)
- Ollama (for local LLM inference)
- Git
```bash
# Linux Mint / Ubuntu / Debian
sudo apt install python3.12 python3.12-venv python3-tk git
```

---

## 🔧 Detailed Installation Reference

> **Note**: See [Quick Start](#-quick-start---choose-your-installation-method) above for step-by-step setup guides.

### Available AI Models

Choose models based on your hardware:

| Model | Size | RAM Required | Speed | Quality | Best For |
|-------|------|--------------|-------|---------|----------|
| `deepseek-coder:6.7b` | 3.8 GB | ~8 GB | Medium | Better | **General use (Default)** |
| `codellama:7b` | 3.8 GB | ~5 GB | Fast | Good | Simple tasks, low RAM |
| `qwen2.5-coder:7b` | 4.4 GB | ~8 GB | Medium | Better | Alternative to DeepSeek |
| `qwen2.5-coder:32b` | 19 GB | ~18 GB | Slow | Best | Complex logic (needs 32GB RAM) |

### Pull Models

**Local Ollama:**
```bash
ollama pull deepseek-coder:6.7b   # Default
ollama pull codellama:7b          # Optional
ollama pull qwen2.5-coder:7b      # Optional
```

**Docker:**
```bash
docker exec ollama-server ollama pull deepseek-coder:6.7b
docker exec ollama-server ollama pull codellama:7b
docker exec ollama-server ollama pull qwen2.5-coder:7b
```

### Python Environment Setup
```bash
# Create virtual environment
python3 -m venv genai
source genai/bin/activate         # Linux/macOS
# OR
genai\Scripts\activate            # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Usage

### Basic Workflow
1. **Select model** from dropdown (DeepSeek 6.7B is default)
2. **Enter prompt**: e.g., "create a function that finds prime numbers less than n"
3. **Click Start**: Agent refines your prompt
4. **Review refinement**: Choose "Use Original" or "Use Refined"
5. **Wait for generation**: Watch agents work in real-time
6. **View results**: Code appears with syntax highlighting
7. **Open in VS Code**: Edit and test your code

### GUI Features
- **Real-time logs**: See each agent's activity
- **Version history**: Compare all code iterations
- **Progress tracking**: Attempts counter and time elapsed
- **Error reporting**: Separate error log tab
- **Session save/load**: Resume work later

---

## 📁 Project Structure
```
code_generation_crew/
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── main.py                  # Entry point
├── workflow.py              # LangGraph orchestration
├── BENCHMARK.py             # Benchmark runner
│
├── docker-compose.yml       # Ollama container config
├── setup.sh                 # Full setup script
├── setup_ollama.sh          # Ollama-only setup
├── start.sh                 # Start Ollama container
├── stop.sh                  # Stop Ollama container
│
├── agents/                  # AI agents
│   ├── __init__.py
│   ├── refiner.py          # Prompt clarification
│   ├── coder.py            # Code generation
│   ├── reviewer.py         # Static analysis
│   └── tester.py           # Automated testing
│
├── benchmark_prompts/       # Test datasets
│   ├── test_prompts.json          # Simple prompts (v1.0)
│   └── refined_test_prompts.json  # Complex prompts (v2.0)
│
├── benchmark_results/       # Test results
│   ├── improved_test_prompts_results.txt
│   └── refined_prompts_results_deepseek-coder_6.7b_*.txt
│
├── gui/                     # User interface
│   ├── __init__.py
│   └── app.py              # Tkinter GUI (dark theme)
│
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── state.py            # State management
│   └── flake8_checker.py   # Style checking
│
├── saves/                   # Saved sessions
├── outputs/                 # Generated code
└── logs/                    # Runtime logs
```

---

## Agent Workflow
```
┌─────────────┐
│ User Prompt │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Refiner    │ Clarifies requirements
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Coder     │ Generates Python code
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Reviewer   │ Static analysis
└──────┬──────┘
       │ Approved?
       ├─ No ──► (Retry with feedback)
       │
       ▼ Yes
┌─────────────┐
│   Tester    │ Runs pytest tests
└──────┬──────┘
       │ Pass?
       ├─ No ──► (Retry with feedback)
       │
       ▼ Yes
┌─────────────┐
│   Flake8    │ Style check (non-blocking)
└──────┬──────┘
       │
       ▼
   SUCCESS
```

---

## Benchmark Test Examples

### Simple Prompts (v1.0) - Examples

**Easy (10 tests - 100% success):**
```
create a function that adds two numbers
create a function that checks if a number is even
create a function that reverses a string
create a function that checks if a number is odd
create a function that calculates the square of a number
create a function that returns the absolute value of a number
create a function that converts celsius to fahrenheit
create a function that finds the length of a string
create a function that checks if a string is empty
create a function that multiplies two numbers
```

**Medium (15 tests - 100% success):**
```
create a function that calculates the factorial of a number
create a function that counts vowels in a string
create a function that checks if a string is a palindrome
create a function that finds the maximum value in a list
create a function that finds the minimum value in a list
create a function that calculates the sum of all numbers in a list
create a function that calculates the average of numbers in a list
create a function that checks if a number is prime
create a function that counts the occurrences of a character in a string
create a function that removes duplicates from a list
create a function that checks if a string contains only digits
create a function that finds the second largest number in a list
create a function that counts words in a string
create a function that converts a string to uppercase
create a function that finds the longest word in a string
```

**Hard (7 tests - 100% success):**
```
create a function that checks if a string is a valid email address
create a function that sorts a list using bubble sort
create a function that finds all prime numbers less than n
create a function that finds the greatest common divisor of two numbers
create a function that finds the least common multiple of two numbers
create a function that converts a binary string to decimal
create a function that flattens a nested list
```

**Very Hard (4 tests - 100% success):**
```
create a function that implements quicksort algorithm
create a function that implements merge sort algorithm
create a function that checks if parentheses in a string are balanced
create a function that finds the nth fibonacci number using memoization
```

---

## Key Features Explained

### 1. Intelligent Prompt Refinement
The Refiner agent clarifies ambiguous prompts:
- **Input**: "make a prime checker"
- **Output**: "Create a function that takes an integer n and returns True if n is prime, False otherwise. Handle edge cases: n <= 1 returns False."

### 2. Iterative Error Correction
If code fails:
1. Feedback sent back to Coder
2. New attempt with context
3. Up to 10 attempts (configurable)
4. Learning from previous mistakes

### 3. Smart Test Generation
Automatically creates pytest tests:
```python
# For: "create a function that finds primes less than n"
def test_finds_primes():
    assert find_primes(10) == [2, 3, 5, 7]
    assert find_primes(2) == []
```

### 4. Non-Blocking Flake8
Style issues are reported but don't block workflow:
```
[Flake8] Found 2 style issues (non-blocking)
  - Line 9: E305 expected 2 blank lines
  - Line 15: W292 no newline at end of file
[Success] Code generation complete
```

---

## Tech Stack
- **LangGraph**: Multi-agent workflow orchestration
- **LangChain**: Agent framework and LLM integration
- **Ollama**: Local LLM inference (no API keys needed)
- **Flake8**: Python code linting
- **pytest**: Automated testing framework
- **Tkinter**: Cross-platform GUI
- **Pygments**: Syntax highlighting

---

## Troubleshooting

### Docker Issues
```bash
# Check if Ollama container is running
docker ps | grep ollama

# View container logs
docker logs ollama-server

# Restart container
docker-compose restart

# Reset everything (removes models too)
docker-compose down -v
./setup_ollama.sh
```

### GUI doesn't start
```bash
# macOS
brew install python-tk@3.12

# Linux (Ubuntu/Debian)
sudo apt install python3-tk

# Verify installation
python3 -c "import tkinter; print('OK')"
```

### Port 11434 already in use (Docker)
```bash
# This means Ollama is already running locally
# Option 1: Use local Ollama (no Docker needed)
ollama list

# Option 2: Stop local Ollama, use Docker
pkill ollama                    # Linux/macOS
# OR
brew services stop ollama       # macOS with Homebrew

# Then run setup again
./setup.sh
```

### Ollama not responding
```bash
# Check status
systemctl status ollama

# Restart service
sudo systemctl restart ollama

# Test connection
ollama list
```

### Model not found
```bash
# List installed models
ollama list

# Download missing model
ollama pull deepseek-coder:6.7b
```

### Code generation keeps failing
1. Check model is properly loaded: `ollama list`
2. Try simpler prompt first
3. Use "Use Original" instead of refined
4. Check logs in GUI error tab
5. Increase max_attempts in `workflow.py`

### Tokenization artifacts in code
Fixed in latest version. If you see `<|begin_of_sentence|>`, the clean_code function in coder.py handles these artifacts.

---

## Ollama Commands Reference
```bash
ollama list                    # List installed models
ollama pull <model>            # Download a model
ollama rm <model>              # Remove a model
ollama run <model>             # Test interactively
ollama ps                      # Show running models
ollama stop <model>            # Stop a model
```

Models location: `~/.ollama/models/`

---

## Development

### Adding New Models
Edit `gui/app.py`:
```python
AVAILABLE_MODELS = [
    ("your-model:tag", "Display Name - Description"),
    ...
]
```

### Modifying Agents
Each agent in `agents/` can be customized:
- `coder.py`: Code generation logic
- `reviewer.py`: Review criteria
- `tester.py`: Test generation patterns
- `refiner.py`: Prompt refinement strategy

---

## Known Limitations
- No support for non-Python languages
- Requires local Ollama installation
- Large models need significant RAM
- No GPU acceleration (CPU only)
- Limited to single-file programs

---

## Contributing
This is an academic project. For suggestions:
1. Test with benchmark suite
2. Document issues with logs
3. Submit feedback to authors

---

## License
Academic project - CNAM Paris

---

## Authors
**Mehdi Amine DJERBOUA**, Ali TALEB, Sahil SARTAJ

**Course**: USEEW2 - Generative AI for Advanced Automation 
**Instructor**: Dr. Fehmi Ben Abdesslem 
**Institution**: CNAM Paris - Master 2 AI for Connected Industry 
**Year**: 2024-2025

---

## Acknowledgments
- Anthropic Claude for development assistance
- Ollama team for local LLM infrastructure
- LangChain community for agent frameworks
- CNAM Paris for academic support

---

**Ready to generate code? Run `python main.py` and start coding!**