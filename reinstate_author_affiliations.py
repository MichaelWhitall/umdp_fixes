#!/usr/bin/env python3
"""
Reinstate author affiliation footnotes lost by pandoc, inserting them
immediately after the author field list (not at end of document).

Inputs:
  1) original LaTeX file
  2) converted ReST file
"""

import re
import sys
from pathlib import Path


# ----------------------------------------------------------------------
# LaTeX parsing
# ----------------------------------------------------------------------

TITLECONTENT_RE = re.compile(
    r"\\titlecontent\s*\{(.*?)\}",
    re.DOTALL
)

AFFIL_RE = re.compile(
    r"\$\^(\d+)\$\s*(.*?)\\\\",
    re.DOTALL
)


def extract_affiliations(tex_text):
    """
    Return dict: number -> affiliation text
    """
    m = TITLECONTENT_RE.search(tex_text)
    if not m:
        return {}

    block = m.group(1)
    affils = {}

    for num, text in AFFIL_RE.findall(block):
        cleaned = " ".join(text.split())
        affils[num] = cleaned

    return affils


# ----------------------------------------------------------------------
# ReST modification
# ----------------------------------------------------------------------

SUPERSCRIPT_RE = re.compile(r":math:`\^\{(\d+)\}`")


def reinstate(rest_lines, affils):
    output = []
    used = set()

    i = 0
    n = len(rest_lines)
    in_author_block = False

    # First pass: replace superscripts with footnote refs
    for line in rest_lines:

        # Detect start of author block
        if line.startswith(":Author"):
            in_author_block = True

        # Detect end of author block
        elif in_author_block:
            if not (line.startswith(" ") or line.startswith("\t") or line.strip() == ""):
                in_author_block = False

        # Apply replacement ONLY inside author block
        if in_author_block:
            def repl(m):
                num = m.group(1)
                used.add(num)
                return f"[#affil{num}]_"

            line = SUPERSCRIPT_RE.sub(repl, line)

        output.append(line)


    # Second pass: insert footnotes after author field list
    final = []
    inserted = False
    i = 0

    while i < len(output):
        final.append(output[i])

        # Detect end of :Author: field list
        if not inserted and output[i].startswith(":Author"):
            i += 1
            # consume continuation lines
            while i < len(output) and (
                output[i].startswith(" ") or output[i].strip() == ""
            ):
                final.append(output[i])
                i += 1

            # insert footnotes here
            final.append("\n")
            for num in sorted(used, key=int):
                text = affils.get(num, "(affiliation text missing)")
                final.append(
                    f".. [#affil{num}] {text}\n"
                )
            final.append("\n")
            inserted = True
            continue

        i += 1

    return final


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def main(tex_path, rst_path):
    tex_text = Path(tex_path).read_text(encoding="utf-8")
    rst_lines = Path(rst_path).read_text(encoding="utf-8").splitlines(keepends=True)

    affils = extract_affiliations(tex_text)
    if affils:
        fixed = reinstate(rst_lines, affils)
        Path(rst_path).write_text("".join(fixed), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} output.rst")
        sys.exit(1)
    rst_path = Path(sys.argv[1])
    tex_path = rst_path.with_suffix(".tex")
    main(tex_path, rst_path)
