from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT
from pypdf import PdfReader

OUT='output/pdf/MeatCODE_Expert_Review_Brief.pdf'
W,H=595.276,841.89
c=canvas.Canvas(OUT,pagesize=(W,H))
c.setTitle('MeatCODE | Expert review brief')
c.setAuthor('MeatCODE')
ink=HexColor('#172E38'); muted=HexColor('#536772'); teal=HexColor('#087F8C'); light=HexColor('#EDF5F5'); rule=HexColor('#D9E4E7')
styles={
 'intro':ParagraphStyle('intro',fontName='Helvetica',fontSize=10.3,leading=14,textColor=ink),
 'body':ParagraphStyle('body',fontName='Helvetica',fontSize=9.2,leading=11.3,textColor=ink),
 'small':ParagraphStyle('small',fontName='Helvetica',fontSize=8.1,leading=10.5,textColor=muted),
 'out':ParagraphStyle('out',fontName='Helvetica',fontSize=9.6,leading=13,textColor=ink),
}
def para(text,x,top,width,style):
 p=Paragraph(text,styles[style]); _,h=p.wrap(width,H)
 p.drawOn(c,x,top-h)
 return h

m=37
c.setFillColor(teal);c.rect(0,H-9,W,9,fill=1,stroke=0)
c.setFont('Helvetica-Bold',9);c.drawString(m,H-36,'MEATCODE  /  EXPERT REVIEW BRIEF')
c.setFillColor(muted);c.setFont('Helvetica',8.5);c.drawRightString(W-m,H-36,'26 OCTOBER 2026')
c.setFillColor(ink);c.setFont('Helvetica-Bold',23);c.drawString(m,H-72,'The boundaries of reliable reasoning')
para('Priority: mathematical feasibility and optimized navigation from a question to a supported answer.',m,H-86,W-2*m,'intro')
para('<b>Core ask.</b> Determine the theoretical limits of the proposed knowledge-graph architecture and the best practical design using existing tools. Specify every transition: question → interpretation → evidence retrieval → reasoning → answer or explicit gap. Define what can be guaranteed, under which assumptions and resource budgets.',m,H-118,W-2*m,'intro')

rows=[
('01','Define the optimization problem','Optimization + decision theory',
 'What makes a route "best": relevance, evidence coverage, scientific validity, latency or cost? The shortest graph path need not give the best answer.',
 'Specify admissible answers, measurable objectives and constraints. Define tradeoffs between quality and resources. Distinguish exact solutions, approximations and heuristics; state where optimality can actually be proved.'),
('02','Preserve meaning in the knowledge layer','Knowledge modeling + scientific NLP',
 'Can extraction, merging or segmentation discard evidence needed later? A graph does not automatically preserve all information in its source documents.',
 'Define claims, identities, conditions and provenance; retain source evidence. Compare section-aware text, graph and hybrid representations. Test whether relevant questions remain answerable after transformation; identify information loss and recovery paths.'),
('03','Bound the search space','Graph algorithms + complexity',
 'Unrestricted path enumeration can grow exponentially with depth. Disconnected or missing links can hide evidence; aggressive pruning can remove useful routes.',
 'Analyze runtime and memory under explicit graph/query assumptions. Compare indexed search, bounded traversal and adaptive expansion. Quantify pruning versus recall; benchmark against exhaustive search where tractable. Specify depth, fan-out and stopping limits.'),
('04','Make the answer path inspectable','Query planning + reasoning systems',
 'A neural network does not inherently navigate the complete graph or identify every missing premise. An early retrieval error can derail the final answer.',
 'Design an explicit planner: resolve intent, decompose the question, retrieve, check evidence coverage, expand if needed, then synthesize. Define contracts for every stage. Trace subquestions to evidence; handle ambiguity, conflicts and failed retrieval.'),
('05','State guarantees and failure boundaries','Formal methods + uncertainty',
 'Finite evidence cannot answer every question. A missing link does not prove no relationship exists; inventing a bridge risks hallucination.',
 'State assumptions for soundness, completeness and termination. Separate observed facts, deductions and hypotheses. Require clarification, partial answers or abstention when support is missing. Distinguish unresolved science from pipeline failures.'),
('06','Select tools through controlled tests','ML evaluation + systems engineering',
 'Model capability alone cannot repair lost evidence or poor search. More graph nodes, tokens or GPU capacity do not establish better reasoning.',
 'Compare model roles and text, vector and graph/hybrid retrieval on held-out expert tasks. Measure evidence coverage, supported answers, abstention, latency and cost. Test missing evidence and growth; choose the simplest design meeting agreed bounds.'),
]
start=H-191
rowh=87
left=m+29
for i,(n,title,expert,problem,solution) in enumerate(rows):
 top=start-i*rowh
 c.setStrokeColor(rule);c.line(m,top+7,W-m,top+7)
 c.setFillColor(teal);c.setFont('Helvetica-Bold',11);c.drawString(m,top-8,n)
 c.setFillColor(ink);c.setFont('Helvetica-Bold',11);c.drawString(left,top-8,title)
 c.setFillColor(muted);c.setFont('Helvetica',8);c.drawRightString(W-m,top-8,expert)
 # Pair questions with concrete review outputs in two columns.
 col=190
 rightcol=W-2*m-29-15-col
 h1=para('<b>Risk / open question</b><br/>'+problem,left,top-17,col,'body')
 h2=para('<b>What we need to resolve</b><br/>'+solution,left+col+15,top-17,rightcol,'body')
 if max(h1,h2)>62: raise ValueError((title,h1,h2))

bottom=start-6*rowh+2
c.setFillColor(light);c.roundRect(m,bottom-71,W-2*m,71,6,fill=1,stroke=0)
para('<b>Requested expert outcome</b>  A mathematical problem specification; complexity and information-loss analysis; an end-to-end retrieval/reasoning design with explicit assumptions, failure handling and resource bounds; and a reproducible benchmark. Prioritize graph algorithms, optimization and retrieval expertise, supported by scientific and ML review.',m+11,bottom-10,W-2*m-22,'out')
para('Scope: expert review of the proposed architecture, not a claim of universal optimality or completeness. Working basis: MeatCODE engineered RAG architecture, curation/scaling proposal and evaluation protocol.',m,43,W-2*m,'small')
c.save()
r=PdfReader(OUT)
assert len(r.pages)==1,len(r.pages)
print(OUT)
print('Pages:',len(r.pages))
print('Words:',len(r.pages[0].extract_text().split()))
