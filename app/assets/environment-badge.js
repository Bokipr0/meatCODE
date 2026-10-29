/* Last updated: 2026-10-29 · Codex · server-verified development badge beside the brand. */
(function(){
  'use strict';
  fetch('/api/version',{credentials:'same-origin',cache:'no-store'}).then(function(response){
    if(!response.ok)throw new Error('Environment unavailable');return response.json();
  }).then(function(version){
    if(!version || version.env!=='dev')return;
    document.body.classList.add('mc-development-site');
    document.querySelectorAll('.topbar .brand-name,.brandbar .brand').forEach(function(brand){
      if(brand.querySelector('.mc-dev-label'))return;
      var badge=document.createElement('span');badge.className='mc-dev-label';badge.textContent='DEV';
      badge.title='Development site · developer settings and testing';
      badge.setAttribute('aria-label','Development site');brand.appendChild(badge);
    });
  }).catch(function(){ /* An unknown environment must never be labelled development. */ });
  var style=document.createElement('style');
  style.textContent='.mc-dev-label{display:inline-flex;vertical-align:middle;align-items:center;margin-left:8px;padding:3px 7px;border:1px solid var(--wine-tint,#b6d1c9);border-radius:6px;background:var(--wine-mist,#e4efeb);color:var(--wine,#00736e);font:700 10px/1.2 var(--round,system-ui);letter-spacing:.08em;white-space:nowrap}';
  document.head.appendChild(style);
})();
