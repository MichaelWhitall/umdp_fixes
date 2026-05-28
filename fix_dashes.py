import re
import sys

def fix_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Replace "-  " with "- " only at the start of a line
    lines = [re.sub(r'^-  ', '- ', line) for line in lines]

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_dashes.py <filename>")
        sys.exit(1)

    fix_file(sys.argv[1])
