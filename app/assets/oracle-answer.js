/* Last updated: 2026-11-17 · Codex · Short answer with accessible supporting detail. */
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
    return { brief: text.slice(0, boundary).trim(), detail: text.slice(boundary).trim(), boundary: boundary };
  }
  function mount(body, text, citedIds, options) {
    if (!body) return;
    options = options || {};
    var previous = body.querySelector('.oracle-answer-detail');
    var open = previous && previous.open;
    var restoreFocus = previous && previous.querySelector('summary') === body.ownerDocument.activeElement;
    var parts = split(text, options.briefEnd, options.streaming);
    body.innerHTML = '<div class="oracle-answer-brief">' + options.format(parts.brief, citedIds) + '</div>' +
      (parts.detail ? '<details class="oracle-answer-detail"' + (open ? ' open' : '') + '>' +
        '<summary><span class="oracle-expand-label">Expand answer</span><span class="oracle-collapse-label">Show less</span></summary>' +
        '<div class="oracle-answer-support" role="region" aria-label="Supporting detail">' + options.format(parts.detail, citedIds) + '</div></details>' : '');
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
