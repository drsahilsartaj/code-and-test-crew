"""Tester Agent - Executes code and runs tests with LLM fallback and signature validation."""

import subprocess
import sys
import tempfile
import os
import re
import ast
from utils.state import AgentState
from langchain_ollama import ChatOllama

# LLM for fallback test generation (only used when no pattern matches)
test_llm = ChatOllama(model="codellama:7b-instruct-q4_0", temperature=0.2)


# ============================================================
# TASK DETECTION
# ============================================================

def detect_function_type(code: str, problem_desc: str) -> str:
    """Detect if function prints, returns, or both."""
    problem_lower = problem_desc.lower()
    
    print_keywords = ['print', 'display', 'show', 'output']
    return_keywords = ['return', 'calculate', 'compute', 'find', 'get', 'check', 'is']
    
    has_print_intent = any(kw in problem_lower for kw in print_keywords)
    has_return_intent = any(kw in problem_lower for kw in return_keywords)
    
    func_bodies = re.findall(r'def\s+(\w+)\s*\([^)]*\):[^\n]*\n((?:\s{4,}.*\n)*)', code)
    main_func_body = ""
    for func_name, body in func_bodies:
        if func_name != 'main':
            main_func_body = body
            break
    
    has_print_call = 'print(' in main_func_body
    has_return_statement = re.search(r'\n\s+return\s+', main_func_body) is not None
    
    if has_print_call and not has_return_statement:
        return 'print'
    elif has_return_statement and not has_print_call:
        return 'return'
    elif has_print_call and has_return_statement:
        return 'both'
    else:
        if has_print_intent and not has_return_intent:
            return 'print'
        else:
            return 'return'


def detect_modification_task(problem: str) -> bool:
    """Detect if this is a code modification task."""
    indicators = [
        'EXISTING CODE',
        'MODIFICATIONS REQUESTED',
        'CHANGES REQUESTED',
        'MODIFICATION TASK',
        'modify',
        'change this code',
    ]
    return any(ind.lower() in problem.lower() for ind in indicators)


def detect_loop_requirement(problem: str) -> bool:
    """Detect if task requires endless loop behavior."""
    problem_lower = problem.lower()
    loop_keywords = ['endless', 'keep asking', 'continuously', 'repeatedly', 'loop', 'again and again', 'while true']
    return any(kw in problem_lower for kw in loop_keywords)


def detect_error_handling_requirement(problem: str) -> bool:
    """Detect if task requires error handling."""
    problem_lower = problem.lower()
    error_keywords = ['handle', 'edge case', 'invalid', 'error', 'letter', 'negative', 'exception', 'valueerror']
    return any(kw in problem_lower for kw in error_keywords)


# ============================================================
# FUNCTION INFO EXTRACTION (IMPROVED)
# ============================================================

def extract_function_info(code: str) -> dict:
    """Extract function name, parameter count, types, and return type from code using AST."""
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip main, __init__, and private functions
                if node.name in ['main', '__init__'] or node.name.startswith('_'):
                    continue
                
                # Extract parameter information
                param_count = len(node.args.args)
                param_names = [arg.arg for arg in node.args.args]
                param_types = []
                
                # Get type annotations if available
                for arg in node.args.args:
                    if arg.annotation:
                        param_types.append(ast.unparse(arg.annotation))
                    else:
                        param_types.append('unknown')
                
                # Get return type annotation if available
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns)
                
                return {
                    'name': node.name,
                    'param_count': param_count,
                    'param_names': param_names,
                    'param_types': param_types,
                    'return_type': return_type
                }
        
        # Fallback to regex if AST parsing doesn't find function
        return extract_function_info_regex(code)
        
    except SyntaxError:
        # If AST fails, fall back to regex
        return extract_function_info_regex(code)


