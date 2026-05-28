#!/usr/bin/env python3
import sys
from pathlib import Path
import re
import math
from textwrap import fill

ANCHOR_IMAGE = "blank.svg"

# ------------------------------------------------------------
# LaTeX parsing
# ------------------------------------------------------------

FIGURE_RE = re.compile(
    r"\\begin\{figure\}.*?"
    r"(?P<body1>.*?)"
    r"\\label\{(?P<label>[^}]+)\}.*?"
    r"(?P<body2>.*?)"
    r"\\end\{figure\}",
    re.DOTALL,
)

INCLUDE_RE = re.compile(
    r"(?:\\scalebox\{(?P<scale>[\d.]+)\}\{)?"
    r"\\includegraphics(?:\[(?P<opts>[^\]]+)\])?\{(?P<img>[^}]+)\}"
)


def extract_width(opts, scale):
    # Case 1: width=...\\textwidth
    if opts:
        m = re.search(r"width\s*=\s*([\d.]+)\s*\\(?:textwidth|columnwidth)",
                      opts)
        if m:
            return float(m.group(1))

        # Case 2: scale=...
        m = re.search(r"scale\s*=\s*([\d.]+)", opts)
        if m:
            return float(m.group(1))

    # Case 3: \\scalebox{...}{\\includegraphics}
    if scale:
        return float(scale)

    return None


def extract_braced_argument(text, start):
    """
    Extract a {...} argument starting at position start (which should
    point just after the opening '{'), handling nested braces.
    Returns (content, end_index).
    """
    depth = 1
    i = start
    out = []

    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
            out.append(text[i])
        elif text[i] == "}":
            depth -= 1
            if depth > 0:
                out.append(text[i])
        else:
            out.append(text[i])
        i += 1

    return "".join(out), i


def parse_latex_figures(tex):
    figs = {}

    for m in FIGURE_RE.finditer(tex):
        body = m.group("body1") + m.group("body2")
        label = m.group("label")

        images = []
        widths = []

        for im in INCLUDE_RE.finditer(body):
            img = im.group("img")
            scale = im.group("scale")
            opts = im.group("opts")
            w = extract_width(opts, scale)
            images.append(img)
            widths.append(w)

        caption = ""
        for mcap in re.finditer(r"\\caption(?:arb)?\{", body):
            start = mcap.end()
            caption, _ = extract_braced_argument(body, start)
            caption = " ".join(caption.split())
            # Convert latex caption \ref, \cite, $math$ to pandoc forms
            caption = re.sub(r'\\ref\{\s*([^}]+?)\s*\}',
                             r'`[\1] <#\1>`__', caption)
            caption = re.sub(r'\\cite\{([^}]+)\}',
                             r':raw-latex:`\\cite{\1}`', caption)
            caption = re.sub(r'\$\s*(.+?)\s*\$',
                             r':math:`\1`', caption)
            break

        if any(w is None for w in widths):
            widths = [1.0 / len(images)] * len(images)

        figs[label] = {
            "images": images,
            "widths": widths,
            "caption": caption,
        }

    return figs


# ------------------------------------------------------------
# Layout logic
# ------------------------------------------------------------

def choose_grid(widths):
    n = len(widths)
    total = sum(widths)
    avg = total / n

    if total <= 1.05:
        return 1, n
    if n == 4 and abs(avg - 0.5) < 0.1:
        return 2, 2
    if n == 6 and 0.25 < avg < 0.34:
        return 2, 3

    rows = math.ceil(total)
    cols = math.ceil(n / rows)
    return rows, cols


# ------------------------------------------------------------
# Grid table generation
# ------------------------------------------------------------

