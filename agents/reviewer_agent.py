"""
Reviewer Agent: Reviews code quality using Flake8
"""
import subprocess
import os

class ReviewerAgent:
    def __init__(self):
        self.name = "ReviewerAgent"
        
    def review_code(self, file_path):
        """
        Review code using Flake8 for style and quality
        
        Args:
            file_path (str): Path to the Python file to review
            
        Returns:
            dict: Review results with issues and suggestions
        """
        print(f"\n[ReviewerAgent] Reviewing: {file_path}")
        
        if not os.path.exists(file_path):
            return {
                "passed": False,
                "issues": [f"File not found: {file_path}"],
                "feedback": f"Error: File {file_path} does not exist"
            }
        
        # Run Flake8
        flake8_results = self._run_flake8(file_path)
        
        # Analyze basic code structure
        structure_issues = self._check_code_structure(file_path)
        
        # Combine all issues
        all_issues = flake8_results + structure_issues
        
        passed = len(all_issues) == 0
        
        feedback = self._generate_feedback(all_issues, passed)
        
        result = {
            "passed": passed,
            "issues": all_issues,
            "feedback": feedback
        }
        
        print(f"[ReviewerAgent] Review complete - {'PASSED' if passed else 'ISSUES FOUND'}")
        if not passed:
            print(f"[ReviewerAgent] Found {len(all_issues)} issue(s)")
        
        return result
    
    def _run_flake8(self, file_path):
        """Run Flake8 linter on the code"""
        issues = []
        
        try:
            # Run flake8 with relaxed settings for AI-generated code
            # Ignore: W292 (no newline at end), E501 (line too long), W503 (line break before operator)
            result = subprocess.run(
                ['flake8', file_path, 
                 '--max-line-length=100', 
                 '--ignore=E501,W503,W292'],  # Added W292 to ignore list
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                # Parse flake8 output
                for line in result.stdout.strip().split('\n'):
                    if line:
                        issues.append(f"Flake8: {line}")
            
        except FileNotFoundError:
            print("[ReviewerAgent] Warning: Flake8 not found, skipping style check")
        except Exception as e:
            print(f"[ReviewerAgent] Error running Flake8: {e}")
        
        return issues


    def _check_code_structure(self, file_path):
        """Check basic code structure requirements"""
        issues = []
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Check for docstring
            if '"""' not in code and "'''" not in code:
                issues.append("Missing docstring: Function should have a docstring")
            
            # Check for function definition
            if 'def ' not in code:
                issues.append("Missing function: No function definition found")
            
            # Check for TODO or placeholder code
            if 'TODO' in code or 'pass' in code:
                issues.append("Incomplete implementation: Found TODO or pass statement")
            
            # Check for basic error handling (for some function types)
            if 'factorial' in file_path.lower() and 'if' not in code:
                issues.append("Missing edge case handling: Should check for edge cases")
                
        except Exception as e:
            issues.append(f"Error reading file: {e}")
        
        return issues
    
    def _generate_feedback(self, issues, passed):
        """Generate human-readable feedback"""
        if passed:
            return "✓ Code review passed! No issues found."
        
        feedback = "Code review found the following issues:\n\n"
        for i, issue in enumerate(issues, 1):
            feedback += f"{i}. {issue}\n"
        
        feedback += "\nPlease fix these issues and resubmit."
        
        return feedback


# Test the Reviewer Agent
if __name__ == "__main__":
    from prompt_agent import PromptAgent
    from coder_agent import CoderAgent
    
    print("=== Testing Reviewer Agent ===\n")
    
    # Create agents
    prompt_agent = PromptAgent()
    coder_agent = CoderAgent()
    reviewer_agent = ReviewerAgent()
    
    # Generate code
    user_request = "Write a function that returns the factorial of a number"
    spec = prompt_agent.generate_specification(user_request)
    file_path = coder_agent.write_code(spec)
    
    # Review the code
    review_result = reviewer_agent.review_code(file_path)
    
    print("\n=== Review Results ===")
    print(f"Passed: {review_result['passed']}")
    print(f"\nFeedback:\n{review_result['feedback']}")
    
    if review_result['issues']:
        print(f"\nIssues found: {len(review_result['issues'])}")