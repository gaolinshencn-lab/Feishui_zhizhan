// Drives www/doc-sound.js (one live segment's battlefield sound) and writes the stem as a 32-bit float WAV.
import { createRequire } from 'node:module';
import { openSync, writeSync, closeSync } from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [seg, out] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage();
page.on('pageerror', (e) => console.log('pageerror', e.message));
page.on('console', (m) => /error|warn/i.test(m.type()) && console.log('console', m.text()));
await page.goto('http://127.0.0.1:8765/index.html');
const t0 = Date.now();
const info = await page.evaluate(async (s) => (await import('/doc-sound.js')).render(s), seg);
console.log(seg, info, `rendered in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
const fd = openSync(out, 'w');
const bytes = info.length * info.channels * 4;
const hdr = Buffer.alloc(44);
hdr.write('RIFF', 0); hdr.writeUInt32LE(36 + bytes, 4); hdr.write('WAVE', 8); hdr.write('fmt ', 12);
hdr.writeUInt32LE(16, 16); hdr.writeUInt16LE(3, 20); hdr.writeUInt16LE(info.channels, 22); hdr.writeUInt32LE(info.sr, 24);
hdr.writeUInt32LE(info.sr * info.channels * 4, 28); hdr.writeUInt16LE(info.channels * 4, 32); hdr.writeUInt16LE(32, 34); hdr.write('data', 36); hdr.writeUInt32LE(bytes, 40);
writeSync(fd, hdr);
const N = 48000 * 5;
for (let off = 0; off < info.length; off += N) {
  const b64 = await page.evaluate(async ([o, n]) => (await import('/doc-sound.js')).slice(o, n), [off, N]);
  writeSync(fd, Buffer.from(b64, 'base64'));
}
closeSync(fd);
await browser.close();
console.log('wrote', out);
