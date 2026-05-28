#!/usr/bin/env python3
r"""
fix_eq_refs.py

Move a single \label{...} inside a '.. math::' block up into the directive
as a `:label: <label>` option, and replace inline reference links like
(`[label] <#label>`__) or (`label <#label>`__) with :eq:`label`.

Notes:
- Only moves the label when exactly one \label{...} occurs inside a math block.
  If multiple labels are found (e.g. per-line labels inside align), the block
  is left unchanged and a warning is emitted.
- Preserves leading indentation of equation lines when removing an in-line \label.
"""
from pathlib import Path
import re
import sys

LABEL_RE = re.compile(r'\\label\{\s*([^}\s]+)\s*\}')
#REF_BRACKETED_RE = re.compile(r'(?<![:`])\(?`?\[(?P<label>[^\]]+)\]\s*<\#(?P=label)>\s*`__\)?')
#REF_SIMPLE_RE = re.compile(r'(?<![:`])\(?`?(?P<label>[^\s`<>]+)\s*<\#(?P=label)>\s*`__\)?')
REF_BRACKETED_RE = re.compile(
    r'(?<![:`])(?P<open>\()?`?\[(?P<label>[^\]]+)\]\s*<\#(?P=label)>\s*`__(?P<close>\))?')
REF_SIMPLE_RE = re.compile(
    r'(?<![:`])(?P<open>\()?`?(?P<label>[^\s`<>]+)\s*<\#(?P=label)>\s*`__(?P<close>\))?')

# Match one-line math directives
# e.g. "   .. math:: a=b \label{eq:test}"
INLINE_MATH_RE = re.compile(
    r'^(\s*)\.\.\s+math::\s+(?!:)(.*\S)\s*$'
)


def leading_ws_len(s):
    return len(s) - len(s.lstrip(' \t'))


def process_math_directive(lines, start_idx):
    r"""
    Given file lines and index of a '.. math::' directive, collect the indented block
    and attempt to find/move a single \label{...}.
    Returns (replacement_chunk, consumed_count, changed_bool, warning_or_None).
    """
    dir_line = lines[start_idx]
    dir_indent_len = leading_ws_len(dir_line)
    dir_indent_str = dir_line[:dir_indent_len]

    # If directive already has :label: leave it alone
    if ':label:' in dir_line:
        j = start_idx + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        while j < len(lines):
            if lines[j].strip() == '':
                if leading_ws_len(lines[j]) > dir_indent_len:
                    j += 1
                    continue
                else:
                    break
            if leading_ws_len(lines[j]) > dir_indent_len:
                j += 1
            else:
                break
        consumed = j - start_idx
        return lines[start_idx:start_idx+consumed], consumed, False, None

    # Collect any blank lines immediately after directive (preserve)
    j = start_idx + 1
    pre_blank_lines = []
    while j < len(lines) and lines[j].strip() == '':
        pre_blank_lines.append(lines[j])
        j += 1

    # Collect indented block (lines whose indent > dir indent)
    block_start = j
    while j < len(lines):
        if lines[j].strip() == '':
            if leading_ws_len(lines[j]) > dir_indent_len:
                j += 1
                continue
            else:
                break
        if leading_ws_len(lines[j]) > dir_indent_len:
            j += 1
        else:
            break
    block_end = j
    block_lines = lines[block_start:block_end]
    consumed = block_end - start_idx

    if not block_lines:
        # nothing in the block
        return lines[start_idx:start_idx+consumed], consumed, False, None

    # Find all \label occurrences in block_lines
    matches = []
    for idx, bl in enumerate(block_lines):
        for m in LABEL_RE.finditer(bl):
            matches.append((idx, m.start(), m.end(), m.group(1)))

    if not matches:
        # nothing to move
        chunk = [lines[start_idx]] + pre_blank_lines + block_lines
        return chunk, consumed, False, None

    if len(matches) > 1:
        # multiple labels -> do not move them automatically
        warning = f"Multiple labels ({len(matches)}) in math block at directive line {start_idx+1}; skipping move"
        chunk = [lines[start_idx]] + pre_blank_lines + block_lines
        return chunk, consumed, False, warning

    # Exactly one label: move it
    m_idx, m_s, m_e, label_text = matches[0]
    new_block_lines = []
    for idx, bl in enumerate(block_lines):
        if idx == m_idx:
            # Remove the exact slice [m_s:m_e] from the line, preserving all original leading whitespace
            before = bl[:m_s]
            after = bl[m_e:]
            new_line = before + after
            # Do not collapse leading spaces. Only remove trailing whitespace.
            if new_line.endswith('\n'):
                new_line = new_line.rstrip(' \t\n') + '\n'
            else:
                new_line = new_line.rstrip(' \t')
            # If the line becomes blank (e.g., label was the only thing), skip it.
            if new_line.strip() == '':
                continue
            new_block_lines.append(new_line)
        else:
            new_block_lines.append(bl)

    # Build directive line augmented with :label:
    new_dir_line = dir_line.rstrip('\n') + f' :label: {label_text}\n'
    chunk = [new_dir_line] + pre_blank_lines + new_block_lines
    return chunk, consumed, True, None


def fix_oneline_math_blocks(text):
    out = []

    for line in text.splitlines():
        m = INLINE_MATH_RE.match(line)
        if not m:
            out.append(line)
            continue

        indent = m.group(1)
        content = m.group(2)

        # Only rewrite if a label is present
        lm = LABEL_RE.search(content)
        if not lm:
            out.append(line)
            continue

        label = lm.group(1)
        content = LABEL_RE.sub('', content).strip()

        out.append(f"{indent}.. math:: :label: {label}")
        out.append("")
        out.append(f"{indent}   {content}")

    return "\n".join(out)


def fix_reference_links(text):
    def rep(m):
        lbl = m.group('label')
        open_br = m.group('open')
        close_br = m.group('close')

        if open_br and close_br:
            return f":eq:`{lbl}`"
        else:
            return f"{open_br or ''}:eq:`{lbl}`{close_br or ''}"

    text = REF_BRACKETED_RE.sub(rep, text)
    text = REF_SIMPLE_RE.sub(rep, text)
    return text


def process_file_text(text):
    lines = text.splitlines(keepends=True)
    out_lines = []
    i = 0
    changed_any = False
    warnings = []

    while i < len(lines):
        ln = lines[i]
        stripped = ln.lstrip()
        if stripped.startswith('.. math::'):
            chunk, consumed, changed, warning = process_math_directive(lines, i)
            out_lines.extend(chunk)
            if changed:
                changed_any = True
            if warning:
                warnings.append((i+1, warning))
            i += consumed
        else:
            out_lines.append(ln)
            i += 1

    new_text = ''.join(out_lines)

    new_text = fix_oneline_math_blocks(new_text)

    new_text = fix_reference_links(new_text)
    if new_text != text:
        changed_any = True
    return new_text, changed_any, warnings


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_eq_refs.py file.rst")

    rst_path = Path(sys.argv[1])
    if not rst_path.exists():
        sys.exit("Error: .rst file not found")

    text = rst_path.read_text(encoding="utf-8")

    new_text, changed, warnings = process_file_text(text)

    rst_path.write_text(new_text, encoding="utf-8")

    if changed: print(f"✅ Equation cross-references updated in {rst_path}")
