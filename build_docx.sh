#!/bin/sh
# Builds paper.docx from paper.tex (requires pandoc, python-docx). ref.docx holds the styles.
python3 prep_pandoc.py
pandoc paper_pandoc.tex -f latex -t docx --citeproc --bibliography references.bib \
  --reference-doc ref.docx --number-sections -M link-citations=true \
  -M reference-section-title=References -o paper.docx
python3 fix_tables.py
rm -f paper_pandoc.tex