def list_table(images, widths, rows, cols):
    """
    Build a reST list-table for figure panels.

    images  : list of image filenames (without extension if you prefer)
    widths  : list of width fractions (0–1) corresponding to images
    rows    : number of rows
    cols    : number of columns
    """

    # Convert width fractions to integer percentages per column
    col_widths = []
    for c in range(cols):
        # average width of images that will appear in this column
        ws = []
        for r in range(rows):
            idx = r * cols + c
            if idx < len(widths):
                ws.append(widths[idx])
        if ws:
            col_widths.append(int(round(100 * sum(ws) / len(ws))))
        else:
            col_widths.append(int(round(100 / cols)))

    lines = []
    lines.append(".. list-table::")
    lines.append("   :align: center")
    lines.append(
        "   :widths: " + " ".join(str(w) for w in col_widths)
    )
    lines.append("")

    idx = 0
    for _ in range(rows):
        row_imgs = []
        row_widths = []

        for _ in range(cols):
            if idx < len(images):
                row_imgs.append(images[idx])
                row_widths.append(int(round(widths[idx] * 100 * cols)))
                idx += 1
            else:
                row_imgs.append(None)
                row_widths.append(None)

        # First cell in row
        first = True
        for img, pct in zip(row_imgs, row_widths):
            if first:
                prefix = "   * - "
                first = False
            else:
                prefix = "     - "

            if img is None:
                lines.append(prefix)
                continue

            lines.append(prefix + f".. image:: {img}")
            if pct is not None and pct < 100:
                lines.append(" "*len(prefix + ".. image:: ") +
                             ":width: {}%".format(pct))

    return lines


# ------------------------------------------------------------
# RST generation
# ------------------------------------------------------------

def build_figure(label, fig):
    images = fig["images"]
    widths = fig["widths"]
    caption = fig["caption"]

    rows, cols = choose_grid(widths)

    for i in range(len(images)):
        images[i] = images[i].replace(".epsi", "")
        images[i] = images[i].replace(".eps", "")
        images[i]+=".svg"

    lines = []
    lines.append(f".. figure:: {ANCHOR_IMAGE}")
    lines.append(f"   :name: {label}")
    lines.append("")

    if caption:
        #for ln in fill(caption, width=76).splitlines():
        #    lines.append(f"   {ln}")
        lines.append("   "+caption)
        lines.append("")

    table = list_table(images, widths, rows, cols)
    for ln in table:
        if len(ln) > 0:  ln = "   " + ln
        lines.append(ln)
    lines.append("")
    lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------
# RST replacement
# ------------------------------------------------------------

def fix_rst(rst, figs):
    lines = rst.splitlines()
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Match container:: float with optional leading whitespace
        m = re.match(r'^(\s*)\.\.\s+container::\s+float\s*$', line)
        if m:
            base_indent = m.group(1)
            start = i
            label = None
            i += 1

            # Look for :name:
            while i < n and (lines[i].startswith(base_indent + " ") or
                             not lines[i].strip()):
                stripped = lines[i].strip()
                if stripped.startswith(":name:"):
                    label = stripped.split(":name:", 1)[1].strip()
                i += 1

            # Consume all following indented or blank lines
            while i < n and (
                lines[i].startswith(base_indent + " ")
                or not lines[i].strip()
            ):
                i += 1

            # Replace entire Pandoc figure block
            if label in figs:
                fig_rst = build_figure(label, figs[label])
                for ln in fig_rst.splitlines():
                    out.append(base_indent + ln)
            else:
                # Fallback: keep original block unchanged
                out.extend(lines[start:i])

            continue

        out.append(line)
        i += 1

    return "\n".join(out)


# ------------------------------------------------------------
# Tidy-up loose pandoc-generated image stuff
# ------------------------------------------------------------

def remove_image_substitutions(rst):
    """
    Remove Pandoc-generated image substitution definitions,
    but preserve surrounding spacing.
    """
    lines = rst.splitlines()
    out = []
    skip_next_blank = False

    for line in lines:
        #if re.match(r"\.\.\s+\|image\d+\|\s+image::", line):
        if re.match(r"\.\.\s+\|image\d*\|\s+image::.*$", line):
            # Drop this line and mark that we may want to skip
            # at most ONE following blank line or width spec
            skip_next_blank = True
            continue

        if skip_next_blank:
            if (not line.strip()) or (line[:10]=="   :width:"):
                # Skip only a single blank line or width spec
                skip_next_blank = False
                continue
            skip_next_blank = False

        out.append(line)

    return "\n".join(out)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_figures_from_latex.py file.rst")

    rst_path = Path(sys.argv[1])
    tex_path = rst_path.with_suffix(".tex")

    if not rst_path.exists() or not tex_path.exists():
        sys.exit("Error: matching .rst or .tex file not found")

    tex = tex_path.read_text(encoding="utf-8")
    rst = rst_path.read_text(encoding="utf-8")

    figs = parse_latex_figures(tex)
    fixed = fix_rst(rst, figs) + "\n"

    fixed = remove_image_substitutions(fixed)

    rst_path.write_text(fixed, encoding="utf-8")
    print("✅ Figures rebuilt using grid tables with transparent anchor")


if __name__ == "__main__":
    main()