def extract_function_info_regex(code: str) -> dict:
    """Fallback regex-based function extraction."""
    all_funcs = re.findall(r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?:', code)
    
    for func_name, params, return_type in all_funcs:
        if func_name != 'main':
            param_count = 0
            param_names = []
            param_types = []
            
            if params.strip():
                param_list = [p.strip() for p in params.split(',') if p.strip()]
                param_count = len(param_list)
                
                for param in param_list:
                    if ':' in param:
                        name, type_hint = param.split(':', 1)
                        param_names.append(name.strip())
                        param_types.append(type_hint.strip())
                    else:
                        param_names.append(param.strip())
                        param_types.append('unknown')
            
            return_type_clean = return_type.strip() if return_type else None
            
            return {
                'name': func_name,
                'param_count': param_count,
                'param_names': param_names,
                'param_types': param_types,
                'return_type': return_type_clean
            }
    
    return {'name': 'unknown', 'param_count': 0, 'param_names': [], 'param_types': [], 'return_type': None}


def detect_expected_param_type(code: str, problem_desc: str, func_info: dict) -> str:
    """Detect what type of parameter the function expects."""
    problem_lower = problem_desc.lower()
    param_types = func_info.get('param_types', [])
    
    if param_types:
        first_type = param_types[0]
        if 'list' in first_type.lower() or '[' in first_type:
            return 'list'
        elif 'str' in first_type.lower():
            return 'str'
        elif 'int' in first_type.lower():
            return 'int'
        elif 'float' in first_type.lower():
            return 'float'
    
    list_keywords = ['list', 'array', 'elements', 'items', 'values in a', 'numbers in a', 
                     'maximum value in a', 'minimum value in a', 'sum of a', 'average of a', 
                     'sort a', 'reverse a', 'merge', 'sorted list']
    if any(kw in problem_lower for kw in list_keywords):
        return 'list'
    
    string_keywords = ['string', 'text', 'word', 'palindrome', 'reverse a string', 
                       'vowels', 'characters', 'substring', 'permutation', 'anagram']
    if any(kw in problem_lower for kw in string_keywords):
        return 'str'
    
    return 'int'


# ============================================================
# SIGNATURE VALIDATION (NEW!)
# ============================================================

def validate_function_call(func_name: str, test_call: str, expected_param_count: int) -> bool:
    """
    Validate that a test function call has the correct number of arguments.
    Returns True if valid, False otherwise.
    """
    # Extract arguments from function call
    # Match pattern: func_name(arg1, arg2, ...)
    pattern = rf'{re.escape(func_name)}\s*\((.*?)\)'
    match = re.search(pattern, test_call)
    
    if not match:
        return False
    
    args_str = match.group(1).strip()
    
    if not args_str:
        return expected_param_count == 0
    
    # Count arguments (simple comma split, doesn't handle nested structures perfectly)
    # But good enough for most cases
    arg_count = len([arg.strip() for arg in args_str.split(',') if arg.strip()])
    
    return arg_count == expected_param_count


def generate_smart_test_values(param_count: int, param_types: list, problem_desc: str) -> list:
    """
    Generate appropriate test values based on parameter count and types.
    Returns a list of test value sets (each set is a list of values).
    """
    problem_lower = problem_desc.lower()
    test_sets = []
    
    if param_count == 0:
        return [[]]  # No arguments needed
    
    elif param_count == 1:
        param_type = param_types[0] if param_types else 'unknown'
        
        # Determine type from type hint or problem description
        if 'list' in param_type.lower() or 'list' in problem_lower:
            test_sets.append(['[3, 1, 4, 1, 5, 9]'])
            test_sets.append(['[1, 2, 3]'])
            test_sets.append(['[-5, -2, -10]'])
        elif 'str' in param_type.lower() or any(kw in problem_lower for kw in ['string', 'text', 'word']):
            if 'palindrome' in problem_lower:
                test_sets.append(['"radar"'])
                test_sets.append(['"hello"'])
            elif 'vowel' in problem_lower:
                test_sets.append(['"hello"'])
                test_sets.append(['"aeiou"'])
            else:
                test_sets.append(['"test"'])
                test_sets.append(['"hello"'])
        else:
            # Numeric types
            test_sets.append(['5'])
            test_sets.append(['10'])
            test_sets.append(['0'])
    
    elif param_count == 2:
        # Two parameters - common patterns
        if 'two strings' in problem_lower or 'anagram' in problem_lower:
            test_sets.append(['"listen"', '"silent"'])
            test_sets.append(['"hello"', '"world"'])
        elif 'two numbers' in problem_lower or 'gcd' in problem_lower or 'lcm' in problem_lower:
            test_sets.append(['12', '18'])
            test_sets.append(['5', '10'])
        elif 'subsequence' in problem_lower or 'common' in problem_lower:
            test_sets.append(['"ABCBDAB"', '"BDCAB"'])
            test_sets.append(['"AGGTAB"', '"GXTXAYB"'])
        else:
            # Default two numeric parameters
            test_sets.append(['2', '3'])
            test_sets.append(['5', '10'])
    
    else:
        # 3+ parameters - generate generic values
        generic_values = []
        for i in range(param_count):
            generic_values.append(str(i + 1))
        test_sets.append(generic_values)
    
    return test_sets if test_sets else [['1'] * param_count]


# ============================================================
# BEHAVIORAL TESTING FOR MODIFICATION TASKS (FIXED)
# ============================================================

def generate_behavioral_tests(code: str, problem_desc: str) -> str:
    """
    Generate tests that check BEHAVIOR, not just return values.
    For modification tasks with loops and error handling.
    """
    needs_loop = detect_loop_requirement(problem_desc)
    needs_error_handling = detect_error_handling_requirement(problem_desc)
    
    # Simpler tests that don't have syntax issues
    test_code = '''from code import *
import inspect

'''
    
    # Test 1: Check for while True loop existence
    if needs_loop:
        test_code += '''def test_has_while_true_loop():
    """Check that code contains a while True loop."""
    source = inspect.getsource(main)
    assert "while True" in source or "while true" in source.lower(), \\
        "Code should have while True loop for continuous input"

'''
    
    # Test 2: Check that loop uses print not return for results
    if needs_loop:
        test_code += '''def test_uses_print_not_return_in_loop():
    """Check that loop uses print, not return, to show results."""
    source = inspect.getsource(main)
    # The loop should have print statements for showing results
    assert "print(" in source, "Loop should use print() to show results"
    # Check there's no return with f-string inside the while block
    lines = source.split("\\n")
    in_while = False
    for line in lines:
        if "while True" in line:
            in_while = True
        if in_while and line.strip().startswith("return ") and ("f\\'" in line or "f\\"" in line):
            assert False, "Should not use return with f-string in loop - use print() instead"

'''
    
    # Test 3: Check for try/except
    if needs_error_handling:
        test_code += '''def test_has_error_handling():
    """Check that code has try/except for error handling."""
    source = inspect.getsource(main)
    assert "try:" in source and "except" in source, \\
        "Code should have try/except block for handling invalid input"

'''
    
    # Test 4: Check for ValueError handling
    if needs_error_handling:
        test_code += '''def test_handles_valueerror():
    """Check that code handles ValueError (for non-numeric input)."""
    source = inspect.getsource(main)
    assert "ValueError" in source or "Exception" in source, \\
        "Code should catch ValueError for invalid input like letters"

'''
    
    # Test 5: Test core function works
    test_code += '''def test_core_function_works():
    """Test that the core logic function works correctly."""
    # Test is_prime if it exists
    if "is_prime" in dir():
        assert is_prime(7) == True, "7 is prime"
        assert is_prime(4) == False, "4 is not prime"
        assert is_prime(2) == True, "2 is prime"
        assert is_prime(1) == False, "1 is not prime"

'''
    
    return test_code


# ============================================================
# TEST CODE PREPARATION
# ============================================================

def make_code_testable(code: str, problem_desc: str) -> str:
    """Replace input() calls with test values."""
    lines = code.split('\n')
    modified_lines = []
    
    for line in lines:
        input_match = re.match(r'(\s*)(\w+)\s*=\s*(int|float|str)?\(?\s*input\(', line)
        
        if input_match:
            indent = input_match.group(1)
            var_name = input_match.group(2)
            cast_type = input_match.group(3)
            
            modified_lines.append(f"{indent}# {line.strip()}  # [AUTO-COMMENTED FOR TESTING]")
            test_value = generate_smart_test_value(var_name, cast_type, problem_desc)
            modified_lines.append(f"{indent}{var_name} = {test_value}  # [TEST VALUE]")
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)


