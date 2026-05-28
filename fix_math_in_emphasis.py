#!/usr/bin/env python3
import sys
from pathlib import Path
import re

EMPH_RE = re.compile(
    r'(?<!\\)'        # ✅ not preceded by backslash
    r'(\*\*|\*)'
    r'(?=\S)'         
    r'(.+?)'
    r'(?<=\S)'
    r'(?<!\\)'        # ✅ closing marker also not escaped
    r'\1',
    re.DOTALL
)

MATH_RE = re.compile(r':math:`([^`]+)`')

BACKTICK_RE = re.compile(r'`[^`]*`')

PLACEHOLDER = "__STAR__"  # unlikely to appear naturally


def protect_stars_in_math_blocks(text):
    lines = text.splitlines(keepends=True)

    result = []
    in_math_block = False

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        # ---- Detect start of math block ----
        if stripped.startswith(".. math::"):
            in_math_block = True
            indent = len(line) - len(stripped)
            result.append(line.replace("*", PLACEHOLDER))
            continue

        if in_math_block:
            # Check if this line belongs to the math block
            if line.strip() == "":
                # Blank lines are allowed inside math blocks
                result.append(line)
                continue

            if len(line) - len(stripped) >= indent + 3:
                # Still inside math block → replace *
                result.append(line.replace("*", PLACEHOLDER))
                continue
            else:
                # End of math block
                in_math_block = False

        # Normal line
        result.append(line)

    return "".join(result)

def protect_stars_in_backticks(text):
    def repl(m):
        span = m.group(0)
        # replace * only inside this span
        return span.replace('*', PLACEHOLDER)
    
    return BACKTICK_RE.sub(repl, text)

def restore_stars(text):
    return text.replace(PLACEHOLDER, '*')


def split_emphasis_around_math(text):

    def process_emph(m):
        marker = m.group(1)
        content = m.group(2)

        if ":math:`" not in content:
            return m.group(0)

        result = content
        offset = 0  # track shifting positions

        for math_match in list(MATH_RE.finditer(content)):
            start, end = math_match.span()
            inner = math_match.group(1)

            # Apply bold only for **
            if marker == '**' and not inner.startswith(r'\boldsymbol'):
                new_inner = rf'\boldsymbol{{{inner}}}'
            else:
                new_inner = inner

            math_replacement = f":math:`{new_inner}`"

            # Update positions with offset
            start += offset
            end += offset

            # Replace math content
            result = result[:start] + math_replacement + result[end:]
            delta = len(math_replacement) - (end - start)

            offset += delta
            end = start + len(math_replacement)

            # ---- Insert left marker ----
            i = start - 1
            while i >= 0 and result[i] in (' ', '\n'):
                i -= 1

            insert_left = i + 1

            # Check if there was no whitespace
            if insert_left == start:
                result = result[:start] + " " + result[start:]
                start += 1
                end += 1
                offset += 1

            result = result[:insert_left] + marker + result[insert_left:]
            offset += len(marker)
            start += len(marker)
            end += len(marker)

            # ---- Insert right marker ----
            i = end
            while i < len(result) and result[i] in (' ', '\n'):
                i += 1

            insert_right = i

            # If no whitespace, add space
            if insert_right == end:
                result = result[:end] + " " + result[end:]
                insert_right += 1
                offset += 1

            result = result[:insert_right] + marker + result[insert_right:]
            offset += len(marker)

        result = f"{marker}{result}{marker}"

        # Remove any empty emphasized regions left at the start or end
        double = marker+marker
        result = result.removeprefix(double+' ').removesuffix(' '+double)

        return result

    return EMPH_RE.sub(process_emph, text)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_math_in_emphasis.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    text = protect_stars_in_backticks(text)
    text = protect_stars_in_math_blocks(text)
    text = split_emphasis_around_math(text)
    text = restore_stars(text)

    path.write_text(text, encoding="utf-8")

    print(f"✅ Fixed in-line math inside bold or italic text in {path}.")

if __name__ == "__main__":
    main()
