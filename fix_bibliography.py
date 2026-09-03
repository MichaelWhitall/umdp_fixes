#!/usr/bin/env python3
import re
import sys
from pathlib import Path
import textwrap


def latex_to_unicode(s):
    """
    Convert basic LaTeX accent commands to Unicode.
    """

    replacements = {
        r"\\'a": "á", r"\\'e": "é", r"\\'i": "í", r"\\'o": "ó", r"\\'u": "ú",
        r"\\'c": "ć",
        r'\\"a': "ä", r'\\"o': "ö", r'\\"u': "ü",
        r"\\u{s}": "š",
        r"\\'{c}": "ć",
        r"\\v{s}": "š",
    }

    # Replace braced forms: {\'{c}} → ć
    for pattern, repl in replacements.items():
        s = re.sub(r'\{' + pattern + r'\}', repl, s)
        s = re.sub(pattern, repl, s)

    # Remove remaining braces
    #s = re.sub(r'[{}]', '', s)

    return s

def clean_field(text, macros=None):
    if not text:
        return ""
    text = " ".join(text.split())
    if macros and text in macros:
        return macros[text]
    return text

def indent_paragraph(text, indent=3, width=78):
    wrapper = textwrap.TextWrapper(
        width=width,
        subsequent_indent=" " * indent,
        initial_indent=" " * indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapper.fill(text)

def parse_bibtex_strings(text):
    strings = {}
    string_re = re.compile(
        r'@string\s*\{\s*(\w+)\s*=\s*"(.*?)"\s*\}',
        re.IGNORECASE | re.DOTALL
    )
    for m in string_re.finditer(text):
        strings[m.group(1)] = m.group(2)
    return strings

def find_used_links(rst_text):
    """
    Find used hyperlink references: `Label`_
    """
    return set(
        m.group(1)
        for m in re.finditer(r'`([^`]+)`_', rst_text)
    )

def make_readable_label(author_field, year):
    """
    Generate a readable citation label like:
      Smith (1990)
      Rogers and Yau (1989)
      Brooks et al. (2005)

    Removes all initials / given names and keeps surnames only.
    """
    if not author_field:
        return f"Anon ({year})"

    authors = [a.strip() for a in author_field.split(" and ")]
    surnames = []

    for a in authors:
        if "," in a:
            # BibTeX form: "Surname, Initials"
            surnames.append(a.split(",", 1)[0].strip())
        else:
            # BibTeX form: "Initials Surname"
            parts = a.split()
            surnames.append(parts[-1])

    if len(surnames) == 1:
        return f"{surnames[0]} ({year})"
    elif len(surnames) == 2:
        return f"{surnames[0]} and {surnames[1]} ({year})"
    else:
        return f"{surnames[0]} et al. ({year})"

# ------------------------------------------------------------
# BibTeX parsing
# ------------------------------------------------------------

def extract_braced_value(text, start):
    """
    Extract a {...} block starting at 'start', handling nested braces.
    Returns (value, end_index)
    """
    assert text[start] == '{'
    depth = 0
    i = start

    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                # include outer braces
                return text[start+1:i], i + 1
        i += 1

    raise ValueError("Unmatched braces")

def parse_bibtex(text):
    entries = {}
    raw_entries = re.split(r'\n@', text)

    for raw in raw_entries:
        raw = raw.strip()
        if not raw:
            continue
        if not raw.startswith("@"):
            raw = "@" + raw

        if raw.lower().startswith("@string"):
            continue

        m = re.match(r'@\w+\s*\{\s*([^,]+)\s*,', raw)
        if not m:
            continue

        key = m.group(1).strip().lower()
        body = raw[m.end():].rsplit("}", 1)[0]

        fields = {}
        i = 0
        while i < len(body):
            # match field name
            m = re.match(r'\s*(\w+)\s*=\s*', body[i:])
            if not m:
                i += 1
                continue

            name = m.group(1).lower()
            i += m.end()

            # now parse value
            if i < len(body) and body[i] == '{':
                value, i = extract_braced_value(body, i)
            elif i < len(body) and body[i] == '"':
                j = i + 1
                while j < len(body) and body[j] != '"':
                    j += 1
                value = body[i+1:j]
                i = j + 1
            else:
                m2 = re.match(r'(\w+)', body[i:])
                if m2:
                    value = m2.group(1)
                    i += m2.end()
                else:
                    continue

            # skip trailing commas/spaces
            while i < len(body) and body[i] in ', \n\t':
                i += 1

            fields[name] = value.strip()
            # Remove leftover stray curly brackets
            fields[name] = re.sub(r'[{}]', '', fields[name])

        entries[key] = fields

    return entries


def bibtex_to_rst(entries, macros, used_keys, label_map):
    lines = []

    for key, f in entries.items():
        if key not in used_keys:
            continue

        label = label_map[key]

        author = clean_field(f.get("author", ""))
        year = clean_field(f.get("year", "n.d."))
        title = clean_field(f.get("title", ""))
        journal = clean_field(f.get("journal", ""), macros)
        institution = clean_field(f.get("institution", ""))
        volume = clean_field(f.get("volume", ""))
        pages = clean_field(f.get("pages", "")).replace("--", "–")
        doi = clean_field(f.get("doi", ""))

        # Hyperlink target
        lines.append(f".. _{label}:")
        lines.append("")
        #lines.append(indent_paragraph(f"**{label}**"))
        lines.append(indent_paragraph(f"{author} ({year})."))

        if title:
            lines.append(indent_paragraph(f"*{title}*."))

        if journal:
            ref = journal
            if volume:
                ref += f", {volume}"
            if pages:
                ref += f", {pages}"
            lines.append(indent_paragraph(ref + "."))

        elif institution:
            lines.append(indent_paragraph(institution + "."))

        if doi:
            doi = doi.replace("https://doi.org/", "").replace("doi:", "")
            lines.append(indent_paragraph(f"https://doi.org/{doi}"))

        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------
# Citation fixes
# ------------------------------------------------------------

def fix_citations(text):
    def cite_block(keys):
        return ", ".join(f"`{k.strip().lower()}`_" for k in keys.split(","))

    def repl(m):
        note1 = m.group(1)  # first [...]
        note2 = m.group(2)  # second [...]
        keys = cite_block(m.group(3))

        if note1 is None and note2 is None:
            # \cite{key}
            return keys

        note = note1 or note2 or ""

        if note == "":
            # \cite[]{key} or \cite[][]{key}
            return f"[{keys}]"

        # \cite[text]{key} or \cite[text][]{key}
        sep = "" if note.endswith((" ", "~")) else " "
        return f"[{note}{sep}{keys}]"

    text = re.sub(
        r"(?:\:raw-latex:`)?\\cite[a-z]*(?:\[([^]]*)\])?(?:\[([^]]*)\])?\{([^}]+)\}`?",
        repl,
        text,
    )

    return text


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python fix_bibliography.py file.rst refs.bib")

    rst_path = Path(sys.argv[1])
    bib_path = Path(sys.argv[2])

    rst = rst_path.read_text(encoding="utf-8")
    bib = bib_path.read_text(encoding="utf-8")

    bib = re.sub(r"`", "'", bib)  # Remove backticks as they break rst!
    bib = latex_to_unicode(bib)   # Convert latex special characters to unicode

    macros = parse_bibtex_strings(bib)
    entries = parse_bibtex(bib)

    # Build readable labels
    label_map = {}
    used_labels = set()
    for key, f in entries.items():
        label = make_readable_label(
            clean_field(f.get("author", "")),
            clean_field(f.get("year", "n.d."))
        )
        base = label
        suffix = 1
        while label in used_labels:
            suffix += 1
            label = f"{base} {suffix}"
        label_map[key] = label
        used_labels.add(label)

    rst = fix_citations(rst)

    # Replace keys with labels in inline links
    for key, label in label_map.items():
        #print( key, "    ", label )
        rst = re.sub(
            rf"`{re.escape(key)}`_",
            lambda m: f"`{label}`_",
            rst
        )

    used_labels = find_used_links(rst)
    reverse_label_map = {v: k for k, v in label_map.items()}

    used_keys = {
        reverse_label_map[l] for l in used_labels
        if l in reverse_label_map
    }

    if "References\n" not in rst:
        rst += "\n\nReferences\n==========\n\n"
        rst += bibtex_to_rst(entries, macros, used_keys, label_map)

    rst_path.write_text(rst, encoding="utf-8")
    print(f"✅ Bibliography and hyperlinks fixed in {rst_path}")


if __name__ == "__main__":
    main()
