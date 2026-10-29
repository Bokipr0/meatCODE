/* Last updated: 2026-10-29 · Codex · v2 notes: banners, avatar customization, demo label and flags. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright'),fs=require('fs'),path=require('path'),assert=require('assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_EXECUTABLE});try{
const context=await browser.newContext({viewport:{width:1440,height:1000}});await context.addInitScript(()=>Object.defineProperty(navigator,'webdriver',{get:()=>false}));const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));let enabled=true;
await page.route('**/*',route=>{const u=new URL(route.request().url());if(u.hostname!=='127.0.0.1')return route.abort();
 if(u.pathname==='/api/version')return route.fulfill({json:{env:'prod'}});
 if(u.pathname==='/api/flags')return route.fulfill({json:{demo_badge:enabled,meatcode_avatar:enabled,live_testing_dashboard:false}});
 if(u.pathname==='/api/research/config')return route.fulfill({json:{enabled:true,demo_mode:true,environment:'prod',consent_version:'2026-10-29-demo-v1',posthog:{enabled:false},clarity_project_id:''}});
 if(u.pathname.startsWith('/api/'))return route.fulfill({json:{ok:true,rows:[],totals:{}}});
 const file=path.join(process.cwd(),u.pathname==='/'?'app/meatcode_mockup.html':decodeURIComponent(u.pathname));if(!fs.existsSync(file))return route.fulfill({status:404,body:''});return route.fulfill({contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.png')?'image/png':file.endsWith('.jpg')?'image/jpeg':'text/html',body:fs.readFileSync(file)});
});
await page.goto('http://127.0.0.1:18789/#oracle');await page.locator('#oracle .mc-avatar-change').waitFor();
assert.deepEqual(await page.locator('#oracle .oracle-welcome-points b').allTextContents(),['Curated','Responsive','Human Validated']);assert.equal(await page.locator('#oracle .oracle-heading').count(),0);assert.equal(await page.locator('#oracle .oracle-empty-state .hint').count(),0);assert.equal(await page.locator('#oracle .oracle-empty-state .kick').count(),0);
assert.equal(await page.locator('#oracle .mc-demo-label').innerText(),'DEMO');assert.equal(await page.locator('#oracle .mc-dashboard-btn').isVisible(),false);
await page.waitForFunction(()=>document.querySelector('#mcResearchButton')?.disabled);assert.equal(await page.locator('#mcResearchButton').innerText(),'Demo testing');assert.equal(await page.locator('#mcResearchPanel').isVisible(),false);
await page.locator('#oracle .mc-testing-settings').click();assert(await page.locator('#mcResearchPanel').isVisible());await page.locator('[data-research-close]').click();
await page.locator('#oracle .mc-avatar-change').click();await page.locator('.mc-avatar-dialog input').setInputFiles('app/assets/meatcode-avatar.jpg');await page.waitForFunction(()=>localStorage.getItem('mc_oracle_avatar_v1')?.startsWith('data:image/webp;'));
await page.locator('.mc-avatar-dialog [data-close]').click();await page.reload();await page.locator('#oracle .mc-avatar-change').waitFor();assert((await page.locator('.mc-avatar-change img').getAttribute('src')).startsWith('data:image/webp;'));
await page.locator('.mc-avatar-change').click();await page.locator('[data-reset]').click();await page.locator('.mc-avatar-dialog [data-close]').click();
await page.screenshot({path:'/private/tmp/meatcode-v2-oracle.png'});
await page.evaluate(()=>{mcRecordOracleQuestion('Delete fixture');renderOracleSidebar();});const del=page.locator('#oracle .ctx-del').first();await page.mouse.move(1400,900);assert.equal(await del.locator('svg').evaluate(el=>getComputedStyle(el).opacity),'0');await del.hover();assert.equal(await del.locator('svg').evaluate(el=>getComputedStyle(el).opacity),'1');await del.click();
await page.locator('#oracleNewChatBtn').click();await page.locator('.mc-avatar-change').waitFor();enabled=false;await page.reload();await page.waitForTimeout(300);assert.equal(await page.locator('.mc-demo-label').count(),0);assert.equal(await page.locator('.mc-avatar-change').count(),0);assert.deepEqual(errors,[]);
await context.close();console.log('PASS: v2 cards, passive demo label, privacy settings, avatar upload/reset/reload, hover delete, Release Center OFF, no page errors.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
