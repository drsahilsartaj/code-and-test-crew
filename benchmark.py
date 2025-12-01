"""
Benchmark Suite: Test the multi-agent system with 10 different problems
"""
from main import CodeTestCrew
import json
from datetime import datetime

class Benchmark:
    def __init__(self):
        self.crew = CodeTestCrew(max_attempts=10)
        self.test_cases = [
            "Write a function that returns the factorial of a number",
            "Write a function that returns the nth Fibonacci number",
            "Write a function that checks if a number is prime",
            "Write a function that reverses a string",
            "Write a function that calculates the sum of a list of numbers",
            "Write a function that finds the maximum number in a list",
            "Write a function that checks if a string is a palindrome",
            "Write a function that counts vowels in a string",
            "Write a function that returns the square of a number",
            "Write a function that converts Celsius to Fahrenheit"
        ]
        self.results = []
    
    def run(self):
        """Run all benchmark tests"""
        print("="*80)
        print("BENCHMARK TEST SUITE - 10 PROGRAMMING PROBLEMS")
        print("="*80)
        print(f"Total tests: {len(self.test_cases)}\n")
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n{'='*80}")
            print(f"BENCHMARK TEST {i}/{len(self.test_cases)}")
            print(f"{'='*80}\n")
            
            # Reset the coder agent for each test
            self.crew.coder_agent.reset_attempts()
            
            # Run the test
            result = self.crew.process_request(test_case)
            
            # Store result
            self.results.append({
                "test_number": i,
                "request": test_case,
                "success": result["success"],
                "attempts": result["attempts"],
                "file_path": result.get("file_path", "")
            })
            
            print(f"\n{'='*80}")
            print(f"TEST {i} RESULT: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
            print(f"{'='*80}\n")
        
        # Generate summary
        self._print_summary()
        self._save_results()
    
    def _print_summary(self):
        """Print benchmark summary"""
        print("\n" + "="*80)
        print("BENCHMARK SUMMARY")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        pass_rate = (passed / total) * 100
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        # Average attempts for successful tests
        successful_attempts = [r["attempts"] for r in self.results if r["success"]]
        if successful_attempts:
            avg_attempts = sum(successful_attempts) / len(successful_attempts)
            print(f"Average Attempts (successful): {avg_attempts:.1f}")
        
        # Detailed results
        print("\n" + "-"*80)
        print("DETAILED RESULTS")
        print("-"*80)
        
        for result in self.results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{result['test_number']}. {status} (Attempts: {result['attempts']}) - {result['request'][:50]}...")
    
    def _save_results(self):
        """Save benchmark results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/benchmark_{timestamp}.json"
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        pass_rate = (passed / total) * 100
        
        benchmark_data = {
            "timestamp": timestamp,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": pass_rate,
            "results": self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(benchmark_data, f, indent=2)
        
        print(f"\n📄 Benchmark results saved to: {filename}")


if __name__ == "__main__":
    benchmark = Benchmark()
    benchmark.run()