"""Prompt Refiner Agent - Clarifies user requirements before code generation."""
from langchain_ollama import ChatOllama
from utils.state import AgentState
import re

llm = ChatOllama(model="codellama:7b-instruct-q4_0", temperature=0.3)


def detect_existing_code(prompt: str) -> bool:
    """Detect if the prompt contains existing Python code."""
    code_indicators = [
        r'def \w+\s*\(',
        r'class \w+',
        r'if __name__\s*==',
        r'import \w+',
        r'from \w+ import',
    ]
    
    for pattern in code_indicators:
        if re.search(pattern, prompt, re.MULTILINE):
            return True
    return False


def extract_code_and_instructions(prompt: str) -> tuple:
    """
    Split prompt into (code, instructions).
    Returns (None, prompt) if no code found.
    """
    lines = prompt.split('\n')
    code_lines = []
    instruction_lines = []
    
    in_code = False
    code_ended = False
    
    for line in lines:
        stripped = line.strip()
        
        if not in_code and (stripped.startswith('def ') or stripped.startswith('import ') or 
                           stripped.startswith('from ') or stripped.startswith('class ')):
            in_code = True
        
        if in_code and not code_ended:
            is_instruction = (
                len(stripped) > 20 and
                not stripped.startswith(('#', 'def ', 'class ', 'import ', 'from ', 'if ', 'for ', 
                                        'while ', 'return ', 'print', '    ', '\t', '@', '"""', "'''")) and
                not '=' in stripped[:15] and
                not stripped.endswith(':') and
                not stripped.startswith((')', ']', '}'))
            )
            
            instruction_keywords = [
                'change', 'modify', 'add', 'fix', 'update', 'make', 'want', 'please', 
                'can you', 'could you', 'i need', 'handle', 'also', 'dont', "don't", 
                'keep', 'endless', 'loop', 'continuously', 'error', 'edge case',
                'invalid', 'letter', 'negative', 'exception', 'repeatedly', 'again'
            ]
            
            if is_instruction and any(word in stripped.lower() for word in instruction_keywords):
                code_ended = True
        
        if not code_ended and in_code:
            code_lines.append(line)
        elif code_ended or (not in_code and stripped):
            instruction_lines.append(line)
    
    code = '\n'.join(code_lines).strip()
    instructions = '\n'.join(instruction_lines).strip()
    
    if code and detect_existing_code(code):
        return code, instructions
    return None, prompt


# ============================================================
# PROMPT TYPE DETECTION - Standardize output types
# ============================================================

def detect_check_task(prompt: str) -> bool:
    """Detect if this is a check/validation task that should return boolean."""
    prompt_lower = prompt.lower()
    check_patterns = [
        'check if', 'checks if', 'check whether',
        'is prime', 'is even', 'is odd', 'is palindrome', 'is leap',
        'is valid', 'is anagram', 'is armstrong',
        'whether', 'or not', 'true or false', 'true/false',
        'determine if', 'verify if', 'test if',
    ]
    return any(p in prompt_lower for p in check_patterns)


def detect_count_task(prompt: str) -> bool:
    """Detect if this is a counting task."""
    prompt_lower = prompt.lower()
    count_patterns = ['count', 'how many', 'number of']
    return any(p in prompt_lower for p in count_patterns)


def detect_find_task(prompt: str) -> bool:
    """Detect if this is a find/search task."""
    prompt_lower = prompt.lower()
    find_patterns = ['find', 'smallest', 'largest', 'minimum', 'maximum', 'search']
    return any(p in prompt_lower for p in find_patterns)


def detect_calculate_task(prompt: str) -> bool:
    """Detect if this is a calculation task."""
    prompt_lower = prompt.lower()
    calc_patterns = ['calculate', 'compute', 'factorial', 'fibonacci', 'sum', 'gcd', 'lcm']
    return any(p in prompt_lower for p in calc_patterns)


