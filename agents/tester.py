"""Tester Agent - Executes code and runs tests with generic code analysis."""

import subprocess
import sys
import tempfile
import os
import re
import ast
from utils.state import AgentState
from langchain_ollama import ChatOllama

test_llm = ChatOllama(model="codellama:7b-instruct-q4_0", temperature=0.2)


# ============================================================
# GENERIC CODE ANALYSIS - Determines input type from actual code
# ============================================================

def analyze_code_input_expectations(code: str, func_info: dict) -> dict:
    """
    Analyze the ACTUAL CODE to determine what input type the function expects.
    """
    if not func_info or not code:
        return {'input_type': 'unknown', 'confidence': 'low', 'reason': 'No code provided'}
    
    param_names = func_info.get('param_names', [])
    if not param_names:
        return {'input_type': 'unknown', 'confidence': 'low', 'reason': 'No parameters'}
    
    first_param = param_names[0]
    code_lower = code.lower()
    first_param_lower = first_param.lower()
    
    # PATTERN 1: String split patterns
    split_patterns = [
        f'{first_param_lower}.split(',
        f'{first_param_lower}.split()',
        f'{first_param_lower}.strip(',
        f'{first_param_lower}.strip().',
    ]
    for pattern in split_patterns:
        if pattern in code_lower:
            return {
                'input_type': 'str_numbers',
                'confidence': 'high',
                'reason': f'Code uses {pattern} - expects space-separated string'
            }
    
    if '.split' in code_lower and ('int(' in code_lower or 'float(' in code_lower):
        return {
            'input_type': 'str_numbers',
            'confidence': 'high',
            'reason': 'Code splits string and converts to numbers'
        }
    
    # PATTERN 2: Direct list operations
    list_funcs = ['min(', 'max(', 'sum(', 'sorted(', 'len(', 'enumerate(']
    for func in list_funcs:
        if f'{func}{first_param_lower})' in code_lower or f'{func}{first_param_lower},' in code_lower:
            if '.split' not in code_lower:
                return {
                    'input_type': 'list',
                    'confidence': 'high',
                    'reason': f'Code uses {func} directly on parameter'
                }
    
    if re.search(rf'{re.escape(first_param_lower)}\s*\[', code_lower):
        if '.split' not in code_lower:
            return {
                'input_type': 'list',
                'confidence': 'medium',
                'reason': 'Code uses indexing on parameter'
            }
    
    if f'for ' in code_lower and f' in {first_param_lower}' in code_lower:
        if '.split' not in code_lower:
            return {
                'input_type': 'list',
                'confidence': 'medium',
                'reason': 'Code iterates over parameter'
            }
    
    # PATTERN 3: String text operations
    str_methods = ['.lower()', '.upper()', '.replace(', '.count(', '.find(', '[::-1]', '.isalpha()', '.isdigit()']
    for method in str_methods:
        if f'{first_param_lower}{method}' in code_lower:
            return {
                'input_type': 'str_text',
                'confidence': 'high',
                'reason': f'Code uses string method {method}'
            }
    
    # PATTERN 4: Numeric operations
    numeric_ops = ['%', '//', '/', '**', '*', '<', '>', '<=', '>=', '==']
    for op in numeric_ops:
        if f'{first_param_lower} {op}' in code_lower or f'{first_param_lower}{op}' in code_lower:
            return {
                'input_type': 'int',
                'confidence': 'high',
                'reason': f'Code uses numeric operator {op}'
            }
    
    if f'range({first_param_lower}' in code_lower or f'range(1, {first_param_lower}' in code_lower or f'range(2, {first_param_lower}' in code_lower:
        return {
            'input_type': 'int',
            'confidence': 'high',
            'reason': 'Code uses parameter in range()'
        }
    
    # PATTERN 5: Type hints
    param_types = func_info.get('param_types', [])
    if param_types and param_types[0] != 'unknown':
        hint = param_types[0].lower()
        if 'list' in hint or '[' in hint:
            return {
                'input_type': 'list',
                'confidence': 'high',
                'reason': f'Type hint: {param_types[0]}'
            }
        elif 'str' in hint:
            if 'int(' in code_lower or 'float(' in code_lower:
                return {
                    'input_type': 'str_numbers',
                    'confidence': 'high',
                    'reason': 'Type hint str with number conversion'
                }
            return {
                'input_type': 'str_text',
                'confidence': 'high',
                'reason': f'Type hint: {param_types[0]}'
            }
        elif 'int' in hint:
            return {
                'input_type': 'int',
                'confidence': 'high',
                'reason': f'Type hint: {param_types[0]}'
            }
        elif 'float' in hint:
            return {
                'input_type': 'float',
                'confidence': 'high',
                'reason': f'Type hint: {param_types[0]}'
            }
    
    # PATTERN 6: Parameter name inference (EXACT MATCH ONLY)
    list_names = ['numbers', 'nums', 'arr', 'array', 'items', 'elements', 'data', 'values', 'lst', 'list']
    if first_param_lower in list_names:
        return {
            'input_type': 'list',
            'confidence': 'medium',
            'reason': f'Parameter name "{first_param}" suggests list'
        }
    
    string_names = ['s', 'text', 'string', 'word', 'sentence', 'str', 'input_str']
    if first_param_lower in string_names:
        return {
            'input_type': 'str_text',
            'confidence': 'medium',
            'reason': f'Parameter name "{first_param}" suggests string'
        }
    
    int_names = ['n', 'num', 'number', 'x', 'y', 'count', 'size', 'limit', 'max_val', 'min_val']
    if first_param_lower in int_names:
        return {
            'input_type': 'int',
            'confidence': 'medium',
            'reason': f'Parameter name "{first_param}" suggests integer'
        }
    
    return {'input_type': 'unknown', 'confidence': 'low', 'reason': 'Could not determine input type'}


