/* Last updated: 2026-11-21 22:42 UTC · Claude (Opus 5.5) · status line names the graph source (hosted LightRAG sandbox vs local) and flags a truncated read · prev 2026-11-17 · Codex · map snapshots, graph feedback and contextual forks. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const stages = ['Precursors', 'Reactions', 'Volatiles', 'Descriptors', 'Methods'];
  const storeKey = 'mc_graph_oracle_v1';
  let session = sessionStorage.getItem('mc_graph_session');
  if (!session) { session = crypto.randomUUID(); sessionStorage.setItem('mc_graph_session', session); }
  let chats = [], activeId, busy = false, forkMap = null, feedbackRequest = null;
  // Session-scoped storage keeps maps tied to their server session capability.
  try { chats = JSON.parse(sessionStorage.getItem(storeKey) || '[]'); } catch (_) {}
  function button(text, fn, className) {
    const el = document.createElement('button'); el.type = 'button'; el.textContent = text;
    if (className) el.className = className;
    el.addEventListener('click', fn); return el;
  }
  function text(tag, value, className) {
    const el = document.createElement(tag); el.textContent = value;
    if (className) el.className = className; return el;
  }
  function current() { return chats.find(c => c.id === activeId); }
  function currentMap() { return current()?.maps.at(-1) || current()?.context || null; }
  function save() { try { sessionStorage.setItem(storeKey, JSON.stringify(chats)); } catch (_) { $('requestStatus').textContent = 'Browser storage is full. Keep this page open to retain this conversation.'; } }
  function newChat(context) {
    if (busy) return;
    const chat = { id: crypto.randomUUID(), title: context ? context.title : 'New exploration', messages: [], maps: [], context: context || null };
    chats.push(chat); activeId = chat.id; save(); render();
  }
  function sourceDetails(node) {
    const el = document.createElement('details'); el.className = 'source-record';
    el.append(text('summary', node.name));
    el.append(text('code', 'Entity ID: ' + node.id), text('p', node.description));
    el.append(text('p', 'Evidence chunks: ' + (node.source_ids.join(', ') || 'No chunk reference supplied')));
    el.append(text('p', 'Papers: ' + ((node.papers || []).join(', ') || 'See the connected graph for document provenance')));
    return el;
  }
  function card(title) { const el = document.createElement('article'); el.className = 'message'; el.append(text('h3', title)); return el; }
  function displayExploration(entry, container) {
    const map = entry.map, ids = entry.entity ? [entry.entity] : map.stages[entry.stage];
    const selected = new Set(ids);
    const box = card(entry.entity ? map.nodes.find(n => n.id === entry.entity)?.name || 'Entity' : entry.stage + ' · connections');
    box.append(text('p', map.title, 'hint'));
    const diagram = document.createElement('div'); diagram.className = 'diagram';
    map.nodes.filter(n => selected.has(n.id)).forEach(n => {
      diagram.append(button(n.name, () => explore(map, entry.stage, n.id)));
      if (entry.entity) box.append(sourceDetails(n));
    });
    box.append(diagram);
    const edges = map.edges.filter(e => selected.has(e.source) || selected.has(e.target));
    edges.forEach(e => {
      const edge = document.createElement('div'); edge.className = 'edge';
      edge.append(button(e.source, () => explore(map, entry.stage, e.source), 'chip'));
      edge.append(text('span', e.directed ? ' → ' : ' ↔ '));
      edge.append(button(e.target, () => explore(map, entry.stage, e.target), 'chip'));
      edge.append(text('p', e.description));
      edge.append(text('p', 'Extracted connection · ID ' + e.id + ' · chunks ' + (e.source_ids.join(', ') || 'unavailable'), 'relation-label'));
      box.append(edge);
    });
    if (!edges.length) box.append(text('p', 'No evidence-linked connection between these displayed components is available in this map.', 'hint'));
    if (!ids.length) box.append(text('p', 'The graph did not supply a supported component for this stage.', 'hint'));
    container.append(box);
  }
  function explore(map, stage, entity) {
    if (busy) return;
    current().messages.push({ kind: 'diagram', map, stage, entity }); save(); renderMessages();
    $('messages').lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
  function renderMessages() {
    $('messages').replaceChildren();
    current().messages.forEach(entry => {
      if (entry.kind === 'diagram') { displayExploration(entry, $('messages')); return; }
      const box = card(entry.kind === 'user' ? 'You' : 'Graph Oracle');
      if (entry.kind === 'user') box.classList.add('user');
      box.append(text('p', entry.text));
      if (entry.evidence?.length) {
        const details = document.createElement('details'); details.append(text('summary', 'Graph evidence · ' + entry.evidence.length + ' records'));
        entry.evidence.forEach(n => details.append(sourceDetails(n))); box.append(details);
      }
      if (entry.map) box.append(button('Explore this map', () => { current().messages.push({kind:'diagram',map:entry.map,stage:entry.map.focus}); save(); renderMessages(); }));
      $('messages').append(box);
    });
  }
  function fork(map) { if (busy) return; forkMap = map; $('forkTitle').textContent = map.title; $('forkQuestion').value = ''; $('forkDialog').showModal(); }
  function renderRail() {
    const map = currentMap(); $('stages').replaceChildren(); $('previousMaps').replaceChildren();
    $('mapEmpty').hidden = !!map; $('mapTools').hidden = !map;
    $('mapTitle').textContent = map?.title || 'Start with an ingredient';
    if (map) {
      stages.forEach((stage, index) => {
        const group = document.createElement('div'); group.className = 'stage' + (stage === map.focus ? ' active' : '');
        group.append(button(stage, () => explore(map, stage)));
        const components = document.createElement('div'); components.className = 'components';
        (map.stages[stage] || []).forEach(id => components.append(button(map.nodes.find(n => n.id === id)?.name || id, () => explore(map, stage, id))));
        if (!components.childNodes.length) components.append(text('span', 'No supported component', 'empty'));
        group.append(components); $('stages').append(group);
        if (index < stages.length - 1) $('stages').append(text('div', '↓', 'arrow'));
      });
      $('revision').textContent = 'Graph ' + map.graph_version.slice(0,8) + ' · feedback revision ' + map.feedback_revision;
    }
    const previous = current().maps.slice(0,-1).reverse();
    previous.forEach(old => {
      const details = document.createElement('details'); details.className = 'previous-map';
      details.append(text('summary', old.title));
      details.append(text('p', old.question, 'hint'));
      details.append(button('View diagram', () => explore(old, old.focus)));
      details.append(button('Ask in a new chat', () => fork(old))); $('previousMaps').append(details);
    });
  }
  function render() {
    $('chatList').replaceChildren();
    chats.slice().reverse().forEach(c => {
      const b = button(c.title, () => { if (busy) return; activeId=c.id; render(); });
      if(c.id===activeId)b.setAttribute('aria-current','true'); $('chatList').append(b);
    });
    renderMessages(); renderRail();
  }
  async function request(action, body) {
    const response = await fetch('/api/graph-oracle/' + action, { method: 'POST', credentials: 'same-origin', headers: {'Content-Type':'application/json','X-KG-Session':session}, body:JSON.stringify(body) });
    if (!response.ok) { const e=await response.json().catch(()=>({})); throw Error(e.error || 'Graph request failed ('+response.status+').'); }
    return response.json();
  }
  async function run(action, body, userText) {
    if (busy) return;
    busy=true; $('ask').disabled=true; $('revise').disabled=true; $('newChat').disabled=true;
    const chat=current();
    chat.messages.push({kind:'user',text:userText}); if(chat.title==='New exploration')chat.title=userText.slice(0,55);
    render(); $('requestStatus').textContent='Reading graph evidence and building your answer…';
    try {
      const result=await request(action,body);
      chat.messages.push({kind:'answer',text:result.answer,evidence:result.evidence,map:result.map});
      if(result.map)chat.maps.push(result.map);
      if(action==='feedback'){refreshStatus();feedbackRequest=null;$('feedback').value='';$('feedbackForm').hidden=true;}
      $('requestStatus').textContent=result.map ? 'Answer and process map ready.' : 'Answer ready. No ingredient map was created.';
    } catch(e){ $('requestStatus').textContent=e.message; }
    finally { busy=false; $('ask').disabled=false;$('revise').disabled=false;$('newChat').disabled=false;save();render(); }
  }
  $('questionForm').addEventListener('submit',e=>{e.preventDefault();const q=$('question').value.trim();if(!q||busy)return;const map=currentMap();$('question').value='';run('ask',{question:q,map_id:map?.id},q);});
  $('newChat').addEventListener('click',()=>newChat());
  $('mapHelpful').addEventListener('click', () => {
    const map = currentMap();
    if (!map || busy) return;
    run('feedback', {map_id:map.id, comment:'This map is useful as shown.', request_id:crypto.randomUUID()}, 'This map is useful as shown.');
  });
  $('feedbackOpen').addEventListener('click',()=>{$('feedbackForm').hidden=!$('feedbackForm').hidden;});
  $('feedbackForm').addEventListener('submit',e=>{e.preventDefault();const map=currentMap(),comment=$('feedback').value.trim();if(!map||!comment||busy)return;feedbackRequest ||= crypto.randomUUID();run('feedback',{map_id:map.id,comment,request_id:feedbackRequest},'Refine this map: '+comment);});
  $('feedback').addEventListener('input',()=>{feedbackRequest=null;});
  $('forkCancel').addEventListener('click',()=>$('forkDialog').close());
  $('forkForm').addEventListener('submit',e=>{e.preventDefault();const q=$('forkQuestion').value.trim();if(!q)return;const context=forkMap;$('forkDialog').close();newChat(context);run('ask',{question:q,map_id:context.id},q);});
  if(chats.length){activeId=chats.at(-1).id;render();}else newChat();
  function refreshStatus() {
    return fetch('/api/graph-oracle/status',{credentials:'same-origin'}).then(r=>r.json()).then(s=>{
    const message=s.ready ? s.nodes.toLocaleString()+' entities · '+s.connections.toLocaleString()+' connections · '+(s.source==='hosted_lightrag_graph'?'hosted LightRAG sandbox':'local LightRAG graph')+(s.graph_truncated?' · PARTIAL (graph read was truncated)':'') : s.message || 'Graph service unavailable.';
    $('connection').textContent=message;$('graphStatus').textContent=message;
    const sync=s.feedback_sync;
    $('syncStatus').textContent=sync ? sync.message+' '+sync.synced+' contributions synchronized'+(sync.pending ? ', '+sync.pending+' pending.' : '.') : 'Feedback connection unavailable.';
    if(!s.ready){$('ask').disabled=true;$('requestStatus').textContent='Connect the graph before asking a question.';}
  }).catch(()=>{$('connection').textContent='Graph service unavailable.';$('ask').disabled=true;});
  }
  refreshStatus();
  setInterval(() => { if (!document.hidden && !busy) refreshStatus(); }, 15000);
})();
