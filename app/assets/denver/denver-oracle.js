/* Updated 2026-10-31 · Persistent Denver at Oracle's viewport edge; first-party research notes. */
(function(){
 'use strict';
 if(document.getElementById('mcDenver') || !customElements.get('denver-companion'))return;
 var css=document.createElement('style');
 css.textContent='#mcDenver{position:fixed;right:0;top:clamp(100px,24vh,220px);width:min(360px,100vw);height:min(390px,calc(100dvh - 110px));z-index:2050;pointer-events:none}#mcDenver[hidden]{display:none!important}@media(max-height:550px){#mcDenver{top:70px;height:calc(100dvh - 75px)}}';
 document.head.appendChild(css);
 var pet=document.createElement('denver-companion');pet.id='mcDenver';pet.setAttribute('viewport','');pet.setAttribute('mood','curious');pet.setAttribute('motion-mode','system');pet.setAttribute('data-clarity-mask','true');pet.setAttribute('aria-label','Denver, your MeatCODE companion');
 var context=null,pending=false;
 function onOracle(){return !location.hash || location.hash==='#oracle';}
 function sync(){pet.hidden=!onOracle();}
 const still = document.getElementById('oracleDenverPeek');
 function revealAnimation() {
   // Leave the native editor intact if someone opened it while the kit was loading.
   if (!still || !pet.lastPose || pet.canvas.width < 2 || pet.canvas.height < 2 || pet.hidden) return;
   if (still.open || still.querySelector('textarea').value) { pet.style.visibility='hidden'; return; }
   pet.style.visibility='';
   still.hidden=true;
   pet.removeEventListener('denver:frame',revealAnimation);
 }
 if (still) {
   pet.addEventListener('denver:frame',revealAnimation);
   still.addEventListener('toggle',revealAnimation);
 }
 sync();document.body.appendChild(pet);window.addEventListener('hashchange',sync);
 window.addEventListener('pageshow',()=>{if(pet.isConnected&&!pet.hidden)pet.resize();});
 // Each offer arrives only after the research server commits an eligible answer.
 const questions = [];
 const panel = document.createElement('section');
 panel.hidden = true;
 panel.className = 'answer-rating';
 panel.setAttribute('aria-label','Denver answer feedback');
 panel.setAttribute('data-clarity-mask','true');
 panel.innerHTML = `<strong>How good is this answer?</strong><p class="which"></p>
   <div class="choices"><button data-rating="helpful">Good</button><button data-rating="neutral">Okay</button>
   <button data-rating="unhelpful">Poor</button></div>
   <button class="skip">Skip</button><small role="status"></small>`;
 const design = document.createElement('style');
 design.textContent = `.answer-rating{position:absolute;z-index:3;right:var(--denver-edge-width,49px);top:15%;width:232px;max-width:calc(100% - 58px);max-height:80%;overflow:auto;padding:14px;border:1px solid #cbbd9f;border-radius:14px;background:#fff9e9;box-shadow:0 3px 12px #36222524;pointer-events:auto}
 .answer-rating[hidden]{display:none}.answer-rating strong{font-size:16px}.answer-rating .which{font-size:12px;line-height:1.35;overflow-wrap:anywhere;margin:5px 0 10px;color:#685c54}
 .choices{display:flex;gap:5px}.choices button{flex:1;padding:6px 2px;color:#165e58;background:#fff;border:1px solid #b7c9c2;border-radius:7px}
 .answer-rating .skip{margin-top:7px;border:none;background:none;text-decoration:underline;color:#685c54}.answer-rating small:empty{display:none}`;
 pet.shadowRoot.append(design,panel);
 let sending = false;
 let displayed = null;
 function showRating() {
   while (questions.length && !questions[0].valid()) questions.shift();
   const next = questions[0];
   const show = !!next && onOracle() && !pet.noteOpen && !pet.opening;
   panel.hidden = !show;
   pet.ratingOpen = show;
   if (!show) return;
   pet.touchDenver();
   if (displayed === next) return;
   displayed = next;
   panel.querySelector('.which').textContent = 'Answer '+next.number+' · '+next.question;
   panel.querySelector('small').textContent = '';
   panel.querySelectorAll('button').forEach(button=>button.disabled=false);
 }
 panel.addEventListener('click', async function(event) {
   const button=event.target.closest('button'), offer=questions[0];
   if (!button || !offer || sending) return;
   if (!offer.valid() || button.classList.contains('skip')) {
     questions.shift();showRating();return;
   }
   sending=true;
   panel.querySelectorAll('button').forEach(b=>b.disabled=true);
   try {
     await offer.submit(button.dataset.rating);
     if (questions[0]===offer) questions.shift();
   } catch (_) {
     if (questions[0]===offer) {
       panel.querySelector('small').textContent='Could not confirm the save. Retry your rating or skip.';
       button.disabled=false;
       panel.querySelector('.skip').disabled=false;
     }
   } finally {
     sending=false;
     showRating();
   }
 });
 window.addEventListener('denver:rate-answer', function(event) {
   const offer=event.detail;
   if (!offer.valid() || questions.some(q=>q.turnId===offer.turnId)) return;
   questions.push(offer);showRating();
 });
 window.addEventListener('denver:session-end', function() {
   questions.length=0;displayed=null;showRating();
 });
 window.addEventListener('hashchange',showRating);
 pet.addEventListener('denver:note-open',showRating);
 pet.addEventListener('denver:note-close',showRating);
 function newContext(){return window.MCResearch&&MCResearch.noteContext(typeof window.oracleActiveId==='string'?window.oracleActiveId:null);}
 pet.addEventListener('denver:note-open',function(){if(!context || !pet.input.value.trim())context=newContext();});
 pet.input.addEventListener('input',function(){if(!context)context=newContext();});
 pet.addEventListener('denver:note',function(e){
  if(pending)return;
  if(!context)context=newContext();
  if(!window.MCResearch || !context){pet.setSubmission('error','Notes can be saved after entering your name in the production demo. Your text is still here.');return;}
  pending=true;pet.setSubmission('pending','Saving your note…');
  MCResearch.submitNote(e.detail.text,context).then(function(){pet.input.value='';context=null;pet.setSubmission('success','Thank you. Your note was saved to this session.');}).catch(function(){pet.setSubmission('error','Your note could not be saved. Your text is still here—please try again.');}).finally(function(){pending=false;});
 });
 pet.addEventListener('denver:oracle-request',function(e){
  if(pending)return;
  var input=document.getElementById('oracleTextarea');if(!input)return;
  if(input.value.trim() && input.value.trim()!==e.detail.text.trim()){pet.setSubmission('error','Your Oracle question already has a draft. Send or clear it before moving this text.');return;}
  location.hash='oracle';input.value=e.detail.text;input.dispatchEvent(new Event('input',{bubbles:true}));pet.closeNote();input.focus();
 });
 window.addEventListener('mc:oracle-state',function(e){pet.oraclePending=e.detail.state==='pending';pet.touchDenver();if(pending||pet.noteOpen||pet.opening)return;pet.react(e.detail.state==='pending'?'thinking':e.detail.state==='success'?'delighted':'oops');});
})();
