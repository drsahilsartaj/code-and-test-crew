"""Reviewer Agent - Static analysis of code without execution (FIXED VERSION)."""

import re
import ast
from langchain_ollama import ChatOllama
from utils.state import AgentState


llm = ChatOllama(model="codellama:7b-instruct-q4_0", temperature=0.1)


# ============================================================
# AST-BASED ERROR DETECTION (catches typos like useruser_input)
# ============================================================

def check_undefined_names(code: str) -> tuple:
    """
    Use AST to find undefined variable names (catches typos).
    Returns: (has_error, error_message)
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return True, f"Syntax error at line {e.lineno}: {e.msg}"
    
    # Built-in names that are always available
    builtins = {
        'print', 'input', 'int', 'float', 'str', 'list', 'dict', 'set', 'tuple',
        'len', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
        'sum', 'min', 'max', 'abs', 'round', 'pow', 'divmod', 'bin', 'hex', 'oct',
        'open', 'type', 'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr',
        'True', 'False', 'None',
        'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
        'RuntimeError', 'StopIteration', 'AttributeError', 'NameError', 'ZeroDivisionError',
        'FileNotFoundError', 'IOError', 'OSError', 'ImportError', 'ModuleNotFoundError',
        'all', 'any', 'bool', 'bytes', 'callable', 'chr', 'ord',
        'complex', 'dir', 'eval', 'exec', 'format', 'globals', 'locals',
        'hash', 'help', 'id', 'iter', 'next', 'object', 'repr', 'slice', 'super', 'vars',
        '__name__', '__main__', '__file__', '__doc__',
    }
    
    # Collect all defined names in each scope
    defined_names = set(builtins)
    
    class NameCollector(ast.NodeVisitor):
        def __init__(self):
            self.defined = set()
            self.used = []  # (name, lineno)
            self.current_scope_definitions = set()
        
        def visit_FunctionDef(self, node):
            # Function name is defined
            self.defined.add(node.name)
            
            # Save outer scope
            outer_definitions = self.current_scope_definitions.copy()
            self.current_scope_definitions = self.defined.copy()
            
            # Add parameters to current scope
            for arg in node.args.args:
                self.current_scope_definitions.add(arg.arg)
            for arg in node.args.posonlyargs:
                self.current_scope_definitions.add(arg.arg)
            for arg in node.args.kwonlyargs:
                self.current_scope_definitions.add(arg.arg)
            if node.args.vararg:
                self.current_scope_definitions.add(node.args.vararg.arg)
            if node.args.kwarg:
                self.current_scope_definitions.add(node.args.kwarg.arg)
            
            # Visit function body
            for child in node.body:
                self.visit(child)
            
            # Restore outer scope
            self.defined.update(self.current_scope_definitions)
            self.current_scope_definitions = outer_definitions
        
        def visit_ClassDef(self, node):
            self.defined.add(node.name)
            self.generic_visit(node)
        
        def visit_Import(self, node):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split('.')[0]
                self.defined.add(name)
                self.current_scope_definitions.add(name)
        
        def visit_ImportFrom(self, node):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                self.defined.add(name)
                self.current_scope_definitions.add(name)
        
        def visit_Assign(self, node):
            # First visit the value (right side) to check for undefined names
            self.visit(node.value)
            # Then add the targets as defined
            for target in node.targets:
                self._add_target(target)
        
        def visit_AnnAssign(self, node):
            if node.value:
                self.visit(node.value)
            self._add_target(node.target)
        
        def visit_AugAssign(self, node):
            # For +=, -=, etc., the target must already be defined
            self.visit(node.value)
            if isinstance(node.target, ast.Name):
                self.used.append((node.target.id, node.target.lineno))
        
        def _add_target(self, target):
            if isinstance(target, ast.Name):
                self.defined.add(target.id)
                self.current_scope_definitions.add(target.id)
            elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                for elt in target.elts:
                    self._add_target(elt)
        
        def visit_For(self, node):
            self._add_target(node.target)
            self.visit(node.iter)
            for child in node.body:
                self.visit(child)
            for child in node.orelse:
                self.visit(child)
        
        def visit_With(self, node):
            for item in node.items:
                self.visit(item.context_expr)
                if item.optional_vars:
                    self._add_target(item.optional_vars)
            for child in node.body:
                self.visit(child)
        
        def visit_ExceptHandler(self, node):
            if node.name:
                self.defined.add(node.name)
                self.current_scope_definitions.add(node.name)
            for child in node.body:
                self.visit(child)
        
        def visit_ListComp(self, node):
            # Comprehension variables are local
            for generator in node.generators:
                self._add_target(generator.target)
                self.visit(generator.iter)
                for if_clause in generator.ifs:
                    self.visit(if_clause)
            self.visit(node.elt)
        
        def visit_SetComp(self, node):
            for generator in node.generators:
                self._add_target(generator.target)
                self.visit(generator.iter)
            self.visit(node.elt)
        
        def visit_DictComp(self, node):
            for generator in node.generators:
                self._add_target(generator.target)
                self.visit(generator.iter)
            self.visit(node.key)
            self.visit(node.value)
        
        def visit_GeneratorExp(self, node):
            for generator in node.generators:
                self._add_target(generator.target)
                self.visit(generator.iter)
            self.visit(node.elt)
        
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                # Check if name is defined
                all_defined = self.defined | self.current_scope_definitions
                if node.id not in all_defined:
                    self.used.append((node.id, node.lineno))
    
    collector = NameCollector()
    collector.visit(tree)
    
    # Find truly undefined names
    undefined = []
    all_defined = collector.defined | builtins
    
    for name, lineno in collector.used:
        if name not in all_defined:
            undefined.append((name, lineno))
    
    if undefined:
        # Format error message with suggestions
        error_parts = []
        for name, lineno in undefined[:3]:
            # Try to suggest a fix by finding similar defined names
            similar = []
            for defined_name in all_defined:
                if defined_name.startswith(name[:3]) or name.startswith(defined_name[:3]):
                    similar.append(defined_name)
            
            if similar:
                error_parts.append(f"'{name}' at line {lineno} (did you mean '{similar[0]}'?)")
            else:
                error_parts.append(f"'{name}' at line {lineno}")
        
        return True, f"UNDEFINED VARIABLE(S): {', '.join(error_parts)}. FIX: Check for typos in variable names!"
    
    return False, ""


def check_syntax_errors(code: str) -> tuple:
    """
    Check for Python syntax errors using AST.
    Returns: (has_error, error_message)
    """
    try:
        ast.parse(code)
        return False, ""
    except SyntaxError as e:
        return True, f"Syntax error at line {e.lineno}: {e.msg}"


# ============================================================
# TASK INTENT DETECTION
# ============================================================

def detect_task_intent(problem: str) -> dict:
    """
    Analyze problem description to understand what the code should do.
    """
    problem_lower = problem.lower()
    
    # Print/display keywords
    print_keywords = ['print', 'display', 'show', 'output']
    has_print_intent = any(kw in problem_lower for kw in print_keywords)
    
    # Return/compute keywords
    return_keywords = ['return', 'calculate', 'compute', 'find', 'get', 'check', 'is', 'determine']
    has_return_intent = any(kw in problem_lower for kw in return_keywords)
    
    # Determine action
    if has_print_intent and not has_return_intent:
        action = 'print'
    elif has_return_intent and not has_print_intent:
        action = 'return'
    else:
        action = 'both'
    
    # Determine expected data type
    data_type = 'any'
    if 'list' in problem_lower or 'all' in problem_lower:
        data_type = 'list'
    elif 'true' in problem_lower or 'false' in problem_lower or 'check' in problem_lower:
        data_type = 'bool'
    elif 'number' in problem_lower or 'count' in problem_lower:
        data_type = 'number'
    
    # Detect if task needs a loop
    loop_keywords = ['endless', 'keep asking', 'continuously', 'repeatedly', 'loop', 'again and again', 'until', 'while true']
    needs_loop = any(kw in problem_lower for kw in loop_keywords)
    
    # Detect if task needs try/except error handling
    # Be more specific - only require try/except for user input parsing scenarios
    # NOT for simple type checking which can use isinstance()
    error_keywords_strict = [
        'try/except', 'try except', 'exception handling',
        'handle invalid input', 'handle letters', 'handle non-numeric',
        'catch error', 'catch exception'
    ]
    # These only need error handling when combined with user input/parsing
    error_keywords_with_input = ['invalid', 'error', 'letter', 'negative']
    input_keywords = ['input', 'user', 'enter', 'prompt', 'ask']
    
    needs_error_handling = any(kw in problem_lower for kw in error_keywords_strict)
    
    # Only require try/except if there's user input AND error handling mentioned
    if not needs_error_handling:
        has_input = any(kw in problem_lower for kw in input_keywords)
        has_error_context = any(kw in problem_lower for kw in error_keywords_with_input)
        needs_error_handling = has_input and has_error_context and needs_loop
    
    return {
        'action': action, 
        'data_type': data_type,
        'needs_loop': needs_loop,
        'needs_error_handling': needs_error_handling
    }


def analyze_function_behavior(code: str) -> dict:
    """
    Analyze what the main function actually does.
    
    FIXED VERSION: Only looks INSIDE function bodies, not at if __name__ block.
    """
    # Find the first non-main function
    func_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*([^:]+))?:'
    matches = re.findall(func_pattern, code)
    
    other_func_name = None
    return_type_hint = None
    
    for func_name, ret_type in matches:
        if func_name not in ['main', 'test_', '__']:  # Skip main and test functions
            other_func_name = func_name
            return_type_hint = ret_type.strip() if ret_type else None
            break
    
    # ================================================================
    # FIX: Check if function returns by looking ONLY inside function body
    # ================================================================
    has_return = False
    
    # Method 1: Return type hint (-> int, -> bool, etc.)
    if return_type_hint and return_type_hint.lower().strip() not in ['none', 'noreturn']:
        has_return = True
    
    # Method 2: Extract ONLY the function body (not if __name__ block!)
    if not has_return and other_func_name:
        # Match from "def func_name" to next "def" or "if __name__" or "class"
        # This ensures we ONLY look inside the function, not the test block
        func_body_pattern = rf'def\s+{re.escape(other_func_name)}\s*\([^)]*\)[^:]*:(.*?)(?=\n(?:def\s|class\s|if\s+__name__))'
        body_match = re.search(func_body_pattern, code, re.DOTALL)
        
        if body_match:
            func_body = body_match.group(1)
            # Check for "return <value>" (not just bare "return")
            if re.search(r'\breturn\s+(?!None\s*$)[^\s]', func_body):
                has_return = True
        else:
            # Fallback: function goes to end of file
            func_body_pattern_eof = rf'def\s+{re.escape(other_func_name)}\s*\([^)]*\)[^:]*:(.*?)$'
            body_match = re.search(func_body_pattern_eof, code, re.DOTALL)
            if body_match:
                func_body = body_match.group(1)
                # Don't include if __name__ block
                func_body = re.sub(r'if\s+__name__.*$', '', func_body, flags=re.DOTALL)
                if re.search(r'\breturn\s+(?!None\s*$)[^\s]', func_body):
                    has_return = True
    
    # Check main() function
    main_match = re.search(r'def\s+main\s*\([^)]*\):[^\n]*\n((?:\s{4,}.*\n)*)', code)
    main_body = main_match.group(1) if main_match else ""
    
    # Check for print in the non-main function (for loop tasks only)
    has_print_in_other = False
    if other_func_name:
        func_body_pattern = rf'def\s+{re.escape(other_func_name)}\s*\([^)]*\)[^:]*:(.*?)(?=\n(?:def\s|class\s|if\s+__name__))'
        body_match = re.search(func_body_pattern, code, re.DOTALL)
        if body_match:
            has_print_in_other = 'print(' in body_match.group(1)
    
    has_while_true = 'while True' in code
    has_try_except = 'try:' in code
    has_print_in_main = 'print(' in main_body
    
    has_return_in_loop = False
    if has_while_true:
        while_match = re.search(r'while\s+True\s*:((?:\n(?:        |\t\t).*)*)', code)
        if while_match:
            loop_body = while_match.group(1)
            if 'return ' in loop_body:
                lines = loop_body.split('\n')
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('return ') and ('f"' in stripped or "f'" in stripped):
                        has_return_in_loop = True
                        break
    
    return {
        'has_return': has_return,
        'has_print': has_print_in_other or has_print_in_main,
        'has_while_true': has_while_true,
        'has_try_except': has_try_except,
        'has_return_in_loop': has_return_in_loop,
        'return_type_hint': return_type_hint
    }


def detect_modification_task(problem: str) -> bool:
    """Detect if this is a code modification task."""
    indicators = [
        'EXISTING CODE',
        'MODIFICATIONS REQUESTED',
        'CHANGES REQUESTED',
        'MODIFICATION TASK',
        'modify',
        'change this code',
        'update this code',
    ]
    return any(ind.lower() in problem.lower() for ind in indicators)


# ============================================================
# STATIC CHECKS
# ============================================================

def has_syntax_issues(code: str) -> tuple:
    """Check for obvious syntax issues."""
    lines = code.split('\n')
    
    for i, line in enumerate(lines):
        if line.strip().startswith('def '):
            if line[0] == ' ':
                return True, "Code has improper indentation - top-level function definitions should not be indented."
            break
    
    return False, ""


def has_input_in_core_logic(code: str) -> tuple:
    """Check if code has input() calls in core logic functions."""
    func_pattern = r'def\s+(\w+)\s*\([^)]*\):'
    functions = re.findall(func_pattern, code)
    
    lines = code.split('\n')
    
    for func_name in functions:
        if func_name.lower() in ['main', 'run', 'interactive', 'demo', 'start']:
            continue
        
        func_def_pattern = f'def\\s+{func_name}\\s*\\([^)]*\\):'
        func_start_idx = None
        
        for i, line in enumerate(lines):
            if re.search(func_def_pattern, line):
                func_start_idx = i
                break
        
        if func_start_idx is None:
            continue
        
        func_end_idx = len(lines)
        for i in range(func_start_idx + 1, len(lines)):
            if lines[i].strip().startswith('def '):
                if len(lines[i]) - len(lines[i].lstrip()) <= len(lines[func_start_idx]) - len(lines[func_start_idx].lstrip()):
                    func_end_idx = i
                    break
        
        func_body = '\n'.join(lines[func_start_idx:func_end_idx])
        if 'input(' in func_body:
            return True, func_name
    
    return False, ""


def has_main_function(code: str) -> bool:
    """Check if code has a main() function."""
    return 'def main(' in code


def detect_interactive_requirement(problem: str) -> bool:
    """Detect if the problem requires user interaction."""
    problem_lower = problem.lower()
    
    interactive_keywords = [
        'ask', 'asks', 'prompt', 'prompts', 'input', 'user enters',
        'user input', 'get from user', 'request from user',
        'interactive', 'enter', 'type in', 'keep asking'
    ]
    
    return any(keyword in problem_lower for keyword in interactive_keywords)


# ============================================================
# BEHAVIORAL CHECKS
# ============================================================

def check_loop_behavior(code: str, task_intent: dict) -> tuple:
    """Check if code properly implements loop behavior when required."""
    if not task_intent.get('needs_loop'):
        return False, ""
    
    if 'while True' not in code and 'while true' not in code.lower():
        return True, "Task requires an endless loop (keep asking for input), but no 'while True' loop was found."
    
    func_behavior = analyze_function_behavior(code)
    if func_behavior.get('has_return_in_loop'):
        return True, "CRITICAL: Code has 'return' inside the while True loop which exits after first iteration! Use 'print()' to show results."
    
    return False, ""


def check_error_handling(code: str, task_intent: dict) -> tuple:
    """Check if code properly implements error handling when required."""
    if not task_intent.get('needs_error_handling'):
        return False, ""
    
    if 'try:' not in code or 'except' not in code:
        return True, "Task requires error handling but no try/except block was found."
    
    return False, ""


def check_return_vs_print_in_loop(code: str, task_intent: dict) -> tuple:
    """Specifically check for the return-in-loop bug."""
    if not task_intent.get('needs_loop'):
        return False, ""
    
    while_pattern = r'while\s+True\s*:(.*?)(?=\ndef\s|\nclass\s|\nif\s+__name__|$)'
    matches = re.findall(while_pattern, code, re.DOTALL)
    
    for match in matches:
        lines = match.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('return ') and ('f"' in stripped or "f'" in stripped):
                return True, f"BUG: '{stripped[:50]}' uses return to show result inside loop. Use print() instead."
    
    return False, ""


# ============================================================
# MAIN REVIEW FUNCTION
# ============================================================

REVIEWER_PROMPT = """You are a Code Reviewer Agent. Analyze the following Python code for correctness WITHOUT executing it.

