/* Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · team pop-out shows the card's own profile (name, role, organisation); 'Use your own Claude' opens in a new tab so the page stays. Prior: 2026-11-22 UTC · Claude (Sonnet 5.5) · minimal: pop-out = name, Claude status, Add credits (only when needed), one usage line, Log out; Add-credits card = one sentence + two buttons. Prior: 2026-11-22 UTC · Claude (Sonnet 5.5) · free-trial status and a highlighted Add-credits button in the pop-out; window.mcShowCreditsGate draws the guided Add-credits card in the Oracle. Prior: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — the sidebar profile card becomes the signed-in user's profile pop-out: Claude connection, usage this month + recent activity, Log out (returns to /welcome). Self-contained; every server string is written with textContent. */
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
      '#mc-acct-pop li{flex-wrap:wrap}#mc-acct-pop li .pv{flex-basis:100%;color:#6B6A64;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '#mc-acct-pop li:last-child{border-bottom:0}#mc-acct-pop li small{color:#6B6A64;white-space:nowrap}#mc-acct-pop li.err span{color:#A8573A}' +
      '#mc-acct-pop .btn{display:inline-block;padding:8px 16px;border-radius:999px;border:1.5px solid #2F7F79;color:#2F7F79;background:transparent;text-decoration:none;font:inherit;font-weight:600;cursor:pointer}' +
      '#mc-acct-pop .btn.primary{background:#2F7F79;color:#fff}#mc-acct-pop .btn.out{width:100%;border-color:#D2C8B5;color:#4A4A4A;text-align:center}' +
      '#mc-acct-pop .btn:focus-visible{outline:3px solid #B5DDD8;outline-offset:2px}#mc-acct-pop .btn[disabled]{opacity:.6;cursor:progress}' +
      '#mc-acct-pop .muted{color:#6B6A64;font-size:13px}#mc-acct-pop p.warnline{color:#A8573A;font-weight:600}' +
      '.mc-gate{border:1.5px solid #D97757;background:#FFF8F4;border-radius:14px;padding:18px 20px;margin:6px 0;max-width:620px;color:#1A1A1A;font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}' +
      '.mc-gate h4{margin:0 0 6px;font-size:17px}.mc-gate p{margin:0 0 8px;color:#4A4A4A}.mc-gate ol{margin:6px 0 10px;padding-left:22px;color:#4A4A4A}.mc-gate li{margin:4px 0}' +
      '.mc-gate .row{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 8px}.mc-gate small{display:block;color:#6B6A64;font-size:12.5px}' +
      '.mc-gate .btn,#mc-acct-pop .btn.pulse{display:inline-block;padding:10px 18px;border-radius:999px;border:1.5px solid #2F7F79;color:#2F7F79;background:transparent;text-decoration:none;font:inherit;font-weight:600;cursor:pointer}' +
      '.mc-gate .btn.primary,.mc-gate .btn.pulse,#mc-acct-pop .btn.pulse{background:#2F7F79;color:#fff}' +
      '@keyframes mcpulse{0%{box-shadow:0 0 0 0 rgba(217,119,87,.55)}70%{box-shadow:0 0 0 12px rgba(217,119,87,0)}100%{box-shadow:0 0 0 0 rgba(217,119,87,0)}}' +
      '.mc-gate .btn.pulse,#mc-acct-pop .btn.pulse{animation:mcpulse 1.8s ease-out infinite}' +
      '@media (prefers-reduced-motion:reduce){.mc-gate .btn.pulse,#mc-acct-pop .btn.pulse{animation:none;outline:3px solid #D97757;outline-offset:2px}}';
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
  var BILLING = 'https://platform.claude.com/settings/billing';
  function addCreditsButton(url) {
    var a = el('a', 'btn pulse', 'Add credits');                       // the highlighted step: opens Claude's Billing page
    a.href = (url && /^https:\/\/platform\.claude\.com\//.test(url)) ? url : BILLING; a.target = '_blank'; a.rel = 'noopener noreferrer';
    return a;
  }
  function fillClaudeExtra(box, u) {
    var t = u.trial;
    if (u.needs_credits) {
      box.appendChild(addCreditsButton(u.billing_url));                 // the one highlighted action, no explanation
    } else if (t && t.sessions_total > 0 && !t.exhausted) {
      var n = Math.min(t.answers_in_session > 0 ? t.sessions_used : t.sessions_used + 1, t.sessions_total);
      box.appendChild(el('p', 'muted', 'Free trial · session ' + n + ' of ' + t.sessions_total));
    }
  }
  function claudeSection(usageP) {
    var c = (ME && ME.claude) || {}, sec = el('div', 'sec'), t = el('div', 't');
    t.appendChild(el('span', null, 'Claude'));
    t.appendChild(el('span', 'pill ' + (linked() ? 'ok' : (c.needs_attention ? 'warn' : '')),
                     linked() ? 'Connected' : (c.needs_attention ? 'Needs attention' : 'Not connected')));
    sec.appendChild(t);
    var extra = el('div'); sec.appendChild(extra);                      // trial status / Add credits, once usage has loaded
    usageP.then(function (r) { if (r.ok && r.json && r.json.available !== false) fillClaudeExtra(extra, r.json); }).catch(function () {});
    if (!linked() && c.available !== false) { var a = el('a', 'btn primary', 'Connect Claude'); a.href = '/connect'; sec.appendChild(a); }
    return sec;
  }
  function usageSection(usageP) {
    var sec = el('div', 'sec'), line = el('p', 'muted');
    sec.style.display = 'none'; sec.appendChild(line);
    usageP.then(function (r) {
      if (!r.ok || !r.json || r.json.available === false) return;       // no usage table / not signed in: show nothing
      var u = r.json;
      line.textContent = u.requests ? u.requests + ' request' + (u.requests === 1 ? '' : 's') + ' · ' + fmt((u.input_tokens || 0) + (u.output_tokens || 0)) + ' tokens this month' : 'No usage yet';
      sec.style.display = '';
    }).catch(function () {});
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
    sec.appendChild(el('p', null, 'Signed in with the team password. Questions run on MeatCODE\'s Claude account and aren\'t saved to a personal profile.'));
    var a = el('a', 'btn', 'Use your own Claude'); a.href = '/connect'; a.target = '_blank'; a.rel = 'noopener'; sec.appendChild(a);   // new tab: the page you are on stays put
    return sec;
  }
  function build(card) {
    var p = el('div'); p.id = 'mc-acct-pop'; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', 'Your profile'); p.tabIndex = -1;
    if (ME.signed_in) {
      p.appendChild(header(initials(ME.user.display_name || '?'), ME.user.display_name || 'You', ME.user.email || 'Signed in with Claude'));
      var usageP = api('/api/account/usage');                         // one request feeds both sections
      p.appendChild(claudeSection(usageP)); p.appendChild(usageSection(usageP));
      p.appendChild(logoutSection());
    } else {
      // Team access has no personal account: show the profile this card carries, then how access works.
      var txt = function (sel) { var n = card && $(sel, card); return n ? (n.textContent || '').trim() : ''; };
      var nm = txt('.user-name') || 'Team access';
      p.appendChild(header(nm === 'Team access' ? 'T' : initials(nm), nm, [txt('.user-role'), txt('.user-org')].filter(Boolean).join(' · ') || 'Shared password'));
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
    close(); POP = build(card); document.body.appendChild(POP); OPEN_FOR = card;
    card.setAttribute('aria-expanded', 'true'); place(card); POP.focus({ preventScroll: true });
    // usage loads after first paint and can change the height: re-place once it settles
    setTimeout(function () { if (POP && OPEN_FOR === card) place(card); }, 400);
  }

  /* ── Oracle: free sessions used + no credits on the person's Claude account ── */
  window.mcShowCreditsGate = function (data, bodyEl, question) {
    var info = {}; try { info = JSON.parse(data) || {}; } catch (_) {}
    injectStyle();
    var card = el('div', 'mc-gate'); card.setAttribute('role', 'alert');
    card.appendChild(el('h4', null, 'Add credits to keep asking'));
    card.appendChild(el('p', null, 'Your free sessions are used. Add credits to your Claude account to continue.'));
    var row = el('div', 'row'), add = addCreditsButton(info.billing_url); add.className = 'btn pulse';
    var retry = el('button', 'btn', 'I added credits — try again'); retry.type = 'button';
    retry.onclick = function () {
      var ta = document.getElementById('oracleTextarea');
      if (ta && question && typeof window.askOracle === 'function') { ta.value = question; window.askOracle(); } else { location.reload(); }
    };
    row.appendChild(add); row.appendChild(retry); card.appendChild(row);
    if (bodyEl) { while (bodyEl.firstChild) bodyEl.removeChild(bodyEl.firstChild); bodyEl.appendChild(card); }
  };

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
