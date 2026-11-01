import { copyFileSync, mkdirSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
mkdirSync(resolve(root, 'dist'), { recursive: true });
for (const name of readdirSync(resolve(root, 'src')).sort()) {
  if (name.endsWith('.js')) copyFileSync(resolve(root, 'src', name), resolve(root, 'dist', name));
}
console.log('Built JavaScript entry points in dist/');
