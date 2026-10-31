/* Last updated: 2026-10-31 · Isolated name/session flow against the exact release assets. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=process.env.NAME_RELEASE_ROOT||path.resolve(__dirname,'..');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_EXECUTABLE});
try{
 const context=await browser.newContext({viewport:{width:1000,height:760}});let fail=true;const writes=[],errors=[];
 await context.addInitScript(()=>Object.defineProperty(navigator,'webdriver',{get:()=>false}));
 await context.route('**/*',async route=>{
  const req=route.request(),u=new URL(req.url());
  if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><meta charset="utf-8"></head><body style="background:#faf7f0"><h1>MeatCODE Oracle</h1><script src="/app/assets/user-research.js"></script></body></html>'});
  if(u.pathname==='/api/research/config')return route.fulfill({json:{enabled:true,demo_mode:true,environment:'prod',consent_version:'2026-10-29-demo-v1',posthog:{enabled:false}}});
  if(u.pathname.startsWith('/api/research/')){writes.push({path:u.pathname,body:req.postDataJSON()});return route.fulfill({status:u.pathname.endsWith('/name')&&fail?503:200,json:{ok:true}});}
  const file=path.join(root,u.pathname);if(fs.existsSync(file))return route.fulfill({contentType:file.endsWith('.js')?'application/javascript':'image/png',body:fs.readFileSync(file)});
  return route.abort();
 });
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:18774/#oracle');await page.locator('#mcTesterWelcome').waitFor();
 assert.equal(await page.locator('input').count(),1);const sid=await page.evaluate(()=>sessionStorage.getItem('mc_research_session_v1'));
 await page.locator('input').fill('Alex');await page.locator('button').click();await page.waitForFunction(()=>document.querySelector('#mcTesterWelcome [role=status]').textContent.includes('try again'));
 assert(await page.locator('#mcTesterWelcome').isVisible());fail=false;await page.locator('button').click();await page.locator('#mcTesterWelcome').waitFor({state:'hidden'});
 await page.reload();await page.waitForTimeout(350);assert.equal(await page.locator('#mcTesterWelcome').count(),0);assert.equal(await page.evaluate(()=>sessionStorage.getItem('mc_research_session_v1')),sid);
 const seed=await page.evaluate(()=>Object.fromEntries(Object.entries(sessionStorage))),other=await context.newPage();
 await other.addInitScript(seed=>Object.entries(seed).forEach(([k,v])=>sessionStorage.setItem(k,v)),seed);
 await other.goto('http://127.0.0.1:18774/#oracle');await other.locator('#mcTesterWelcome').waitFor();
 assert.notEqual(await other.evaluate(()=>sessionStorage.getItem('mc_research_session_v1')),sid);
 await other.setViewportSize({width:390,height:844});assert(await other.locator('#mcTesterWelcome').evaluate(el=>el.getBoundingClientRect().width<=innerWidth));
 if(process.env.NAME_SCREENSHOT)await other.screenshot({path:process.env.NAME_SCREENSHOT});
 await other.locator('input').fill('Alex');await other.locator('button').click();await other.locator('#mcTesterWelcome').waitFor({state:'hidden'});
 await page.evaluate(()=>{const t=MCResearch.startOracle('Fixture question','fixture-chat');MCResearch.completeOracle(t);});await page.waitForTimeout(400);
 const chat=writes.find(x=>x.path.endsWith('/chat'));assert.equal(chat.body.session_id,sid);assert.equal(chat.body.tester_label,'Alex');assert.deepEqual(errors,[]);
 console.log(JSON.stringify({nameOnly:true,serverAcknowledgement:true,retry:true,reload:true,duplicatedTabIsolation:true,sameNamesDistinct:true,chatLinked:true,mobile:true,errors:0}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
