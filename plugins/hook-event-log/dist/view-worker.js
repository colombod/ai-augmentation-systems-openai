import {
  closeSync, constants, fstatSync, openSync, opendirSync, readSync,
} from 'node:fs';
import { enterRoot, enterChild, openRegular, resolveDataRoot } from './filesystem.js';
import { parseJSONStrict, validateRecord } from './record.js';

const MAX_RECORD = 65536;
const MAX_LEGACY = 64 * 1024 * 1024;
const MAX_ENTRIES = 10000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const session = process.argv[2];
const chunk = Buffer.alloc(8192);
let acknowledge;
process.on('message', (message) => {
  if (message?.type !== 'ack' || !acknowledge) return process.exit(1);
  const accept = acknowledge;
  acknowledge = undefined;
  accept();
});
process.on('disconnect', () => process.exit(1));

function readInput() {
  const chunks = [];
  let size = 0;
  while (true) {
    const count = readSync(0, chunk, 0, chunk.length, null);
    if (!count) break;
    size += count;
    if (size > 1024 * 1024) throw new Error();
    chunks.push(Buffer.from(chunk.subarray(0, count)));
  }
  const state = parseJSONStrict(Buffer.concat(chunks, size));
  if (!state || typeof state !== 'object' || !Array.isArray(state.seen)
    || state.seen.length > MAX_ENTRIES || state.seen.some((id) => typeof id !== 'string' || !UUID.test(id))
    || new Set(state.seen).size !== state.seen.length) throw new Error();
  if (state.legacy !== null) {
    const value = state.legacy;
    if (!value || typeof value !== 'object' || !Number.isSafeInteger(value.offset) || value.offset < 0
      || typeof value.dev !== 'string' || !/^\d+$/.test(value.dev)
      || typeof value.ino !== 'string' || !/^\d+$/.test(value.ino)
      || typeof value.tail !== 'string' || value.tail.length > Math.ceil(MAX_RECORD / 3) * 4) throw new Error();
    const tail = Buffer.from(value.tail, 'base64');
    if (tail.length > MAX_RECORD || tail.toString('base64') !== value.tail) throw new Error();
  }
  return state;
}

async function emit(bytes) {
  if (!bytes.length || bytes.length > MAX_RECORD || bytes.at(-1) !== 10
    || bytes.subarray(0, -1).includes(10)) throw new Error();
  const record = parseJSONStrict(bytes.subarray(0, -1));
  if (!validateRecord(record)) throw new Error();
  // Emit only the validated record, never discarded duplicate-key tokens or surrounding bytes.
  const line = `${JSON.stringify(record)}\n`;
  await new Promise((resolve, reject) => {
    acknowledge = resolve;
    process.send({ type: 'record', line }, (error) => {
      if (error) { acknowledge = undefined; reject(error); }
    });
  });
}

function missing(error) { return error?.code === 'ENOENT'; }

async function readLegacy(root, previous) {
  let fd;
  try {
    enterRoot(root);
    enterChild('event-types', { private: true });
    fd = openRegular(`${session}.jsonl`);
  } catch (error) {
    if (missing(error) && previous === null) return { state: null, found: false };
    throw error;
  }
  try {
    const stat = fstatSync(fd, { bigint: true });
    if (previous && (previous.dev !== String(stat.dev) || previous.ino !== String(stat.ino)
      || stat.size < BigInt(previous.offset))) throw new Error();
    let offset = previous?.offset ?? 0;
    if (stat.size - BigInt(offset) > BigInt(MAX_LEGACY)) throw new Error();
    let tail = previous ? Buffer.from(previous.tail, 'base64') : Buffer.alloc(0);
    let read = 0;
    while (true) {
      const count = readSync(fd, chunk, 0, Math.min(chunk.length, MAX_LEGACY - read + 1), offset);
      if (!count) break;
      read += count;
      if (read > MAX_LEGACY || !Number.isSafeInteger(offset + count)) throw new Error();
      offset += count;
      let start = 0;
      while (start < count) {
        const end = chunk.subarray(0, count).indexOf(10, start);
        const stop = end < 0 ? count : end + 1;
        const segment = chunk.subarray(start, stop);
        if (tail.length + segment.length > MAX_RECORD) throw new Error();
        tail = Buffer.concat([tail, segment]);
        if (end >= 0) { await emit(tail); tail = Buffer.alloc(0); }
        start = stop;
      }
    }
    return {
      state: { dev: String(stat.dev), ino: String(stat.ino), offset, tail: tail.toString('base64') },
      found: true,
    };
  } finally { closeSync(fd); }
}

function currentDirectory() {
  const fd = openSync('.', constants.O_RDONLY | constants.O_DIRECTORY | constants.O_NOFOLLOW);
  try { return fstatSync(fd, { bigint: true }); } finally { closeSync(fd); }
}

function returnToSession(sessionFd) {
  const expected = fstatSync(sessionFd, { bigint: true });
  process.chdir('..');
  const actual = currentDirectory();
  if (actual.dev !== expected.dev || actual.ino !== expected.ino) throw new Error();
}

async function readFragments(root, seen) {
  try {
    enterRoot(root);
    enterChild('event-types-v2', { private: true });
    enterChild(session, { private: true });
  } catch (error) {
    if (missing(error) && seen.size === 0) return false;
    throw error;
  }
  // Keep this inode alive while child directories can be moved independently.
  const sessionFd = openSync('.', constants.O_RDONLY | constants.O_DIRECTORY | constants.O_NOFOLLOW);
  try {
    const directory = opendirSync('.');
    const ids = [];
    try {
      for (let entry; (entry = directory.readSync()) !== null;) {
        if (ids.length >= MAX_ENTRIES || !UUID.test(entry.name) || !entry.isDirectory()) throw new Error();
        ids.push(entry.name);
      }
    } finally { directory.closeSync(); }
    ids.sort();
    const present = new Set(ids);
    if ([...seen].some((id) => !present.has(id))) throw new Error();
    let found = seen.size > 0;
    for (const id of ids) {
      if (seen.has(id)) continue;
      enterChild(id, { private: true });
      let fd;
      try { fd = openRegular('record.jsonl'); }
      catch (error) {
        if (!missing(error)) throw error;
        returnToSession(sessionFd);
        continue;
      }
      try {
        if (fstatSync(fd, { bigint: true }).size > BigInt(MAX_RECORD)) throw new Error();
        const pieces = [];
        let size = 0;
        while (true) {
          const count = readSync(fd, chunk, 0, Math.min(chunk.length, MAX_RECORD - size + 1), null);
          if (!count) break;
          size += count;
          if (size > MAX_RECORD) throw new Error();
          pieces.push(Buffer.from(chunk.subarray(0, count)));
        }
        await emit(Buffer.concat(pieces, size));
        if (seen.size >= MAX_ENTRIES) throw new Error();
        seen.add(id);
        found = true;
      } finally { closeSync(fd); }
      returnToSession(sessionFd);
    }
    return found;
  } finally { closeSync(sessionFd); }
}

try {
  if (process.argv.length !== 3 || !/^[0-9a-f]{64}$/.test(session ?? '') || !process.send) throw new Error();
  const root = resolveDataRoot();
  const state = readInput();
  const seen = new Set(state.seen);
  const legacy = await readLegacy(root, state.legacy);
  const fragmentsFound = await readFragments(root, seen);
  process.send({ type: 'done', state: { legacy: legacy.state, seen: [...seen] }, found: legacy.found || fragmentsFound }, (error) => {
    process.exit(error ? 1 : 0);
  });
} catch { process.exit(1); }
