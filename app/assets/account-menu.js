/* Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — the sidebar profile card becomes the signed-in user's profile pop-out: Claude connection, usage this month + recent activity, Log out (returns to /welcome). Self-contained; every server string is written with textContent. */
(function () {
  'use strict';
  var ME = null, POP = null, OPEN_FOR = null;

  function $(sel, root) { return (root || document).querySelector(sel); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function api(path, body) {
    return fetch(path, {
      method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body)
    }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, json: j }; }); });
  }
  function fmt(n) {
    n = Number(n) || 0;
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + 'k';
    return String(n);
  }
  function ago(iso) {
    var t = Date.parse(iso); if (isNaN(t)) return '';
    var s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + ' min ago';
    if (s < 86400) return Math.floor(s / 3600) + ' h ago';
    return Math.floor(s / 86400) + ' d ago';
  }
  function initials(name) {
    var p = String(name || '?').trim().split(/\s+/);
    return ((p[0] || '?')[0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase();
  }
  function linked() { return !!(ME && ME.claude && ME.claude.status === 'linked'); }

  /* ── styles ─────────────────────────────────────────────────────────── */
  function injectStyle() {
    if ($('#mc-acct-style')) return;
    var s = el('style'); s.id = 'mc-acct-style';
    s.textContent =
      '.user-card.mc-acct{cursor:pointer}.user-card.mc-acct:hover{box-shadow:0 0 0 2px #B5DDD8}.user-card.mc-acct:focus-visible{outline:3px solid #B5DDD8;outline-offset:2px}' +
      '.mc-acct-initials{display:grid;place-items:center;width:100%;height:100%;font:700 15px/1 system-ui,-apple-system,"Segoe UI",sans-serif;color:#21595A}' +
      '#mc-acct-pop{position:fixed;z-index:2147483000;width:320px;max-width:calc(100vw - 24px);max-height:calc(100vh - 24px);overflow:auto;background:#fff;color:#1A1A1A;' +
      'border:1px solid #E5DDD0;border-radius:16px;box-shadow:0 18px 50px rgba(20,20,19,.22);font:14px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;outline:none}' +
      '#mc-acct-pop *{box-sizing:border-box}' +
      '#mc-acct-pop .h{display:flex;gap:12px;align-items:center;padding:16px 16px 12px}' +
      '#mc-acct-pop .av{flex:none;display:grid;place-items:center;width:44px;height:44px;border-radius:50%;background:#E0F0EE;color:#21595A;font-weight:700}' +
      '#mc-acct-pop .nm{font-weight:700;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '#mc-acct-pop .em{color:#55544F;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '#mc-acct-pop .sec{padding:12px 16px;border-top:1px solid #EFEBE0}' +
      '#mc-acct-pop .t{display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:700;font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:#55544F;margin-bottom:6px}' +
      '#mc-acct-pop p{margin:0 0 8px;color:#4A4A4A}' +
      '#mc-acct-pop .pill{display:inline-block;padding:2px 9px;border-radius:999px;font:600 12px/1.6 inherit;letter-spacing:0;text-transform:none;background:#EEE;color:#444}' +
      '#mc-acct-pop .pill.ok{background:#E3F3E8;color:#1E6B3A}#mc-acct-pop .pill.warn{background:#F8E9E2;color:#A8573A}' +
      '#mc-acct-pop .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:6px 0}' +
      '#mc-acct-pop .stat{background:#F5F4ED;border-radius:10px;padding:8px 6px;text-align:center}' +
      '#mc-acct-pop .stat b{display:block;font-size:17px}#mc-acct-pop .stat span{font-size:11px;color:#55544F}' +
      '#mc-acct-pop ul{list-style:none;margin:6px 0 0;padding:0}#mc-acct-pop li{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px dashed #EFEBE0;font-size:13px}' +
      '#mc-acct-pop li:last-child{border-bottom:0}#mc-acct-pop li small{color:#6B6A64;white-space:nowrap}#mc-acct-pop li.err span{color:#A8573A}' +
      '#mc-acct-pop .btn{display:inline-block;padding:8px 16px;border-radius:999px;border:1.5px solid #2F7F79;color:#2F7F79;background:transparent;text-decoration:none;font:inherit;font-weight:600;cursor:pointer}' +
      '#mc-acct-pop .btn.primary{background:#2F7F79;color:#fff}#mc-acct-pop .btn.out{width:100%;border-color:#D2C8B5;color:#4A4A4A;text-align:center}' +
      '#mc-acct-pop .btn:focus-visible{outline:3px solid #B5DDD8;outline-offset:2px}#mc-acct-pop .btn[disabled]{opacity:.6;cursor:progress}' +
      '#mc-acct-pop .muted{color:#6B6A64;font-size:13px}';
    document.head.appendChild(s);
  }

  /* ── pop-out contents ───────────────────────────────────────────────── */
  function header(av, name, sub) {
    var h = el('div', 'h'), a = el('div', 'av', av), box = el('div');
    box.style.minWidth = '0';
    box.appendChild(el('div', 'nm', name)); box.appendChild(el('div', 'em', sub));
    h.appendChild(a); h.appendChild(box);
    return h;
  }
  function claudeSection() {
    var c = (ME && ME.claude) || {}, sec = el('div', 'sec'), t = el('div', 't');
    t.appendChild(el('span', null, 'Claude'));
    var pill = el('span', 'pill ' + (linked() ? 'ok' : (c.needs_attention ? 'warn' : '')),
                  linked() ? 'Connected' : (c.needs_attention ? 'Needs attention' : 'Not connected'));
    t.appendChild(pill); sec.appendChild(t);
    sec.appendChild(el('p', null, linked()
      ? 'Questions you ask run on your own Claude organization and are billed to it.'
      : (c.available === false ? 'Connecting Claude isn\'t switched on for this server yet.'
         : 'Connect your Claude organization to ask the Oracle.')));
    if (linked() || c.available !== false) {
      var a = el('a', 'btn' + (linked() ? '' : ' primary'), linked() ? 'Manage connection' : 'Connect Claude');
      a.href = '/connect'; sec.appendChild(a);
    }
    return sec;
  }
  function usageSection() {
    var sec = el('div', 'sec'), t = el('div', 't'), label = el('span', null, 'Usage'), body = el('div');
    t.appendChild(label); sec.appendChild(t); body.appendChild(el('p', 'muted', 'Loading…')); sec.appendChild(body);
    api('/api/account/usage').then(function (r) {
      body.textContent = '';
      if (!r.ok || !r.json || r.json.available === false) { body.appendChild(el('p', 'muted', 'Usage isn\'t available yet.')); return; }
      var u = r.json;
      label.textContent = 'Usage · ' + (u.month_label || 'this month');
      var stats = el('div', 'stats');
      [['Requests', u.requests], ['Input tokens', fmt(u.input_tokens)], ['Output tokens', fmt(u.output_tokens)]].forEach(function (x) {
        var s = el('div', 'stat'); s.appendChild(el('b', null, String(x[1]))); s.appendChild(el('span', null, x[0])); stats.appendChild(s);
      });
      body.appendChild(stats);
      if (!u.recent || !u.recent.length) { body.appendChild(el('p', 'muted', 'No activity yet.')); return; }
      body.appendChild(el('div', 'muted', 'Recent activity'));
      var ul = el('ul');
      u.recent.slice(0, 5).forEach(function (it) {
        var li = el('li', it.status === 'error' ? 'err' : '');
        li.appendChild(el('span', null, it.label + (it.status === 'error' ? ' (failed)' : '') + ' · ' + fmt((it.input_tokens || 0) + (it.output_tokens || 0)) + ' tok'));
        li.appendChild(el('small', null, ago(it.at)));
        ul.appendChild(li);
      });
      body.appendChild(ul);
    }).catch(function () { body.textContent = ''; body.appendChild(el('p', 'muted', 'Usage isn\'t available yet.')); });
    return sec;
  }
  function credsHint() {
    var sec = el('div', 'sec');
    sec.appendChild(el('p', 'muted', 'Your profile lives in this browser. Add an email and password to sign in from other devices.'));
    var a = el('a', 'btn', 'Add email & password'); a.href = '/account'; sec.appendChild(a);
    return sec;
  }
  function logoutSection() {
    var sec = el('div', 'sec'), b = el('button', 'btn out', 'Log out'); b.type = 'button';
    b.onclick = function () {
      b.disabled = true;
      var go = function () { location.href = '/welcome'; };      // signing out always returns to the landing page
      api('/api/account/logout', {}).then(go).catch(go);
    };
    sec.appendChild(b); return sec;
  }
  function teamSection() {
    var sec = el('div', 'sec'), t = el('div', 't');
    t.appendChild(el('span', null, 'Access')); t.appendChild(el('span', 'pill', 'Shared password')); sec.appendChild(t);
    sec.appendChild(el('p', null, 'You\'re using the shared team password, so questions run on MeatCODE\'s own Claude account and aren\'t logged to a personal profile.'));
    var a = el('a', 'btn primary', 'Use your own Claude'); a.href = '/connect'; sec.appendChild(a);
    return sec;
  }
  function build() {
    var p = el('div'); p.id = 'mc-acct-pop'; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', 'Your profile'); p.tabIndex = -1;
    if (ME.signed_in) {
      p.appendChild(header(initials(ME.user.display_name || '?'), ME.user.display_name || 'You', ME.user.email || 'Signed in with Claude'));
      p.appendChild(claudeSection()); p.appendChild(usageSection());
      if (ME.user.has_credentials === false) p.appendChild(credsHint());
      p.appendChild(logoutSection());
    } else {
      p.appendChild(header('T', 'Team access', 'Shared password'));
      p.appendChild(teamSection());
    }
    return p;
  }

  /* ── open / close / position ────────────────────────────────────────── */
  function place(card) {
    var r = card.getBoundingClientRect(), pw = POP.offsetWidth, ph = POP.offsetHeight, m = 12;
    var left = Math.min(Math.max(m, r.left), window.innerWidth - pw - m);
    var top = (r.top - ph - 8 >= m) ? r.top - ph - 8 : Math.min(r.bottom + 8, window.innerHeight - ph - m);
    POP.style.left = left + 'px'; POP.style.top = Math.max(m, top) + 'px';
  }
  function close() {
    if (!POP) return;
    var card = OPEN_FOR; POP.remove(); POP = null; OPEN_FOR = null;
    if (card) { card.setAttribute('aria-expanded', 'false'); try { card.focus({ preventScroll: true }); } catch (_) {} }
  }
  function open(card) {
    close(); POP = build(); document.body.appendChild(POP); OPEN_FOR = card;
    card.setAttribute('aria-expanded', 'true'); place(card); POP.focus({ preventScroll: true });
    // usage loads after first paint and can change the height: re-place once it settles
    setTimeout(function () { if (POP && OPEN_FOR === card) place(card); }, 400);
  }

  /* ── make the card real ─────────────────────────────────────────────── */
  function personalize(card) {
    if (card.classList.contains('mc-acct')) return;
    card.classList.add('mc-acct'); card.setAttribute('role', 'button'); card.tabIndex = 0;
    card.setAttribute('aria-haspopup', 'dialog'); card.setAttribute('aria-expanded', 'false'); card.title = 'Your profile';
    if (!ME.signed_in) return;                               // team: card keeps its demo text, only the pop-out is added
    var set = function (sel, text) { var n = $(sel, card); if (n) n.textContent = text; };
    set('.user-name', ME.user.display_name || 'You'); set('.user-role', ME.user.email || 'Signed in with Claude');
    set('.user-org', linked() ? 'Claude connected' : 'Claude not connected');
    var av = $('.user-avatar', card);
    if (av) { while (av.firstChild) av.removeChild(av.firstChild); av.appendChild(el('span', 'mc-acct-initials', initials(ME.user.display_name || '?'))); }
  }

  function start() {
    fetch('/api/account/me', { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d || !d.enabled || !(d.signed_in || d.team)) return;   // accounts off, or neither a person nor the team: leave the product untouched
      ME = d; injectStyle();
      Array.prototype.forEach.call(document.querySelectorAll('.user-card'), personalize);
      document.addEventListener('click', function (e) {
        var card = e.target.closest && e.target.closest('.user-card.mc-acct');
        if (card) { if (OPEN_FOR === card) close(); else open(card); return; }
        if (POP && !POP.contains(e.target)) close();
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && POP) { close(); return; }
        var card = e.target && e.target.classList && e.target.classList.contains('mc-acct') ? e.target : null;
        if (card && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); if (OPEN_FOR === card) close(); else open(card); }
      });
      window.addEventListener('resize', function () { if (POP && OPEN_FOR) place(OPEN_FOR); });
    }).catch(function () {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
