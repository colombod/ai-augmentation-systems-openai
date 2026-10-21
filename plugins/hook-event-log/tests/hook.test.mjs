import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, rm, readFile, readdir, mkdir, symlink, stat, cp, writeFile, realpath } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const events = ['SessionStart','SessionEnd','UserPromptSubmit','PreToolUse','PostToolUse','PermissionRequest','SubagentStart','SubagentStop','PreCompact','PostCompact','Stop','Interrupt'];
const failure = 'hook-event-log: event could not be recorded\n';
const session = 'session-sentinel-must-never-appear';
const filename = createHash('sha256').update(session).digest('hex') + '.jsonl';
const payload = (event = 'PreToolUse', extra = {}) => JSON.stringify({hook_event_name:event, session_id:session, prompt:'secret-sentinel', tool_input:{secret:'secret-sentinel'}, ...extra});
function invoke(data, directory, options = {}) {
  return new Promise((accept, reject) => {
    const env = {...process.env};
    delete env.PLUGIN_DATA;
    if (directory !== undefined) env.PLUGIN_DATA = directory;
    const child = spawn(process.execPath, [join(options.root ?? root, 'dist/hook.js')], {env, stdio:['pipe','pipe','pipe']});
    let stdout = '', stderr = '';
    const started = performance.now();
    child.stdout.on('data', b => stdout += b);
    child.stderr.on('data', b => stderr += b);
    child.stdin.on('error', () => {});
    child.on('error', reject);
    child.on('close', (code, signal) => accept({code,signal,stdout,stderr,ms:performance.now()-started}));
    if (!options.idle) child.stdin.end(data);
    const watchdog = setTimeout(() => {child.kill('SIGKILL'); reject(Error('Adapter exceeded test watchdog'));}, 5000);
    child.on('close', () => clearTimeout(watchdog));
  });
}
async function isolated(fn) {
  const directory = await realpath(await mkdtemp(join(tmpdir(), 'hook-event-log-test-')));
  try { return await fn(directory); } finally { await rm(directory, {recursive:true, force:true}); }
}
function success(result) { assert.equal(result.code,0); assert.equal(result.signal,null); assert.equal(result.stdout,''); assert.equal(result.stderr,''); }
function fails(result) { assert.equal(result.code,1); assert.equal(result.signal,null); assert.equal(result.stdout,''); assert.equal(result.stderr,failure); }

test('twelve registered event types produce only exact one-key records', () => isolated(async directory => {
  for (const event of events) success(await invoke(payload(event),directory));
  assert.deepEqual(await readdir(directory), ['event-types']);
  assert.deepEqual(await readdir(join(directory,'event-types')), [filename]);
  const output = await readFile(join(directory,'event-types',filename),'utf8');
  assert.deepEqual(output.trim().split('\n').map(JSON.parse),events.map(event_type => ({event_type})));
  assert.ok(!output.includes('sentinel'));
  if (process.platform !== 'win32') assert.equal((await stat(join(directory,'event-types',filename))).mode & 0o777,0o600);
}));
test('32 concurrent invocations append complete records', () => isolated(async directory => {
  (await Promise.all(Array.from({length:32},() => invoke(payload(),directory)))).forEach(success);
  assert.deepEqual((await readFile(join(directory,'event-types',filename),'utf8')).trim().split('\n').map(JSON.parse),Array.from({length:32},() => ({event_type:'PreToolUse'})));
}));
test('malformed, missing identifiers and unknown events create no log', () => isolated(async directory => {
  for (const data of ['{secret-sentinel', '[]', '{}', payload('Unknown'), payload('Stop',{session_id:''}), payload('Stop',{session_id:null})]) fails(await invoke(data,directory));
  assert.deepEqual(await readdir(directory),[]);
}));
test('absent and relative PLUGIN_DATA fail quietly', async () => {
  fails(await invoke(payload(),undefined));
  fails(await invoke(payload(),'relative-data-sentinel'));
});
test('exact 1 MiB input is accepted; 1 byte over is rejected', () => isolated(async directory => {
  const base = payload('Stop',{padding:''});
  const sized = payload('Stop',{padding:'x'.repeat(1024*1024-Buffer.byteLength(base))});
  assert.equal(Buffer.byteLength(sized),1024*1024);
  success(await invoke(sized,directory));
  fails(await invoke(sized+' ',directory));
  assert.equal((await readFile(join(directory,'event-types',filename),'utf8')).trim().split('\n').length,1);
}));
test('log target symlink is refused and destination unchanged', {skip:process.platform==='win32'}, () => isolated(async directory => {
  const destination = join(directory,'protected');
  await writeFile(destination,'protected-sentinel');
  await mkdir(join(directory,'event-types'));
  await symlink(destination,join(directory,'event-types',filename));
  fails(await invoke(payload(),directory));
  assert.equal(await readFile(destination,'utf8'),'protected-sentinel');
}));
test('idle stdin is terminated below configured hook timeout', () => isolated(async directory => {
  const result = await invoke('',directory,{idle:true});
  fails(result); assert.ok(result.ms<3000,`Idle runtime ${result.ms} ms`);
  assert.deepEqual(await readdir(directory),[]);
}));
test('missing binary fails with no content leak', () => isolated(async directory => {
  const fixture = join(directory,'fixture');
  await mkdir(join(fixture,'dist'),{recursive:true});
  await cp(join(root,'dist/hook.js'),join(fixture,'dist/hook.js'));
  await writeFile(join(fixture,'package.json'),'{"type":"module"}');
  fails(await invoke(payload(),join(directory,'data'),{root:fixture}));
}));
test('hung native child is killed within hook deadline', {skip:process.platform==='win32'}, () => isolated(async directory => {
  const fixture = join(directory,'fixture');
  await mkdir(join(fixture,'dist'),{recursive:true});
  await mkdir(join(fixture,'bin',`${process.platform}-${process.arch}`),{recursive:true});
  await cp(join(root,'dist/hook.js'),join(fixture,'dist/hook.js'));
  await writeFile(join(fixture,'package.json'),'{"type":"module"}');
  const binary=join(fixture,'bin',`${process.platform}-${process.arch}`,'event-log-core');
  await writeFile(binary,`#!${process.execPath}\nsetInterval(() => {}, 1000);\n`,{mode:0o755});
  const result = await invoke(payload(),join(directory,'data'),{root:fixture});
  fails(result); assert.ok(result.ms<3000,`Child runtime ${result.ms} ms`);
}));
test('hook registration matches implemented supported events', async () => {
  const config=JSON.parse(await readFile(join(root,'hooks/hooks.json'),'utf8'));
  assert.deepEqual(Object.keys(config.hooks).sort(),[...events].sort());
  for(const group of Object.values(config.hooks)) {
    assert.equal(group[0].hooks[0].timeout,3);
    assert.equal(group[0].hooks[0].command,'node "${PLUGIN_ROOT}/dist/hook.js"');
  }
});

test('compatibility manifest exposes hooks without conflicting portable root', async () => {
  const manifest=JSON.parse(await readFile(join(root,'.codex-plugin/plugin.json'),'utf8'));
  assert.equal(manifest.hooks,'./hooks/hooks.json');
  await assert.rejects(stat(join(root,'plugin.json')), {code:'ENOENT'});
});
