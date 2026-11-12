from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
d=Document('paper.docx')
for tb in d.tables:
    tblPr=tb._tbl.tblPr
    w=tblPr.find(qn('w:tblW'))
    if w is None:
        w=OxmlElement('w:tblW'); tblPr.append(w)
    w.set(qn('w:w'),'5000'); w.set(qn('w:type'),'pct')
    lay=OxmlElement('w:tblLayout'); lay.set(qn('w:type'),'autofit'); tblPr.append(lay)
    for row in tb.rows:
        for c in row.cells:
            for p in c.paragraphs: p.paragraph_format.first_line_indent=0
d.save('paper.docx')
