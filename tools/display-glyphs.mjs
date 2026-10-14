// Prints every character that is set in the calligraphic display face, so the font can be
// subset to exactly what the model shows (see tools/subset_fonts.py).
import { EPISODES } from '../src/data/episodes.js';
import { TACTICAL_PLACES, STRATEGIC_PLACES } from '../src/data/places.js';
import { TACTICAL_UNITS, STRATEGIC_UNITS } from '../src/data/units.js';
import { TACTICAL_ROUTES, STRATEGIC_ROUTES } from '../src/data/routes.js';
import { TACTICAL_EVENTS, STRATEGIC_EVENTS } from '../src/data/events.js';
import { readFileSync } from 'node:fs';

const out = [];
for (const e of EPISODES) out.push(e.no, e.title, e.subtitle, e.quote.text, e.date);
for (const p of [...TACTICAL_PLACES, ...STRATEGIC_PLACES]) out.push(p.name);
for (const u of [...TACTICAL_UNITS, ...STRATEGIC_UNITS]) out.push(u.banner || '');
for (const r of [...TACTICAL_ROUTES, ...STRATEGIC_ROUTES]) out.push(r.label || '');
for (const e of [...TACTICAL_EVENTS, ...STRATEGIC_EVENTS]) out.push(e.title, e.kind === 'speech' ? e.text : '');
// numbers in the force panel and strings hard-coded in the UI with the display face
for (const e of EPISODES) for (const s of ['qin', 'jin']) out.push(String(e.forces?.[s]?.value ?? ''));
const ui = readFileSync(new URL('../src/ui/UI.js', import.meta.url), 'utf8') + readFileSync(new URL('../src/app/App.js', import.meta.url), 'utf8');
for (const m of ui.matchAll(/[㐀-鿿豈-﫿　-〿＀-￯]+/g)) out.push(m[0]);
out.push('0123456789万千百十第节晋秦淝水之战北「」“”、，。：；！？（）·—… ');
const set = new Set([...out.join('')]);
process.stdout.write([...set].sort().join(''));
