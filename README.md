# 🤖 Intelligent Code Generation Crew

**A Three-Agent System for Automated Python Development**




## 🚀 Quick Start Guide

### Prerequisites
- ✅ Ollama installed
- ✅ Python 3.8+
- ✅ 5 minutes of your time

---

## 📦 Installation

### 1. Create Virtual Environment

```bash
# Navigate to project folder
cd code-test-crew

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install requests
```

That's it! ✅

---

## 🎮 How to Run

### Step 1: Start Ollama Server

Open a **FIRST TERMINAL** and run:

```bash
ollama serve
```

⚠️ **IMPORTANT:** Keep this terminal open while using the system!

You should see:
```
Listening on 127.0.0.1:11434
```

---

### Step 2: Download a Model (First Time Only)

Open a **SECOND TERMINAL** and run:

```bash
# Check available models
ollama list

# If you don't have a model, download one:
# Option 1 (RECOMMENDED - Fast):
ollama pull gemma3:1b

# Option 2 (Good balance):
ollama pull llama3.2

# Option 3 (Most powerful):
ollama pull llama3:latest
```

---

### Step 3: Run the System

In the **SECOND TERMINAL** (with venv activated):

```bash
python main.py
```

---

## 🎯 Using the System

### When the program starts:

1. **Choose a model:**
   ```
   Quel modèle Ollama utiliser ? (défaut: llama3.2) :
   ```
   - Press **Enter** to use default (llama3.2)
   - OR type `gemma3:1b` or `llama3:latest`

2. **Choose a problem:**
   ```
   Choisis un exemple (1-7) ou tape ton propre problème :
   ```
   - Type `1` for factorial
   - Type `2` for palindrome
   - OR type your own problem in French or English

3. **Watch the agents work:**
   - 🤖 Coder writes code
   - 🧪 Tester tests the code
   - ✅ Success or 🔄 Retry with feedback

4. **Save the code:**
   ```
   💾 Sauvegarder le code ? (o/n) :
   ```
   - Type `o` to save
   - Give it a filename (e.g., `factorial.py`)

---

## 📝 Example Run

```bash
# Terminal 1
ollama serve

# Terminal 2
cd code-test-crew
source venv/bin/activate  # or venv\Scripts\activate on Windows
python main.py

# When prompted:
Quel modèle ? → gemma3:1b
Choisis un exemple → 1
# Wait ~30 seconds
# ✅ Code generated!
Sauvegarder ? → o
Nom du fichier → factorial.py
```

---

## 🗂️ Project Structure

```
code-test-crew/
├── agent_base.py          # Base class for all agents
├── coder_agent.py         # Coder Agent implementation
├── tester_agent.py        # Tester Agent V1 (static analysis)
├── tester_agent_v2.py     # Tester Agent V2 (real execution)
├── reviewer_agent.py      # Reviewer Agent (optional, Phase 2)
├── orchestrator.py        # System orchestrator
├── llm_client.py          # Ollama client
├── main.py               # Main entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

---

## 🔧 Troubleshooting

### Problem: "Impossible de se connecter à Ollama"

**Solution:**
```bash
# Make sure Ollama is running in Terminal 1
ollama serve
```

### Problem: "ModuleNotFoundError: No module named 'requests'"

**Solution:**
```bash
# Make sure venv is activated (you should see (venv) in your prompt)
pip install requests
```

### Problem: "Model not found"

**Solution:**
```bash
# Download the model you're trying to use
ollama pull gemma3:1b
```

### Problem: "Timeout - Le modèle met trop de temps"

**Solution:**
- Use a smaller model: `gemma3:1b` (fastest)
- OR increase timeout in `llm_client.py` line 20: change `timeout=60` to `timeout=300`

---

## 🎮 Available Models

| Model           | Size | Speed | Quality |
|-------          |------|-------|---------|
| `gemma3:1b`     | 815 MB | ⚡⚡⚡ Very Fast | ⭐⭐ Good |
| `llama3.2`      | 2 GB    | ⚡⚡ Fast | ⭐⭐⭐ Very Good |
| `llama3:latest` | 4.7 GB | ⚡ Slower | ⭐⭐⭐⭐ Excellent |

**Recommendation:** Start with `gemma3:1b` for testing, use `llama3.2` for best results.

---

## 📊 Evaluation Metrics

The system tracks:
- **Pass Rate:** Percentage of functions that work (Target: 70%+)
- **First-Try Success:** Functions that work immediately
- **Average Attempts:** Mean iterations needed (Target: < 2.5)
- **Failure Analysis:** Why failures occur (syntax, logic, edge cases)

## 🆘 Need Help?

1. Check the Troubleshooting section above
2. Make sure Ollama is running: `ollama serve`
3. Make sure venv is activated: you should see `(venv)` in your terminal
4. Check that your model is installed: `ollama list`

---

## 🎉 Quick Test

Want to quickly test if everything works?

```bash
# Terminal 1
ollama serve

# Terminal 2
cd code-test-crew
source venv/bin/activate
python main.py
# Press Enter twice (use defaults)
# Type: 1
# Wait ~30 seconds
# Should see: ✅ SUCCÈS !
```

If you see success, you're all set! 🚀

---

**Last Updated:** November 17, 2025