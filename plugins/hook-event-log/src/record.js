import { createHash } from 'node:crypto';

export const LIMIT = 1_048_576;
export const EVENTS = Object.freeze(['SessionStart', 'SessionEnd', 'UserPromptSubmit', 'PreToolUse',
  'PostToolUse', 'PermissionRequest', 'SubagentStart', 'SubagentStop', 'PreCompact', 'PostCompact', 'Stop', 'Interrupt']);
const decoder = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });
const blank = value => /^[\p{White_Space}]*$/u.test(value);
function scalarString(value) {
  for (let i = 0; i < value.length; i++) {
    const unit = value.charCodeAt(i);
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = value.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) throw new Error();
    } else if (unit >= 0xdc00 && unit <= 0xdfff) throw new Error();
  }
}

export function parseJSONStrict(input) {
  if (!Buffer.isBuffer(input) || input.length > LIMIT) throw new Error();
  const text = decoder.decode(input);
  // Validate every token, including values hidden by a later duplicate object key.
  let depth = 0;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (char === '"') {
      const start = i++;
      for (; i < text.length; i++) {
        if (text[i] === '\\') { i++; continue; }
        if (text[i] === '"') break;
      }
      scalarString(JSON.parse(text.slice(start, i + 1)));
    } else if (char === '[' || char === '{') {
      if (++depth >= 128) throw new Error();
    } else if (char === ']' || char === '}') depth--;
    else if (char === '-' || (char >= '0' && char <= '9')) {
      const start = i;
      while (i + 1 < text.length && /[0-9eE+.-]/.test(text[i + 1])) i++;
      if (!Number.isFinite(Number(text.slice(start, i + 1)))) throw new Error();
    }
  }
  return JSON.parse(text);
}

function metadata(value, maxBytes) {
  return typeof value === 'string' && !blank(value) && Buffer.byteLength(value) <= maxBytes && !/\p{Cc}/u.test(value);
}

export function validateRecord(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !EVENTS.includes(value.event_type)) return false;
  const subagent = ['SubagentStart', 'SubagentStop'].includes(value.event_type);
  for (const [key, field] of Object.entries(value)) {
    if (key === 'event_type') continue;
    if (!subagent) return false;
    if (key === 'agent_id' && metadata(field, 1024)) continue;
    if (key === 'agent_type' && metadata(field, 256)) continue;
    if (key === 'agent_transcript_path' && value.event_type === 'SubagentStop' && metadata(field, 4096) && field.startsWith('/')) continue;
    return false;
  }
  return true;
}

export function parseEvent(input) {
  const value = parseJSONStrict(input);
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
  const event = value.hook_event_name;
  const session = value.session_id;
  if (!EVENTS.includes(event) || typeof session !== 'string' || blank(session) || Buffer.byteLength(session) > 1024) throw new Error();
  const record = { event_type: event };
  if (event === 'SubagentStart' || event === 'SubagentStop') {
    if (metadata(value.agent_id, 1024)) record.agent_id = value.agent_id;
    if (metadata(value.agent_type, 256)) record.agent_type = value.agent_type;
    if (event === 'SubagentStop' && metadata(value.agent_transcript_path, 4096) && value.agent_transcript_path.startsWith('/')) record.agent_transcript_path = value.agent_transcript_path;
  }
  const ordered = Object.fromEntries(Object.entries(record).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
  return {
    sessionHash: createHash('sha256').update(session, 'utf8').digest('hex'), record: ordered,
    bytes: Buffer.from(`${JSON.stringify(ordered)}\n`),
  };
}