def generate_smart_test_value(var_name: str, cast_type: str, problem_desc: str) -> str:
    """Generate intelligent test values based on variable name and context."""
    var_lower = var_name.lower()
    
    if cast_type == 'int':
        if 'age' in var_lower:
            return '25'
        elif 'year' in var_lower:
            return '2000'
        elif 'number' in var_lower or 'num' in var_lower or 'n' == var_lower:
            return '100'
        else:
            return '10'
    elif cast_type == 'float':
        return '5.0'
    else:
        return '"test"'


def generate_test_value(param_type: str, problem_desc: str) -> str:
    """Generate appropriate test value based on parameter type."""
    problem_lower = problem_desc.lower()
    
    if param_type == 'list':
        if 'max' in problem_lower:
            return '[3, 1, 4, 1, 5, 9, 2, 6]'
        elif 'sort' in problem_lower:
            return '[5, 2, 8, 1, 9]'
        else:
            return '[1, 2, 3, 4, 5]'
    elif param_type == 'str':
        if 'palindrome' in problem_lower:
            return '"radar"'
        elif 'vowel' in problem_lower:
            return '"hello world"'
        else:
            return '"test"'
    elif param_type == 'float':
        return '3.14'
    else:
        return '10'


# ============================================================
# PRINT FUNCTION TESTS
# ============================================================

