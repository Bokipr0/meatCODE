#!/usr/bin/env python3
"""
MeatCODE KG — build the self-contained explorer HTML.
Last updated: 2026-08-15 · Advisory

Reads kg/kg_data.json + kg/demo_queries.json and writes kg/kg_explorer.html:
a single file with no dependencies that shows both graphs, lets you walk them, and
demonstrates how the Oracle would retrieve through the graph instead of over flat text.

Run:  python3 kg/make_explorer.py
"""
import json, os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def build_viz_subset(d, max_mol=320, max_pap=260):
    """A full 799x639 force layout is unreadable and slow. Keep the molecules that carry the
    most signal (papers first, then aroma richness) plus everything they touch."""
    mols = d["nodes"]["molecules"]
    mols_sorted = sorted(mols, key=lambda m: (-(m["papers"] or 0), -(m["n_odours"] or 0)))
    keep_mol = {m["id"] for m in mols_sorted[:max_mol]}

    paps = sorted(d["nodes"]["papers"],
                  key=lambda p: -((p.get("relevance") or 0) + (p.get("citations") or 0) / 50))
    linked = {e["s"] if e["s"].startswith("s") else e["t"]
              for e in d["edges"] if e["kind"] == "mentions"}
    keep_pap = {p["id"] for p in paps if p["id"] in linked}
    keep_pap |= {p["id"] for p in paps[:max_pap]}
    keep_pap = set(list(keep_pap)[:max_pap])

    keep_od, keep_chem, keep_top = set(), set(), set()
    edges = []
    for e in d["edges"]:
        s, t, k = e["s"], e["t"], e["kind"]
        if k == "smells_of" and s in keep_mol:
            keep_od.add(t); edges.append(e)
        elif k == "aroma_similar" and s in keep_mol and t in keep_mol:
            edges.append(e)
        elif k in ("in_class", "functional_group", "subgroup", "formed_by") and s in keep_mol:
            keep_chem.add(t); edges.append(e)
        elif k == "mentions" and (s in keep_pap or t in keep_pap):
            m = s if s.startswith("m") else t
            p = s if s.startswith("s") else t
            if m in keep_mol and p in keep_pap:
                edges.append(e)
        elif k == "about_topic" and s in keep_pap:
            keep_top.add(t); edges.append(e)

    nodes = []
    for m in mols:
        if m["id"] in keep_mol:
            nodes.append({k: m[k] for k in
                          ("id", "label", "type", "category", "papers", "n_odours",
                           "cas", "chem_group", "subgroup", "process", "in_mvl",
                           "beef_relevance", "odours")})
    for o in d["nodes"]["odours"]:
        if o["id"] in keep_od:
            nodes.append({k: o[k] for k in ("id", "label", "type", "category", "n_molecules")})
    for c in d["nodes"]["chem"]:
        if c["id"] in keep_chem:
            nodes.append(c)
    for p in d["nodes"]["papers"]:
        if p["id"] in keep_pap:
            nodes.append({k: p.get(k) for k in
                          ("id", "label", "type", "year", "journal", "relevance",
                           "citations", "study_type", "matrix", "method", "main_claim")})
    for t in d["nodes"]["topics"]:
        if t["id"] in keep_top:
            nodes.append(t)
    return {"nodes": nodes, "edges": edges}


