import re
import sys

def fix_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Prepend copyright notice to the start of the file
    lines = ["""
.. -----------------------------------------------------------------------------
    (c) Crown copyright Met Office. All rights reserved.
    The file LICENCE, distributed with this code, contains details of the terms
    under which the code may be used.
   -----------------------------------------------------------------------------

.. attention::

   This documentation has been transfered directly from the UM to LFRic;
   It is still a work in progress. There are still UM-specific references
   and terminology that are yet to be updated.

"""[1:]     ] + lines

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python add_copyright.py <filename>")
        sys.exit(1)

    fix_file(sys.argv[1])