def get_standardized_output(prompt: str) -> str:
    """
    Get standardized output specification based on task type.
    This ensures consistent return types across all prompts.
    """
    prompt_lower = prompt.lower()
    
    # Check/validation tasks -> Always boolean
    if detect_check_task(prompt):
        if 'prime' in prompt_lower:
            return "Boolean True if the number is prime, False otherwise"
        elif 'even' in prompt_lower:
            return "Boolean True if even, False if odd"
        elif 'odd' in prompt_lower:
            return "Boolean True if odd, False if even"
        elif 'palindrome' in prompt_lower:
            return "Boolean True if palindrome, False otherwise"
        elif 'leap' in prompt_lower:
            return "Boolean True if leap year, False otherwise"
        elif 'valid' in prompt_lower:
            return "Boolean True if valid, False otherwise"
        elif 'anagram' in prompt_lower:
            return "Boolean True if anagrams, False otherwise"
        else:
            return "Boolean True or False"
    
    # Count tasks -> Integer
    if detect_count_task(prompt):
        return "Integer count"
    
    # Find tasks -> Depends on context
    if detect_find_task(prompt):
        if 'string' in prompt_lower or 'text' in prompt_lower:
            return "The found string or substring"
        else:
            return "The found number/value"
    
    # Calculate tasks -> Number
    if detect_calculate_task(prompt):
        return "The calculated numeric result"
    
    # Default
    return "The result value"


def get_function_name(prompt: str) -> str:
    """Generate appropriate function name from prompt."""
    prompt_lower = prompt.lower()
    
    if 'prime' in prompt_lower:
        if detect_check_task(prompt):
            return "is_prime"
        return "find_primes"
    elif 'even' in prompt_lower or 'odd' in prompt_lower:
        return "is_even" if 'even' in prompt_lower else "is_odd"
    elif 'palindrome' in prompt_lower:
        return "is_palindrome"
    elif 'leap' in prompt_lower:
        return "is_leap_year"
    elif 'factorial' in prompt_lower:
        return "factorial"
    elif 'fibonacci' in prompt_lower:
        return "fibonacci"
    elif 'vowel' in prompt_lower:
        return "count_vowels"
    elif 'gcd' in prompt_lower:
        return "gcd"
    elif 'lcm' in prompt_lower:
        return "lcm"
    elif 'smallest' in prompt_lower or 'minimum' in prompt_lower:
        return "find_min"
    elif 'largest' in prompt_lower or 'maximum' in prompt_lower:
        return "find_max"
    elif 'sort' in prompt_lower:
        return "sort_list"
    elif 'reverse' in prompt_lower:
        return "reverse_string"
    elif 'valid' in prompt_lower and 'email' in prompt_lower:
        return "validate_email"
    elif 'anagram' in prompt_lower:
        return "is_anagram"
    
    return "process"


# ============================================================
# REFINER PROMPT TEMPLATE
# ============================================================

REFINER_PROMPT_NEW = """You are a Prompt Refiner Agent. Take the user's programming request and output a clear problem description.

User's raw prompt: {raw_prompt}

OUTPUT FORMAT:
```
FUNCTION: [name]
PURPOSE: [what it does]
INPUT: [parameters and types]
OUTPUT: [return value and type]
EDGE CASES: [what to handle]
```

IMPORTANT RULES:
1. For "check if", "is X", "whether", "or not" type tasks -> OUTPUT MUST be: Boolean True/False
2. For counting tasks -> OUTPUT MUST be: Integer
3. For calculation tasks -> OUTPUT MUST be: Numeric result
4. Do NOT use string returns like "prime"/"not prime" - use Boolean True/False instead
5. Keep it concise and clear

OUTPUT:"""


def refine_prompt(state: AgentState) -> str:
    """Generate a refined version of the user's prompt."""
    raw_prompt = state["raw_prompt"]
    
    # Detect if prompt contains existing code (modification task)
    if detect_existing_code(raw_prompt):
        code, instructions = extract_code_and_instructions(raw_prompt)
        
        if code:
            return build_modification_spec(code, instructions)
        else:
            return refine_new_prompt(raw_prompt)
    else:
        return refine_new_prompt(raw_prompt)


