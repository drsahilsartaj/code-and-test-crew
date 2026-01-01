"""Coder Agent - Generates Python code from problem descriptions (FIXED VERSION)."""

import re
import os
from utils.state import AgentState
from langchain_ollama import ChatOllama

# Will be set dynamically by GUI
llm = ChatOllama(model="deepseek-coder:6.7b", temperature=0.2)


# ============================================================
# MODIFICATION TASK DETECTION
# ============================================================

def detect_modification_task(problem: str) -> bool:
    """Detect if this is a code modification task (existing code provided)."""
    indicators = [
        'EXISTING CODE TO KEEP',
        'EXISTING CODE:',
        'EXISTING CODE TO MODIFY',
        'MODIFICATIONS REQUESTED',
        'CHANGES REQUESTED',
        'MODIFICATION TASK',
        'modify the existing',
        'change this code',
        'update this code',
    ]
    return any(ind.lower() in problem.lower() for ind in indicators)


def detect_interactive_modification(problem: str) -> bool:
    """Detect if modification wants interactive/loop behavior."""
    problem_lower = problem.lower()
    indicators = [
        'endless loop',
        'keep asking',
        'continuously',
        'repeatedly',
        'while true',
        'infinite loop',
        'loop forever',
        'keep running',
        'ask again',
    ]
    return any(ind in problem_lower for ind in indicators)


# ============================================================
# DETECTION FUNCTIONS
# ============================================================

def detect_task_action(problem: str) -> str:
    """Detect if the task wants print, return, or both."""
    problem_lower = problem.lower()
    
    print_keywords = ['print', 'display', 'show', 'output']
    has_print_intent = any(kw in problem_lower for kw in print_keywords)
    
    return_keywords = ['return', 'calculate', 'compute', 'find', 'get', 'check', 'is', 'determine']
    has_return_intent = any(kw in problem_lower for kw in return_keywords)
    
    if has_print_intent and not has_return_intent:
        return 'print'
    elif has_return_intent and not has_print_intent:
        return 'return'
    else:
        return 'return'


def analyze_feedback_for_return_issue(feedback_history: list) -> bool:
    """Check if feedback indicates NoneType/return value issues."""
    for feedback in feedback_history[-3:]:
        message = feedback.get('message', '').lower()
        if any(keyword in message for keyword in [
            'nonetype', 'none type', 'returns none', 'return none',
            'should return', 'must return', 'needs to return',
            'return a value', 'return the result'
        ]):
            return True
    return False


def analyze_feedback_for_typo(feedback_history: list) -> tuple:
    """Check if feedback indicates undefined variable (typo)."""
    for feedback in feedback_history[-3:]:
        message = feedback.get('message', '')
        if 'UNDEFINED VARIABLE' in message or 'undefined name' in message.lower():
            match = re.search(r"'(\w+)'", message)
            if match:
                return True, match.group(1)
    return False, None


def detect_interactive_task(problem: str) -> bool:
    """Detect if the task requires user interaction."""
    problem_lower = problem.lower()
    
    interactive_keywords = [
        'ask', 'asks', 'prompt', 'prompts', 'input', 'user enters',
        'user input', 'get from user', 'request from user',
        'interactive', 'enter', 'type in'
    ]
    
    return any(keyword in problem_lower for keyword in interactive_keywords)


# ============================================================
# TYPO FIXING (post-processing)
# ============================================================

def fix_common_typos(code: str) -> str:
    """Fix common variable name typos that LLMs make."""
    typo_patterns = [
        (r'\buseruser_', 'user_'),
        (r'\buserer_', 'user_'),
        (r'\buser_user_', 'user_'),
        (r'\binputinput', 'input'),
        (r'\bnumnum', 'num'),
        (r'\bvalval', 'val'),
        (r'\bresultresult', 'result'),
        (r'\bstringstring', 'string'),
        (r'\blistlist', 'list'),
    ]
    
    for pattern, replacement in typo_patterns:
        code = re.sub(pattern, replacement, code)
    
    return code


