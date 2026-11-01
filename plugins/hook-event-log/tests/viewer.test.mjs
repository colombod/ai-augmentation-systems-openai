import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  appendFileSync, chmodSync, linkSync, mkdirSync, mkdtempSync, readFileSync,
  realpathSync, rmSync, symlinkSync, truncateSync, writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import test from 'node:test';

const viewer = fileURLToPath(new URL('../dist/view-log.js', import.meta.url));
const failure = 'hook-event-log: session view incomplete\n';
const hash = createHash('sha256').update('synthetic-viewer-session').digest('hex');
const event = (name = 'Stop') => `${JSON.stringify({ event_type: name })}\n`;
const id = (number) => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
function fixture(t) {
  const root = mkdtempSync(join(realpathSync(tmpdir()), 'event-viewer-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  return root;
}
function legacy(root, bytes) {
  mkdirSync(join(root, 'event-types'), { recursive: true, mode: 0o700 });
  const path = join(root, 'event-types', `${hash}.jsonl`);
  writeFileSync(path, bytes, { mode: 0o600 });
  return path;
}
function fragment(root, number, bytes, name = 'record.jsonl') {
  const directory = join(root, 'event-types-v2', hash, id(number));
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const path = join(directory, name);
  writeFileSync(path, bytes, { mode: 0o600 });
  return path;
}
function view(root, args = ['--session', hash]) {
  return spawnSync(process.execPath, [viewer, ...args], {
    env: { ...process.env, PLUGIN_DATA: root }, encoding: 'utf8', timeout: 35000,
  });
}
function rejected(result) {
  assert.equal(result.status, 1, result.error?.message);
  assert.equal(result.stderr, failure);
}
function waitFor(predicate, timeout = 6000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      if (predicate()) return resolve();
      if (Date.now() - start >= timeout) return reject(new Error('Observation timed out'));
      setTimeout(check, 20);
    };
    check();
  });
}

test('viewer requires an explicit lowercase session hash and never creates missing roots', (t) => {
  const root = fixture(t);
  for (const args of [[], ['--session', '../other'], ['--session', hash.toUpperCase()], ['--session', hash, '--other']]) {
    const result = view(join(root, 'absent'), args);
    rejected(result);
    assert.equal(result.stdout, '');
  }
  rejected(view(join(root, 'absent')));
});

test('combined export preserves legacy bytes, repeats, and fixed fragment order', (t) => {
  const root = fixture(t);
  const original = event('SessionStart') + event('Stop') + event('Stop');
  const path = legacy(root, original);
  fragment(root, 20, event('Interrupt'));
  fragment(root, 10, event('SessionEnd'));
  fragment(root, 30, '{"event_type":', 'pending');
  const result = view(root);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, original + event('SessionEnd') + event('Interrupt'));
  assert.equal(result.stderr, '');
  assert.equal(readFileSync(path, 'utf8'), original);
});