def generate_tests_for_print_function(func_info: dict, problem_desc: str) -> str:
    """Generate tests for functions that print output."""
    func_name = func_info['name']
    problem_lower = problem_desc.lower()
    
    is_prime_list = "prime" in problem_lower and any(word in problem_lower for word in 
                    ["all", "list", "display", "print", "show"])
    
    if is_prime_list:
        return f'''from code import *
import sys
from io import StringIO

def test_contains_small_primes():
    """Test that output contains small prime numbers."""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    {func_name}(100)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    assert '2' in output, "Output should contain 2"
    assert '3' in output, "Output should contain 3"
'''
    
    return f'''from code import *
import sys
from io import StringIO

def test_prints_output():
    """Test that function produces output."""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    {func_name}(10)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    assert len(output) > 0, "Function should print something"
'''


# ============================================================
# LLM FALLBACK TEST GENERATION (IMPROVED WITH VALIDATION)
# ============================================================

def generate_llm_test_cases(func_name: str, problem_desc: str, func_info: dict) -> str:
    """FALLBACK: Use LLM to generate test cases when no pattern matches, with signature validation."""
    param_count = func_info['param_count']
    param_types = func_info.get('param_types', [])
    param_names = func_info.get('param_names', [])
    
    # Build parameter description
    param_desc = ""
    if param_count > 0:
        param_parts = []
        for i, name in enumerate(param_names):
            type_hint = param_types[i] if i < len(param_types) else 'unknown'
            param_parts.append(f"{name}: {type_hint}")
        param_desc = f"Parameters: {', '.join(param_parts)}"
    else:
        param_desc = "Parameters: none"
    
    prompt = f"""Generate 3 pytest test cases for this Python function:
Function name: {func_name}
{param_desc}
Problem: {problem_desc}

CRITICAL: The function takes exactly {param_count} parameter(s). Your test calls MUST match this.

Output ONLY in this format (use appropriate test values for the parameter types):
TEST_1: input=<values> | expected=<result>
TEST_2: input=<values> | expected=<result>
TEST_3: input=<values> | expected=<result>

Example for 2-parameter function: TEST_1: input="hello", "world" | expected=True"""

    try:
        response = test_llm.invoke(prompt)
        test_code = parse_llm_test_cases(response.content, func_info, problem_desc)
        
        # Validate the generated test code
        if validate_generated_tests(test_code, func_name, param_count):
            return test_code
        else:
            # LLM generated invalid tests, use smart fallback
            return generate_validated_fallback_test(func_info, problem_desc)
    except:
        return generate_validated_fallback_test(func_info, problem_desc)


