import { spawn, type ChildProcess } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// This adapter transports opaque bytes only. Validation and logging belong to Rust.
const LIMIT = 1024 * 1024;
const FAILURE = 'hook-event-log: event could not be recorded\n';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const executable = resolve(root, 'bin', `${process.platform}-${process.arch}`,
  process.platform === 'win32' ? 'event-log-core.exe' : 'event-log-core');
let child: ChildProcess | undefined;
let finished = false;
let size = 0;
let chunks: Buffer[] = [];

function finish(success: boolean): void {
  if (finished) return;
  finished = true;
  clearTimeout(deadline);
  process.stdin.destroy();
  chunks = [];
  if (child && child.exitCode === null) child.kill('SIGKILL');
  if (!success) process.stderr.write(FAILURE);
  process.exitCode = success ? 0 : 1;
  // Terminate even when input remains open or a broken native process retains pipes.
  process.exit(process.exitCode);
}

// Covers idle stdin, oversized input and the complete native subprocess lifetime.
const deadline = setTimeout(() => finish(false), 2400);
process.stdin.on('error', () => finish(false));
process.stdin.on('data', (chunk: Buffer) => {
  size += chunk.length;
  if (size > LIMIT) return finish(false);
  chunks.push(chunk);
});
process.stdin.on('end', () => {
  if (finished) return;
  const payload = Buffer.concat(chunks, size);
  chunks = [];
  child = spawn(executable, [], { shell: false, stdio: ['pipe', 'ignore', 'ignore'] });
  child.on('error', () => finish(false));
  child.on('close', (code) => finish(code === 0));
  child.stdin!.on('error', () => finish(false));
  child.stdin!.end(payload);
});