def refine_new_prompt(raw_prompt: str) -> str:
    """Refine a new code request (no existing code)."""
    
    # For simple well-known tasks, generate standardized spec directly
    # This avoids LLM inconsistency
    if is_well_known_task(raw_prompt):
        return generate_standardized_spec(raw_prompt)
    
    # For complex/unknown tasks, use LLM
    prompt = REFINER_PROMPT_NEW.format(raw_prompt=raw_prompt)
    response = llm.invoke(prompt)
    refined = response.content.strip()
    
    # Post-process to ensure boolean output for check tasks
    if detect_check_task(raw_prompt):
        refined = enforce_boolean_output(refined, raw_prompt)
    
    return refined


def is_well_known_task(prompt: str) -> bool:
    """Check if this is a well-known programming task."""
    prompt_lower = prompt.lower()
    
    well_known = [
        'prime', 'factorial', 'fibonacci', 'palindrome',
        'leap year', 'even', 'odd', 'vowel', 'gcd', 'lcm',
        'smallest', 'largest', 'sort', 'reverse',
        'anagram', 'balanced', 'parenthes', 'perfect square',
        'roman', 'password', 'all prime', 'less than',
        'email', 'binary', 'decimal', 'flatten', 'quicksort',
        'merge sort', 'sum', 'average', 'occurrence', 'duplicate',
        'digit', 'second largest', 'count word', 'uppercase', 'longest word'
    ]
    
    return any(task in prompt_lower for task in well_known)


def generate_standardized_spec(prompt: str) -> str:
    """Generate standardized specification for well-known tasks."""
    prompt_lower = prompt.lower()
    func_name = get_function_name(prompt)
    output_type = get_standardized_output(prompt)
    
    # Prime factors - MUST BE BEFORE prime check
    if 'prime' in prompt_lower and 'factor' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Return all prime factors of a number as a list.
INPUT: A positive integer (n: int)
OUTPUT: A list of prime factors in ascending order, with repetition
EDGE CASES: Numbers less than 2 should return empty list."""
    
    if 'prime' in prompt_lower and ('all' in prompt_lower or 'less than' in prompt_lower):
        return f"""FUNCTION: {func_name}
PURPOSE: Find all prime numbers less than n.
INPUT: A positive integer (n: int)
OUTPUT: A list of all prime numbers less than n
ALGORITHM: Use Sieve of Eratosthenes or iterate and check each number for primality.
EDGE CASES: n <= 2 returns empty list."""

    # Prime check
    if 'prime' in prompt_lower and detect_check_task(prompt):
        return f"""FUNCTION: {func_name}
PURPOSE: Check if a number is prime.
INPUT: A positive integer (n: int)
OUTPUT: {output_type}
EDGE CASES: Numbers less than 2 should return False."""

    # Factorial
    if 'factorial' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Calculate the factorial of a number.
INPUT: A non-negative integer (n: int)
OUTPUT: The factorial value (int)
EDGE CASES: factorial(0) = 1, factorial(1) = 1."""

    # Fibonacci
    if 'fibonacci' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Calculate the nth Fibonacci number.
INPUT: A non-negative integer (n: int)
OUTPUT: The nth Fibonacci number (int)
EDGE CASES: fib(0) = 0, fib(1) = 1."""

    # Balanced parentheses - MUST BE BEFORE palindrome (both have 'check')
    if 'balanced' in prompt_lower or 'parenthes' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Check if parentheses/brackets in a string are balanced using a STACK algorithm.
INPUT: A string containing parentheses, brackets, or braces (s: str)
OUTPUT: {output_type}
ALGORITHM: Use a stack data structure:
  1. For each character in string:
     - If opening bracket (, [, {{ -> push to stack
     - If closing bracket ), ], }} -> pop from stack and check if it matches
     - If no match or stack empty when closing -> return False
  2. After loop, return True only if stack is empty
EDGE CASES: 
  - Empty string returns True
  - '([)]' returns False (interleaved - wrong order)
  - '([])' returns True (properly nested)"""

    # Palindrome
    if 'palindrome' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Check if a string is a palindrome.
