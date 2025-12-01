"""
Main Orchestrator: Coordinates all agents in a feedback loop
"""
import json
import os
from datetime import datetime
from agents.prompt_agent import PromptAgent
from agents.coder_agent import CoderAgent
from agents.reviewer_agent import ReviewerAgent
from agents.tester_agent import TesterAgent

class CodeTestCrew:
    def __init__(self, model_name="gemma3:1b", max_attempts=10):
        self.prompt_agent = PromptAgent()
        self.coder_agent = CoderAgent(model_name=model_name)
        self.reviewer_agent = ReviewerAgent()
        self.tester_agent = TesterAgent()
        self.max_attempts = max_attempts
        
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
    def process_request(self, user_request):
        """
        Process a user request through the entire multi-agent system
        
        Args:
            user_request (str): User's coding request
            
        Returns:
            dict: Final results including success status and file path
        """
        print("="*80)
        print("CODE & TEST CREW - MULTI-AGENT SYSTEM")
        print("="*80)
        print(f"\nUser Request: {user_request}\n")
        
        # Step 1: Generate specification
        print("\n[STEP 1] Prompt Agent - Generating Specification...")
        specification = self.prompt_agent.generate_specification(user_request)
        print(f"✓ Specification created for function: {specification['function_name']}")
        
        # Reset coder attempt counter
        self.coder_agent.reset_attempts()
        
        # Feedback loop
        feedback = None
        final_result = None
        
        for attempt in range(1, self.max_attempts + 1):
            print(f"\n{'='*80}")
            print(f"ATTEMPT {attempt}/{self.max_attempts}")
            print(f"{'='*80}")
            
            # Step 2: Generate code
            print(f"\n[STEP 2] Coder Agent - Writing Code...")
            file_path = self.coder_agent.write_code(specification, feedback)
            
            # Step 3: Review code
            print(f"\n[STEP 3] Reviewer Agent - Checking Code Quality...")
            review_result = self.reviewer_agent.review_code(file_path)
            
            # Step 4: Test code
            print(f"\n[STEP 4] Tester Agent - Running Tests...")
            test_result = self.tester_agent.test_code(file_path, specification)
            
            # Check if both passed
            both_passed = review_result['passed'] and test_result['passed']
            
            # Display results
            print(f"\n{'='*80}")
            print(f"ATTEMPT {attempt} RESULTS")
            print(f"{'='*80}")
            print(f"Review: {'✓ PASSED' if review_result['passed'] else '✗ FAILED'}")
            print(f"Tests:  {'✓ PASSED' if test_result['passed'] else '✗ FAILED'}")
            
            if both_passed:
                print(f"\n🎉 SUCCESS! Code passed both review and tests on attempt {attempt}")
                final_result = {
                    "success": True,
                    "attempts": attempt,
                    "file_path": file_path,
                    "specification": specification,
                    "review_result": review_result,
                    "test_result": test_result
                }
                break
            else:
                # Generate feedback for next iteration
                feedback = self._generate_feedback(review_result, test_result)
                print(f"\n📝 Feedback for next attempt:")
                print(feedback)
                
                if attempt == self.max_attempts:
                    print(f"\n❌ FAILED: Maximum attempts ({self.max_attempts}) reached")
                    final_result = {
                        "success": False,
                        "attempts": attempt,
                        "file_path": file_path,
                        "specification": specification,
                        "review_result": review_result,
                        "test_result": test_result,
                        "reason": "Max attempts reached"
                    }
        
        # Save results to log
        self._save_log(user_request, final_result)
        
        return final_result
    
    def _generate_feedback(self, review_result, test_result):
        """Combine feedback from reviewer and tester"""
        feedback = ""
        
        if not review_result['passed']:
            feedback += "=== CODE REVIEW ISSUES ===\n"
            feedback += review_result['feedback']
            feedback += "\n\n"
        
        if not test_result['passed']:
            feedback += "=== TEST FAILURES ===\n"
            feedback += test_result['feedback']
        
        return feedback
    
    def _save_log(self, user_request, result):
        """Save execution log"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/execution_{timestamp}.json"
        
        log_data = {
            "timestamp": timestamp,
            "user_request": user_request,
            "result": result
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"\n📄 Log saved to: {log_file}")


# Main execution
if __name__ == "__main__":
    # Create the crew
    crew = CodeTestCrew(max_attempts=10)
    
    # Test with factorial
    print("\n" + "="*80)
    print("TEST 1: Factorial Function")
    print("="*80)
    
    result1 = crew.process_request("Write a function that returns the factorial of a number")
    
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"Success: {result1['success']}")
    print(f"Attempts: {result1['attempts']}")
    print(f"Final file: {result1['file_path']}")
    
    # Display final code
    if result1['success']:
        print("\n" + "="*80)
        print("FINAL WORKING CODE")
        print("="*80)
        with open(result1['file_path'], 'r') as f:
            print(f.read())