def fix_undefined_variable(code: str, typo_name: str) -> str:
    """Try to fix a specific undefined variable by finding similar defined names."""
    assigned_vars = set(re.findall(r'\b(\w+)\s*=\s*(?!.*=)', code))
    
    best_match = None
    best_score = 0
    
    for var in assigned_vars:
        common_len = 0
        for i in range(min(len(var), len(typo_name))):
            if var[i] == typo_name[i]:
                common_len += 1
            else:
                break
        
        if common_len > best_score and common_len >= 3:
            best_score = common_len
            best_match = var
    
    if best_match:
        code = re.sub(rf'\b{re.escape(typo_name)}\b', best_match, code)
    
    return code


# ============================================================
# MAIN CODE GENERATION
# ============================================================

def generate_code(state: AgentState) -> str:
    """Generate Python code based on the problem description and feedback."""
    problem = state["problem_description"]
    attempt = state["current_attempt"]
    feedback_history = state.get("feedback_history", [])
    
    # Detect task type
    is_modification = detect_modification_task(problem)
    is_interactive_mod = detect_interactive_modification(problem)
    task_action = detect_task_action(problem)
    is_interactive = detect_interactive_task(problem)
    
    # Check feedback for specific issues
    has_return_issue = analyze_feedback_for_return_issue(feedback_history)
    has_typo, typo_name = analyze_feedback_for_typo(feedback_history)
    
    # Build feedback context
    feedback_context = ""
    if feedback_history:
        feedback_context = "\n\n**CRITICAL - FIX THESE ERRORS:**\n"
        for fb in feedback_history[-2:]:
            source = fb.get('source', 'Unknown')
            message = fb.get('message', '')[:400]
            feedback_context += f"- [{source}]: {message}\n"
        
        if has_typo and typo_name:
            feedback_context += f"\n**TYPO FIX REQUIRED:** You wrote '{typo_name}' but this variable doesn't exist. Check your variable names carefully!\n"
    
    # Generate code
    if is_modification:
        prompt = generate_modification_prompt(problem, feedback_context, is_interactive_mod)
    else:
        prompt = generate_new_code_prompt(problem, task_action, is_interactive, has_return_issue, feedback_context)

    response = llm.invoke(prompt)
    code = response.content
    
    # Clean up the response
    code = clean_code(code)
    
    # Fix common typos
    code = fix_common_typos(code)
    
    # If we know there was a specific typo, try to fix it
    if has_typo and typo_name:
        code = fix_undefined_variable(code, typo_name)
    
    # Remove any assert statements
    code = remove_assertions(code)
    
    # For NEW code tasks only, ensure proper structure
    if not is_modification:
        if is_interactive:
            code = ensure_main_function_exists(code, problem)
        code = ensure_clean_name_block(code)
    
    return code


# ============================================================
# MODIFICATION PROMPT
# ============================================================

def generate_modification_prompt(problem: str, feedback_context: str, is_interactive_mod: bool) -> str:
    """Generate prompt for code modification tasks."""
    
    interactive_rules = ""
    if is_interactive_mod:
        interactive_rules = """
CRITICAL FOR INTERACTIVE/LOOP TASKS:
- Use print() to show results to the user, NOT return
- If user wants endless loop: use "while True:" with proper break condition
- Keep the loop running until user explicitly exits
- DO NOT use "return" inside the main loop to show results - use print()
"""
    
    return f"""You are an expert Python developer. MODIFY the existing code as requested.

{problem}
{feedback_context}

CRITICAL MODIFICATION RULES - FOLLOW EXACTLY:
1. **OUTPUT THE COMPLETE CODE** - Include ALL functions from the EXISTING CODE
2. **KEEP UNCHANGED FUNCTIONS** - Functions like is_prime(), calculate(), helper(), etc. must be kept EXACTLY as they appear in the original
3. **PRESERVE ORDER** - Output functions in the same order as the original code
4. **ONLY MODIFY WHAT'S REQUESTED** - If the request says "change main()", only change main(). Keep everything else identical.
5. **INCLUDE ALL IMPORTS** - If original has imports, keep them
6. **KEEP DOCSTRINGS** - Preserve all docstrings from original functions
7. For interactive programs that loop, use print() to show results, NOT return
8. Handle edge cases as requested (invalid input, try/except, etc.)
9. Do NOT add assertions
10. **DOUBLE-CHECK ALL VARIABLE NAMES** - make sure every variable you use is defined!
{interactive_rules}

EXAMPLE - User says "add loop to main()":
WRONG (missing is_prime):
```python
def main():
    while True:
        num = int(input(...))
        print(is_prime(num))  # ❌ is_prime not defined!
```

CORRECT (complete code):
```python
def is_prime(n: int) -> bool:
    \"\"\"Check if n is prime.\"\"\"  # KEPT FROM ORIGINAL
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def main():  # ONLY THIS WAS MODIFIED
    while True:
        try:
            text = input("Enter a number (or 'quit' to exit): ")
            if text.lower() == 'quit':
                print("Goodbye!")
                break
            n = int(text)
            if n < 0:
                print("Please enter a positive number.")
                continue
            result = is_prime(n)
            print(f"Result: {{result}}")
        except ValueError:
            print("Invalid input.")


if __name__ == "__main__":
    main()
```

See how is_prime() was kept EXACTLY as it was? That's what you must do.

OUTPUT: Return the COMPLETE Python code with ALL functions from the original, no explanations.
"""