def get_test_values_for_type(input_type: str, problem_desc: str = "") -> list:
    """Generate appropriate test values based on detected input type."""
    problem_lower = problem_desc.lower()
    
    if input_type == 'str_numbers':
        return [['"3 1 4 1 5 9"'], ['"1 2 3 4 5"'], ['"-5 -2 0 3 10"']]
    
    elif input_type == 'list':
        return [['[3, 1, 4, 1, 5, 9]'], ['[1, 2, 3, 4, 5]'], ['[-5, -2, 0, 3, 10]']]
    
    elif input_type == 'str_text':
        if 'palindrome' in problem_lower:
            return [['"radar"'], ['"hello"'], ['"a"']]
        elif 'vowel' in problem_lower:
            return [['"hello"'], ['"aeiou"'], ['"xyz"']]
        elif 'reverse' in problem_lower:
            return [['"hello"'], ['"python"'], ['"a"']]
        else:
            return [['"hello"'], ['"test"'], ['"python"']]
    
    elif input_type == 'int':
        if 'prime' in problem_lower:
            return [['7'], ['2'], ['10'], ['1']]
        elif 'factorial' in problem_lower:
            return [['5'], ['0'], ['1'], ['10']]
        elif 'fibonacci' in problem_lower or 'fib' in problem_lower:
            return [['10'], ['0'], ['1'], ['5']]
        elif 'leap' in problem_lower and 'year' in problem_lower:
            return [['2000'], ['1900'], ['2024'], ['2100']]
        elif 'even' in problem_lower or 'odd' in problem_lower:
            return [['4'], ['7'], ['0'], ['1']]
        else:
            return [['5'], ['10'], ['0'], ['1']]
    
    elif input_type == 'float':
        return [['3.14'], ['0.0'], ['-2.5'], ['1.0']]
    
    return [['5'], ['10'], ['0']]


# ============================================================
# FUNCTION DETECTION UTILITIES
# ============================================================

def detect_function_type(code: str, problem_desc: str) -> str:
    """Detect if function primarily prints output or returns values."""
    func_bodies = re.findall(r'def\s+(\w+)\s*\([^)]*\):[^\n]*\n((?:\s{4,}.*\n)*)', code)
    
    for func_name, body in func_bodies:
        if func_name != 'main':
            has_print = 'print(' in body
            has_return = re.search(r'\n\s+return\s+', body) is not None
            
            if has_print and not has_return:
                return 'print'
            elif has_return:
                return 'return'
    
    return 'return'


def detect_modification_task(problem: str) -> bool:
    """Check if this is a code modification task."""
    indicators = ['EXISTING CODE', 'MODIFICATIONS REQUESTED', 'MODIFICATION TASK', 'modify the']
    return any(i.lower() in problem.lower() for i in indicators)


def detect_loop_requirement(problem: str) -> bool:
    """Check if problem requires continuous loop."""
    keywords = ['endless', 'keep asking', 'continuously', 'repeatedly', 'loop until', 'while true', 'infinite loop']
    return any(k in problem.lower() for k in keywords)


def detect_error_handling_requirement(problem: str) -> bool:
    """Check if problem requires error handling."""
    keywords = ['handle', 'edge case', 'invalid input', 'error', 'exception', 'valueerror', 'try/except']
    return any(k in problem.lower() for k in keywords)


# ============================================================
# FUNCTION INFO EXTRACTION
# ============================================================

