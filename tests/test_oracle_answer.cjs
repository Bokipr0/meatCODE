/* Last updated: 2026-11-17 · Codex · Legacy and formatted answer splitting. */
const assert = require('node:assert/strict');
const api = require('../app/assets/oracle-answer.js');
let text = 'Recommendation first [880].\n\nWorking from: pea protein.\n\nMechanism and evidence [144].';
let boundary = text.indexOf('Working from:');
assert.equal(api.split(text, boundary).brief, 'Recommendation first [880].');
assert(api.split(text, boundary).detail.includes('Working from:'));
assert.equal(api.split('A complete short answer.').detail, '');
assert.equal(api.split('Lead sentence.\n\nEssential qualification still arriving.', null, true).detail, '');
assert.equal(api.split('Legacy lead.\n\nLegacy supporting detail.').brief, 'Legacy lead.');
text = Array.from({length:240},(_,i)=>'word'+i).join(' ');
let parts = api.split(text);
assert(parts.brief.split(/\s+/).length <= 120);
assert.equal((parts.brief+' '+parts.detail).trim(), text);
assert(api.split(text, 999999).detail);
assert(api.split(text, -1).detail);
assert.equal(api.split('First sentence. '+text).brief, 'First sentence.');
assert(api.split('条件を確認してください。\n\n追加の説明。').detail);
console.log('PASS: marked boundaries, short and legacy answers, 120-word fallback, intact full content, invalid boundaries and Unicode.');
