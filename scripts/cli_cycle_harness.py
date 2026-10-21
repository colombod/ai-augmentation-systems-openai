"""Evidence-only helpers for the maintainer's real CLI cycle, never installed.

All queue/database input is a read-only snapshot from the running public CLI.
These helpers infer no human authority and never launch a model or mutate tasks.
"""
import json
import re
import signal
import subprocess
import time
import uuid
from pathlib import Path


class HarnessFailure(RuntimeError):
    pass


def new_attempt(evidence_root):
    path = Path(evidence_root)/'attempts'/(time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+'-'+uuid.uuid4().hex)
    path.mkdir(parents=True, exist_ok=False)
    return path


def _message_turns(events, role, ident):
    pattern = re.compile(r'^\[(?:Operator-assigned work|Untrusted peer context from [^\]\n]+); queued message '+re.escape(ident)+r'\]\n')
    found = {}
    for event in events:
        data = event.get('data', {})
        native = data.get('native', {})
        item = native.get('item', {})
        if event.get('kind') != 'item/completed' or data.get('role') != role or item.get('type') != 'userMessage':
            continue
        content = item.get('content', [])
        if any(isinstance(c, dict) and isinstance(c.get('text'), str) and pattern.match(c['text']) for c in content):
            key = (native.get('threadId'), native.get('turnId'))
            if not all(isinstance(x, str) and x for x in key):
                raise HarnessFailure('Native queued message lacks thread/turn identity')
            found.setdefault(key, []).append(event['id'])
    if len(found) > 1:
        raise HarnessFailure('One queued message was observed in multiple native turns')
    return found


def message_completion(roles, queues, events, role, message_id):
    """Return exact native completion proof, or None while legitimately pending."""
    if not isinstance(message_id, str) or not message_id:
        raise HarnessFailure('An exact queued message ID is required')
    rows = [q for q in queues if q.get('id') == message_id]
    if not rows:
        return None
    if len(rows) != 1 or rows[0].get('role') != role:
        raise HarnessFailure('Ambiguous or wrong-role queue binding')
    job = rows[0]
    current = next((r for r in roles if r.get('name') == role), None)
    if current is None:
        raise HarnessFailure('Bound role disappeared')
    if job.get('state') not in ('queued', 'started', 'idle') or current.get('phase') in ('needs-reconciliation', 'unavailable'):
        raise HarnessFailure('Exact native job failed or requires reconciliation')
    turns = _message_turns(events, role, message_id)
    if not turns:
        return None
    (thread, turn), message_events = next(iter(turns.items()))
    if current.get('thread') != thread:
        raise HarnessFailure('Queued work moved to another native thread')
    intents = [e for e in events if e.get('kind') == 'turn_intent' and e.get('data', {}).get('message_id') == message_id and e['data'].get('role') == role]
    if not intents:
        return None
    terminals = [e for e in events if e.get('kind') == 'turn_terminal' and e.get('data', {}).get('role') == role and
                 e['data'].get('native', {}).get('threadId') == thread and
                 e['data']['native'].get('turn', {}).get('id') == turn]
    if not terminals:
        return None
    if any(e['data']['native']['turn'].get('status') != 'completed' for e in terminals):
        raise HarnessFailure('Exact native turn did not complete successfully')
    terminal = terminals[-1]
    if min(message_events) <= intents[0]['id'] or terminal['id'] <= min(message_events):
        raise HarnessFailure('Inconsistent native request/terminal event ordering')
    if job['state'] != 'idle' or current.get('phase') != 'idle':
        return None
    return {'role': role, 'message_id': message_id, 'native_thread': thread, 'native_turn': turn,
            'intent_event': intents[0]['id'], 'user_message_events': message_events,
            'terminal_event': terminal['id'], 'queue_state': job['state']}


