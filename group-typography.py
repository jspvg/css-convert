import argparse
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass


DEFAULT_INPUT_FILE = "input.css"
DEFAULT_OUTPUT_FILE = "grouped_typography.css"
DEFAULT_ROOT_FONT_SIZE = 16.0
DEFAULT_VIEWPORTS = OrderedDict((
    ("s", 375.0),
    ("m", 640.0),
    ("l", 1440.0),
))
MERGE_PROPERTIES = (
    "font-family",
    "font-weight",
    "font-size",
    "line-height",
    "letter-spacing",
)
VARIABLE_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?P<name>--[\w-]+):\s*(?P<value>[^;]+);\s*$"
)
NUMERIC_PATTERN = re.compile(r"^(?P<number>-?\d+(?:\.\d+)?)(?P<unit>rem|em)?$")


@dataclass
class Declaration:
    indent: str
    name: str
    value: str


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Collapse viewport-specific typography tokens into a single token set "
            "using clamp() values."
        )
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_FILE,
        help=f"CSS file to read. Defaults to {DEFAULT_INPUT_FILE}.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"CSS file to write. Defaults to {DEFAULT_OUTPUT_FILE}.",
    )
    parser.add_argument(
        "--root-font-size",
        type=float,
        default=DEFAULT_ROOT_FONT_SIZE,
        help=(
            "Root font size in px used when deriving clamp() formulas. "
            f"Defaults to {DEFAULT_ROOT_FONT_SIZE:g}."
        ),
    )
    parser.add_argument(
        "--viewport",
        action="append",
        default=[],
        metavar="NAME=PX",
        help=(
            "Override a viewport width, for example --viewport s=390. "
            "Can be supplied multiple times."
        ),
    )
    return parser.parse_args()


