import { spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Rust owns root resolution and read-only discovery; this is transport only.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const executable = resolve(root, 'bin', `${process.platform}-${process.arch}`,
  process.platform === 'win32' ? 'event-log-core.exe' : 'event-log-core');
const result = spawnSync(executable, ['--latest-log'], {
  shell: false, stdio: ['ignore', 'pipe', 'ignore'], timeout: 2400, maxBuffer: 128 * 1024,
});
if (!result.error && result.status === 0) {
  process.stdout.write(result.stdout);
} else {
  process.stderr.write('hook-event-log: no readable session log found\n');
  process.exitCode = 1;
}
