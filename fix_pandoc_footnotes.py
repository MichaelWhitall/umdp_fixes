#!/usr/bin/env python3
"""
Convert pandoc-style numbered footnotes to named, auto-numbered
Sphinx/ReST footnotes, keeping definitions in their existing location.

Example:

  [1]_

  .. [1]
     Footnote text

Becomes:

  [#fnote1]_

  .. [#fnote1]
     Footnote text
"""

import re
import sys
from pathlib import Path


FOOTNOTE_REF_RE = re.compile(r"\[(\d+)\]_")
FOOTNOTE_DEF_RE = re.compile(r"^(\s*)\.\.\s*\[(\d+)\]\s*$")


def convert(lines):
    number_to_label = {}
    next_index = 1

    def label_for(num):
        nonlocal next_index
        if num not in number_to_label:
            number_to_label[num] = f"fnote{next_index}"
            next_index += 1
        return number_to_label[num]

    output = []

    for line in lines:
        # Replace references: [1]_ -> [#fnote1]_
        def repl_ref(m):
            label = label_for(m.group(1))
            return f"[#{label}]_"

        line = FOOTNOTE_REF_RE.sub(repl_ref, line)

        # Replace definitions: .. [1] -> .. [#fnote1]
        m = FOOTNOTE_DEF_RE.match(line)
        if m:
            indent, num = m.groups()
            label = label_for(num)
            line = f"{indent}.. [#{label}]\n"

        output.append(line)

    return output


def main(path):
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    fixed = convert(lines)
    path.write_text("".join(fixed), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} FILE.rst")
        sys.exit(1)
    main(sys.argv[1])
