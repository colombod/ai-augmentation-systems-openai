import { constants as C, openSync, closeSync, fstatSync, mkdirSync } from 'node:fs';

const DIRECTORY = C.O_RDONLY | C.O_DIRECTORY | C.O_NOFOLLOW;

export function assertComponent(name) {
  if (typeof name !== 'string' || !name || name === '.' || name === '..' || name.includes('/') || name.includes('\0')) throw new Error();
}

export function privateOwned(fd, { directory = false } = {}) {
  const stat = fstatSync(fd, { bigint: true });
  if (typeof process.geteuid !== 'function' || stat.uid !== BigInt(process.geteuid()) ||
      (stat.mode & 0o077n) !== 0n || (directory ? !stat.isDirectory() : !stat.isFile()) ||
      (!directory && stat.nlink !== 1n)) throw new Error();
  return stat;
}

// Use only in an isolated process with synchronous, relative filesystem operations.
export function enterChild(name, { create = false, private: owned = false } = {}) {
  assertComponent(name);
  if (create) {
    try { mkdirSync(name, { mode: 0o700 }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
  }
  const before = openSync(name, DIRECTORY);
  let current;
  try {
    const expected = fstatSync(before, { bigint: true });
    process.chdir(name);
    current = openSync('.', DIRECTORY);
    const actual = fstatSync(current, { bigint: true });
    if (actual.dev !== expected.dev || actual.ino !== expected.ino) throw new Error();
    if (owned) privateOwned(current, { directory: true });
    return actual;
  } finally {
    if (current !== undefined) closeSync(current);
    closeSync(before);
  }
}

export function enterRoot(root, { create = false } = {}) {
  if (!['linux', 'darwin'].includes(process.platform) || typeof root !== 'string' || !root.startsWith('/') || root.includes('\0')) throw new Error();
  const components = root.split('/').filter(name => name !== '' && name !== '.');
  if (components.some(name => name === '..')) throw new Error();
  process.chdir('/');
  for (const name of components) enterChild(name, { create });
}

export function resolveDataRoot(env = process.env, { fallback = true } = {}) {
  const absolute = value => {
    if (typeof value !== 'string' || !value.startsWith('/') || value.includes('\0')) throw new Error();
    return value;
  };
  if (env.PLUGIN_DATA !== undefined) return absolute(env.PLUGIN_DATA);
  if (!fallback) throw new Error();
  const base = env.CODEX_HOME !== undefined ? absolute(env.CODEX_HOME) : `${absolute(env.HOME)}/.codex`;
  return `${base}/plugins/data/hook-event-log-ai-augmentation-systems-openai`;
}

export function openRegular(name) {
  assertComponent(name);
  const fd = openSync(name, C.O_RDONLY | C.O_NOFOLLOW | C.O_NONBLOCK);
  try { privateOwned(fd); return fd; }
  catch (error) { closeSync(fd); throw error; }
}
