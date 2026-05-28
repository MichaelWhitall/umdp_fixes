import re
import sys
from pathlib import Path


# -------------------------------------------------------------
#  CELL MERGING LOGIC (Fixes your hyphens/spaces issue)
# -------------------------------------------------------------

ROLE_RE = re.compile(r':[a-zA-Z0-9_-]+:`')

def join_cell_lines(lines):
    """
    Join wrapped cell text preserving:
      - normal prose (joined with spaces)
      - inline backtick spans as atomic (no spaces inside)
      - :math:`...` spans as atomic (no spaces inside)
    """

    frags = [ln.strip() for ln in lines if ln.strip()]
    if not frags:  return ""
    if not len(frags) > 1:  return frags[0]

    result = frags[0]

    # Loop through remaining frags
    in_region = False
    i = 1
    while ( i < len(frags) ):

        # Flip in / out of region if frag has odd number of ` characters
        if frags[i-1].count("`") % 2 > 0:  in_region = not in_region

        if ( ( in_region and ( not frags[i].startswith("<#") ) ) or
             ( len(ROLE_RE.findall(frags[i-1]+frags[i])) >
         len(ROLE_RE.findall(frags[i-1])) + len(ROLE_RE.findall(frags[i])) ) or
#             ( (frags[i-1]+frags[i]).count(":math:`") >
#               frags[i-1].count(":math:`") + frags[i].count(":math:`") ) or
             ( (frags[i-1]+frags[i]).count("`__") >
               frags[i-1].count("`__") + frags[i].count("`__") )
           ):
            # Append frag with no whitespace if inside a "`" region,
            # or if boundary splits a ":math:`" or "`__"
            result = result + frags[i]
        else:
            # Otherwise append frag with whitespace
            result = result + " " + frags[i]

        i = i + 1

    return result


# -------------------------------------------------------------
#  PARSE GRID TABLE
# -------------------------------------------------------------

def is_grid_sep(line):
    return bool(re.match(r'^\+(?:[+=-]+)\+(?:[+=-]+\+)*\s*$',
                         line.strip()))

def is_simple_sep(line):
    return bool(re.match(r'^(?:[=-]{2,})(?:\s+(?:[=-]{2,}))+\s*$',
                         line.strip()))

def is_grid_border(line):
    return is_grid_sep(line) or is_simple_sep(line)

def parse_grid_table(table_lines):
    """
    Parse a grid table into rows of cells, using column positions
    derived from +-----+ separator lines.
    """

    rows = []
    i = 0
    sep = ''

    # find first separator line (column layout)
    while i < len(table_lines):
        grid_sep = is_grid_sep(table_lines[i].lstrip())
        simple_sep = is_simple_sep(table_lines[i].lstrip())
        if grid_sep or simple_sep:
            sep = table_lines[i].rstrip('\n')
            break
        i += 1

    if not len(sep)>0:
        return []  # not a table

    # find column boundaries
    if grid_sep:
        col_positions = [idx for idx, ch in enumerate(sep) if ch == '+']
    elif simple_sep:
        sep = '  '+sep+'  '
        col_positions = [idx-2 for idx in range(1,len(sep)-1)
                         if ( sep[idx]==' ' and ( (not sep[idx-1]==' ') or
                                                  (not sep[idx+1]==' ') ) )]

    ncols = len(col_positions) - 1

    # process rows
    i += 1
    current_row = []

    while i < len(table_lines):

        grid_border = is_grid_border(table_lines[i].lstrip())

        # Flush existing row content
        if (grid_border or simple_sep) and current_row:
            rows.append(current_row)
            current_row = []
        # Skip through row-border lines
        if grid_border:
            i += 1
            continue

        # Start new row structure
        if not current_row:  current_row = [[] for _ in range(ncols)]
        # Loop over columns
        for c in range(ncols):
            start = col_positions[c]
            end   = col_positions[c+1]
            # slice column content (skip leading '|' and trim spaces)
            cell_text = (table_lines[i][start+1:end].rstrip('\n')).strip()
            if cell_text:  current_row[c].append(cell_text)

        i += 1

    # Merge lines inside each cell properly
    merged = []
    for row in rows:
        merged.append([join_cell_lines(cell) for cell in row])

    return merged


# -------------------------------------------------------------
#  REMOVE SURROUNDING DIRECTIVES
# -------------------------------------------------------------

