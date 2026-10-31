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
 sync();document.body.appendChild(pet);window.addEventListener('hashchange',sync);
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
 window.addEventListener('mc:oracle-state',function(e){if(pending||pet.noteOpen||pet.opening)return;pet.react(e.detail.state==='pending'?'thinking':e.detail.state==='success'?'delighted':'oops');});
})();
