import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const FAILURE = 'hook-event-log: session view incomplete\n';
const worker = fileURLToPath(new URL('./view-worker.js', import.meta.url));
let child;
let failed = false;
let timer;
let session;
let follow = false;

function fail() {
  if (failed) return;
  failed = true;
  clearTimeout(timer);
  if (child) child.kill('SIGKILL');
  process.stderr.write(FAILURE);
  process.exit(1);
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    if (child) child.kill('SIGKILL');
    process.exit(signal === 'SIGINT' ? 130 : 143);
  });
}
process.on('exit', () => { if (child) child.kill('SIGKILL'); });
process.stdout.on('error', fail);
process.stdin.destroy();

const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--session' && session === undefined) session = args[++i];
  else if (args[i] === '--follow' && !follow) follow = true;
  else fail();
}
if (!/^[0-9a-f]{64}$/.test(session ?? '')) fail();

let state = { legacy: null, seen: [] };
let initial = true;

function scan() {
  return new Promise((resolve) => {
    let done = false;
    let nextState;
    let waitingForOutput = false;
    const current = spawn(process.execPath, [worker, session], {
      shell: false, stdio: ['pipe', 'ignore', 'ignore', 'ipc'],
    });
    child = current;
    timer = setTimeout(fail, initial ? 30000 : 2400);
    current.on('error', fail);
    current.stdin.on('error', fail);
    current.stdin.end(JSON.stringify(state));
    current.on('message', (message) => {
      if (done || !message || typeof message !== 'object') return fail();
      if (message.type === 'record') {
        // One acknowledged record at a time bounds both queues even with a stalled consumer.
        if (waitingForOutput || typeof message.line !== 'string'
          || Buffer.byteLength(message.line) > 65536 || !message.line.endsWith('\n')) return fail();
        waitingForOutput = true;
        process.stdout.write(message.line, (error) => {
          if (error || failed || !current.connected) return fail();
          waitingForOutput = false;
          current.send({ type: 'ack' }, (sendError) => { if (sendError) fail(); });
        });
      } else if (message.type === 'done') {
        if (waitingForOutput || !message.state || !Array.isArray(message.state.seen)
          || message.state.seen.length > 10000 || (initial && !message.found)) return fail();
        nextState = message.state;
        done = true;
      } else fail();
    });
    current.on('close', (code) => {
      clearTimeout(timer);
      child = undefined;
      if (code !== 0 || !done || failed) return fail();
      state = nextState;
      initial = false;
      resolve();
    });
  });
}

try {
  do {
    await scan();
    if (follow) await new Promise((resolve) => setTimeout(resolve, 1000));
  } while (follow);
} catch { fail(); }