# ============================================================
# NEW CODE PROMPT
# ============================================================

def generate_new_code_prompt(problem: str, task_action: str, is_interactive: bool, has_return_issue: bool, feedback_context: str) -> str:
    """Generate prompt for new code creation."""
    
    return_requirement = ""
    if has_return_issue or task_action == 'return':
        return_requirement = """
**CRITICAL - RETURN VALUE REQUIRED:**
Your function MUST return a value for automated testing.
"""
    
    interactive_requirement = ""
    if is_interactive:
        interactive_requirement = """
**INTERACTIVE TASK:**
Create both: 1) Core function that returns value, 2) main() with input()
"""
    
    return f"""You are an expert Python developer. Generate clean, testable Python code.

TASK: {problem}
{return_requirement}
{interactive_requirement}
{feedback_context}

REQUIREMENTS:
1. Functions MUST return results for testing
2. Include type hints and docstrings
3. Handle edge cases
4. Create a main() function for interactive use with input()
5. End with: if __name__ == "__main__": followed by commented main() call
6. **CHECK ALL VARIABLE NAMES** - every variable must be defined before use!

IMPORTANT: The if __name__ == "__main__": block should ONLY contain:
    # main()
    pass

This allows users to uncomment main() to run interactively.

Return ONLY Python code, no explanations.
"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def remove_assertions(code: str) -> str:
    """Remove any assert statements from the code."""
    lines = code.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('assert '):
            continue
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def ensure_main_function_exists(code: str, problem: str) -> str:
    """If task is interactive but main() doesn't exist, create one."""
    if 'def main(' in code:
        return code
    
    func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', code)
    if not func_match:
        return code
    
    core_func_name = func_match.group(1)
    params_str = func_match.group(2)
    
    params = []
    if params_str.strip():
        for param in params_str.split(','):
            param = param.strip()
            if ':' in param:
                param_name = param.split(':')[0].strip()
                param_type = param.split(':')[1].strip()
            else:
                param_name = param
                param_type = 'str'
            params.append((param_name, param_type))
    
    if not params:
        return code
    
    main_func = '\n\ndef main():\n    """Interactive wrapper for user input."""\n'
    
    for param_name, param_type in params:
        if 'int' in param_type.lower():
            main_func += f'    {param_name} = int(input("Enter {param_name}: "))\n'
        elif 'float' in param_type.lower():
            main_func += f'    {param_name} = float(input("Enter {param_name}: "))\n'
        else:
            main_func += f'    {param_name} = input("Enter {param_name}: ")\n'
    
    param_names = ', '.join([p[0] for p in params])
    main_func += f'    result = {core_func_name}({param_names})\n'
    main_func += '    print(f"Result: {result}")\n'
    
    # Remove any existing __name__ block first
    code = re.sub(r'\n*if\s+__name__\s*==\s*["\']__main__["\']\s*:.*$', '', code, flags=re.DOTALL)
    code = code.rstrip()
    
    # Add main function
    code = code + main_func
    
    return code


