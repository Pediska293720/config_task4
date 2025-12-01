import sys
import re


def parse_arguments():
    args = {'output_file': 'default.yaml'}
    if "--output" in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith('--'):
            args['output_file'] = sys.argv[idx + 1]
        else:
            print("Error: no value for output\n")
            sys.exit(1)
    return args


def read_input():
    print("Enter your configuration (empty line to finish):")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        except KeyboardInterrupt:
            print("\nInput cancelled")
            sys.exit(1)
    return "\n".join(lines)


def parse_hex_number(hex_str):
    if hex_str.lower().startswith('0x'):
        return int(hex_str, 16)
    return int(hex_str)


def parse_value(value_str, variables=None):
    if variables is None:
        variables = {}

    value_str = value_str.strip()

    if variables:
        value_str = substitute_variables(value_str, variables)

    if value_str.startswith('[') and not value_str.endswith(']'):
        raise ValueError("Unclosed array bracket")

    if value_str.startswith('[') and value_str.endswith(']'):
        return parse_array(value_str, variables)

    elif re.match(r'^0[xX][0-9a-fA-F]+$', value_str):
        return parse_hex_number(value_str)

    elif re.match(r'^[0-9]+$', value_str):
        return int(value_str)

    elif value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]

    else:
        return value_str

def parse_array(array_str, variables=None):
    if variables is None:
        variables = {}
    content = array_str[1:-1].strip()
    if not content:
        return []

    elements = []
    i = 0
    current_element = ""
    bracket_count = 0

    while i < len(content):
        char = content[i]

        if char == '[':
            bracket_count += 1
            current_element += char
        elif char == ']':
            if bracket_count == 0:
                raise ValueError("Unexpected closing bracket in array")
            bracket_count -= 1
            current_element += char
        elif char == ';' and bracket_count == 0:
            if current_element.strip():
                elements.append(parse_value(current_element.strip(), variables))
            current_element = ""
        else:
            current_element += char
        i += 1

    if bracket_count != 0:
        raise ValueError("Unclosed nested array")

    if current_element.strip():
        elements.append(parse_value(current_element.strip(), variables))

    return elements


def extract_variables(lines):
    variables = {}

    for line in lines:
        line = line.strip()
        if line.startswith('var '):
            parts = line[4:].split(':=', 1)
            if len(parts) == 2:
                var_name = parts[0].strip()
                var_value = parts[1].strip()
                variables[var_name] = parse_value(var_value, {})

    return variables


def substitute_variables(text, variables):
    def replace_match(match):
        var_name = match.group(1)
        if var_name in variables:
            value = variables[var_name]
            if isinstance(value, list):
                items = []
                for item in value:
                    if isinstance(item, str):
                        items.append(f'"{item}"')
                    else:
                        items.append(str(item))
                return '[' + '; '.join(items) + ']'
            elif isinstance(value, str):
                return f'"{value}"'
            else:
                return str(value)
        else:
            raise ValueError(f"Undefined variable: {var_name}")

    return re.sub(r'\$\{([^}]+)\}', replace_match, text)


def convert_to_yaml(data_lines, variables):
    yaml_lines = []

    for line in data_lines:
        line = line.strip()

        if not line or line.startswith('var '):
            continue

        try:
            line_with_subs = substitute_variables(line, variables)

            if ':=' in line_with_subs:
                key, value = line_with_subs.split(':=', 1)
                key = key.strip()
                value = value.strip().rstrip(';')

                parsed_value = parse_value(value, variables)

                if isinstance(parsed_value, list):
                    formatted_array = format_array_for_yaml(parsed_value)
                    yaml_lines.append(f"{key}: {formatted_array}")
                elif isinstance(parsed_value, str):
                    yaml_lines.append(f"{key}: \"{parsed_value}\"")
                else:
                    yaml_lines.append(f"{key}: {parsed_value}")

            elif ':' in line_with_subs and not line_with_subs.endswith(':'):
                key, value = line_with_subs.split(':', 1)
                key = key.strip()
                value = value.strip().rstrip(';')

                parsed_value = parse_value(value, variables)

                if isinstance(parsed_value, list):
                    formatted_array = format_array_for_yaml(parsed_value)
                    yaml_lines.append(f"{key}: {formatted_array}")
                elif isinstance(parsed_value, str):
                    yaml_lines.append(f"{key}: \"{parsed_value}\"")
                else:
                    yaml_lines.append(f"{key}: {parsed_value}")
            else:
                yaml_lines.append(line_with_subs.rstrip(';'))

        except Exception as e:
            print(f"Warning: Skipping line due to error: {e}")

    return '\n'.join(yaml_lines)


def format_array_for_yaml(array):
    items = []
    for item in array:
        if isinstance(item, list):
            items.append(format_array_for_yaml(item))
        elif isinstance(item, str):
            items.append(f'"{item}"')
        else:
            items.append(str(item))
    return '[' + ', '.join(items) + ']'


def translate_to_yaml(input_text):
    lines = input_text.split('\n')
    variables = extract_variables(lines)
    yaml_output = convert_to_yaml(lines, variables)
    return yaml_output


def main():
    arguments = parse_arguments()

    if arguments['output_file'] is None:
        print("Error: no output file specified")
        return

    input_text = read_input()

    if not input_text.strip():
        print("Error: no input provided")
        return

    try:
        yaml_output = translate_to_yaml(input_text)
        with open(arguments['output_file'], 'w', encoding='utf-8') as f:
            f.write(yaml_output)
        print(f"Success: YAML saved to {arguments['output_file']}")

    except Exception as e:
        print(f"Error during translation: {e}")


if __name__ == "__main__":
    main()
