def bmi_category(height: float, weight: float) -> str:
    """

    Parameters:
        height (float): Height in cm
        weight (float): Weight in kg

    Returns:
        str: String representing the BMI category (underweight, normal, overweight or obese)
    """
    if not isinstance(height, (int, float)) or not isinstance(weight, (int, float)):
        return "Error: Inputs must be numbers"

    if height <= 0 or weight <= 0:
        return "Error: Inputs must be greater than 0"

    bmi = weight / ((height/100)**2)

    if bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 25:
        return "Normal"
    elif 25 <= bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def main():
    height = float(input("Enter your height in cm: "))
    weight = float(input("Enter your weight in kg: "))
    print(bmi_category(height, weight))


if __name__ == "__main__":
    print(f"bmi_category(1.75, 70) = {bmi_category(1.75, 70)}")
    print(f"bmi_category(1.80, 90) = {bmi_category(1.80, 90)}")
    
    # Uncomment to run interactive mode:
    # main()