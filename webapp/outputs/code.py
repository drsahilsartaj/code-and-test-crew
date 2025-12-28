def fibonacci_sequence(n: int) -> list[int]:
    """Generate Fibonacci sequence up to a given number of terms."""
    if n <= 0:
        return []

    fib = [0, 1] + [0] * (n-2)
    for i in range(2, n):
        fib[i] = fib[i-1] + fib[i-2]

    return fib

def main():
    num_terms = int(input("Enter the number of terms to generate: "))
    print(fibonacci_sequence(num_terms))


if __name__ == "__main__":
    print(f"fibonacci_sequence(10) = {fibonacci_sequence(10)}")
    print(f"fibonacci_sequence(0) = {fibonacci_sequence(0)}")
    
    # Uncomment to run interactive mode:
    # main()