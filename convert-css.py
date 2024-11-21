css_values = """
--type-scale-m-label-bold-l-font-family: var(--primary-font-family);
--type-scale-m-label-bold-l-font-weight: "bold";
--type-scale-m-label-bold-l-font-size: 16;
--type-scale-m-label-bold-l-line-height: 22;
--type-scale-m-label-bold-l-letter-spacing: 1.8200000524520874;
--type-scale-m-label-bold-s-font-family: var(--primary-font-family);
--type-scale-m-label-bold-s-font-weight: "bold";
--type-scale-m-label-bold-s-font-size: 14;
--type-scale-m-label-bold-s-line-height: 20;
--type-scale-m-label-bold-s-letter-spacing: 1.2699999809265137;
"""


def convert_to_rem(px_value, base=16):
    return f"{px_value / base:.4f}rem"


def convert_to_em(px_value, font_size):
    return f"{px_value / font_size:.4f}em"


def convert_to_unitless(line_height_px, font_size_px):
    return f"{line_height_px / font_size_px:.4f}"  # Remove '%' from the format


properties = css_values.strip().split(';')
font_sizes = {}
grouped_css = {}

# First, collect all font sizes
for prop in properties:
    if prop.strip():
        key, value = prop.split(':')
        key = key.strip()
        value = value.strip().replace('px', '')

        if 'font-size' in key:
            font_size_px = float(value)
            font_sizes[key] = font_size_px
            grouped_css[key] = convert_to_rem(font_size_px)

# Then process all properties
for prop in properties:
    if prop.strip():
        key, value = prop.split(':')
        key = key.strip()
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

        elif 'font-family' in key or 'font-weight' in key:
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

with open("converted_css.css", "w") as file:
    file.write(output)

print("Converted CSS written to converted_css.css")
