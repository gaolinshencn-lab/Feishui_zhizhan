// Copies the single-file build into docs/ (served by GitHub Pages, or opened directly).
import { copyFileSync, mkdirSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const src = resolve(root, 'dist/index.html');
const out = resolve(root, 'docs/index.html');
mkdirSync(dirname(out), { recursive: true });
copyFileSync(src, out);
const mb = (statSync(out).size / 1024 / 1024).toFixed(2);
console.log(`docs/index.html written (${mb} MB, fully self-contained)`);
