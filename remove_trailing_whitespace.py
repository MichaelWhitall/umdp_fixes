#!/usr/bin/env python3
import sys
from pathlib import Path

def process_rst(text):
    lines = text.splitlines()
    for i in range(len(lines)):  lines[i] = lines[i].rstrip()
    return "\n".join(lines)+"\n"

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python remove_trailing_whitespace.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    text = process_rst(text)
    path.write_text(text, encoding="utf-8")

    print(f"✅ Removed trailing whitespace from {path}.")


if __name__ == "__main__":
    main()
