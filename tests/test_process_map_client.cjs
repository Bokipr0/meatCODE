// Last updated: 2026-11-22 UTC · Claude (Fable 5.2) · the shared process-map rail: short descriptions, toggle, info card, no chat writes
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Minimal DOM: enough for process-map.js (createElement, classes, attributes, click listeners, children).
function node(tag) {
  const n = { tagName: tag.toUpperCase(), children: [], attrs: {}, listeners: {}, className: '', textContent: '', type: '' };
  n.classList = { add: c => { if (!n.className.split(' ').includes(c)) n.className = (n.className + ' ' + c).trim(); } };
  n.setAttribute = (k, v) => { n.attrs[k] = String(v); };
  n.addEventListener = (k, fn) => { n.listeners[k] = fn; };
  n.append = (...kids) => { n.children.push(...kids); };
  n.replaceChildren = () => { n.children = []; };
  n.click = () => n.listeners.click && n.listeners.click();
  return n;
}
const all = (n, test, out = []) => { if (test(n)) out.push(n); n.children.forEach(c => all(c, test, out)); return out; };
const byClass = (root, c) => all(root, n => n.className.split(' ').includes(c));

global.window = {};
global.document = { createElement: node };
eval(fs.readFileSync(path.join(__dirname, '..', 'app', 'modules', 'process-map.js'), 'utf8'));
const PM = window.MCProcessMap;

// Short description: first extracted description only, first sentence, hard cap.
assert.strictEqual(PM.shortDescription('Hexanal is an aldehyde. More detail here.<SEP>Second record.'), 'Hexanal is an aldehyde.');
const long = PM.shortDescription('x'.repeat(40) + ' ' + 'word '.repeat(80));
assert.ok(long.length <= 150 && long.endsWith('…'));
assert.strictEqual(PM.shortDescription(''), 'No description in the graph for this entry.');

const map = { id: 'm', focus: 'Reactions', stages: { Precursors: ['a', 'b'], Reactions: ['r'] },
  nodes: [{ id: 'a', name: 'Alpha', type: 'compound', description: 'Alpha is the first precursor here. Then more.<SEP>Other.', source_ids: ['c1', 'c2'] },
          { id: 'b', name: 'Beta', description: 'Beta.' }, { id: 'r', name: 'Rho', description: 'Rho.' }] };
const host = node('div');
let chatWrites = 0;
PM.render(host, map, { onStageDetails: () => chatWrites++, onEntityDetails: () => chatWrites++ });

const selectedSteps = () => byClass(host, 'pm-stage').filter(s => s.className.includes('selected')).map(s => byClass(s, 'pm-step')[0].textContent);
const step = name => byClass(host, 'pm-step').find(s => s.textContent === name);
const chip = name => byClass(host, 'pm-chip').find(s => s.textContent === name);

assert.deepStrictEqual(byClass(host, 'pm-step').map(s => s.textContent), PM.STAGES);
assert.deepStrictEqual(selectedSteps(), ['Reactions']);                 // the map's focus starts selected
step('Volatiles').click();
assert.deepStrictEqual(selectedSteps(), ['Volatiles']);                 // clicking a step toggles it on …
assert.strictEqual(step('Volatiles').attrs['aria-pressed'], 'true');
step('Volatiles').click();
assert.deepStrictEqual(selectedSteps(), []);                            // … and off again

chip('Alpha').click();                                                  // a component opens ONE short card in the rail
let cards = byClass(host, 'pm-card');
assert.strictEqual(cards.length, 1);
assert.strictEqual(byClass(cards[0], 'pm-card-text')[0].textContent, 'Alpha is the first precursor here.');
assert.ok(all(cards[0], n => /2 evidence chunks/.test(n.textContent)).length);
assert.deepStrictEqual(selectedSteps(), ['Precursors']);
assert.ok(chip('Alpha').className.includes('selected'));
chip('Beta').click();
assert.strictEqual(byClass(host, 'pm-card').length, 1);                 // never a stack of cards
assert.strictEqual(byClass(byClass(host, 'pm-card')[0], 'pm-card-text')[0].textContent, 'Beta.');
chip('Beta').click();
assert.strictEqual(byClass(host, 'pm-card').length, 0);                 // same chip again closes it
assert.strictEqual(chatWrites, 0);                                      // none of the above wrote into the conversation

chip('Alpha').click();
byClass(host, 'pm-link').forEach(link => link.click());                 // only the explicit links do
assert.strictEqual(chatWrites, 2);

const quiet = node('div');                                              // classic Oracle panel: no "in chat" links at all
PM.render(quiet, { ...map, id: 'm2' }, {});
byClass(quiet, 'pm-chip')[0].click();
assert.strictEqual(byClass(quiet, 'pm-link').length, 0);
console.log('process-map client: ok');