def peer_handoff(queues, events, sender, sender_message_id, recipient, sender_complete=False):
    turns = _message_turns(events, sender, sender_message_id)
    found = set()
    if turns:
        thread, turn = next(iter(turns))
        for e in events:
            d = e.get('data', {})
            if (e.get('kind') != 'controlled_tool_result' or d.get('tool') != 'delivery_send' or
                    (d.get('role'), d.get('thread'), d.get('turn')) != (sender, thread, turn)):
                continue
            response = d.get('result', {})
            if not response.get('success'):
                raise HarnessFailure('Native peer handoff failed')
            try:
                ident = json.loads(response['contentItems'][0]['text'])['queued_message_id']
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise HarnessFailure('Malformed native peer handoff result') from error
            if any(q.get('id') == ident and q.get('role') == recipient and q.get('source') == 'peer:'+sender for q in queues):
                found.add(ident)
    if len(found) > 1:
        raise HarnessFailure('Ambiguous duplicate peer assignments')
    if found:
        return next(iter(found))
    if sender_complete:
        raise HarnessFailure('Completed sender never handed off the required peer assignment')
    return None


def scoped_tool_results(events, tool, proof):
    results = []
    for e in events:
        d = e.get('data', {})
        if (e.get('kind') != 'controlled_tool_result' or d.get('tool') != tool or
                (d.get('role'), d.get('thread'), d.get('turn')) !=
                (proof['role'], proof['native_thread'], proof['native_turn'])):
            continue
        raw = d.get('result', {})
        try:
            value = json.loads(raw['contentItems'][0]['text']) if raw.get('success') else None
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise HarnessFailure('Malformed controlled tool result') from error
        results.append((d, value))
    return results


def successful_tool(events, tool, proof):
    results = [value for _, value in scoped_tool_results(events, tool, proof) if isinstance(value, dict)]
    if not results:
        raise HarnessFailure('No successful exact-turn native tool call: '+tool)
    return results[-1]


def judge_fixture(catalogue_path):
    catalogue = json.loads(Path(catalogue_path).read_text())
    required = catalogue['questions']['is_fix']['state']
    state = {'candidate': 'Build a new deterministic ASCII-only slugify CLI from requirements',
             'linked_item': 'No shipped feature or security finding; this is a new synthetic fixture',
             'context': 'New local Python CLI implementation, not repair of existing shipped work'}
    if set(required) != set(state):
        raise HarnessFailure('Judge fixture no longer matches the actual is_fix catalogue')
    return state


def answered_judge(events, proof, provider, model):
    results = scoped_tool_results(events, 'delivery_judge', proof)
    if len(results) != 1:
        raise HarnessFailure('Expected exactly one first-call judge result, without corrective retries')
    _, result = results[0]
    if (not isinstance(result, dict) or result.get('skipped') or result.get('error') or
            result.get('provider') != provider or result.get('model') != model or result.get('question') != 'is_fix' or
            result.get('answer') not in ('yes', 'no') or result.get('type') != 'noul' or
            result.get('human_authority') is not False or result.get('advisory') is not True):
        raise HarnessFailure('Judge first call did not produce an actual selected-provider advisory answer')
    probability = result.get('p')
    if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not 0 <= probability <= 1:
        raise HarnessFailure('Judge probability is outside the declared answer domain')
    return result


def exit_code(state):
    checks = state.get('checks')
    return 0 if (state.get('stage') == 'finished-through-human-barrier' and not state.get('error') and
                 not state.get('snapshot_error') and not state.get('cleanup_error') and
                 isinstance(checks, dict) and checks and all(v is True for v in checks.values())) else 1


def planned_stop(process, timeout=20):
    """An unexpected prior exit or forced cleanup never counts as normal stop."""
    previous = process.poll()
    if previous is not None:
        raise HarnessFailure('Supervisor exited before planned stop: '+str(previous))
    process.send_signal(signal.SIGINT)
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        raise HarnessFailure('Supervisor required forced cleanup after SIGINT timeout')
    if code not in (0, -signal.SIGINT):
        raise HarnessFailure('Supervisor failed during planned SIGINT stop: '+str(code))
    return {'pre_stop_exit_code': previous, 'signal_requested': 'SIGINT',
            'exit_code': code, 'forced_cleanup': False}