Problem Description:
{problem_description}

Code to Review:
```python
{code}
```

IMPORTANT CONTEXT:
{context}

Analyze the code for:
1. Logic errors - Does the algorithm correctly solve the problem?
2. Edge cases - Are boundary conditions handled?
3. Input validation - Are inputs properly checked?
4. Best practices - Is the code well-structured?
5. **LOOP BEHAVIOR** - If endless loop requested, does it use print() not return?

Respond in this EXACT format:
STATUS: APPROVED or REJECTED
FEEDBACK: Your detailed feedback here (one paragraph)
"""


def review_code(state: AgentState) -> dict:
    """Review the generated code and return status and feedback."""
    
    problem = state["problem_description"]
    code = state["generated_code"]
    
    # ============================================================
    # CRITICAL: Check for undefined names FIRST (catches typos!)
    # ============================================================
    has_undefined, undefined_msg = check_undefined_names(code)
    if has_undefined:
        return {
            "status": "rejected",
            "feedback": undefined_msg
        }
    
    # Check for syntax issues
    has_issues, issue_msg = has_syntax_issues(code)
    if has_issues:
        return {
            "status": "rejected",
            "feedback": f"Syntax issue detected: {issue_msg}"
        }
    
    # Detect task requirements
    task_intent = detect_task_intent(problem)
    task_intent['problem_text'] = problem
    
    is_modification = detect_modification_task(problem)
    requires_interaction = detect_interactive_requirement(problem)
    
    # Check for input() in core logic (only for new code)
    if not is_modification:
        has_input, func_with_input = has_input_in_core_logic(code)
        if has_input:
            return {
                "status": "rejected",
                "feedback": f"Code contains input() in '{func_with_input}' function, making it untestable."
            }
    
    # Check if interactive task is missing main()
    if not is_modification and requires_interaction and not has_main_function(code):
        return {
            "status": "rejected",
            "feedback": "Task requires interaction but no main() function found."
        }
    
    # Check loop behavior
    loop_issue, loop_msg = check_loop_behavior(code, task_intent)
    if loop_issue:
        return {
            "status": "rejected",
            "feedback": loop_msg
        }
    
    # Check return vs print in loop
    return_issue, return_msg = check_return_vs_print_in_loop(code, task_intent)
    if return_issue:
        return {
            "status": "rejected",
            "feedback": return_msg
        }
    
    # Check error handling
    error_issue, error_msg = check_error_handling(code, task_intent)
    if error_issue:
        return {
            "status": "rejected",
            "feedback": error_msg
        }
    
    # Check return value for new code
    if not is_modification:
        func_behavior = analyze_function_behavior(code)
        if task_intent['action'] == 'return' and not func_behavior['has_return']:
            return {
                "status": "rejected",
                "feedback": "Function should return a value for testing but only prints."
            }
    
    # Build context for LLM
    context = f"Task expects: {task_intent['action']} action"
    if task_intent['needs_loop']:
        context += ", REQUIRES ENDLESS LOOP"
    if task_intent['needs_error_handling']:
        context += ", REQUIRES ERROR HANDLING"
    
    func_behavior = analyze_function_behavior(code)
    context += f"\nFunction: returns={func_behavior['has_return']}, has_while_true={func_behavior['has_while_true']}, has_try_except={func_behavior['has_try_except']}"
    
    if is_modification:
        context += "\nThis is a CODE MODIFICATION task."
    
    # LLM review
    prompt = REVIEWER_PROMPT.format(
        problem_description=problem,
        code=code,
        context=context
    )
    
    response = llm.invoke(prompt)
    content = response.content.strip()
    
    # Parse response
    status = "rejected"
    feedback = content
    
    lines = content.split("\n")
    for line in lines:
        if line.startswith("STATUS:"):
            status_text = line.replace("STATUS:", "").strip().lower()
            if "approved" in status_text:
                status = "approved"
            else:
                status = "rejected"
        elif line.startswith("FEEDBACK:"):
            feedback = line.replace("FEEDBACK:", "").strip()
            idx = content.find("FEEDBACK:")
            if idx != -1:
                feedback = content[idx + 9:].strip()
    
    return {
        "status": status,
        "feedback": feedback
    }