def main():
    d = json.load(open(os.path.join(HERE, "kg_data.json"), encoding="utf-8"))
    demos = json.load(open(os.path.join(HERE, "demo_queries.json"), encoding="utf-8"))
    viz = build_viz_subset(d)

    st = d["stats"]
    mols = d["nodes"]["molecules"]
    cls = Counter(m["category"] for m in mols)
    path = Counter(m["process"] for m in mols if m.get("process"))
    linked_mol = sum(1 for m in mols if (m["papers"] or 0) > 0)

    diagnostics = {
        "molecules_total": st["molecules"],
        "molecules_linked_to_papers": linked_mol,
        "molecules_with_cas": sum(1 for m in mols if m.get("cas")),
        "papers_total": st["sources"],
        "papers_linked_to_molecules": st["sources_with_any_molecule"],
        "bridge_curated": st["bridge_curated"],
        "bridge_mined": st["bridge_mined"],
        "classes": cls.most_common(),
        "pathways": path.most_common(),
    }

    html = TEMPLATE.replace("__VIZ__", json.dumps(viz, ensure_ascii=False)) \
                   .replace("__STATS__", json.dumps(st, ensure_ascii=False)) \
                   .replace("__DIAG__", json.dumps(diagnostics, ensure_ascii=False)) \
                   .replace("__DEMOS__", json.dumps(demos, ensure_ascii=False)) \
                   .replace("__GEN__", d["generated_utc"])
    out = os.path.join(HERE, "kg_explorer.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out}  ({os.path.getsize(out)/1e6:.2f} MB)")
    print(f"  viz nodes: {len(viz['nodes'])}  viz edges: {len(viz['edges'])}")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MeatCODE · Knowledge Graph MVP</title>
