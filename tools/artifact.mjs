// Turns the single-file build into a page fragment for hosts that supply their own
// <!doctype>/<head>/<body> skeleton (e.g. a claude.ai artifact).
// Usage: node tools/artifact.mjs docs/index.html out.html
import { readFileSync, writeFileSync } from 'node:fs';

const [src = 'docs/index.html', out = 'dist/artifact.html'] = process.argv.slice(2);
const html = readFileSync(src, 'utf8');
const pick = (re) => [...html.matchAll(re)].map((m) => m[0]);
const title = '<title>淝水之战三维沙盘</title>';
const metas = pick(/<meta name="(?:claude:viewport-fit-sides|description|theme-color)"[^>]*>/g);
const links = pick(/<link rel="(?:preconnect|stylesheet)"[^>]*>/g);
const styles = pick(/<style[^>]*>[\s\S]*?<\/style>/g);
const scripts = pick(/<script type="module"[^>]*>[\s\S]*?<\/script>/g);
if (!scripts.length) throw new Error('no inline module script found');
const page = [title, ...metas, ...links, ...styles, '<div id="app"></div>', ...scripts].join('\n');
writeFileSync(out, page);
console.log(`${out}: ${(page.length / 1024 / 1024).toFixed(2)} MB`);
