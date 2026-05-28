#!/usr/bin/env python3
import sys
from pathlib import Path
import re


TILDE_LINE = re.compile(r'^\s*(~+)\s*$')
HAT_LINE = re.compile(r'^\s*(\^+)\s*$')

def process_rst(text):
    lines = text.splitlines()
    out = []

    for i, line in enumerate(lines):
        m1 = TILDE_LINE.match(line)
        m2 = HAT_LINE.match(line)
        m = None
        if m1:
            m = m1
            ch = "^"
        if m2:
            m = m2
            ch = '"'

        if m and i > 0:
            title = lines[i - 1].rstrip()

            # Only treat as a header underline if the line above is non-blank
            # and the underline is at least as long as the title
            if title and len(m.group(1)) >= len(title):
                out.append(ch * len(m.group(1)))
                continue

        out.append(line)

    return "\n".join(out)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_subsubsection_underlines.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    fixed = process_rst(text) + "\n"
    path.write_text(fixed, encoding="utf-8")

    print(f"✅ Replaced '~' subsubsection underlines with '^' in {path}")


if __name__ == "__main__":
    main()
