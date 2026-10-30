"""Optional in-process host boundary; no network transport or model tool.

Only trusted host code may construct Bridge after authenticating its caller.
The principal argument is a host assertion, never an agent-provided field.
Local Python/file access to the coordinator is already a trusted capability.
This module alone does not authenticate a ChatGPT dot or install an integration.
"""
import json
import re
import time
import uuid

from delivery_gates import GateService, digest


class SupervisionError(ValueError):
    pass


def initialize(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS supervisor_requests(
        request_id TEXT PRIMARY KEY, payload TEXT NOT NULL, assignment TEXT UNIQUE NOT NULL,
        task_seal TEXT NOT NULL, thread TEXT, turn TEXT, terminal_event INTEGER, binding TEXT)''')
    if 'binding' not in {r[1] for r in store.db.execute('PRAGMA table_info(supervisor_requests)')}:
        store.db.execute('ALTER TABLE supervisor_requests ADD COLUMN binding TEXT')


def configuration(store):
    row = store.db.execute("SELECT value FROM settings WHERE key='supervision'").fetchone()
    return json.loads(row['value']) if row else None


def configure(store, value):
    """Called only by trusted local prepare, within its transaction."""
    if value is None:
        return  # Ordinary prepare never silently revokes an existing binding.
    if not isinstance(value, dict) or set(value) != {'principal', 'environment', 'tasks'}:
        raise SupervisionError('Supervision requires principal, environment and task-to-initiative bindings')
    for key in ('principal', 'environment'):
        if not isinstance(value[key], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value[key]):
            raise SupervisionError('Invalid supervision identity')
    if not isinstance(value['tasks'], dict) or not value['tasks']:
        raise SupervisionError('Explicit task scope required')
    for task, initiative in value['tasks'].items():
        if any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', x)
               for x in (task, initiative)):
            raise SupervisionError('Invalid task or initiative scope')
    current = configuration(store)
    if current and {k:v for k,v in current.items() if k != 'binding_id'} != value:
        raise SupervisionError('Existing supervisor binding cannot be silently replaced; use explicit native fallback first')
    if current:
        return
    require_quiescent(store)
    # Admission always targets the existing dispatcher, never a second executor.
    if not store.db.execute("SELECT 1 FROM roles WHERE name='coordinator'").fetchone():
        raise SupervisionError('Native coordinator required')
    binding = {**value, 'binding_id':str(uuid.uuid4())}
    store.db.execute("INSERT OR REPLACE INTO settings VALUES('supervision',?)", (json.dumps(binding, sort_keys=True),))
    store.event('supervision_configured', binding)


def revision(store):
    # Include mutable rows, not just an event counter: native phase changes also
    # happen without events. Beads criteria/dependencies have a separate seal.
    return digest({table: [dict(r) for r in store.db.execute('SELECT * FROM '+table+' ORDER BY 1')]
                   for table in ('roles', 'queue', 'controls', 'pending', 'settings', 'events', 'supervisor_requests')})


class Bridge:
    def __init__(self, store, *, authenticated_principal, environment, beads=None):
        self.store = store
        self.binding = configuration(store)
        if not self.binding or (authenticated_principal, environment) != (
                self.binding['principal'], self.binding['environment']):
            raise SupervisionError('Host identity/environment does not match configured supervisor')
        self.gates = GateService(store, beads)

    def check_binding(self):
        if configuration(self.store) != self.binding:
            raise SupervisionError('Supervisor binding revoked or changed')

    def snapshot(self, task):
        self.check_binding()
        if task not in self.binding['tasks']:
            raise SupervisionError('Task outside configured supervisor scope')
        _, seal = self.gates.snapshot(task)
        return {'project': str(self.store.project), 'environment': self.binding['environment'],
                'initiative': self.binding['tasks'][task], 'task': task,
                'expected_revision': revision(self.store), 'task_revision': seal}

    def submit(self, request):
        fields = {'request_id', 'task', 'initiative', 'recipient', 'message', 'expected_revision', 'task_revision'}
        if not isinstance(request, dict) or set(request) != fields or any(not isinstance(v, str) for v in request.values()):
            raise SupervisionError('Exact assignment fields required; no actor, policy or approval fields')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', request['request_id']):
            raise SupervisionError('Stable caller request ID required')
        if not request['message'].strip() or len(request['message']) > 64000:
            raise SupervisionError('Message must contain 1–64000 characters')
        encoded = json.dumps(request, sort_keys=True)
        with self.store.transaction():
            self.check_binding()
            previous = self.store.db.execute('SELECT * FROM supervisor_requests WHERE request_id=?', (request['request_id'],)).fetchone()
            if previous:
                if previous['binding'] != self.binding['binding_id']:
                    raise SupervisionError('Request ID belongs to another supervisor binding')
                if previous['payload'] != encoded:
                    raise SupervisionError('Request ID already used with different payload')
                return self.receipt(request['request_id'])
            if request['recipient'] != 'coordinator' or not self.store.db.execute("SELECT 1 FROM roles WHERE name='coordinator'").fetchone():
                raise SupervisionError('Only the bound native coordinator may receive supervisor assignments')
            if self.store.db.execute("SELECT 1 FROM queue WHERE state='unknown'").fetchone():
                raise SupervisionError('Uncertain assignments require explicit investigation before new supervision work')
            if self.binding['tasks'].get(request['task']) != request['initiative']:
                raise SupervisionError('Task/initiative outside configured supervisor scope')
            if request['expected_revision'] != revision(self.store):
                raise SupervisionError('Stale runtime revision; read current state before a new request')
            _, seal = self.gates.snapshot(request['task'])
            if seal != request['task_revision']:
                raise SupervisionError('Stale canonical task evidence')
            ident = str(uuid.uuid4())
            self.store.db.execute("INSERT INTO queue(id,role,message,state,created,source) VALUES(?,?,?,'queued',?,?)",
                (ident, 'coordinator', request['message'], time.time(), 'agent:'+self.binding['principal']))
            self.store.db.execute('INSERT INTO supervisor_requests VALUES(?,?,?,?,NULL,NULL,NULL,?)',
                (request['request_id'], encoded, ident, seal,self.binding['binding_id']))
            self.store.event('supervisor_admitted', {'request_id':request['request_id'], 'assignment':ident,
                'principal': self.binding['principal'], 'environment':self.binding['environment'],
                'task':request['task'], 'initiative':request['initiative'], 'human_authority':False})
            return self.receipt(request['request_id'])

    def receipt(self, request_id):
        self.check_binding()
        row = self.store.db.execute('''SELECT s.*,q.state,r.phase FROM supervisor_requests s
            JOIN queue q ON q.id=s.assignment JOIN roles r ON r.name=q.role WHERE request_id=?''', (request_id,)).fetchone()
        if not row or row['binding'] != self.binding['binding_id']:
            raise SupervisionError('Unknown request; absence is not evidence of an external effect')
        request = json.loads(row['payload'])
        evidence = []
        if row['terminal_event'] is not None:
            for event in self.store.db.execute('SELECT id,kind,data FROM events WHERE id<=? ORDER BY id', (row['terminal_event'],)):
                data = json.loads(event['data'])
                native = data.get('native', {})
                if ((data.get('thread') == row['thread'] and data.get('turn') == row['turn']) or
                        (native.get('threadId') == row['thread'] and native.get('turnId') == row['turn']) or
                        event['id'] == row['terminal_event']):
                    evidence.append({'event_id':event['id'], 'kind':event['kind']})
        return {'request_id':request_id, 'assignment_id':row['assignment'], 'task':request['task'],
                'initiative':request['initiative'], 'state':row['state'], 'role_phase':row['phase'], 'thread':row['thread'], 'turn':row['turn'],
                'terminal_event':row['terminal_event'], 'evidence':evidence,
                'human_authority':False, 'accepted':False}


def validate_dispatch(store, assignment):
    row = store.db.execute('SELECT * FROM supervisor_requests WHERE assignment=?', (assignment,)).fetchone()
    if row:
        request = json.loads(row['payload'])
        if store.db.execute("SELECT 1 FROM queue WHERE state='unknown'").fetchone():
            raise SupervisionError('Uncertain assignment blocks further supervisor dispatch')
        if not configuration(store) or configuration(store)['binding_id'] != row['binding']:
            raise SupervisionError('Supervisor assignment requires explicit reconciliation after fallback')
        _, seal = GateService(store).snapshot(request['task'])
        if seal != row['task_seal']:
            raise SupervisionError('Canonical task changed after admission; assignment requires reconciliation')


def assignment_context(store, assignment):
    row = store.db.execute('SELECT request_id,payload FROM supervisor_requests WHERE assignment=?', (assignment,)).fetchone()
    if not row:
        return ''
    request = json.loads(row['payload'])
    return '[Bound supervisor scope: '+json.dumps({k:request[k] for k in ('request_id','task','initiative')}, sort_keys=True)+']\n'


def require_quiescent(store):
    if store.db.execute("SELECT 1 FROM queue WHERE state NOT IN ('idle','cancelled','failed','interrupted')").fetchone() or store.db.execute(
            "SELECT 1 FROM roles WHERE phase NOT IN ('idle','prepared')").fetchone():
        raise SupervisionError('Reconcile outstanding jobs/roles before supervision handover')


def fallback(store, reason):
    """Trusted local control, with serve.lock held and no ambiguous jobs."""
    if not isinstance(reason, str) or not reason.strip():
        raise SupervisionError('Explicit fallback reason required')
    with store.transaction():
        require_quiescent(store)
        store.db.execute("DELETE FROM settings WHERE key='supervision'")
        store.event('supervision_native_fallback', {'reason':reason})


def cancel(store, request_id, reason):
    if not isinstance(reason, str) or not reason.strip():
        raise SupervisionError('Explicit cancellation reason required')
    with store.transaction():
        row = store.db.execute('SELECT assignment FROM supervisor_requests WHERE request_id=?', (request_id,)).fetchone()
        if not row or store.db.execute("UPDATE queue SET state='cancelled' WHERE id=? AND state IN ('queued','blocked')",
                (row['assignment'],)).rowcount != 1:
            raise SupervisionError('Only undispatched assignments can be cancelled; reconcile uncertain effects first')
        store.event('supervisor_assignment_cancelled', {'request_id':request_id,'reason':reason})
