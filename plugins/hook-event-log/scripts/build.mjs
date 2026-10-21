import { spawnSync } from 'node:child_process';
import { chmodSync, copyFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
function run(command, args) {
  const result = spawnSync(command, args, { cwd: root, stdio: 'inherit', shell: false });
  if (result.error || result.status !== 0) throw new Error(`Build failed: ${command}`);
}
run(process.execPath, [resolve(root, 'node_modules/typescript/bin/tsc'), '-p', 'tsconfig.json']);
// A deterministic local target directory avoids accidental external target copies.
run('cargo', ['build', '--locked', '--release', '--manifest-path', 'core/Cargo.toml',
  '--target-dir', 'core/target']);
const name = process.platform === 'win32' ? 'event-log-core.exe' : 'event-log-core';
const destination = resolve(root, 'bin', `${process.platform}-${process.arch}`);
mkdirSync(destination, { recursive: true });
copyFileSync(resolve(root, 'core/target/release', name), resolve(destination, name));
chmodSync(resolve(destination, name), 0o755);
console.log(`Built dist/hook.js and bin/${process.platform}-${process.arch}/${name}`);