def strip_preceding_table_block(lines, table_start):
    """
    Remove the directive block immediately preceding a grid table, e.g.:

      .. container:: center
         .. container::
            :name: tab:xxx
            .. table:: Title

    Returns (new_lines, new_table_start_index).
    """

    i = table_start - 1

    while i >= 0:
        line = lines[i]

        # Blank lines are allowed inside the block
        if line.strip() == "":
            i -= 1
            continue

        # Table-related directives (possibly indented)
        if (
            re.match(r'\s*\.\.\s+container::', line)
            or re.match(r'\s*\.\.\s+table::', line)
            or re.match(r'\s*:name:\s+\S+', line)
        ):
            i -= 1
            continue

        # Any other content => stop
        break

    # Delete lines from i+1 up to table_start-1
    return lines[: i + 1] + lines[table_start:], i + 1


# -------------------------------------------------------------
#  EXTRACT TITLE / NAME IF AVAILABLE
# -------------------------------------------------------------

def extract_table_metadata(block_lines):
    """
    Extract multi-line table title and :name: from a Pandoc table block.
    """
    title_lines = []
    name = ""

    i = 0
    n = len(block_lines)

    while i < n:
        line = block_lines[i]

        # Match start of table title
        m = re.match(r'\s*\.\.\s*table::\s*(.*)', line)
        if m:
            # First line of title
            title_lines.append(m.group(1).strip())
            i += 1

            # Consume indented continuation lines
            while i < n:
                cont = block_lines[i]
                if cont.startswith(" ") and cont.strip():
                    title_lines.append(cont.strip())
                    i += 1
                else:
                    break
            continue

        # Extract :name:
        m = re.match(r'\s*:name:\s*([A-Za-z0-9:_-]+)', line)
        if m:
            name = m.group(1).strip()

        i += 1

    title = " ".join(title_lines) if title_lines else ""
    return title, name


# -------------------------------------------------------------
#  CONVERT TO LIST-TABLE
# -------------------------------------------------------------

def convert_to_list_table(rows, title, name):
    out = []
    if len(title)>0: 
        out.append(f".. list-table:: {title}")
    else:
        out.append(f".. list-table::")
    if len(name)>0:
        out.append(f"   :name: {name}")
    out.append("   :header-rows: 1")
    out.append("")

    header = rows[0]
    out.append("   * - " + "\n     - ".join(header))

    for row in rows[1:]:
        out.append("\n   * - " + "\n     - ".join(row))

    return "\n".join(out) + "\n"


# -------------------------------------------------------------
#  MAIN: CONVERT ALL TABLES IN A FILE
# -------------------------------------------------------------

def find_table_block_start(lines, grid_start):
    """
    Find the start index of the container/table directive block
    immediately preceding a grid table.
    """
    i = grid_start - 1

    while i >= 0:
        line = lines[i]

        if line.strip() == "":
            i -= 1
            continue
        if lines[i][0] == " ":
            i -= 1
            continue

        break

    return i


def find_grid_start(lines, table_start):
    i = table_start
    while i < len(lines) and not is_grid_border(lines[i]):
        i += 1
    return i


def find_grid_end(lines, grid_start):
    i = grid_start
    while i < len(lines) and lines[i].strip() != "":
        i += 1
    return i


def convert_all_tables_in_file(input_path):
    text = Path(input_path).read_text()
    lines = text.splitlines()

    out_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Detect .. table:: directive, or grid-table start-line
        # (grid-table blocks can be inserted without a .. table:: directive)
        if (line.lstrip().startswith('.. table::') or
            is_grid_sep(line.lstrip())):
            table_start = i

            # Find start of table grid
            grid_start = find_grid_start(lines, table_start)

            # Find full table block
            block_start = find_table_block_start(lines, grid_start)
            grid_end = find_grid_end(lines, grid_start)

            # REMOVE already-emitted table directives from OUTPUT
            # Number of lines already written that belong to this block:
            emitted_block_len = table_start - block_start
            if emitted_block_len > 0:
                del out_lines[-emitted_block_len:]

            # Extract metadata BEFORE deleting anything
            meta_block = lines[block_start:grid_start]
            title, name = extract_table_metadata(meta_block)

            # Parse grid table
            table_block = lines[grid_start:grid_end]
            rows = parse_grid_table(table_block)

            # Emit replacement
            list_table = convert_to_list_table(rows, title, name)
            out_lines.append(list_table)

            # Skip entire original block
            i = grid_end + 1
            continue

        # Normal line
        out_lines.append(line)
        i += 1

    out_lines.append("")

    #output_path = str(Path(input_path).with_suffix(".converted.rst"))
    output_path = input_path
    Path(output_path).write_text("\n".join(out_lines))

    print(f"✅ Converted file written to: {output_path}")


# -------------------------------------------------------------
#  CLI ENTRY POINT
# -------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_tables.py <input.rst>")
        sys.exit(1)

    convert_all_tables_in_file(sys.argv[1])
