/* Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · NEW — the "Your process map" rail as one shared component, used by the
   Knowledge Graph Oracle page (graph-oracle.js) and by the classic Oracle's side panel (assets/oracle-process-map.js).
   A step toggles (blue while selected); a component opens a short info card in the rail instead of writing into the chat.
   Every server string is written with textContent. */
(() => {
  'use strict';
  const STAGES = ['Precursors', 'Reactions', 'Volatiles', 'Descriptors', 'Methods'];
  const SHORT_CHARS = 150;
  const chosen = new Map();                       // map id -> {stage, entity}: selection survives a re-render

  function el(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value != null) node.textContent = value;
    return node;
  }

  /* One short sentence from a graph description. LightRAG joins several extracted descriptions with "<SEP>";
     only the first is used, cut at its first sentence and at SHORT_CHARS. */
  function shortDescription(value) {
    let text = String(value || '').split('<SEP>')[0].replace(/\s+/g, ' ').trim();
    if (!text) return 'No description in the graph for this entry.';
    const stop = text.search(/[.!?](\s|$)/);
    if (stop > 20) text = text.slice(0, stop + 1);
    if (text.length > SHORT_CHARS) text = text.slice(0, SHORT_CHARS - 1).replace(/[\s,;:]+\S*$/, '') + '…';
    return text;
  }

  function infoCard(node, stage, close) {
    const card = el('div', 'pm-card');
    card.setAttribute('role', 'note');
    const head = el('div', 'pm-card-head');
    head.append(el('strong', '', node.name || node.id));
    const shut = el('button', 'pm-card-close', '×');
    shut.type = 'button';
    shut.setAttribute('aria-label', 'Close ' + (node.name || node.id));
    shut.addEventListener('click', close);
    head.append(shut);
    card.append(head);
    card.append(el('p', 'pm-card-kind', [stage, node.type].filter(Boolean).join(' · ')));
    card.append(el('p', 'pm-card-text', shortDescription(node.description)));
    const chunks = (node.source_ids || []).length;
    card.append(el('p', 'pm-card-kind', chunks ? chunks + ' evidence chunk' + (chunks === 1 ? '' : 's') + ' in the graph' : 'No evidence chunk listed'));
    return card;
  }

  /* render(host, map) — the rail is read-only towards the conversation: selecting a step or a component changes
     only the rail (2026-11-22: the "Show … in chat" links were removed at Lior's request). */
  function render(host, map, options) {
    options = options || {};
    host.replaceChildren();
    host.classList.add('pm-root');
    if (!map) return;
    if (!chosen.has(map.id)) chosen.set(map.id, { stage: STAGES.includes(map.focus) ? map.focus : null, entity: null });
    const state = chosen.get(map.id);
    const again = () => render(host, map, options);
    STAGES.forEach((stage, index) => {
      const ids = (map.stages && map.stages[stage]) || [];
      const group = el('div', 'pm-stage' + (state.stage === stage ? ' selected' : ''));
      const step = el('button', 'pm-step', stage);
      step.type = 'button';
      step.setAttribute('aria-pressed', state.stage === stage ? 'true' : 'false');
      step.addEventListener('click', () => {                 // toggle: a second click clears the step
        state.stage = state.stage === stage ? null : stage;
        if (state.entity && !ids.includes(state.entity)) state.entity = null;
        again();
      });
      group.append(step);
      const parts = el('div', 'pm-parts');
      ids.forEach(id => {
        const node = (map.nodes || []).find(n => n.id === id) || { id: id, name: id };
        const chip = el('button', 'pm-chip' + (state.entity === id ? ' selected' : ''), node.name || id);
        chip.type = 'button';
        chip.setAttribute('aria-pressed', state.entity === id ? 'true' : 'false');
        chip.addEventListener('click', () => {               // the card opens in the rail; the conversation is untouched
          state.entity = state.entity === id ? null : id;
          if (state.entity) state.stage = stage;
          again();
        });
        parts.append(chip);
      });
      if (!ids.length) parts.append(el('span', 'pm-empty', 'No supported component'));
      group.append(parts);
      const open = ids.includes(state.entity) ? (map.nodes || []).find(n => n.id === state.entity) : null;
      if (open) group.append(infoCard(open, stage, () => { state.entity = null; again(); }));
      host.append(group);
      if (index < STAGES.length - 1) host.append(el('div', 'pm-arrow', '↓'));
    });
  }

  window.MCProcessMap = { STAGES: STAGES, render: render, shortDescription: shortDescription };
})();
