def is_leap_year(year: int) -> bool:
    """

    Parameters:
        year (int): A positive integer representing the year 

    Returns:
        bool: A boolean value indicating whether the input year is a leap year
    """
    # Handle edge cases where the input year is less than 1582 for years before the introduction of the Gregorian calendar.
    if year < 1582:
        return False

    # Check if the year is evenly divisible by 4, except for end of century years not evenly divisible by 400.
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return True

    return False

def main():
    # Get input from user
    year = int(input("Enter a year: "))
    print(f"{year} is a leap year: {is_leap_year(year)}")

if __name__ == '__main__':
    test_list = [1900, 2000, 2020]
    for i in test_list:
        print(f"is_leap_year({i}) = {is_leap_year(i)}")