def ensure_clean_name_block(code: str) -> str:
    """
    Ensure code has a clean if __name__ == "__main__" block.
    The block should ONLY contain: # main() and pass
    This allows user to uncomment main() to run interactively.
    """
    # Remove any existing __name__ block
    code = re.sub(r'\n*if\s+__name__\s*==\s*["\']__main__["\']\s*:.*$', '', code, flags=re.DOTALL)
    code = code.rstrip()
    
    # Check if main() function exists
    has_main = 'def main(' in code
    
    # Add clean __name__ block
    if has_main:
        code += '\n\n\nif __name__ == "__main__":\n    # main()\n    pass\n'
    else:
        # No main function - just add pass
        code += '\n\n\nif __name__ == "__main__":\n    pass\n'
    
    return code


def clean_code(code: str) -> str:
    """Clean up generated code by removing markdown and extra content."""
    # Replace full-width characters
    code = code.replace('｜', '|')
    code = code.replace('（', '(')
    code = code.replace('）', ')')
    code = code.replace('：', ':')
    code = code.replace('，', ',')
    code = code.replace('＝', '=')
    code = code.replace('［', '[')
    code = code.replace('］', ']')
    
    # Remove LLM tokenization artifacts
    code = re.sub(r'<\|[^|]+\|>', '', code)
    code = re.sub(r'<\|begin[^>]+>', '', code)
    code = re.sub(r'<\|end[^>]+>', '', code)
    
    # Remove markdown code blocks
    code = re.sub(r'^```python\s*\n?', '', code)
    code = re.sub(r'^```\s*\n?', '', code)
    code = re.sub(r'\n?```\s*$', '', code)
    code = re.sub(r'\n```\s*\n', '\n', code)
    
    # Remove inline prose/explanations between code sections
    lines = code.split('\n')
    cleaned_lines = []
    
    prose_patterns = [
        'And here is', 'And here\'s', 'Here is', 'Here\'s',
        'Please note', 'Note that', 'Note:',
        'This function', 'This code', 'The function', 'The code',
        'In this', 'Above', 'Below',
        'For example', 'For instance',
        'You can', 'You could', 'You might', 'You would',
        'To do', 'To use', 'To run', 'To test',
        'If you', 'However', 'Additionally', 'Furthermore',
        'This is', 'This will', 'This should',
        'For a more', 'For more',
    ]
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == '```' or stripped == '```python':
            continue
        
        if not stripped:
            cleaned_lines.append(line)
            continue
        
        is_prose = False
        for pattern in prose_patterns:
            if stripped.startswith(pattern):
                if not stripped.startswith('#') and not stripped.startswith('"') and not stripped.startswith("'"):
                    is_prose = True
                    break
        
        if not is_prose and stripped and stripped[0].isupper():
            code_starters = ['def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except', 
                           'return ', 'import ', 'from ', 'with ', 'raise ', 'assert ',
                           'True', 'False', 'None', '@', '#']
            
            is_comment_like = (
                len(stripped) > 30 and 
                ' ' in stripped and
                not any(stripped.startswith(cs) for cs in code_starters) and
                (stripped.endswith('.') or stripped.endswith('!')) and not stripped.endswith('...')
            ) and not any([
                '=' in stripped and '==' not in stripped,
                stripped.startswith(('return ', 'if ', 'for ', 'while ', 'elif ', 'else:', 'try:', 'except', 'with ', 'import ', 'from ', 'class ', 'def ')),
                stripped.endswith(':'),
                '(' in stripped and ')' in stripped,
                stripped.startswith('@'),
            ])
            
            if is_comment_like:
                cleaned_lines.append(f"# {stripped}")
                continue
        
        if not is_prose:
            cleaned_lines.append(line)
    
    code = '\n'.join(cleaned_lines)
    
    # Remove excessive blank lines
    while '\n\n\n\n' in code:
        code = code.replace('\n\n\n\n', '\n\n\n')
    
    return code.strip()


def save_code(code: str, file_path: str) -> None:
    """Save generated code to file."""
    os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(code)