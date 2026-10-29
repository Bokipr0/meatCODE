/* Last updated: 2026-10-29 · Codex UI/UX · browser fixture verifies consent, masking, payload minimization and Oracle terminal outcomes. */
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const SOURCE = process.env.RESEARCH_HTML || 'app/meatcode_mockup.html';
const ROOT = path.resolve(__dirname,'..');
const PRIVATE = 'PRIVATE_QUESTION_AND_ANSWER_9287';
const COMMENT = 'EXPLICIT_FEEDBACK_COMMENT_2859';
(async function(){
 const browser = await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE ? {executablePath:process.env.PLAYWRIGHT_EXECUTABLE}: {})});
 try {
 async function fixture(options={}) {
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
  const records=[],errors=[];let outcome='success',withdrawFails=false;
  page.on('pageerror',e=>errors.push(e.message));
  if(options.oldConsent)await context.addInitScript(()=>sessionStorage.setItem('mc_research_consent_v1','2026-10-28:yes'));
  if(options.pending)await context.addInitScript(()=>sessionStorage.setItem('mc_research_withdraw_pending_v1','910fe0c3-1ef3-4d0b-8f13-39c55f2e4f76'));
  await page.route('**/*',async route=>{
   const req=route.request(),u=new URL(req.url());
   if(u.pathname==='/app/vendor/posthog/posthog.js') {
    records.push({kind:'ph-sdk'});if(options.blockPosthog)return route.abort();
    if(options.delayPosthog)await new Promise(r=>setTimeout(r,options.delayPosthog));
    return route.fulfill({contentType:'application/javascript',body:`window.__phEvents=[];window.posthog={init:function(token,config){window.__phToken=token;window.__phConfig=config;window.__phInitCount=(window.__phInitCount||0)+1;return this},capture:function(name,properties){if(window.__phOptedOut)return;var candidate={uuid:crypto.randomUUID(),event:name,properties:Object.assign({token:window.__phToken,distinct_id:'BAD_ACCOUNT_ID',$current_url:location.href,$referrer:'${PRIVATE}',$user_agent:'${PRIVATE}',$lib:'web',$lib_version:'1.442.0',$set:{email:'${PRIVATE}'}},properties),timestamp:new Date(),$set:{email:'${PRIVATE}'}};var clean=window.__phConfig.before_send(candidate);if(clean)window.__phEvents.push(clean)},opt_out_capturing:function(){window.__phOptedOut=true}};`});
   }
   if(u.hostname==='www.clarity.ms') {
    records.push({kind:'sdk',url:u.href});
    return route.fulfill({contentType:'text/javascript',body:'window.__maskAtSDK = document.body.getAttribute("data-clarity-mask"); window.__clarityCalls=(window.clarity.q||[]).map(function(x){return Array.from(x)}); window.clarity=function(){window.__clarityCalls.push(Array.from(arguments))};'});
   }
   if(u.hostname!=='127.0.0.1')return route.abort();
   if(u.pathname==='/api/research/config')return route.fulfill({contentType:'application/json',body:JSON.stringify({enabled:options.enabled!==false,environment:'dev',clarity_project_id:options.noClarity?'':'z4upnrbddu',posthog:options.noPosthog?{enabled:false}:{enabled:true,project_token:'phc_fixture_public',api_host:'https://eu.i.posthog.com'},consent_version:'2026-10-29-chat-v1',retention_days:90})});
   if(u.pathname.startsWith('/api/research/')) {
    records.push({kind:'post',path:u.pathname,body:req.postDataJSON(),headers:req.headers()});
    return route.fulfill({status:u.pathname.endsWith('/withdraw') && withdrawFails ? 503 : 200,contentType:'application/json',body:'{"ok":true}'});
   }
   if(u.pathname==='/api/ask') {
    if(outcome==='network')return route.abort('failed');
    if(outcome==='http401')return route.fulfill({status:401,body:'session expired'});
    const body=outcome==='sse-error' ? 'event: error\ndata: model unavailable '+PRIVATE+'\n\nevent: done\ndata: {}\n\n' : outcome==='missingdone' ? 'event: status\ndata: answering\n\n' : 'event: sources\ndata: [{"id":1,"title":"'+PRIVATE+'"}]\n\nevent: chunk\ndata: '+PRIVATE+'\n\nevent: done\ndata: {}\n\n';
    return route.fulfill({contentType:'text/event-stream',body});
   }
   if(u.pathname==='/api/flags')return route.fulfill({contentType:'application/json',body:'{}'});
   if(u.pathname.startsWith('/api/'))return route.fulfill({contentType:'application/json',body:'{"ok":true,"rows":[],"totals":{},"phase_topics":[]}'});
   const file=u.pathname==='/'?path.resolve(ROOT,SOURCE):path.join(ROOT,decodeURIComponent(u.pathname));
   if(fs.existsSync(file)&&fs.statSync(file).isFile())return route.fulfill({contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.html')?'text/html':undefined,body:fs.readFileSync(file)});
   return route.fulfill({status:404,body:''});
  });
  await page.goto('http://127.0.0.1:18774/'+(options.query || '')+'#oracle');
  await page.waitForFunction(()=>!!window.MCResearch);
  const events=()=>records.filter(r=>r.path==='/api/research/events').flatMap(r=>r.body.events);
  const ask=async value=>{await page.locator('#oracleTextarea').fill(value);await page.locator('#oracleAskBtn').click();await page.waitForFunction(()=>!document.querySelector('#oracleAskBtn').disabled);await page.waitForTimeout(400);};
  return {page,context,records,errors,events,ask,outcome:value=>{outcome=value;},withdrawFails:value=>{withdrawFails=value;}};
 }
 const f=await fixture();
 await f.page.locator('#mcResearchPanel').waitFor();
 assert.equal(f.records.length,0,'no SDK or research POST before opt-in');
 assert.equal(await f.page.evaluate(()=>window.MCResearch.startOracle()),null);
 await f.page.locator('[data-research-close]').click();
 await f.ask(PRIVATE);
 assert.equal(f.records.length,0,'unconsented Oracle request produces no research events');
 await f.page.locator('#mcResearchButton').click();await f.page.locator('[data-research-accept]').click();
 await f.page.waitForFunction(()=>window.__maskAtSDK==='true');
 assert.equal(await f.page.locator('[data-clarity-unmask]').count(),0);
 assert.equal(await f.page.locator('[name=rating]').inputValue(),'','rating requires explicit selection');
 await f.page.locator('[data-research-close]').click();await f.ask(PRIVATE);
 let completed=f.events().filter(e=>e.name==='oracle.completed');assert.equal(completed.length,1);assert.equal(completed[0].properties.source_count,1);
 f.outcome('sse-error');await f.ask(PRIVATE);assert.equal(f.events().filter(e=>e.name==='oracle.completed').length,1,'SSE error followed by done cannot count success');
 assert.equal(f.events().filter(e=>e.name==='oracle.failed').at(-1).properties.error_code,'model_unavailable');
 f.outcome('http401');await f.ask(PRIVATE);assert.equal(f.events().filter(e=>e.name==='oracle.failed').at(-1).properties.error_code,'session_expired');
 f.outcome('network');await f.ask(PRIVATE);assert.equal(f.events().filter(e=>e.name==='oracle.failed').at(-1).properties.error_code,'network');
 f.outcome('missingdone');await f.ask(PRIVATE);assert.equal(f.events().filter(e=>e.name==='oracle.failed').at(-1).properties.error_code,'unknown');
 await f.page.locator('#mcResearchButton').click();await f.page.locator('[name=rating]').selectOption('helpful');await f.page.locator('[name=comment]').fill(COMMENT);await f.page.locator('#mcResearchPanel [type=submit]').click();await f.page.waitForTimeout(400);
 const feedback=f.records.find(r=>r.path==='/api/research/feedback');assert.equal(feedback.body.comment,COMMENT);assert.equal(feedback.body.consent,true);
 assert(!JSON.stringify(f.events()).includes(PRIVATE));assert(!JSON.stringify(f.events()).includes(COMMENT));
 const ph=await f.page.evaluate(()=>({events:window.__phEvents,initCount:window.__phInitCount,config:{defaults:window.__phConfig.defaults,persistence:window.__phConfig.persistence,profiles:window.__phConfig.person_profiles,autocapture:window.__phConfig.autocapture,pageview:window.__phConfig.capture_pageview,recording:window.__phConfig.disable_session_recording,flags:window.__phConfig.advanced_disable_flags}}));
 assert.equal(ph.initCount,1);assert.equal(ph.config.defaults,'2026-08-30');assert.equal(ph.config.persistence,'memory');assert.equal(ph.config.profiles,'never');assert.equal(ph.config.autocapture,false);assert.equal(ph.config.pageview,false);assert.equal(ph.config.recording,true);assert.equal(ph.config.flags,true);
 assert(!JSON.stringify(ph.events).includes(PRIVATE));assert(!JSON.stringify(ph.events).includes(COMMENT));assert(!JSON.stringify(ph.events).includes('BAD_ACCOUNT_ID'));assert(!JSON.stringify(ph.events).includes('$current_url'));assert(ph.events.every(e=>e.uuid&&e.properties.token==='phc_fixture_public'));assert(ph.events.some(e=>e.event==='feedback.submitted'&&e.properties.rating==='helpful'));
 const clarity=await f.page.evaluate(()=>window.__clarityCalls);assert(!JSON.stringify(clarity).includes(PRIVATE));assert(!JSON.stringify(clarity).includes(COMMENT));assert(clarity.some(x=>x[0]==='event'&&x[1]==='oracle.failed'));
 const sid=feedback.body.session_id;assert(!JSON.stringify(ph.events).includes(sid),'first-party deletion ID must not enter PostHog');assert(!JSON.stringify(clarity).includes(sid),'first-party deletion bearer ID must never go to Microsoft');
 for(const r of f.records.filter(r=>r.kind==='post')){assert.equal(r.headers['x-meatcode-research'],'1');assert.equal(r.headers['content-type'],'application/json');assert(!JSON.stringify(r.body).includes(PRIVATE));if(r.body.events)assert(r.body.events.length<=20);}
 f.withdrawFails(true);await f.page.locator('[data-research-stop]').click();await f.page.waitForTimeout(200);
 assert.equal(await f.page.evaluate(()=>window.MCResearch.startOracle()),null);assert.equal(await f.page.evaluate(()=>sessionStorage.getItem('mc_research_session_v1')),null);
 assert(await f.page.locator('[data-research-stop]').isVisible());
 f.withdrawFails(false);await f.page.locator('[data-research-stop]').click();await f.page.waitForTimeout(500);
 const lastWithdraw=f.records.map(r=>r.path).lastIndexOf('/api/research/withdraw');
 assert.equal(f.records.slice(lastWithdraw+1).filter(r=>r.kind==='post'||r.kind==='sdk'||r.kind==='ph-sdk').length,0,'no SDK reload or future collection after withdrawal');
 assert.equal(await f.page.evaluate(()=>sessionStorage.getItem('mc_research_withdraw_pending_v1')),null);
 assert.deepEqual(f.errors,[]);await f.context.close();
 const disabled=await fixture({enabled:false});await disabled.page.waitForTimeout(200);assert.equal(disabled.records.length,0);assert.equal(await disabled.page.locator('#mcResearchButton').count(),0);await disabled.context.close();
 const unsafe=await fixture({query:'?question=PRIVATE_URL_VALUE'});await unsafe.page.locator('[data-research-accept]').click();await unsafe.page.waitForTimeout(300);assert.equal(unsafe.records.filter(r=>r.kind==='sdk').length,0);assert(unsafe.page.url().includes('PRIVATE_URL_VALUE'),'integration must not rewrite user URL');await unsafe.context.close();
 const old=await fixture({oldConsent:true});await old.page.locator('#mcResearchPanel').waitFor();assert.equal(old.records.length,0,'Oct28 consent must not resume after provider change');await old.context.close();
 const absent=await fixture({noPosthog:true});await absent.page.locator('[data-research-accept]').click();await absent.page.waitForTimeout(300);assert.equal(absent.records.filter(r=>r.kind==='ph-sdk').length,0);assert(absent.events().some(e=>e.name==='session.started'));await absent.context.close();
 const blocked=await fixture({blockPosthog:true});await blocked.page.locator('[data-research-accept]').click();await blocked.page.locator('[data-research-close]').click();await blocked.ask(PRIVATE);assert(blocked.events().some(e=>e.name==='oracle.completed'));assert.equal(await blocked.page.evaluate(()=>window.__phInitCount),undefined);await blocked.context.close();
 const race=await fixture({delayPosthog:600,noClarity:true});await race.page.locator('[data-research-accept]').click();await race.page.locator('[data-research-stop]').click();await race.page.waitForTimeout(850);assert.equal(await race.page.evaluate(()=>window.__phInitCount),undefined,'withdraw during SDK loading cannot initialize tracking');assert.equal(await race.page.evaluate(()=>window.MCResearch.startOracle()),null);await race.context.close();
 const pending=await fixture({enabled:false,pending:true});await pending.page.locator('#mcResearchButton').click();assert(await pending.page.locator('[data-research-stop]').isVisible());assert(await pending.page.locator('[data-research-accept]').isDisabled());await pending.page.locator('[data-research-stop]').click();await pending.page.waitForTimeout(200);assert(pending.records.some(r=>r.path==='/api/research/withdraw'));await pending.context.close();
 console.log(JSON.stringify({source:SOURCE,preConsentNoCollection:true,bodyMaskedBeforeSDK:true,oracleSuccessAndSSEFailures:true,feedbackOnlyFirstParty:true,explicitRating:true,withdrawStopsAndRetries:true,disabledNoCollection:true,unsafeURLSkipsSDK:true,pendingDeletionWhenDisabled:true,freshProviderConsent:true,posthogStrictWhitelist:true,posthogMissingOrBlockedSafe:true,posthogOptoutRaceSafe:true,zeroPageErrors:true}));
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1);});
