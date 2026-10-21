import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, realpath, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const session = 'subagent-metadata-test-parent';
async function fixture(run) {
  const directory = await realpath(await mkdtemp(join(tmpdir(), 'subagent-links-')));
  try { return await run(directory); }
  finally { await rm(directory, {recursive: true, force: true}); }
}
function append(directory, event, fields) {
  const result = spawnSync(process.execPath, [join(root, 'dist/hook.js')], {
    input: JSON.stringify({session_id: session, hook_event_name: event,
      prompt: 'PRIVATE_CONTENT_SENTINEL', tool_input: 'PRIVATE_CONTENT_SENTINEL',
      last_assistant_message: 'PRIVATE_CONTENT_SENTINEL', ...fields}),
    env: {...process.env, PLUGIN_DATA: directory}, encoding: 'utf8', timeout: 4000,
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
  assert.equal(result.stderr, '');
}
async function rows(directory) {
  const name = createHash('sha256').update(session).digest('hex') + '.jsonl';
  const bytes = await readFile(join(directory, 'event-types', name), 'utf8');
  assert.ok(!bytes.includes('PRIVATE_CONTENT_SENTINEL'));
  return bytes.trim().split('\n').map(JSON.parse);
}

test('subagent lifecycle pairs correlate IDs; only stop includes the host transcript path', () => fixture(async directory => {
  const fields = {agent_id: 'child-42', agent_type: 'reviewer',
    agent_transcript_path: '/private/tmp/a-native-transcript-that-does-not-exist.jsonl'};
  append(directory, 'SubagentStart', fields);
  append(directory, 'SubagentStop', fields);
  assert.deepEqual(await rows(directory), [
    {event_type: 'SubagentStart', agent_id: fields.agent_id, agent_type: fields.agent_type},
    {event_type: 'SubagentStop', ...fields},
  ]);
}));

test('non-subagent events ignore metadata and existing one-key rows stay readable', () => fixture(async directory => {
  append(directory, 'SubagentStart', {});
  append(directory, 'PostToolUse', {agent_id: 'child', agent_type: 'worker',
    agent_transcript_path: '/private/tmp/not-to-log'});
  append(directory, 'SubagentStop', {agent_id: 'child'});
  assert.deepEqual(await rows(directory), [{event_type: 'SubagentStart'},
    {event_type: 'PostToolUse'}, {event_type: 'SubagentStop', agent_id: 'child'}]);
}));

test('invalid optional metadata is omitted without losing lifecycle records', () => fixture(async directory => {
  for (const fields of [
    {agent_id: null, agent_type: 123, agent_transcript_path: null},
    {agent_id: '', agent_type: ' ', agent_transcript_path: 'relative.jsonl'},
    {agent_id: 'x'.repeat(1025), agent_type: 'x'.repeat(257), agent_transcript_path: '/' + 'x'.repeat(4096)},
    {agent_id: 'bad\nline', agent_type: 'bad\u0000type', agent_transcript_path: '/bad\npath'},
  ]) append(directory, 'SubagentStop', fields);
  assert.deepEqual(await rows(directory), Array.from({length: 4}, () => ({event_type: 'SubagentStop'})));
}));

test('JSON escaping preserves identifiers without injecting additional records', () => fixture(async directory => {
  const fields = {agent_id: 'child-"quoted"-\\-雪', agent_type: 'reviewer',
    agent_transcript_path: '/private/tmp/a "quoted" path.jsonl'};
  append(directory, 'SubagentStop', fields);
  assert.deepEqual(await rows(directory), [{event_type: 'SubagentStop', ...fields}]);
}));
