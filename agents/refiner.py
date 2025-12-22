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
        
        # Detect start of code
        if not in_code and (stripped.startswith('def ') or stripped.startswith('import ') or 
                           stripped.startswith('from ') or stripped.startswith('class ')):
            in_code = True
        
        # Detect end of code (instruction-like text after code block)
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

IMPORTANT:
- Output ONLY the refined prompt in the format above
- Do NOT output these instructions
- Do NOT explain your reasoning
- Keep it concise and clear

OUTPUT:"""


def refine_prompt(state: AgentState) -> str:
    """Generate a refined version of the user's prompt."""
    raw_prompt = state["raw_prompt"]
    
    # Detect if prompt contains existing code
    if detect_existing_code(raw_prompt):
        code, instructions = extract_code_and_instructions(raw_prompt)
        
        if code:
            # For modification tasks, build a structured specification directly
            # ALWAYS preserve the exact original code - never summarize or describe it!
            
            instructions_lower = instructions.lower() if instructions else ""
            
            # Extract what user wants
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
            
            # If no specific patterns found, use the raw instructions
            if not changes and instructions:
                changes.append(instructions)
            elif not changes:
                changes.append("Modify the code as needed")
            
            # CRITICAL: Always emphasize keeping ALL original code
            rules.append("Output the COMPLETE code - include EVERY function from the original")
            rules.append("Keep ALL helper functions (is_prime, calculate, etc.) EXACTLY as they are")
            rules.append("Only modify the specific parts mentioned in MODIFICATIONS REQUESTED")
            
            # Build specification with COMPLETE original code preserved
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
        else:
            # No valid code extracted, use LLM
            prompt = REFINER_PROMPT_NEW.format(raw_prompt=raw_prompt)
            response = llm.invoke(prompt)
            return response.content.strip()
    else:
        # New code request, use LLM
        prompt = REFINER_PROMPT_NEW.format(raw_prompt=raw_prompt)
        response = llm.invoke(prompt)
        return response.content.strip()
