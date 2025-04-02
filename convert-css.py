import re

# File paths
input_file = "input.css"
output_file = "converted_css.css"

# Read the input file
with open(input_file, "r") as file:
    css_content = file.read()


# Extract content inside :root { ... }
root_match = re.search(r":root\s*{([\s\S]*?)}", css_content)
if not root_match:
    print("Error: No :root { ... } block found in input.css.")
    exit(1)

css_values = root_match.group(1)  # Extract the inside content


def convert_to_rem(px_value, base=16):
    return f"{px_value / base:.4f}rem"


def convert_to_em(px_value, font_size):
    return f"{px_value / font_size:.4f}em"


def convert_to_unitless(line_height_px, font_size_px):
    return f"{line_height_px / font_size_px:.4f}"


def convert_font_weight(value):
    font_weight_map = {
        "light": 300,
        "book": 400,
        "regular": 400,
        "medium": 450,
        "demi": 500,
        "heavy": 600,
        "bold": 700,
        "extra bold": 800
    }
    cleaned_value = value.lower().strip('\"').strip()
    return str(font_weight_map.get(cleaned_value, value))


# Extract CSS properties as key-value pairs
properties = re.findall(r'(--[\w-]+):\s*([^;]+);', css_values)
font_sizes = {}
grouped_css = {}

# First, collect all font sizes
for key, value in properties:
    value = value.strip().replace('px', '')

    if 'font-size' in key:
        font_size_px = float(value)
        font_sizes[key] = font_size_px
        grouped_css[key] = convert_to_rem(font_size_px)

# Then process all properties
for key, value in properties:
    value = value.strip().replace('px', '')

    if 'line-height' in key:
        line_height_px = float(value)
        base_name = "-".join(key.split('-')[:-2]) + "-font-size"
        font_size_px = font_sizes.get(base_name)
        if font_size_px:
            grouped_css[key] = convert_to_unitless(line_height_px, font_size_px)

    elif 'letter-spacing' in key:
        letter_spacing_px = float(value)
        base_name = "-".join(key.split('-')[:-2]) + "-font-size"
        font_size_px = font_sizes.get(base_name)
        if font_size_px:
            grouped_css[key] = convert_to_em(letter_spacing_px, font_size_px)

    elif 'font-weight' in key:
        grouped_css[key] = convert_font_weight(value)

    elif 'font-family' in key:
        grouped_css[key] = value  # Preserve these properties as-is

output = ":root {\n"

processed_names = set()

for key in grouped_css.keys():
    base_name = "-".join(key.split('-')[:-2])
    if base_name not in processed_names:
        processed_names.add(base_name)
        font_family_key = f"{base_name}-font-family"
        font_weight_key = f"{base_name}-font-weight"
        font_size_key = f"{base_name}-font-size"
        line_height_key = f"{base_name}-line-height"
        letter_spacing_key = f"{base_name}-letter-spacing"

        output += f"  {font_family_key}: {grouped_css.get(font_family_key, 'auto')};\n"
        output += f"  {font_weight_key}: {grouped_css.get(font_weight_key, 'auto')};\n"
        output += f"  {font_size_key}: {grouped_css.get(font_size_key, 'auto')};\n"
        output += f"  {line_height_key}: {grouped_css.get(line_height_key, 'auto')};\n"
        output += f"  {letter_spacing_key}: {grouped_css.get(letter_spacing_key, 'auto')};\n"

output += "}\n"

# Write the converted CSS to a file
with open(output_file, "w") as file:
    file.write(output)

print(f"Converted CSS written to {output_file}")