def load_css(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_css(path, content):
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def parse_viewports(overrides):
    viewports = OrderedDict(DEFAULT_VIEWPORTS)
    for item in overrides:
        if "=" not in item:
            raise ValueError(f"Invalid viewport override: {item}")
        name, raw_width = item.split("=", 1)
        try:
            width = float(raw_width)
        except ValueError as exc:
            raise ValueError(f"Invalid viewport width: {item}") from exc
        viewports[name.strip()] = width
    return viewports


def extract_root_block(css_content):
    match = re.search(r":root\s*{(?P<body>[\s\S]*?)}", css_content)
    if not match:
        raise ValueError("No :root { ... } block found.")
    return match.group("body")


def parse_root_declarations(root_body):
    declarations = []
    for line in root_body.splitlines():
        if not line.strip():
            continue
        match = VARIABLE_PATTERN.match(line)
        if not match:
            declarations.append(Declaration("", line.strip(), ""))
            continue
        declarations.append(
            Declaration(
                indent=match.group("indent") or "  ",
                name=match.group("name"),
                value=match.group("value").strip(),
            )
        )
    return declarations


def parse_numeric_value(value):
    match = NUMERIC_PATTERN.match(value.strip())
    if not match:
        return None
    return float(match.group("number")), match.group("unit") or ""


def format_number(value):
    rounded = round(value, 4)
    text = f"{rounded:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def format_numeric_value(number, unit):
    return f"{format_number(number)}{unit}"


def parse_typography_variable(name, viewports):
    prefix = "--typography-"
    if not name.startswith(prefix):
        return None

    body = name[len(prefix):]
    for viewport in sorted(viewports.keys(), key=len, reverse=True):
        viewport_prefix = f"{viewport}-"
        if not body.startswith(viewport_prefix):
            continue

        remainder = body[len(viewport_prefix):]
        for property_name in MERGE_PROPERTIES:
            suffix = f"-{property_name}"
            if remainder.endswith(suffix):
                token = remainder[:-len(suffix)]
                if token:
                    return viewport, token, property_name

    return None


def build_clamp(min_value, max_value, min_px, max_px, root_font_size, unit):
    if abs(max_value - min_value) < 1e-9:
        return format_numeric_value(min_value, unit)

    min_width = min_px / root_font_size
    max_width = max_px / root_font_size
    slope = ((max_value - min_value) / (max_width - min_width)) * 100
    intercept = min_value - (slope / 100) * min_width
    preferred_unit = unit if unit else ""
    intercept_value = format_numeric_value(intercept, preferred_unit)
    slope_value = format_number(abs(slope))
    operator = "+" if slope >= 0 else "-"
    return (
        f"clamp({format_numeric_value(min_value, unit)}, "
        f"{intercept_value} {operator} {slope_value}vw, "
        f"{format_numeric_value(max_value, unit)})"
    )


def convert_line_height_points(font_size_points, line_height_points):
    line_height_units = {unit for _, _, unit in line_height_points}
    if len(line_height_units) != 1:
        return None

    line_height_unit = next(iter(line_height_units))
    if line_height_unit:
        return line_height_points

    font_size_units = {unit for _, _, unit in font_size_points}
    if len(font_size_units) != 1:
        return None

    font_size_unit = next(iter(font_size_units))
    converted_points = []
    for (width, font_size, _), (_, line_height, _) in zip(font_size_points, line_height_points):
        converted_points.append((width, font_size * line_height, font_size_unit))
    return converted_points


def build_groups(declarations, viewports):
    groups = OrderedDict()
    unmatched = []

    for declaration in declarations:
        if not declaration.value:
            unmatched.append(declaration)
            continue

        parsed = parse_typography_variable(declaration.name, viewports)
        if not parsed:
            unmatched.append(declaration)
            continue

        viewport, token, property_name = parsed

        if token not in groups:
            groups[token] = {
                "indent": declaration.indent or "  ",
                "properties": OrderedDict(),
            }

        properties = groups[token]["properties"]
        if viewport not in properties:
            properties[viewport] = {}
        properties[viewport][property_name] = declaration.value

    return groups, unmatched


def build_merged_token(token, group, viewports, root_font_size):
    viewport_entries = []
    for viewport, values in group["properties"].items():
        if all(prop in values for prop in MERGE_PROPERTIES):
            viewport_entries.append((viewport, values))

    if len(viewport_entries) < 2:
        return None

    viewport_entries.sort(key=lambda item: viewports[item[0]])
    font_family_values = {values["font-family"] for _, values in viewport_entries}
    font_weight_values = {values["font-weight"] for _, values in viewport_entries}
    letter_spacing_values = {values["letter-spacing"] for _, values in viewport_entries}

    if len(font_family_values) != 1 or len(font_weight_values) != 1:
        return None

    font_size_points = []
    line_height_points = []

    for viewport, values in viewport_entries:
        font_size_value = parse_numeric_value(values["font-size"])
        line_height_value = parse_numeric_value(values["line-height"])
        if font_size_value is None or line_height_value is None:
            return None
        font_size_points.append((viewports[viewport], *font_size_value))
        line_height_points.append((viewports[viewport], *line_height_value))

    font_size_units = {unit for _, _, unit in font_size_points}
    if len(font_size_units) != 1:
        return None

    rendered_line_height_points = convert_line_height_points(
        font_size_points,
        line_height_points,
    )
    if rendered_line_height_points is None:
        return None

    min_font_size = font_size_points[0]
    max_font_size = font_size_points[-1]
    min_line_height = rendered_line_height_points[0]
    max_line_height = rendered_line_height_points[-1]

    merged = OrderedDict()
    merged["font-family"] = next(iter(font_family_values))
    merged["font-weight"] = next(iter(font_weight_values))
    merged["font-size"] = build_clamp(
        min_font_size[1],
        max_font_size[1],
        min_font_size[0],
        max_font_size[0],
        root_font_size,
        min_font_size[2],
    )
    merged["line-height"] = build_clamp(
        min_line_height[1],
        max_line_height[1],
        min_line_height[0],
        max_line_height[0],
        root_font_size,
        min_line_height[2],
    )
    merged["letter-spacing"] = (
        next(iter(letter_spacing_values))
        if len(letter_spacing_values) == 1
        else None
    )

    if merged["letter-spacing"] is None:
        letter_spacing_points = []
        for viewport, values in viewport_entries:
            letter_spacing_value = parse_numeric_value(values["letter-spacing"])
            if letter_spacing_value is None:
                return None
            letter_spacing_points.append((viewports[viewport], *letter_spacing_value))
        letter_spacing_units = {unit for _, _, unit in letter_spacing_points}
        if len(letter_spacing_units) != 1:
            return None
        min_letter_spacing = min(letter_spacing_points, key=lambda item: item[1])
        max_letter_spacing = max(letter_spacing_points, key=lambda item: item[1])
        merged["letter-spacing"] = build_clamp(
            min_letter_spacing[1],
            max_letter_spacing[1],
            min_letter_spacing[0],
            max_letter_spacing[0],
            root_font_size,
            min_letter_spacing[2],
        )

    return group["indent"], merged


def render_output(groups, unmatched, viewports, root_font_size):
    lines = [":root {"]
    merged_count = 0

    for token, group in groups.items():
        merged_token = build_merged_token(token, group, viewports, root_font_size)
        if merged_token is None:
            for viewport, values in group["properties"].items():
                for property_name in MERGE_PROPERTIES:
                    if property_name not in values:
                        continue
                    lines.append(
                        f"{group['indent']}--typography-{viewport}-{token}-{property_name}: "
                        f"{values[property_name]};"
                    )
            continue

        indent, merged_values = merged_token
        merged_count += 1
        for property_name, value in merged_values.items():
            lines.append(f"{indent}--typography-{token}-{property_name}: {value};")

    for declaration in unmatched:
        if declaration.value:
            lines.append(f"{declaration.indent}{declaration.name}: {declaration.value};")
        else:
            lines.append(f"  {declaration.name}")

    lines.append("}")
    return "\n".join(lines) + "\n", merged_count


args = parse_args()

try:
    css_content = load_css(args.input)
    viewports = parse_viewports(args.viewport)
    root_body = extract_root_block(css_content)
    declarations = parse_root_declarations(root_body)
    groups, unmatched = build_groups(declarations, viewports)
    output, merged_count = render_output(
        groups,
        unmatched,
        viewports,
        args.root_font_size,
    )
    write_css(args.output, output)
except Exception as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)

print(
    f"Wrote {args.output} with {merged_count} merged typography token groups.",
    file=sys.stdout,
)
