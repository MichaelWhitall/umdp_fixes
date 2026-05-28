#!/usr/bin/env python3
r"""
Fix LaTeX constructs unsupported by MathJax, ONLY inside ReST math regions:

Inline math:
  :math:`...`

Display math:
  .. math::
     <math content>

Fixes applied:
  1) \ensuremath{X}  -> X        (handles nested ensuremath)
  2) \mbox{X}        -> \mathrm{X}
  3) remove \tiny
  4) remove \noindent
  5) \rm X / \rm{X}  -> \mathrm{X}
  6) \it X / \it{X}  -> \mathit{X}
"""

import re
import sys
from pathlib import Path


# ------------------------------------------------------------
# Utilities for balanced-brace parsing
# ------------------------------------------------------------

def strip_outer_braces(s):
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        return s[1:-1]
    return s


def remove_ensuremath(s):
    r"""
    Remove \ensuremath{...}, handling nested occurrences.
    """
    out = ""
    i = 0
    while i < len(s):
        if s.startswith(r"\ensuremath{", i):
            i += len(r"\ensuremath{")
            depth = 1
            start = i
            while i < len(s) and depth > 0:
                if s[i] == "{":
                    depth += 1
                elif s[i] == "}":
                    depth -= 1
                i += 1
            inner = s[start:i-1]
            out += remove_ensuremath(inner)
        else:
            out += s[i]
            i += 1
    return out


# ------------------------------------------------------------
# Font command replacements
# ------------------------------------------------------------

FONT_CMD_RE = re.compile(
    r"""
    \\(rm|it|bf|cal)        # command
    \s*
    (                       # argument
        \{[^{}]*\}          # braced
      | [A-Za-z0-9]+        # single token
    )
    """,
    re.VERBOSE
)


def fix_font_commands(s):
    def repl(m):
        cmd = m.group(1)
        arg = strip_outer_braces(m.group(2))
        return rf"\math"+cmd+rf"{{{arg}}}"
    return FONT_CMD_RE.sub(repl, s)


# ------------------------------------------------------------
# Main math-content transformation
# ------------------------------------------------------------

TINY_RE = re.compile(r"\\tiny\b")
NOINDENT_RE = re.compile(r"\\noindent\b")
MBOX_RE = re.compile(r"\\mbox\s*\{([^{}]*)\}")


def fix_math_content(s: str) -> str:
    s = TINY_RE.sub("", s)
    s = NOINDENT_RE.sub("", s)
    s = remove_ensuremath(s)

    # \mbox{X} -> \mathrm{X}
    while MBOX_RE.search(s):
        s = MBOX_RE.sub(r"\\mathrm{\1}", s)

    s = fix_font_commands(s)
    return s


# ------------------------------------------------------------
# Inline math handling
# ------------------------------------------------------------

INLINE_MATH_RE = re.compile(r":math:`([^`]*)`")


def fix_inline_math(line: str) -> str:
    def repl(m):
        return f":math:`{fix_math_content(m.group(1))}`"
    return INLINE_MATH_RE.sub(repl, line)


# ------------------------------------------------------------
# Display math handling
# ------------------------------------------------------------

def process_file(lines):
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = fix_inline_math(lines[i])

        if line.lstrip().startswith(".. math::"):
            out.append(line)
            i += 1

            while i < n:
                next_line = lines[i]

                if next_line.strip() == "":
                    out.append(next_line)
                    i += 1
                    continue

                if next_line.startswith(" ") or next_line.startswith("\t"):
                    out.append(fix_math_content(next_line))
                    i += 1
                else:
                    break
            continue

        out.append(line)
        i += 1

    return out


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

def main(path):
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    fixed = process_file(lines)
    path.write_text("".join(fixed), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} FILE.rst")
        sys.exit(1)
    main(sys.argv[1])
