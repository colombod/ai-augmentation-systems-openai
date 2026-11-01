import { constants as C, mkdirSync, openSync, closeSync, writeSync, readSync,
  lstatSync, renameSync, opendirSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { enterRoot, enterChild, privateOwned, resolveDataRoot } from './filesystem.js';
import { LIMIT, parseEvent } from './record.js';

function input() {
  const chunks = [];
  let length = 0;
  while (true) {
    const buffer = Buffer.alloc(Math.min(65536, LIMIT + 1 - length));
    const count = readSync(0, buffer, 0, buffer.length, null);
    if (count === 0) return Buffer.concat(chunks, length);
    chunks.push(buffer.subarray(0, count));
    length += count;
    if (length > LIMIT) throw new Error();
  }
}

function publish() {
  const { sessionHash, bytes } = parseEvent(input());
  enterRoot(resolveDataRoot(process.env, { fallback: false }), { create: true });
  enterChild('event-types-v2', { create: true, private: true });
  enterChild(sessionHash, { create: true, private: true });
  let id;
  for (let attempt = 0; attempt < 8; attempt++) {
    id = randomUUID();
    try { mkdirSync(id, { mode: 0o700 }); break; }
    catch (error) { if (error.code !== 'EEXIST' || attempt === 7) throw error; }
  }
  enterChild(id, { private: true });
  const fd = openSync('pending', C.O_WRONLY | C.O_CREAT | C.O_EXCL | C.O_NOFOLLOW | C.O_NONBLOCK, 0o600);
  let identity;
  try {
    identity = privateOwned(fd);
    let offset = 0;
    while (offset < bytes.length) {
      const count = writeSync(fd, bytes, offset, bytes.length - offset, null);
      if (count <= 0) throw new Error();
      offset += count;
    }
    const after = privateOwned(fd);
    if (after.size !== BigInt(bytes.length)) throw new Error();
  } finally { closeSync(fd); }
  const staged = lstatSync('pending', { bigint: true });
  if (!staged.isFile() || staged.dev !== identity.dev || staged.ino !== identity.ino || staged.nlink !== 1n) throw new Error();
  try { lstatSync('record.jsonl'); throw new Error(); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  renameSync('pending', 'record.jsonl');
  const published = lstatSync('record.jsonl', { bigint: true });
  if (!published.isFile() || published.dev !== identity.dev || published.ino !== identity.ino || published.nlink !== 1n) throw new Error();
}

function latest() {
  const root = resolveDataRoot();
  enterRoot(root);
  enterChild('event-types');
  const directory = opendirSync('.');
  let selected;
  try {
    for (let entry; (entry = directory.readSync()) !== null;) {
      const stat = lstatSync(entry.name, { bigint: true });
      if (stat.isSymbolicLink()) throw new Error();
      if (!stat.isFile() || !/^[0-9a-f]{64}\.jsonl$/.test(entry.name)) continue;
      if (!selected || stat.mtimeNs > selected.time || (stat.mtimeNs === selected.time && entry.name > selected.name)) selected = { time: stat.mtimeNs, name: entry.name };
    }
  } finally { directory.closeSync(); }
  if (!selected) throw new Error();
  process.stdout.write(`${root.replace(/\/$/, '')}/event-types/${selected.name}\n`);
}

try {
  const args = process.argv.slice(2);
  if (args.length === 0) publish();
  else if (args.length === 1 && args[0] === '--latest-log') latest();
  else throw new Error();
} catch {
  process.stderr.write('hook-event-log: operation failed\n');
  process.exitCode = 1;
}
