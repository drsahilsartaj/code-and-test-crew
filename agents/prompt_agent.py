"""
Prompt Agent: AI-powered specification generator using Ollama
"""
import ollama
import json
import re

class PromptAgent:
    def __init__(self, model_name="codellama:7b"):
        self.name = "PromptAgent"
        self.model_name = model_name
    
    def generate_specification(self, user_request):
        """
        Uses AI to analyze request and generate detailed specification
        
        Args:
            user_request (str): The user's description of what they want
            
        Returns:
            dict: A structured specification for the coder
        """
        print(f"[PromptAgent] Analyzing request with AI...")
        
        # Use Ollama to generate specification
        spec_data = self._generate_spec_with_ai(user_request)
        
        specification = {
            "task": user_request,
            "requirements": spec_data.get("requirements", ["Implement the requested functionality"]),
            "function_name": spec_data.get("function_name", "solution"),
            "expected_behavior": spec_data.get("expected_behavior", f"Function should: {user_request}"),
            "test_cases": spec_data.get("test_cases", [])
        }
        
        print(f"[PromptAgent] Generated function name: {specification['function_name']}")
        print(f"[PromptAgent] Generated {len(specification['test_cases'])} test cases")
        
        return specification
    
    def _generate_spec_with_ai(self, user_request):
        """Use Ollama to generate specification details"""
        
        prompt = f"""You are a software specification expert. Analyze this coding request and provide a structured specification.

User Request: {user_request}

Generate a JSON response with:
1. function_name: A descriptive snake_case function name (e.g., "calculate_factorial", "is_palindrome")
2. requirements: List of 3-5 specific requirements
3. expected_behavior: One sentence describing what the function does
4. test_cases: List of 5 test cases as objects with "input", "expected_output", and "description"

CRITICAL INSTRUCTIONS:
- Output ONLY valid JSON, nothing else
- Do not include any markdown formatting or code blocks
- Do not include any explanatory text before or after the JSON
- The response must start with {{ and end with }}

Example format:
{{
  "function_name": "is_prime",
  "requirements": ["Check if number is prime", "Handle edge cases", "Return boolean"],
  "expected_behavior": "Determines if a number is prime",
  "test_cases": [
    {{"input": 2, "expected_output": true, "description": "2 is prime"}},
    {{"input": 4, "expected_output": false, "description": "4 is not prime"}},
    {{"input": 17, "expected_output": true, "description": "17 is prime"}},
    {{"input": 1, "expected_output": false, "description": "1 is not prime"}},
    {{"input": 0, "expected_output": false, "description": "0 is not prime"}}
  ]
}}

Now generate the specification for: {user_request}

Remember: Output ONLY the JSON object, no other text."""

        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "top_p": 0.9,
                }
            )
            
            response_text = response['response'].strip()
            
            # Clean up response - remove markdown formatting if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Try to extract JSON if there's extra text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_text = json_match.group(0)
            
            # Parse the JSON
            spec_data = json.loads(response_text)
            
            return spec_data
            
        except json.JSONDecodeError as e:
            print(f"[PromptAgent] Warning: Failed to parse AI response as JSON: {e}")
            print(f"[PromptAgent] Response was: {response_text[:200]}...")
            return self._fallback_specification(user_request)
        except Exception as e:
            print(f"[PromptAgent] Warning: AI generation failed: {e}")
            return self._fallback_specification(user_request)
    
    def _fallback_specification(self, user_request):
        """Fallback specification if AI fails"""
        return {
            "function_name": "solution",
            "requirements": [
                "Implement the requested functionality",
                "Handle edge cases appropriately",
                "Return appropriate value"
            ],
            "expected_behavior": f"Function should: {user_request}",
            "test_cases": []
        }


# Test the intelligent Prompt Agent
if __name__ == "__main__":
    agent = PromptAgent()
    
    print("=== Testing Intelligent Prompt Agent ===\n")
    
    # Test various requests
    test_requests = [
        "Write a function that checks if a string is a palindrome",
        "Write a function that returns the factorial of a number",
        "Write a function that finds the largest number in a list",
        "Write a function that converts Celsius to Fahrenheit"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {request}")
        print('='*80)
        
        spec = agent.generate_specification(request)
        
        print(f"\nFunction Name: {spec['function_name']}")
        print(f"\nRequirements:")
        for req in spec['requirements']:
            print(f"  - {req}")
        print(f"\nExpected Behavior: {spec['expected_behavior']}")
        print(f"\nTest Cases ({len(spec['test_cases'])}):")
        for tc in spec['test_cases'][:3]:  # Show first 3
            print(f"  - Input: {tc.get('input')}, Expected: {tc.get('expected_output')}")