def extract_function_info(code: str) -> dict:
    """Extract function signature information using AST with regex fallback."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name not in ['main', '__init__'] and not node.name.startswith('_'):
                    param_types = []
                    for arg in node.args.args:
                        if arg.annotation:
                            param_types.append(ast.unparse(arg.annotation))
                        else:
                            param_types.append('unknown')
                    
                    return_type = ast.unparse(node.returns) if node.returns else None
                    
                    return {
                        'name': node.name,
                        'param_count': len(node.args.args),
                        'param_names': [arg.arg for arg in node.args.args],
                        'param_types': param_types,
                        'return_type': return_type
                    }
    except:
        pass
    
    # Regex fallback
    match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?:', code)
    if match and match.group(1) != 'main':
        func_name = match.group(1)
        params_str = match.group(2)
        return_type = match.group(3).strip() if match.group(3) else None
        
        params = [p.strip() for p in params_str.split(',') if p.strip()]
        param_names = []
        param_types = []
        
        for p in params:
            if ':' in p:
                name, ptype = p.split(':', 1)
                param_names.append(name.strip())
                param_types.append(ptype.strip())
            else:
                param_names.append(p.strip())
                param_types.append('unknown')
        
        return {
            'name': func_name,
            'param_count': len(params),
            'param_names': param_names,
            'param_types': param_types,
            'return_type': return_type
        }
    
    return {
        'name': 'unknown',
        'param_count': 0,
        'param_names': [],
        'param_types': [],
        'return_type': None
    }


# ============================================================
# SMART TEST VALUE GENERATION
# ============================================================

def generate_smart_test_values(param_count: int, param_types: list, problem_desc: str, code: str = None, func_info: dict = None) -> list:
    """Generate test values using code analysis."""
    if param_count == 0:
        return [[]]
    problem_lower = problem_desc.lower()

    if 'prime' in problem_lower and ('all' in problem_lower or 'less than' in problem_lower):
        return [['10'], ['20'], ['30']]
        
    if param_count == 1 and code and func_info:
        analysis = analyze_code_input_expectations(code, func_info)
        print(f"[Tester] Code analysis: {analysis['reason']} -> {analysis['input_type']} ({analysis['confidence']})")
        
        if analysis['input_type'] != 'unknown':
            return get_test_values_for_type(analysis['input_type'], problem_desc)
    
    if param_count == 1:
        problem_lower = problem_desc.lower()
        if any(k in problem_lower for k in ['prime', 'factorial', 'fibonacci', 'even', 'odd', 'leap', 'number']):
            return get_test_values_for_type('int', problem_desc)
        elif any(k in problem_lower for k in ['palindrome', 'vowel', 'reverse', 'string', 'text', 'word']):
            return get_test_values_for_type('str_text', problem_desc)
        elif any(k in problem_lower for k in ['smallest', 'largest', 'sort', 'max', 'min', 'sum', 'list', 'array']):
            return get_test_values_for_type('list', problem_desc)
        return get_test_values_for_type('int', problem_desc)
    
    if param_count == 2:
        problem_lower = problem_desc.lower()
        if 'gcd' in problem_lower or 'lcm' in problem_lower:
            return [['12', '18'], ['5', '10'], ['7', '3']]
        elif 'anagram' in problem_lower:
            return [['"listen"', '"silent"'], ['"hello"', '"world"']]
        elif 'count' in problem_lower and ('occurrence' in problem_lower or 'character' in problem_lower):
            return [['"hello"', '"l"'], ['"aaa"', '"a"'], ['"test"', '"z"']]
        else:
            return [['2', '3'], ['5', '10'], ['0', '1']]
    
    return [[str(i + 1) for i in range(param_count)]]


# ============================================================
# PRE-VALIDATION
# ============================================================

def pre_validate_code(code: str, problem_desc: str) -> dict:
    """Run quick sanity checks before formal testing."""
    func_info = extract_function_info(code)
    
    try:
        ast.parse(code)
    except SyntaxError as e:
        return {
            'valid': False,
            'reason': f"Syntax error on line {e.lineno}: {e.msg}",
            'suggestions': ["Fix the syntax error", "Check for missing colons, parentheses, or indentation"]
        }
    
    return try_execute_function(code, func_info, problem_desc)


def try_execute_function(code: str, func_info: dict, problem_desc: str) -> dict:
    """Try executing the function with generated test values."""
    func_name = func_info['name']
    if func_name == 'unknown':
        return {'valid': False, 'reason': "Could not find function", 'suggestions': ["Define a function"]}
    
    test_values = generate_smart_test_values(
        func_info['param_count'],
        func_info.get('param_types', []),
        problem_desc,
        code,
        func_info
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = os.path.join(tmpdir, "test_code.py")
        
        with open(code_path, "w") as f:
            f.write(code)
            f.write("\n\nif __name__ == '__main__':\n")
            for i, vals in enumerate(test_values[:3]):
                args = ', '.join(vals)
                f.write(f"    try:\n")
                f.write(f"        result_{i} = {func_name}({args})\n")
                f.write(f"        print(f'TEST_{i}_PASS: {{type(result_{i}).__name__}}')\n")
                f.write(f"    except Exception as e:\n")
                f.write(f"        print(f'TEST_{i}_FAIL: {{e}}')\n")
        
        try:
            result = subprocess.run(
                [sys.executable, code_path],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=tmpdir
            )
            
            output = result.stdout + result.stderr
            
            if '_FAIL' in output:
                errors = [line for line in output.split('\n') if 'FAIL' in line][:3]
                return {
                    'valid': False,
                    'reason': f"Function execution failed:\n" + '\n'.join(errors),
                    'suggestions': ["Check function logic", "Verify parameter handling"]
                }
            
            if '_PASS' not in output:
                return {
                    'valid': False,
                    'reason': f"No output from function. Output: {output[:200]}",
                    'suggestions': ["Check function returns a value", "Verify function is callable"]
                }
            
            return {'valid': True, 'reason': "Pre-validation passed", 'suggestions': []}
            
        except subprocess.TimeoutExpired:
            return {
                'valid': False,
                'reason': "Function timed out (possible infinite loop)",
                'suggestions': ["Check for infinite loops", "Verify loop termination conditions"]
            }
        except Exception as e:
            return {
                'valid': False,
                'reason': f"Execution error: {str(e)}",
                'suggestions': ["Check for runtime errors"]
            }


# ============================================================
# TEST CODE PREPARATION
# ============================================================

def make_code_testable(code: str, problem_desc: str) -> str:
    """Replace input() calls with test values for testing."""
    lines = code.split('\n')
    modified_lines = []
    
    for line in lines:
        input_match = re.match(r'(\s*)(\w+)\s*=\s*(int|float|str)?\(?\s*input\(', line)
        
        if input_match:
            indent = input_match.group(1)
            var_name = input_match.group(2)
            cast_type = input_match.group(3)
            
            modified_lines.append(f"{indent}# {line.strip()}  # [COMMENTED FOR TESTING]")
            
            if cast_type == 'int':
                test_val = '10'
            elif cast_type == 'float':
                test_val = '5.0'
            else:
                test_val = '"test"'
            
            modified_lines.append(f"{indent}{var_name} = {test_val}  # [TEST VALUE]")
        else:
            modified_lines.append(line)
    
    return '\n'.join(modified_lines)


# ============================================================
# BEHAVIORAL TESTS (for modification tasks)
# ============================================================

def generate_behavioral_tests(code: str, problem_desc: str) -> str:
    """Generate tests that check code structure/behavior for modification tasks."""
    needs_loop = detect_loop_requirement(problem_desc)
    needs_error_handling = detect_error_handling_requirement(problem_desc)
    
    test_code = '''from code import *
import inspect

'''
    
    if needs_loop:
        test_code += '''def test_has_while_true_loop():
    """Check that code contains a while True loop."""
    source = inspect.getsource(main)
    assert "while True" in source or "while true" in source.lower(), \\
        "Code should have while True loop"

def test_uses_print_in_loop():
    """Check that loop uses print to show results."""
    source = inspect.getsource(main)
    assert "print(" in source, "Code should use print() to show results"

'''
    
    if needs_error_handling:
        test_code += '''def test_has_try_except():
    """Check that code has error handling."""
    source = inspect.getsource(main)
    assert "try:" in source and "except" in source, \\
        "Code should have try/except for error handling"

'''
    
    test_code += '''def test_code_is_valid():
    """Basic validity check."""
    assert True, "Code structure is valid"
'''
    
    return test_code


# ============================================================
# TEST GENERATION FOR PRINT FUNCTIONS
# ============================================================

def generate_tests_for_print_function(func_info: dict, problem_desc: str, code: str) -> str:
    """Generate tests for functions that print output."""
    func_name = func_info['name']
    
    analysis = analyze_code_input_expectations(code, func_info)
    test_values = get_test_values_for_type(analysis['input_type'], problem_desc)
    
    arg = test_values[0][0] if test_values and test_values[0] else '10'
    
    return f'''from code import *
import sys
from io import StringIO

def test_function_prints_output():
    """Test that function produces output."""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        {func_name}({arg})
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    
    assert len(output) > 0, "Function should print something"
'''


# ============================================================
# TEST GENERATION FOR RETURN FUNCTIONS (WITH CASE-INSENSITIVE CHECKS)
# ============================================================

def generate_tests_for_return_function(func_info: dict, problem_desc: str, code: str) -> str:
    """Generate tests for functions that return values."""
    func_name = func_info['name']
    problem_lower = problem_desc.lower()
    
    analysis = analyze_code_input_expectations(code, func_info)
    input_type = analysis['input_type']
    
    print(f"[Tester] Generating tests for {func_name} - input type: {input_type} ({analysis['reason']})")
    
    # ===== PATTERN-BASED TESTS =====

    is_check_task = any(w in problem_lower for w in ["check if", "is prime", "whether", "determine if", "is a prime"])
    is_all_primes = any(w in problem_lower for w in ["all prime", "all primes", "find all", "primes less", "primes under", "primes below", "primes smaller"])
    
    # Prime factors - MUST BE BEFORE prime check
    if "prime" in problem_lower and "factor" in problem_lower:
        return f'''from code import *

def test_prime_factors():
    assert {func_name}(12) == [2, 2, 3], "12 = 2*2*3"
    assert {func_name}(7) == [7], "7 is prime"
    assert {func_name}(100) == [2, 2, 5, 5], "100 = 2*2*5*5"
'''

    if "prime" in problem_lower and is_all_primes and not is_check_task:
        return f'''from code import *

def test_primes_less_than():
    result = {func_name}(10)
    assert isinstance(result, list), "Should return a list"
    assert 2 in result, "2 is prime"
    assert 3 in result, "3 is prime"
    assert 5 in result, "5 is prime"
    assert 7 in result, "7 is prime"
    assert 4 not in result, "4 is not prime"

def test_primes_less_than_20():
    result = {func_name}(20)
    assert 11 in result, "11 is prime"
    assert 13 in result, "13 is prime"
    assert 17 in result, "17 is prime"
    assert 19 in result, "19 is prime"
'''
    
    # Prime number check
    if "prime" in problem_lower and any(w in problem_lower for w in ["check", "is", "whether", "determine"]):
        return_type = func_info.get('return_type', '')
        if return_type and 'str' in return_type.lower():
            return f'''from code import *

def test_prime_numbers():
    result = {func_name}(7)
    assert isinstance(result, str), "Should return a string"
    assert "not" not in result.lower(), "7 is prime, should not contain 'not'"
    assert "prime" in result.lower(), "7 is prime"

def test_prime_2():
    result = {func_name}(2)
    assert isinstance(result, str), "Should return a string"
    assert "not" not in result.lower(), "2 is prime, should not contain 'not'"

def test_not_prime_numbers():
    result = {func_name}(4)
    assert isinstance(result, str), "Should return a string"
    assert "not" in result.lower(), "4 is not prime"

def test_not_prime_1():
    result = {func_name}(1)
    assert isinstance(result, str), "Should return a string"
    assert "not" in result.lower(), "1 is not prime"
'''
        return f'''from code import *

def test_prime_numbers():
    assert {func_name}(7) == True, "7 is prime"
    assert {func_name}(2) == True, "2 is prime"

def test_not_prime_numbers():
    assert {func_name}(4) == False, "4 is not prime"
    assert {func_name}(1) == False, "1 is not prime"
'''
    
    # Factorial
    if "factorial" in problem_lower:
        return f'''from code import *

def test_factorial():
    assert {func_name}(0) == 1, "0! = 1"
    assert {func_name}(1) == 1, "1! = 1"
    assert {func_name}(5) == 120, "5! = 120"
'''
    
    # Fibonacci
    if "fibonacci" in problem_lower or "fib" in problem_lower:
        return f'''from code import *

def test_fibonacci():
    assert {func_name}(0) == 0, "fib(0) = 0"
    assert {func_name}(1) == 1, "fib(1) = 1"
    assert {func_name}(10) == 55, "fib(10) = 55"
'''
    
    # Leap year
    if "leap" in problem_lower and "year" in problem_lower:
        return_type = func_info.get('return_type', '')
        if return_type and 'str' in return_type.lower():
            return f'''from code import *

def test_leap_year():
    result = {func_name}(2000)
    assert "leap" in str(result).lower() or result == True, "2000 is leap year"

def test_not_leap_year():
    result = {func_name}(1900)
    assert "not" in str(result).lower() or result == False, "1900 is not leap year"
'''
        return f'''from code import *

def test_leap_year():
    assert {func_name}(2000) == True, "2000 is leap year"
    assert {func_name}(2024) == True, "2024 is leap year"

def test_not_leap_year():
    assert {func_name}(1900) == False, "1900 is not leap year"
    assert {func_name}(2023) == False, "2023 is not leap year"
'''
    # Balanced parentheses check - MUST BE BEFORE even/odd
    if "balanced" in problem_lower or ("parenthes" in problem_lower and "check" in problem_lower):
        return f'''from code import *

def test_balanced():
    assert {func_name}("()") == True, "() is balanced"
    assert {func_name}("()[]{{}}") == True, "()[]{{}} is balanced"
    assert {func_name}("([])") == True, "([]) is balanced"

def test_not_balanced():
    assert {func_name}("(]") == False, "(] is not balanced"
    assert {func_name}("([)]") == False, "([)] is not balanced"
    assert {func_name}("(") == False, "( is not balanced"
'''
    # Even/Odd
    if ("even" in problem_lower or "odd" in problem_lower) and "balanced" not in problem_lower:
        return f'''from code import *

def test_even():
    result = {func_name}(4)
    assert result == True or "even" in str(result).lower(), "4 is even"

def test_odd():
    result = {func_name}(7)
    assert result == False or "odd" in str(result).lower(), "7 is odd"
'''
    
    # Palindrome
    if "palindrome" in problem_lower:
        return_type = func_info.get('return_type', '')
        if return_type and 'str' in return_type.lower():
            return f'''from code import *

def test_palindrome():
    result = {func_name}("radar")
    assert result == True or "yes" in str(result).lower() or "palindrome" in str(result).lower(), "radar is palindrome"

def test_not_palindrome():
    result = {func_name}("hello")
    assert result == False or "no" in str(result).lower() or "not" in str(result).lower(), "hello is not palindrome"
'''
        return f'''from code import *

def test_palindrome():
    assert {func_name}("radar") == True, "radar is palindrome"
    assert {func_name}("hello") == False, "hello is not palindrome"
'''
    
    # Count vowels
    if "vowel" in problem_lower and "count" in problem_lower:
        return f'''from code import *

def test_count_vowels():
    assert {func_name}("hello") == 2, "hello has 2 vowels"
    assert {func_name}("xyz") == 0, "xyz has 0 vowels"
'''
    
    # GCD
    if "gcd" in problem_lower:
        return f'''from code import *

def test_gcd():
    assert {func_name}(12, 18) == 6, "GCD(12,18) = 6"
    assert {func_name}(7, 3) == 1, "GCD(7,3) = 1"
'''
    
    # LCM
    if "lcm" in problem_lower:
        return f'''from code import *

def test_lcm():
    assert {func_name}(12, 18) == 36, "LCM(12,18) = 36"
'''
    
    # Password validation
    if "password" in problem_lower and "valid" in problem_lower:
        return f'''from code import *

def test_valid_password():
    assert {func_name}("Abcd123!") == True, "Valid password"
    assert {func_name}("Abcd1234@") == True, "Valid password with @"

def test_invalid_password():
    assert {func_name}("abc") == False, "Too short"
    assert {func_name}("abcdefgh") == False, "No uppercase, digit, special"
    assert {func_name}("ABCDEFGH") == False, "No lowercase, digit, special"
    assert {func_name}("Abcdefgh") == False, "No digit, special"
    assert {func_name}("Abcdefg1") == False, "No special character"
'''
    # Perfect square check - MUST BE BEFORE min/smallest
    if "perfect" in problem_lower and "square" in problem_lower:
        return f'''from code import *

def test_perfect_square():
    assert {func_name}(16) == True, "16 is perfect square"
    assert {func_name}(25) == True, "25 is perfect square"
    assert {func_name}(1) == True, "1 is perfect square"

def test_not_perfect_square():
    assert {func_name}(15) == False, "15 is not perfect square"
    assert {func_name}(2) == False, "2 is not perfect square"
'''
    
    # Find smallest/minimum
    if any(w in problem_lower for w in ["smallest", "minimum", "min"]) and \
       not any(w in problem_lower for w in ["password", "validate", "length", "characters", "square"]):
        if input_type == 'str_numbers':
            return f'''from code import *

def test_find_smallest():
    assert {func_name}("3 1 4 1 5 9") == 1, "Smallest in '3 1 4 1 5 9' is 1"
    assert {func_name}("-5 -2 0 3") == -5, "Smallest in '-5 -2 0 3' is -5"
'''
        return f'''from code import *

def test_find_smallest():
    assert {func_name}([3, 1, 4, 1, 5, 9]) == 1, "Smallest in list is 1"
    assert {func_name}([-5, -2, 0, 3]) == -5, "Smallest is -5"
'''
    
    # Find largest/maximum
    if any(w in problem_lower for w in ["largest", "maximum", "max"]):
        if input_type == 'str_numbers':
            return f'''from code import *

def test_find_largest():
    assert {func_name}("3 1 4 1 5 9") == 9, "Largest in '3 1 4 1 5 9' is 9"
'''
        return f'''from code import *

def test_find_largest():
    assert {func_name}([3, 1, 4, 1, 5, 9]) == 9, "Largest in list is 9"
'''
    
    # Quicksort
    if "quicksort" in problem_lower or "quick sort" in problem_lower:
        return f'''from code import *

def test_quicksort():
    assert {func_name}([5, 2, 8, 1, 9]) == [1, 2, 5, 8, 9], "Sort ascending"
    assert {func_name}([1]) == [1], "Single element"
    assert {func_name}([]) == [], "Empty list"
'''
    # Merge sort
    if "merge" in problem_lower and "sort" in problem_lower:
        return f'''from code import *

def test_merge_sort():
    assert {func_name}([5, 2, 8, 1, 9]) == [1, 2, 5, 8, 9], "Sort ascending"
    assert {func_name}([1]) == [1], "Single element"
    assert {func_name}([]) == [], "Empty list"
'''
    if "sort" in problem_lower:
        return f'''from code import *

def test_sort():
    assert {func_name}([5, 2, 8, 1, 9]) == [1, 2, 5, 8, 9], "Should sort ascending"
'''
    
    # Reverse string
    if "reverse" in problem_lower and input_type == 'str_text':
        return f'''from code import *

def test_reverse():
    assert {func_name}("hello") == "olleh", "Should reverse string"
'''
    
    # Roman numeral conversion
    if "roman" in problem_lower:
        return f'''from code import *

def test_roman_to_int():
    assert {func_name}("III") == 3, "III = 3"
    assert {func_name}("IV") == 4, "IV = 4"
    assert {func_name}("IX") == 9, "IX = 9"
    assert {func_name}("LVIII") == 58, "LVIII = 58"
    assert {func_name}("MCMXCIV") == 1994, "MCMXCIV = 1994"
'''
    
    # Anagram check
    if "anagram" in problem_lower:
        return f'''from code import *

def test_anagram():
    assert {func_name}("listen", "silent") == True, "listen/silent are anagrams"
    assert {func_name}("hello", "world") == False, "hello/world are not anagrams"
'''
    # Email validation
    if "email" in problem_lower and ("valid" in problem_lower or "check" in problem_lower):
        return f'''from code import *

def test_valid_email():
    assert {func_name}("test@example.com") == True, "Valid email"
    assert {func_name}("user.name@domain.org") == True, "Valid with dot"

def test_invalid_email():
    assert {func_name}("invalid") == False, "No @ symbol"
    assert {func_name}("@domain.com") == False, "No username"
    assert {func_name}("test@") == False, "No domain"
'''

    # Binary to decimal
    if "binary" in problem_lower and "decimal" in problem_lower:
        return f'''from code import *

def test_binary_to_decimal():
    assert {func_name}("1010") == 10, "1010 = 10"
    assert {func_name}("1111") == 15, "1111 = 15"
    assert {func_name}("1000") == 8, "1000 = 8"
    assert {func_name}("0") == 0, "0 = 0"
'''

    # Flatten nested list
    if "flatten" in problem_lower and "list" in problem_lower:
        return f'''from code import *

def test_flatten():
    assert {func_name}([[1, 2], [3, 4]]) == [1, 2, 3, 4], "Simple nested"
    assert {func_name}([[1], [2, 3], [4]]) == [1, 2, 3, 4], "Uneven nested"
    assert {func_name}([]) == [], "Empty list"
'''


    # Sum of list
    if "sum" in problem_lower and ("list" in problem_lower or "number" in problem_lower):
        return f'''from code import *

def test_sum():
    assert {func_name}([1, 2, 3, 4, 5]) == 15, "Sum is 15"
    assert {func_name}([10]) == 10, "Single element"
    assert {func_name}([]) == 0, "Empty list"
'''

    # Average of list
    if "average" in problem_lower or "avg" in problem_lower:
        return f'''from code import *

def test_average():
    assert {func_name}([1, 2, 3, 4, 5]) == 3, "Average is 3"
    assert {func_name}([10, 20]) == 15, "Average is 15"
'''

    # Count character occurrences
    if "count" in problem_lower and ("occurrence" in problem_lower or "character" in problem_lower) and "vowel" not in problem_lower:
        return f'''from code import *

def test_count_char():
    assert {func_name}("hello", "l") == 2, "l appears 2 times"
    assert {func_name}("aaa", "a") == 3, "a appears 3 times"
    assert {func_name}("hello", "z") == 0, "z appears 0 times"
'''

    # Remove duplicates
    if "remove" in problem_lower and "duplicate" in problem_lower:
        return f'''from code import *

def test_remove_duplicates():
    result = {func_name}([1, 2, 2, 3, 3, 3])
    assert len(result) == 3, "Should have 3 unique elements"
    assert 1 in result and 2 in result and 3 in result, "Should contain 1, 2, 3"
'''

    # Check digits only
    if "digit" in problem_lower and ("only" in problem_lower or "check" in problem_lower or "contain" in problem_lower):
        return f'''from code import *

def test_digits_only():
    assert {func_name}("12345") == True, "Only digits"
    assert {func_name}("123a45") == False, "Contains letter"
    assert {func_name}("") == False, "Empty string"
'''

    # Second largest
    if "second" in problem_lower and ("largest" in problem_lower or "maximum" in problem_lower or "biggest" in problem_lower):
        return f'''from code import *

def test_second_largest():
    assert {func_name}([1, 2, 3, 4, 5]) == 4, "Second largest is 4"
    assert {func_name}([10, 20, 30]) == 20, "Second largest is 20"
'''

    # Count words
    if "count" in problem_lower and "word" in problem_lower:
        return f'''from code import *

def test_count_words():
    assert {func_name}("hello world") == 2, "Two words"
    assert {func_name}("one") == 1, "One word"
    assert {func_name}("this is a test") == 4, "Four words"
'''

    # Convert to uppercase
    if "uppercase" in problem_lower or "upper case" in problem_lower:
        return f'''from code import *

def test_uppercase():
    assert {func_name}("hello") == "HELLO", "Convert to uppercase"
    assert {func_name}("Hello World") == "HELLO WORLD", "Mixed case"
'''

    # Longest word
    if "longest" in problem_lower and "word" in problem_lower:
        return f'''from code import *

def test_longest_word():
    assert {func_name}("the quick brown fox") == "quick" or {func_name}("the quick brown fox") == "brown", "Longest is quick or brown (5 chars)"
    assert {func_name}("hello") == "hello", "Single word"
'''
    
    # ===== SMART FALLBACK: Based on return type and code analysis =====
    print(f"[Tester] No pattern match - using smart fallback for {func_name}")
    
    test_values = generate_smart_test_values(
        func_info['param_count'],
        func_info.get('param_types', []),
        problem_desc,
        code,
        func_info
    )
    
    first_arg = test_values[0][0] if test_values and test_values[0] else '"test"'
    
    return_type = func_info.get('return_type', '') or ''
    return_type_lower = return_type.lower()
    
    # Check code patterns to determine return type
    has_list_return = ('list' in return_type_lower or 
                       '[]' in return_type or 
                       '.append(' in code or 
                       'return []' in code or
                       'return sorted(' in code)
    
    has_bool_return = ('bool' in return_type_lower or 
                       'return True' in code or 
                       'return False' in code)
    
    has_int_return = ('int' in return_type_lower or 
                      'return 0' in code or 
                      'return 1' in code or
                      'return len(' in code or
                      'return sum(' in code)
    
    has_str_return = ('str' in return_type_lower and 'list' not in return_type_lower)
    
    # Generate appropriate test based on detected return type
    if has_list_return:
        return f'''from code import *

def test_returns_list():
    result = {func_name}({first_arg})
    assert result is not None, "Should not return None"
    assert isinstance(result, list), "Should return a list"
'''
    
    if has_bool_return:
        return f'''from code import *

def test_returns_boolean():
    result = {func_name}({first_arg})
    assert result is not None, "Should not return None"
    assert isinstance(result, bool), "Should return True or False"
'''
    
    if has_str_return:
        return f'''from code import *

def test_returns_string():
    result = {func_name}({first_arg})
    assert result is not None, "Should not return None"
    assert isinstance(result, str), "Should return a string"
'''
    
    if has_int_return:
        return f'''from code import *

def test_returns_number():
    result = {func_name}({first_arg})
    assert result is not None, "Should not return None"
    assert isinstance(result, (int, float)), "Should return a number"
'''
    
    # Ultimate fallback
    return f'''from code import *

def test_function_returns_value():
    result = {func_name}({first_arg})
    assert result is not None, "Should return a value"

def test_function_callable():
    try:
        result = {func_name}({first_arg})
        assert True, "Function executed successfully"
    except TypeError as e:
        assert False, f"Function call failed: {{e}}"
'''

# ============================================================
# MAIN TEST RUNNER
# ============================================================

def run_tests(state: AgentState) -> dict:
    """Main entry point - runs tests on generated code."""
    problem = state["problem_description"]
    code_to_test = state["generated_code"]
    
    is_modification = detect_modification_task(problem)
    needs_loop = detect_loop_requirement(problem)
    
    skip_prevalidation = is_modification and needs_loop
    
    if not skip_prevalidation:
        print("[Tester] Running pre-validation...")
        validation_result = pre_validate_code(code_to_test, problem)
        
        if not validation_result['valid']:
            print(f"[Tester] ❌ Pre-validation FAILED: {validation_result['reason']}")
            return {
                "status": "fail",
                "results": f"""PRE-VALIDATION FAILED:
{validation_result['reason']}

