/* Updated 2026-10-31: Oracle viewport adapter and acknowledged research-note states. Original kit preserved separately. */
(function(){
'use strict';
// Milliseconds: change this constant to tune the inactivity reminder.
const DENVER_IDLE_PROMPT_MS = 30_000;
let nextId=0;
class DenverCompanion extends HTMLElement{
 static get observedAttributes(){return ['mood','motion-mode'];}
 constructor(){super();this.attachShadow({mode:'open'});this.mood='curious';this.motion='curious';this.started=0;this.manual=false;this.paused=false;this.forcedTime=null;this.look={x:0,y:-1};this.pointer={x:0,y:0,seen:false};this.frameCount=0;this.demoPointer=false;this.noteOpen=false;this.opening=false;this.lastTick=0;this.reduced=matchMedia('(prefers-reduced-motion: reduce)');this.widgetId=++nextId;this._globalPointer=e=>{if(e.pointerType==='touch')return;const r=this.getBoundingClientRect();this.pointer={x:e.clientX-r.left,y:e.clientY-r.top,seen:true};};this._key=e=>{if(e.key==='Escape'&&this.noteOpen)this.closeNote();};}
 connectedCallback(){
  if(this.initialized)return;this.initialized=true;
  this.shadowRoot.innerHTML=`<style>*{box-sizing:border-box}:host{display:block;position:relative;min-height:300px;overflow:hidden;background:#f1ebdf;color:#362225;font:14px/1.5 system-ui,sans-serif}canvas{width:100%;height:100%;position:absolute;inset:0;image-rendering:pixelated;pointer-events:none}.rail{position:absolute;top:0;bottom:0;right:13px;width:3px;background:#d7cbbb}button,textarea{font:inherit}button{cursor:pointer}button:focus-visible,textarea:focus-visible{outline:3px solid #165e58;outline-offset:3px}.hit{position:absolute;background:transparent;border:0;padding:0;border-radius:0}.paper{position:absolute;z-index:2;width:230px;max-width:calc(100% - 110px);padding:14px;background:#fff9dd;border:3px solid #491d20;box-shadow:5px 5px #cdbd9f;transform-origin:right var(--port,110px);animation:paper-in .3s steps(6)}.paper[hidden]{display:none}.head{display:flex;justify-content:space-between;align-items:center;gap:8px;font:18px Georgia,serif}.close{border:0;background:none;font-size:22px;padding:0 3px}textarea{box-sizing:border-box;width:100%;height:80px;margin:12px 0 9px;padding:8px;background:#fffdf4;border:1px solid #cbbd9f;resize:none;font-size:13px;color:#362225}.submit,.oracle{border:0;padding:9px 11px;background:#165e58;color:white;font-size:12px}.oracle{background:transparent;color:#165e58;padding:7px 0;display:block;text-align:left}small{display:block;font-size:10px;color:#806f5e;margin-top:8px}output{display:block;font-size:12px;color:#165e58;margin-top:8px}output:empty{display:none}.speech{position:absolute;left:20px;top:20px;max-width:62%;font:17px/1.45 Georgia,serif;pointer-events:none}.badge{position:absolute;left:20px;bottom:18px;font:11px monospace;color:#817575}.dot{position:absolute;border:2px dashed #165e58;width:20px;height:20px;border-radius:50%;pointer-events:none;transform:translate(-50%,-50%)}.dot[hidden]{display:none}@keyframes paper-in{from{opacity:0;transform:scale(.15)}to{opacity:1;transform:scale(1)}}@media(prefers-reduced-motion:reduce){.paper{animation:none}}:host([viewport]){min-height:0;background:transparent;pointer-events:none}:host([viewport]) .rail,:host([viewport]) .speech,:host([viewport]) .badge{display:none}:host([viewport]) .hit,:host([viewport]) .paper{pointer-events:auto}:host([viewport]) .paper{width:230px;max-width:calc(100% - 78px)}:host([viewport]) button:disabled{opacity:.6;cursor:wait}</style><div class="rail"></div><canvas aria-hidden="true"></canvas><span class="speech">Hi… I’m Denver.</span><button class="hit" aria-label="Open Denver’s note" aria-expanded="false"></button><span class="dot" hidden></span><form class="paper" hidden><div class="head"><label for="denver-text-${this.widgetId}">A little idea?</label><button type="button" class="close" aria-label="Close Denver’s note">×</button></div><textarea id="denver-text-${this.widgetId}" required maxlength="500" placeholder="What would you like to create?"></textarea><button class="submit" type="submit">Give Denver the note ↗</button><button class="oracle" type="button">Meet the Oracle →</button><small>Kit preview · no Oracle connection yet</small><output aria-live="polite"></output></form><span class="badge"></span>`;
  this.canvas=this.shadowRoot.querySelector('canvas');this.ctx=this.canvas.getContext('2d');this.sprite=document.createElement('canvas');this.sprite.width=this.sprite.height=96;this.sc=this.sprite.getContext('2d');this.hit=this.shadowRoot.querySelector('.hit');this.paper=this.shadowRoot.querySelector('.paper');this.input=this.shadowRoot.querySelector('textarea');this.output=this.shadowRoot.querySelector('output');this.speech=this.shadowRoot.querySelector('.speech');this.badge=this.shadowRoot.querySelector('.badge');this.dot=this.shadowRoot.querySelector('.dot');
  this.hit.onpointerenter=e=>{if(e.pointerType!=='touch'&&!this.hasAttribute('manual-only'))this.openNote(false);};this.hit.onclick=()=>this.openNote(true);this.shadowRoot.querySelector('.close').onclick=()=>this.closeNote();
  if(this.hasAttribute('viewport')){this.paper.setAttribute('data-clarity-mask','true');this.input.setAttribute('data-clarity-mask','true');this.input.maxLength=2000;this.shadowRoot.querySelector('label').textContent='A note for the team';this.input.placeholder='Tell us what you noticed…';this.shadowRoot.querySelector('.submit').textContent='Send note';this.shadowRoot.querySelector('.oracle').textContent='Use as an Oracle question →';this.shadowRoot.querySelector('small').textContent='Your note will be saved with this demo session.';}
  this.paper.onsubmit=e=>{e.preventDefault();if(this.busy)return;const text=this.input.value.trim();if(!text){this.input.setCustomValidity('Write a little idea first.');this.input.reportValidity();return;}this.input.setCustomValidity('');if(!this.hasAttribute('viewport'))this.output.textContent='Your idea is ready for the Oracle.';this.positionPaper();this.dispatchEvent(new CustomEvent('denver:note',{detail:{text},bubbles:true,composed:true}));};this.input.oninput=()=>this.input.setCustomValidity('');
  this.shadowRoot.querySelector('.oracle').onclick=()=>{const text=this.input.value.trim();this.dispatchEvent(new CustomEvent('denver:oracle-request',{detail:{text},bubbles:true,composed:true}));if(!this.hasAttribute('viewport'))this.output.textContent='Oracle invitation opened in this preview.';this.positionPaper();};
  if (this.hasAttribute('viewport')) this.setupAttention();
  window.addEventListener('pointermove',this._globalPointer,{passive:true,capture:true});document.addEventListener('keydown',this._key);this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(this);this.mood=this.getAttribute('mood')||'curious';this.motion=this.mood;this.started=performance.now();this.resize();this._loop=now=>{if(this.isConnected){if(!document.hidden&&now-this.lastTick>=45){this.lastTick=now;this.render(now);}this.raf=requestAnimationFrame(this._loop);}};this.raf=requestAnimationFrame(this._loop);
 }
 disconnectedCallback(){cancelAnimationFrame(this.raf);this.observer?.disconnect();window.removeEventListener('pointermove',this._globalPointer,true);this.attentionListeners?.abort();document.removeEventListener('keydown',this._key);this.initialized=false;}
 setupAttention() {
  const style = document.createElement('style');
  style.textContent = `
   .invite { position:absolute; right:var(--denver-edge-width,54px); z-index:1; display:grid; grid-template-columns:1fr auto; align-items:center; gap:2px; max-width:calc(100% - 62px); padding:2px 4px 2px 8px; border:1px solid #cfbe9e; border-radius:13px; background:#fff9e9; box-shadow:0 2px 6px #36222515; pointer-events:auto; }
   .invite[hidden] { display:none; }
   .invite button { min-height:32px; border:0; background:transparent; color:#3c302c; line-height:1.25; }
   .invite .dismiss { min-width:32px; color:#685c54; font-size:18px; }
   .invite .idle-question { font-weight:700; padding:4px 2px; }
   .invite .idle-actions { grid-column:1/-1; display:flex; flex-wrap:wrap; gap:8px; }
   .invite .resume { font-weight:700; color:#165e58; }`;
  this.invite = document.createElement('div');
  this.invite.className = 'invite';
  this.invite.hidden = true;
  this.invite.innerHTML = '<span class="idle-question" role="status" aria-live="polite"></span><button type="button" class="dismiss" aria-label="Dismiss Denver’s reminder">×</button><div class="idle-actions"><button type="button" class="resume">I’m here</button><button type="button" class="write">Leave a note</button></div>';
  this.shadowRoot.append(style, this.invite);
  this.invite.querySelector('.resume').onclick = () => { this.touchDenver(); this.hit.focus({preventScroll:true}); };
  this.invite.querySelector('.write').onclick = () => this.openNote(true);
  this.invite.querySelector('.dismiss').onclick = () => {
    this.invite.hidden = true;
    this.hit.focus({preventScroll:true});
    this.inviteShown = true;
  };
  this.attentionListeners = new AbortController();
  const options = {signal:this.attentionListeners.signal};
  // Watch interaction timing only; never read typed text or pointer coordinates.
  // Keep the bubble visible while its own buttons are being clicked or focused.
  const activity = event => {
    if (event.composedPath().includes(this.invite)) return;
    this.touchDenver();
  };
  ['pointermove','pointerdown','keydown','input','scroll','wheel'].forEach(name => {
    document.addEventListener(name, activity, {...options, passive:true, capture:true});
  });
  this.hit.addEventListener('pointerenter', () => this.touchDenver(), options);
  this.hit.addEventListener('pointerleave', () => this.touchDenver(), options);
  this.hit.addEventListener('focus', () => this.touchDenver(), options);
  document.addEventListener('visibilitychange', () => this.touchDenver(), options);
  window.addEventListener('hashchange', () => this.touchDenver(), options);
  this.touchDenver();
 }
 touchDenver() {
  if (!this.invite) return;
  this.idleSince = performance.now();
  this.invite.hidden = true;
  this.invite.querySelector('.idle-question').textContent = '';
  this.inviteShown = false;
 }
 idleMotion(now) {
  if (!this.invite) return this.motion;
  const welcomeOpen = document.getElementById('mcTesterWelcome')?.open;
  if (this.hidden || document.hidden || welcomeOpen || this.ratingOpen || this.noteOpen || this.opening || this.busy || this.oraclePending || document.querySelector('dialog:modal')) {
    this.touchDenver();
    return this.motion;
  }
  const idle = now - this.idleSince;
  if (idle < 20000) return this.motion;
  if (this.hit.matches(':hover')) {
    this.touchDenver();
    return this.motion;
  }
  if (idle >= DENVER_IDLE_PROMPT_MS && !this.inviteShown && !document.querySelector('dialog:modal')) {
    this.invite.style.top = Math.max(8, this.anchorY - 20) + 'px';
    this.invite.querySelector('.idle-question').textContent = 'Still there?';
    this.invite.hidden = false;
    this.inviteShown = true;
  }
  return this.invite.hidden ? 'sleepy' : 'curious';
 }
 attributeChangedCallback(name,old,value){if(name==='mood'&&DenverMotions.motions[value]){this.mood=value;if(!this.noteOpen&&!this.opening)this.play(value,false);}if(name==='motion-mode'&&this.initialized)this.render(performance.now());}
 react(name){if(!DenverMotions.motions[name])return;this.motion=name;this.started=performance.now();this.forcedTime=null;this.paused=false;this.render(performance.now());}
 setSubmission(state,message){this.busy=state==='pending';this.input.disabled=this.busy;this.shadowRoot.querySelectorAll('.submit,.oracle').forEach(b=>b.disabled=this.busy);this.output.textContent=message||'';this.react(state==='pending'?'thinking':state==='success'?'thanks':state==='error'?'oops':'listening');this.positionPaper();}
 get motionAllowed(){const mode=this.getAttribute('motion-mode')||'system';return mode==='on'||(mode!=='off'&&!this.reduced.matches);}
 resize(){const r=this.getBoundingClientRect();this.w=Math.max(1,Math.round(r.width));this.h=Math.max(1,Math.round(r.height));if(!this.canvas)return;this.canvas.width=this.w;this.canvas.height=this.h;this.u=Math.min(3.5,Math.max(1.8,(this.h-80)/96));if(this.hasAttribute('viewport'))this.u=window.innerWidth<=600 || window.innerHeight<=550 ? 1.9 : 2.6;this.boundary=this.hasAttribute('viewport')?this.w:this.w-14;this.anchorY=Math.max(125,this.h*.43);this.x=this.boundary-58*this.u;this.y=this.anchorY-48*this.u;Object.assign(this.hit.style,{left:(this.boundary-27*this.u)+'px',top:(this.y+6*this.u)+'px',width:31*this.u+'px',height:84*this.u+'px'});this.style.setProperty('--denver-edge-width', Math.ceil(27*this.u)+'px');this.positionPaper();this.render(performance.now());}
 positionPaper(){if(!this.paper)return;const height=this.paper.hidden?265:Math.ceil(this.paper.getBoundingClientRect().height);const top=Math.max(12,Math.min(this.h-height-14,this.anchorY+20*this.u-110));this.paper.style.right=(20+27*this.u)+'px';this.paper.style.top=top+'px';this.paper.style.setProperty('--port',(this.anchorY+20*this.u-top)+'px');}
 play(name,force=true){if(!DenverMotions.motions[name])return;this.motion=name;this.started=performance.now();this.manual=force;this.paused=false;this.forcedTime=null;this.noteOpen=false;this.opening=false;if(this.paper)this.paper.hidden=true;if(force)this.setAttribute('motion-mode','on');if(this.hit)this.hit.setAttribute('aria-expanded','false');this.render(performance.now());}
 scrub(fraction){this.paused=true;this.forcedTime=DenverMotions.motions[this.motion].duration*Math.max(0,Math.min(1,fraction));this.render(performance.now());}
 openNote(focus=false){this.touchDenver();if(!focus&&performance.now()<(this.cooldown||0))return;if(this.noteOpen){if(focus)this.input.focus();return;}if(this.opening){this.focusAfterOpen ||= focus;return;}this.play('note',false);this.opening=true;this.focusAfterOpen=focus;this.hit.setAttribute('aria-expanded','true');this.output.textContent='';this.render(performance.now());}
 closeNote(){this.touchDenver();this.cooldown=performance.now()+700;this.paper.hidden=true;this.hit.setAttribute('aria-expanded','false');this.noteOpen=this.opening=false;this.play(this.mood,false);this.hit.focus({preventScroll:true});this.dispatchEvent(new Event('denver:note-close'));}
 render(now){if(!this.ctx||!this.w)return;const motion=this.idleMotion(now),M=DenverMotions.motions[motion],elapsed=this.forcedTime??(this.paused?this.lastElapsed||0:Math.max(0,now-this.started));this.lastElapsed=elapsed;let ms=M.loop?elapsed%M.duration:Math.min(elapsed,M.duration);if(!this.motionAllowed)ms=this.motion==='note'?M.duration:0;
  if(this.opening&&(ms>=440||!this.motionAllowed)){this.opening=false;this.noteOpen=true;this.paper.hidden=false;this.positionPaper();if(this.focusAfterOpen)this.input.focus({preventScroll:true});this.dispatchEvent(new CustomEvent('denver:note-open',{bubbles:true,composed:true}));}
  const target=this.demoPointer?{x:this.w*.38+Math.sin(now/650)*this.w*.30,y:this.h*.43+Math.cos(now/870)*this.h*.27,seen:true}:this.pointer;this.dot.hidden=!this.demoPointer;if(this.demoPointer){this.dot.style.left=target.x+'px';this.dot.style.top=target.y+'px';}
  let tx=0,ty=-1;if(target.seen){tx=Math.max(-1.5,Math.min(1.5,-(target.y-this.anchorY)/(this.h*.22)));ty=Math.max(-3,Math.min(1,(target.x-this.boundary+this.w*.25)/(this.w*.28)));}this.look.x+=(tx-this.look.x)*.3;this.look.y+=(ty-this.look.y)*.3;
  const p=DenverMotions.pose(motion,ms,{lookX:this.look.x,lookY:this.look.y,still:!this.motionAllowed});if(this.noteOpen){p.noteOpen=true;p.noteAmount=1;p.eyeLift=3;}if (this.invite && motion === 'sleepy') {
    p.lid = 1;
  } else if (this.invite && target.seen) {
    const gaze = DenverSprite.gazeAt(target.x - (this.boundary - 14*this.u), target.y - this.anchorY);
    // This pose is turned a quarter turn. Screen left points down the sprite's Y axis.
    p.lookX = -gaze.y;
    p.lookY = gaze.x;
  }
  this.lastPose=p;
  const c=this.ctx;c.clearRect(0,0,this.w,this.h);c.imageSmoothingEnabled=false;DenverSprite.draw(this.sc,p);c.drawImage(this.sprite,Math.round(this.x),Math.round(this.y),96*this.u,96*this.u);
  if(p.accent){c.fillStyle='#d5a64a';const ax=this.boundary-33*this.u,ay=this.anchorY-12*this.u;if(p.accent==='dots'){for(let i=0;i<3;i++){c.globalAlpha=.25+.75*Math.max(0,Math.sin(ms/300-i));c.fillRect(ax-i*11,ay,4,4);}c.globalAlpha=1;}else{for(let i=0;i<(p.accent==='sparkles'?3:1);i++){const x=ax-i*15,y=ay+Math.sin(ms/250+i)*8;c.fillRect(x-4,y,12,4);c.fillRect(x,y-4,4,12);}}}
  if(this.noteOpen){const a=this.paper.getBoundingClientRect(),b=this.getBoundingClientRect(),left=a.right-b.left,mx=this.boundary-6*this.u,y=this.anchorY+20*this.u;c.fillStyle='#491d20';c.fillRect(left,y-6,Math.max(0,mx-left),12);c.fillStyle='#fff9dd';c.fillRect(left,y-3,Math.max(0,mx-left),6);}
  const line=this.noteOpen?'You can write it here. I’ll hold it.':M.line;if(this.speech.textContent!==line)this.speech.textContent=line;this.frameCount++;this.badge.textContent=this.motionAllowed?(this.paused?'Paused · use the timeline':M.label):'Motion paused by preference · press Play to preview';
  this.dispatchEvent(new CustomEvent('denver:frame',{detail:{motion,ms,frame:this.frameCount,allowed:this.motionAllowed,pointer:target.seen,lookX:p.lookX,lookY:p.lookY},bubbles:false}));
 }
}
customElements.define('denver-companion',DenverCompanion);
})();
