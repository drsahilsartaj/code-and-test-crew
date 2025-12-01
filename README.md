# Code & Test Crew - Multi-Agent AI System

**Author:** Sahil Sartaj  
**Course:** Gen AI - USEEW2  
**Project:** Multi-Agent Code Generation & Testing System

## What I Built

A multi-agent AI system that automatically writes, reviews, and tests Python code using local LLMs. The system works completely autonomously - you give it a coding task, and it iteratively improves the code until it passes all tests.

## Key Features

- **4 Intelligent Agents:**
  - Prompt Agent - Analyzes requests and generates specifications
  - Coder Agent - Writes Python code
  - Reviewer Agent - Checks code quality with Flake8
  - Tester Agent - Runs automated tests

- **Two Different LLM Models Used:**
  - **Gemma3 1B** - Initially used for rapid prototyping (lightweight model)
  - **CodeLlama 7B** - Final model for better code generation (specialized coding model)
  - Both run locally via Ollama (no API costs!)

- **Feedback Loop:** Up to 10 attempts to fix errors automatically
- **Real-time Web Interface:** Live progress updates as agents work
- **Performance Improvement:** 50% → 75% success rate after switching to CodeLlama

## How It Works

1. User enters a coding request (e.g., "Write a function that checks if a string is a palindrome")
2. Prompt Agent uses AI to create detailed specifications and test cases
3. Coder Agent writes the Python code
4. Reviewer Agent checks code quality
5. Tester Agent runs tests
6. If tests fail → feedback sent back to Coder Agent → retry (up to 10 times)
7. Success → Clean, tested code delivered!

## Installation
```bash
# Clone repository
git clone https://github.com/drsahilsartaj/code-and-test-crew.git
cd code-and-test-crew

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Ollama and models
# Download Ollama from https://ollama.com
ollama pull gemma3:1b      # Lightweight model (815 MB)
ollama pull codellama:7b   # Better coding model (3.8 GB)
```

## Usage

**Web Interface (Recommended):**
```bash
python web_interface.py
# Open browser to http://localhost:5001
```

**Command Line:**
```bash
python main.py
```

**Run Benchmark Tests:**
```bash
python benchmark.py
```

## Example Tasks It Can Handle

- Check if string is palindrome
- Calculate factorial of a number
- Find largest number in a list
- Convert Celsius to Fahrenheit
- Remove duplicates from a list
- Sum of even numbers in a list
- And many more...

## Results

**With Gemma3 1B:**
- Success Rate: 50% (5 out of 10 benchmark tests)
- Average Attempts: 1.8 for successful tasks

**With CodeLlama 7B:**
- Success Rate: 75% (3 out of 4 diverse tests)
- Average Attempts: 1-2 for successful tasks
- Much better at handling complex logic and edge cases

## Technologies

- Python 3.13
- Gemma3 1B + CodeLlama 7B (Ollama)
- Flask + SocketIO
- Flake8
- HTML/CSS/JavaScript

## What I Learned

- Multi-agent system design and orchestration
- Comparing different LLM models for coding tasks
- Working with local LLMs (Ollama)
- Prompt engineering for structured outputs
- Automated code quality checking and testing
- Real-time web applications with WebSockets
- Iterative improvement through feedback loops
- Model selection impacts success rates significantly

## Key Insights

- **Model Size Matters:** CodeLlama 7B (3.8GB) significantly outperforms Gemma3 1B (815MB) for coding tasks
- **Specialized Models Win:** CodeLlama is specifically trained for coding and handles it better than general models
- **Trade-offs:** Gemma3 is faster but less accurate; CodeLlama is slower but more reliable
- **Local LLMs are Viable:** No need for expensive cloud APIs - local models work great!

---

**Note:** This project demonstrates that you don't need expensive cloud APIs to build intelligent coding assistants - everything runs locally!
