#!/usr/bin/env python3
# Last updated: 2026-10-18 10:00 UTC · Codex / Design-RAG · precise demo process diagram.
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'platform_docs/diagrams/meatcode-rag-demo-flow.svg'
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1420" viewBox="0 0 1920 1420" role="img" aria-labelledby="title desc">
<!-- Last updated: 2026-10-18 10:00 UTC · Codex / Design-RAG · existing extraction versus prepared Neon demo. -->
<title id="title">MeatCODE — from extracted knowledge to a cited answer</title>
<desc id="desc">Two distinct flows: prepare knowledge asynchronously; answer user questions interactively. The graph and its original vectors are imported into Neon dev and semantic retrieval is verified. The relevance cutoff is removed in local code. Claude is retained with credential repair pending. Benchmark detail is separate from the overview.</desc>
<defs><style>
text{font-family:'Avenir Next','Helvetica Neue',sans-serif;fill:#193e3b}
.eyebrow{font-size:13px;font-weight:700;letter-spacing:2.3px;fill:#58716b}
.title{font-size:49px;font-weight:650;letter-spacing:-1.5px}
.sub{font-size:20px;fill:#637671}
.lane{font-size:23px;font-weight:650;letter-spacing:-.4px}
.head{font-size:24px;font-weight:650;letter-spacing:-.6px}
.body{font-size:18px;fill:#526b64}
.small{font-size:14px;fill:#637671}
.status{font-size:11px;font-weight:750;letter-spacing:1.25px}
.label{font-size:14px;font-weight:600;fill:#59746c}
.card{fill:#fff;stroke:#d4e0d9;stroke-width:1.3}
.build{fill:none;stroke:#087f75;stroke-width:2.3;stroke-linejoin:round;stroke-linecap:round;marker-end:url(#teal)}
.query{fill:none;stroke:#b17b2e;stroke-width:2.7;stroke-linejoin:round;stroke-linecap:round;marker-end:url(#gold)}
.pending{stroke-dasharray:6 7}
</style>
<marker id="teal" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9" fill="#087f75"/></marker>
<marker id="gold" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9" fill="#b17b2e"/></marker>
<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r=".7" fill="#c7d7cd"/></pattern>
</defs>
<rect width="1920" height="1420" fill="#f7f7f0"/>
<rect x="1250" y="0" width="670" height="180" fill="url(#dots)" opacity=".6"/>
''']


def text(x, y, value, cls='body', **attrs):
    extra = ' '.join(f'{k.replace("_", "-")}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
    parts.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{escape(value)}</text>')


def rect(x, y, w, h, fill, radius=16, extra=''):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" {extra}/>')


def line(path, cls='build'):
    parts.append(f'<path d="{path}" class="{cls}"/>')


def pill(x, y, value, state='existing'):
    color, ink = {'existing': ('#e4f1e9', '#26684f'), 'prepared': ('#f4e9d4', '#886020'),
                  'target': ('#eef0ed', '#6c7c73')}[state]
    width = 20 + len(value) * 7
    rect(x, y, width, 24, color, 12)
    text(x + 10, y + 16, value, 'status', style=f'fill:{ink}')


def card(x, y, w, title, subtitle, lines, status, state='existing', number=None):
    rect(x, y, w, 206, '#fff', 18, 'class="card"')
    pill(x + 22, y + 22, status, state)
    if number:
        text(x + w - 26, y + 40, number, 'eyebrow', text_anchor='end')
    text(x + 22, y + 88, title, 'head')
    text(x + 22, y + 118, subtitle, 'body')
    for i, item in enumerate(lines):
        text(x + 22, y + 156 + i * 24, item, 'small')


text(80, 59, 'MEATCODE / SYSTEM DESIGN', 'eyebrow')
text(80, 126, 'From extracted knowledge to a cited answer.', 'title')
text(82, 164, 'One knowledge source. Two separate flows. Every answer traces back to a paper.', 'sub')
text(1840, 59, '18 OCT 2026', 'eyebrow', text_anchor='end')

rect(58, 220, 1804, 426, '#edf2e9', 24)
text(85, 265, '01', 'eyebrow')
text(135, 269, 'Prepare the knowledge', 'lane')
text(1832, 265, 'ASYNCHRONOUS · NOT PART OF A USER REQUEST', 'eyebrow', text_anchor='end')

card(85, 310, 360, 'Parse & extract', 'GROBID → LightRAG',
     ['3 papers · 194 source chunks', '3,418 entities · 4,164 relationships'], 'EXTRACTION EXISTS', number='A')
card(510, 310, 360, 'Check & map', 'Evidence → canonical source IDs',
     ['DOI mapping + vector/provenance checks', 'Scientific review remains a distinct step'], 'IMPORT CHECKS READY', 'prepared', 'B')
card(935, 310, 360, 'Store the graph', 'Neon Postgres',
     ['Entities + relations + evidence links', 'Demo records retain “extracted” status'], 'IMPORTED + VERIFIED', 'existing', 'C')
card(1360, 310, 470, 'Index the knowledge', 'pgvector in the same Neon database',
     ['7,582 existing entity/relation vectors', 'BGE-M3 · 1,024 dimensions · cosine search'], 'IMPORTED + VERIFIED', 'existing', 'D')

for a, b, label in [(445, 510, 'verify'), (870, 935, 'import'), (1295, 1360, 'index')]:
    line(f'M{a+5} 411H{b-7}')
    text((a + b) / 2, 389, label, 'label', text_anchor='middle')

rect(85, 548, 1745, 68, '#e3eae0', 12)
text(108, 575, 'SOURCE ARTIFACTS IN THIS DEMO', 'eyebrow')
text(108, 599, 'PDFs, TEI and exact source text stay local.', 'small')
text(670, 575, 'EXISTING EMBEDDINGS', 'eyebrow')
text(670, 599, 'Reuse the original vectors; embed again only when text/model changes.', 'small')
text(1422, 575, 'TARGET INGESTION', 'eyebrow')
text(1422, 599, 'Qwen extraction → independent validation', 'small')

# Evidence flows from both Neon graph and pgvector into the bounded retrieval stage.
text(82, 703, 'No relevance-score cutoff', 'lane')
text(82, 733, 'Removed in local Oracle code at Lior’s request.', 'body')

rect(58, 790, 1804, 366, '#f1eee6', 24)
# Draw after lane backgrounds, routed through the whitespace between note columns.
line('M1115 516V533H1325V686H1020V865', 'build')
line('M1595 516V532H1845V715H1165V865', 'build')
rect(996, 737, 216, 32, '#f7f7f0', 7)
text(1104, 759, 'graph + vector evidence', 'label', text_anchor='middle')
text(85, 828, '02', 'eyebrow')
text(135, 832, 'Answer a question', 'lane')
text(1832, 828, 'INTERACTIVE · ONLY RETRIEVAL + REASONING', 'eyebrow', text_anchor='end')

card(85, 872, 310, 'Ask in Oracle', 'User question + context',
     ['The existing platform interface', 'Citations link to source records'], 'USER EXPERIENCE', 'target', '1')
card(465, 872, 310, 'Handle the request', 'MeatCODE server',
     ['POST /api/ask', 'Authentication + streamed response'], 'EXISTING API', 'existing', '2')
card(845, 872, 410, 'Retrieve evidence', 'Query embedding + graph context',
     ['BGE-M3 query via local Ollama → Neon', 'Bounded evidence pack with source IDs'], 'SEMANTIC QUERY VERIFIED', 'existing', '3')
card(1325, 872, 505, 'Reason & cite', 'Hosted answer model',
     ['Claude kept configured at Lior’s request', 'User will repair the rejected API credential'], 'CLAUDE KEY NEEDS REPAIR', 'prepared', '4')
for a, b, label in [(395, 465, 'question'), (775, 845, 'search'), (1255, 1325, 'context')]:
    line(f'M{a+6} 972H{b-7}', 'query')
    text((a + b) / 2, 949, label, 'label', text_anchor='middle')

line('M1577 1078V1116H620V1084', 'query')
line('M555 1078V1135H240V1084', 'query')
rect(867, 1101, 469, 30, '#f1eee6', 5)
text(1101, 1121, 'MODEL RESPONSE → SERVER', 'status', text_anchor='middle', style='fill:#986d30')
rect(278, 1120, 237, 30, '#f1eee6', 5)
text(396, 1140, 'SSE ANSWER + CITATIONS', 'status', text_anchor='middle', style='fill:#986d30')

rect(58, 1200, 1804, 138, '#173f39', 22)
text(85, 1239, '03 / BENCHMARK THE WHOLE CONFIGURATION', 'eyebrow', style='fill:#a9c6bb')
text(85, 1280, 'Same question. Same model. Same evidence budget.', 'lane', style='fill:#fff')
text(85, 1310, 'Direct model  →  vector-only RAG  →  graph + vector RAG     |     Then compare GPT and Claude with fixed retrieval.', 'body', style='fill:#c7d9d0')
text(1450, 1267, 'QUALITY · CITATIONS · LATENCY', 'status', style='fill:#c7d9d0')
text(1450, 1295, 'COST · COVERAGE · GRAPH VALUE', 'status', style='fill:#c7d9d0')

text(82, 1377, 'LIVE DEV: graph + pgvector imported; semantic retrieval verified. Answer generation awaits Claude credential repair.', 'small')
text(1840, 1377, 'Teal: knowledge   /   Gold: query and answer', 'small', text_anchor='end')
parts.append('</svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text('\n'.join(parts))
print(OUT)

# A portable diagram viewer: no third-party code, analytics or network calls.
viewer = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<!-- Last updated: 2026-10-18 10:00 UTC · Codex / Design-RAG · standalone architecture viewer. -->
<title>MeatCODE — knowledge to answer</title>
<style>
:root{color-scheme:light;--ink:#193e3b;--teal:#087f75;--paper:#f7f7f0;--line:#d4e0d9}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:'Avenir Next','Helvetica Neue',sans-serif}
header{padding:18px 30px;display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:2}
.brand{font-size:15px;font-weight:750;letter-spacing:.12em}.brand small{display:block;font-weight:450;letter-spacing:0;font-size:12px;margin-top:4px;color:#637671}
nav{display:flex;gap:5px;background:#eef2ec;padding:4px;border-radius:10px}button,a.download{border:0;border-radius:7px;padding:10px 16px;background:transparent;color:var(--ink);font:600 13px inherit;text-decoration:none;cursor:pointer}
button[aria-pressed=true]{background:var(--ink);color:#fff}button:hover,a:hover{outline:1px solid #98b0a2}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #b17b2e;outline-offset:3px}
.actions{display:flex;gap:8px;align-items:center}.download{border:1px solid var(--line)!important}main{max-width:2000px;margin:auto}#stage{padding:10px 12px}svg{width:100%;height:auto;display:block;transition:opacity .15s}
.notes{margin:0 30px 30px;padding:20px 25px;background:#edf2e9;border:1px solid var(--line);border-radius:14px;font-size:14px;line-height:1.65}.notes summary{font-weight:650;cursor:pointer}.notes p{max-width:1050px;margin-bottom:0}.badge{display:inline-block;width:8px;height:8px;border-radius:50%;background:#b17b2e;margin-right:7px}
@media(max-width:850px){header{flex-wrap:wrap;padding:14px}nav{order:3;width:100%;justify-content:center}.actions button{display:none}.brand{font-size:13px}#stage{padding:0}.notes{margin:10px;padding:16px}}
@media print{header,.notes{display:none}#stage{padding:0}svg{max-height:96vh}body{background:white}}
</style></head><body>
<header><div class="brand">MEATCODE<small>Knowledge architecture · 18 October 2026</small></div>
<nav aria-label="Diagram view"><button data-view="overview" aria-pressed="true">Overview</button><button data-view="ingestion" aria-pressed="false">Prepare knowledge</button><button data-view="query" aria-pressed="false">Answer a question</button><button data-view="details" aria-pressed="false">Detailed flow</button><button data-view="benchmark" aria-pressed="false">Benchmark</button></nav>
<div class="actions"><a class="download" href="meatcode-rag-demo-overview.svg" download>Download SVG</a><button id="print">Print</button></div></header>
<main><div id="stage">DIAGRAM_HERE</div>
<details class="notes"><summary><span class="badge"></span>Read the implementation status</summary>
<p>Neon dev contains <strong>3,418 entities, 4,164 relationships, 7,582 entity/relation embeddings and 8,932 evidence links</strong>, from three processed papers. The import was applied and verified, and rerunning it created no duplicates. A real semantic query returned 15 evidence items linked to source 275. The Oracle relevance cutoff has been removed. <strong>The Claude answer credential is rejected (401):</strong> Lior chose to keep Claude configured and will repair its credentials. Production is unchanged.</p>
<p>The current demo imports extracted candidate descriptions and original vectors without marking them scientifically reviewed. The target model split is Qwen for extraction, an independent validator for curation, and GPT for reasoning. The existing Oracle uses Claude. The diagram keeps the intended architecture separate from verified deployment status.</p>
</details><template id="detailedDiagram">DETAIL_DIAGRAM_HERE</template></main>
<script>
const stage=document.querySelector('#stage');
const overview=stage.querySelector('svg').cloneNode(true);
const views={overview:'0 0 1920 1080',ingestion:'35 195 1850 455',query:'35 650 1850 350',details:'0 0 1920 1420',benchmark:'35 1180 1850 180'};
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
 document.querySelectorAll('[data-view]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
 stage.replaceChildren((button.dataset.view==='details'||button.dataset.view==='benchmark')?document.querySelector('#detailedDiagram').content.cloneNode(true):overview.cloneNode(true));
 const diagram=stage.querySelector('svg');
 diagram.setAttribute('viewBox',views[button.dataset.view]);
 const box=views[button.dataset.view].split(' ').map(Number);diagram.style.aspectRatio=box[2]+'/'+box[3];
}));
document.querySelector('#print').addEventListener('click',()=>window.print());
</script></body></html>'''
overview_path=OUT.with_name('meatcode-rag-demo-overview.svg')
overview_svg=overview_path.read_text() if overview_path.exists() else '\n'.join(parts)
OUT.with_suffix('.html').write_text(viewer.replace('DETAIL_DIAGRAM_HERE', '\n'.join(parts)).replace('DIAGRAM_HERE', overview_svg))
print(OUT.with_suffix('.html'))
