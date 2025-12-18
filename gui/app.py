"""Improved Tkinter GUI for Code Generation Crew with Green/Black Theme."""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, Menu
import threading
import queue
import os
import json
import subprocess
import re
from datetime import datetime

try:
    from pygments import lex
    from pygments.lexers import PythonLexer
    from pygments.token import Token
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

from utils.state import create_initial_state
from agents.refiner import refine_prompt
from agents.coder import generate_code, save_code
from agents.reviewer import review_code
from agents.tester import run_tests
from utils.flake8_checker import run_flake8


# Available models
AVAILABLE_MODELS = [
    ("codellama:7b-instruct-q4_0", "CodeLlama 7B (Fast)"),
    ("deepseek-coder:6.7b", "DeepSeek Coder 6.7B (Balanced)"),
    ("qwen2.5-coder:32b", "Qwen 2.5 Coder 32B (Best Quality)"),
]

DEFAULT_MODEL = "deepseek-coder:6.7b"

# Matrix/Crypto Dark Theme - Neon green on very dark background
COLORS = {
    "bg": "#0a0f0d",                    # Very dark green-black
    "bg_light": "#0f1612",              # Dark panel background
    "bg_lighter": "#1a2520",            # Lighter panel (hover)
    "fg": "#c8e6c9",                    # Light green-tinted text
    "fg_dim": "#4a6b5a",                # Dimmed green-gray
    "accent": "#00ff88",                # Neon green accent
    "accent_hover": "#00cc6a",          # Darker green hover
    "success": "#00ff88",               # Success green
    "error": "#ff4444",                 # Red for errors
    "warning": "#ffaa00",               # Orange warning
    "border": "#1a3d2e",                # Dark green border
    "input_bg": "#0d1510",              # Very dark input
    "selection": "#1a4d3a",             # Dark green selection
    "refiner": "#00ff88",               # Bright neon green
    "coder": "#00e67a",                 # Slightly darker
    "reviewer": "#00cc6a",              # Medium green
    "tester": "#00b35c",                # Forest green
    "flake8": "#009955",                # Dark green
    "system": "#556b5f",                # Gray-green
}

# Syntax highlighting colors (if Pygments available)
SYNTAX_COLORS = {
    Token.Keyword: "#00ff88",           # Neon green keywords
    Token.Keyword.Namespace: "#00e67a",
    Token.Name.Builtin: "#00cc6a",
    Token.Name.Function: "#00ffaa",     # Bright green functions
    Token.Name.Class: "#00ff88",
    Token.String: "#8bc34a",            # Light lime green
    Token.String.Doc: "#6a9d4f",
    Token.Number: "#00ffaa",
    Token.Comment: "#4a6b5a",           # Dim green
    Token.Operator: "#c8e6c9",
    Token.Name: "#c8e6c9",
}


class LineNumberText(tk.Text):
    """Text widget with line numbers."""
    
    def __init__(self, parent, *args, **kwargs):
        tk.Text.__init__(self, parent, *args, **kwargs)
        
        self.linenumbers = tk.Text(parent, width=4, padx=4, takefocus=0,
                                   border=0, background=COLORS["bg_light"],
                                   foreground=COLORS["fg_dim"],
                                   state='disabled', font=self['font'])
        
        self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Bind events
        self.bind('<KeyRelease>', self._on_change)
        self.bind('<MouseWheel>', self._on_change)
        self.bind('<Button-4>', self._on_change)  # Linux scroll up
        self.bind('<Button-5>', self._on_change)  # Linux scroll down
    
    def _on_change(self, event=None):
        """Update line numbers."""
        self.linenumbers.config(state='normal')
        self.linenumbers.delete('1.0', 'end')
        
        # Get the number of lines
        line_count = self.get('1.0', 'end-1c').count('\n') + 1
        line_numbers = '\n'.join(str(i) for i in range(1, line_count + 1))
        
        self.linenumbers.insert('1.0', line_numbers)
        self.linenumbers.config(state='disabled')


