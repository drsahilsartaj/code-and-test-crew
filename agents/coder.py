"""Coder Agent - Generates Python code from problem descriptions (FIXED VERSION)."""

import re
import textwrap
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
            # Extract the typo'd variable name
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
    # Common patterns where LLM duplicates parts of variable names
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
    # Find all variable assignments
    assigned_vars = set(re.findall(r'\b(\w+)\s*=\s*(?!.*=)', code))
    
    # Find the most similar assigned variable
    best_match = None
    best_score = 0
    
    for var in assigned_vars:
        # Simple similarity: common prefix length
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
        # Replace the typo with the correct variable name
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
    
    # Build feedback context with SPECIFIC instructions
    feedback_context = ""
    if feedback_history:
        feedback_context = "\n\n**CRITICAL - FIX THESE ERRORS:**\n"
        for fb in feedback_history[-2:]:  # Last 2 feedback items
            source = fb.get('source', 'Unknown')
            message = fb.get('message', '')[:400]
            feedback_context += f"- [{source}]: {message}\n"
        
        # Add specific typo fix instruction
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
    
    # Fix common typos (post-processing safety net)
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
        code = ensure_test_block(code, problem)
        code = ensure_main_is_commented(code)
    
    return code


# ============================================================
# MODIFICATION PROMPT (with cleaner variable names)
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
    return True  # KEPT EXACTLY AS IS


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
            print(f"Result: {{result}}")  # USE PRINT, NOT RETURN!
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
4. In if __name__ == "__main__": add print tests (NO assertions!)
5. **CHECK ALL VARIABLE NAMES** - every variable must be defined before use!

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
    
    if 'if __name__' in code:
        parts = code.split('if __name__')
        code = parts[0] + main_func + '\n\nif __name__' + parts[1]
    else:
        code = code + main_func
    
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
    
    # Patterns that indicate prose (not code)
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
        
        # Skip markdown code blocks
        if stripped == '```' or stripped == '```python':
            continue
        
        # Skip empty lines (but keep them for formatting)
        if not stripped:
            cleaned_lines.append(line)
            continue
        
        # Check if line looks like prose (starts with prose pattern and doesn't look like code)
        is_prose = False
        for pattern in prose_patterns:
            if stripped.startswith(pattern):
                # Make sure it's not a string or comment containing this pattern
                if not stripped.startswith('#') and not stripped.startswith('"') and not stripped.startswith("'"):
                    is_prose = True
                    break
        
        # Additional check: if line starts with capital letter and doesn't look like code
        if not is_prose and stripped and stripped[0].isupper():
            # Check if it looks like a sentence (has spaces and no code characters at start)
            code_starters = ['def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except', 
                           'return ', 'import ', 'from ', 'with ', 'raise ', 'assert ',
                           'True', 'False', 'None', '@', '#']
            looks_like_code = any(stripped.startswith(cs) for cs in code_starters)
            
            if not looks_like_code and ' ' in stripped and not '=' in stripped and not '(' in stripped[:20]:
                # Likely a sentence/prose
                is_prose = True
        
        if not is_prose:
            cleaned_lines.append(line)
    
    code = '\n'.join(cleaned_lines)
    code = code.strip()
    
    # Remove leading "Here's the code" prefixes
    lines = code.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('def ') or stripped.startswith('import ') or stripped.startswith('from ') or stripped.startswith('#'):
            start_idx = i
            break
    
    code = '\n'.join(lines[start_idx:])
    code = textwrap.dedent(code)
    code = fix_uncommented_lines(code)
    
    return code.strip()


def fix_uncommented_lines(code: str) -> str:
    """Detect lines that look like comments but aren't commented and add # to them."""
    lines = code.split('\n')
    fixed_lines = []
    in_function = False
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]
        
        if stripped.startswith('def '):
            in_function = True
            fixed_lines.append(line)
            continue
        
        if in_function and (stripped.startswith('"""') or stripped.startswith("'''")):
            if not in_docstring:
                in_docstring = True
                docstring_char = stripped[:3]
                fixed_lines.append(line)
                if stripped.count(docstring_char) >= 2:
                    in_docstring = False
                continue
            elif docstring_char in stripped:
                in_docstring = False
                fixed_lines.append(line)
                continue
        
        if in_docstring:
            fixed_lines.append(line)
            continue
        
        if in_function and stripped and not stripped.startswith('#'):
            is_comment_like = (
                (stripped[0].isupper() and ' ' in stripped) or
                stripped.startswith(('This ', 'The ', 'Returns ', 'Calculates ', 'Checks ', 'Creates ', 'Gets ', 'Sets ')) or
                (stripped.endswith(('.', '!')) and not stripped.endswith('...'))
            ) and not any([
                '=' in stripped and '==' not in stripped,
                stripped.startswith(('return ', 'if ', 'for ', 'while ', 'elif ', 'else:', 'try:', 'except', 'with ', 'import ', 'from ', 'class ', 'def ')),
                stripped.endswith(':'),
                '(' in stripped and ')' in stripped,
                stripped.startswith('@'),
            ])
            
            if is_comment_like:
                fixed_lines.append(f"{indent}# {stripped}")
                continue
        
        if stripped.startswith('def ') or (in_function and stripped and not stripped.startswith(' ') and not stripped.startswith('#')):
            if stripped.startswith('def '):
                in_function = True
            elif not stripped.startswith('if __name__'):
                in_function = False
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def ensure_main_is_commented(code: str) -> str:
    """Ensure main() call is commented in __name__ block."""
    if 'def main(' not in code:
        return code
    
    lines = code.split('\n')
    modified_lines = []
    in_name_block = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if 'if __name__' in line:
            in_name_block = True
            modified_lines.append(line)
            continue
        
        # Comment out ANY main() calls in __name__ block (not already commented)
        if in_name_block and 'main()' in stripped and not stripped.startswith('#'):
            indent = line[:len(line) - len(line.lstrip())]
            # Comment out the line
            modified_lines.append(f"{indent}# {stripped}  # Uncomment to run interactive mode")
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)


