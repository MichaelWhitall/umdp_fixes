#!/usr/bin/env python3
import re
import sys
from pathlib import Path


# Match :math:` ... ` spans, including those with newlines
INLINE_MATH_RE = re.compile(
    r":math:`(.*?)`",
    re.DOTALL,
)


def fix_inline_math(text):
    def repl(m):
        content = m.group(1)

        # Only fix if a continuation line is indented
        if not re.search(r"\n[ \t]+", content):
            return m.group(0)

        # Collapse newline + indentation into single space
        fixed = re.sub(r"\s*\n\s*", " ", content)

        return f":math:`{fixed}`"

    return INLINE_MATH_RE.sub(repl, text)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_multiline_inline_math.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    fixed = fix_inline_math(text)
    path.write_text(fixed, encoding="utf-8")

    print(f"✅ Fixed multiline inline math in {path}")


if __name__ == "__main__":
    main()
