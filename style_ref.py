from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
d=Document('ref.docx')
S={s.name:s for s in d.styles}
def font(st,size=None,bold=None,italic=None):
    r=st.font; r.name='Cambria'
    rpr=st.element.get_or_add_rPr(); rf=rpr.find(qn('w:rFonts'))
    if rf is None: rf=rpr.makeelement(qn('w:rFonts'),{}); rpr.insert(0,rf)
    for a in ('w:asciiTheme','w:hAnsiTheme','w:cstheme','w:eastAsiaTheme'):
        rf.attrib.pop(qn(a),None)
    for a in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'): rf.set(qn(a),'Cambria')
    if size: r.size=Pt(size)
    if bold is not None: r.bold=bold
    if italic is not None: r.italic=italic
    if st.name!='Hyperlink': r.color.rgb=RGBColor(0,0,0)
for n,s in S.items():
    if s.type==1 or n=='Hyperlink':
        try: font(s)
        except Exception: pass
for n in ['Normal','Body Text','First Paragraph','Compact','Bibliography']: font(S[n],11)
for n in ['Body Text','First Paragraph','Abstract','Bibliography']:
    pf=S[n].paragraph_format; pf.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; pf.space_after=Pt(4); pf.line_spacing=1.1
S['Body Text'].paragraph_format.first_line_indent=Inches(0.25)
S['First Paragraph'].paragraph_format.first_line_indent=Inches(0)
for n in ['Abstract','Abstract Title']:
    S[n].paragraph_format.left_indent=Inches(0.5); S[n].paragraph_format.right_indent=Inches(0.5)
font(S['Abstract'],10); font(S['Abstract Title'],10,True)
font(S['Title'],17,False); S['Title'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
S['Title'].paragraph_format.space_before=Pt(24); S['Title'].paragraph_format.space_after=Pt(12)
for n in ['Author','Date']:
    font(S[n],12); S[n].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
for n,sz in [('Heading 1',14),('Heading 2',12),('Heading 3',11)]:
    font(S[n],sz,True,False); S[n].paragraph_format.space_before=Pt(14 if sz==14 else 10); S[n].paragraph_format.space_after=Pt(6)
for n in ['Caption','Image Caption','Table Caption']:
    if n in S: font(S[n],10,None,False); S[n].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
sec=d.sections[0]; sec.page_width=Inches(8.27); sec.page_height=Inches(11.69)
for m in ('left_margin','right_margin','top_margin','bottom_margin'): setattr(sec,m,Inches(1))
d.save('ref.docx')