INPUT: A string (s: str)
OUTPUT: {output_type}
EDGE CASES: Single character and empty string are palindromes."""

    # Leap year
    if 'leap' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Check if a year is a leap year.
INPUT: A year (year: int)
OUTPUT: {output_type}
EDGE CASES: Divisible by 4, but not 100 unless also 400."""

    # Perfect square - MUST BE BEFORE even/odd (both can have 'check')
    if 'perfect' in prompt_lower and 'square' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Check if a number is a perfect square.
INPUT: A non-negative integer (n: int)
OUTPUT: {output_type}
ALGORITHM: Take square root and check if it's a whole number.
EDGE CASES: 0 and 1 are perfect squares."""

    # Even/Odd
    if ('even' in prompt_lower or 'odd' in prompt_lower) and 'balanced' not in prompt_lower:
        check_type = "even" if 'even' in prompt_lower else "odd"
        return f"""FUNCTION: {func_name}
PURPOSE: Check if a number is {check_type}.
INPUT: An integer (n: int)
OUTPUT: {output_type}
EDGE CASES: Zero is even."""

    # Count vowels
    if 'vowel' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Count the number of vowels in a string.
INPUT: A string (s: str)
OUTPUT: Integer count of vowels
EDGE CASES: Empty string returns 0. Consider both upper and lower case."""

    # GCD
    if 'gcd' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Find the greatest common divisor of two numbers.
INPUT: Two positive integers (a: int, b: int)
OUTPUT: The GCD (int)
EDGE CASES: GCD(a, 0) = a."""

    # LCM
    if 'lcm' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Find the least common multiple of two numbers.
INPUT: Two positive integers (a: int, b: int)
OUTPUT: The LCM (int)
EDGE CASES: Use GCD to calculate: LCM(a,b) = a*b/GCD(a,b)."""

    # Password validation
    if 'password' in prompt_lower and 'valid' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Check if password meets security requirements.
INPUT: A string (password: str)
OUTPUT: {output_type}
REQUIREMENTS: At least 8 characters, one uppercase, one lowercase, one digit, one special character.
EDGE CASES: Empty string returns False."""

    # Roman numeral
    if 'roman' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Convert a Roman numeral string to an integer.
INPUT: A string representing a Roman numeral (s: str)
OUTPUT: Integer value
ALGORITHM: Map each symbol to value (I=1, V=5, X=10, L=50, C=100, D=500, M=1000). If smaller value precedes larger, subtract it.
EDGE CASES: Handle invalid characters with error."""

    # Find smallest
    if 'smallest' in prompt_lower or 'minimum' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Find the smallest number in a collection.
INPUT: A string of space-separated numbers (numbers: str)
OUTPUT: The smallest number (int)
EDGE CASES: Handle empty input with error message."""

    # Find largest
    if 'largest' in prompt_lower or 'maximum' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Find the largest number in a collection.
INPUT: A string of space-separated numbers (numbers: str)
OUTPUT: The largest number (int)
EDGE CASES: Handle empty input with error message."""

    # Quicksort - MUST BE BEFORE generic sort
    if 'quicksort' in prompt_lower or 'quick sort' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Sort a list using quicksort algorithm.
INPUT: A list of numbers (arr: list)
OUTPUT: Sorted list in ascending order
ALGORITHM: Choose pivot, partition into less/greater, recursively sort.
EDGE CASES: Empty list returns empty list."""
    
    # Merge sort - MUST BE BEFORE generic sort
    if 'merge' in prompt_lower and 'sort' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Sort a list using merge sort algorithm.
INPUT: A list of numbers (arr: list)
OUTPUT: Sorted list in ascending order
ALGORITHM: Divide list in half, recursively sort, merge sorted halves.
EDGE CASES: Empty list returns empty list."""
    
    # Sort (generic)
    if 'sort' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Sort a list of numbers.