def validate_generated_tests(test_code: str, func_name: str, expected_param_count: int) -> bool:
    """Validate that generated test code has correct function signatures."""
    # Find all function calls in the test code
    pattern = rf'{re.escape(func_name)}\s*\([^)]*\)'
    calls = re.findall(pattern, test_code)
    
    if not calls:
        return False
    
    # Check each call
    for call in calls:
        if not validate_function_call(func_name, call, expected_param_count):
            return False
    
    return True


def parse_llm_test_cases(response: str, func_info: dict, problem_desc: str) -> str:
    """Parse LLM response into pytest test code with validation."""
    func_name = func_info['name']
    param_count = func_info['param_count']
    
    test_cases = []
    lines = response.strip().split('\n')
    
    for line in lines:
        if 'TEST_' in line and '|' in line:
            try:
                parts = line.split('|')
                input_part = parts[0].split('input=')[1].strip()
                expected_part = parts[1].split('expected=')[1].strip()
                
                # Validate argument count in input_part
                arg_count = len([arg.strip() for arg in input_part.split(',') if arg.strip()])
                if arg_count == param_count:
                    test_cases.append((input_part, expected_part))
            except:
                continue
    
    if len(test_cases) < 2:
        return generate_validated_fallback_test(func_info, problem_desc)
    
    test_code = f'''from code import *

def test_llm_generated():
    """LLM-generated test cases."""
'''
    for i, (input_val, expected_val) in enumerate(test_cases, 1):
        test_code += f'    assert {func_name}({input_val}) == {expected_val}, "Test {i}"\n'
    
    return test_code


def generate_validated_fallback_test(func_info: dict, problem_desc: str) -> str:
    """Generate fallback tests with proper signature validation."""
    func_name = func_info['name']
    param_count = func_info['param_count']
    param_types = func_info.get('param_types', [])
    
    # Generate smart test values based on parameter info
    test_value_sets = generate_smart_test_values(param_count, param_types, problem_desc)
    
    test_code = f'''from code import *

def test_generated():
    """Auto-generated test cases based on function signature."""
'''
    
    for i, values in enumerate(test_value_sets[:3], 1):  # Max 3 test cases
        args = ', '.join(values)
        test_code += f'    result = {func_name}({args})\n'
        test_code += f'    assert result is not None, "Test {i}: Function should return a value"\n'
    
    return test_code


def generate_generic_fallback_test(func_name: str, param_count: int) -> str:
    """DEPRECATED: Use generate_validated_fallback_test instead."""
    if param_count == 0:
        return f'''from code import *

def test_callable():
    result = {func_name}()
    assert result is not None
'''
    elif param_count == 1:
        return f'''from code import *

def test_callable():
    result = {func_name}(10)
    assert result is not None
'''
    else:
        return f'''from code import *

def test_callable():
    result = {func_name}(5, 10)
    assert result is not None
'''


# ============================================================
# MAIN TEST GENERATION (UPDATED)
# ============================================================