def ensure_test_block(code: str, problem: str) -> str:
    """Ensure the code has a proper test block at the end."""
    
    # Find the main function name (not 'main')
    func_match = re.search(r'def\s+(\w+)\s*\(', code)
    if not func_match:
        return code
    
    func_name = func_match.group(1)
    
    if func_name == 'main':
        all_funcs = re.findall(r'def\s+(\w+)\s*\(', code)
        for f in all_funcs:
            if f != 'main':
                func_name = f
                break
    
    param_match = re.search(rf'def\s+{func_name}\s*\(([^)]*)\)', code)
    params = param_match.group(1) if param_match else ""
    
    has_main = 'def main(' in code
    
    # Check if __name__ block already exists
    if 'if __name__' in code:
        # Check if it has actual test code (not just main() or pass)
        name_block_match = re.search(r'if\s+__name__\s*==\s*["\']__main__["\']\s*:(.*?)(?=\ndef\s|\nclass\s|$)', code, re.DOTALL)
        if name_block_match:
            block_content = name_block_match.group(1)
            # If block only has pass, main(), or comments, replace it
            lines = [l.strip() for l in block_content.split('\n') if l.strip()]
            has_real_tests = any(
                line and 
                not line.startswith('#') and 
                line != 'pass' and 
                line != 'main()' and
                'pass  #' not in line
                for line in lines
            )
            
            if has_real_tests:
                # Already has tests, just ensure main() is commented
                return code
            
            # Remove the empty/useless __name__ block
            code = re.sub(r'\n*if\s+__name__\s*==\s*["\']__main__["\']\s*:.*?(?=\ndef\s|\nclass\s|$)', '', code, flags=re.DOTALL)
            code = code.rstrip()
    
    # Generate test block
    test_block = generate_test_block(func_name, params, problem)
    
    if has_main:
        test_block += "\n    \n    # Uncomment to run interactive mode:\n    # main()"
    
    code = code.rstrip() + "\n\n\n" + test_block
    
    return code


