/* MeatCODE template connector
 * Last updated: 2026-07-05 13:30 UTC · deploy-templates session · initial version
 *
 * Drop-in bridge between a Claude Design template page and the MeatCODE
 * FastAPI server (server/reaktzia-mvp, port 8000) — the same server the
 * canonical mockup talks to. Include it in any template:
 *
 *     <script src="meatcode-api.js"></script>
 *
 * Two ways to use it:
 *
 * 1) Zero-JS auto-wiring with data attributes (works on exported templates
 *    without touching their scripts):
 *
 *      <textarea data-mc-input></textarea>
 *      <button data-mc-ask data-mc-output="#answer" data-mc-sources="#src">Ask</button>
 *      <div id="src"></div><div id="answer"></div>
 *
 *      <div data-mc-recent="6"></div>        ← fills with recent papers
 *      <span data-mc-health></span>          ← live server/DB status badge
 *
 *    A button may also carry data-mc-question="fixed question text" instead
 *    of pointing at an input (useful for starter-prompt chips).
 *
 * 2) Programmatic, from the template's own script:
 *
 *      MeatCODE.ask("why does heme drive meaty aroma?", {
 *        onSources: function (list) { ... },
 *        onChunk:   function (text, fullSoFar) { ... },
 *        onDone:    function (fullText) { ... },
 *        onError:   function (message) { ... }
 *      });
 *      MeatCODE.health().then(...);
 *      MeatCODE.paper(42).then(...);
 *      MeatCODE.recentPapers(6).then(...);
 */
(function () {
  'use strict';

  // Same rule as the mockup: opened as file:// → talk to localhost:8000;
  // served by the FastAPI server itself → relative paths.
  var API_BASE = (location.protocol === 'file:') ? 'http://127.0.0.1:8000' : '';

  function getJSON(path) {
    return fetch(API_BASE + path).then(function (res) {
      if (!res.ok) {
        return res.text().then(function (t) { throw new Error(t || ('HTTP ' + res.status)); });
      }
      return res.json();
    });
  }

  function escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ── core: POST /api/ask consumed as SSE (EventSource is GET-only) ── */
  function ask(question, opts) {
    opts = opts || {};
    var fullText = '';

    return fetch(API_BASE + '/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        k: opts.k || 5,
        model: opts.model || null
      })
    }).then(function (res) {
      if (!res.ok) {
        return res.text().then(function (t) { throw new Error(t || ('HTTP ' + res.status)); });
      }

      var reader  = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer  = '';

      function handleBlock(block) {
        var lines = block.split('\n');
        var event = 'message', dataLines = [];
        lines.forEach(function (ln) {
          if (ln.indexOf('event:') === 0) event = ln.slice(6).trim();
          else if (ln.indexOf('data:') === 0) dataLines.push(ln.slice(5).replace(/^ /, ''));
        });
        var data = dataLines.join('\n');
        if (event === 'sources' && opts.onSources) {
          try { opts.onSources(JSON.parse(data)); } catch (e) { /* malformed sources — skip */ }
        } else if (event === 'chunk') {
          fullText += data;
          if (opts.onChunk) opts.onChunk(data, fullText);
        } else if (event === 'error') {
          throw new Error(data || 'stream error');
        }
      }

      return reader.read().then(function pump(chunk) {
        if (chunk.done) {
          if (opts.onDone) opts.onDone(fullText);
          return fullText;
        }
        buffer += decoder.decode(chunk.value, { stream: true });
        var blocks = buffer.split('\n\n');
        buffer = blocks.pop();
        blocks.forEach(handleBlock);
        return reader.read().then(pump);
      });
    }).catch(function (e) {
      if (opts.onError) opts.onError(String(e && e.message ? e.message : e));
      else throw e;
    });
  }

  /* ── auto-wiring via data attributes ── */
  function resolveTarget(el, attr) {
    var sel = el.getAttribute(attr);
    return sel ? document.querySelector(sel) : null;
  }

  function wireAskButton(btn) {
    var handler = function () {
      var input = resolveTarget(btn, 'data-mc-input') ||
                  document.querySelector('[data-mc-input]');
      var q = btn.getAttribute('data-mc-question') ||
              (input ? input.value.trim() : '');
      if (!q) { if (input) input.focus(); return; }

      var out = resolveTarget(btn, 'data-mc-output');
      var src = resolveTarget(btn, 'data-mc-sources');
      if (out) out.innerHTML = '<em data-mc-state="loading">Searching the database and asking Claude…</em>';
      if (src) src.innerHTML = '';
      btn.disabled = true;

      ask(q, {
        onSources: function (list) {
          if (!src) return;
          src.innerHTML = list.map(function (s) {
            return '<span class="mc-source" data-paper-id="' + s.id + '">[' +
              s.id + '] ' + escapeHTML(s.title || '') +
              (s.year ? ' (' + s.year + ')' : '') + '</span>';
          }).join(' ');
        },
        onChunk: function (_piece, full) {
          if (out) out.textContent = full;
        },
        onDone: function () { btn.disabled = false; },
        onError: function (msg) {
          btn.disabled = false;
          if (out) out.innerHTML = '<em data-mc-state="error">' + escapeHTML(msg) +
            ' — is the FastAPI server running on port 8000?</em>';
        }
      });
    };
    btn.addEventListener('click', handler);

    var input = resolveTarget(btn, 'data-mc-input');
    if (input) {
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handler(); }
      });
    }
  }

  function wireRecent(el) {
    var limit = parseInt(el.getAttribute('data-mc-recent'), 10) || 6;
    getJSON('/api/papers/recent?limit=' + limit).then(function (papers) {
      el.innerHTML = papers.map(function (p) {
        return '<div class="mc-paper" data-paper-id="' + p.id + '">' +
          '<strong>' + escapeHTML(p.title || '') + '</strong>' +
          (p.year ? ' · ' + p.year : '') +
          (p.journal ? ' · ' + escapeHTML(p.journal) : '') +
          '</div>';
      }).join('');
    }).catch(function (e) {
      el.innerHTML = '<em data-mc-state="error">' + escapeHTML(String(e.message || e)) + '</em>';
    });
  }

  function wireHealth(el) {
    getJSON('/api/health').then(function (h) {
      var ok = h.ok && h.db_ok && h.has_anthropic_key;
      el.textContent = ok ? '● connected (' + (h.model || '') + ')'
                          : '● degraded' + (h.db_ok ? '' : ' — DB unreachable') +
                            (h.has_anthropic_key ? '' : ' — no API key');
      el.style.color = ok ? '#00736E' : '#B3261E';
    }).catch(function () {
      el.textContent = '● offline — start server/reaktzia-mvp (port 8000)';
      el.style.color = '#B3261E';
    });
  }

  function autowire() {
    document.querySelectorAll('[data-mc-ask]').forEach(wireAskButton);
    document.querySelectorAll('[data-mc-recent]').forEach(wireRecent);
    document.querySelectorAll('[data-mc-health]').forEach(wireHealth);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autowire);
  } else {
    autowire();
  }

  /* public API */
  window.MeatCODE = {
    API_BASE: API_BASE,
    ask: ask,
    health: function () { return getJSON('/api/health'); },
    paper: function (id) { return getJSON('/api/papers/' + id); },
    recentPapers: function (limit) { return getJSON('/api/papers/recent?limit=' + (limit || 6)); },
    escapeHTML: escapeHTML
  };
})();