<style>
 :root{ color-scheme:light; --wine:#7a2d3d; --wine-dk:#5c2130; --ink:#241d1b; --dim:#857a75;
        --line:#ebe2e3; --bg:#faf7f4; --card:#fff; --teal:#1f6f68;
        --mol:#7a2d3d; --od:#c98a2b; --pap:#2f6f8f; --chem:#5b8c5a; --top:#8a6aa8; }
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--ink);
      font:14.5px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,sans-serif}
 .wrap{max-width:1180px;margin:0 auto;padding:20px 18px 60px}
 h1{font-size:20px;margin:0;color:var(--wine)}
 .sub{color:var(--dim);font-size:12.5px;margin-top:3px}
 .tabs{display:flex;gap:6px;margin:18px 0 16px;flex-wrap:wrap;border-bottom:1px solid var(--line)}
 .tab{padding:9px 15px;cursor:pointer;font-weight:640;font-size:13.5px;color:#6d6360;
      border-bottom:2px solid transparent;margin-bottom:-1px}
 .tab.on{color:var(--wine);border-bottom-color:var(--wine)}
 .panel{display:none} .panel.on{display:block}
 .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px}
 .kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
 .kpi .n{font-size:22px;font-weight:700;line-height:1.1;color:var(--wine)}
 .kpi .l{font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin-top:3px}
 .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:12px}
 .card h3{margin:0 0 4px;font-size:14.5px;color:var(--wine-dk)}
 .card p{margin:6px 0;font-size:13.5px}
 .warn{background:#fff6ef;border-color:#f0d9c2}
 .good{background:#f1f8f4;border-color:#cfe6d8}
 .bar{height:9px;background:#eee7e3;border-radius:99px;overflow:hidden;margin:7px 0 3px}
 .bar span{display:block;height:100%;background:var(--wine)}
 .legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--dim);margin:10px 0}
 .legend b{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
 .controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
 select,input[type=search]{border:1px solid var(--line);border-radius:9px;padding:7px 11px;font-size:13px;background:#fff}
 button.b{border:1px solid var(--line);background:#fff;border-radius:9px;padding:7px 12px;font-size:12.5px;cursor:pointer;font-weight:600}
 button.b.on{background:var(--wine);color:#fff;border-color:var(--wine)}
 canvas{width:100%;height:560px;background:#fff;border:1px solid var(--line);border-radius:14px;display:block;cursor:grab}
 .side{position:relative}
 .detail{position:absolute;top:12px;right:12px;width:290px;background:rgba(255,255,255,.97);
         border:1px solid var(--line);border-radius:12px;padding:13px 15px;font-size:12.5px;
         box-shadow:0 4px 16px rgba(0,0,0,.08);max-height:520px;overflow:auto}
 .detail h4{margin:0 0 6px;font-size:13.5px;color:var(--wine)}
 .detail .row{margin:3px 0;color:#5d5350}
 .detail .row b{color:var(--ink)}
 .chip{display:inline-block;background:#f2ece8;border-radius:99px;padding:2px 8px;margin:2px 3px 0 0;font-size:11px}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
 th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--dim)}
 .q{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:14px}
 .q h3{margin:0 0 10px;font-size:15px;color:var(--wine)}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
 @media(max-width:820px){.two{grid-template-columns:1fr}}
 .route{border:1px solid var(--line);border-radius:11px;padding:12px 13px}
 .route.g{background:#f4f8fb;border-color:#cfe0ec} .route.f{background:#faf8f5}
 .route h4{margin:0 0 7px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--dim)}
 .pill{display:inline-block;font-size:11px;padding:1px 7px;border-radius:99px;background:#e8eef3;color:#2f6f8f;margin:1px 2px 0 0}
 .pill.m{background:#f3e6ea;color:var(--wine)}
 .paper{font-size:12.5px;padding:6px 0;border-top:1px dashed var(--line)}
 .paper .t{font-weight:600}
 .muted{color:var(--dim);font-size:12px}
 code{background:#f2ece8;padding:1px 5px;border-radius:5px;font-size:12px}
</style></head><body><div class="wrap">

<h1>MeatCODE · Knowledge Graph MVP</h1>
<div class="sub">Built live from the Neon corpus · <span id="gen"></span></div>

<div class="tabs">
 <div class="tab on" data-p="ov">Overview</div>
 <div class="tab" data-p="mol">Molecule graph</div>
 <div class="tab" data-p="pap">Paper graph</div>
 <div class="tab" data-p="bot">How the Oracle uses it</div>
</div>

<div class="panel on" id="p-ov"></div>

<div class="panel" id="p-mol">
 <div class="controls">
  <input type="search" id="mSearch" placeholder="Find a compound…" style="min-width:220px">
  <select id="mClass"></select>
  <select id="mPath"><option value="">Any pathway</option><option>Maillard</option><option>Lipid oxidation</option><option>Both</option></select>
  <button class="b on" data-l="smells_of">aroma edges</button>
  <button class="b on" data-l="aroma_similar">similarity</button>
  <button class="b" data-l="in_class">class</button>
  <button class="b" data-l="formed_by">pathway</button>
 </div>
 <div class="legend">
  <span><b style="background:var(--mol)"></b>molecule</span><span><b style="background:var(--od)"></b>odour</span>
  <span><b style="background:var(--chem)"></b>chemistry (class · group · pathway)</span>
  <span class="muted">drag to pan · scroll to zoom · click a node</span>
 </div>
 <div class="side"><canvas id="cMol"></canvas><div class="detail" id="dMol">Click a node.</div></div>
</div>

<div class="panel" id="p-pap">
 <div class="controls">
  <input type="search" id="pSearch" placeholder="Find a paper…" style="min-width:260px">
  <button class="b on" data-l2="mentions">molecule links</button>
  <button class="b on" data-l2="about_topic">topics</button>
 </div>
 <div class="legend">
  <span><b style="background:var(--pap)"></b>paper</span><span><b style="background:var(--mol)"></b>molecule</span>
  <span><b style="background:var(--top)"></b>topic</span>
 </div>
 <div class="side"><canvas id="cPap"></canvas><div class="detail" id="dPap">Click a node.</div></div>
</div>

<div class="panel" id="p-bot"></div>

</div>
<script>
const VIZ=__VIZ__, STATS=__STATS__, DIAG=__DIAG__, DEMOS=__DEMOS__;
document.getElementById('gen').textContent=new Date("__GEN__").toLocaleString();
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===t));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));
  $('#p-'+t.dataset.p).classList.add('on');
  if(t.dataset.p==='mol') MOL.start(); if(t.dataset.p==='pap') PAP.start();
});

/* ---------------- OVERVIEW ---------------- */
(function(){
  const pctLinkedMol=Math.round(100*DIAG.molecules_linked_to_papers/DIAG.molecules_total);
  const pctLinkedPap=Math.round(100*DIAG.papers_linked_to_molecules/DIAG.papers_total);
  $('#p-ov').innerHTML=`
  <div class="kpis">
    <div class="kpi"><div class="n">${STATS.molecules}</div><div class="l">molecules</div></div>
    <div class="kpi"><div class="n">${STATS.molecule_odour_edges}</div><div class="l">aroma edges</div></div>
    <div class="kpi"><div class="n">${STATS.sources}</div><div class="l">papers</div></div>
    <div class="kpi"><div class="n">${STATS.total_edges}</div><div class="l">total edges</div></div>
    <div class="kpi"><div class="n">${STATS.bridge_mined}</div><div class="l">bridge edges mined</div></div>
  </div>

  <div class="card good"><h3>What the MVP proves</h3>
   <p>Both graphs already exist inside your Postgres — the join tables <i>are</i> edges. No graph
   database was added: this is projected straight from Neon, so nothing new has to be maintained.</p>
   <p>The <b>molecule graph</b> is genuinely rich: ${STATS.molecule_odour_edges} compound→aroma links
   across ${STATS.odours} descriptors, plus ${STATS.aroma_similarity_edges} "these two smell alike"
   edges and a chemistry scaffold of class → functional group → formation pathway.</p>
   <p>The <b>bridge</b> went from <b>${STATS.bridge_curated} curated links to ${STATS.bridge_mined} mined</b>
   by matching compound names in abstracts — a ${Math.round(STATS.bridge_mined/Math.max(1,STATS.bridge_curated))}×
   increase, connecting the two halves of MeatCODE for the first time.</p></div>

  <div class="card warn"><h3>The honest bottleneck this exposes</h3>
   <p>The chemistry is dense; the literature is dense; <b>the join between them is thin</b>.
   Only <b>${DIAG.molecules_linked_to_papers} of ${DIAG.molecules_total} molecules (${pctLinkedMol}%)</b>
   connect to any paper, and <b>${DIAG.papers_linked_to_molecules} of ${DIAG.papers_total} papers (${pctLinkedPap}%)</b>
   connect to any molecule.</p>
   <div class="bar"><span style="width:${pctLinkedMol}%"></span></div>
   <div class="muted">molecules reachable from the literature</div>
   <div class="bar"><span style="width:${pctLinkedPap}%"></span></div>
   <div class="muted">papers reachable from the chemistry</div>
   <p style="margin-top:10px">You can see the consequence in the Oracle tab: for the roasted/nutty
   question the graph identifies exactly the right pyrazines — and then finds <b>zero papers</b>,
   because those specific compounds have no literature edges yet. <b>Densifying this bridge is the
   single highest-value next step</b>, and it is what a claim-extraction pass would produce.</p></div>

  <div class="card"><h3>Also surfaced (data quality)</h3>
   <p>Only <b>${DIAG.molecules_with_cas} of ${DIAG.molecules_total}</b> molecules carry a CAS number —
   <code>cas_number</code> and <code>pubchem_cid</code> are empty in the table, so compounds can only be
   matched by name. Names collide and drift; without canonical IDs some edges will always be wrong.</p>
   <p>The builder also refused <b>${STATS.names_skipped_as_unminable}</b> rows in <code>molecules</code>
   that are not compounds (e.g. <code>Decline</code>) — they would otherwise have generated hundreds of
   false links. Worth cleaning at source.</p></div>

  <div class="card"><h3>Chemical classes in the graph</h3>
   <table><tr><th>class</th><th>molecules</th></tr>
   ${DIAG.classes.map(([k,v])=>`<tr><td>${esc(k)}</td><td>${v}</td></tr>`).join('')}</table>
   <p class="muted" style="margin-top:8px">Formation pathway is known for
   ${DIAG.pathways.reduce((a,b)=>a+b[1],0)} compounds (from the Meaty Volatile Library):
   ${DIAG.pathways.map(([k,v])=>esc(k)+' '+v).join(' · ')}.</p></div>`;
})();

/* ---------------- FORCE GRAPH ---------------- */
function Graph(canvasId, detailId, filterFn, colorFn, labelFn, detailFn){
  const cv=document.getElementById(canvasId), ctx=cv.getContext('2d');
  let N=[],E=[],started=false,tx=0,ty=0,scale=1,sel=null,drag=null,raf=null,ticks=0;
  function resize(){ const r=cv.getBoundingClientRect(), d=window.devicePixelRatio||1;
    cv.width=r.width*d; cv.height=r.height*d; ctx.setTransform(d,0,0,d,0,0); }
  function build(){
    const keep=filterFn(); const ids=new Set(keep.map(n=>n.id));
    N=keep.map(n=>({...n,x:(Math.random()-.5)*700,y:(Math.random()-.5)*500,vx:0,vy:0}));
    const byId={}; N.forEach(n=>byId[n.id]=n);
    E=VIZ.edges.filter(e=>ids.has(e.s)&&ids.has(e.t)&&LAYERS.has(e.kind))
               .map(e=>({...e,a:byId[e.s],b:byId[e.t]}));
    const deg={}; E.forEach(e=>{deg[e.s]=(deg[e.s]||0)+1;deg[e.t]=(deg[e.t]||0)+1});
    N.forEach(n=>n.deg=deg[n.id]||0);
    ticks=0;
  }
  function step(){
    const k=.035, rep=520;
    for(let i=0;i<N.length;i++){ const a=N[i];
      for(let j=i+1;j<N.length;j++){ const b=N[j];
        let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy||1;
        if(d2<40000){ const f=rep/d2; a.vx+=dx*f; a.vy+=dy*f; b.vx-=dx*f; b.vy-=dy*f; } } }
    E.forEach(e=>{ const dx=e.b.x-e.a.x, dy=e.b.y-e.a.y, d=Math.sqrt(dx*dx+dy*dy)||1;
      const f=(d-70)*k*.06; e.a.vx+=dx/d*f; e.a.vy+=dy/d*f; e.b.vx-=dx/d*f; e.b.vy-=dy/d*f; });
    N.forEach(n=>{ n.vx-=n.x*.0022; n.vy-=n.y*.0022; n.x+=n.vx*=.86; n.y+=n.vy*=.86; });
  }
  function draw(){
    const r=cv.getBoundingClientRect();
    ctx.clearRect(0,0,r.width,r.height);
    ctx.save(); ctx.translate(r.width/2+tx, r.height/2+ty); ctx.scale(scale,scale);
    ctx.lineWidth=.6;
    E.forEach(e=>{ const hl=sel&&(e.s===sel.id||e.t===sel.id);
      ctx.strokeStyle=hl?'rgba(122,45,61,.55)':'rgba(140,130,128,.16)';
      ctx.beginPath(); ctx.moveTo(e.a.x,e.a.y); ctx.lineTo(e.b.x,e.b.y); ctx.stroke(); });
    N.forEach(n=>{ const rr=Math.min(11,3.2+Math.sqrt(n.deg||1)*1.25);
      ctx.beginPath(); ctx.arc(n.x,n.y,rr,0,7); ctx.fillStyle=colorFn(n);
      ctx.globalAlpha=sel&&sel.id!==n.id?.55:1; ctx.fill(); ctx.globalAlpha=1;
      if(sel&&sel.id===n.id){ ctx.strokeStyle='#241d1b'; ctx.lineWidth=2; ctx.stroke(); ctx.lineWidth=.6; }
      if(scale>1.05||n.deg>7||sel&&sel.id===n.id){ ctx.fillStyle='#3a2f2c';
        ctx.font='10px -apple-system,sans-serif';
        ctx.fillText(labelFn(n).slice(0,26), n.x+rr+3, n.y+3); } });
    ctx.restore();
  }
  function loop(){ if(ticks<420){ step(); ticks++; } draw(); raf=requestAnimationFrame(loop); }
  function pick(mx,my){ const r=cv.getBoundingClientRect();
    const x=(mx-r.left-r.width/2-tx)/scale, y=(my-r.top-r.height/2-ty)/scale;
    let best=null,bd=1e9; N.forEach(n=>{const d=(n.x-x)**2+(n.y-y)**2; if(d<bd){bd=d;best=n}});
    return bd<400?best:null; }
  cv.addEventListener('mousedown',e=>{drag={x:e.clientX,y:e.clientY,tx,ty,moved:false}});
  window.addEventListener('mousemove',e=>{ if(!drag)return;
    if(Math.abs(e.clientX-drag.x)+Math.abs(e.clientY-drag.y)>3)drag.moved=true;
    tx=drag.tx+(e.clientX-drag.x); ty=drag.ty+(e.clientY-drag.y); });
  window.addEventListener('mouseup',e=>{ if(drag&&!drag.moved){ const n=pick(e.clientX,e.clientY);
      if(n){sel=n; document.getElementById(detailId).innerHTML=detailFn(n);} } drag=null; });
  cv.addEventListener('wheel',e=>{e.preventDefault(); scale=Math.max(.25,Math.min(4,scale*(e.deltaY<0?1.12:.89)));},{passive:false});
  const LAYERS=new Set();
  return { start(){ if(!started){started=true;resize();window.addEventListener('resize',()=>{resize()});}
             build(); if(!raf) loop(); },
           refresh(){ build(); ticks=0; },
           layers:LAYERS };
}

/* ---------------- MOLECULE GRAPH ---------------- */
const COL={molecule:'#7a2d3d',odour:'#c98a2b',chem:'#5b8c5a',paper:'#2f6f8f',topic:'#8a6aa8'};
const MOL=(function(){
  let q='',cls='',pth='';
  const g=Graph('cMol','dMol',
    ()=>{ const keep=VIZ.nodes.filter(n=>{
        if(n.type==='molecule'){
          if(cls&&n.category!==cls) return false;
          if(pth&&n.process!==pth) return false;
          if(q&&!n.label.toLowerCase().includes(q)) return false;
          return true; }
        return n.type==='odour'||n.type==='chem'; });
      const molIds=new Set(keep.filter(n=>n.type==='molecule').map(n=>n.id));
      const touched=new Set();
      VIZ.edges.forEach(e=>{ if(molIds.has(e.s)) touched.add(e.t); if(molIds.has(e.t)) touched.add(e.s); });
      return keep.filter(n=>n.type==='molecule'||touched.has(n.id)); },
    n=>COL[n.type]||'#999', n=>n.label,
    n=>{ if(n.type==='molecule') return `<h4>${esc(n.label)}</h4>
        <div class="row"><b>class</b> ${esc(n.category)}</div>
        ${n.chem_group?`<div class="row"><b>group</b> ${esc(n.chem_group)}</div>`:''}
        ${n.process?`<div class="row"><b>formed by</b> ${esc(n.process)}</div>`:''}
        ${n.cas?`<div class="row"><b>CAS</b> ${esc(n.cas)}</div>`:'<div class="row muted">no CAS in the table</div>'}
        ${n.beef_relevance?`<div class="row"><b>beef relevance</b> ${esc(n.beef_relevance)}</div>`:''}
        <div class="row"><b>papers linked</b> ${n.papers||0}</div>
        <div class="row" style="margin-top:6px"><b>aroma</b><br>${(n.odours||[]).map(o=>`<span class="chip">${esc(o)}</span>`).join('')||'<span class="muted">none</span>'}</div>`;
      if(n.type==='odour') return `<h4>${esc(n.label)}</h4><div class="row"><b>family</b> ${esc(n.category)}</div>
        <div class="row"><b>compounds with this note</b> ${n.n_molecules}</div>`;
      return `<h4>${esc(n.label)}</h4><div class="row"><b>${esc(n.kind)}</b></div>`; });
  ['smells_of','aroma_similar'].forEach(l=>g.layers.add(l));
  document.querySelectorAll('[data-l]').forEach(b=>b.onclick=()=>{
    const l=b.dataset.l; b.classList.toggle('on');
    if(g.layers.has(l))g.layers.delete(l);else g.layers.add(l); g.refresh(); });
  const sel=$('#mClass'); sel.innerHTML='<option value="">Any class</option>'+
    DIAG.classes.map(([k,v])=>`<option>${esc(k)}</option>`).join('');
  sel.onchange=e=>{cls=e.target.value;g.refresh()};
  $('#mPath').onchange=e=>{pth=e.target.value;g.refresh()};
  let t; $('#mSearch').oninput=e=>{clearTimeout(t);t=setTimeout(()=>{q=e.target.value.toLowerCase().trim();g.refresh()},250)};
  return g;
})();

/* ---------------- PAPER GRAPH ---------------- */
const PAP=(function(){
  let q='';
  const g=Graph('cPap','dPap',
    ()=>{ const keep=VIZ.nodes.filter(n=>{
        if(n.type==='paper'){ if(q&&!(n.label||'').toLowerCase().includes(q)) return false; return true; }
        return n.type==='molecule'||n.type==='topic'; });
      const pIds=new Set(keep.filter(n=>n.type==='paper').map(n=>n.id));
      const touched=new Set();
      VIZ.edges.forEach(e=>{ if(pIds.has(e.s))touched.add(e.t); if(pIds.has(e.t))touched.add(e.s); });
      return keep.filter(n=>n.type==='paper'||touched.has(n.id)); },
    n=>COL[n.type]||'#999', n=>n.type==='paper'?(n.label||'').slice(0,30):n.label,
    n=>{ if(n.type==='paper') return `<h4>${esc((n.label||'').slice(0,90))}</h4>
        <div class="row"><b>${esc(n.year||'')}</b> ${esc(n.journal||'')}</div>
        <div class="row"><b>relevance</b> ${n.relevance??'—'} · <b>citations</b> ${n.citations??'—'}</div>
        ${n.study_type?`<div class="row"><b>study</b> ${esc(n.study_type)}</div>`:''}
        ${(n.matrix||[]).length?`<div class="row"><b>matrix</b> ${(n.matrix||[]).map(esc).join(', ')}</div>`:''}
        ${(n.method||[]).length?`<div class="row"><b>method</b> ${(n.method||[]).map(esc).join(', ')}</div>`:''}
        <div class="row" style="margin-top:6px">${esc((n.main_claim||'').slice(0,260))}</div>`;
      if(n.type==='molecule') return `<h4>${esc(n.label)}</h4><div class="row"><b>class</b> ${esc(n.category)}</div>
        <div class="row"><b>papers</b> ${n.papers||0}</div>`;
      return `<h4>${esc(n.label)}</h4><div class="row">topic</div>`; });
  ['mentions','about_topic'].forEach(l=>g.layers.add(l));
  document.querySelectorAll('[data-l2]').forEach(b=>b.onclick=()=>{
    const l=b.dataset.l2; b.classList.toggle('on');
    if(g.layers.has(l))g.layers.delete(l);else g.layers.add(l); g.refresh(); });
  let t; $('#pSearch').oninput=e=>{clearTimeout(t);t=setTimeout(()=>{q=e.target.value.toLowerCase().trim();g.refresh()},250)};
  return g;
})();

/* ---------------- ORACLE / CHATBOT TAB ---------------- */
(function(){
  const intro=`<div class="card"><h3>Where the graph plugs into the Oracle</h3>
   <p>Today: the question is turned into keywords, ranked over <code>sources.search_vec</code>, and the
   top 6 abstracts are pasted into the prompt. The model has to re-derive the chemistry from prose
   every single time.</p>
   <p>With the graph, retrieval starts from <b>entities</b> instead of words:</p>
   <p style="font-family:ui-monospace,monospace;font-size:12.5px;background:#f7f2ee;padding:10px 12px;border-radius:9px">
   question → aroma descriptors → compounds producing them → aroma-similar + same class/pathway →
   papers linked to those compounds → rank by how much of the chemistry each paper covers</p>
   <p>The model then receives a <b>structured skeleton</b> — "these compounds, these families, this
   formation pathway, evidenced by these papers" — instead of six blobs of text. That is what lets
   the Oracle say <i>"five papers support this and they cluster on Maillard pyrazines"</i>, which is
   exactly the consensus/contradiction behaviour on your whiteboard.</p></div>`;

  const qs=DEMOS.map(d=>{
    const g=d.graph,f=d.flat;
    const gids=new Set(g.papers.map(p=>p.id)), fids=new Set(f.papers.map(p=>p.id));
    const only=[...gids].filter(x=>!fids.has(x)).length;
    const prof=g.chemistry_profile;
    return `<div class="q"><h3>${esc(d.question)}</h3>
      <div class="two">
      <div class="route g"><h4>Graph route</h4>
        <div class="row"><b>aroma nodes matched:</b> ${g.odours_matched.map(o=>`<span class="pill">${esc(o)}</span>`).join('')||'<span class="muted">none</span>'}</div>
        <div style="margin-top:6px"><b style="font-size:12px">compounds found:</b><br>
          ${g.seed_molecules.slice(0,10).map(m=>`<span class="pill m">${esc(m)}</span>`).join('')}</div>
        <div style="margin-top:6px"><b style="font-size:12px">expanded by chemistry:</b><br>
          ${g.expanded_molecules.slice(0,6).map(m=>`<span class="pill m">${esc(m)}</span>`).join('')||'<span class="muted">—</span>'}</div>
        <div style="margin-top:8px" class="muted">classes: ${prof.classes.map(c=>esc(c[0])+' ×'+c[1]).join(' · ')}
          ${prof.pathways.length?'<br>pathway: '+prof.pathways.map(c=>esc(c[0])+' ×'+c[1]).join(' · '):''}</div>
        <div style="margin-top:8px"><b style="font-size:12px">papers (${g.n_candidate_papers} candidates):</b></div>
        ${g.papers.length?g.papers.map(p=>`<div class="paper"><div class="t">[${p.id}] ${esc(p.title.slice(0,72))}</div>
           <div class="muted">covers ${p.molecules_covered} compound(s): ${p.which.map(esc).join(', ')}</div></div>`).join('')
          :'<div class="paper muted">No papers — the compounds are right, but none of them have literature edges yet. This is the bridge gap, made visible.</div>'}
      </div>
      <div class="route f"><h4>Flat keyword route (today)</h4>
        <div class="muted">${f.n_candidate_papers} candidates → top ${f.papers.length}</div>
        ${f.papers.map(p=>`<div class="paper"><div class="t">[${p.id}] ${esc(p.title.slice(0,72))}</div>
          <div class="muted">${p.keyword_hits} keyword hit(s)</div></div>`).join('')}
        <div class="muted" style="margin-top:8px">No compound-level structure: the model gets text and
        must infer the chemistry itself.</div>
      </div></div>
      <div class="muted" style="margin-top:9px">Overlap between the two routes:
        <b>${[...gids].filter(x=>fids.has(x)).length}</b> of ${gids.size} —
        the graph surfaced <b>${only}</b> paper(s) keywords missed.</div>
    </div>`; }).join('');

  const close=`<div class="card warn"><h3>What this MVP says to do next</h3>
   <p><b>1 · Densify the bridge.</b> It is the binding constraint — the chemistry and the literature are
   both strong, the join is not. Claim extraction produces exactly these edges, with conditions and
   evidence attached, which is the same work item as the claim layer.</p>
   <p><b>2 · Give molecules canonical IDs</b> (PubChem CID / CAS) before scaling extraction, or duplicate
   nodes will quietly corrupt every count.</p>
   <p><b>3 · Keep it in Postgres.</b> Nothing here needed a graph database; at this size recursive SQL
   is enough. Revisit only if traversal depth becomes the bottleneck.</p>
   <p><b>4 · Ship the molecule graph first.</b> It is already demoable and it is the visual that makes
   MeatCODE look like infrastructure rather than a search box.</p></div>`;
  $('#p-bot').innerHTML=intro+qs+close;
})();
</script></body></html>"""


if __name__ == "__main__":
    main()