INPUT: A list of numbers (nums: list)
OUTPUT: Sorted list in ascending order
EDGE CASES: Empty list returns empty list."""

    # Reverse string
    if 'reverse' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Reverse a string.
INPUT: A string (s: str)
OUTPUT: The reversed string
EDGE CASES: Empty string returns empty string."""

    # Anagram
    if 'anagram' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Check if two strings are anagrams.
INPUT: Two strings (s1: str, s2: str)
OUTPUT: {output_type}
EDGE CASES: Ignore case and spaces."""
    
    # Email validation
    if 'email' in prompt_lower and ('valid' in prompt_lower or 'check' in prompt_lower):
        return f"""FUNCTION: {func_name}
PURPOSE: Check if a string is a valid email address.
INPUT: A string (email: str)
OUTPUT: {output_type}
ALGORITHM: Check for @ symbol, valid username, valid domain with TLD.
EDGE CASES: Empty string returns False."""

    # Binary to decimal
    if 'binary' in prompt_lower and 'decimal' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Convert a binary string to decimal integer.
INPUT: A string of 0s and 1s (binary: str)
OUTPUT: Integer decimal value
ALGORITHM: Use int(binary, 2) or manual conversion.
EDGE CASES: "0" returns 0."""

    # Flatten nested list
    if 'flatten' in prompt_lower and 'list' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Flatten a nested list into a single list.
INPUT: A nested list (nested: list)
OUTPUT: A flat list with all elements
ALGORITHM: Use recursion or itertools.chain.
EDGE CASES: Empty list returns empty list."""

    # Sum of list
    if 'sum' in prompt_lower and ('list' in prompt_lower or 'number' in prompt_lower):
        return f"""FUNCTION: {func_name}
PURPOSE: Calculate the sum of all numbers in a list.
INPUT: A list of numbers (nums: list)
OUTPUT: Integer or float sum
EDGE CASES: Empty list returns 0."""

    # Average of list
    if 'average' in prompt_lower or 'avg' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Calculate the average of numbers in a list.
INPUT: A list of numbers (nums: list)
OUTPUT: Float average value
EDGE CASES: Empty list should handle division by zero."""

    # Count character occurrences
    if 'count' in prompt_lower and ('occurrence' in prompt_lower or 'character' in prompt_lower) and 'vowel' not in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Count occurrences of a character in a string.
INPUT: A string and a character (s: str, char: str)
OUTPUT: Integer count
EDGE CASES: Character not found returns 0."""

    # Remove duplicates
    if 'remove' in prompt_lower and 'duplicate' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Remove duplicate elements from a list.
INPUT: A list (lst: list)
OUTPUT: List with unique elements only
ALGORITHM: Use set or iterate and check.
EDGE CASES: Empty list returns empty list."""

    # Check digits only
    if 'digit' in prompt_lower and ('only' in prompt_lower or 'check' in prompt_lower or 'contain' in prompt_lower):
        return f"""FUNCTION: {func_name}
PURPOSE: Check if a string contains only digits.
INPUT: A string (s: str)
OUTPUT: {output_type}
ALGORITHM: Use str.isdigit() or regex.
EDGE CASES: Empty string returns False."""

    # Second largest
    if 'second' in prompt_lower and ('largest' in prompt_lower or 'maximum' in prompt_lower):
        return f"""FUNCTION: {func_name}
PURPOSE: Find the second largest number in a list.
INPUT: A list of numbers (nums: list)
OUTPUT: The second largest number (int or float)
ALGORITHM: Sort and return second from end, or track two largest.
EDGE CASES: List with less than 2 elements should handle error."""

    # Count words
    if 'count' in prompt_lower and 'word' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Count the number of words in a string.
