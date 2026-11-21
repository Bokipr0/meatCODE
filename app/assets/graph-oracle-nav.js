/* Last updated: 2026-11-22 · Claude (Fable 5.2) · chip click no longer hijacked to #oracle by the shell's label router. Prior 2026-11-21 · Claude (Haiku 5.5) · the "Graph Oracle" top-banner chip is now gated by the graph_oracle feature
   switch (body.ff-graph_oracle, set by the /api/flags pass) instead of the backend status probe. Turning the switch on adds the chip
   to every topbar (after Science/Ecosystem/Oracle); turning it off removes it. Clicking opens the in-app #graphoracle scene.
   Prior 2026-11-21 · Claude (Sonnet 5.5) · Graph Oracle as a platform module, chip only when /api/graph-oracle/status was ready.
   Caveat: with the switch on but no backend (e.g. a production build without /api/graph-oracle/*), the chip shows and the
   scene will not load. */
(() => {
  'use strict';
  const ICON = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="4" cy="4.5" r="1.8"/><circle cx="12" cy="4" r="1.8"/><circle cx="8" cy="12" r="1.8"/><path d="M5.6 5.2 7 10.4M10.5 5.3 9 10.4M5.8 4.4h4.4"/></svg>';
  function insertChip() {
    if (!document.body.classList.contains('ff-graph_oracle')) {
      document.querySelectorAll('[data-mod-chip="graphoracle"]').forEach(node => node.remove());
      return;
    }
    document.querySelectorAll('.topbar .domains').forEach(row => {
      if (row.querySelector('[data-mod-chip="graphoracle"]')) return;
      const chip = document.createElement('div');
      chip.className = 'domain';
      chip.dataset.modChip = 'graphoracle';
      chip.title = 'Knowledge Graph Oracle';
      chip.innerHTML = ICON + 'Graph Oracle';
      chip.addEventListener('click', event => { event.stopPropagation(); location.hash = '#graphoracle'; });   // keep the shell's label router ("oracle" in the label) from overriding this
      const chips = Array.from(row.querySelectorAll('.domain'));
      const last = ['Ecosystem', 'Science', 'Oracle']
        .map(label => chips.find(d => (d.textContent || '').trim() === label))
        .find(Boolean);
      if (last) last.after(chip); else row.append(chip);
    });
    // Deep link (#graphoracle) loaded before the chip existed: re-run the router so the chip lights up.
    if (location.hash === '#graphoracle' && typeof setScene === 'function') setScene();
  }
  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn();
  }
  ready(() => {
    insertChip();
    try {
      new MutationObserver(insertChip).observe(document.body, {attributes: true, attributeFilter: ['class']});
    } catch (e) { /* older browsers: the chip still appears on the first load */ }
  });
})();
