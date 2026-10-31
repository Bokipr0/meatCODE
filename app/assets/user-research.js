/* Last updated: 2026-10-31 · Name-only Oracle welcome, durable session binding and tab isolation. */
(function () {
  'use strict';
  // Known browser automation must not create research rows or provider sessions.
  if (navigator.webdriver === true || window.MCResearch) return;
  var VERSION = '2026-10-29-journey-v1', CONSENT_KEY = 'mc_research_consent_v1', SESSION_KEY = 'mc_research_session_v1';
  var demoMode = false, internalStopping=false, INTERNAL_KEY='mc_research_internal';
  var PENDING_KEY = 'mc_research_withdraw_pending_v1';
  var SCENES = ['oracle','research','science','ecosystem','simulate','analytics','database','map','papers','dev','inventory'];
  var ERRORS = ['network','model_unavailable','session_expired','unknown'];
  var config = null, active = false, session = null, queue = [], timer = null, sending = false;
  var generation = 0, loaded = false, needsReload = false, requests = new Set(), panel, status, consentSection, feedbackSection;
  var ph = null, phLoading = false, phInitialized = false, phQueue = [], phIdentity = null;
  var NAMES = ['session.started','scene.viewed','module.clicked','oracle.submitted','oracle.completed','oracle.failed','feedback.submitted'];
  var chatConsent=false, conversations={}, CHAT_KEY='mc_research_chat_consent_v1', CHAT_MAP='mc_research_chat_map_v1';
  var journey=null, journeyBaseline=0, journeyPerformance=0, JOURNEY_KEY='mc_research_journey_v1';
  var starting=false, welcome=null;
  var nativeFetch = window.fetch.bind(window);
  document.body.setAttribute('data-clarity-mask', 'true');
  function read(key) { try { return sessionStorage.getItem(key); } catch (_) { return null; } }
  function save(key, value) { try { if (value === null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, value); } catch (_) {} }
  function uuid() { return window.crypto && typeof window.crypto.randomUUID === 'function' ? window.crypto.randomUUID() : null; }
  function validUUID(value) { return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value || ''); }
  function scene() { var value = location.hash.replace(/^#/, ''); return SCENES.indexOf(value) >= 0 ? value : 'other'; }
  function internalBrowser(){try{return localStorage.getItem(INTERNAL_KEY)==='1';}catch(_){return false;}}
  function permitted() { return !internalBrowser() && active && config && config.environment==='prod' && config.enabled === true && session; }
  function speak(text) { if (status) status.textContent = text; }
  function elapsed(){return journey?Math.max(0,Math.min(86400000,Math.round(journeyBaseline+performance.now()-journeyPerformance))):null;}
  function journeyFields(body){if(!journey)return body;body.user_ref=journey.user_ref;if(journey.clarity_ref)body.clarity_ref=journey.clarity_ref;if(journey.tester_label)body.tester_label=journey.tester_label;return body;}
  function clarityReference(){if(chatConsent&&journey&&validUUID(journey.clarity_ref))clarityCall('set','research_reference',journey.clarity_ref);}
  function post(path, body, signal) {
    return nativeFetch('/api/research/' + path, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-MeatCODE-Research':'1'}, body:JSON.stringify(body), referrerPolicy:'no-referrer', signal:signal}).then(function (res) {
      if (!res.ok) throw new Error('RESEARCH_REQUEST_FAILED');
      return res;
    });
  }
  function event(name, properties, providerProperties, targetScene) {
    if (!permitted()) return;
    var id = uuid(); if (!id) return;
    // Callers receive no generic logger: only these allow-listed lifecycle methods reach here.
    var target=SCENES.indexOf(targetScene)>=0?targetScene:scene();
    queue.push({event_id:id, name:name, scene:target, elapsed_ms:elapsed(),properties:properties || {}});
    if (loaded && safeURL()) { clarityCall('set','scene',target); clarityCall('event',name);if(name==='module.clicked')clarityCall('event','module.'+target+'.clicked'); }
    posthogEvent(name, Object.assign({},providerProperties || properties || {},{scene:target}));
    if (queue.length > 100) queue.shift();
    if (!timer) timer = setTimeout(flush, 200);
    if(name==='module.clicked'){if(timer)clearTimeout(timer);flush();}
  }
  function flush() {
    timer = null;
    if (!permitted() || sending || !queue.length) return;
    var batch = queue.splice(0,20), sid = session, current = generation, controller = new AbortController();
    sending = true;
    var request = post('events', journeyFields({session_id:sid, consent:true, consent_version:VERSION, events:batch}), controller.signal);
    requests.add(controller);
    request.catch(function () { /* testing never blocks the product; failed batches are not retained */ }).finally(function () {
      requests.delete(controller); sending = false;
      if (current === generation && permitted() && queue.length) timer = setTimeout(flush, 200);
    });
  }
  function clarityCall() { if (typeof window.clarity === 'function') window.clarity.apply(window, arguments); }
  function safeURL() {
    // Clarity records page URLs itself: fail closed rather than alter a user's route.
    return !location.search && (!location.hash || SCENES.indexOf(location.hash.slice(1)) >= 0);
  }
  function loadClarity() {
    if (!permitted() || loaded || config.clarity_project_id !== 'z4upnrbddu') return;
    if (location.pathname !== '/' && location.pathname !== '/app/meatcode_mockup.html') return;
    if (!safeURL()) return;
    document.body.setAttribute('data-clarity-mask', 'true');
    if (document.querySelector('[data-clarity-unmask]')) return; // fail closed if another integration unmasks content
    loaded = true;
    window.clarity = window.clarity || function () { (window.clarity.q = window.clarity.q || []).push(arguments); };
    // Official Microsoft ConsentV2 API. Advertising remains denied.
    clarityCall('consentv2', {ad_Storage:'denied', analytics_Storage:'granted'});
    clarityCall('set','environment',['dev','prod','staging','local'].indexOf(config.environment)>=0 ? config.environment : 'other');
    clarityReference();
    var sdk = document.createElement('script'); sdk.async = true; sdk.id = 'mc-clarity-sdk';
    sdk.src = 'https://www.clarity.ms/tag/z4upnrbddu'; sdk.referrerPolicy = 'no-referrer';
    sdk.onload = function () { if(active)clarityReference(); if (!active) { clarityCall('consentv2',{ad_Storage:'denied',analytics_Storage:'denied'}); clarityCall('stop'); } };
    document.head.appendChild(sdk);
  }
  function posthogAllowed() {
    var p = config && config.posthog;
    if (!p || p.enabled !== true || typeof p.project_token !== 'string' || !p.project_token || typeof p.api_host !== 'string') return false;
    try { var host = new URL(p.api_host); return host.protocol === 'https:' && !host.username && !host.password && !host.search && !host.hash && (host.pathname === '/' || host.pathname === '') && ['eu.i.posthog.com','us.i.posthog.com'].indexOf(host.hostname) >= 0; } catch (_) { return false; }
  }
  function publicProperties(properties) {
    var clean = {environment:['dev','prod','staging','local'].indexOf(config.environment)>=0 ? config.environment : 'other', scene:SCENES.concat(['other']).indexOf(properties.scene)>=0 ? properties.scene : scene()};
    if (Number.isInteger(properties.duration_ms)) clean.duration_ms = Math.max(0,Math.min(3600000,properties.duration_ms));
    if (Number.isInteger(properties.source_count)) clean.source_count = Math.max(0,Math.min(1000,properties.source_count));
    if (ERRORS.indexOf(properties.error_code)>=0) clean.error_code=properties.error_code;
    if (['helpful','neutral','unhelpful'].indexOf(properties.rating)>=0) clean.rating=properties.rating;
    if (['answer','usability','bug','other'].indexOf(properties.category)>=0) clean.category=properties.category;
    return clean;
  }
  function beforePosthogSend(captured) {
    if (!permitted() || !posthogAllowed() || !captured || NAMES.indexOf(captured.event)<0) return null;
    var original = captured.properties || {}, clean = publicProperties(original);
    // Keep ingestion credentials and this SDK's separate page-memory identity only.
    clean.token = config.posthog.project_token; clean.distinct_id = phIdentity;
    clean.$lib='web';
    if (/^[0-9]+\.[0-9]+\.[0-9]+(?:[-.][a-zA-Z0-9]+)*$/.test(original.$lib_version || '')) clean.$lib_version=original.$lib_version;
    clean.$process_person_profile=false; clean.$is_identified=false;
    if (typeof captured.uuid!=='string' || !/^[0-9a-f-]{36}$/i.test(captured.uuid)) return null;
    var result={uuid:captured.uuid,event:captured.event,properties:clean};
    if(captured.timestamp instanceof Date && isFinite(captured.timestamp.getTime()))result.timestamp=captured.timestamp;
    return result;
  }
  function posthogEvent(name, properties) {
    if (!permitted() || !posthogAllowed() || NAMES.indexOf(name)<0) return;
    var entry={name:name,properties:publicProperties(properties)};
    if (ph && phInitialized) { try { ph.capture(entry.name,entry.properties,{send_instantly:true}); } catch (_) {} }
    else if (phLoading) { phQueue.push(entry); if(phQueue.length>100)phQueue.shift(); }
  }
  function loadPosthog() {
    if (!permitted() || !posthogAllowed() || phLoading || phInitialized || !safeURL()) return;
    phLoading=true;var current=generation,script=document.createElement('script');script.id='mc-posthog-sdk';script.async=true;script.src='/app/vendor/posthog/posthog.js';script.referrerPolicy='no-referrer';
    script.onerror=function(){phLoading=false;phQueue=[];};
    script.onload=function(){
      phLoading=false;if(!permitted() || current!==generation){phQueue=[];return;}
      if(!window.posthog || typeof window.posthog.init!=='function'){phQueue=[];return;}
      phIdentity=uuid();if(!phIdentity){phQueue=[];return;}
      try {
        phInitialized=true;
        ph=window.posthog.init(config.posthog.project_token,{
          api_host:config.posthog.api_host,defaults:'2026-08-30',persistence:'memory',person_profiles:'never',
          bootstrap:{distinctID:phIdentity,isIdentifiedID:false},autocapture:false,capture_pageview:false,capture_pageleave:false,
          disable_session_recording:true,disable_surveys:true,disable_conversations:true,disable_product_tours:true,
          capture_performance:false,capture_exceptions:false,capture_dead_clicks:false,capture_heatmaps:false,capture_webmcp:false,
          advanced_disable_flags:true,disable_external_dependency_loading:true,request_batching:false,
          before_send:beforePosthogSend
        }) || window.posthog;
        if(!permitted() || current!==generation){ph.opt_out_capturing({clear_persistence:true});phQueue=[];return;}
        var pending=phQueue;phQueue=[];pending.forEach(function(item){if(permitted())posthogEvent(item.name,item.properties);});
      } catch(_){ph=null;phQueue=[];}
    };
    document.head.appendChild(script);
  }
  function start(action) {
    if(starting || active)return;
    starting=true;
    // A duplicated tab may inherit sessionStorage. Claim the session exclusively
    // before capture so its new owner can never inherit another tester's name.
    var candidate=read(CONSENT_KEY)===VERSION+':yes'?read(SESSION_KEY):null;
    if(!validUUID(candidate))candidate=uuid();
    function fresh(){[SESSION_KEY,JOURNEY_KEY,CHAT_MAP,CHAT_KEY].forEach(function(key){save(key,null);});}
    if(navigator.locks && candidate){
      navigator.locks.request('mc-research-tab:'+candidate,{ifAvailable:true},function(lock){
        if(!lock){fresh();starting=false;start(action);return;}
        save(SESSION_KEY,candidate);save(CONSENT_KEY,VERSION+':yes');
        begin(action);starting=false;
        return new Promise(function(){}); // Browser releases this on document teardown.
      }).catch(function(){fresh();starting=false;begin(action);});
    }else{fresh();starting=false;begin(action);}
  }
  function begin(action) {
    if (!config || config.environment!=='prod' || config.enabled !== true || internalBrowser() || active) return;
    if (needsReload || read(PENDING_KEY)) { speak('Finish deleting this session before joining another test.'); return; }
    var previous = read(CONSENT_KEY)===VERSION+':yes' ? read(SESSION_KEY) : null; session = validUUID(previous) ? previous : uuid();
    if (!session) { speak('Testing is unavailable in this browser. The platform still works normally.'); return; }
    chatConsent=demoMode ? true : action ? !!panel.querySelector('[data-research-chat]').checked : read(CHAT_KEY)===VERSION+':yes';
    save(CHAT_KEY,chatConsent?VERSION+':yes':null);
    try{conversations=JSON.parse(read(CHAT_MAP)||'{}');}catch(_){conversations={};}
    var stored=null;try{stored=JSON.parse(read(JOURNEY_KEY)||'null');}catch(_){}
    if(previous&&stored&&stored.session===session&&validUUID(stored.user_ref)&&stored.user_ref!==session&&(!chatConsent||(validUUID(stored.clarity_ref)&&stored.clarity_ref!==session&&stored.clarity_ref!==stored.user_ref))){journey=stored;}
    else{journey={session:session,user_ref:uuid(),clarity_ref:chatConsent?uuid():null,started_at:Date.now(),tester_label:chatConsent&&action&&!demoMode?panel.querySelector('[data-research-label]').value.trim().slice(0,80):null};}
    if(!chatConsent){journey.clarity_ref=null;journey.tester_label=null;}
    if(!validUUID(journey.user_ref)){journey=null;speak('Testing is unavailable in this browser.');return;}
    var age=Date.now()-Number(journey.started_at);journeyBaseline=Number.isFinite(age)?Math.max(0,Math.min(86400000,age)):0;journeyPerformance=performance.now();save(JOURNEY_KEY,JSON.stringify(journey));
    active = true; generation++; save(SESSION_KEY, session); save(CONSENT_KEY, VERSION + ':yes');
    loadClarity(); loadPosthog(); event('session.started'); event('scene.viewed'); renderState();
    speak(demoMode ? 'Demo testing is active. New Oracle conversations are saved privately for review.' : 'Optional testing is on for this tab. You can stop at any time.');
    welcomeTester();
  }
  function welcomeTester(){
    if(!demoMode || !permitted() || !journey || journey.tester_label || (location.hash && scene()!=='oracle'))return;
    if(welcome){if(!welcome.open)welcome.showModal();return;}
    var css=document.createElement('style');
    css.textContent='#mcTesterWelcome{box-sizing:border-box;width:min(400px,calc(100vw - 32px));padding:32px;border:1px solid #ded5c5;border-radius:24px;background:#fbf7ee;color:#223b38;font:16px/1.5 var(--round,system-ui);text-align:center;box-shadow:0 24px 80px #143e3826}#mcTesterWelcome::backdrop{background:#173b3840}#mcTesterWelcome img{width:176px;max-width:100%;height:auto;image-rendering:pixelated}#mcTesterWelcome h2{font-size:25px;margin:16px 0 24px}#mcTesterWelcome input{box-sizing:border-box;width:100%;padding:13px 15px;border:1px solid #b7c9c2;border-radius:12px;background:white;color:#223b38;font:inherit}#mcTesterWelcome input:focus-visible,#mcTesterWelcome button:focus-visible{outline:3px solid #65b9b2;outline-offset:3px}#mcTesterWelcome button{width:100%;margin-top:14px;padding:13px;border:0;border-radius:12px;background:#00736e;color:white;font:inherit;cursor:pointer}#mcTesterWelcome button:disabled{opacity:.65;cursor:wait}#mcTesterWelcome [role=status]{margin:12px 0 0;font-size:13px}';
    document.head.appendChild(css);
    welcome=document.createElement('dialog');welcome.id='mcTesterWelcome';welcome.setAttribute('aria-labelledby','mcTesterTitle');welcome.setAttribute('data-clarity-mask','true');
    welcome.innerHTML='<img src="/app/assets/soft-welcome.png" alt="Soft, the MeatCODE character"><h2 id="mcTesterTitle">What’s your name?</h2><form><input name="testerName" aria-label="Your name" placeholder="Your name" autocomplete="off" maxlength="80" required><button type="submit">Continue</button><p role="status" aria-live="polite"></p></form>';
    welcome.addEventListener('cancel',function(e){e.preventDefault();});
    welcome.querySelector('form').addEventListener('submit',function(e){
      e.preventDefault();if(!permitted()||!journey)return;
      var form=e.target,input=form.elements.testerName,name=input.value.trim(),button=form.querySelector('button'),message=form.querySelector('[role=status]');
      if(!name || /[\x00-\x1f]/.test(name)){message.textContent='Please enter your name.';input.focus();return;}
      var sid=session,current=generation,controller=new AbortController(),timeout=setTimeout(function(){controller.abort();},10000);
      var body=journeyFields({session_id:sid,consent:true,consent_version:VERSION});body.tester_label=name;
      button.disabled=true;input.disabled=true;message.textContent='Saving…';requests.add(controller);
      post('name',body,controller.signal).then(function(res){return res.json();}).then(function(result){
        if(!result || result.ok!==true)throw new Error('NAME_NOT_SAVED');
        if(current!==generation || session!==sid || !permitted())return;
        journey.tester_label=name;save(JOURNEY_KEY,JSON.stringify(journey));welcome.close();
      }).catch(function(){message.textContent='Your name could not be saved. Please try again.';}).finally(function(){
        clearTimeout(timeout);requests.delete(controller);button.disabled=false;input.disabled=false;
      });
    });
    document.body.appendChild(welcome);welcome.showModal();welcome.querySelector('input').focus();
  }
  function stop(options) {
    if(welcome){welcome.close();welcome.remove();welcome=null;}
    var sid = session || read(PENDING_KEY) || read(SESSION_KEY);
    active = false; chatConsent=false;conversations={};journey=null;save(JOURNEY_KEY,null);save(CHAT_KEY,null);save(CHAT_MAP,null);generation++; queue = []; phQueue = [];
    if(ph){try{ph.opt_out_capturing({clear_persistence:true});}catch(_){}}
    var phScript=document.getElementById('mc-posthog-sdk');if(phScript)phScript.remove();
    if (timer) clearTimeout(timer); timer = null;
    requests.forEach(function (controller) { controller.abort(); }); requests.clear();
    session = null; save(SESSION_KEY, null); save(CONSENT_KEY, VERSION + ':no');
    needsReload = loaded || phInitialized;
    if (loaded) {
      clarityCall('consentv2',{ad_Storage:'denied',analytics_Storage:'denied'});
      clarityCall('stop');
      var sdk = document.getElementById('mc-clarity-sdk'); if (sdk) sdk.remove();
    }
    if(config&&config.environment!=='prod'){save(PENDING_KEY,null);renderState();speak('Collection is disabled on this site. Local testing preferences were cleared; older server data requires an administrator.');return Promise.resolve();}
    if (validUUID(sid)) save(PENDING_KEY, sid);
    renderState();
    if (!validUUID(sid)) { speak('Testing is off.'); return Promise.resolve(); }
    speak('Testing stopped. Deleting this tab’s first-party testing data…');
    return post('withdraw', {session_id:sid}).then(function () {
      save(PENDING_KEY, null); renderState();
      speak('First-party testing data deleted. Microsoft recordings are managed separately in Clarity.');
      // ConsentV2 denied alone permits cookieless collection. A reload unloads the SDK completely.
      if (needsReload && (!options || options.reload!==false)) location.reload();
    }).catch(function () {
      speak('Testing is off, but deletion could not finish. Use “Stop testing & delete session data” again to retry.');
    });
  }
  function excludeCurrentTab(){if(internalStopping)return Promise.resolve();internalStopping=true;return stop({reload:false}).then(function(){location.reload();});}
  window.addEventListener('storage',function(e){if(e.key===INTERNAL_KEY&&e.newValue==='1'&&config&&config.environment==='prod')excludeCurrentTab();});
  function setInternal(excluded){
    try{if(excluded)localStorage.setItem(INTERNAL_KEY,'1');else localStorage.removeItem(INTERNAL_KEY);}catch(_){}
    document.cookie='__Host-mc_research_internal='+(excluded?'1':'')+'; Path=/; Secure; SameSite=Strict; Max-Age='+(excluded?'31536000':'0');
    var control=panel&&panel.querySelector('[data-research-internal]');if(control)control.disabled=true;
    if(excluded){
      speak('This browser is now excluded. Stopping collection and removing this tab’s first-party testing data…');
      return excludeCurrentTab();
    }
    // Unchecking is an explicit request to resume normal production testing.
    // Optional-consent sites show their choice again; demo sites resume after reload.
    if(read(CONSENT_KEY)===VERSION+':no')save(CONSENT_KEY,null);
    speak('Browser exclusion removed. Reloading to apply this site’s testing settings…');location.reload();
  }
  function chatPrefix(text,limit){var value=text.slice(0,limit);return /[\uD800-\uDBFF]$/.test(value)?value.slice(0,-1):value;}
  function putChat(turn,state,code) {
    if(!current(turn) || !turn.chat || !chatConsent)return;
    var body={session_id:session,consent:true,consent_version:VERSION,full_chat_consent:true,
      turn_id:turn.id,conversation_id:turn.conversation,turn_index:turn.index,question:turn.question,
      answer:turn.answer,status:state,revision:turn.revision++,source_ids:turn.source_ids,truncated:turn.truncated,elapsed_ms:turn.elapsed_ms};
    journeyFields(body);
    if(code)body.error_code=ERRORS.indexOf(code)>=0?code:'unknown';
    var controller=new AbortController();requests.add(controller);
    post('chat',body,controller.signal).catch(function(){if(permitted())speak('The Oracle still works, but a chat-research update could not be saved.');}).finally(function(){requests.delete(controller);});
    turn.lastWrite=performance.now();
  }
  function startOracle(question,chatKey) {
    if (!permitted()) return null;
    event('oracle.submitted');
    var turn={generation:generation, started:performance.now(), finished:false, source_count:0};
    if(chatConsent && typeof question==='string' && question.length){
      var key=String(chatKey||'active');var conversation=conversations[key];
      if(!conversation || !validUUID(conversation.id))conversation=conversations[key]={id:uuid(),next:1};
      if(validUUID(conversation.id)){
        turn.chat=true;turn.elapsed_ms=elapsed();turn.id=uuid();turn.conversation=conversation.id;turn.index=conversation.next++;
        turn.question=chatPrefix(question,12000);turn.answer='';turn.source_ids=[];turn.revision=0;turn.truncated=question.length>12000;
        save(CHAT_MAP,JSON.stringify(conversations));putChat(turn,'submitted');
      }
    }
    return turn;
  }
  function current(turn) { return turn && permitted() && turn.generation === generation && !turn.finished; }
  function sourceCount(turn, count, ids) {
    if(current(turn) && Number.isInteger(count))turn.source_count=Math.max(0,Math.min(1000,count));
    if(current(turn) && turn.chat && Array.isArray(ids))turn.source_ids=ids.map(Number).filter(function(x){return Number.isSafeInteger(x)&&x>0;}).slice(0,100);
  }
  function appendOracle(turn,text){
    if(!current(turn)||!turn.chat||typeof text!=='string')return;
    if(turn.answer.length+text.length>64000)turn.truncated=true;
    turn.answer=chatPrefix(turn.answer+text,64000);
    if(performance.now()-turn.lastWrite>=2000)putChat(turn,'submitted');
  }
  function clarifyOracle(turn,raw){
    if(!current(turn)||!turn.chat)return;
    try{var d=JSON.parse(raw);if(typeof d.question!=='string')return;
      turn.clarification=true;turn.answer=d.question+'\nOptions: '+(Array.isArray(d.options)?d.options.filter(function(x){return typeof x==='string';}).slice(0,4).join(' | '):'')+' | Not sure | Just answer';
      if(turn.answer.length>64000){turn.answer=chatPrefix(turn.answer,64000);turn.truncated=true;}
    }catch(_){}
  }
  function finish(turn, code, interrupted) {
    if (!current(turn)) return;
    putChat(turn,interrupted?'interrupted':code?'failed':turn.clarification?'clarification':'complete',code);
    turn.finished = true;turn.question='';turn.answer='';
    var properties = {duration_ms:Math.max(0,Math.min(3600000,Math.round(performance.now()-turn.started)))};
    if (code) properties.error_code = ERRORS.indexOf(code) >= 0 ? code : 'unknown';
    else properties.source_count = turn.source_count;
    event(code ? 'oracle.failed' : 'oracle.completed', properties);
  }
  window.MCResearch = Object.freeze({startOracle:startOracle,sourceCount:sourceCount,appendOracle:appendOracle,clarifyOracle:clarifyOracle,completeOracle:function(t){finish(t);},failOracle:function(t,c){finish(t,c||'unknown');},interruptOracle:function(t){finish(t,'unknown',true);}});
  document.addEventListener('click',function(e){
    if(!permitted()||!e.isTrusted||!e.target||!e.target.closest)return;
    var control=e.target.closest('a[href^="#"],a[href="/app/dev/index.html"],.domains .domain,#invBtn,.mc-toolbench-btn'),target=null;
    if(!control||control.hidden||control.getAttribute('aria-disabled')==='true'||control.getClientRects().length===0)return;
    if(control.id==='invBtn'||control.classList.contains('mc-toolbench-btn'))target='inventory';
    else if(control.hasAttribute('data-mod-chip'))target=control.getAttribute('data-mod-chip');
    else if(control.hasAttribute('data-analytics-chip'))target='analytics';
    else if(control.classList.contains('domain')){target={Oracle:'oracle',Science:'science',Ecosystem:'ecosystem',Research:'research',Simulate:'simulate',Analytics:'analytics',Database:'database',Map:'map',Papers:'papers'}[(control.textContent||'').trim()]||null;}
    else{var href=control.getAttribute('href');if(href==='/app/dev/index.html')target='dev';else if(href&&/^#[a-z]+$/.test(href))target=href.slice(1);}
    if(SCENES.indexOf(target)>=0)event('module.clicked',{}, {},target);
  },true);
  window.addEventListener('hashchange', function () {
    welcomeTester();
    if (!permitted()) return;
    if (loaded && !safeURL()) { clarityCall('consentv2',{ad_Storage:'denied',analytics_Storage:'denied'}); clarityCall('stop'); needsReload = true; }
    event('scene.viewed');
  });
  function renderState() {
    if (!panel) return;
    var excluded=config&&config.capture_excluded;var internal=panel.querySelector('[data-research-internal]');if(internal){internal.checked=internalBrowser()||excluded==='internal';internal.disabled=excluded==='nonproduction';}
    var exclusionStatus=panel.querySelector('[data-research-exclusion-status]');if(exclusionStatus)exclusionStatus.textContent=excluded==='nonproduction'?'Only the production platform is collected. This development/local site sends no testing events or recordings.':excluded==='internal'||internalBrowser()?'This browser is excluded from production research and Clarity/PostHog collection. Uncheck to resume normal testing settings.':'Use internal testing for your own checks. It excludes this browser without changing normal platform access.';
    if(demoMode){var demoButton=document.getElementById('mcResearchButton');if(demoButton){demoButton.textContent='Demo testing';demoButton.disabled=true;demoButton.removeAttribute('aria-haspopup');demoButton.style.cursor='default';}}
    var demoNotice=document.getElementById('mcDemoNotice');
    if(demoNotice){demoNotice.hidden=!!active;if(read(CONSENT_KEY)===VERSION+':no')demoNotice.textContent='Demo testing has stopped for this tab.';}
    consentSection.hidden = !demoMode && active;
    feedbackSection.hidden = !active;
    var chatStatus=panel.querySelector('[data-chat-status]');if(chatStatus)chatStatus.textContent=chatConsent?'Full Oracle chat sharing is ON for new turns in this tab.':'Full Oracle chat sharing is OFF.';
    panel.querySelector('[data-research-stop]').hidden = !active && !read(PENDING_KEY) && !validUUID(read(SESSION_KEY));
    if(!demoMode)panel.querySelector('[data-research-accept]').disabled = !config || config.enabled !== true || needsReload || !!read(PENDING_KEY);
  }
  function ui() {
    var style = document.createElement('style');
    style.textContent = '#mcResearchButton{position:fixed;right:14px;bottom:12px;z-index:2100;padding:7px 11px;border:1px solid var(--line,#ddd);border-radius:100px;background:var(--surface,#fff);color:var(--ink-dim,#444);font:11px var(--round,system-ui);cursor:pointer}#mcResearchPanel{width:min(430px,calc(100vw - 32px));max-height:85vh;overflow:auto;padding:24px;border:1px solid var(--line,#ddd);border-radius:18px;background:var(--surface,#fff);color:var(--ink,#222);font:14px/1.5 var(--round,system-ui);box-shadow:var(--shadow-lg)}#mcResearchPanel::backdrop{background:rgba(0,30,28,.25)}#mcResearchPanel h2{margin:0 0 12px;font-size:20px}#mcResearchPanel p{font-size:13px}#mcResearchPanel label{display:block;margin:10px 0}#mcResearchPanel select,#mcResearchPanel textarea{display:block;width:100%;font:inherit;color:inherit;border:1px solid var(--line,#ddd);border-radius:8px;padding:9px;background:var(--surface,#fff)}#mcResearchPanel textarea{min-height:82px}#mcResearchPanel button{font:inherit;padding:8px 11px;margin:5px 5px 5px 0;border:1px solid var(--line,#ddd);border-radius:9px;background:var(--surface-2,#eee);color:inherit;cursor:pointer}#mcResearchPanel [data-research-accept],#mcResearchPanel [type=submit]{background:var(--wine,#00736e);color:white}#mcResearchPanel [hidden]{display:none!important}#mcResearchStatus{font-size:12px;color:var(--ink-dim,#555)}';
    document.head.appendChild(style);
    // Owner-directed demo UI: a passive label, with no feedback/session settings controls.
    // Existing internal-cookie exclusions and automatic capture are independent of this UI.
    if(demoMode || (config && config.capture_excluded)){
      var indicator=document.createElement('span');indicator.id='mcResearchButton';indicator.textContent='Demo testing';
      indicator.setAttribute('role','status');indicator.style.cssText='cursor:default;pointer-events:none';
      indicator.title=config&&config.capture_excluded?'Testing collection is excluded for this browser or environment.':'Demo testing starts automatically after login.';
      document.body.appendChild(indicator);return;
    }
    var button = document.createElement('button'); button.id = 'mcResearchButton'; button.type = 'button'; button.textContent = 'Testing privacy'; button.setAttribute('aria-haspopup','dialog');
    document.body.appendChild(button);
    panel = document.createElement('dialog'); panel.id = 'mcResearchPanel'; panel.setAttribute('aria-labelledby','mcResearchTitle'); panel.setAttribute('data-clarity-mask','true');
    panel.innerHTML = '<h2 id="mcResearchTitle">Help improve MeatCODE</h2><section data-research-consent><p>Optional testing records navigation, response timing and success or failure in MeatCODE and, when configured, PostHog. PostHog receives explicit events with a temporary page identity; no recordings or account identity. Microsoft Clarity provides masked interactions and analytics cookies; advertising storage stays off. MeatCODE also records clicks on supported module links and time elapsed since joining testing, using a random tab pseudonym. Questions, answers, attachments and profile text are masked.</p><p>MeatCODE has a 90-day testing-data retention policy. You can stop and request deletion of this tab’s testing data below. Microsoft recordings follow the project’s separate Clarity retention settings.</p><label><input type="checkbox" data-research-chat> Also share my submitted Oracle questions, answers, clarification choices, citations and journey timing with MeatCODE researchers, linked to my masked Clarity session by a random research reference.</label><label>Tester nickname or code (optional; not your email)<input type="text" maxlength="80" data-research-label autocomplete="off" spellcheck="false"></label><p>The nickname stays in MeatCODE only. Only the random research reference is sent to Clarity; no question, answer, nickname or account details are sent. This optional full-chat history is stored privately in Neon under MeatCODE’s 90-day testing-data policy, not sent to Clarity or PostHog. Earlier chats, unsent text, attachment contents and account details are not imported. Avoid confidential or personal information. Stop testing deletes this tab’s first-party research data.</p><button type="button" data-research-accept>Allow optional testing</button><button type="button" data-research-decline>Continue without testing</button></section><section data-research-feedback hidden><p data-chat-status></p><form><label>How was this experience?<select name="rating" required><option value="" selected disabled>Choose one</option><option value="helpful">Helpful</option><option value="neutral">Neutral</option><option value="unhelpful">Unhelpful</option></select></label><label>About<select name="category"><option value="answer">Oracle answer</option><option value="usability">Using the platform</option><option value="bug">A problem or bug</option><option value="other">Other</option></select></label><label>Comment (optional)<textarea name="comment" maxlength="2000" placeholder="Please leave out names, contact details and confidential research."></textarea></label><p>Submitted feedback comments go to MeatCODE’s own database. Full chat text is included there only if you selected the separate chat-sharing option. It is never sent to Clarity or PostHog. Only the selected rating and category may be included in PostHog feedback events.</p><button type="submit">Send feedback</button></form></section><section data-research-exclusion><label><input type="checkbox" data-research-internal> Internal testing: exclude this browser</label><p data-research-exclusion-status></p></section><button type="button" data-research-stop hidden>Stop testing &amp; delete session data</button><p id="mcResearchStatus" role="status" aria-live="polite"></p><button type="button" data-research-close>Close</button>';
    document.body.appendChild(panel);
    consentSection = panel.querySelector('[data-research-consent]'); feedbackSection = panel.querySelector('[data-research-feedback]'); status = panel.querySelector('#mcResearchStatus');
    if(demoMode){
      button.textContent='Demo testing';button.disabled=true;button.style.cursor='default';button.removeAttribute('aria-haspopup');
      var notice=document.createElement('aside');notice.id='mcDemoNotice';notice.setAttribute('role','note');
      notice.style.cssText='position:fixed;left:16px;bottom:12px;max-width:min(560px,calc(100vw - 32px));z-index:2090;padding:8px 12px;border-radius:12px;background:var(--surface,#fff);color:var(--ink,#222);border:1px solid var(--line,#ddd);font:12px/1.4 var(--round,system-ui)';
      notice.textContent='Demo testing: after login, MeatCODE records usage and saves new Oracle questions and answers privately for review (90 days). Avoid confidential information.';
      // Stack the details control above the notice without covering the input controls.
      notice.style.position='relative';notice.style.left='auto';notice.style.bottom='auto';notice.style.maxWidth='560px';
      var bar=document.createElement('div');bar.id='mcDemoTestingBar';bar.style.cssText='position:fixed;right:14px;bottom:12px;left:14px;z-index:2100;display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:8px;pointer-events:none';
      notice.style.pointerEvents='auto';button.style.cssText='position:static;flex:none;pointer-events:auto';bar.appendChild(notice);bar.appendChild(button);document.body.appendChild(bar);
      panel.querySelector('#mcResearchTitle').textContent='Demo testing & feedback';
      consentSection.innerHTML='<p>Demo testing starts automatically after login. Usage and newly submitted Oracle questions, answers, clarification choices and citations are saved privately in MeatCODE for 90 days. Masked interactions may be recorded by Microsoft Clarity; PostHog receives usage events. Oracle text is not sent to either provider. Earlier chats, unsent text, attachment contents and account details are excluded.</p><p>Microsoft recordings follow the Clarity project’s separate retention settings. You can delete this tab’s first-party testing data below.</p>';
      var description=feedbackSection.querySelector('form p');description.textContent='Feedback and new Oracle conversations are stored privately in MeatCODE. Chat text is not sent to Clarity or PostHog.';
    }
    button.addEventListener('click',function(){if(!demoMode){renderState();panel.showModal();}});
    panel.querySelector('[data-research-close]').addEventListener('click',function(){panel.close();});
    if(!demoMode)panel.querySelector('[data-research-decline]').addEventListener('click',function(){save(CONSENT_KEY,VERSION+':no');panel.close();});
    if(!demoMode)panel.querySelector('[data-research-accept]').addEventListener('click',start);
    panel.querySelector('[data-research-stop]').addEventListener('click',stop);
    panel.querySelector('[data-research-internal]').addEventListener('change',function(){setInternal(this.checked);});
    panel.querySelector('form').addEventListener('submit',function(e){
      e.preventDefault(); if(!permitted())return;
      var form=e.target, submit=form.querySelector('[type=submit]'), sid=session, current=generation, id=uuid(); if(!id)return;
      var payload={session_id:sid,event_id:id,consent:true,consent_version:VERSION,rating:form.elements.rating.value,category:form.elements.category.value,comment:form.elements.comment.value.slice(0,2000),elapsed_ms:elapsed()};journeyFields(payload);
      submit.disabled=true;
      var controller=new AbortController();requests.add(controller);
      post('feedback',payload,controller.signal).then(function(){
        if(current!==generation || !permitted())return;
        form.elements.comment.value='';event('feedback.submitted', {}, {rating:payload.rating,category:payload.category});speak('Thank you. Your feedback was saved to MeatCODE.');
      }).catch(function(){if(current===generation && permitted())speak('Feedback could not be saved. Please try again.');}).finally(function(){requests.delete(controller);submit.disabled=false;});
    });
    renderState();
  }
  nativeFetch('/api/research/config',{credentials:'same-origin',cache:'no-store',referrerPolicy:'no-referrer'}).then(function(res){if(!res.ok)throw new Error('disabled');return res.json();}).then(function(value){
    if(!value || ['2026-10-29-journey-v1','2026-10-29-demo-v1'].indexOf(value.consent_version)<0)return;
    if(value.environment!=='prod'){value.enabled=false;value.demo_mode=false;value.capture_excluded='nonproduction';}
    else if(internalBrowser()){value.enabled=false;value.demo_mode=false;value.capture_excluded='internal';}
    config=value;demoMode=value.demo_mode===true;VERSION=value.consent_version;
    if(value.enabled!==true && !value.capture_excluded && !read(PENDING_KEY) && !validUUID(read(SESSION_KEY)))return;
    ui();
    if(read(PENDING_KEY)){renderState();speak('A previous deletion needs to be retried. Testing remains off.');return;}
    if(value.enabled!==true){speak(value.capture_excluded==='internal'?'Internal testing is on: this browser is not collected. Uncheck the internal-testing control to resume normal testing.':value.capture_excluded==='nonproduction'?'Testing collection is disabled outside the production platform.':'Testing is currently disabled. You can still delete this tab’s earlier testing data.');return;}
    // This same-origin config is behind the site's existing login gate.
    if(demoMode){if(read(CONSENT_KEY)!==VERSION+':no')start();}
    else if(read(CONSENT_KEY)===VERSION+':yes')start();
    else if(read(CONSENT_KEY)!==VERSION+':no')panel.showModal();
  }).catch(function(){
    // Keep first-party deletion reachable even if collection is disabled or config is unavailable.
    if((read(PENDING_KEY) || validUUID(read(SESSION_KEY))) && !panel){config={enabled:false};ui();speak('Testing is off. Retry deleting the previous session below.');}
  });
})();

