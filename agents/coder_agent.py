"""
Coder Agent: Writes Python code based on specifications
"""
import os
import json
import ollama

class CoderAgent:
    def __init__(self, model_name="codellama:7b"):
        self.name = "CoderAgent"
        self.model_name = model_name
        self.attempt_count = 0
        self.max_attempts = 10
        
    def write_code(self, specification, feedback=None):
        """
        Write Python code based on specification
        
        Args:
            specification (dict): Spec from PromptAgent
            feedback (str): Optional feedback from ReviewerAgent/TesterAgent
            
        Returns:
            str: File path of generated code
        """
        self.attempt_count += 1
        
        # Create prompt for the LLM
        prompt = self._create_prompt(specification, feedback)
        
        # Generate code using Ollama
        code = self._generate_with_ollama(prompt)
        
        # Save to file
        file_path = self._save_code(code, specification['function_name'])
        
        print(f"[CoderAgent] Attempt {self.attempt_count}/{self.max_attempts}")
        print(f"[CoderAgent] Code written to: {file_path}")
        
        return file_path
    
    def _create_prompt(self, specification, feedback):
        """Create a detailed prompt for code generation"""
        prompt = f"""Write a Python function with the following specification:

Task: {specification['task']}
Function Name: {specification['function_name']}
Requirements:
"""
        for req in specification['requirements']:
            prompt += f"- {req}\n"
        
        prompt += f"\nExpected Behavior: {specification['expected_behavior']}\n"
        
        if feedback:
            prompt += f"\n### FEEDBACK FROM PREVIOUS ATTEMPT:\n{feedback}\n"
            prompt += "\nPlease fix the issues mentioned above.\n"
        
        prompt += """
### IMPORTANT INSTRUCTIONS:
1. Write ONLY the Python function code, no explanations
2. Include proper docstring
3. Handle edge cases
4. Make the code clean and readable
5. Do NOT include any markdown formatting or ```python blocks
6. Start directly with the function definition

Generate the complete, working Python function now:
"""
        
        return prompt
    
    def _generate_with_ollama(self, prompt):
        """Generate code using Ollama"""
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.2,  # Lower temperature for more deterministic code
                    "top_p": 0.9,
                }
            )
            
            code = response['response'].strip()
            
            # Clean up any markdown formatting if present
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
            
            return code
            
        except Exception as e:
            print(f"[CoderAgent] Error generating code: {e}")
            # Fallback: return a basic template
            return self._fallback_template(prompt)
    
    def _fallback_template(self, prompt):
        """Provide a basic template if LLM fails"""
        return """def solution(n):
    '''Generated function template'''
    # TODO: Implement functionality
    pass
"""
    
    def _save_code(self, code, function_name):
        """Save generated code to file"""
        # Ensure generated_code directory exists
        os.makedirs("generated_code", exist_ok=True)
        
        file_path = f"generated_code/{function_name}_attempt_{self.attempt_count}.py"
        
        with open(file_path, 'w') as f:
            f.write(code)
        
        return file_path
    
    def reset_attempts(self):
        """Reset attempt counter for new task"""
        self.attempt_count = 0


# Test the Coder Agent
if __name__ == "__main__":
    from prompt_agent import PromptAgent
    
    print("=== Testing Coder Agent ===\n")
    
    # Create agents
    prompt_agent = PromptAgent()
    coder_agent = CoderAgent()
    
    # Generate specification
    user_request = "Write a function that returns the factorial of a number"
    spec = prompt_agent.generate_specification(user_request)
    
    print(f"Specification generated: {spec['function_name']}\n")
    
    # Generate code
    file_path = coder_agent.write_code(spec)
    
    print(f"\n✓ Code generated successfully!")
    print(f"Check the file: {file_path}")
    
    # Display the generated code
    with open(file_path, 'r') as f:
        print("\n=== Generated Code ===")
        print(f.read())