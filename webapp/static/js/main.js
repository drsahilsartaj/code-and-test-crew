/**
 * Code Generation Crew - Web App JavaScript
 * Added: VS Code Online (vscode.dev) integration
 */

let socket = null;
let sessionId = null;
let isRunning = false;
let codeVersions = [];
let currentCode = '';
let refinedPromptText = '';
let originalPromptText = '';
let waitingForPromptChoice = false;

const MAX_ATTEMPTS = 10;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    checkStatus();
});

function initSocket() {
    socket = io();
    
    socket.on('connect', () => {
        document.getElementById('connectionStatus').textContent = 'Connected';
        document.getElementById('connectionStatus').style.color = '#00ff88';
    });
    
    socket.on('disconnect', () => {
        document.getElementById('connectionStatus').textContent = 'Disconnected';
        document.getElementById('connectionStatus').style.color = '#ff4444';
    });
    
    socket.on('session_created', (data) => {
        sessionId = data.session_id;
    });
    
    socket.on('log', (data) => {
        if (data.session_id === sessionId) {
            addLog(data.agent, data.message, data.level, data.timestamp);
            updateAgentStatus(data.agent, data.level);
        }
    });
    
    socket.on('status', (data) => {
        if (data.session_id === sessionId) {
            handleStatus(data.status, data.data);
        }
    });
    
    socket.on('refined_prompt', (data) => {
        if (data.session_id === sessionId) {
            showRefinedPrompt(data.original, data.refined);
        }
    });
    
    socket.on('code_result', (data) => {
        if (data.session_id === sessionId) {
            handleCodeResult(data);
        }
    });
    
    socket.on('error', (data) => {
        toast(data.message, 'error');
    });
}

async function checkStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.ollama_connected) {
            document.getElementById('connectionStatus').textContent = 'Ready';
            document.getElementById('connectionStatus').style.color = '#00ff88';
        } else {
            document.getElementById('connectionStatus').textContent = 'Ollama Offline';
            document.getElementById('connectionStatus').style.color = '#ff4444';
            toast('Start Ollama: ./start.sh', 'error');
        }
    } catch (e) {
        document.getElementById('connectionStatus').textContent = 'Server Error';
        document.getElementById('connectionStatus').style.color = '#ff4444';
    }
}

// Agent Status - FIXED: Keep warning state, don't clear completed agents
function updateAgentStatus(agent, level) {
    const agentEl = document.getElementById(`agent-${agent}`);
    if (agentEl) {
        // Only remove 'active' from other agents (keep success/warning/error)
        document.querySelectorAll('.agent-item').forEach(el => {
            if (el.id !== `agent-${agent}`) {
                el.classList.remove('active');
            }
        });
        
        // Remove only active state, keep final states
        agentEl.classList.remove('active');
        
        if (level === 'success') {
            agentEl.classList.remove('error', 'warning');
            agentEl.classList.add('success');
        } else if (level === 'error') {
            agentEl.classList.remove('success', 'warning');
            agentEl.classList.add('error');
        } else if (level === 'warning') {
            agentEl.classList.remove('success', 'error');
            agentEl.classList.add('warning');
        } else {
            agentEl.classList.add('active');
        }
    }
}

function resetAgentStatus() {
    document.querySelectorAll('.agent-item').forEach(el => {
        el.classList.remove('active', 'success', 'error', 'warning');
    });
}

// Logging
function addLog(agent, message, level = 'info', timestamp = null) {
    const time = timestamp || new Date().toLocaleTimeString('en-US', { hour12: false });
    const entry = document.createElement('div');
    entry.className = `log-entry ${agent} ${level}`;
    entry.innerHTML = `
        <span class="time">${time}</span>
        <span class="agent">[${agent.charAt(0).toUpperCase() + agent.slice(1)}]</span>
        <span class="message">${escapeHtml(message)}</span>
    `;
    
    const activityTab = document.getElementById('activityTab');
    activityTab.appendChild(entry);
    activityTab.scrollTop = activityTab.scrollHeight;
    
    if (level === 'error') {
        const errorsTab = document.getElementById('errorsTab');
        errorsTab.appendChild(entry.cloneNode(true));
        errorsTab.scrollTop = errorsTab.scrollHeight;
    }
}

function switchTab(btn, tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('activityTab').style.display = tab === 'activity' ? 'block' : 'none';
    document.getElementById('errorsTab').style.display = tab === 'errors' ? 'block' : 'none';
}

// Prompt Handling
function showRefinedPrompt(original, refined) {
    originalPromptText = original;
    refinedPromptText = refined;
    document.getElementById('refinedPrompt').textContent = refined;
    
    document.getElementById('useOriginalBtn').disabled = false;
    document.getElementById('useRefinedBtn').disabled = false;
    document.getElementById('refineAgainBtn').disabled = false;
    
    waitingForPromptChoice = true;
    document.getElementById('statusText').textContent = 'Choose prompt';
    
    addLog('system', 'Choose: Use Original, Use Refined, or Refine Again', 'info');
}

function useOriginal() {
    if (!waitingForPromptChoice) return;
    waitingForPromptChoice = false;
    disablePromptButtons();
    addLog('system', 'Using original prompt', 'info');
    continueGeneration(false);
}

function useRefined() {
    if (!waitingForPromptChoice) return;
    waitingForPromptChoice = false;
    disablePromptButtons();
    addLog('system', 'Using refined prompt', 'info');
    continueGeneration(true);
}

function refineAgain() {
    if (!waitingForPromptChoice) return;
    addLog('system', 'Refining prompt again...', 'info');
    socket.emit('refine_again', { session_id: sessionId });
}

