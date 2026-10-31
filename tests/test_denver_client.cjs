/* Updated 2026-10-31 · Denver stays visible, saves real research notes and preserves Oracle drafts. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=process.env.DENVER_ROOT||path.resolve(__dirname,'..');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_EXECUTABLE});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();let fail=false;const records=[],errors=[];
 await context.addInitScript(()=>Object.defineProperty(navigator,'webdriver',{get:()=>false}));page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{const req=route.request(),u=new URL(req.url());if(u.hostname!=='127.0.0.1')return route.abort();
  if(u.pathname==='/api/research/config')return route.fulfill({json:{enabled:true,demo_mode:true,environment:'prod',consent_version:'2026-10-29-demo-v1',posthog:{enabled:false}}});
  if(u.pathname.startsWith('/api/research/')){records.push({path:u.pathname,body:req.postDataJSON()});return route.fulfill({status:u.pathname.endsWith('/note')&&fail?503:200,json:{ok:true}});}
  if(u.pathname==='/api/version')return route.fulfill({json:{env:'prod'}});
  if(u.pathname==='/api/flags')return route.fulfill({json:{oracle_redesign:true,live_testing_dashboard:false}});
  if(u.pathname==='/api/ask')return route.fulfill({contentType:'text/event-stream',body:'event: chunk\ndata: Fixture response\n\nevent: done\ndata: {}\n\n'});
  if(u.pathname.startsWith('/api/'))return route.fulfill({json:{ok:true,rows:[],totals:{},phase_topics:[]}});
  const relative=u.pathname==='/'?'app/meatcode_mockup.html':u.pathname.slice(1);let file=path.join(root,relative);if(!fs.existsSync(file))file=path.resolve(__dirname,'..',relative);
  return fs.existsSync(file)?route.fulfill({contentType:file.endsWith('.js')?'application/javascript; charset=utf-8':file.endsWith('.html')?'text/html; charset=utf-8':'image/png',body:fs.readFileSync(file)}):route.fulfill({status:404,body:''});
 });
 await page.goto('http://127.0.0.1:18774/#oracle');await page.locator('#mcTesterWelcome').waitFor();await page.locator('[name=testerName]').fill('Denver Tester');await page.locator('#mcTesterWelcome button').click();await page.locator('#mcTesterWelcome').waitFor({state:'hidden'});
 const pet=page.locator('#mcDenver');assert(await pet.isVisible());assert.equal(await pet.evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');assert.equal(await pet.evaluate(e=>getComputedStyle(e).pointerEvents),'none');
 const sid=await page.evaluate(()=>sessionStorage.getItem('mc_research_session_v1'));
 await page.locator('#oracleTextarea').fill('Fixture question');await page.locator('#oracleAskBtn').click();await page.waitForTimeout(450);
 await page.locator('#mcDenver .hit').hover();await page.locator('#mcDenver textarea').waitFor({state:'visible'});
 await page.locator('#mcDenver textarea').fill('This is a research note.');
 const firstTurn=records.find(r=>r.path.endsWith('/chat')).body;
 // A subsequent question must not replace the context of an already open note.
 await page.evaluate(()=>{const t=MCResearch.startOracle('Another turn',oracleActiveId);MCResearch.completeOracle(t);});
 fail=true;await page.locator('#mcDenver .submit').click();await page.waitForFunction(()=>document.querySelector('#mcDenver').output.textContent.includes('could not'));
 assert.equal(await page.locator('#mcDenver textarea').inputValue(),'This is a research note.');
 fail=false;await page.locator('#mcDenver .submit').click();await page.waitForFunction(()=>document.querySelector('#mcDenver').output.textContent.includes('was saved'));
 const notes=records.filter(r=>r.path.endsWith('/note'));assert.equal(notes.length,2);assert.equal(notes[0].body.event_id,notes[1].body.event_id);assert.equal(notes[1].body.session_id,sid);assert.equal(notes[1].body.tester_label,'Denver Tester');assert.equal(notes[1].body.turn_id,firstTurn.turn_id);assert.equal(notes[1].body.conversation_id,firstTurn.conversation_id);assert(!('rating' in notes[1].body));assert.equal(await page.locator('#mcDenver textarea').inputValue(),'');
 assert(!JSON.stringify(records.filter(r=>r.body.events)).includes('This is a research note.'));
 await page.locator('#mcDenver textarea').fill('Oracle draft');await page.locator('#mcDenver .oracle').click();assert.equal(await page.locator('#oracleTextarea').inputValue(),'Oracle draft');assert(await pet.isVisible());
 await page.locator('#mcDenver .hit').focus();await page.keyboard.press('Enter');await page.locator('#mcDenver textarea').waitFor({state:'visible'});await page.keyboard.press('Escape');assert(!(await page.locator('#mcDenver textarea').isVisible()));
 await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await pet.evaluate(e=>e.motionAllowed),false);await page.reload();await pet.waitFor();assert.equal(await page.locator('#mcTesterWelcome').count(),0,'existing named testers still see Denver');
 await page.setViewportSize({width:390,height:844});await page.locator('#mcDenver .hit').click();await page.locator('#mcDenver textarea').waitFor({state:'visible'});assert(await page.locator('#mcDenver .paper').evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;}));
 if(process.env.DENVER_SCREENSHOT)await page.screenshot({path:process.env.DENVER_SCREENSHOT});
 await page.evaluate(()=>location.hash='science');assert(!(await pet.isVisible()));assert.deepEqual(errors,[]);
 console.log(JSON.stringify({persistent:true,transparent:true,notesAcknowledged:true,retrySameId:true,sessionAndName:true,openingContextPreserved:true,noFakeRating:true,draftHandoff:true,keyboard:true,reducedMotion:true,mobile:true,errors:0}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
