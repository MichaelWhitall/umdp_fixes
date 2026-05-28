#!/bin/bash

# Find directory where this script resides;
# assumed to contain the python scripts we'll run below
SCRIPT_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")

# Pass the files to process to AI-generated python code to apply corrections...

module load scitools

echo "Restoring aligned equation labels."
python $SCRIPT_DIR/restore_eqnarray_labels.py $1

echo "Fixing aligned equation regions."
python $SCRIPT_DIR/split_aligned_equations.py $1

echo "Fixing tables"
python $SCRIPT_DIR/convert_tables.py $1

echo "Fixing figures"
python $SCRIPT_DIR/fix_figures_from_latex.py $1

echo "Fixing bibliography"
python $SCRIPT_DIR/fix_bibliography.py $1 refs.bib

echo "Fixing equation cross-referencing."
python $SCRIPT_DIR/fix_eq_refs.py $1

echo "Fixing figure cross-referencing."
python $SCRIPT_DIR/fix_figure_refs.py $1

echo "Fixing table cross-referencing."
python $SCRIPT_DIR/fix_table_refs.py $1

echo "Fixing section cross-referencing."
python $SCRIPT_DIR/fix_section_refs.py $1

echo "Fixing UMDP cross-reference placeholders."
python $SCRIPT_DIR/fix_umdp_refs.py $1

echo "Fixing spurious double-spaces after bullet points"
python $SCRIPT_DIR/fix_dashes.py $1

echo "Fixing latex directives not supported in mathjax"
python $SCRIPT_DIR/fix_mathjax_compat.py $1

echo "Fixing spurious nested math blocks"
python $SCRIPT_DIR/fix_subequations_blocks.py $1

echo "Fixing spurious indents in multiline inline math."
python $SCRIPT_DIR/fix_multiline_inline_math.py $1

echo "Fixing inline math inside bold or italic regions."
python $SCRIPT_DIR/fix_math_in_emphasis.py $1

echo "Fixing footnotes."
python $SCRIPT_DIR/fix_pandoc_footnotes.py $1

echo "Fixing author affiliations notes."
python $SCRIPT_DIR/reinstate_author_affiliations.py $1

echo "Converting non-ASCII characters."
# sed -i 's/\xC2\xA0/ /g' $1
iconv -f UTF-8 -t ASCII//TRANSLIT $1 > tmp.rst
mv tmp.rst $1

echo "Removing trailing whitespace"
python $SCRIPT_DIR/remove_trailing_whitespace.py $1

echo "Adding LFRic copyright notice."
python $SCRIPT_DIR/add_copyright.py $1

echo "Correcting subsubsection header format as-per the style guide."
python $SCRIPT_DIR/fix_subsubsection_underlines.py $1

echo "Wrapping source to max 80 column width as per the style guide."
python $SCRIPT_DIR/split_long_rst_lines.py $1

echo "Finished!"
