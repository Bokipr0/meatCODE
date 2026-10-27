"""Updated 2026-10-26 · Render the editable SVG and one-page review brief."""
from pathlib import Path
import re
import sys
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from pypdf import PdfReader

root = Path(__file__).resolve().parent.parent
svg = root / 'diagrams/meatcode-adaptive-architecture.svg'
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BriefTitle', fontName='Helvetica-Bold', fontSize=19, leading=23, textColor=colors.HexColor('#173B3A'), spaceAfter=9))
styles.add(ParagraphStyle(name='BriefHeading', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=colors.HexColor('#00736E'), spaceBefore=8, spaceAfter=3))
styles.add(ParagraphStyle(name='BriefBody', fontName='Helvetica', fontSize=9.1, leading=12, spaceAfter=4))
story=[]
stem = sys.argv[1] if len(sys.argv) > 1 else 'ADAPTIVE_ORACLE_ONE_PAGE'
for line in (root/(stem+'.md')).read_text().splitlines():
    if not line.strip(): continue
    style='BriefBody'
    if line.startswith('# '): line=line[2:];style='BriefTitle'
    elif line.startswith('## '): line=line[3:];style='BriefHeading'
    elif line.startswith('- '): line='• '+line[2:]
    line=line.replace('&','&amp;').replace('—','-').replace('–','-')
    line=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',line)
    if line.startswith('_') and line.endswith('_'): line='<i>'+line[1:-1]+'</i>'
    story.append(Paragraph(line,styles[style]))
out=root/(stem+'.pdf')
SimpleDocTemplate(str(out),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=35,bottomMargin=35).build(story)
assert len(PdfReader(out).pages)==1, 'Brief exceeds one page'
print('Verified: PDF is one page. SVG preview rendered separately.')
