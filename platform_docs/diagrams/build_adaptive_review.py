"""Updated 2026-10-29 · Render one-page review briefs, including permission tables."""
from pathlib import Path
import re
import sys
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from pypdf import PdfReader

root = Path(__file__).resolve().parent.parent
svg = root / 'diagrams/meatcode-adaptive-architecture.svg'
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BriefTitle', fontName='Helvetica-Bold', fontSize=19, leading=23, textColor=colors.HexColor('#173B3A'), spaceAfter=9))
styles.add(ParagraphStyle(name='BriefHeading', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=colors.HexColor('#00736E'), spaceBefore=8, spaceAfter=3))
styles.add(ParagraphStyle(name='BriefBody', fontName='Helvetica', fontSize=9.1, leading=12, spaceAfter=4))
story=[]
stem = sys.argv[1] if len(sys.argv) > 1 else 'ADAPTIVE_ORACLE_ONE_PAGE'
styles.add(ParagraphStyle(name='TableBody', fontName='Helvetica', fontSize=8, leading=10))
table_rows=[]
def flush_table():
    if not table_rows: return
    rows=[]
    for i,row in enumerate(table_rows):
        rows.append([Paragraph(('<b>'+v+'</b>') if i==0 else v, styles['TableBody']) for v in row])
    width=A4[0]-80
    table=Table(rows,colWidths=[width/len(rows[0])]*len(rows[0]),hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEDEA')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F4F7F6'),colors.white]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#7DA8A2')),
    ]))
    story.extend([table,Spacer(1,6)])
    table_rows.clear()
for line in (root/(stem+'.md')).read_text().splitlines():
    if line.startswith('|'):
        cells=[v.strip() for v in line.strip('|').split('|')]
        if all(re.fullmatch(r'[: -]+',v) for v in cells): continue
        table_rows.append([v.replace('&','&amp;') for v in cells])
        continue
    flush_table()
    if not line.strip(): continue
    if line.startswith('![') and 'meatcode-dataset-modules.svg' in line:
        from dataset_modules_illustration import module_diagram
        story.extend([module_diagram(),Spacer(1,5)])
        continue
    style='BriefBody'
    if line.startswith('# '): line=line[2:];style='BriefTitle'
    elif line.startswith('## '): line=line[3:];style='BriefHeading'
    elif line.startswith('- '): line='• '+line[2:]
    line=line.replace('&','&amp;').replace('—','-').replace('–','-')
    line=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',line)
    if line.startswith('_') and line.endswith('_'): line='<i>'+line[1:-1]+'</i>'
    story.append(Paragraph(line,styles[style]))
flush_table()
out=root/(stem+'.pdf')
SimpleDocTemplate(str(out),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=35,bottomMargin=35).build(story)
assert len(PdfReader(out).pages)==1, 'Brief exceeds one page'
print('Verified: PDF is one page. SVG preview rendered separately.')
