#!/usr/bin/env python3
import re
import sys
from pathlib import Path

#LABEL_RE = re.compile(r'\\label\{([^}]+)\}')
LABEL_RE = re.compile(r'[ \t]*\n*[ \t]*\\label\{([^}]+)\}')
NONUMBER_RE = re.compile(r'[ \t]*\n*[ \t]*\\nonumber|\\notag')

ENDS_WITH_OP = re.compile(r'[+=\-*/,(]$')
STARTS_WITH_OP = re.compile(r'^[+=\-*/,)]')

def is_equation_boundary(prev, curr):
    prev = prev.rstrip()
    curr = curr.lstrip(' &')
    if not prev or not curr:
        return False
    return (
        (not ENDS_WITH_OP.search(prev)) and
        (not NONUMBER_RE.search(prev)) and
        ( ( not STARTS_WITH_OP.search(curr) ) or
          ( '=' in curr and not curr[0]=='=' ) )
    )

def split_on_double_backslash(lines):
    rows = []
    current = []
    for ln in lines:
        parts = re.split(r'(\\\\)', ln)
        for p in parts:
            if p == '\\\\':
                current.append(p)
                rows.append(current)
                current = []
            else:
                current.append(p)
    if any(x.strip() for x in current):
        rows.append(current)
    return rows

def split_aligned_into_groups(aligned_body_lines):
    rows = split_on_double_backslash(aligned_body_lines)
    groups = [[rows[0]]]
    for prev, curr in zip(rows, rows[1:]):
        if is_equation_boundary(''.join(prev), ''.join(curr)):
            groups.append([curr])
        else:
            groups[-1].append(curr)
    return groups

def process_rst(text):
    lines = text.splitlines()
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.lstrip().startswith('.. math::'):
            out.append(line)
            i += 1
            continue

        indent = line[:len(line) - len(line.lstrip())]
        i += 1

        #if i < len(lines) and not lines[i].strip():
        #    i += 1

        block = []
        while i < len(lines) and (lines[i].startswith(indent + '   ') or not lines[i].strip()):
            block.append(lines[i])
            i += 1

        if not any(r'\begin{aligned}' in l for l in block):
            out.append(line)
            out.extend(block)
            continue

        # Extract aligned environment intact
        inner = []
        inside = False
        for l in block:
            if l.strip().startswith(r'\begin{aligned}'):
                inside = True
                continue
            if l.strip().startswith(r'\end{aligned}'):
                inside = False
                continue
            if inside:
                #inner.append(l.strip())
                inner.append(l.rstrip())

        groups = split_aligned_into_groups(inner)

        for group in groups:
            group_text = ''.join('\n'.join(x) for x in group)

            labels = LABEL_RE.findall(group_text)
            if len(labels) > 1:
                raise RuntimeError(f"Multiple labels in aligned equation: {labels}")

            label = labels[0] if labels else None

            cleaned = LABEL_RE.sub('', group_text)
            cleaned = NONUMBER_RE.sub('', cleaned).rstrip()

            # Count rows (number of \\), but ignore instances at end of group
            cleaned = cleaned.rstrip('\\\\')
            num_rows = cleaned.count('\\\\') + 1

            # Clean any trailing blanks after removing final \\
            cleaned = cleaned.rstrip()

            if label:
                out.append(f"{indent}.. math:: :label: {label}")
            else:
                out.append(f"{indent}.. math::")
            out.append("")

            lns = cleaned.splitlines()
            if lns[0] == "":  lns = lns[1:]
            add_ind = None
            ind1 = len(indent) + 3

            if num_rows > 1:  out.append(indent + '   ' + r'\begin{aligned}')
            for ln in lns:
                if len(ln) > 0:
                    if num_rows == 1: ln = ln.replace('&', '')
                    indn = len(ln) - len(ln.lstrip())
                    if add_ind is None:  add_ind = ind1 - indn
                    indn = max( indn + add_ind, ind1 )
                    ln = ' '*indn + ln.lstrip().rstrip()
                out.append(ln)
            if num_rows > 1:  out.append(indent + '   ' + r'\end{aligned}')

            out.append("")

    return "\n".join(out)

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python split_aligned_equations.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding='utf-8')
    fixed = process_rst(text)
    path.write_text(fixed, encoding='utf-8')
    print(f"✅ Processed {path}")

if __name__ == "__main__":
    main()
