import re

# File paths
input_file = "converted_css.css"
output_file = "cleaned_css.css"

# Read the input file
with open(input_file, "r") as file:
    css_content = file.read()

# Function to clean up trailing zeros in numbers (excluding font-weight)
def clean_number(match):
    before = match.group(1)  # Property name and colon
    value = match.group(2)   # Numeric value
    unit = match.group(3) or ""  # Unit (rem, em, px, etc.)
    after = match.group(4)   # Semicolon

    # Don't modify font-weight values (they don't have units like rem/em)
    if "font-weight" in before:
        return before + value + after  # Return unmodified

    # Convert value to float to remove unnecessary trailing zeros
    cleaned_value = str(float(value)).rstrip("0").rstrip(".") if "." in value else value

    return f"{before}{cleaned_value}{unit}{after}"

# Regex pattern to find number values (excluding font-weight)
pattern = re.compile(r"(\s*--[\w-]+:\s*)([-+]?\d*\.?\d+|\d+)(rem|em|px|%)?(\s*;)", re.IGNORECASE)

# Apply transformation
cleaned_css = pattern.sub(clean_number, css_content)

# Write the cleaned CSS to a new file
with open(output_file, "w") as file:
    file.write(cleaned_css)

print(f"Cleaned CSS written to {output_file}")
