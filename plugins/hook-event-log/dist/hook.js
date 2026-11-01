import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const LIMIT = 1_048_576;
const FAILURE = 'hook-event-log: event could not be recorded\n';
const worker = fileURLToPath(new URL('./core.js', import.meta.url));
let child;
let finished = false;
let size = 0;
let chunks = [];
function finish(success) {
  if (finished) return;
  finished = true;
  clearTimeout(deadline);
  process.stdin.destroy();
  chunks = [];
  if (child && child.exitCode === null) child.kill('SIGKILL');
  if (!success) process.stderr.write(FAILURE);
  process.exit(success ? 0 : 1);
}
const deadline = setTimeout(() => finish(false), 2400);
process.stdin.on('error', () => finish(false));
process.stdin.on('data', chunk => {
  size += chunk.length;
  if (size > LIMIT) return finish(false);
  chunks.push(chunk);
});
process.stdin.on('end', () => {
  if (finished) return;
  const payload = Buffer.concat(chunks, size);
  chunks = [];
  child = spawn(process.execPath, [worker], { shell: false, stdio: ['pipe', 'ignore', 'ignore'] });
  child.on('error', () => finish(false));
  child.on('close', code => finish(code === 0));
  child.stdin.on('error', () => finish(false));
  child.stdin.end(payload);
});
