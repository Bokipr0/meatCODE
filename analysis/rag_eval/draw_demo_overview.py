#!/usr/bin/env python3
# Last updated: 2026-10-18 10:12 UTC · Codex / Design-RAG · minimal icon-led live-demo overview.
from pathlib import Path
from html import escape
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'platform_docs/diagrams'
ET.register_namespace('', 'http://www.w3.org/2000/svg')
ns = {'s': 'http://www.w3.org/2000/svg'}
source = ET.parse(BASE / 'meatcode-engineered-rag-architecture.svg').getroot()
icons = {}
for name, transform in [('pdf','160 332'),('parse','400 332'),('extract','640 332'),
                        ('check','640 638'),('db','990 638'),('search','1280 638'),
                        ('server','1450 304'),('oracle','1704 304'),('model','1600 638')]:
    group = next(g for g in source.findall('s:g', ns) if g.get('transform') == 'translate(' + transform + ')')
    icons[name] = ''.join(ET.tostring(x, encoding='unicode') for x in group)

parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-labelledby="title desc" font-family="Avenir Next, Helvetica, sans-serif">
<!-- Last updated: 2026-10-18 10:12 UTC · Codex / Design-RAG · verified Neon graph/vector demo; Claude credential pending. -->
<title id="title">MeatCODE: knowledge to answer</title><desc id="desc">Minimal process diagram. GROBID and LightRAG extraction is imported through checks into Neon graph tables and pgvector. Oracle calls the server, which embeds a query, retrieves graph and vector evidence and calls Claude. The model response returns through the server. Graph and vector retrieval are verified live; the Claude key needs repair. No relevance-score cutoff.</desc>
<defs><style>
text{fill:#193e3b}.title{font-size:46px;font-weight:700;letter-spacing:-1px}.sub{font-size:19px;fill:#697a70}
.zone{font-size:13px;font-weight:700;letter-spacing:2px;fill:#648277}.label{font-size:22px;font-weight:650;letter-spacing:-.4px}
.detail{font-size:14px;fill:#63796e}.edge{font-size:14px;font-weight:600;fill:#58776a}.status{font-size:11px;font-weight:750;letter-spacing:1px}
.data{fill:none;stroke:#087f75;stroke-width:2.7;stroke-linecap:round;stroke-linejoin:round;marker-end:url(#t)}
.query{fill:none;stroke:#b17b2e;stroke-width:2.7;stroke-linecap:round;stroke-linejoin:round;marker-end:url(#g)}
.future{stroke-dasharray:6 7}
</style><marker id="t" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9" fill="#087f75"/></marker>
<marker id="g" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9" fill="#b17b2e"/></marker>
<filter id="soft-shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="5" stdDeviation="12" flood-color="#173f39" flood-opacity=".07"/></filter>
''']
for name, icon in icons.items():
    parts.append('<g id="' + name + '">' + icon + '</g>')
parts.append('''<g id="vectors"><circle r="64" fill="#d9efec"/><g stroke="#087f75" stroke-width="2.8" fill="none" stroke-linecap="round"><path d="M-29-27V28H29M-27 18L-3-13L23-3M-27 18L13 29M-3-13L26-27"/><circle cx="-27" cy="18" r="5" fill="#fff"/><circle cx="-3" cy="-13" r="5" fill="#fff"/><circle cx="23" cy="-3" r="5" fill="#fff"/><circle cx="26" cy="-27" r="5" fill="#fff"/><circle cx="13" cy="29" r="5" fill="#fff"/></g></g></defs>
<rect width="1920" height="1080" fill="#f8f7f0"/>
<rect x="54" y="205" width="1812" height="323" rx="30" fill="#edf2e7"/>
<rect x="54" y="661" width="1812" height="326" rx="30" fill="#edf4f0"/>
''')


def text(x, y, value, cls, center=False, extra=''):
    parts.append(f'<text x="{x}" y="{y}" class="{cls}" '+('text-anchor="middle" ' if center else '')+extra+'>'+escape(value)+'</text>')


def path(value, cls='data'):
    parts.append(f'<path d="{value}" class="{cls}"/>')


def node(x, y, icon, title, detail):
    parts.append(f'<use href="#{icon}" transform="translate({x} {y})"/>')
    text(x, y+99, title, 'label', True)
    text(x, y+127, detail, 'detail', True)


text(78, 61, 'MEATCODE / LIVE DEMO ARCHITECTURE', 'zone')
text(78, 122, 'Knowledge to answer.', 'title')
text(79, 162, 'Extract once. Store with provenance. Retrieve the evidence. Reason with citations.', 'sub')
parts.append('<circle cx="1464" cy="110" r="5" fill="#087f75"/>')
text(1480, 115, 'NEON DEV · RETRIEVAL VERIFIED', 'status', extra='style="fill:#087f75"')
text(1480, 143, 'No relevance-score cutoff', 'detail')
text(84, 247, '01 / PREPARE KNOWLEDGE', 'zone')
text(1531, 247, 'ASYNCHRONOUS INGESTION', 'zone')

for a, b, verb in [(150,450,'parse'),(450,750,'extract'),(750,1050,'check'),(1050,1350,'import'),(1350,1650,'index')]:
    path(f'M{a+76} 332H{b-80}')
    text((a+b)/2, 310, verb, 'edge', True)

# Branches avoid every node label; evidence is read by the retrieval step.
path('M1350 396V409H1460V562H1000V674')
path('M1650 396V409H1784V615H1100V674')
text(1190, 545, 'graph context', 'edge', True)
text(1495, 599, 'nearest vector matches', 'edge', True)

node(150,332,'pdf','Source papers','3 processed documents')
node(450,332,'parse','GROBID','194 source chunks')
node(750,332,'extract','LightRAG','Entities + relationships')
node(1050,332,'check','Import checks','DOI + evidence mapping')
node(1350,332,'db','Neon graph','3,418 entities · 4,164 edges')
node(1650,332,'vectors','pgvector','7,582 BGE-M3 vectors')

text(84, 583, 'Original embeddings reused · 1,024 dimensions', 'detail')
text(84, 612, 'Extracted demo records retain their provenance and review status.', 'detail')
text(84, 702, '02 / ANSWER A QUESTION', 'zone')
text(1564, 702, 'INTERACTIVE SERVING', 'zone')

path('M226 775H474', 'query');text(350,753,'question','edge',True)
path('M626 775H924', 'query');text(775,753,'embed + search','edge',True)
path('M1076 775H1424', 'query future');text(1250,753,'evidence + citations','edge',True)

node(150,775,'oracle','Oracle','User question')
node(550,775,'server','MeatCODE server','POST /api/ask')
node(1000,775,'search','Graph + vector retrieval','Query embedding via local Ollama')
node(1500,775,'model','Claude','Reason from retrieved evidence')

# Return path is explicitly model → server → browser, never model → browser.
path('M1500 839V852H1730V953H700V812H610', 'query future')
text(1160,936,'model response → server','edge',True)
path('M497 812H410V952H150V844', 'query')
text(312,936,'stream answer','edge',True)
parts.append('<rect x="1400" y="922" width="305" height="25" rx="12" fill="#f4e6cc"/>')
text(1552,939,'CLAUDE KEY NEEDS REPAIR','status',True,extra='style="fill:#946522"')

text(78,1034,'Live: imported graph + semantic retrieval. Pending: Claude authentication. Production unchanged.','detail')
text(1495,1034,'18 OCT 2026 · DEMO STATE','status')
parts.append('</svg>')
(BASE/'meatcode-rag-demo-overview.svg').write_text('\n'.join(parts))
print(BASE/'meatcode-rag-demo-overview.svg')
