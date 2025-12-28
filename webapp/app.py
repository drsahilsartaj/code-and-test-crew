"""
Code and Test Crew - Web Application
Uses the ACTUAL agents from parent project (same as Tkinter GUI)
FIXED: Proper handling of review_code return value
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import requests
from datetime import datetime
import uuid

# Import the ACTUAL agents - same as gui/app.py
try:
    from agents.coder import generate_code, save_code
    from agents.reviewer import review_code
    from agents.tester import run_tests
    from agents.refiner import refine_prompt
    from utils.state import create_initial_state
    from utils.flake8_checker import run_flake8
    from langchain_ollama import ChatOllama
    
    import agents.coder as coder_module
    import agents.reviewer as reviewer_module
    import agents.refiner as refiner_module
    
    AGENTS_AVAILABLE = True
    print("✅ Loaded agents from parent project")
except ImportError as e:
    AGENTS_AVAILABLE = False
    print(f"❌ Could not load agents: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

OLLAMA_BASE_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')

AVAILABLE_MODELS = [
    {"id": "codellama:7b-instruct-q4_0", "name": "CodeLlama 7B (Fast)"},
    {"id": "deepseek-coder:6.7b", "name": "DeepSeek Coder 6.7B (Balanced)"},
    {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B (Best Quality)"},
]

DEFAULT_MODEL = "deepseek-coder:6.7b"
sessions = {}


def check_ollama():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except:
        return False


def get_models():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m['name'] for m in r.json().get('models', [])]
    except:
        pass
    return []


def run_refinement(session_id, prompt, model):
    """Run prompt refinement using ACTUAL refiner agent."""
    session = sessions.get(session_id, {})
    
    try:
        state = create_initial_state(prompt)
        session['state'] = state
        session['model'] = model
        
        refiner_module.llm = ChatOllama(model=model, temperature=0.3)
        
        socketio.emit('log', {
            'session_id': session_id,
            'agent': 'refiner',
            'message': 'Refining prompt...',
            'level': 'info',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        refined = refine_prompt(state)
        state["refined_prompt"] = refined
        state["refinement_history"].append(refined)
        
        socketio.emit('log', {
            'session_id': session_id,
            'agent': 'refiner',
            'message': 'Prompt refined',
            'level': 'success',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        socketio.emit('refined_prompt', {
            'session_id': session_id,
            'original': prompt,
            'refined': refined
        })
        
    except Exception as e:
        socketio.emit('log', {
            'session_id': session_id,
            'agent': 'refiner',
            'message': f'Error: {str(e)[:100]}',
            'level': 'error',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        if 'state' not in session:
            state = create_initial_state(prompt)
            session['state'] = state
        session['state']["refined_prompt"] = prompt
        
        socketio.emit('refined_prompt', {
            'session_id': session_id,
            'original': prompt,
            'refined': prompt
        })


def run_workflow(session_id):
    """Run workflow using ACTUAL agents - FIXED reviewer handling."""
    
    session = sessions.get(session_id, {})
    state = session.get('state')
    model = session.get('model', DEFAULT_MODEL)
    
    if not state:
        return
    
    def emit_log(msg, agent="system", level="info"):
        socketio.emit('log', {
            'session_id': session_id,
            'agent': agent,
            'message': msg,
            'level': level,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    
    def emit_status(status, data=None):
        socketio.emit('status', {
            'session_id': session_id,
            'status': status,
            'data': data
        })
    
    try:
        session['is_running'] = True
        session['stop_requested'] = False
        session['code_versions'] = []
        
        # Setup LLMs - SAME as Tkinter GUI
        coder_module.llm = ChatOllama(model=model, temperature=0.2)
        reviewer_module.llm = ChatOllama(model=model, temperature=0.1)
        
        emit_status('started')
        emit_log(f"Using model: {model}", "system")
        
        max_attempts = state.get("max_attempts", 10)
        
        while state["workflow_status"] == "in_progress":
            if session.get('stop_requested'):
                emit_log("Stopped by user", "system", "warning")
                emit_status('stopped')
                return
            
            if state["current_attempt"] >= max_attempts:
                emit_log(f"Max attempts ({max_attempts}) reached", "system", "error")
                emit_status('failed')
                return
            
            state["current_attempt"] += 1
            attempt = state["current_attempt"]
            
            emit_status('generating', {'attempt': attempt, 'max': max_attempts})
            emit_log(f"--- Attempt {attempt}/{max_attempts} ---", "system")
            
            # ===== CODER AGENT =====
            emit_log("Generating code...", "coder")
            try:
                code = generate_code(state)
                state["generated_code"] = code
                os.makedirs("outputs", exist_ok=True)
                save_code(code, state["code_file_path"])
                emit_log("Code generated", "coder", "success")
            except Exception as e:
                emit_log(f"Coder error: {str(e)[:80]}", "coder", "error")
                state["feedback_history"].append({"source": "Coder", "message": str(e)})
                continue
            
            # Store version
            session['code_versions'].append({
                'attempt': attempt,
                'code': code,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            
            socketio.emit('code_result', {
                'session_id': session_id,
                'code': code,
                'versions': session['code_versions'],
                'success': False
            })
            
            # ===== REVIEWER AGENT - FIXED! =====
            emit_log("Reviewing code...", "reviewer")
            try:
                # review_code RETURNS a dict, doesn't modify state!
                review_result = review_code(state)
                
                if review_result is None:
                    emit_log("Reviewer returned None, skipping...", "reviewer", "warning")
                    continue
                
                status = review_result.get("status", "rejected")
                feedback = review_result.get("feedback", "No feedback")
                
                # Update state with review results
                state["reviewer_status"] = status
                state["reviewer_feedback"] = feedback
                
                if status == "approved":
                    emit_log("Code approved", "reviewer", "success")
                else:
                    emit_log(f"Rejected: {feedback[:80]}...", "reviewer", "warning")
                    state["feedback_history"].append({
                        "source": "Reviewer",
                        "message": feedback,
                        "attempt": attempt
                    })
                    continue
                    
            except Exception as e:
                emit_log(f"Reviewer error: {str(e)[:80]}", "reviewer", "error")
                continue
            
            # ===== FLAKE8 CHECK =====
            emit_log("Running style check...", "flake8")
            try:
                flake8_issues = run_flake8(code)
                if flake8_issues:
                    state["flake8_status"] = "issues"
                    state["flake8_report"] = flake8_issues
                    emit_log(f"{len(flake8_issues)} style issues (non-blocking)", "flake8", "warning")
                else:
                    state["flake8_status"] = "clean"
                    emit_log("Style check passed", "flake8", "success")
            except Exception as e:
                emit_log(f"Flake8: {str(e)[:50]}", "flake8", "warning")
            
            # ===== TESTER AGENT - FIXED! =====
            emit_log("Running tests...", "tester")
            try:
                # run_tests RETURNS a dict too!
                test_result = run_tests(state)
                
                if test_result is None:
                    emit_log("Tester returned None", "tester", "warning")
                    continue
                
                test_status = test_result.get("status", "fail")
                test_results = test_result.get("results", "No results")
                
                state["tester_status"] = test_status
                state["tester_results"] = test_results
                
                if test_status == "pass":
                    emit_log("All tests passed!", "tester", "success")
                    state["workflow_status"] = "success"
                    break
                else:
                    emit_log("Tests failed", "tester", "warning")
                    state["feedback_history"].append({
                        "source": "Tester",
                        "message": f"Tests failed: {test_results[:200]}",
                        "attempt": attempt
                    })
                    
            except Exception as e:
                emit_log(f"Tester error: {str(e)[:80]}", "tester", "error")
                state["feedback_history"].append({"source": "Tester", "message": str(e)})
        
        # Final result
        if state["workflow_status"] == "success":
            emit_status('completed')
            emit_log("✅ Code generation complete!", "system", "success")
        else:
            emit_status('failed')
            emit_log("❌ Generation failed", "system", "error")
        
        socketio.emit('code_result', {
            'session_id': session_id,
            'code': state.get("generated_code", ""),
            'versions': session['code_versions'],
            'success': state["workflow_status"] == "success"
        })
        
    except Exception as e:
        emit_log(f"Workflow error: {str(e)}", "system", "error")
        emit_status('error')
    finally:
        session['is_running'] = False


# ========== Routes ==========

@app.route('/')
def index():
    return render_template('index.html', models=AVAILABLE_MODELS, default_model=DEFAULT_MODEL)


@app.route('/api/status')
def api_status():
    return jsonify({
        'ollama_connected': check_ollama(),
        'available_models': get_models(),
        'agents_available': AGENTS_AVAILABLE
    })


# ========== WebSocket Events ==========

@socketio.on('connect')
def handle_connect():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'is_running': False,
        'code_versions': [],
        'state': None,
        'model': DEFAULT_MODEL
    }
    emit('session_created', {'session_id': session_id})


@socketio.on('start_generation')
def handle_start(data):
    session_id = data.get('session_id')
    prompt = data.get('prompt', '').strip()
    model = data.get('model', DEFAULT_MODEL)
    
    if not prompt:
        emit('error', {'message': 'Enter a prompt'})
        return
    
    if not session_id or session_id not in sessions:
        emit('error', {'message': 'Invalid session'})
        return
    
    session = sessions[session_id]
    if session.get('is_running'):
        emit('error', {'message': 'Already running'})
        return
    
    session['model'] = model
    
    emit('status', {'session_id': session_id, 'status': 'refining'})
    emit('log', {
        'session_id': session_id,
        'agent': 'system',
        'message': 'Starting code generation...',
        'level': 'info',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    thread = threading.Thread(target=run_refinement, args=(session_id, prompt, model))
    thread.daemon = True
    thread.start()


@socketio.on('continue_generation')
def handle_continue(data):
    session_id = data.get('session_id')
    use_refined = data.get('use_refined', True)
    
    if not session_id or session_id not in sessions:
        emit('error', {'message': 'Invalid session'})
        return
    
    session = sessions[session_id]
    state = session.get('state')
    
    if not state:
        emit('error', {'message': 'No state - click Start first'})
        return
    
    if use_refined and state.get("refined_prompt"):
        state["problem_description"] = state["refined_prompt"]
        socketio.emit('log', {
            'session_id': session_id,
            'agent': 'system',
            'message': 'Using refined prompt',
            'level': 'info',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    else:
        state["problem_description"] = state["raw_prompt"]
        socketio.emit('log', {
            'session_id': session_id,
            'agent': 'system',
            'message': 'Using original prompt',
            'level': 'info',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    
    state["workflow_status"] = "in_progress"
    state["prompt_confirmed"] = True
    
    thread = threading.Thread(target=run_workflow, args=(session_id,))
    thread.daemon = True
    thread.start()


@socketio.on('refine_again')
def handle_refine_again(data):
    session_id = data.get('session_id')
    
    if not session_id or session_id not in sessions:
        return
    
    session = sessions[session_id]
    state = session.get('state')
    model = session.get('model', DEFAULT_MODEL)
    
    if not state:
        return
    
    prompt = state.get('raw_prompt', '')
    
    socketio.emit('log', {
        'session_id': session_id,
        'agent': 'system',
        'message': 'Re-refining prompt...',
        'level': 'info',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })
    
    thread = threading.Thread(target=run_refinement, args=(session_id, prompt, model))
    thread.daemon = True
    thread.start()


@socketio.on('stop_generation')
def handle_stop(data):
    session_id = data.get('session_id')
    if session_id and session_id in sessions:
        sessions[session_id]['stop_requested'] = True
        socketio.emit('log', {
            'session_id': session_id,
            'agent': 'system',
            'message': 'Stop requested...',
            'level': 'warning',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        emit('status', {'session_id': session_id, 'status': 'stopped'})


# ========== Main ==========

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()
    
    print("\n" + "="*55)
    print("  Code Generation Crew - Web Application")
    print("="*55)
    
    if not AGENTS_AVAILABLE:
        print("\n❌ Cannot start without agents!")
        print("   pip install langchain-ollama")
        sys.exit(1)
    
    if check_ollama():
        print("✅ Ollama connected")
        models = get_models()
        print(f"📦 Models: {', '.join(models[:3]) if models else 'None'}")
    else:
        print("⚠️  Ollama not connected")
    
    print(f"\n🌐 Web App: http://localhost:{args.port}")
    print("="*55 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=args.port, debug=True, allow_unsafe_werkzeug=True)
