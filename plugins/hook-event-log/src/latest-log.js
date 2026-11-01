import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const worker = fileURLToPath(new URL('./core.js', import.meta.url));
const result = spawnSync(process.execPath, [worker, '--latest-log'], {
  shell: false, stdio: ['ignore', 'pipe', 'ignore'], timeout: 2400, killSignal: 'SIGKILL', maxBuffer: 128 * 1024,
});
if (!result.error && result.status === 0) process.stdout.write(result.stdout);
else {
  process.stderr.write('hook-event-log: no readable session log found\n');
  process.exitCode = 1;
}
