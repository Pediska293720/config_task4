import sys
from lark import Lark, Token, Tree


def parse_arguments():
    if "--output" in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith('--'):
            return sys.argv[idx + 1]
        else:
            print("Error: no value for --output parameter")
            sys.exit(1)
    return 'output.yaml'


def read_input():
    print("Enter your configuration (empty line to finish):")
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
    except KeyboardInterrupt:
        print("\nInput cancelled")
        sys.exit(1)

    if not lines:
        print("Error: no input provided")
        sys.exit(1)

    return "\n".join(lines)


GRAMMAR = """
    start: (var_decl | config_line)*

    var_decl: "var" CNAME ":=" value
    config_line: CNAME (":=" | ":") value

    value: array
         | NUMBER
         | ESCAPED_STRING  
         | var_ref

    array: "[" [value (";" value)*] "]"
    var_ref: "${" CNAME "}"

    NUMBER: /0[xX][0-9a-fA-F]+/ | /[0-9]+/

    %import common.ESCAPED_STRING
    %import common.CNAME
    %import common.WS
    %ignore WS
"""


def evaluate_tree(tree, variables=None):
    if variables is None:
        variables = {}

    if isinstance(tree, Token):
        if tree.type == 'CNAME':
            return tree.value
        elif tree.type == 'ESCAPED_STRING':
            return tree.value[1:-1]
        elif tree.type == 'NUMBER':
            val = tree.value
            try:
                if val.lower().startswith('0x'):
                    return int(val, 16)
                return int(val)
            except ValueError as e:
                raise ValueError(f"Invalid number format: {val}")
        return tree.value

    elif isinstance(tree, Tree):
        if tree.data == 'var_decl':
            name = evaluate_tree(tree.children[0], variables)
            value = evaluate_tree(tree.children[1], variables)
            variables[name] = value
            return None

        elif tree.data == 'config_line':
            name = evaluate_tree(tree.children[0], variables)
            value = evaluate_tree(tree.children[1], variables)
            return (name, value)

        elif tree.data == 'array':
            return [evaluate_tree(child, variables) for child in tree.children]

        elif tree.data == 'var_ref':
            var_name = evaluate_tree(tree.children[0], variables)
            if var_name not in variables:
                raise ValueError(f"Undefined variable: {var_name}")
            return variables[var_name]

        elif tree.data == 'value':
            return evaluate_tree(tree.children[0], variables)

        elif tree.data == 'start':
            config = {}
            errors = []
            for child in tree.children:
                try:
                    result = evaluate_tree(child, variables)
                    if result is not None:
                        name, value = result
                        config[name] = value
                except ValueError as e:
                    errors.append(str(e))
            for error in errors:
                print(f"Error: {error}")
            return config

    return None


def format_value(value):
    if isinstance(value, list):
        items = []
        for item in value:
            items.append(format_value(item))
        return "[" + ", ".join(items) + "]"
    elif isinstance(value, str):
        return f'"{value}"'
    else:
        return str(value)


def main():
    output_file = parse_arguments()
    input_text = read_input()

    try:
        parser = Lark(GRAMMAR, parser='lalr')
        tree = parser.parse(input_text)

        config = evaluate_tree(tree)
        if not config:
            print("Error: No valid configuration lines found")
            sys.exit(1)

        output_lines = []
        for key, value in config.items():
            formatted_value = format_value(value)
            output_lines.append(f"{key}: {formatted_value}")

        output = "\n".join(output_lines)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)

        print(f"Success: Output saved to {output_file}")

    except Exception as e:
        error_msg = str(e)
        if "Unexpected token" in error_msg:
            if "Expected" in error_msg:
                # Извлекаем полезную информацию
                lines = input_text.split('\n')
                for i, line in enumerate(lines, 1):
                    if ':=' in line or ':' in line:
                        if line.strip().endswith((':=')) or line.strip().endswith(':'):
                            print(f"Error: Missing value")
                            sys.exit(1)
                        elif '[' in line and ']' not in line:
                            print(f"Error: Unclosed array")
                            sys.exit(1)
                        elif '${' in line and '}' not in line:
                            print(f"Error: Unclosed variable reference")
                            sys.exit(1)
                print(f"Error: Syntax error")
                sys.exit(1)

        print(f"Error: {error_msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()