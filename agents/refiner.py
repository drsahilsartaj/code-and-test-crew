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
                'invalid', 'letter', 'negative', 'exception'
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
            # Don't rely on LLM to format it - do it ourselves for reliability!
            
            instructions_lower = instructions.lower() if instructions else ""
            
            # Extract what user wants
            changes = []
            rules = []
            
            if 'endless' in instructions_lower or 'loop' in instructions_lower or 'keep asking' in instructions_lower:
                changes.append("Add endless while True loop in main() that keeps asking for input")
                rules.append("Use while True: for the endless loop")
                rules.append("Use print() to show results, NOT return (return exits the loop!)")
            
            if 'error' in instructions_lower or 'handle' in instructions_lower or 'letter' in instructions_lower or 'invalid' in instructions_lower:
                changes.append("Add try/except to handle invalid input like letters")
                rules.append("Use try/except ValueError to catch non-numeric input")
            
            if 'negative' in instructions_lower:
                changes.append("Handle negative numbers with appropriate error message")
                rules.append("Check if number < 0 or < 2 and show error message")
            
            if 'quit' in instructions_lower or 'exit' in instructions_lower or 'stop' in instructions_lower:
                changes.append("Add way for user to quit (e.g., type 'quit')")
                rules.append("Check for quit command before processing number")
            
            if not changes:
                changes.append(instructions if instructions else "Improve the code")
            
            # Always add these rules for modification tasks
            if not rules:
                rules.append("Keep original function logic")
            rules.append("Keep the original is_prime() (or other core function) unchanged")
            
            # Build specification
            spec = f"""MODIFICATION TASK

EXISTING CODE TO MODIFY:
```python
{code}
```

CHANGES REQUESTED:
"""
            for i, change in enumerate(changes, 1):
                spec += f"{i}. {change}\n"
            
            spec += "\nCRITICAL RULES FOR IMPLEMENTATION:\n"
            for rule in rules:
                spec += f"- {rule}\n"
            
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