Suggestions:
{chr(10).join('  • ' + s for s in validation_result['suggestions'])}
"""
            }
        print("[Tester] ✅ Pre-validation PASSED")
    else:
        print("[Tester] ⏭️ Skipping pre-validation (interactive loop task)")
    
    needs_error_handling = detect_error_handling_requirement(problem)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        if is_modification and (needs_loop or needs_error_handling):
            tests = generate_behavioral_tests(code_to_test, problem)
        else:
            if 'input(' in code_to_test:
                code_to_test = make_code_testable(code_to_test, problem)
            
            func_info = extract_function_info(code_to_test)
            func_type = detect_function_type(code_to_test, problem)
            
            if func_type == 'print':
                tests = generate_tests_for_print_function(func_info, problem, state["generated_code"])
            else:
                tests = generate_tests_for_return_function(func_info, problem, state["generated_code"])
        
        code_path = os.path.join(tmpdir, "code.py")
        test_path = os.path.join(tmpdir, "test_code.py")
        
        with open(code_path, "w") as f:
            f.write(code_to_test)
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
                print("[Tester] ✅ All tests PASSED!")
                return {"status": "pass", "results": output}
            else:
                print("[Tester] ❌ Tests failed")
                return {"status": "fail", "results": output}
                
        except subprocess.TimeoutExpired:
            return {"status": "fail", "results": "Test execution timed out (30 seconds)"}
        except Exception as e:
            return {"status": "fail", "results": f"Error running tests: {str(e)}"}