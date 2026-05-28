#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import html


# Match Pandoc section label lines
SECTION_LABEL_RE = re.compile(
    r'^\.\.\s+_`([^`]+)`:\s*$'
)

# Match Pandoc cross-references like `2.2 <#sec:s_dist>`__
CROSS_REF_RE = re.compile(
    r'`(?:\d+(?:\.\d+)*)\s*<#([^>]+)>`__'
)

# Match a section title underline
UNDERLINE_RE = re.compile(r'^[=~`\-^"#*+]{3,}\s*$')


def normalise_label(label):
    """Replace illegal characters in reST labels."""
    return re.sub(r'[^0-9A-Za-z_-]', '_', label)

def normalise_title(title):
    """Remove math in titles as they break the cross-referencing."""
    title = re.sub(r':math:', '', title)
    title = re.sub(r'`', '', title)
    return title


def fix_rst(text):

    # HTML-escaped links like &lt;#sec:foo&gt;
    text = html.unescape(text)

    lines = text.splitlines()
    out = []
    label_to_title = {}
    i = 0

    # Pass 1: fix labels and record titles
    while i < len(lines):
        if lines[i].lstrip().startswith(":"):
            out.append(lines[i])
            i += 1
            continue
        m = SECTION_LABEL_RE.match(lines[i])
        if m:
            old_label = m.group(1)
            new_label = normalise_label(old_label)

            out.append(f".. _{new_label}:")
            i += 1

            # Next non-blank line is the title
            while ( (not lines[i].strip()) and i < len(lines) ):
                out.append(lines[i])
                i += 1

            title = normalise_title(lines[i].strip())
            label_to_title[new_label] = title

        out.append(lines[i])
        i += 1

    fixed = "\n".join(out)

    # Pass 2: fix cross-references
    def repl(m):
        old = m.group(1)
        new = normalise_label(old)

        # Only rewrite if this is a known section label
        if new not in label_to_title:
            return m.group(0)

        title = label_to_title[new]
        return f":ref:`{title} <{new}>`"

    fixed = CROSS_REF_RE.sub(repl, fixed)
    return fixed


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_section_refs.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    fixed = fix_rst(text) + "\n"
    path.write_text(fixed, encoding="utf-8")

    print("✅ Section labels and references fixed")


if __name__ == "__main__":
    main()