def generate_tests_for_return_function(func_info: dict, problem_desc: str, code: str) -> str:
    """Generate tests for functions that return values."""
    func_name = func_info['name']
    param_count = func_info['param_count']
    problem_lower = problem_desc.lower()
    expected_type = detect_expected_param_type(code, problem_desc, func_info)
    
    # Prime CHECK
    is_prime_check = ("prime" in problem_lower and 
                     any(word in problem_lower for word in ["check", "is", "whether"]) and
                     not any(word in problem_lower for word in ["all", "list", "find all"]))
    
    returns_bool = func_info.get('return_type') and 'bool' in func_info['return_type'].lower()
    
    if is_prime_check or (returns_bool and "prime" in problem_lower):
        return f'''from code import *

def test_prime_numbers():
    assert {func_name}(7) == True, "7 is prime"
    assert {func_name}(2) == True, "2 is prime"
    assert {func_name}(11) == True, "11 is prime"

def test_not_prime():
    assert {func_name}(4) == False, "4 is not prime"
    assert {func_name}(1) == False, "1 is not prime"
    assert {func_name}(9) == False, "9 is not prime"
'''
    
    # Maximum in list
    elif "max" in problem_lower and expected_type == 'list':
        return f'''from code import *

def test_find_max():
    assert {func_name}([3, 1, 4, 1, 5, 9, 2, 6]) == 9
    assert {func_name}([1]) == 1
    assert {func_name}([-5, -2, -10]) == -2
'''
    
    # Count vowels
    elif "vowel" in problem_lower:
        return f'''from code import *

def test_count_vowels():
    assert {func_name}("hello") == 2
    assert {func_name}("aeiou") == 5
    assert {func_name}("xyz") == 0
'''
    
    # Palindrome
    elif "palindrome" in problem_lower:
        return f'''from code import *

def test_palindrome():
    assert {func_name}("radar") == True
    assert {func_name}("hello") == False
'''
    
    # Email validation
    elif "email" in problem_lower and ("valid" in problem_lower or "check" in problem_lower):
        return f'''from code import *

def test_valid_emails():
    assert {func_name}("test@example.com") == True, "Basic email"
    assert {func_name}("user.name@domain.org") == True, "Email with dot in username"

def test_invalid_emails():
    assert {func_name}("invalid") == False, "No @ symbol"
    assert {func_name}("no@domain") == False, "No TLD"
    assert {func_name}("") == False, "Empty string"
'''
    
    # Reverse string
    elif "reverse" in problem_lower and expected_type == 'str':
        return f'''from code import *

def test_reverse():
    assert {func_name}("hello") == "olleh"
    assert {func_name}("a") == "a"
'''
    
    # Sort
    elif "sort" in problem_lower and expected_type == 'list':
        return f'''from code import *

def test_sort():
    assert {func_name}([5, 2, 8, 1, 9]) == [1, 2, 5, 8, 9]
    assert {func_name}([1]) == [1]
'''
    
    # Factorial
    elif "factorial" in problem_lower:
        return f'''from code import *

def test_factorial():
    assert {func_name}(0) == 1
    assert {func_name}(5) == 120
'''
    
    # Fibonacci
    elif "fibonacci" in problem_lower or "fib" in problem_lower:
        if param_count == 1:
            # Single parameter - likely nth fibonacci
            return f'''from code import *

def test_fibonacci():
    assert {func_name}(0) == 0, "fib(0) = 0"
    assert {func_name}(1) == 1, "fib(1) = 1"
    assert {func_name}(10) == 55, "fib(10) = 55"
'''
        else:
            # Multiple parameters or returns sequence
            return f'''from code import *

def test_fibonacci_sequence():
    result = {func_name}(5)
    assert isinstance(result, list), "Should return a list"
    assert len(result) > 0, "Should return non-empty sequence"
'''
    
    # Balanced parentheses
    elif "parenthes" in problem_lower and "balanced" in problem_lower:
        return f'''from code import *

def test_balanced_parentheses():
    assert {func_name}("()") == True, "Simple balanced"
    assert {func_name}("()[]{{}}") == True, "Multiple types balanced"
    assert {func_name}("(())") == True, "Nested balanced"

def test_unbalanced_parentheses():
    assert {func_name}("(") == False, "Open only"
    assert {func_name}(")(") == False, "Wrong order"
    assert {func_name}("(()") == False, "Missing close"
'''
    
    # GCD
    elif "greatest common divisor" in problem_lower or "gcd" in problem_lower:
        return f'''from code import *

def test_gcd():
    assert {func_name}(12, 18) == 6, "GCD(12, 18) = 6"
    assert {func_name}(5, 10) == 5, "GCD(5, 10) = 5"
    assert {func_name}(7, 13) == 1, "GCD(7, 13) = 1 (coprime)"
'''
    
    # LCM
    elif "least common multiple" in problem_lower or "lcm" in problem_lower:
        return f'''from code import *

def test_lcm():
    assert {func_name}(12, 18) == 36, "LCM(12, 18) = 36"
    assert {func_name}(5, 10) == 10, "LCM(5, 10) = 10"
    assert {func_name}(3, 7) == 21, "LCM(3, 7) = 21"
'''
    
    # Longest word(s) - handles multiple words with same length
    elif "longest word" in problem_lower:
        return f'''from code import *

def test_longest_single_word():
    result = {func_name}("python")
    assert "python" in result, "Single word should be returned"
    
def test_longest_equal_length():
    result = {func_name}("hello world")
    assert isinstance(result, list), "Should return a list"
    assert len(result) == 2, "Both words have same length (5)"
    assert "hello" in result and "world" in result, "Should contain both words"
    
def test_longest_different_length():
    result = {func_name}("the quick brown fox")
    assert isinstance(result, list), "Should return a list"
    # "quick" and "brown" both have 5 letters
    assert "quick" in result and "brown" in result, "Should contain longest words"
    assert len(result[0]) == 5, "Longest words should have 5 letters"
'''
    
    # Default: LLM fallback WITH VALIDATION
    else:
        return generate_llm_test_cases(func_name, problem_desc, func_info)