def generate_test_block(func_name: str, params: str, problem: str) -> str:
    """Generate appropriate test block based on function signature and problem."""
    problem_lower = problem.lower()
    
    # Extract parameter info
    param_list = []
    if params.strip():
        for param in params.split(','):
            param = param.strip()
            if ':' in param:
                param_name = param.split(':')[0].strip()
                param_type = param.split(':')[1].strip()
            else:
                param_name = param
                param_type = 'str'
            param_list.append((param_name, param_type))
    
    param_count = len(param_list)
    
    # Prime numbers - FIXED TO DETECT BOOLEAN VS LIST
    if 'prime' in problem_lower:
        # Check if it's asking for a LIST of primes or a BOOLEAN check
        is_list_task = any(w in problem_lower for w in ['all primes', 'list of primes', 'display all', 'print all', 'smaller than', 'less than', 'under', 'below', 'between'])
        is_check_task = any(w in problem_lower for w in ['check if', 'is prime', 'determine if', 'whether', 'prime or not'])
        
        if is_list_task and not is_check_task:
            # Function returns a LIST of primes
            return f'''if __name__ == "__main__":
    result = {func_name}(100)
    print(f"Primes < 100: {{result[:10]}}... ({{len(result)}} total)")'''
        elif is_check_task:
            # Function returns TRUE/FALSE for a single number
            return f'''if __name__ == "__main__":
    print(f"{func_name}(7) = {{{func_name}(7)}}")   # Should be True
    print(f"{func_name}(10) = {{{func_name}(10)}}") # Should be False'''
    
    # Factorial
    elif 'factorial' in problem_lower:
        return f'''if __name__ == "__main__":
    print(f"{func_name}(5) = {{{func_name}(5)}}")
    print(f"{func_name}(0) = {{{func_name}(0)}}")'''
    
    # Fibonacci
    elif 'fibonacci' in problem_lower or 'fib' in problem_lower:
        return f'''if __name__ == "__main__":
    print(f"{func_name}(10) = {{{func_name}(10)}}")
    print(f"{func_name}(0) = {{{func_name}(0)}}")'''
    
    # Palindrome
    elif 'palindrome' in problem_lower:
        return f'''if __name__ == "__main__":
    print(f"{func_name}('radar') = {{{func_name}('radar')}}")
    print(f"{func_name}('hello') = {{{func_name}('hello')}}")'''
    
    # Longest word - FIX: Use strings instead of number list
    elif 'longest word' in problem_lower:
        return f'''if __name__ == "__main__":
    print(f"{func_name}('hello world') = {{{func_name}('hello world')}}")
    print(f"{func_name}('the quick brown fox') = {{{func_name}('the quick brown fox')}}")'''
    
    # Maximum/Minimum in list
    elif 'maximum' in problem_lower or 'max' in problem_lower:
        return f'''if __name__ == "__main__":
    test_list = [3, 1, 4, 1, 5, 9, 2, 6]
    print(f"{func_name}({{test_list}}) = {{{func_name}(test_list)}}")  # Expected: 9'''
    
    elif 'minimum' in problem_lower or 'min' in problem_lower:
        return f'''if __name__ == "__main__":
    test_list = [3, 1, 4, 1, 5, 9, 2, 6]
    print(f"{func_name}({{test_list}}) = {{{func_name}(test_list)}}")  # Expected: 1'''
    
    # BMI calculator - NEW FIX
    elif 'bmi' in problem_lower:
        if param_count == 2:
            return f'''if __name__ == "__main__":
    print(f"{func_name}(1.75, 70) = {{{func_name}(1.75, 70)}}")
    print(f"{func_name}(1.80, 90) = {{{func_name}(1.80, 90)}}")'''
        else:
            return f'''if __name__ == "__main__":
    print(f"Test: {{{func_name}(175, 70)}}")'''
    
    # Password validator - NEW FIX
    elif 'password' in problem_lower:
        return f'''if __name__ == "__main__":
    print(f"{func_name}('Weak1!') = {{{func_name}('Weak1!')}}")
    print(f"{func_name}('StrongP@ss123') = {{{func_name}('StrongP@ss123')}}")'''
    
    # Sum/Add with 2 params
    elif ('add' in problem_lower or 'sum' in problem_lower) and param_count >= 2:
        return f'''if __name__ == "__main__":
    print(f"{func_name}(2, 3) = {{{func_name}(2, 3)}}")
    print(f"{func_name}(10, 20) = {{{func_name}(10, 20)}}")'''
    
    # GENERIC FALLBACK - Use actual parameter types
    else:
        if param_count == 0:
            return f'''if __name__ == "__main__":
    result = {func_name}()
    print(f"Result: {{result}}")'''
        
        elif param_count == 1:
            param_name, param_type = param_list[0]
            # Generate appropriate test values based on type
            if 'int' in param_type.lower():
                return f'''if __name__ == "__main__":
    print(f"Test 1: {{{func_name}(5)}}")
    print(f"Test 2: {{{func_name}(10)}}")'''
            elif 'float' in param_type.lower():
                return f'''if __name__ == "__main__":
    print(f"Test 1: {{{func_name}(5.5)}}")
    print(f"Test 2: {{{func_name}(10.0)}}")'''
            elif 'str' in param_type.lower():
                return f'''if __name__ == "__main__":
    print(f"Test 1: {{{func_name}('hello')}}")
    print(f"Test 2: {{{func_name}('world')}}")'''
            elif 'list' in param_type.lower():
                return f'''if __name__ == "__main__":
    print(f"Test 1: {{{func_name}([1, 2, 3])}}")
    print(f"Test 2: {{{func_name}([4, 5, 6])}}")'''
            else:
                return f'''if __name__ == "__main__":
    print(f"Test: {{{func_name}('test')}}")'''
        
        elif param_count == 2:
            p1_name, p1_type = param_list[0]
            p2_name, p2_type = param_list[1]
            
            # Generate appropriate values for both parameters
            def get_test_value(param_type, is_second=False):
                if 'int' in param_type.lower():
                    return '3' if not is_second else '5'
                elif 'float' in param_type.lower():
                    return '1.75' if not is_second else '70.0'
                elif 'str' in param_type.lower():
                    return "'hello'" if not is_second else "'world'"
                else:
                    return '5' if not is_second else '10'
            
            val1 = get_test_value(p1_type, False)
            val2 = get_test_value(p2_type, True)
            
            return f'''if __name__ == "__main__":
    print(f"{func_name}({val1}, {val2}) = {{{func_name}({val1}, {val2})}}")
    print(f"{func_name}({get_test_value(p1_type, True)}, {get_test_value(p2_type, False)}) = {{{func_name}({get_test_value(p1_type, True)}, {get_test_value(p2_type, False)})}}")'''
        
        else:
            # 3+ parameters - generic approach
            return f'''if __name__ == "__main__":
    print(f"Test: {{{func_name}(1, 2, 3)}}")'''


def save_code(code: str, file_path: str) -> None:
    """Save generated code to file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)