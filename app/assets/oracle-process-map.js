/* Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · NEW — "Your process map" side panel for the classic Oracle.
   After each Oracle answer it asks the Knowledge Graph Oracle for the process map of the same question
   (POST /api/graph-oracle/ask, guided off) and draws it with the shared rail (app/modules/process-map.js):
   a step toggles blue, a component opens a short info card. Nothing is written into the Oracle conversation.
   Shown only when the graph_oracle feature switch is on (body.ff-graph_oracle). The map request is one extra
   model call per answer, so it is made only while the panel is open; a collapsed panel loads it when opened. */
(() => {
  'use strict';
  const OPEN_KEY = 'mc_oracle_process_map_open';
  let panel, tab, body, title, note, loaded = false, pending = null, shown = null, serial = 0;

  function flagOn() { return document.body.classList.contains('ff-graph_oracle'); }
  function isOpen() { try { return localStorage.getItem(OPEN_KEY) !== '0'; } catch (e) { return true; } }
  function setOpen(value) { try { localStorage.setItem(OPEN_KEY, value ? '1' : '0'); } catch (e) {} apply(); if (value && pending) load(pending); }

  function session() {
    let id = null;
    try { id = sessionStorage.getItem('mc_graph_session'); } catch (e) {}
    if (!id) { id = crypto.randomUUID(); try { sessionStorage.setItem('mc_graph_session', id); } catch (e) {} }
    return id;
  }

  function el(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value != null) node.textContent = value;
    return node;
  }

  function assets() {
    if (loaded) return Promise.resolve();
    loaded = true;
    const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = '/app/modules/process-map.css';
    document.head.append(css);
    const own = document.createElement('style');
    own.textContent =
      '.opm-panel{position:fixed;right:16px;top:84px;bottom:16px;width:286px;z-index:40;display:flex;flex-direction:column;' +
      'background:var(--bg,#FAF6EF);border:1px solid var(--line,#E5DDD0);border-radius:16px;box-shadow:var(--shadow-lg,0 10px 32px rgba(0,67,64,.12));overflow:hidden}' +
      '.opm-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;padding:16px 16px 6px}' +
      '.opm-eyebrow{font-size:10px;letter-spacing:.14em;font-weight:bold;color:var(--wine,#00736E)}' +
      '.opm-title{font-size:15px;line-height:1.4;margin:6px 0 0;color:var(--ink,#1A1A1A)}' +
      '.opm-hide,.opm-tab{font:inherit;cursor:pointer;border:1px solid var(--line-strong,#D2C8B5);background:#fff;color:var(--wine-deep,#015A56)}' +
      '.opm-hide{border-radius:8px;font-size:12px;padding:4px 8px;white-space:nowrap}' +
      '.opm-scroll{overflow:auto;padding:6px 16px 16px}' +
      '.opm-note{font-size:12px;line-height:1.6;color:var(--ink-dim,#4A4A4A);margin:6px 0 10px}' +
      '.opm-tab{position:fixed;right:0;top:120px;z-index:40;border-right:0;border-radius:12px 0 0 12px;padding:10px 12px;font-size:12px;font-weight:700;box-shadow:var(--shadow,0 4px 16px rgba(0,67,64,.08))}' +
      '.opm-hide:hover,.opm-tab:hover{background:var(--wine-mist,#E0F0EE)}' +
      /* Make room instead of covering the conversation, the question box or the Denver companion. */
      '@media(min-width:1101px){body.opm-open #oracle main.canvas{padding-right:310px}body.opm-open #mcDenver{right:310px !important}}' +
      '@media(max-width:1100px){.opm-panel{top:auto;height:58vh;box-shadow:0 -8px 30px rgba(0,67,64,.18)}}' +
      '@media(max-width:900px){.opm-panel{left:12px;right:12px;width:auto;top:auto;height:62vh}}';
    document.head.append(own);
    return new Promise(resolve => {
      if (window.MCProcessMap) return resolve();
      const script = document.createElement('script'); script.src = '/app/modules/process-map.js';
      script.onload = resolve; script.onerror = resolve; document.head.append(script);
    });
  }

  function build() {
    const scene = document.getElementById('oracle');
    if (!scene || panel) return;
    panel = el('aside', 'opm-panel'); panel.id = 'mcOracleProcessMap'; panel.setAttribute('aria-label', 'Process map');
    const head = el('div', 'opm-head'), left = el('div');
    left.append(el('span', 'opm-eyebrow', 'YOUR PROCESS MAP'));
    title = el('h2', 'opm-title', 'Ask about an ingredient'); left.append(title);
    const hide = el('button', 'opm-hide', 'Hide'); hide.type = 'button'; hide.addEventListener('click', () => setOpen(false));
    head.append(left, hide);
    const scroll = el('div', 'opm-scroll');
    note = el('p', 'opm-note', 'An ingredient or process question adds a map here: precursors, reactions, volatiles, descriptors and methods from the knowledge graph.');
    note.setAttribute('role', 'status');
    body = el('div');
    scroll.append(note, body);
    panel.append(head, scroll);
    tab = el('button', 'opm-tab', 'Process map'); tab.type = 'button'; tab.addEventListener('click', () => setOpen(true));
    scene.append(panel, tab);      // inside the Oracle scene: hidden with it on every other module
    apply();
  }

  function apply() {
    if (!panel) return;
    const on = flagOn(), open = on && isOpen();
    panel.hidden = !open; tab.hidden = !on || open;
    document.body.classList.toggle('opm-open', open);
  }

  function load(question) {
    pending = question;
    if (!flagOn() || !panel || !isOpen()) return;       // collapsed: fetched when the person opens the panel
    pending = null;
    const mine = ++serial;
    note.hidden = false; note.textContent = 'Building the process map from the knowledge graph…';
    fetch('/api/graph-oracle/ask', { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-KG-Session': session() },
      body: JSON.stringify({ question: String(question).slice(0, 2000), guided: false }) })
      .then(response => response.json().catch(() => ({})).then(data => ({ ok: response.ok, data: data })))
      .then(result => {
        if (mine !== serial) return;                       // a newer question has replaced this one
        if (!result.ok) { note.textContent = result.data.error || 'The process map is unavailable right now.'; return; }
        const map = result.data.map;
        if (!map) { note.textContent = shown ? 'No new map for that question — showing the last one.' : 'The knowledge graph has no process map for this question.'; return; }
        shown = map; title.textContent = map.title || 'Process map';
        note.textContent = 'From the knowledge graph. Select a step, or a component for a short description.';
        window.MCProcessMap.render(body, map, {});          // the panel never writes into the Oracle conversation
      })
      .catch(() => { if (mine === serial) note.textContent = 'The process map is unavailable right now.'; });
  }

  function start() {
    if (!flagOn()) { apply(); return; }
    assets().then(() => { build(); apply(); });
  }

  document.addEventListener('mc:oracle-answer-done', event => {
    const question = event.detail && event.detail.question;
    if (!question || !flagOn()) return;
    assets().then(() => { build(); if (window.MCProcessMap) load(question); });
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
  try { new MutationObserver(start).observe(document.body, { attributes: true, attributeFilter: ['class'] }); } catch (e) {}
})();
