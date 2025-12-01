"""
Web Interface: Real-time visualization of the multi-agent system
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import threading
from main import CodeTestCrew

app = Flask(__name__)
app.config['SECRET_KEY'] = 'code-test-crew-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global crew instance
crew = None

def emit_progress(message, status="info"):
    """Emit progress updates to the web interface"""
    socketio.emit('progress', {'message': message, 'status': status})

class WebCoderAgent:
    """Extended Coder Agent with web notifications"""
    def __init__(self, base_agent):
        self.agent = base_agent
    
    def write_code(self, specification, feedback=None):
        emit_progress(f"🤖 Coder Agent: Writing code (Attempt {self.agent.attempt_count + 1})...", "working")
        result = self.agent.write_code(specification, feedback)
        emit_progress(f"✓ Code written to: {result}", "success")
        return result
    
    def __getattr__(self, name):
        return getattr(self.agent, name)

class WebReviewerAgent:
    """Extended Reviewer Agent with web notifications"""
    def __init__(self, base_agent):
        self.agent = base_agent
    
    def review_code(self, file_path):
        emit_progress("🔍 Reviewer Agent: Checking code quality...", "working")
        result = self.agent.review_code(file_path)
        if result['passed']:
            emit_progress("✓ Code review: PASSED", "success")
        else:
            emit_progress(f"⚠ Code review: Found {len(result['issues'])} issue(s)", "warning")
        return result

class WebTesterAgent:
    """Extended Tester Agent with web notifications"""
    def __init__(self, base_agent):
        self.agent = base_agent
    
    def test_code(self, file_path, specification):
        emit_progress("🧪 Tester Agent: Running tests...", "working")
        result = self.agent.test_code(file_path, specification)
        if result['passed']:
            emit_progress(f"✓ All {len(result.get('passed_tests', []))} tests passed!", "success")
        else:
            emit_progress(f"✗ Tests failed: {len(result['errors'])} error(s)", "error")
        return result

def run_crew_with_updates(user_request):
    """Run the crew with real-time updates"""
    global crew
    
    emit_progress(f"📝 Starting: {user_request}", "info")
    emit_progress("", "separator")
    
    # Generate specification
    emit_progress("🎯 Prompt Agent: Analyzing request...", "working")
    spec = crew.prompt_agent.generate_specification(user_request)
    emit_progress(f"✓ Specification created: {spec['function_name']}", "success")
    emit_progress("", "separator")
    
    # Reset attempts
    crew.coder_agent.reset_attempts()
    
    feedback = None
    
    for attempt in range(1, crew.max_attempts + 1):
        emit_progress(f"🔄 ATTEMPT {attempt}/{crew.max_attempts}", "info")
        
        # Write code
        file_path = crew.coder_agent.write_code(spec, feedback)
        
        # Review code
        review_result = crew.reviewer_agent.review_code(file_path)
        
        # Test code
        test_result = crew.tester_agent.test_code(file_path, spec)
        
        # Check results
        both_passed = review_result['passed'] and test_result['passed']
        
        if both_passed:
            emit_progress("", "separator")
            emit_progress(f"🎉 SUCCESS on attempt {attempt}!", "success")
            
            # Read final code
            with open(file_path, 'r') as f:
                final_code = f.read()
            
            socketio.emit('complete', {
                'success': True,
                'attempts': attempt,
                'file_path': file_path,
                'code': final_code
            })
            return
        else:
            feedback = crew._generate_feedback(review_result, test_result)
            if attempt < crew.max_attempts:
                emit_progress("🔄 Generating feedback for next attempt...", "warning")
                emit_progress("", "separator")
    
    # Failed after max attempts
    emit_progress("", "separator")
    emit_progress(f"❌ FAILED after {crew.max_attempts} attempts", "error")
    
    # Read the last attempted code even if failed
    try:
        with open(file_path, 'r') as f:
            final_code = f.read()
    except:
        final_code = "// Error reading the generated code"
    
    socketio.emit('complete', {
        'success': False,
        'attempts': crew.max_attempts,
        'file_path': file_path,
        'code': final_code  # Add the code here
    })

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@socketio.on('start_coding')
def handle_start_coding(data):
    """Handle coding request from web interface"""
    global crew
    
    user_request = data.get('request', '')
    
    if not user_request:
        emit('error', {'message': 'Please provide a coding request'})
        return
    
    # Initialize crew if needed
    if crew is None:
        crew = CodeTestCrew(max_attempts=10)
        # Wrap agents with web-enabled versions
        crew.coder_agent = WebCoderAgent(crew.coder_agent)
        crew.reviewer_agent = WebReviewerAgent(crew.reviewer_agent)
        crew.tester_agent = WebTesterAgent(crew.tester_agent)
    
    # Run in background thread
    thread = threading.Thread(target=run_crew_with_updates, args=(user_request,))
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    
    print("\n" + "="*80)
    print("CODE & TEST CREW - WEB INTERFACE")
    print("="*80)
    print("\nStarting server...")
    print("Open your browser and go to: http://localhost:5001")
    print("\nPress Ctrl+C to stop the server")
    print("="*80 + "\n")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5001)