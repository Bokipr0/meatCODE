/* Last updated: 2026-11-18 09:04 UTC · Codex · Compact source expansion and visible next steps. */
(function (root) {
  'use strict';
  var MAX_BRIEF_WORDS = 120;
  function split(text, briefEnd, streaming) {
    text = String(text || '');
    var boundary = Number.isInteger(briefEnd) && briefEnd > 0 && briefEnd <= text.length ? briefEnd : null;
    var words = Array.from(text.matchAll(/\S+/g));
    var cap = words.length > MAX_BRIEF_WORDS ? words[MAX_BRIEF_WORDS].index : text.length;
    if (boundary === null) {
      // Old answers and models that ignore the format remain fully readable on expansion.
      var paragraph = streaming ? -1 : text.search(/\n\s*\n/);
      boundary = paragraph > 0 ? paragraph : text.length;
    }
    boundary = Math.min(boundary, cap);
    if (boundary === cap && cap < text.length) {
      // Prefer a complete sentence if the model's introductory paragraph is too long.
      var candidate = text.slice(0, cap), sentence = /[.!?](?:\s*\[\d+\])*\s+(?=\S)/g, match, last = 0;
      while ((match = sentence.exec(candidate))) last = match.index + match[0].length;
      if (last > 0) boundary = last;
    }
    var brief = text.slice(0, boundary).trim(), detail = text.slice(boundary).trim();
    // Older guided answers placed their explicit action in the final paragraph. Keep that
    // recommendation visible without generating, shortening or inventing another one.
    if (!/\bNext step:/i.test(brief)) {
      var next = /\bNext step:\s*[\s\S]*?(?=\n\s*\n|$)/i.exec(detail);
      if (next) {
        brief += '\n\n' + next[0].trim();
        detail = (detail.slice(0,next.index) + detail.slice(next.index+next[0].length)).trim();
      }
    }
    return { brief: brief, detail: detail, boundary: boundary };
  }
  function mount(body, text, citedIds, options) {
    if (!body) return;
    options = options || {};
    var previous = body.querySelector('.oracle-answer-detail');
    var open = previous && previous.open;
    var restoreFocus = previous && previous.querySelector('summary') === body.ownerDocument.activeElement;
    var parts = split(text, options.briefEnd, options.streaming);
    body.innerHTML = '<div class="oracle-answer-brief">' + options.format(parts.brief, citedIds) + '</div>' +
      (parts.detail || options.moreSources ? '<details class="oracle-answer-detail"' + (open ? ' open' : '') + '>' +
        '<summary><span class="oracle-expand-label">Expand answer</span><span class="oracle-collapse-label">Show less</span></summary>' +
        (parts.detail ? '<div class="oracle-answer-support" role="region" aria-label="Supporting detail">' + options.format(parts.detail, citedIds) + '</div>' : '') + '</details>' : '');
    if (restoreFocus) {
      var summary = body.querySelector('.oracle-answer-detail summary');
      if (summary) summary.focus({ preventScroll: true });
    }
    return parts;
  }
  var api = { split: split, mount: mount, maxBriefWords: MAX_BRIEF_WORDS };
  root.MCOracleAnswer = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
