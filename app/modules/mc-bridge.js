/* Last updated: 2026-10-25 · Yochai (PM) with Claude · NEW cross-module handoff bus for the embedded
   product modules (Science, Ecosystem) and the platform shell (app/meatcode_mockup.html).

   Why: modules run as same-origin iframes inside the platform (?embed=1), so a button inside Science
   ("Ask the Oracle about fat") can't just change the page. It posts a message to the shell instead, and
   the shell switches scene and delivers the payload to the target module. Opened standalone (no shell),
   the same call stores the handoff in sessionStorage and navigates to the platform, which replays it.

   Contract (all messages carry mc:1 and are only accepted from location.origin):
     module → shell   {mc:1, type:'open',  target, payload}   target: oracle | science | ecosystem
     module → shell   {mc:1, type:'ready', module}            sent once by MC.init(); shell answers with any
                                                              payload queued for that module
     shell  → module  {mc:1, type:'deliver', payload}         what the module should show (topic, query…)
   Payload fields used today: oracle {ask, send}, science {topic}, ecosystem {q, topic, expert}.
*/
(function () {
  'use strict';
  var HANDOFF_KEY = 'mc_handoff_v1';
  var qs = new URLSearchParams(location.search);
  var embedded = qs.get('embed') === '1' && window.parent !== window;
  if (embedded) document.documentElement.classList.add('mc-embed');

  var moduleName = null;
  var handler = null;

  function toShell(msg) {
    try { window.parent.postMessage(msg, location.origin); } catch (e) {}
  }

  var MC = {
    embedded: embedded,

    /* Open another part of MeatCODE. Inside the shell → postMessage; standalone → sessionStorage + navigate. */
    open: function (target, payload) {
      var msg = { mc: 1, type: 'open', target: String(target || ''), payload: payload || {} };
      if (embedded) { toShell(msg); return; }
      try { sessionStorage.setItem(HANDOFF_KEY, JSON.stringify(msg)); } catch (e) {}
      location.href = '/app/meatcode_mockup.html#' + encodeURIComponent(msg.target);
    },

    /* Register this page as module `name`; `onDeliver(payload)` runs whenever the shell (or a standalone
       handoff) asks this module to show something. */
    init: function (name, onDeliver) {
      moduleName = String(name || '');
      handler = typeof onDeliver === 'function' ? onDeliver : null;
      if (embedded) { toShell({ mc: 1, type: 'ready', module: moduleName }); return; }
      try {
        var raw = sessionStorage.getItem(HANDOFF_KEY);
        var msg = raw ? JSON.parse(raw) : null;
        if (msg && msg.target === moduleName) {
          sessionStorage.removeItem(HANDOFF_KEY);
          if (handler) handler(msg.payload || {});
        }
      } catch (e) {}
    }
  };

  window.addEventListener('message', function (e) {
    if (e.origin !== location.origin) return;
    var d = e.data;
    if (!d || d.mc !== 1 || d.type !== 'deliver') return;
    if (handler) { try { handler(d.payload || {}); } catch (err) {} }
  });

  window.MC = MC;
})();