# ============================================================
# MAIN TEST RUNNER
# ============================================================

def run_tests(state: AgentState) -> dict:
    """Execute the code with generated tests and return results."""
    
    problem = state["problem_description"]
    code_to_test = state["generated_code"]
    
    # Detect if this is a modification task
    is_modification = detect_modification_task(problem)
    needs_loop = detect_loop_requirement(problem)
    needs_error_handling = detect_error_handling_requirement(problem)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        
        # For modification tasks with behavioral requirements, use behavioral tests
        if is_modification and (needs_loop or needs_error_handling):
            # Don't modify input() calls for behavioral tests - we test structure
            code_path = os.path.join(tmpdir, "code.py")
            with open(code_path, "w") as f:
                f.write(code_to_test)
            
            tests = generate_behavioral_tests(code_to_test, problem)
        else:
            # Standard testing
            if 'input(' in code_to_test:
                code_to_test = make_code_testable(code_to_test, problem)
            
            code_path = os.path.join(tmpdir, "code.py")
            with open(code_path, "w") as f:
                f.write(code_to_test)
            
            func_type = detect_function_type(code_to_test, problem)
            func_info = extract_function_info(code_to_test)
            
            if func_type == 'print':
                tests = generate_tests_for_print_function(func_info, problem)
            else:
                tests = generate_tests_for_return_function(func_info, problem, code_to_test)
        
        test_path = os.path.join(tmpdir, "test_code.py")
        with open(test_path, "w") as f:
            f.write(tests)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir
            )
            
            output = result.stdout + result.stderr
            
            if result.returncode == 0:
                return {"status": "pass", "results": output}
            else:
                return {"status": "fail", "results": output}
                
        except subprocess.TimeoutExpired:
            return {"status": "fail", "results": "Test execution timed out (30 seconds)"}
        except Exception as e:
            return {"status": "fail", "results": f"Error running tests: {str(e)}"}
