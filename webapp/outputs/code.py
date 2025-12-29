from typing import List, Union

def find_smallest_number(numbers: List[Union[int, float]]) -> float:
    """Finds the smallest number in a list of numbers."""

    if not numbers:  # handle edge case where input is an empty list
        return None

    smallest = numbers[0]
    for num in numbers:
        if num < smallest:
            smallest = num

    return float(smallest)

def main():
    """Main function to interactively get user input."""

    # Get a list of numbers from the user
    print("Enter a list of numbers, separated by spaces:")
    numbers_str = input().split()  # split on whitespace

    try:
        numbers = [float(num) for num in numbers_str]  # convert to floats
    except ValueError:
        print("Invalid input. Please enter a list of numbers.")
        return

    smallest = find_smallest_number(numbers)

    if smallest is not None:
        print(f"The smallest number in the list is {smallest}")
    else:
        print("No numbers were provided.")


if __name__ == "__main__":
    print(f"find_smallest_number(3, 'world') = {find_smallest_number(3, 'world')}")
    print(f"find_smallest_number(5, 'hello') = {find_smallest_number(5, 'hello')}")
    
    # Uncomment to run interactive mode:
    # main()