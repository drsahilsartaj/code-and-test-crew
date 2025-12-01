"""
Tester Agent: Executes and tests Python code
"""
import subprocess
import os
import sys
import importlib.util

class TesterAgent:
    def __init__(self):
        self.name = "TesterAgent"
        
    def test_code(self, file_path, specification):
        """
        Test the generated code
        
        Args:
            file_path (str): Path to the Python file to test
            specification (dict): Original specification with requirements
            
        Returns:
            dict: Test results
        """
        print(f"\n[TesterAgent] Testing: {file_path}")
        
        if not os.path.exists(file_path):
            return {
                "passed": False,
                "errors": [f"File not found: {file_path}"],
                "feedback": f"Error: Cannot test - file {file_path} does not exist"
            }
        
        # Run syntax check first
        syntax_ok, syntax_error = self._check_syntax(file_path)
        if not syntax_ok:
            return {
                "passed": False,
                "errors": [f"Syntax Error: {syntax_error}"],
                "feedback": f"Code has syntax errors:\n{syntax_error}\n\nPlease fix the syntax and try again."
            }
        
        # Run functional tests
        test_results = self._run_functional_tests(file_path, specification)
        
        return test_results
    
    def _check_syntax(self, file_path):
        """Check if the code has valid Python syntax"""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            compile(code, file_path, 'exec')
            return True, None
            
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def _run_functional_tests(self, file_path, specification):
        """Run functional tests based on the specification"""
        function_name = specification['function_name']
        errors = []
        passed_tests = []
        
        try:
            # Import the module dynamically
            spec = importlib.util.spec_from_file_location("test_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get the function
            if not hasattr(module, function_name):
                errors.append(f"Function '{function_name}' not found in the code")
                return {
                    "passed": False,
                    "errors": errors,
                    "feedback": f"Error: Function '{function_name}' is not defined in the code."
                }
            
            func = getattr(module, function_name)
            
            # Run tests based on function type
            test_cases = self._get_test_cases(function_name, specification)
            
            for test_input, expected_output, description in test_cases:
                try:
                    result = func(test_input)
                    if result == expected_output:
                        passed_tests.append(f"✓ {description}: PASSED")
                    else:
                        errors.append(f"✗ {description}: Expected {expected_output}, got {result}")
                except Exception as e:
                    errors.append(f"✗ {description}: Runtime error - {str(e)}")
            
        except Exception as e:
            errors.append(f"Error importing/executing code: {str(e)}")
        
        # Generate results
        passed = len(errors) == 0
        
        feedback = self._generate_test_feedback(passed, passed_tests, errors)
        
        result = {
            "passed": passed,
            "errors": errors,
            "passed_tests": passed_tests,
            "feedback": feedback
        }
        
        print(f"[TesterAgent] Tests complete - {'PASSED' if passed else 'FAILED'}")
        print(f"[TesterAgent] Passed: {len(passed_tests)}, Failed: {len(errors)}")
        
        return result
    
    def _get_test_cases(self, function_name, specification):
        """Get test cases from specification or generate default ones"""
        
        # First, try to use AI-generated test cases from specification
        if 'test_cases' in specification and specification['test_cases']:
            test_cases = []
            for tc in specification['test_cases']:
                test_input = tc.get('input')
                expected_output = tc.get('expected_output')
                description = tc.get('description', f"Test with input {test_input}")
                test_cases.append((test_input, expected_output, description))
            
            print(f"[TesterAgent] Using {len(test_cases)} AI-generated test cases")
            return test_cases
        
        # Fallback to keyword-based test cases if AI didn't generate any
        print(f"[TesterAgent] Using fallback test cases")
        test_cases = []
        
        # Factorial tests
        if "factorial" in function_name.lower():
            test_cases = [
                (0, 1, "factorial(0)"),
                (1, 1, "factorial(1)"),
                (5, 120, "factorial(5)"),
                (6, 720, "factorial(6)"),
                (10, 3628800, "factorial(10)"),
            ]
        
        # Fibonacci tests
        elif "fibonacci" in function_name.lower():
            test_cases = [
                (0, 0, "fibonacci(0)"),
                (1, 1, "fibonacci(1)"),
                (5, 5, "fibonacci(5)"),
                (10, 55, "fibonacci(10)"),
            ]
        
        # Prime number tests
        elif "prime" in function_name.lower():
            test_cases = [
                (2, True, "is_prime(2)"),
                (3, True, "is_prime(3)"),
                (4, False, "is_prime(4)"),
                (17, True, "is_prime(17)"),
                (20, False, "is_prime(20)"),
            ]
        
        # Palindrome tests
        elif "palindrome" in function_name.lower():
            test_cases = [
                ("racecar", True, "palindrome('racecar')"),
                ("hello", False, "palindrome('hello')"),
                ("A man a plan a canal Panama", True, "palindrome with spaces"),
                ("", True, "empty string"),
                ("a", True, "single character"),
            ]
        
        # Sum tests
        elif "sum" in function_name.lower():
            test_cases = [
                ([1, 2, 3], 6, "sum([1,2,3])"),
                ([10, 20, 30], 60, "sum([10,20,30])"),
                ([], 0, "sum([])"),
            ]
        
        # Reverse string tests
        elif "reverse" in function_name.lower():
            test_cases = [
                ("hello", "olleh", "reverse('hello')"),
                ("python", "nohtyp", "reverse('python')"),
                ("", "", "reverse('')"),
            ]
        
        # Default generic tests
        else:
            test_cases = [
                (5, None, "Basic test with input 5"),
            ]
        
        return test_cases


    def _generate_test_feedback(self, passed, passed_tests, errors):
        """Generate feedback based on test results"""
        if passed:
            feedback = "✓ All tests passed!\n\n"
            feedback += "Passed tests:\n"
            for test in passed_tests:
                feedback += f"  {test}\n"
            return feedback
        
        feedback = "✗ Tests failed!\n\n"
        
        if passed_tests:
            feedback += f"Passed tests ({len(passed_tests)}):\n"
            for test in passed_tests:
                feedback += f"  {test}\n"
            feedback += "\n"
        
        feedback += f"Failed tests ({len(errors)}):\n"
        for error in errors:
            feedback += f"  {error}\n"
        
        feedback += "\nPlease fix the errors and try again."
        
        return feedback


# Test the Tester Agent
if __name__ == "__main__":
    from prompt_agent import PromptAgent
    from coder_agent import CoderAgent
    
    print("=== Testing Tester Agent ===\n")
    
    # Create agents
    prompt_agent = PromptAgent()
    coder_agent = CoderAgent()
    tester_agent = TesterAgent()
    
    # Generate code
    user_request = "Write a function that returns the factorial of a number"
    spec = prompt_agent.generate_specification(user_request)
    file_path = coder_agent.write_code(spec)
    
    # Test the code
    test_result = tester_agent.test_code(file_path, spec)
    
    print("\n=== Test Results ===")
    print(f"Passed: {test_result['passed']}")
    print(f"\nFeedback:\n{test_result['feedback']}")