/* Last updated: 2026-10-29 · Codex · Release Center demo/portrait flags and browser-local avatar selection. */
(function(){
 'use strict';
 var DEFAULT='/app/assets/meatcode-avatar.jpg',KEY='mc_oracle_avatar_v1',flags={},dialog;
 function chosen(){try{var value=localStorage.getItem(KEY);return value&&/^data:image\/webp;base64,/.test(value)&&value.length<400000?value:DEFAULT;}catch(_){return DEFAULT;}}
 function apply(){
  var demo=flags.demo_badge===true;
  document.querySelectorAll('.topbar .brand-name').forEach(function(brand){
   var badge=brand.querySelector('.mc-demo-label');
   if(!demo){if(badge)badge.remove();return;}
   if(!badge){badge=document.createElement('span');badge.className='mc-demo-label';badge.textContent='DEMO';badge.title='MeatCODE demonstration platform';brand.appendChild(badge);}
  });
  document.querySelectorAll('#oracle .oracle-empty-state .icon').forEach(function(icon){
   if(!flags.meatcode_avatar){if(icon.textContent!=='M'||icon.children.length)icon.replaceChildren(document.createTextNode('M'));return;}
   var button=icon.querySelector('button');if(button)return;
   icon.replaceChildren();button=document.createElement('button');button.type='button';button.className='mc-avatar-change';button.title='Change Oracle icon';button.setAttribute('aria-label','Change Oracle icon');
   var img=document.createElement('img');img.src=chosen();img.alt='MeatCODE: meaty flavour meets molecular science';img.onerror=function(){if(img.getAttribute('src')!==DEFAULT)img.src=DEFAULT;};button.appendChild(img);button.onclick=openPicker;icon.appendChild(button);
  });
 }
 function refreshImages(){document.querySelectorAll('.mc-avatar-change img').forEach(function(img){img.src=chosen();});}
 function openPicker(){
  if(!dialog){dialog=document.createElement('dialog');dialog.className='mc-avatar-dialog';dialog.setAttribute('aria-label','Choose Oracle icon');
   dialog.innerHTML='<h2>Oracle icon</h2><p>Choose an image for this browser. It stays on this device.</p><label>Image (PNG, JPEG or WebP, up to 5 MB)<input type="file" accept="image/png,image/jpeg,image/webp"></label><p role="status"></p><button type="button" data-reset>Use MeatCODE icon</button><button type="button" data-close>Done</button>';
   document.body.appendChild(dialog);var status=dialog.querySelector('[role=status]');
   dialog.querySelector('[data-close]').onclick=function(){dialog.close();};
   dialog.querySelector('[data-reset]').onclick=function(){try{localStorage.removeItem(KEY);refreshImages();status.textContent='MeatCODE icon restored.';}catch(_){status.textContent='Browser storage is unavailable.';}};
   dialog.querySelector('input').onchange=function(e){var file=e.target.files[0];if(!file)return;
    if(!/^image\/(png|jpeg|webp)$/.test(file.type)||file.size>5*1024*1024){status.textContent='Choose a PNG, JPEG or WebP under 5 MB.';return;}
    var url=URL.createObjectURL(file),img=new Image();img.onload=function(){
     try{if(img.width>8192||img.height>8192)throw new Error();var canvas=document.createElement('canvas');canvas.width=canvas.height=256;var context=canvas.getContext('2d'),size=Math.min(img.width,img.height);context.drawImage(img,(img.width-size)/2,(img.height-size)/2,size,size,0,0,256,256);var value=canvas.toDataURL('image/webp',.85);localStorage.setItem(KEY,value);refreshImages();status.textContent='Icon updated for this browser.';}catch(_){status.textContent='Image could not be saved. Try a smaller image.';}finally{URL.revokeObjectURL(url);}
    };img.onerror=function(){URL.revokeObjectURL(url);status.textContent='This image could not be opened.';};img.src=url;
   };
  }dialog.showModal();
 }
 var style=document.createElement('style');style.textContent='.topbar .brand-name{display:inline-flex;align-items:center;white-space:nowrap}.mc-demo-label{display:inline-flex;vertical-align:middle;margin-left:8px;padding:3px 7px;border:1px solid var(--line-strong);border-radius:6px;background:var(--surface-2);color:var(--wine);font:700 10px/1.2 var(--round,system-ui);letter-spacing:.08em}.mc-avatar-change{width:100%;height:100%;padding:0;border:0;border-radius:50%;overflow:hidden;cursor:pointer;background:var(--wine)}.mc-avatar-change img{display:block;width:100%;height:100%;object-fit:cover}.mc-avatar-change:focus-visible{outline:3px solid var(--wine);outline-offset:4px}#oracle .oracle-empty-state .icon:has(.mc-avatar-change){width:96px;height:96px;overflow:visible}.mc-avatar-dialog{max-width:min(420px,calc(100vw - 32px));padding:26px;border:1px solid var(--line);border-radius:18px;background:var(--surface);color:var(--ink);font:14px/1.5 var(--round,system-ui)}.mc-avatar-dialog button{padding:9px 14px;margin:12px 8px 0 0;border:1px solid var(--line);border-radius:10px;background:var(--wine-mist);color:var(--wine);cursor:pointer}.mc-avatar-dialog input{display:block;margin-top:10px;max-width:100%}';document.head.appendChild(style);
 fetch('/api/flags',{credentials:'same-origin',cache:'no-store'}).then(function(r){if(!r.ok)throw new Error();return r.json();}).then(function(value){flags=value||{};apply();}).catch(function(){});
 var thread=document.getElementById('oracleThread');if(thread)new MutationObserver(function(){apply();}).observe(thread,{childList:true,subtree:true});
})();