INPUT: A string (s: str)
OUTPUT: Integer count of words
ALGORITHM: Split by whitespace and count.
EDGE CASES: Empty string returns 0."""

    # Convert to uppercase
    if 'uppercase' in prompt_lower or 'upper case' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Convert a string to uppercase.
INPUT: A string (s: str)
OUTPUT: Uppercase string
ALGORITHM: Use str.upper().
EDGE CASES: Empty string returns empty string."""

    # Longest word
    if 'longest' in prompt_lower and 'word' in prompt_lower:
        return f"""FUNCTION: {func_name}
PURPOSE: Find the longest word in a string.
INPUT: A string (s: str)
OUTPUT: The longest word (str)
ALGORITHM: Split by whitespace, compare lengths.
EDGE CASES: Single word returns that word."""

    # Fallback - use LLM
    prompt_template = REFINER_PROMPT_NEW.format(raw_prompt=prompt)
    response = llm.invoke(prompt_template)
    return response.content.strip()

def enforce_boolean_output(refined: str, original_prompt: str) -> str:
    """Ensure the refined prompt specifies boolean output for check tasks."""
    lines = refined.split('\n')
    new_lines = []
    
    for line in lines:
        if line.strip().startswith('OUTPUT:'):
            # Check if it already has boolean
            if 'bool' not in line.lower() and 'true' not in line.lower() and 'false' not in line.lower():
                # Replace with boolean output
                standardized = get_standardized_output(original_prompt)
                new_lines.append(f"OUTPUT: {standardized}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)


def build_modification_spec(code: str, instructions: str) -> str:
    """Build specification for code modification tasks."""
    instructions_lower = instructions.lower() if instructions else ""
    
    changes = []
    rules = []
    
    # Detect specific change patterns
    if 'endless' in instructions_lower or 'loop' in instructions_lower or 'keep asking' in instructions_lower or 'repeatedly' in instructions_lower:
        changes.append("Add endless while True loop in main() that keeps asking for input")
        rules.append("Use while True: for the endless loop")
        rules.append("Use print() to show results, NOT return (return exits the loop!)")
    
    if 'error' in instructions_lower or 'handle' in instructions_lower or 'letter' in instructions_lower or 'invalid' in instructions_lower:
        changes.append("Add try/except to handle invalid input like letters")
        rules.append("Use try/except ValueError to catch non-numeric input")
    
    if 'negative' in instructions_lower or 'positive' in instructions_lower:
        changes.append("Handle negative numbers with appropriate error message")
        rules.append("Check if number < 0 or < 2 and show error message")
    
    if 'quit' in instructions_lower or 'exit' in instructions_lower or 'stop' in instructions_lower:
        changes.append("Add way for user to quit (e.g., type 'quit')")
        rules.append("Check for quit command before processing number")
    
    if not changes and instructions:
        changes.append(instructions)
    elif not changes:
        changes.append("Modify the code as needed")
    
    rules.append("Output the COMPLETE code - include EVERY function from the original")
    rules.append("Keep ALL helper functions (is_prime, calculate, etc.) EXACTLY as they are")
    rules.append("Only modify the specific parts mentioned in MODIFICATIONS REQUESTED")
    
    spec = f"""MODIFICATION TASK

EXISTING CODE TO KEEP:
```python
{code}
```

MODIFICATIONS REQUESTED:
"""
    for i, change in enumerate(changes, 1):
        spec += f"{i}. {change}\n"
    
    spec += """
CRITICAL RULES - READ CAREFULLY:
"""
    for rule in rules:
        spec += f"- {rule}\n"
    
    spec += """
EXAMPLE - If original has is_prime() and main(), output BOTH:
```python
def is_prime(n: int) -> bool:
    # KEEP THIS FUNCTION COMPLETELY UNCHANGED
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def main():
    # ONLY THIS FUNCTION GETS MODIFIED
    while True:
        ...


if __name__ == "__main__":
    main()
```
"""
    
    return spec