class CodeDisplayText(tk.Frame):
    """Code display with line numbers and syntax highlighting."""
    
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, bg=COLORS["bg"])
        
        # Line numbers
        self.linenumbers = tk.Text(self, width=5, padx=5, takefocus=0,
                                   border=0, background=COLORS["bg_light"],
                                   foreground=COLORS["fg_dim"],
                                   state='disabled', font=('Consolas', 10))
        self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main text widget
        self.text = tk.Text(self, font=('Consolas', 10),
                           bg=COLORS["input_bg"], fg=COLORS["fg"],
                           insertbackground=COLORS["accent"],
                           selectbackground=COLORS["selection"],
                           relief='flat', **kwargs)
        
        # Scrollbar
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self._on_scroll)
        self.text.configure(yscrollcommand=self._on_text_scroll)
        
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure syntax highlighting tags
        if PYGMENTS_AVAILABLE:
            for token_type, color in SYNTAX_COLORS.items():
                self.text.tag_configure(str(token_type), foreground=color)
        
        # Bind events for line number updates
        self.text.bind('<<Change>>', self._on_change)
        self.text.bind('<KeyRelease>', self._on_change)
    
    def _on_scroll(self, *args):
        """Handle scrollbar movement."""
        self.text.yview(*args)
        self.linenumbers.yview(*args)
    
    def _on_text_scroll(self, *args):
        """Handle text widget scrolling."""
        self.scrollbar.set(*args)
        self.linenumbers.yview_moveto(float(args[0]))
    
    def _on_change(self, event=None):
        """Update line numbers when text changes."""
        self.update_line_numbers()
    
    def update_line_numbers(self):
        """Update the line numbers display."""
        self.linenumbers.config(state='normal')
        self.linenumbers.delete('1.0', 'end')
        
        line_count = int(self.text.index('end-1c').split('.')[0])
        line_numbers = '\n'.join(str(i) for i in range(1, line_count + 1))
        
        self.linenumbers.insert('1.0', line_numbers)
        self.linenumbers.config(state='disabled')
        
        # Sync scroll positions
        self.linenumbers.yview_moveto(self.text.yview()[0])
    
    def insert(self, index, text, *args):
        """Override insert to trigger line number update."""
        self.text.insert(index, text, *args)
        self.update_line_numbers()
        self._apply_syntax_highlighting()
    
    def delete(self, start, end=None):
        """Override delete to trigger line number update."""
        self.text.delete(start, end)
        self.update_line_numbers()
    
    def get(self, start, end=None):
        """Get text content."""
        return self.text.get(start, end)
    
    def configure(self, **kwargs):
        """Configure the text widget."""
        self.text.configure(**kwargs)
    
    def config(self, **kwargs):
        """Alias for configure."""
        self.configure(**kwargs)
    
    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting using simple dictionary-based word matching."""
        # Get all text
        code = self.text.get('1.0', 'end-1c')
        
        # Remove existing highlight tags
        for tag in ['keyword', 'builtin', 'string', 'comment', 'number', 'decorator', 'function_def']:
            self.text.tag_remove(tag, '1.0', 'end')
        
        # Configure tags if not already done
        self.text.tag_configure('keyword', foreground='#00ff88')      # Neon green
        self.text.tag_configure('builtin', foreground='#00cc6a')      # Medium green
        self.text.tag_configure('string', foreground='#8bc34a')       # Lime green
        self.text.tag_configure('comment', foreground='#4a6b5a')      # Dim green
        self.text.tag_configure('number', foreground='#00ffaa')       # Bright green
        self.text.tag_configure('decorator', foreground='#00e67a')    # Light green
        self.text.tag_configure('function_def', foreground='#00ffaa') # Bright green
        
        # Python keywords (exact match only)
        KEYWORDS = {
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
            'while', 'with', 'yield'
        }
        
        # Python builtins (exact match only)
        BUILTINS = {
            'print', 'input', 'len', 'range', 'str', 'int', 'float', 'list',
            'dict', 'set', 'tuple', 'bool', 'type', 'open', 'file', 'abs',
            'all', 'any', 'bin', 'chr', 'ord', 'dir', 'divmod', 'enumerate',
            'eval', 'exec', 'filter', 'format', 'getattr', 'setattr', 'hasattr',
            'hash', 'help', 'hex', 'id', 'isinstance', 'issubclass', 'iter',
            'map', 'max', 'min', 'next', 'oct', 'pow', 'repr', 'reversed',
            'round', 'slice', 'sorted', 'sum', 'super', 'vars', 'zip',
            'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
            'AttributeError', 'NameError', 'RuntimeError', 'StopIteration',
            'FileNotFoundError', 'IOError', 'OSError', 'ZeroDivisionError',
            '__name__', '__main__', '__init__', '__str__', '__repr__',
            'self', 'cls'
        }
        
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines
            if not line.strip():
                continue
            
            # Highlight comments (entire line after #)
            if '#' in line:
                comment_start = line.index('#')
                start_idx = f'{line_num}.{comment_start}'
                end_idx = f'{line_num}.end'
                self.text.tag_add('comment', start_idx, end_idx)
            
            # Highlight strings (simple approach - single and double quotes)
            in_string = False
            string_char = None
            string_start = 0
            i = 0
            while i < len(line):
                char = line[i]
                
                # Skip if in comment
                if not in_string and char == '#':
                    break
                
                # Check for string start/end
                if char in '"\'':
                    # Check for triple quotes
                    if i + 2 < len(line) and line[i:i+3] in ['"""', "'''"]:
                        if not in_string:
                            in_string = True
                            string_char = line[i:i+3]
                            string_start = i
                            i += 3
                            continue
                        elif string_char == line[i:i+3]:
                            end_idx = i + 3
                            self.text.tag_add('string', f'{line_num}.{string_start}', f'{line_num}.{end_idx}')
                            in_string = False
                            string_char = None
                            i += 3
                            continue
                    # Single quotes
                    elif not in_string:
                        in_string = True
                        string_char = char
                        string_start = i
                    elif string_char == char and (i == 0 or line[i-1] != '\\'):
                        end_idx = i + 1
                        self.text.tag_add('string', f'{line_num}.{string_start}', f'{line_num}.{end_idx}')
                        in_string = False
                        string_char = None
                i += 1
            
            # Highlight decorators
            stripped = line.lstrip()
            if stripped.startswith('@'):
                indent = len(line) - len(stripped)
                # Find end of decorator name
                end = indent + 1
                while end < len(line) and (line[end].isalnum() or line[end] == '_'):
                    end += 1
                self.text.tag_add('decorator', f'{line_num}.{indent}', f'{line_num}.{end}')
            
            # Highlight keywords and builtins (whole words only)
            # Use regex to find word boundaries
            import re
            for match in re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', line):
                word = match.group(1)
                start_col = match.start()
                end_col = match.end()
                
                # Check if inside string or comment (skip)
                if '#' in line and start_col > line.index('#'):
                    continue
                
                if word in KEYWORDS:
                    self.text.tag_add('keyword', f'{line_num}.{start_col}', f'{line_num}.{end_col}')
                elif word in BUILTINS:
                    self.text.tag_add('builtin', f'{line_num}.{start_col}', f'{line_num}.{end_col}')
            
            # Highlight numbers
            for match in re.finditer(r'\b(\d+\.?\d*)\b', line):
                start_col = match.start()
                end_col = match.end()
                # Check if not inside string or comment
                if '#' in line and start_col > line.index('#'):
                    continue
                self.text.tag_add('number', f'{line_num}.{start_col}', f'{line_num}.{end_col}')


class CollapsibleFrame(tk.Frame):
    """A collapsible frame widget."""
    
    def __init__(self, parent, text="", **kwargs):
        tk.Frame.__init__(self, parent, bg=COLORS["bg"], **kwargs)
        
        self.show = tk.BooleanVar(value=True)
        
        # Title frame with toggle button
        self.title_frame = tk.Frame(self, bg=COLORS["bg_light"], height=30)
        self.title_frame.pack(fill=tk.X, pady=(0, 2))
        self.title_frame.pack_propagate(False)
        
        # Toggle button
        self.toggle_btn = tk.Label(self.title_frame, text="▼", 
                                   bg=COLORS["bg_light"], fg=COLORS["accent"],
                                   font=('Consolas', 10, 'bold'), cursor="hand2")
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        self.toggle_btn.bind('<Button-1>', self.toggle)
        
        # Title label
        self.title_label = tk.Label(self.title_frame, text=text,
                                    bg=COLORS["bg_light"], fg=COLORS["fg"],
                                    font=('Segoe UI', 10, 'bold'))
        self.title_label.pack(side=tk.LEFT, padx=5)
        self.title_label.bind('<Button-1>', self.toggle)
        
        # Content frame
        self.content_frame = tk.Frame(self, bg=COLORS["bg"])
        self.content_frame.pack(fill=tk.BOTH, expand=True)
    
    def toggle(self, event=None):
        """Toggle the visibility of the content."""
        if self.show.get():
            self.content_frame.pack_forget()
            self.toggle_btn.configure(text="▶")
            self.show.set(False)
        else:
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            self.toggle_btn.configure(text="▼")
            self.show.set(True)


class CodeGenerationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Generation Crew")
        self.root.geometry("1500x950")
        self.root.configure(bg=COLORS["bg"])
        
        # State
        self.state = None
        self.message_queue = queue.Queue()
        self.is_running = False
        self.stop_requested = False
        self.start_time = None
        self.current_model = DEFAULT_MODEL
        
        # Store all code versions
        self.code_versions = []
        self.full_logs = []
        self.error_logs = []
        
        # Reference to vertical_paned for size control
        self.vertical_paned = None
        
        # Create UI
        self.setup_dark_style()
        self.create_menu()
        self.create_widgets()
        
        # Start queue checker
        self.check_queue()
    
    def setup_dark_style(self):
        """Configure dark green/black theme."""
        style = ttk.Style()
        
        # Use a base theme
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')
        
        # Configure colors
        style.configure('.', 
                       background=COLORS["bg"], 
                       foreground=COLORS["fg"],
                       fieldbackground=COLORS["input_bg"],
                       bordercolor=COLORS["border"],
                       darkcolor=COLORS["bg"],
                       lightcolor=COLORS["bg_lighter"])
        
        # Frame
        style.configure('TFrame', background=COLORS["bg"])
        style.configure('Card.TFrame', background=COLORS["bg_light"], 
                       relief='flat', borderwidth=0)
        
        # Labels
        style.configure('TLabel', 
                       background=COLORS["bg"], 
                       foreground=COLORS["fg"],
                       font=('Segoe UI', 9))
        style.configure('Title.TLabel', 
                       background=COLORS["bg_lighter"],
                       foreground=COLORS["accent"], 
                       font=('Segoe UI', 11, 'bold'))
        style.configure('Bold.TLabel', font=('Segoe UI', 9, 'bold'))
        style.configure('Status.TLabel', 
                       background=COLORS["bg_light"],
                       foreground=COLORS["fg"])
        
        # Buttons
        style.configure('TButton',
                       background=COLORS["bg_lighter"],
                       foreground=COLORS["fg"],
                       bordercolor=COLORS["border"],
                       focuscolor=COLORS["accent"],
                       font=('Segoe UI', 9),
                       padding=(10, 5))
        style.map('TButton',
                 background=[('active', COLORS["bg_lighter"]), 
                           ('pressed', COLORS["bg"])],
                 foreground=[('active', COLORS["fg"])])
        
        # Accent button
        style.configure('Accent.TButton',
                       background=COLORS["accent"],
                       foreground=COLORS["bg"],
                       font=('Segoe UI', 9, 'bold'))
        style.map('Accent.TButton',
                 background=[('active', COLORS["accent_hover"]), 
                           ('pressed', COLORS["accent"])])
        
        # LabelFrame
        style.configure('TLabelframe',
                       background=COLORS["bg"],
                       foreground=COLORS["accent"],
                       bordercolor=COLORS["border"],
                       relief='flat')
        style.configure('TLabelframe.Label',
                       background=COLORS["bg"],
                       foreground=COLORS["accent"],
                       font=('Segoe UI', 9, 'bold'))
        
        # Notebook (tabs)
        style.configure('TNotebook',
                       background=COLORS["bg"],
                       bordercolor=COLORS["border"],
                       tabmargins=[2, 5, 2, 0])
        style.configure('TNotebook.Tab',
                       background=COLORS["bg_light"],
                       foreground=COLORS["fg"],
                       padding=[10, 5],
                       font=('Segoe UI', 9))
        style.map('TNotebook.Tab',
                 background=[('selected', COLORS["bg_lighter"])],
                 foreground=[('selected', COLORS["accent"])])
        
        # Combobox
        style.configure('TCombobox',
                       fieldbackground=COLORS["input_bg"],
                       background=COLORS["bg_lighter"],
                       foreground=COLORS["fg"],
                       arrowcolor=COLORS["fg"],
                       bordercolor=COLORS["border"],
                       font=('Segoe UI', 9))
        
        # Progressbar
        style.configure('TProgressbar',
                       background=COLORS["accent"],
                       troughcolor=COLORS["bg_light"],
                       bordercolor=COLORS["border"],
                       lightcolor=COLORS["accent"],
                       darkcolor=COLORS["accent"])
        
        # PanedWindow
        style.configure('TPanedwindow', background=COLORS["bg"])
        style.configure('Sash',
                       sashthickness=8,
                       background=COLORS["border"],
                       sashrelief='raised')
    
    def create_menu(self):
        """Create menu bar."""
        menubar = Menu(self.root,
                      bg=COLORS["bg_light"],
                      fg=COLORS["fg"],
                      activebackground=COLORS["accent"],
                      activeforeground=COLORS["bg"],
                      font=('Segoe UI', 9),
                      relief='flat',
                      borderwidth=0)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0,
                        bg=COLORS["bg_light"],
                        fg=COLORS["fg"],
                        activebackground=COLORS["accent"],
                        activeforeground=COLORS["bg"],
                        font=('Segoe UI', 9))
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Session...", command=self.save_session)
        file_menu.add_command(label="Load Session...", command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label="Open in VS Code", command=self.open_in_vscode)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = Menu(menubar, tearoff=0,
                        bg=COLORS["bg_light"],
                        fg=COLORS["fg"],
                        activebackground=COLORS["accent"],
                        activeforeground=COLORS["bg"],
                        font=('Segoe UI', 9))
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Compare Code Versions", 
                             command=self.show_version_comparison)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0,
                        bg=COLORS["bg_light"],
                        fg=COLORS["fg"],
                        activebackground=COLORS["accent"],
                        activeforeground=COLORS["bg"],
                        font=('Segoe UI', 9))
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_widgets(self):
        """Create all widgets with dark styling."""
        # Main container
        main_frame = tk.Frame(self.root, bg=COLORS["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Compact title bar
        title_frame = tk.Frame(main_frame, bg=COLORS["bg_lighter"], height=28)
        title_frame.pack(fill=tk.X, pady=(0, 8))
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="Code Generation Crew",
                bg=COLORS["bg_lighter"], fg=COLORS["accent"],
                font=('Segoe UI', 11, 'bold')).pack(side=tk.LEFT, padx=8)
        
        # Status indicators in title bar
        status_right = tk.Frame(title_frame, bg=COLORS["bg_lighter"])
        status_right.pack(side=tk.RIGHT, padx=8)
        
        self.time_label = tk.Label(status_right, text="Ready",
                                   bg=COLORS["bg_lighter"], fg=COLORS["fg_dim"],
                                   font=('Segoe UI', 9))
        self.time_label.pack(side=tk.RIGHT, padx=8)
        
        self.attempt_label = tk.Label(status_right, text="Attempt: 0/10",
                                      bg=COLORS["bg_lighter"], fg=COLORS["fg_dim"],
                                      font=('Segoe UI', 9))
        self.attempt_label.pack(side=tk.RIGHT, padx=8)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(status_right, length=150, 
                                           mode='determinate', maximum=10)
        self.progress_bar.pack(side=tk.RIGHT, padx=8)
        
        # Model selector (more compact)
        model_frame = tk.Frame(main_frame, bg=COLORS["bg"])
        model_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(model_frame, text="Model:", bg=COLORS["bg"], fg=COLORS["fg"],
                font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.model_var,
                                        state='readonly', width=35)
        self.model_combo['values'] = [f"{m[1]}" for m in AVAILABLE_MODELS]
        for i, model in enumerate(AVAILABLE_MODELS):
            if model[0] == DEFAULT_MODEL:
                self.model_combo.current(i)
                break
        self.model_combo.pack(side=tk.LEFT, padx=5)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_select)
        
        self.model_status = tk.Label(model_frame, text="Ready",
                                    bg=COLORS["bg"], fg=COLORS["success"],
                                    font=('Segoe UI', 9))
        self.model_status.pack(side=tk.LEFT, padx=8)
        
        # Main content with PanedWindow for resizing
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left pane - Input & Code
        left_pane = tk.Frame(paned_window, bg=COLORS["bg"])
        paned_window.add(left_pane, weight=3)
        
        # Buttons (above the resizable sections)
        btn_frame = tk.Frame(left_pane, bg=COLORS["bg_light"])
        btn_frame.pack(fill=tk.X, pady=(0, 6), padx=0)
        
        btn_inner = tk.Frame(btn_frame, bg=COLORS["bg_light"])
        btn_inner.pack(fill=tk.X, padx=8, pady=6)
        
        self.start_btn = ttk.Button(btn_inner, text="Start",
                                    command=self.start_refinement,
                                    style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        self.use_original_btn = ttk.Button(btn_inner, text="Use Original",
                                          command=self.use_original_prompt,
                                          state=tk.DISABLED)
        self.use_original_btn.pack(side=tk.LEFT, padx=2)
        
        self.use_refined_btn = ttk.Button(btn_inner, text="Use Refined",
                                         command=self.use_refined_prompt,
                                         state=tk.DISABLED)
        self.use_refined_btn.pack(side=tk.LEFT, padx=2)
        
        self.retry_btn = ttk.Button(btn_inner, text="Refine Again",
                                    command=self.refine_again,
                                    state=tk.DISABLED)
        self.retry_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(btn_inner, text="Stop",
                                   command=self.stop_workflow,
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.clear_btn = ttk.Button(btn_inner, text="Clear",
                                    command=self.clear_all_with_confirm)
        self.clear_btn.pack(side=tk.LEFT, padx=2)
        
        # Vertical PanedWindow for ALL resizable sections (prompt, refined, code)
        vertical_paned = ttk.PanedWindow(left_pane, orient=tk.VERTICAL)
        vertical_paned.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        
        # Store reference for size control
        self.vertical_paned = vertical_paned
        
        # Prompt input section (resizable)
        input_frame = tk.Frame(vertical_paned, bg=COLORS["bg_light"])
        vertical_paned.add(input_frame, weight=1)
        
        tk.Label(input_frame, text="Prompt Input", bg=COLORS["bg_light"],
                fg=COLORS["accent"], font=('Segoe UI', 9, 'bold')).pack(
                anchor=tk.W, padx=8, pady=(6, 4))
        
        prompt_container = tk.Frame(input_frame, bg=COLORS["bg_light"])
        prompt_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        
        self.prompt_input = scrolledtext.ScrolledText(prompt_container,
                                    font=('Consolas', 10),
                                    bg=COLORS["input_bg"],
                                    fg=COLORS["fg"],
                                    insertbackground=COLORS["accent"],
                                    selectbackground=COLORS["selection"],
                                    relief='flat', bd=0, wrap=tk.WORD)
        self.prompt_input.pack(fill=tk.BOTH, expand=True)
        
        # Refined prompt section (resizable)
        refined_frame = tk.Frame(vertical_paned, bg=COLORS["bg_light"])
        vertical_paned.add(refined_frame, weight=1)
        
        tk.Label(refined_frame, text="Refined Prompt", bg=COLORS["bg_light"],
                fg=COLORS["accent"], font=('Segoe UI', 9, 'bold')).pack(
                anchor=tk.W, padx=8, pady=(6, 4))
        
        refined_container = tk.Frame(refined_frame, bg=COLORS["bg"])
        refined_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        
        self.refined_display = scrolledtext.ScrolledText(refined_container,
                                       height=6,
                                       font=('Consolas', 9),
                                       bg=COLORS["input_bg"],
                                       fg=COLORS["accent"],
                                       insertbackground=COLORS["accent"],
                                       selectbackground=COLORS["selection"],
                                       relief='flat', bd=0,
                                       state=tk.DISABLED, wrap=tk.WORD)
        self.refined_display.pack(fill=tk.BOTH, expand=True)
        
        # Code display with line numbers (resizable)
        code_frame = tk.Frame(vertical_paned, bg=COLORS["bg_light"])
        vertical_paned.add(code_frame, weight=3)
        
        code_header = tk.Frame(code_frame, bg=COLORS["bg_light"])
        code_header.pack(fill=tk.X, padx=8, pady=(6, 4))
        
        tk.Label(code_header, text="Generated Code", bg=COLORS["bg_light"],
                fg=COLORS["accent"], font=('Segoe UI', 9, 'bold')).pack(
                side=tk.LEFT)
        
        tk.Label(code_header, text="Version:", bg=COLORS["bg_light"],
                fg=COLORS["fg"], font=('Segoe UI', 9)).pack(
                side=tk.LEFT, padx=(16, 4))
        
        self.version_var = tk.StringVar(value="Latest")
        self.version_combo = ttk.Combobox(code_header, textvariable=self.version_var,
                                          state='readonly', width=25)
        self.version_combo['values'] = ["Latest"]
        self.version_combo.pack(side=tk.LEFT, padx=2)
        self.version_combo.bind("<<ComboboxSelected>>", self.on_version_select)
        
        self.vscode_btn = ttk.Button(code_header, text="Open in VS Code",
                                     command=self.open_in_vscode)
        self.vscode_btn.pack(side=tk.RIGHT)
        
        # Code display with line numbers and syntax highlighting
        code_container = tk.Frame(code_frame, bg=COLORS["bg"])
        code_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        
        self.code_display = CodeDisplayText(code_container, state=tk.DISABLED)
        self.code_display.pack(fill=tk.BOTH, expand=True)
        
        # FIX 2: Set initial pane sizes after window is drawn
        def set_initial_pane_sizes():
            """Set initial pane sizes: equal for prompt/refined, larger for code."""
            try:
                total_height = self.vertical_paned.winfo_height()
                if total_height > 100:  # Only if window is properly sized
                    # 20% for prompt, 20% for refined (equal), 60% for code
                    self.vertical_paned.sashpos(0, int(total_height * 0.20))
                    self.vertical_paned.sashpos(1, int(total_height * 0.40))
            except Exception:
                pass
        
        # Schedule the size setting after the window is fully drawn
        self.root.after(100, set_initial_pane_sizes)
        
        # Right pane - Status & Logs
        right_pane = tk.Frame(paned_window, bg=COLORS["bg"])
        paned_window.add(right_pane, weight=1)
        
        # Agent status (more compact)
        status_frame = tk.Frame(right_pane, bg=COLORS["bg_light"])
        status_frame.pack(fill=tk.X, pady=(0, 6))
        
        tk.Label(status_frame, text="Agent Status", bg=COLORS["bg_light"],
                fg=COLORS["accent"], font=('Segoe UI', 9, 'bold')).pack(
                anchor=tk.W, padx=8, pady=(6, 4))
        
        status_grid = tk.Frame(status_frame, bg=COLORS["bg_light"])
        status_grid.pack(fill=tk.X, padx=8, pady=(0, 6))
        
        self.status_labels = {}
        self.agent_activity = {}
        agents = [
            ("refiner", "Refiner", COLORS["refiner"]),
            ("coder", "Coder", COLORS["coder"]),
            ("reviewer", "Reviewer", COLORS["reviewer"]),
            ("tester", "Tester", COLORS["tester"]),
            ("flake8", "Flake8", COLORS["flake8"])
        ]
        
        for agent_id, agent_name, color in agents:
            frame = tk.Frame(status_grid, bg=COLORS["bg_light"])
            frame.pack(fill=tk.X, pady=2)
            
            # Status indicator (colored circle)
            status = tk.Label(frame, text="●", font=('Segoe UI', 12),
                            bg=COLORS["bg_light"], fg=COLORS["fg_dim"], width=2)
            status.pack(side=tk.LEFT)
            
            # Agent name
            tk.Label(frame, text=agent_name, bg=COLORS["bg_light"],
                    fg=color, font=('Segoe UI', 9, 'bold'),
                    width=10, anchor=tk.W).pack(side=tk.LEFT)
            
            # Activity
            activity = tk.Label(frame, text="", bg=COLORS["bg_light"],
                              fg=COLORS["fg_dim"], font=('Segoe UI', 8),
                              anchor=tk.W)
            activity.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.status_labels[agent_id] = status
            self.agent_activity[agent_id] = activity
        
        # Tabbed logs - REMOVED Full Log tab (redundant with Communication)
        log_notebook = ttk.Notebook(right_pane)
        log_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Communication/Activity tab
        comm_frame = tk.Frame(log_notebook, bg=COLORS["bg"])
        log_notebook.add(comm_frame, text="Activity Log")
        
        self.comm_log = tk.Text(comm_frame, font=('Consolas', 8),
                                bg=COLORS["input_bg"], fg=COLORS["fg"],
                                insertbackground=COLORS["accent"],
                                selectbackground=COLORS["selection"],
                                relief='flat', bd=0, state=tk.DISABLED)
        comm_scroll = tk.Scrollbar(comm_frame, orient=tk.VERTICAL,
                                   command=self.comm_log.yview)
        self.comm_log.configure(yscrollcommand=comm_scroll.set)
        self.comm_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        comm_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
        
        # Configure log tags with green theme
        self.comm_log.tag_configure("refiner", foreground=COLORS["refiner"])
        self.comm_log.tag_configure("coder", foreground=COLORS["coder"])
        self.comm_log.tag_configure("reviewer", foreground=COLORS["reviewer"])
        self.comm_log.tag_configure("tester", foreground=COLORS["tester"])
        self.comm_log.tag_configure("flake8", foreground=COLORS["flake8"])
        self.comm_log.tag_configure("system", foreground=COLORS["system"])
        self.comm_log.tag_configure("success", foreground=COLORS["success"])
        self.comm_log.tag_configure("error", foreground=COLORS["error"])
        
        # Errors tab
        error_frame = tk.Frame(log_notebook, bg=COLORS["bg"])
        log_notebook.add(error_frame, text="Errors")
        
        self.error_log = tk.Text(error_frame, font=('Consolas', 8),
                                bg=COLORS["input_bg"], fg=COLORS["error"],
                                insertbackground=COLORS["accent"],
                                selectbackground=COLORS["selection"],
                                relief='flat', bd=0, state=tk.DISABLED)
        error_scroll = tk.Scrollbar(error_frame, orient=tk.VERTICAL,
                                    command=self.error_log.yview)
        self.error_log.configure(yscrollcommand=error_scroll.set)
        self.error_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        error_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
    
    def on_model_select(self, event):
        """Handle model selection."""
        selected_display = self.model_combo.get()
        for model_id, model_display in AVAILABLE_MODELS:
            if model_display == selected_display:
                self.current_model = model_id
                self.model_status.configure(text=f"✓ {model_id}")
                self.log_comm(f"[System] Model changed to: {model_id}", "system")
                break
    
    def open_in_vscode(self):
        """Open generated code in VS Code."""
        code = self.code_display.get("1.0", tk.END).strip()
        
        if not code:
            messagebox.showwarning("No Code", "Generate code first!")
            return
        
        output_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"generated_code_{timestamp}.py")
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)
            
            for cmd in ["code", "/usr/bin/code", "/snap/bin/code"]:
                try:
                    subprocess.Popen([cmd, filename])
                    self.log_comm(f"[System] Opened in VS Code: {filename}", "success")
                    return
                except FileNotFoundError:
                    continue
            
            messagebox.showerror("VS Code Not Found",
                               f"VS Code not found!\n\nFile saved to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open: {str(e)}")
            self.log_error(f"VS Code error: {str(e)}")
    
    def stop_workflow(self):
        """Stop the current workflow."""
        if self.is_running:
            self.stop_requested = True
            self.log_comm("[System] Stop requested, waiting for current operation...", "system")
            self.stop_btn.configure(state=tk.DISABLED)
    
    def clear_all_with_confirm(self):
        """Clear all with confirmation."""
        if messagebox.askyesno("Clear All?", "Clear all data and reset?"):
            self.clear_all()
    
    def clear_all(self):
        """Reset everything."""
        self.prompt_input.delete("1.0", tk.END)
        
        self.comm_log.configure(state=tk.NORMAL)
        self.comm_log.delete("1.0", tk.END)
        self.comm_log.configure(state=tk.DISABLED)
        
        self.error_log.configure(state=tk.NORMAL)
        self.error_log.delete("1.0", tk.END)
        self.error_log.configure(state=tk.DISABLED)
        
        self.refined_display.configure(state=tk.NORMAL)
        self.refined_display.delete("1.0", tk.END)
        self.refined_display.configure(state=tk.DISABLED)
        
        self.code_display.configure(state=tk.NORMAL)
        self.code_display.delete("1.0", tk.END)
        self.code_display.configure(state=tk.DISABLED)
        
        self.state = None
        self.start_time = None
        self.code_versions = []
        self.full_logs = []
        self.error_logs = []
        self.stop_requested = False
        self.is_running = False
        
        self.progress_bar['value'] = 0
        
        for agent in self.status_labels:
            self.update_status(agent, "waiting")
            self.update_activity(agent, "")
        
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.use_original_btn.configure(state=tk.DISABLED)
        self.use_refined_btn.configure(state=tk.DISABLED)
        self.retry_btn.configure(state=tk.DISABLED)
        
        self.attempt_label.configure(text="Attempt: 0/10")
        self.time_label.configure(text="Ready")
    
    def save_session(self):
        """Save session to JSON."""
        if not self.state and not self.code_versions:
            messagebox.showwarning("Nothing to Save", "No data to save!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if filename:
            self.refined_display.configure(state=tk.NORMAL)
            refined_text = self.refined_display.get("1.0", tk.END).strip()
            self.refined_display.configure(state=tk.DISABLED)
            
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "model": self.current_model,
                "raw_prompt": self.prompt_input.get("1.0", tk.END).strip(),
                "refined_prompt": refined_text,
                "code_versions": self.code_versions,
                "logs": self.full_logs,
                "errors": self.error_logs
            }
            
            try:
                with open(filename, "w") as f:
                    json.dump(session_data, f, indent=2)
                messagebox.showinfo("Saved", f"Session saved to:\n{filename}")
                self.log_comm(f"[System] Session saved: {filename}", "success")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {str(e)}")
                self.log_error(f"Save error: {str(e)}")
    
    def load_session(self):
        """Load session from JSON."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        
        if filename:
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                
                self.clear_all()
                self.prompt_input.insert("1.0", data.get("raw_prompt", ""))
                
                self.refined_display.configure(state=tk.NORMAL)
                self.refined_display.insert("1.0", data.get("refined_prompt", ""))
                self.refined_display.configure(state=tk.DISABLED)
                
                self.code_versions = data.get("code_versions", [])
                if self.code_versions:
                    latest = self.code_versions[-1]
                    self.code_display.configure(state=tk.NORMAL)
                    self.code_display.insert("1.0", latest.get("code", ""))
                    self.code_display.configure(state=tk.DISABLED)
                    self.update_version_combo()
                
                # Load logs
                for log_entry in data.get("logs", []):
                    msg = log_entry.get("message", "")
                    tag = log_entry.get("tag")
                    self.comm_log.configure(state=tk.NORMAL)
                    self.comm_log.insert(tk.END, f"{msg}\n", tag)
                    self.comm_log.configure(state=tk.DISABLED)
                
                messagebox.showinfo("Loaded", f"Session loaded from:\n{filename}")
                self.log_comm(f"[System] Session loaded: {filename}", "success")
            except Exception as e:
                messagebox.showerror("Error", f"Load failed: {str(e)}")
                self.log_error(f"Load error: {str(e)}")
    
    def show_version_comparison(self):
        """Show code version comparison."""
        if not self.code_versions:
            messagebox.showinfo("No Versions", "No code versions available yet!")
            return
        
        win = tk.Toplevel(self.root)
        win.title("Code Version Comparison")
        win.geometry("1000x700")
        win.configure(bg=COLORS["bg"])
        
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for v in self.code_versions:
            frame = tk.Frame(notebook, bg=COLORS["bg"])
            notebook.add(frame, text=f"Attempt {v['attempt']}")
            
            # Info header
            info_frame = tk.Frame(frame, bg=COLORS["bg_light"])
            info_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(info_frame, text=f"Attempt {v['attempt']}",
                    bg=COLORS["bg_light"], fg=COLORS["accent"],
                    font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=8)
            
            if v.get('timestamp'):
                tk.Label(info_frame, text=v['timestamp'],
                        bg=COLORS["bg_light"], fg=COLORS["fg_dim"],
                        font=('Segoe UI', 9)).pack(side=tk.RIGHT, padx=8)
            
            # Code display
            code_display = CodeDisplayText(frame, state=tk.NORMAL)
            code_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            code_display.insert("1.0", v['code'])
            code_display.configure(state=tk.DISABLED)
    
    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About Code Generation Crew",
            "Code Generation Crew v2.0\n\n"
            "Multi-agent intelligent code generation system\n\n"
            "Created by:\n"
            "• Mehdi Amine DJERBOUA\n"
            "• Ali TALEB\n"
            "• Sahil SARTAJ\n\n"
            "Features:\n"
            "• Prompt refinement\n"
            "• Iterative code generation\n"
            "• Automated testing\n"
            "• Code review\n"
            "• Syntax highlighting"
        )
    
    def update_version_combo(self):
        """Update version selector combo box."""
        if self.code_versions:
            values = ["Latest"] + [f"Attempt {v['attempt']}" 
                                  for v in self.code_versions]
            self.version_combo['values'] = values
    
    def on_version_select(self, event):
        """Handle version selection."""
        selection = self.version_var.get()
        
        if selection == "Latest" and self.code_versions:
            code = self.code_versions[-1]['code']
        else:
            try:
                attempt_num = int(selection.split()[1])
                code = next((v['code'] for v in self.code_versions 
                           if v['attempt'] == attempt_num), "")
            except:
                code = ""
        
        self.code_display.configure(state=tk.NORMAL)
        self.code_display.delete("1.0", tk.END)
        if code:
            self.code_display.insert("1.0", code)
        self.code_display.configure(state=tk.DISABLED)
    
    def log_comm(self, message, tag=None):
        """Log to activity tab only."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        # Activity log
        self.comm_log.configure(state=tk.NORMAL)
        self.comm_log.insert(tk.END, f"{full_message}\n", tag)
        self.comm_log.see(tk.END)
        self.comm_log.configure(state=tk.DISABLED)
        
        self.full_logs.append({"message": full_message, "tag": tag})
    
    def log_error(self, message):
        """Log to error tab."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        # Error log
        self.error_log.configure(state=tk.NORMAL)
        self.error_log.insert(tk.END, f"{full_message}\n")
        self.error_log.see(tk.END)
        self.error_log.configure(state=tk.DISABLED)
        
        self.error_logs.append(full_message)
        
        # Also log to activity with error tag
        self.comm_log.configure(state=tk.NORMAL)
        self.comm_log.insert(tk.END, f"{full_message}\n", "error")
        self.comm_log.see(tk.END)
        self.comm_log.configure(state=tk.DISABLED)
    
    def update_status(self, agent, status):
        """Update agent status with colored indicators."""
        status_map = {
            "waiting": ("●", COLORS["fg_dim"]),
            "running": ("◉", COLORS["warning"]),
            "success": ("●", COLORS["success"]),
            "failed": ("●", COLORS["error"])
        }
        
        if agent in self.status_labels:
            symbol, color = status_map.get(status, ("●", COLORS["fg_dim"]))
            self.status_labels[agent].configure(text=symbol, foreground=color)
    
    def update_activity(self, agent, activity):
        """Update agent activity text."""
        if agent in self.agent_activity:
            self.agent_activity[agent].configure(text=activity[:20])
    
    def start_refinement(self):
        """Start the refinement process."""
        raw_prompt = self.prompt_input.get("1.0", tk.END).strip()
        
        if not raw_prompt:
            messagebox.showwarning("Warning", "Please enter a prompt first!")
            return
        
        self.state = create_initial_state(raw_prompt)
        self.start_time = datetime.now()
        self.code_versions = []
        self.full_logs = []
        self.error_logs = []
        self.stop_requested = False
        self.is_running = True
        
        self.progress_bar['value'] = 0
        
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.use_original_btn.configure(state=tk.DISABLED)
        self.use_refined_btn.configure(state=tk.DISABLED)
        self.retry_btn.configure(state=tk.DISABLED)
        
        self.log_comm("=" * 60, "system")
        self.log_comm("=== Starting Code Generation Workflow ===", "system")
        self.log_comm(f"Model: {self.current_model}", "system")
        self.log_comm("=" * 60, "system")
        
        thread = threading.Thread(target=self._run_refinement)
        thread.daemon = True
        thread.start()
    
    def _run_refinement(self):
        """Run prompt refinement in background thread."""
        try:
            from agents import refiner
            from langchain_ollama import ChatOllama
            refiner.llm = ChatOllama(model=self.current_model, temperature=0.3)
            
            self.message_queue.put(("agent_start", ("refiner", "Refining...")))
            refined = refine_prompt(self.state)
            self.state["refined_prompt"] = refined
            self.message_queue.put(("refinement_done", refined))
        except Exception as e:
            self.message_queue.put(("error", str(e)))
            self.message_queue.put(("log_error", str(e)))
    
    def use_original_prompt(self):
        """Use the original prompt for code generation."""
        raw_prompt = self.prompt_input.get("1.0", tk.END).strip()
        self.state["problem_description"] = raw_prompt
        self.state["workflow_status"] = "in_progress"
        
        self.log_comm("[System] Using ORIGINAL prompt", "success")
        
        self.use_original_btn.configure(state=tk.DISABLED)
        self.use_refined_btn.configure(state=tk.DISABLED)
        self.retry_btn.configure(state=tk.DISABLED)
        
        thread = threading.Thread(target=self._run_workflow)
        thread.daemon = True
        thread.start()
    
    def use_refined_prompt(self):
        """Use the refined prompt for code generation."""
        self.state["problem_description"] = self.state["refined_prompt"]
        self.state["workflow_status"] = "in_progress"
        
        self.log_comm("[System] Using REFINED prompt", "success")
        
        self.use_original_btn.configure(state=tk.DISABLED)
        self.use_refined_btn.configure(state=tk.DISABLED)
        self.retry_btn.configure(state=tk.DISABLED)
        
        thread = threading.Thread(target=self._run_workflow)
        thread.daemon = True
        thread.start()
    
    def refine_again(self):
        """Re-run refinement."""
        self.log_comm("[System] Re-refining prompt...", "system")
        
        self.use_original_btn.configure(state=tk.DISABLED)
        self.use_refined_btn.configure(state=tk.DISABLED)
        self.retry_btn.configure(state=tk.DISABLED)
        
        thread = threading.Thread(target=self._run_refinement)
        thread.daemon = True
        thread.start()
    
    def _run_workflow(self):
        """Main workflow - code generation, review, and testing."""
        try:
            from agents import coder, reviewer, tester
            from langchain_ollama import ChatOllama
            
            coder.llm = ChatOllama(model=self.current_model, temperature=0.2)
            reviewer.llm = ChatOllama(model=self.current_model, temperature=0.1)
            
            max_attempts = self.state.get("max_attempts", 10)
            
            while self.state["workflow_status"] == "in_progress":
                if self.stop_requested:
                    self.message_queue.put(("workflow_stopped", "User stopped"))
                    break
                
                if self.state["current_attempt"] >= max_attempts:
                    self.message_queue.put(("workflow_failed", 
                                           f"Max attempts ({max_attempts}) reached"))
                    break
                
                self.state["current_attempt"] += 1
                attempt = self.state["current_attempt"]
                
                self.message_queue.put(("attempt_update", attempt))
                self.message_queue.put(("progress_update", attempt))
                
                self.message_queue.put(("log_comm", 
                    (f"\n--- Attempt {attempt}/{max_attempts} ---", "system")))
                
                # Coder agent
                self.message_queue.put(("agent_start", ("coder", "Generating...")))
                code = generate_code(self.state)
                self.state["generated_code"] = code
                save_code(code, self.state["code_file_path"])
                
                # Store version
                version_data = {
                    "attempt": attempt,
                    "code": code,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.message_queue.put(("code_version", version_data))
                self.message_queue.put(("code_generated", code))
                self.message_queue.put(("agent_done", "coder"))
                self.message_queue.put(("log_comm", ("[Coder] Code generated", "coder")))
                
                # Reviewer agent
                self.message_queue.put(("agent_start", ("reviewer", "Reviewing...")))
                review = review_code(self.state)
                
                if review["status"] == "rejected":
                    self.state["feedback_history"].append({
                        "source": "Reviewer",
                        "message": review["feedback"],
                        "attempt": attempt
                    })
                    self.message_queue.put(("agent_failed", ("reviewer", "Rejected")))
                    self.message_queue.put(("log_comm", 
                        (f"[Reviewer] Code rejected: {review['feedback'][:100]}", "reviewer")))
                    self.message_queue.put(("log_error", 
                        f"Attempt {attempt} - Reviewer: {review['feedback']}"))
                    continue
                
                self.message_queue.put(("agent_done", "reviewer"))
                self.message_queue.put(("log_comm", ("[Reviewer] Code approved", "reviewer")))
                
                # Flake8 checker (INFORMATIONAL ONLY - NEVER BLOCKS)
                self.message_queue.put(("agent_start", ("flake8", "Checking...")))
                try:
                    flake8_result = run_flake8(self.state["generated_code"])
                    
                    # Check if there are issues
                    issues = flake8_result.get("issues", [])
                    
                    if issues and len(issues) > 0:
                        # Report issues but don't block
                        issue_count = len(issues)
                        self.message_queue.put(("agent_done", "flake8"))
                        self.message_queue.put(("log_comm",
                            (f"[Flake8] Found {issue_count} style issue(s) (non-blocking)", "flake8")))
                        # Show first 3 issues
                        for issue in issues[:3]:
                            self.message_queue.put(("log_comm",
                                (f"  • {issue}", "flake8")))
                    else:
                        # No issues
                        self.message_queue.put(("agent_done", "flake8"))
                        self.message_queue.put(("log_comm", ("[Flake8] No issues found", "flake8")))
                
                except Exception as e:
                    self.message_queue.put(("log_comm",
                        (f"[Flake8] Error: {str(e)}, skipping", "warning")))
                    self.message_queue.put(("agent_done", "flake8"))
                
                # Tester agent
                self.message_queue.put(("agent_start", ("tester", "Testing...")))
                test_result = run_tests(self.state)
                
                if test_result["status"] == "fail":
                    self.state["feedback_history"].append({
                        "source": "Tester",
                        "message": test_result["results"],
                        "attempt": attempt
                    })
                    self.message_queue.put(("agent_failed", ("tester", "Failed")))
                    self.message_queue.put(("log_comm",
                        (f"[Tester] Tests failed: {test_result['results'][:100]}", "tester")))
                    self.message_queue.put(("log_error",
                        f"Attempt {attempt} - Tester: {test_result['results']}"))
                    continue
                
                self.message_queue.put(("agent_done", "tester"))
                self.message_queue.put(("log_comm", ("[Tester] All tests passed", "tester")))
                
                # Success!
                self.state["workflow_status"] = "success"
                self.message_queue.put(("workflow_success", code))
                break
                
        except Exception as e:
            self.message_queue.put(("error", str(e)))
            self.message_queue.put(("log_error", f"Workflow error: {str(e)}"))
    
    def check_queue(self):
        """Process message queue from background threads."""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "refinement_done":
                    self.refined_display.configure(state=tk.NORMAL)
                    self.refined_display.delete("1.0", tk.END)
                    self.refined_display.insert("1.0", data)
                    self.refined_display.configure(state=tk.DISABLED)
                    
                    self.update_status("refiner", "success")
                    self.update_activity("refiner", "Done")
                    self.log_comm("[Refiner] Refinement complete", "refiner")
                    
                    self.use_original_btn.configure(state=tk.NORMAL)
                    self.use_refined_btn.configure(state=tk.NORMAL)
                    self.retry_btn.configure(state=tk.NORMAL)
                
                elif msg_type == "agent_start":
                    agent, activity = data
                    self.update_status(agent, "running")
                    self.update_activity(agent, activity)
                
                elif msg_type == "agent_done":
                    self.update_status(data, "success")
                    self.update_activity(data, "✓ Done")
                
                elif msg_type == "agent_failed":
                    agent, msg = data
                    self.update_status(agent, "failed")
                    self.update_activity(agent, f"✗ {msg}")
                
                elif msg_type == "attempt_update":
                    self.attempt_label.configure(text=f"Attempt: {data}/10")
                
                elif msg_type == "progress_update":
                    self.progress_bar['value'] = data
                
                elif msg_type == "code_generated":
                    self.code_display.configure(state=tk.NORMAL)
                    self.code_display.delete("1.0", tk.END)
                    self.code_display.insert("1.0", data)
                    self.code_display.configure(state=tk.DISABLED)
                
                elif msg_type == "code_version":
                    self.code_versions.append(data)
                    self.update_version_combo()
                
                elif msg_type == "log_comm":
                    msg, tag = data
                    self.log_comm(msg, tag)
                
                elif msg_type == "log_error":
                    self.log_error(data)
                
                elif msg_type == "workflow_success":
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    self.log_comm("=" * 60, "success")
                    self.log_comm("=== SUCCESS! Code generation complete ===", "success")
                    self.log_comm(f"Time elapsed: {elapsed:.1f}s", "success")
                    self.log_comm("=" * 60, "success")
                    
                    self.is_running = False
                    self.start_btn.configure(state=tk.NORMAL)
                    self.stop_btn.configure(state=tk.DISABLED)
                    self.time_label.configure(text=f"✓ Done ({elapsed:.1f}s)")
                    
                    messagebox.showinfo("Success", 
                        f"Code generated successfully!\n\n"
                        f"Attempts: {self.state['current_attempt']}\n"
                        f"Time: {elapsed:.1f}s")
                
                elif msg_type == "workflow_failed":
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    self.log_comm("=" * 60, "error")
                    self.log_comm(f"=== FAILED: {data} ===", "error")
                    self.log_comm(f"Time elapsed: {elapsed:.1f}s", "error")
                    self.log_comm("=" * 60, "error")
                    
                    self.is_running = False
                    self.start_btn.configure(state=tk.NORMAL)
                    self.stop_btn.configure(state=tk.DISABLED)
                    self.time_label.configure(text=f"✗ Failed ({elapsed:.1f}s)")
                    
                    messagebox.showerror("Failed", f"Workflow failed:\n{data}")
                
                elif msg_type == "workflow_stopped":
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    self.log_comm("=" * 60, "system")
                    self.log_comm("=== STOPPED by user ===", "system")
                    self.log_comm(f"Time elapsed: {elapsed:.1f}s", "system")
                    self.log_comm("=" * 60, "system")
                    
                    self.is_running = False
                    self.start_btn.configure(state=tk.NORMAL)
                    self.stop_btn.configure(state=tk.DISABLED)
                    self.time_label.configure(text=f"Stopped ({elapsed:.1f}s)")
                
                elif msg_type == "error":
                    self.log_comm(f"ERROR: {data}", "error")
                    self.log_error(f"Critical error: {data}")
                    self.is_running = False
                    self.start_btn.configure(state=tk.NORMAL)
                    self.stop_btn.configure(state=tk.DISABLED)
                    messagebox.showerror("Error", f"An error occurred:\n\n{str(data)}")
                
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)


def main():
    """Main entry point."""
    os.makedirs("outputs", exist_ok=True)
    
    root = tk.Tk()
    app = CodeGenerationApp(root)
    
    # Set window icon if available
    try:
        root.iconbitmap('icon.ico')
    except:
        pass
    
    root.mainloop()


if __name__ == "__main__":
    main()
