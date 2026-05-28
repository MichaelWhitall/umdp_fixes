#!/usr/bin/env python3
import re
import sys
from pathlib import Path
import re


TABLE_DIRECTIVE_RE = re.compile(
    r'^(\s*)\.\.\s+list-table::.*$'
)

NAME_OPTION_RE = re.compile(
    r'^\s*:name:\s*([A-Za-z0-9:_\-]+)\s*$'
)

CROSS_REF_RE = re.compile(
    r"""
    (?:
        (?P<prefix>\b(?:table|tab)\.?)\s+
    )?
    `
      \d+
      \s*
      <\#(?P<label>[^>]+)>
    `__
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)


def collect_table_labels(rst_text):
    """
    Return a set of all table labels defined via '.. list-table::' / ':name:'.
    """
    labels = set()
    lines = rst_text.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        m = TABLE_DIRECTIVE_RE.match(line)
        if not m:
            i += 1
            continue

        base_indent = len(m.group(1))
        i += 1

        # Scan following indented option lines
        while i < n:
            opt = lines[i]
            if opt.strip() == "":
                i += 1
                continue

            if len(opt) - len(opt.lstrip()) <= base_indent:
                break

            m_name = NAME_OPTION_RE.match(opt)
            if m_name:
                labels.add(m_name.group(1).lower())
            i += 1

    return labels


def fix_table_references(rst_text):
    table_labels = collect_table_labels(rst_text)

    def repl(m):
        label = m.group("label")
        prefix = m.group("prefix")

        # Only rewrite if this is a known table label
        if label.lower() not in table_labels:
            return m.group(0)

        if prefix:
            return f":numref:`{prefix.capitalize()} %s <{label}>`"
        else:
            return f":numref:`%s <{label}>`"

    return CROSS_REF_RE.sub(repl, rst_text)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_table_refs.py file.rst")

    rst_path = Path(sys.argv[1])
    if not rst_path.exists():
        sys.exit("Error: .rst file not found")

    text = rst_path.read_text(encoding="utf-8")
    fixed = fix_table_references(text)
    rst_path.write_text(fixed, encoding="utf-8")

    print(f"✅ Table cross-references updated in {rst_path}")


if __name__ == "__main__":
    main()
