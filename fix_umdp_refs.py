#!/usr/bin/env python3
import sys
from pathlib import Path
import re

def process_rst(text):
    # pandoc converts the ` characters I inserted in the placeholders for
    # UMDP cross-references to non-ASCII ‘ characters.  Change these back
    # to ` characters.  Also escape the placeholders with `` to avoid
    # undefined reference errors.
    text = re.sub(r":umdp:‘([^‘]+)‘",
                  r"``:umdp:\1``", text)
    #text = re.sub(r":umdp:'([^']+)'",
    #              r":umdp:`\1`", text)
    return text

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python fix_umdp_refs.py file.rst")

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    text = process_rst(text)
    path.write_text(text, encoding="utf-8")

    print(f"✅ Fixed UMDP cross-referencing placeholders in {path}.")

if __name__ == "__main__":
    main()