test('follow observes both generations, completes a partial legacy line and keeps repeats', async (t) => {
  const root = fixture(t);
  const path = legacy(root, event('SessionStart'));
  fragment(root, 1, event('Stop'));
  const child = spawn(process.execPath, [viewer, '--session', hash, '--follow'], {
    env: { ...process.env, PLUGIN_DATA: root }, stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(() => child.kill('SIGKILL'));
  let stdout = '', stderr = '';
  child.stdout.on('data', (data) => { stdout += data; });
  child.stderr.on('data', (data) => { stderr += data; });
  await waitFor(() => stdout === event('SessionStart') + event('Stop'));
  appendFileSync(path, '{"event_type":"Inter');
  fragment(root, 2, event('Stop'));
  await waitFor(() => stdout.split('\n').length === 4);
  assert.equal(stdout, event('SessionStart') + event('Stop') + event('Stop'));
  appendFileSync(path, 'rupt"}\n');
  await waitFor(() => stdout.endsWith(event('Interrupt')));
  assert.equal(stderr, '');
  child.kill('SIGTERM');
  await new Promise((resolve) => child.once('close', resolve));
  const restart = view(root);
  assert.equal(restart.status, 0);
  assert.equal(restart.stdout, event('SessionStart') + event('Interrupt') + event('Stop') + event('Stop'));
});

test('malformed or unallowlisted published content never leaks', (t) => {
  for (const bytes of ['{"event_type":"Stop","secret":"SYNTHETIC_SECRET"}\n', 'not-json\n', event() + event(), '{"event_type":"Stop"}']) {
    const root = fixture(t);
    fragment(root, 1, bytes);
    const result = view(root);
    rejected(result);
    assert.equal(result.stdout, '');
    assert.ok(!result.stderr.includes('SYNTHETIC_SECRET'));
  }
});

test('legacy malformed or unallowlisted content is rejected before emission', (t) => {
  const root = fixture(t);
  legacy(root, '{"event_type":"Stop","extra":"SYNTHETIC_PRIVATE"}\n');
  const result = view(root);
  rejected(result);
  assert.equal(result.stdout, '');
});

test('fragment byte limit accepts exact boundary and rejects one byte over', (t) => {
  const root = fixture(t);
  const line = event();
  const path = fragment(root, 1, ' '.repeat(65536 - Buffer.byteLength(line)) + line);
  const exact = view(root);
  assert.equal(exact.status, 0, exact.stderr);
  assert.equal(exact.stdout, event());
  writeFileSync(path, ' ' + readFileSync(path, 'utf8'));
  rejected(view(root));
});

test('oversized legacy files and incomplete tails fail visibly', (t) => {
  const root = fixture(t);
  const path = legacy(root, '');
  truncateSync(path, 64 * 1024 * 1024 + 1);
  rejected(view(root));
  writeFileSync(path, ' '.repeat(65537));
  rejected(view(root));
});

test('entry budget includes unpublished directories and rejects one over', (t) => {
  const root = fixture(t);
  fragment(root, 0, event());
  const sessionRoot = join(root, 'event-types-v2', hash);
  for (let i = 1; i < 10000; i++) mkdirSync(join(sessionRoot, id(i)), { mode: 0o700 });
  const exact = view(root);
  assert.equal(exact.status, 0, exact.stderr);
  assert.equal(exact.stdout, event());
  mkdirSync(join(sessionRoot, id(10000)), { mode: 0o700 });
  rejected(view(root));
});

test('unsafe fragment files, directories, hardlinks and modes are refused', (t) => {
  for (const unsafe of ['symlink-file', 'hardlink-file', 'mode-file', 'symlink-directory', 'mode-directory']) {
    const root = fixture(t);
    const path = fragment(root, 1, event());
    const outside = join(root, 'outside');
    writeFileSync(outside, 'SYNTHETIC_SENTINEL', { mode: 0o600 });
    if (unsafe === 'symlink-file') { rmSync(path); symlinkSync(outside, path); }
    if (unsafe === 'hardlink-file') linkSync(path, join(root, 'alias'));
    if (unsafe === 'mode-file') chmodSync(path, 0o644);
    if (unsafe === 'symlink-directory') {
      const directory = join(root, 'event-types-v2', hash, id(1));
      rmSync(directory, { recursive: true });
      symlinkSync(root, directory);
    }
    if (unsafe === 'mode-directory') chmodSync(join(root, 'event-types-v2', hash, id(1)), 0o755);
    rejected(view(root));
    assert.equal(readFileSync(outside, 'utf8'), 'SYNTHETIC_SENTINEL');
  }
});

test('follow fails on legacy replacement instead of replaying or skipping silently', async (t) => {
  const root = fixture(t);
  const path = legacy(root, event());
  const child = spawn(process.execPath, [viewer, '--session', hash, '--follow'], {
    env: { ...process.env, PLUGIN_DATA: root }, stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(() => child.kill('SIGKILL'));
  let stdout = '', stderr = '';
  child.stdout.on('data', (data) => { stdout += data; });
  child.stderr.on('data', (data) => { stderr += data; });
  await waitFor(() => stdout === event());
  truncateSync(path, 0);
  const code = await new Promise((resolve) => child.once('close', resolve));
  assert.equal(code, 1);
  assert.equal(stderr, failure);
  assert.equal(stdout, event());
});

test('follow supervisor bounds a stalled output consumer', async (t) => {
  const root = fixture(t);
  const path = legacy(root, event());
  const child = spawn(process.execPath, [viewer, '--session', hash, '--follow'], {
    env: { ...process.env, PLUGIN_DATA: root }, stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(() => child.kill('SIGKILL'));
  const closed = new Promise((resolve) => child.once('close', resolve));
  let stdout = '', stderr = '', exit;
  child.stdout.on('data', (data) => { stdout += data; });
  child.stderr.on('data', (data) => { stderr += data; });
  child.once('exit', (code) => { exit = code; });
  await waitFor(() => stdout === event());
  child.stdout.pause();
  const large = `${JSON.stringify({ event_type: 'SubagentStop', agent_id: 'i'.repeat(1024),
    agent_type: 't'.repeat(256), agent_transcript_path: '/' + 'p'.repeat(4095) })}\n`;
  const start = Date.now();
  appendFileSync(path, large.repeat(1000));
  await waitFor(() => exit !== undefined, 6500);
  assert.equal(exit, 1);
  assert.ok(Date.now() - start >= 2300, 'must exercise the rescan watchdog');
  assert.ok(Date.now() - start < 6500, 'stalled consumer must not hold the process indefinitely');
  child.stdout.resume();
  await closed;
  assert.equal(stderr, failure);
});

 test('viewer emits validated values rather than overwritten duplicate-key bytes', (t) => {
  const root = fixture(t);
  const path = legacy(root, '{"event_type":"SYNTHETIC_SECRET","event_type":"Stop"}\n');
  const before = readFileSync(path);
  fragment(root, 1, '{"event_type":"SYNTHETIC_SECRET","event_type":"SessionEnd"}\n');
  const result = view(root);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, event('Stop') + event('SessionEnd'));
  assert.deepEqual(readFileSync(path), before);
 });

test('viewer retains the session directory inode while an event moves out of its removed parent', async (t) => {
  const root = fixture(t);
  fragment(root, 1, event());
  const sessionRoot = join(root, 'event-types-v2', hash);
  const alternate = join(root, 'alternate');
  mkdirSync(alternate, { mode: 0o700 });
  const probe = join(root, 'probe.json');
  const worker = fileURLToPath(new URL('../dist/view-worker.js', import.meta.url));
  const script = `
    import fs from 'node:fs';
    import {syncBuiltinESMExports} from 'node:module';
    const originalOpen = fs.openSync, originalClose = fs.closeSync, originalChdir = process.chdir;
    const expected = fs.statSync(${JSON.stringify(sessionRoot)}, {bigint:true});
    const live = new Set();
    fs.openSync = (...args) => { const fd = originalOpen(...args); live.add(fd); return fd; };
    fs.closeSync = (fd) => { live.delete(fd); return originalClose(fd); };
    let changed = false;
    process.chdir = (name) => {
      originalChdir(name);
      if (name !== ${JSON.stringify(id(1))} || changed) return;
      changed = true;
      const matches = [...live].filter(fd => {
        const stat=fs.fstatSync(fd,{bigint:true});
        return stat.dev===expected.dev && stat.ino===expected.ino;
      });
      fs.renameSync(${JSON.stringify(join(sessionRoot, id(1)))}, ${JSON.stringify(join(alternate, id(1)))});
      fs.rmdirSync(${JSON.stringify(sessionRoot)});
      const retained = matches.length > 0 && fs.fstatSync(matches[0], {bigint:true}).ino===expected.ino;
      fs.writeFileSync(${JSON.stringify(probe)}, JSON.stringify({pinned: matches.length > 0, retainedAfterRemoval: retained}));
    };
    syncBuiltinESMExports();
    process.argv=[process.execPath,${JSON.stringify(worker)},${JSON.stringify(hash)}];
    await import(${JSON.stringify(pathToFileURL(worker).href)});
  `;
  const child = spawn(process.execPath, ['--input-type=module', '-e', script], {
    env: { ...process.env, PLUGIN_DATA: root }, stdio: ['pipe', 'ignore', 'pipe', 'ipc'],
  });
  t.after(() => child.kill('SIGKILL'));
  const closed = new Promise((resolve) => child.once('close', resolve));
  const lines = [];
  child.on('message', (message) => {
    if (message.type === 'record') { lines.push(message.line); child.send({type:'ack'}); }
  });
  child.stdin.end(JSON.stringify({legacy:null,seen:[]}));
  assert.equal(await closed, 1, 'moving the event under another parent must make the return fail');
  assert.deepEqual(JSON.parse(readFileSync(probe, 'utf8')), {pinned:true,retainedAfterRemoval:true});
  assert.deepEqual(lines, [event()], 'only the already pinned event may be emitted before the failed return');
});
