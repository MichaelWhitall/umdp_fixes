#!/usr/bin/env python3
"""
Fix pandoc-generated math blocks that contain multiple
\\begin{equation} blocks by converting them into a single
\\begin{aligned} block.

Works on ReST files.
"""

import re
import sys
from pathlib import Path


BEGIN_EQ_RE = re.compile(r'\\begin\{equation\}')
END_EQ_RE   = re.compile(r'\\end\{equation\}')


def process_math_block(block_lines):
    """
    Given lines belonging to a math block, transform if needed.
    """
    # Join for easier regex handling
    text = "".join(block_lines)

    # Find all equation contents
    parts = re.split(r'\\begin\{equation\}|\\end\{equation\}', text)

    # parts will look like:
    # [pre, eq1, mid, eq2, ..., post]
    # We want only the actual equation contents
    equations = []
    for i in range(1, len(parts), 2):
        eq = parts[i].strip()
        if eq:
            equations.append(eq)

    # If fewer than 2 equations, do nothing
    if len(equations) <= 1:
        return block_lines

    # Build aligned block
    aligned_lines = []
    aligned_lines.append("   \\begin{aligned}\n")

    for i, eq in enumerate(equations):
        # indent properly
        lines = eq.splitlines()
        for j, line in enumerate(lines):
            line = line.rstrip("\n")
            if j == 0:
                aligned_lines.append(f"   {line}")
            else:
                aligned_lines.append(f"\n   {line}")

        # add \\ except for last equation
        if i != len(equations) - 1:
            aligned_lines.append(" \\\\\n")
        else:
            aligned_lines.append("\n")

    aligned_lines.append("   \\end{aligned}\n")

    return ["\n"] + aligned_lines + ["\n"]


def process_file(lines):
    output = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Detect math block
        if line.lstrip().startswith(".. math::"):
            output.append(line)
            i += 1

            block = []

            # Collect indented math block
            while i < n:
                next_line = lines[i]

                if next_line.strip() == "":
                    block.append(next_line)
                    i += 1
                    continue

                if next_line.startswith(" ") or next_line.startswith("\t"):
                    block.append(next_line)
                    i += 1
                else:
                    break

            # Process block
            new_block = process_math_block(block)
            output.extend(new_block)
            continue

        output.append(line)
        i += 1

    return output


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
