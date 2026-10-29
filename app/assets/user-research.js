/* Last updated: 2026-10-29 · Codex UI/UX · renewed provider consent, explicit PostHog events and private live-testing support. */
(function () {
  'use strict';
  if (window.MCResearch) return;
  var VERSION = '2026-10-29', CONSENT_KEY = 'mc_research_consent_v1', SESSION_KEY = 'mc_research_session_v1';
  var PENDING_KEY = 'mc_research_withdraw_pending_v1';
  var SCENES = ['oracle','research','science','ecosystem','simulate','analytics','database','map','papers','dev'];
  var ERRORS = ['network','model_unavailable','session_expired','unknown'];
  var config = null, active = false, session = null, queue = [], timer = null, sending = false;
  var generation = 0, loaded = false, needsReload = false, requests = new Set(), panel, status, consentSection, feedbackSection;
  var ph = null, phLoading = false, phInitialized = false, phQueue = [], phIdentity = null;
  var NAMES = ['session.started','scene.viewed','oracle.submitted','oracle.completed','oracle.failed','feedback.submitted'];
  var nativeFetch = window.fetch.bind(window);
  document.body.setAttribute('data-clarity-mask', 'true');
  function read(key) { try { return sessionStorage.getItem(key); } catch (_) { return null; } }
  function save(key, value) { try { if (value === null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, value); } catch (_) {} }
  function uuid() { return window.crypto && typeof window.crypto.randomUUID === 'function' ? window.crypto.randomUUID() : null; }
  function validUUID(value) { return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value || ''); }
  function scene() { var value = location.hash.replace(/^#/, ''); return SCENES.indexOf(value) >= 0 ? value : 'other'; }
  function permitted() { return active && config && config.enabled === true && session; }
  function speak(text) { if (status) status.textContent = text; }
  function post(path, body, signal) {
    return nativeFetch('/api/research/' + path, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-MeatCODE-Research':'1'}, body:JSON.stringify(body), referrerPolicy:'no-referrer', signal:signal}).then(function (res) {
      if (!res.ok) throw new Error('RESEARCH_REQUEST_FAILED');
      return res;
    });
  }
  function event(name, properties, providerProperties) {
    if (!permitted()) return;
    var id = uuid(); if (!id) return;
    // Callers receive no generic logger: only these allow-listed lifecycle methods reach here.
    queue.push({event_id:id, name:name, scene:scene(), properties:properties || {}});
    if (loaded && safeURL()) { clarityCall('set','scene',scene()); clarityCall('event',name); }
    posthogEvent(name, providerProperties || properties || {});
    if (queue.length > 100) queue.shift();
    if (!timer) timer = setTimeout(flush, 200);
  }
  function flush() {
    timer = null;
    if (!permitted() || sending || !queue.length) return;
    var batch = queue.splice(0,20), sid = session, current = generation, controller = new AbortController();
    sending = true;
    var request = post('events', {session_id:sid, consent:true, consent_version:VERSION, events:batch}, controller.signal);
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
    var sdk = document.createElement('script'); sdk.async = true; sdk.id = 'mc-clarity-sdk';
    sdk.src = 'https://www.clarity.ms/tag/z4upnrbddu'; sdk.referrerPolicy = 'no-referrer';
    sdk.onload = function () { if (!active) { clarityCall('consentv2',{ad_Storage:'denied',analytics_Storage:'denied'}); clarityCall('stop'); } };
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
  function start() {
    if (!config || config.enabled !== true || active) return;
    if (needsReload || read(PENDING_KEY)) { speak('Finish deleting this session before joining another test.'); return; }
    var previous = read(CONSENT_KEY)===VERSION+':yes' ? read(SESSION_KEY) : null; session = validUUID(previous) ? previous : uuid();
    if (!session) { speak('Testing is unavailable in this browser. The platform still works normally.'); return; }
    active = true; generation++; save(SESSION_KEY, session); save(CONSENT_KEY, VERSION + ':yes');
    loadClarity(); loadPosthog(); event('session.started'); event('scene.viewed'); renderState();
    speak('Optional testing is on for this tab. You can stop at any time.');
  }
  function stop() {
    var sid = session || read(PENDING_KEY) || read(SESSION_KEY);
    active = false; generation++; queue = []; phQueue = [];
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
    if (validUUID(sid)) save(PENDING_KEY, sid);
    renderState();
    if (!validUUID(sid)) { speak('Testing is off.'); return Promise.resolve(); }
    speak('Testing stopped. Deleting this tab’s first-party testing data…');
    return post('withdraw', {session_id:sid}).then(function () {
      save(PENDING_KEY, null); renderState();
      speak('First-party testing data deleted. Microsoft recordings are managed separately in Clarity.');
      // ConsentV2 denied alone permits cookieless collection. A reload unloads the SDK completely.
      if (needsReload) location.reload();
    }).catch(function () {
      speak('Testing is off, but deletion could not finish. Use “Stop testing & delete session data” again to retry.');
    });
  }
  function startOracle() {
    if (!permitted()) return null;
    event('oracle.submitted');
    return {generation:generation, started:performance.now(), finished:false, source_count:0};
  }
  function current(turn) { return turn && permitted() && turn.generation === generation && !turn.finished; }
  function sourceCount(turn, count) { if (current(turn) && Number.isInteger(count)) turn.source_count = Math.max(0,Math.min(1000,count)); }
  function finish(turn, code) {
    if (!current(turn)) return;
    turn.finished = true;
    var properties = {duration_ms:Math.max(0,Math.min(3600000,Math.round(performance.now()-turn.started)))};
    if (code) properties.error_code = ERRORS.indexOf(code) >= 0 ? code : 'unknown';
    else properties.source_count = turn.source_count;
    event(code ? 'oracle.failed' : 'oracle.completed', properties);
  }
  window.MCResearch = Object.freeze({startOracle:startOracle, sourceCount:sourceCount, completeOracle:function(t){finish(t);}, failOracle:function(t,c){finish(t,c || 'unknown');}});
  window.addEventListener('hashchange', function () {
    if (!permitted()) return;
    if (loaded && !safeURL()) { clarityCall('consentv2',{ad_Storage:'denied',analytics_Storage:'denied'}); clarityCall('stop'); needsReload = true; }
    event('scene.viewed');
  });
  function renderState() {
    if (!panel) return;
    consentSection.hidden = active;
    feedbackSection.hidden = !active;
    panel.querySelector('[data-research-stop]').hidden = !active && !read(PENDING_KEY) && !validUUID(read(SESSION_KEY));
    panel.querySelector('[data-research-accept]').disabled = !config || config.enabled !== true || needsReload || !!read(PENDING_KEY);
  }
  function ui() {
    var style = document.createElement('style');
    style.textContent = '#mcResearchButton{position:fixed;right:14px;bottom:12px;z-index:2100;padding:7px 11px;border:1px solid var(--line,#ddd);border-radius:100px;background:var(--surface,#fff);color:var(--ink-dim,#444);font:11px var(--round,system-ui);cursor:pointer}#mcResearchPanel{width:min(430px,calc(100vw - 32px));max-height:85vh;overflow:auto;padding:24px;border:1px solid var(--line,#ddd);border-radius:18px;background:var(--surface,#fff);color:var(--ink,#222);font:14px/1.5 var(--round,system-ui);box-shadow:var(--shadow-lg)}#mcResearchPanel::backdrop{background:rgba(0,30,28,.25)}#mcResearchPanel h2{margin:0 0 12px;font-size:20px}#mcResearchPanel p{font-size:13px}#mcResearchPanel label{display:block;margin:10px 0}#mcResearchPanel select,#mcResearchPanel textarea{display:block;width:100%;font:inherit;color:inherit;border:1px solid var(--line,#ddd);border-radius:8px;padding:9px;background:var(--surface,#fff)}#mcResearchPanel textarea{min-height:82px}#mcResearchPanel button{font:inherit;padding:8px 11px;margin:5px 5px 5px 0;border:1px solid var(--line,#ddd);border-radius:9px;background:var(--surface-2,#eee);color:inherit;cursor:pointer}#mcResearchPanel [data-research-accept],#mcResearchPanel [type=submit]{background:var(--wine,#00736e);color:white}#mcResearchPanel [hidden]{display:none!important}#mcResearchStatus{font-size:12px;color:var(--ink-dim,#555)}';
    document.head.appendChild(style);
    var button = document.createElement('button'); button.id = 'mcResearchButton'; button.type = 'button'; button.textContent = 'Testing privacy'; button.setAttribute('aria-haspopup','dialog');
    document.body.appendChild(button);
    panel = document.createElement('dialog'); panel.id = 'mcResearchPanel'; panel.setAttribute('aria-labelledby','mcResearchTitle'); panel.setAttribute('data-clarity-mask','true');
    panel.innerHTML = '<h2 id="mcResearchTitle">Help improve MeatCODE</h2><section data-research-consent><p>Optional testing records navigation, response timing and success or failure in MeatCODE and, when configured, PostHog. PostHog receives explicit events with a temporary page identity; no recordings or account identity. Microsoft Clarity provides masked interactions and analytics cookies; advertising storage stays off. Questions, answers, attachments and profile text are masked.</p><p>MeatCODE has a 90-day testing-data retention policy. You can stop and request deletion of this tab’s testing data below. Microsoft recordings follow the project’s separate Clarity retention settings.</p><button type="button" data-research-accept>Allow optional testing</button><button type="button" data-research-decline>Continue without testing</button></section><section data-research-feedback hidden><form><label>How was this experience?<select name="rating" required><option value="" selected disabled>Choose one</option><option value="helpful">Helpful</option><option value="neutral">Neutral</option><option value="unhelpful">Unhelpful</option></select></label><label>About<select name="category"><option value="answer">Oracle answer</option><option value="usability">Using the platform</option><option value="bug">A problem or bug</option><option value="other">Other</option></select></label><label>Comment (optional)<textarea name="comment" maxlength="2000" placeholder="Please leave out names, contact details and confidential research."></textarea></label><p>Only the comment you submit goes to MeatCODE’s own database. It is never sent to Clarity or PostHog. Only the selected rating and category may be included in PostHog feedback events.</p><button type="submit">Send feedback</button></form></section><button type="button" data-research-stop hidden>Stop testing &amp; delete session data</button><p id="mcResearchStatus" role="status" aria-live="polite"></p><button type="button" data-research-close>Close</button>';
    document.body.appendChild(panel);
    consentSection = panel.querySelector('[data-research-consent]'); feedbackSection = panel.querySelector('[data-research-feedback]'); status = panel.querySelector('#mcResearchStatus');
    button.addEventListener('click',function(){renderState();panel.showModal();});
    panel.querySelector('[data-research-close]').addEventListener('click',function(){panel.close();});
    panel.querySelector('[data-research-decline]').addEventListener('click',function(){save(CONSENT_KEY,VERSION+':no');panel.close();});
    panel.querySelector('[data-research-accept]').addEventListener('click',start);
    panel.querySelector('[data-research-stop]').addEventListener('click',stop);
    panel.querySelector('form').addEventListener('submit',function(e){
      e.preventDefault(); if(!permitted())return;
      var form=e.target, submit=form.querySelector('[type=submit]'), sid=session, current=generation, id=uuid(); if(!id)return;
      var payload={session_id:sid,event_id:id,consent:true,consent_version:VERSION,rating:form.elements.rating.value,category:form.elements.category.value,comment:form.elements.comment.value.slice(0,2000)};
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
    if(!value || value.consent_version!==VERSION)return;
    config=value;
    if(value.enabled!==true && !read(PENDING_KEY) && !validUUID(read(SESSION_KEY)))return;
    ui();
    if(read(PENDING_KEY)){renderState();speak('A previous deletion needs to be retried. Testing remains off.');return;}
    if(value.enabled!==true){speak('Testing is currently disabled. You can still delete this tab’s earlier testing data.');return;}
    if(read(CONSENT_KEY)===VERSION+':yes')start();
    else if(read(CONSENT_KEY)!==VERSION+':no')panel.showModal();
  }).catch(function(){
    // Keep first-party deletion reachable even if collection is disabled or config is unavailable.
    if((read(PENDING_KEY) || validUUID(read(SESSION_KEY))) && !panel){config={enabled:false};ui();speak('Testing is off. Retry deleting the previous session below.');}
  });
})();
