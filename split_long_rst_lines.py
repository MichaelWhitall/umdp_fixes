#!/usr/bin/env python3
import sys
from pathlib import Path
import re

MAX_WIDTH = 80

# Grid / simple table detection
TABLE_LINE = re.compile(r'^\s*[+|]')
TABLE_RULE = re.compile(r'^\s*[=~-]{3,}(\s+[=~-]{3,})*\s*$')
#DIRECTIVE = re.compile(r'^(\s*)\.\.\s+([a-zA-Z][a-zA-Z0-9-]*)::')
DIRECTIVE = re.compile(r'^(\s*)\.\.\s+(?:([a-zA-Z][a-zA-Z0-9-]*)::|\[.*?\])')
LIST_ITEM_RE = re.compile(
    r'^(\s*)(?:'
    r'[-+*]\s+|'          # bullet list
    r'(?:\d+|[a-zA-Z])[.)]\s+|'  # enumerated list
    r')'
)
NESTED_RE = re.compile(r'^(\s*)\*\s+-\s+')

SECTION_UNDERLINE_RE = re.compile(r'^([=~`\-^"#*+])\1{2,}\s*$')


def is_section_header(lines, i):
    if i + 1 >= len(lines):
        return False
    title = lines[i].rstrip()
    underline = lines[i + 1].rstrip()
    if not title.strip():
        return False
    m = SECTION_UNDERLINE_RE.match(underline)
    if not m:
        return False
    return len(underline) >= len(title)


def split_line(line, max_width):
    """
    Split a single line into multiple lines <= max_width,
    preserving indentation. If the line starts a directive,
    continuation lines are indented one level deeper.
    """
    m1 = DIRECTIVE.match(line)
    m2 = NESTED_RE.match(line)
    m3 = LIST_ITEM_RE.match(line)
    if m1:
        base_indent = m1.group(1)
        cont_indent = base_indent + "   "
    elif m2:
        base_indent = m2.group(1)
        cont_indent = " " * m2.end()
    elif m3:
        base_indent = m3.group(1)
        cont_indent = " " * m3.end()
    else:
        base_indent = re.match(r'\s*', line).group(0)
        cont_indent = base_indent

    content = line[len(base_indent):]
    lines = []

    first = True
    while len(base_indent) + len(content) > max_width:
        cut = max_width - len(base_indent)
        split_at = content.rfind(" ", 0, cut)

        if split_at == -1:
            break

        if first:
            lines.append(base_indent + content[:split_at].rstrip())
            first = False
        else:
            lines.append(cont_indent + content[:split_at].rstrip())

        content = content[split_at + 1:]

    if first:
        lines.append(base_indent + content)
    else:
        lines.append(cont_indent + content)

    return lines


def process_rst(text):
    out = []
    in_table = False
    lines = text.splitlines()
    i = -1

    while i+1 < len(lines):
        i += 1
        line = lines[i]

        # ✅ Skip section headers entirely
        if is_section_header(lines, i):
            out.append(lines[i])
            out.append(lines[i + 1])
            i += 1
            continue

        # Table detection
        if TABLE_LINE.match(line) or TABLE_RULE.match(line):
            in_table = True
            out.append(line)
            continue

        if in_table:
            if not line.strip():
                in_table = False
            out.append(line)
            continue

        # Line is acceptable
        if len(line) <= MAX_WIDTH:
            out.append(line)
            continue

        # Too long: split conservatively
        out.extend(split_line(line, MAX_WIDTH))

    return "\n".join(out)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python split_long_rst_lines.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    fixed = process_rst(text) + "\n"
    path.write_text(fixed, encoding="utf-8")

    print(f"✅ Split lines longer than {MAX_WIDTH} chars in {path}")


if __name__ == "__main__":
    main()
