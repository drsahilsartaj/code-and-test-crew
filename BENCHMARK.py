"""Simple Benchmark GUI for Code Generation Crew - DETAILED LOGGING VERSION."""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import queue
import json
import time
from datetime import datetime
import os
import subprocess
import platform

from utils.state import create_initial_state
from agents.coder import generate_code, save_code
from agents.reviewer import review_code
from agents.tester import run_tests
from utils.flake8_checker import run_flake8
from langchain_ollama import ChatOllama


# Matrix/Crypto Dark Theme
COLORS = {
    "bg": "#0a0f0d",
    "bg_light": "#0f1612",
    "bg_lighter": "#1a2520",
    "fg": "#c8e6c9",
    "fg_dim": "#4a6b5a",
    "accent": "#00ff88",
    "accent_hover": "#00cc6a",
    "success": "#00ff88",
    "error": "#ff4444",
    "warning": "#ffaa00",
    "border": "#1a3d2e",
    "input_bg": "#0d1510",
    "selection": "#1a4d3a",
    "code": "#88ccff",
    "refiner": "#ff88ff",
    "coder": "#88ff88",
    "reviewer": "#ffff88",
    "tester": "#88ffff",
}

# Available models
AVAILABLE_MODELS = [
    ("codellama:7b-instruct-q4_0", "CodeLlama 7B - ⚡ Fastest, good for simple tasks"),
    ("deepseek-coder:6.7b", "DeepSeek Coder 6.7B - ⚖️ Balanced speed/quality"),
    ("qwen2.5-coder:32b", "Qwen 2.5 Coder 32B - 🏆 Best quality, 🧠 complex logic, 🎯 fewer retries, ⏱️ slower"),
]

DEFAULT_MODEL = "deepseek-coder:6.7b"


class BenchmarkGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Generation Benchmark - Detailed Logs")
        self.root.geometry("1400x900")
        self.root.configure(bg=COLORS["bg"])
        
        # State
        self.prompts = []
        self.current_model = DEFAULT_MODEL
        self.is_running = False
        self.message_queue = queue.Queue()
        self.results = []
        
        # Live stats
        self.stats_passed = 0
        self.stats_failed = 0
        self.stats_current = 0
        self.stats_total = 0
        
        # Create UI
        self.setup_dark_style()
        self.create_widgets()
        
        # Start queue checker
        self.check_queue()
    
    def setup_dark_style(self):
        """Configure dark green/black theme."""
        style = ttk.Style()
        
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        
        style.configure('.', 
                       background=COLORS["bg"], 
                       foreground=COLORS["fg"],
                       fieldbackground=COLORS["input_bg"],
                       bordercolor=COLORS["border"])
        
        style.configure('TFrame', background=COLORS["bg"])
        style.configure('TLabel', background=COLORS["bg"], foreground=COLORS["fg"])
        style.configure('Title.TLabel', foreground=COLORS["accent"], 
                       font=('Segoe UI', 12, 'bold'))
        
        style.configure('TButton',
                       background=COLORS["bg_lighter"],
                       foreground=COLORS["fg"],
                       font=('Segoe UI', 9),
                       padding=(10, 5))
        
        style.configure('Accent.TButton',
                       background=COLORS["accent"],
                       foreground=COLORS["bg"],
                       font=('Segoe UI', 9, 'bold'))
        
        style.configure('TProgressbar',
                       background=COLORS["accent"],
                       troughcolor=COLORS["bg_light"])
    
    def create_widgets(self):
        """Create all widgets."""
        # Title bar
        title_frame = tk.Frame(self.root, bg=COLORS["bg_lighter"], height=40)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="📊 Code Generation Benchmark - Detailed Logs",
                bg=COLORS["bg_lighter"], fg=COLORS["accent"],
                font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT, padx=15)
        
        # Main container
        main_frame = tk.Frame(self.root, bg=COLORS["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Configuration
        left_panel = tk.Frame(main_frame, bg=COLORS["bg_light"], width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Configuration section
        config_frame = tk.Frame(left_panel, bg=COLORS["bg_light"])
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(config_frame, text="Configuration",
                bg=COLORS["bg_light"], fg=COLORS["accent"],
                font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Model selector
        tk.Label(config_frame, text="Model:", bg=COLORS["bg_light"],
                fg=COLORS["fg"]).pack(anchor=tk.W, pady=(5, 2))
        
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        model_combo = ttk.Combobox(config_frame, textvariable=self.model_var,
                                   state='readonly', width=45)
        model_combo['values'] = [f"{m[1]}" for m in AVAILABLE_MODELS]
        for i, model in enumerate(AVAILABLE_MODELS):
            if model[0] == DEFAULT_MODEL:
                model_combo.current(i)
                break
        model_combo.pack(fill=tk.X, pady=(0, 10))
        model_combo.bind("<<ComboboxSelected>>", self.on_model_select)
        
        # Load prompts button
        load_btn = ttk.Button(config_frame, text="📁 Load Prompts (JSON)",
                             command=self.load_prompts, style='Accent.TButton')
        load_btn.pack(fill=tk.X, pady=(5, 10))
        
        # Auto-save and shutdown checkbox
        self.auto_shutdown_var = tk.BooleanVar(value=False)
        auto_shutdown_cb = tk.Checkbutton(config_frame,
                                          text="💾 Auto-save & shutdown when finished",
                                          variable=self.auto_shutdown_var,
                                          bg=COLORS["bg_light"],
                                          fg=COLORS["fg"],
                                          selectcolor=COLORS["bg_lighter"],
                                          activebackground=COLORS["bg_light"],
                                          activeforeground=COLORS["accent"],
                                          font=('Segoe UI', 9))
        auto_shutdown_cb.pack(anchor=tk.W, pady=(0, 10))
        
        # Prompts info
        self.prompts_label = tk.Label(config_frame, 
                                      text="No prompts loaded",
                                      bg=COLORS["bg_light"], fg=COLORS["fg_dim"],
                                      font=('Segoe UI', 9))
        self.prompts_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Start/Stop buttons
        btn_frame = tk.Frame(config_frame, bg=COLORS["bg_light"])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Benchmark",
                                    command=self.start_benchmark,
                                    style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop",
                                   command=self.stop_benchmark,
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress section
        progress_frame = tk.Frame(left_panel, bg=COLORS["bg_light"])
        progress_frame.pack(fill=tk.X, padx=10, pady=(20, 10))
        
        tk.Label(progress_frame, text="Progress",
                bg=COLORS["bg_light"], fg=COLORS["accent"],
                font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=330,
                                           mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_label = tk.Label(progress_frame, text="Ready",
                                       bg=COLORS["bg_light"], fg=COLORS["fg"])
        self.progress_label.pack(anchor=tk.W)
        
        # ===== LIVE STATS PANEL =====
        stats_frame = tk.Frame(left_panel, bg=COLORS["bg_lighter"], relief='ridge', bd=1)
        stats_frame.pack(fill=tk.X, padx=10, pady=(15, 10))
        
        tk.Label(stats_frame, text="📊 Live Results",
                bg=COLORS["bg_lighter"], fg=COLORS["accent"],
                font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Stats grid
        stats_grid = tk.Frame(stats_frame, bg=COLORS["bg_lighter"])
        stats_grid.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Passed
        passed_frame = tk.Frame(stats_grid, bg=COLORS["bg_lighter"])
        passed_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Label(passed_frame, text=" Passed",
                bg=COLORS["bg_lighter"], fg=COLORS["success"],
                font=('Segoe UI', 9)).pack()
        self.stats_passed_label = tk.Label(passed_frame, text="0",
                bg=COLORS["bg_lighter"], fg=COLORS["success"],
                font=('Consolas', 24, 'bold'))
        self.stats_passed_label.pack()
        
        # Failed
        failed_frame = tk.Frame(stats_grid, bg=COLORS["bg_lighter"])
        failed_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Label(failed_frame, text=" Failed",
                bg=COLORS["bg_lighter"], fg=COLORS["error"],
                font=('Segoe UI', 9)).pack()
        self.stats_failed_label = tk.Label(failed_frame, text="0",
                bg=COLORS["bg_lighter"], fg=COLORS["error"],
                font=('Consolas', 24, 'bold'))
        self.stats_failed_label.pack()
        
        # Running
        running_frame = tk.Frame(stats_grid, bg=COLORS["bg_lighter"])
        running_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Label(running_frame, text=" Running",
                bg=COLORS["bg_lighter"], fg=COLORS["warning"],
                font=('Segoe UI', 9)).pack()
        self.stats_running_label = tk.Label(running_frame, text="0/0",
                bg=COLORS["bg_lighter"], fg=COLORS["warning"],
                font=('Consolas', 18, 'bold'))
        self.stats_running_label.pack()
        
        # Success rate bar
        rate_frame = tk.Frame(stats_frame, bg=COLORS["bg_lighter"])
        rate_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        tk.Label(rate_frame, text="Success Rate:",
                bg=COLORS["bg_lighter"], fg=COLORS["fg_dim"],
                font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        self.stats_rate_label = tk.Label(rate_frame, text="--",
                bg=COLORS["bg_lighter"], fg=COLORS["accent"],
                font=('Consolas', 12, 'bold'))
        self.stats_rate_label.pack(side=tk.RIGHT)
        
        # Results section
        results_frame = tk.Frame(left_panel, bg=COLORS["bg_light"])
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 10))
        
        tk.Label(results_frame, text="Results Summary",
                bg=COLORS["bg_light"], fg=COLORS["accent"],
                font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        self.results_text = tk.Text(results_frame, height=10,
                                    font=('Consolas', 9),
                                    bg=COLORS["input_bg"], fg=COLORS["fg"],
                                    relief='flat', state=tk.DISABLED)
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # Save results button
        save_btn = ttk.Button(results_frame, text="💾 Save Results", 
                              command=self.save_results, style='Accent.TButton')
        save_btn.pack(fill=tk.X, pady=(10, 0))
        
        # Right panel - Live logs
        right_panel = tk.Frame(main_frame, bg=COLORS["bg"])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Log header with clear button
        log_header = tk.Frame(right_panel, bg=COLORS["bg"])
        log_header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(log_header, text="Live Logs (All Agent Communication)",
                bg=COLORS["bg"], fg=COLORS["accent"],
                font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT)
        
        clear_btn = ttk.Button(log_header, text="🗑 Clear Logs",
                              command=self.clear_logs)
        clear_btn.pack(side=tk.RIGHT)
        
        # Log display
        log_frame = tk.Frame(right_panel, bg=COLORS["bg"])
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                  font=('Consolas', 9),
                                                  bg=COLORS["input_bg"],
                                                  fg=COLORS["fg"],
                                                  insertbackground=COLORS["accent"],
                                                  relief='flat',
                                                  state=tk.DISABLED,
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log tags for different agents/types
        self.log_text.tag_configure("success", foreground=COLORS["success"])
        self.log_text.tag_configure("error", foreground=COLORS["error"])
        self.log_text.tag_configure("warning", foreground=COLORS["warning"])
        self.log_text.tag_configure("accent", foreground=COLORS["accent"])
        self.log_text.tag_configure("code", foreground=COLORS["code"])
        self.log_text.tag_configure("refiner", foreground=COLORS["refiner"])
        self.log_text.tag_configure("coder", foreground=COLORS["coder"])
        self.log_text.tag_configure("reviewer", foreground=COLORS["reviewer"])
        self.log_text.tag_configure("tester", foreground=COLORS["tester"])
        self.log_text.tag_configure("dim", foreground=COLORS["fg_dim"])
    
    def update_live_stats(self):
        """Update the live stats panel."""
        self.stats_passed_label.configure(text=str(self.stats_passed))
        self.stats_failed_label.configure(text=str(self.stats_failed))
        self.stats_running_label.configure(text=f"{self.stats_current}/{self.stats_total}")
        
        # Calculate success rate
        completed = self.stats_passed + self.stats_failed
        if completed > 0:
            rate = (self.stats_passed / completed) * 100
            self.stats_rate_label.configure(text=f"{rate:.0f}%")
            # Color based on rate
            if rate >= 80:
                self.stats_rate_label.configure(fg=COLORS["success"])
            elif rate >= 50:
                self.stats_rate_label.configure(fg=COLORS["warning"])
            else:
                self.stats_rate_label.configure(fg=COLORS["error"])
        else:
            self.stats_rate_label.configure(text="--", fg=COLORS["accent"])
    
    def reset_live_stats(self):
        """Reset live stats to initial state."""
        self.stats_passed = 0
        self.stats_failed = 0
        self.stats_current = 0
        self.stats_total = 0
        self.update_live_stats()
    
    def clear_logs(self):
        """Clear the log display."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def on_model_select(self, event):
        """Handle model selection."""
        selected_display = self.model_var.get()
        for model_id, model_display in AVAILABLE_MODELS:
            if model_display == selected_display:
                self.current_model = model_id
                self.log(f"[System] Model selected: {model_id}", "accent")
                break
    
    def load_prompts(self):
        """Load prompts from JSON file."""
        filename = filedialog.askopenfilename(
            title="Select Prompts File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.prompts = data.get('prompts', [])
            
            if not self.prompts:
                messagebox.showwarning("No Prompts", 
                                      "No prompts found in file!")
                return
            
            # Count by difficulty
            easy = sum(1 for p in self.prompts if p.get('difficulty') == 'Easy')
            medium = sum(1 for p in self.prompts if p.get('difficulty') == 'Medium')
            hard = sum(1 for p in self.prompts if p.get('difficulty') == 'Hard')
            vhard = sum(1 for p in self.prompts if p.get('difficulty') == 'Very Hard')
            
            info_text = f"Loaded {len(self.prompts)} prompts\n"
            info_text += f"Easy: {easy} | Medium: {medium} | Hard: {hard}"
            if vhard > 0:
                info_text += f" | V.Hard: {vhard}"
            
            self.prompts_label.configure(text=info_text, fg=COLORS["success"])
            self.log(f"[System] ✓ Loaded {len(self.prompts)} prompts from {os.path.basename(filename)}", "success")
            
            # Show prompts list
            self.log("=" * 60, "dim")
            self.log("Loaded prompts:", "accent")
            for i, p in enumerate(self.prompts, 1):
                diff = p.get('difficulty', 'Unknown')
                self.log(f"  {i}. [{diff}] {p['prompt'][:50]}...", "dim")
            self.log("=" * 60, "dim")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load prompts:\n{str(e)}")
            self.log(f"[System] ✗ Error loading prompts: {str(e)}", "error")
    
    def log(self, message, tag=None):
        """Add message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, full_message, tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def log_multiline(self, message, tag=None):
        """Add multi-line message to log (no timestamp)."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def start_benchmark(self):
        """Start the benchmark."""
        if not self.prompts:
            messagebox.showwarning("No Prompts", 
                                  "Please load prompts first!")
            return
        
        self.is_running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.results = []
        
        # Reset live stats
        self.stats_total = len(self.prompts)
        self.stats_passed = 0
        self.stats_failed = 0
        self.stats_current = 0
        self.update_live_stats()
        
        # Clear results
        self.results_text.configure(state=tk.NORMAL)
        self.results_text.delete('1.0', tk.END)
        self.results_text.configure(state=tk.DISABLED)
        
        # Clear logs
        self.clear_logs()
        
        self.log("=" * 60, "accent")
        self.log(f"[System] Starting benchmark with {len(self.prompts)} prompts", "accent")
        self.log(f"[System] Model: {self.current_model}", "accent")
        self.log(f"[System] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "accent")
        if self.auto_shutdown_var.get():
            self.log(f"[System] 💾 Auto-save & shutdown enabled", "warning")
        self.log("=" * 60, "accent")
        
        # Start in thread
        thread = threading.Thread(target=self._run_benchmark)
        thread.daemon = True
        thread.start()
    
    def stop_benchmark(self):
        """Stop the benchmark."""
        self.is_running = False
        self.log("[System] ⏹ Benchmark stopped by user", "warning")
    
    def _run_benchmark(self):
        """Run benchmark in background thread."""
        from agents import coder, reviewer
        
        # Set model
        coder.llm = ChatOllama(model=self.current_model, temperature=0.2)
        reviewer.llm = ChatOllama(model=self.current_model, temperature=0.1)
        
        total = len(self.prompts)
        
        for i, prompt_data in enumerate(self.prompts, 1):
            if not self.is_running:
                break
            
            prompt = prompt_data['prompt']
            difficulty = prompt_data.get('difficulty', 'Unknown')
            
            self.message_queue.put(("progress", (i, total)))
            self.message_queue.put(("stats_current", i))
            
            # Log test header
            self.message_queue.put(("log", ("", None)))
            self.message_queue.put(("log", ("=" * 60, "accent")))
            self.message_queue.put(("log", (f"[System] TEST {i}/{total} - Difficulty: {difficulty}", "accent")))
            self.message_queue.put(("log", ("=" * 60, "accent")))
            self.message_queue.put(("log", (f"[System] PROMPT: {prompt}", "accent")))
            self.message_queue.put(("log", ("-" * 60, "dim")))
            
            start_time = time.time()
            result = self._run_single_test(prompt, difficulty, i)
            elapsed = time.time() - start_time
            
            result['elapsed'] = elapsed
            result['prompt_id'] = i
            result['difficulty'] = difficulty
            result['prompt'] = prompt
            
            self.results.append(result)
            
            # Update live stats
            if result['status'] == 'success':
                self.message_queue.put(("stats_passed", None))
            else:
                self.message_queue.put(("stats_failed", None))
            
            # Log result summary
            self.message_queue.put(("log", ("-" * 60, "dim")))
            if result['status'] == 'success':
                self.message_queue.put(("log", 
                    (f"[System] ✅ TEST {i} PASSED in {result['attempts']} attempt(s), {elapsed:.1f}s", "success")))
            else:
                self.message_queue.put(("log", 
                    (f"[System] ❌ TEST {i} FAILED after {result['attempts']} attempt(s), {elapsed:.1f}s", "error")))
                self.message_queue.put(("log", (f"[System] Failure reason: {result['reason']}", "error")))
        
        self.message_queue.put(("complete", None))
    
    def _run_single_test(self, prompt, difficulty, test_id):
        """Run a single test with detailed logging."""
        max_attempts = 10
        state = create_initial_state(prompt)
        state["problem_description"] = prompt
        state["workflow_status"] = "in_progress"
        
        for attempt in range(1, max_attempts + 1):
            if not self.is_running:
                return {
                    'status': 'stopped',
                    'attempts': attempt,
                    'reason': 'Stopped by user',
                    'generated_code': state.get("generated_code", "")
                }
            
            state["current_attempt"] = attempt
            
            self.message_queue.put(("log", ("", None)))
            self.message_queue.put(("log", (f"[System] ─── Attempt {attempt}/{max_attempts} ───", "accent")))
            
            # ===== CODER PHASE =====
            self.message_queue.put(("log", (f"[Coder] Generating code...", "coder")))
            try:
                code = generate_code(state)
                state["generated_code"] = code
                save_code(code, state["code_file_path"])
                
                # Show FULL generated code in logs
                code_lines = code.split('\n')
                self.message_queue.put(("log", (f"[Coder] ✓ Code generated ({len(code_lines)} lines)", "coder")))
                self.message_queue.put(("log", (f"[Coder] Full generated code:", "coder")))
                self.message_queue.put(("multiline", ("    ┌" + "─" * 50, "dim")))
                for line in code_lines:
                    self.message_queue.put(("multiline", (f"    │ {line}", "code")))
                self.message_queue.put(("multiline", ("    └" + "─" * 50, "dim")))
                    
            except Exception as e:
                self.message_queue.put(("log", (f"[Coder] ✗ Error: {str(e)}", "error")))
                return {
                    'status': 'failed',
                    'attempts': attempt,
                    'reason': f"Coder error: {str(e)[:100]}",
                    'generated_code': ""
                }
            
            # ===== REVIEWER PHASE =====
            self.message_queue.put(("log", (f"[Reviewer] Analyzing code...", "reviewer")))
            try:
                review = review_code(state)
                
                if review["status"] == "rejected":
                    feedback = review["feedback"]
                    state["feedback_history"].append({
                        "source": "Reviewer",
                        "message": feedback,
                        "attempt": attempt
                    })
                    self.message_queue.put(("log", (f"[Reviewer] ✗ REJECTED", "error")))
                    self.message_queue.put(("log", (f"[Reviewer] Feedback: {feedback}", "warning")))
                    continue
                else:
                    self.message_queue.put(("log", (f"[Reviewer] ✓ APPROVED", "success")))
                    
            except Exception as e:
                self.message_queue.put(("log", (f"[Reviewer] ✗ Error: {str(e)}", "error")))
                return {
                    'status': 'failed',
                    'attempts': attempt,
                    'reason': f"Reviewer error: {str(e)[:100]}",
                    'generated_code': state.get("generated_code", "")
                }
            
            # ===== FLAKE8 PHASE =====
            self.message_queue.put(("log", (f"[Flake8] Checking style...", "dim")))
            try:
                flake8_result = run_flake8(state["generated_code"])
                if flake8_result.get('issues'):
                    issue_count = len(flake8_result['issues'])
                    self.message_queue.put(("log", (f"[Flake8] Found {issue_count} style issue(s) (non-blocking)", "warning")))
                    for issue in flake8_result['issues'][:5]:  # Show first 5
                        self.message_queue.put(("log", (f"[Flake8]   • {issue}", "dim")))
                    if issue_count > 5:
                        self.message_queue.put(("log", (f"[Flake8]   ... and {issue_count - 5} more", "dim")))
                else:
                    self.message_queue.put(("log", (f"[Flake8] ✓ No style issues", "success")))
            except Exception as e:
                self.message_queue.put(("log", (f"[Flake8] Skipped: {str(e)[:50]}", "dim")))
            
            # ===== TESTER PHASE =====
            self.message_queue.put(("log", (f"[Tester] Running tests...", "tester")))
            try:
                test_result = run_tests(state)
                
                if test_result["status"] == "fail":
                    # Extract error details from test results
                    test_output = test_result.get("results", "")
                    state["feedback_history"].append({
                        "source": "Tester",
                        "message": test_output,
                        "attempt": attempt
                    })
                    self.message_queue.put(("log", (f"[Tester] ✗ TESTS FAILED", "error")))
                    
                    # Show test output (truncated)
                    output_lines = test_output.split('\n')
                    self.message_queue.put(("log", (f"[Tester] Test output:", "tester")))
                    for line in output_lines[:15]:  # First 15 lines
                        if line.strip():
                            self.message_queue.put(("multiline", (f"    {line}", "error")))
                    if len(output_lines) > 15:
                        self.message_queue.put(("multiline", (f"    ... ({len(output_lines) - 15} more lines)", "dim")))
                    continue
                else:
                    self.message_queue.put(("log", (f"[Tester] ✓ ALL TESTS PASSED", "success")))
                    
            except Exception as e:
                self.message_queue.put(("log", (f"[Tester] ✗ Error: {str(e)}", "error")))
                return {
                    'status': 'failed',
                    'attempts': attempt,
                    'reason': f"Tester error: {str(e)[:100]}",
                    'generated_code': state.get("generated_code", "")
                }
            
            # Success!
            self.message_queue.put(("log", (f"[System] ✅ Code generation successful!", "success")))
            return {
                'status': 'success',
                'attempts': attempt,
                'reason': '',
                'generated_code': state.get("generated_code", "")
            }
        
        # Max attempts reached
        self.message_queue.put(("log", (f"[System] ❌ Max attempts ({max_attempts}) reached", "error")))
        return {
            'status': 'failed',
            'attempts': max_attempts,
            'reason': 'Max attempts reached',
            'generated_code': state.get("generated_code", "")
        }
    
    def check_queue(self):
        """Process message queue."""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "log":
                    message, tag = data
                    self.log(message, tag)
                
                elif msg_type == "multiline":
                    message, tag = data
                    self.log_multiline(message, tag)
                
                elif msg_type == "progress":
                    current, total = data
                    self.progress_bar['maximum'] = total
                    self.progress_bar['value'] = current
                    self.progress_label.configure(
                        text=f"Test {current}/{total} ({100*current//total}%)")
                
                elif msg_type == "stats_current":
                    self.stats_current = data
                    self.update_live_stats()
                
                elif msg_type == "stats_passed":
                    self.stats_passed += 1
                    self.update_live_stats()
                
                elif msg_type == "stats_failed":
                    self.stats_failed += 1
                    self.update_live_stats()
                
                elif msg_type == "complete":
                    self.benchmark_complete()
        
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)
    
    def benchmark_complete(self):
        """Handle benchmark completion."""
        self.is_running = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        
        self.log("", None)
        self.log("=" * 60, "accent")
        self.log("[System] 🎉 Benchmark Complete!", "success")
        self.log("=" * 60, "accent")
        
        # Generate summary
        total = len(self.results)
        success = sum(1 for r in self.results if r['status'] == 'success')
        failed = total - success
        
        avg_attempts = sum(r['attempts'] for r in self.results) / total if total > 0 else 0
        avg_time = sum(r['elapsed'] for r in self.results) / total if total > 0 else 0
        
        # By difficulty
        easy = [r for r in self.results if r['difficulty'] == 'Easy']
        medium = [r for r in self.results if r['difficulty'] == 'Medium']
        hard = [r for r in self.results if r['difficulty'] == 'Hard']
        vhard = [r for r in self.results if r['difficulty'] == 'Very Hard']
        
        easy_success = sum(1 for r in easy if r['status'] == 'success')
        medium_success = sum(1 for r in medium if r['status'] == 'success')
        hard_success = sum(1 for r in hard if r['status'] == 'success')
        vhard_success = sum(1 for r in vhard if r['status'] == 'success')
        
        # Log summary
        self.log(f"[System] Total: {total} | Passed: {success} | Failed: {failed}", "accent")
        self.log(f"[System] Success Rate: {100*success//total if total else 0}%", "accent")
        self.log(f"[System] Avg Attempts: {avg_attempts:.1f} | Avg Time: {avg_time:.1f}s", "accent")
        
        # Display results
        self.results_text.configure(state=tk.NORMAL)
        self.results_text.delete('1.0', tk.END)
        
        summary = f"""BENCHMARK RESULTS
{'=' * 40}

Model: {self.current_model}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall:
  Total Tests:    {total}
  Success:        {success} ({100*success//total if total else 0}%)
  Failed:         {failed} ({100*failed//total if total else 0}%)
  
  Avg Attempts:   {avg_attempts:.1f}
  Avg Time:       {avg_time:.1f}s

By Difficulty:
"""
        
        if easy:
            summary += f"  Easy:      {easy_success}/{len(easy)} ({100*easy_success//len(easy)}%)\n"
        if medium:
            summary += f"  Medium:    {medium_success}/{len(medium)} ({100*medium_success//len(medium)}%)\n"
        if hard:
            summary += f"  Hard:      {hard_success}/{len(hard)} ({100*hard_success//len(hard)}%)\n"
        if vhard:
            summary += f"  Very Hard: {vhard_success}/{len(vhard)} ({100*vhard_success//len(vhard)}%)\n"
        
        summary += f"\n{'=' * 40}\n\nDetailed Results:\n\n"
        
        for r in self.results:
            status_icon = "✓" if r['status'] == 'success' else "✗"
            summary += f"{status_icon} [{r['difficulty']}] Test {r['prompt_id']}: "
            summary += f"{r['attempts']} attempts, {r['elapsed']:.1f}s\n"
            summary += f"   Prompt: {r['prompt'][:40]}...\n"
            if r['reason']:
                summary += f"   → {r['reason']}\n"
            summary += "\n"
        
        self.results_text.insert('1.0', summary)
        self.results_text.configure(state=tk.DISABLED)
        
        # AUTO-SAVE AND SHUTDOWN
        if self.auto_shutdown_var.get():
            self.log("[System] 💾 Auto-save enabled - saving results...", "warning")
            self.auto_save_and_shutdown()

    def auto_save_and_shutdown(self):
        """Auto-save results and shutdown the PC."""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"benchmark_results_{self.current_model.replace(':', '_')}_{timestamp}.txt"
            filepath = os.path.join(os.getcwd(), filename)
            
            # Save results
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write summary
                f.write(self.results_text.get('1.0', tk.END))
                
                # Write all generated code
                f.write("\n\n" + "=" * 70 + "\n")
                f.write("GENERATED CODE FOR EACH TEST\n")
                f.write("=" * 70 + "\n")
                
                for r in self.results:
                    status_icon = "✓ PASSED" if r['status'] == 'success' else "✗ FAILED"
                    f.write(f"\n{'─' * 70}\n")
                    f.write(f"TEST {r.get('prompt_id', '?')} - {status_icon}\n")
                    f.write(f"{'─' * 70}\n")
                    f.write(f"Difficulty: {r.get('difficulty', 'Unknown')}\n")
                    f.write(f"Prompt: {r.get('prompt', 'N/A')}\n")
                    f.write(f"Attempts: {r['attempts']} | Time: {r.get('elapsed', 0):.1f}s\n")
                    if r.get('reason'):
                        f.write(f"Failure Reason: {r['reason']}\n")
                    f.write(f"{'─' * 70}\n")
                    
                    code = r.get('generated_code', '')
                    if code:
                        f.write(f"\n```python\n{code}\n```\n")
                    else:
                        f.write("\n(No code generated)\n")
                
                # Write full logs
                f.write("\n\n" + "=" * 70 + "\n")
                f.write("FULL BENCHMARK LOGS\n")
                f.write("=" * 70 + "\n\n")
                f.write(self.log_text.get('1.0', tk.END))
            
            self.log(f"[System] ✅ Results auto-saved to: {filename}", "success")
            self.log("[System] 🔌 Shutting down PC in 5 seconds...", "warning")
            
            # Give user time to see the message
            self.root.after(5000, self.shutdown_pc)
            
        except Exception as e:
            self.log(f"[System] ✗ Auto-save failed: {str(e)}", "error")
            messagebox.showerror("Auto-save Error", f"Failed to auto-save:\n{str(e)}")
    
    def shutdown_pc(self):
        """Shutdown the PC based on OS."""
        try:
            system = platform.system()
            
            if system == "Windows":
                subprocess.run(["shutdown", "/s", "/t", "0"])
            elif system == "Linux":
                subprocess.run(["shutdown", "-h", "now"])
            elif system == "Darwin":  # macOS
                subprocess.run(["sudo", "shutdown", "-h", "now"])
            else:
                self.log(f"[System] ✗ Unsupported OS for shutdown: {system}", "error")
                messagebox.showwarning("Shutdown Failed", f"Unsupported OS: {system}")
                
        except Exception as e:
            self.log(f"[System] ✗ Shutdown failed: {str(e)}", "error")
            messagebox.showerror("Shutdown Error", f"Failed to shutdown:\n{str(e)}")

    def save_results(self):
        """Save benchmark results to a file with all generated code."""
        if not self.results:
            messagebox.showwarning("No Results", "No results to save!")
            return

        filename = filedialog.asksaveasfilename(
            title="Save Results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        
        if not filename:
            return

        try:
            if filename.endswith('.json'):
                # Save as JSON (includes all generated code)
                json_data = {
                    "timestamp": datetime.now().isoformat(),
                    "model": self.current_model,
                    "total_tests": len(self.results),
                    "passed": sum(1 for r in self.results if r['status'] == 'success'),
                    "failed": sum(1 for r in self.results if r['status'] != 'success'),
                    "results": self.results
                }
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2)
            else:
                # Save as text with all generated code
                with open(filename, 'w', encoding='utf-8') as f:
                    # Write summary
                    f.write(self.results_text.get('1.0', tk.END))
                    
                    # Write all generated code
                    f.write("\n\n" + "=" * 70 + "\n")
                    f.write("GENERATED CODE FOR EACH TEST\n")
                    f.write("=" * 70 + "\n")
                    
                    for r in self.results:
                        status_icon = "✓ PASSED" if r['status'] == 'success' else "✗ FAILED"
                        f.write(f"\n{'─' * 70}\n")
                        f.write(f"TEST {r.get('prompt_id', '?')} - {status_icon}\n")
                        f.write(f"{'─' * 70}\n")
                        f.write(f"Difficulty: {r.get('difficulty', 'Unknown')}\n")
                        f.write(f"Prompt: {r.get('prompt', 'N/A')}\n")
                        f.write(f"Attempts: {r['attempts']} | Time: {r.get('elapsed', 0):.1f}s\n")
                        if r.get('reason'):
                            f.write(f"Failure Reason: {r['reason']}\n")
                        f.write(f"{'─' * 70}\n")
                        
                        code = r.get('generated_code', '')
                        if code:
                            f.write(f"\n```python\n{code}\n```\n")
                        else:
                            f.write("\n(No code generated)\n")
                    
                    # Write full logs
                    f.write("\n\n" + "=" * 70 + "\n")
                    f.write("FULL BENCHMARK LOGS\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(self.log_text.get('1.0', tk.END))
            
            messagebox.showinfo("Saved", f"Results saved to {filename}")
            self.log(f"[System] 💾 Results saved to {filename}", "success")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results:\n{str(e)}")
            self.log(f"[System] ✗ Error saving results: {str(e)}", "error")


def main():
    """Main entry point."""
    os.makedirs("outputs", exist_ok=True)
    
    root = tk.Tk()
    app = BenchmarkGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
