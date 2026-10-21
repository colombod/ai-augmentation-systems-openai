import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, realpath, rm, mkdir, readFile, stat, utimes, symlink, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const failure = 'hook-event-log: no readable session log found\n';
function env(overrides = {}) {
  const result = {...process.env};
  for (const key of ['PLUGIN_DATA', 'CODEX_HOME', 'HOME']) delete result[key];
  return {...result, ...overrides};
}
function latest(overrides) {
  return spawnSync(process.execPath, [join(root, 'dist/latest-log.js')], {
    env: env(overrides), encoding: 'utf8', timeout: 4000,
  });
}
async function fixture(run) {
  const directory = await realpath(await mkdtemp(join(tmpdir(), 'latest-log-test-')));
  try { return await run(directory); }
  finally { await rm(directory, {recursive: true, force: true}); }
}
async function record(data, session) {
  const result = spawnSync(process.execPath, [join(root, 'dist/hook.js')], {
    input: JSON.stringify({hook_event_name: 'Stop', session_id: session}),
    env: env({PLUGIN_DATA: data}), encoding: 'utf8', timeout: 4000,
  });
  assert.equal(result.status, 0, result.stderr);
  return join(data, 'event-types', createHash('sha256').update(session).digest('hex') + '.jsonl');
}
function failed(result) {
  assert.equal(result.status, 1);
  assert.equal(result.stdout, '');
  assert.equal(result.stderr, failure);
}

test('latest helper selects by mtime and preserves contents and modification metadata', () => fixture(async directory => {
  const first = await record(directory, 'first');
  const second = await record(directory, 'second');
  await utimes(first, 1000, 1000);
  await utimes(second, 2000, 2000);
  const before = await readFile(second);
  const beforeStat = await stat(second);
  const beforeDir = await stat(join(directory, 'event-types'));
  const result = latest({PLUGIN_DATA: directory});
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
  assert.equal(result.stdout, second + '\n');
  const afterStat = await stat(second);
  assert.equal(afterStat.mtimeMs, beforeStat.mtimeMs);
  assert.equal((await stat(join(directory, 'event-types'))).mtimeMs, beforeDir.mtimeMs);
  assert.deepEqual(await readFile(second), before);
}));

test('explicit root takes precedence over CODEX_HOME and HOME', () => fixture(async directory => {
  const data = join(directory, 'explicit');
  const expected = await record(data, 'explicit');
  const result = latest({PLUGIN_DATA: data, CODEX_HOME: 'invalid-relative', HOME: 'invalid-relative'});
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, expected + '\n');
}));

test('CODEX_HOME and HOME default resolve the documented plugin directory', () => fixture(async directory => {
  const suffix = ['plugins', 'data', 'hook-event-log-ai-augmentation-systems-openai'];
  const codexHome = join(directory, 'codex');
  const explicit = await record(join(codexHome, ...suffix), 'custom-home');
  assert.equal(latest({CODEX_HOME: codexHome, HOME: 'invalid-relative'}).stdout, explicit + '\n');
  const userHome = join(directory, 'user');
  const defaultPath = await record(join(userHome, '.codex', ...suffix), 'default-home');
  assert.equal(latest({HOME: userHome}).stdout, defaultPath + '\n');
}));

test('invalid overrides and missing logs fail without creating paths', () => fixture(async directory => {
  await record(directory, 'valid');
  failed(latest({PLUGIN_DATA: '', CODEX_HOME: directory}));
  failed(latest({PLUGIN_DATA: 'relative', HOME: directory}));
  failed(latest({CODEX_HOME: '', HOME: directory}));
  failed(latest({}));
  const missing = join(directory, 'absent');
  failed(latest({PLUGIN_DATA: missing}));
  await assert.rejects(stat(missing), {code: 'ENOENT'});
}));

test('symlink roots and entries are not followed', {skip: process.platform === 'win32'}, () => fixture(async directory => {
  const data = join(directory, 'data');
  const expected = await record(data, 'valid');
  const alias = join(directory, 'alias');
  await symlink(data, alias);
  failed(latest({PLUGIN_DATA: alias}));
  await rm(expected);
  const other = join(directory, 'other');
  await mkdir(other);
  await symlink(other, expected);
  failed(latest({PLUGIN_DATA: data}));
  assert.deepEqual(await readdir(other), []);
}));
