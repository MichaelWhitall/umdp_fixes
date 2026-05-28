#!/usr/bin/env python3
import re
import sys
from pathlib import Path


# ------------------------------------------------------------
# LaTeX: extract all alignment-type blocks in order
# ------------------------------------------------------------

LATEX_ALIGN_RE = re.compile(
    r"""
    \\begin\{(eqnarray\*?|align\*?|aligned)\}
    (.*?)
    \\end\{\1\}
    (?:\s*\\label\{([^}]+)\})?
    """,
    re.DOTALL | re.VERBOSE,
)


def extract_latex_alignment_blocks(tex_text):
    """
    Return a list of dicts in document order:
      { "env": str, "label": str or None }
    """
    blocks = []
    for m in LATEX_ALIGN_RE.finditer(tex_text):
        env = m.group(1)
        label = m.group(3)
        blocks.append({
            "env": env,
            "label": label,
        })
    return blocks


# ------------------------------------------------------------
# RST: extract all math blocks that contain aligned
# ------------------------------------------------------------

def extract_rst_aligned_blocks(rst_text):
    """
    Return a list of dicts in document order:
      {
        "start": int,
        "end": int,
        "lines": list[str],
        "has_label": bool
      }
    """
    lines = rst_text.splitlines()
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.lstrip().startswith(".. math::"):
            i += 1
            continue

        indent = " " * (len(line) - len(line.lstrip()) + 3)

        start = i
        has_label = ":label:" in line
        i += 1

        # Optional blank line
        if i < n and lines[i].strip() == "":
            i += 1

        body_lines = []
        while i < n and (lines[i].startswith(indent) or
                         lines[i].strip() == ""):
            body_lines.append(lines[i])
            i += 1

        # Only consider blocks that contain aligned
        body_text = "\n".join(body_lines)
        if r"\end{aligned}" in body_text:
            blocks.append({
                "start": start,
                "end": i,
                "lines": lines[start:i],
                "has_label": has_label,
            })

        # else: ignore single-line or non-aligned math

    return blocks


# ------------------------------------------------------------
# Main restoration logic
# ------------------------------------------------------------

def restore_labels_by_index(tex_text, rst_text):
    latex_blocks = extract_latex_alignment_blocks(tex_text)
    rst_blocks = extract_rst_aligned_blocks(rst_text)

    if len(latex_blocks) != len(rst_blocks):
        print(
            f"⚠ Warning: LaTeX alignment blocks ({len(latex_blocks)}) "
            f"!= RST aligned math blocks ({len(rst_blocks)})"
        )

    out_lines = rst_text.splitlines()
    limit = min(len(latex_blocks), len(rst_blocks))

    for i in range(limit):
        latex_label = latex_blocks[i]["label"]
        rst_block = rst_blocks[i]

        # Only transfer label if:
        # - LaTeX block has a label
        # - RST block does NOT already have one
        if latex_label and not rst_block["has_label"]:
            #start = rst_block["start"]
            #out_lines[start] = (
            #    out_lines[start].rstrip() + f" :label: {latex_label}"
            #)
            end = rst_block["end"]
            while not r"\end{aligned}" in out_lines[end]: end = end -1
            ind = len(out_lines[end]) - len(out_lines[end].lstrip())
            out_lines[end] = " "*ind + r"\label{"+latex_label+"}\n" \
                           + out_lines[end]

    return "\n".join(out_lines)


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        sys.exit(
            "Usage: python restore_eqnarray_labels.py file.rst"
        )

    rst_path = Path(sys.argv[1])
    tex_path = rst_path.with_suffix(".tex")

    if not rst_path.exists() or not tex_path.exists():
        sys.exit("Error: matching .rst or .tex file not found")

    tex = tex_path.read_text(encoding="utf-8")
    rst = rst_path.read_text(encoding="utf-8")

    fixed = restore_labels_by_index(tex, rst)
    rst_path.write_text(fixed+"\n", encoding="utf-8")

    print("✅ Restored eqnarray/align labels by index")


if __name__ == "__main__":
    main()