function disablePromptButtons() {
    document.getElementById('useOriginalBtn').disabled = true;
    document.getElementById('useRefinedBtn').disabled = true;
    document.getElementById('refineAgainBtn').disabled = true;
}

function continueGeneration(useRefined) {
    socket.emit('continue_generation', {
        session_id: sessionId,
        use_refined: useRefined
    });
}

// Generation Control
function startGeneration() {
    const prompt = document.getElementById('promptInput').value.trim();
    if (!prompt) {
        toast('Enter a prompt first', 'error');
        return;
    }
    if (!sessionId) {
        toast('No session - refresh page', 'error');
        return;
    }
    if (isRunning) {
        toast('Already running', 'error');
        return;
    }
    
    codeVersions = [];
    currentCode = '';
    updateVersions();
    updateCode('');
    resetAgentStatus();
    document.getElementById('refinedPrompt').textContent = '';
    document.getElementById('activityTab').innerHTML = '';
    document.getElementById('errorsTab').innerHTML = '';
    document.getElementById('attemptInfo').textContent = 'Attempt: 0/10';
    document.getElementById('progressFillHeader').style.width = '0%';
    
    addLog('system', 'Starting code generation...', 'info');
    
    socket.emit('start_generation', {
        session_id: sessionId,
        prompt: prompt,
        model: document.getElementById('modelSelect').value
    });
}

function stopGeneration() {
    if (sessionId) {
        socket.emit('stop_generation', { session_id: sessionId });
        addLog('system', 'Stop requested...', 'warning');
    }
}

function clearAll() {
    document.getElementById('promptInput').value = '';
    document.getElementById('refinedPrompt').textContent = '';
    document.getElementById('activityTab').innerHTML = '';
    document.getElementById('errorsTab').innerHTML = '';
    updateCode('');
    codeVersions = [];
    updateVersions();
    resetAgentStatus();
    document.getElementById('attemptInfo').textContent = 'Attempt: 0/10';
    document.getElementById('progressFillHeader').style.width = '0%';
    document.getElementById('statusText').textContent = 'Ready';
}

function handleStatus(status, data) {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusText = document.getElementById('statusText');
    
    switch (status) {
        case 'started':
            isRunning = true;
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusText.textContent = 'Running';
            break;
            
        case 'refining':
            statusText.textContent = 'Refining...';
            break;
            
        case 'generating':
            if (data) {
                document.getElementById('attemptInfo').textContent = `Attempt: ${data.attempt}/${MAX_ATTEMPTS}`;
                document.getElementById('progressFillHeader').style.width = `${(data.attempt / MAX_ATTEMPTS) * 100}%`;
                statusText.textContent = `Generating (${data.attempt}/${MAX_ATTEMPTS})`;
            }
            break;
            
        case 'completed':
            isRunning = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusText.textContent = 'Complete';
            toast('Code generated successfully!', 'success');
            break;
            
        case 'failed':
            isRunning = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusText.textContent = 'Failed';
            toast('Generation failed', 'error');
            break;
            
        case 'stopped':
            isRunning = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusText.textContent = 'Stopped';
            disablePromptButtons();
            break;
            
        case 'error':
            isRunning = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusText.textContent = 'Error';
            disablePromptButtons();
            break;
    }
}

function handleCodeResult(data) {
    currentCode = data.code || '';
    codeVersions = data.versions || [];
    updateVersions();
    updateCode(currentCode);
}

function updateVersions() {
    const select = document.getElementById('versionSelect');
    select.innerHTML = '<option value="latest">Latest</option>';
    codeVersions.forEach((v, i) => {
        select.innerHTML += `<option value="${i}">v${v.attempt} (${v.timestamp})</option>`;
    });
}

function loadVersion() {
    const val = document.getElementById('versionSelect').value;
    if (val === 'latest') {
        updateCode(currentCode);
    } else {
        const version = codeVersions[parseInt(val)];
        if (version) {
            updateCode(version.code);
        }
    }
}

function updateCode(code) {
    const codeEl = document.getElementById('codeOutput');
    codeEl.textContent = code;
    if (code) {
        hljs.highlightElement(codeEl);
    }
    
    const lines = code ? code.split('\n') : [''];
    document.getElementById('lineNumbers').innerHTML = lines.map((_, i) => i + 1).join('<br>');
}

// ========== RUN CODE ONLINE - Copy and open IDE ==========
function openInVSCode() {
    const code = document.getElementById('codeOutput').textContent;
    if (!code || code.trim() === '') {
        toast('No code to run', 'error');
        return;
    }
    
    // Copy code to clipboard first
    navigator.clipboard.writeText(code).then(() => {
        // Open OneCompiler Python IDE (supports running Python)
        window.open('https://onecompiler.com/python', '_blank');
        toast('Code copied! Press Ctrl+V to paste in editor', 'success');
    }).catch(() => {
        // Fallback
        window.open('https://onecompiler.com/python', '_blank');
        toast('Open editor - copy code manually', 'info');
    });
}

function downloadCode() {
    const code = document.getElementById('codeOutput').textContent;
    if (!code) {
        toast('No code to download', 'error');
        return;
    }
    const blob = new Blob([code], { type: 'text/x-python' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'generated_code.py';
    a.click();
    URL.revokeObjectURL(a.href);
    toast('Downloaded!', 'success');
}

function toast(msg, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `toast show ${type}`;
    setTimeout(() => el.className = 'toast', 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !isRunning) {
        startGeneration();
    }
    if (e.key === 'Escape' && isRunning) {
        stopGeneration();
    }
});
