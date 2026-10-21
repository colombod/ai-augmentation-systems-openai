"""Controlled workflow evidence; Beads remains the sole task/dependency authority.

Local SQLite transactions serialize this coordinator only. Beads claim is atomic
for ownership, not a Git/criteria/dependency transaction. External CLI mutations
can race; coordinator acceptance is not a global Beads/Git transaction. Merge
is never performed or authorized here.
Evidence supplied by a model is a submission, not authenticated host observation.
A separately captured operator attestation can authorize coordinator-scoped close;
it does not verify an external identity or authorize merge/push.
"""
from contextlib import nullcontext
import hashlib
import json
import os
import stat
from pathlib import Path
import re
import subprocess
import time
import uuid

from operator_capture import CaptureAuthority


class GateError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def tool(name, fields, required):
    return {'type': 'function', 'name': 'delivery_'+name,
            'description': 'Controlled delivery '+name+'; no human authority or automatic merge.',
            'inputSchema': {'type': 'object', 'properties': fields, 'required': required, 'additionalProperties': False}}


STRING = {'type': 'string'}
TOOLS = [
    tool('task_materialize', {'path': STRING}, ['path']),
    tool('task_ready', {'issue': STRING, 'surfaces': {'type': 'array', 'items': {'type': 'object'}},
                        'assumptions': {'type': 'array', 'items': {'type': 'object'}}}, ['issue', 'surfaces', 'assumptions']),
    tool('task_reready', {'issue': STRING, 'surfaces': {'type': 'array', 'items': {'type': 'object'}},
                          'assumptions': {'type': 'array', 'items': {'type': 'object'}}, 'reason': STRING},
         ['issue', 'surfaces', 'assumptions', 'reason']),
    tool('task_claim', {'issue': STRING}, ['issue']),
    tool('task_implemented', {'issue': STRING, 'head': STRING, 'evidence': {'type': 'array', 'items': STRING},
                             'passed': {'type': 'boolean'}}, ['issue', 'head', 'evidence', 'passed']),
    tool('task_review', {'issue': STRING, 'head': STRING, 'evidence': {'type': 'array', 'items': STRING},
                        'approved': {'type': 'boolean'}}, ['issue', 'head', 'evidence', 'approved']),
    tool('task_surface', {'issue': STRING, 'head': STRING, 'surface': {'type': 'object'},
                         'evidence': {'type': 'array', 'items': STRING}, 'kind': STRING},
         ['issue', 'head', 'surface', 'evidence', 'kind']),
    tool('task_gate_status', {'issue': STRING}, ['issue']),
    tool('task_accept', {'issue': STRING}, ['issue']),
]
SCHEMAS = {t['name']: t['inputSchema'] for t in TOOLS}


class Beads:
    def __init__(self, project):
        self.project = project

    def run(self, args, actor=None, body=None):
        command = ['bd'] + args + ['--json', '--sandbox']
        if actor:
            command += ['--actor', actor]
        result = subprocess.run(command, cwd=self.project, text=True, capture_output=True, timeout=30, input=body)
        if result.returncode:
            raise GateError('Canonical Beads operation failed: '+result.stderr[:500])
        try:
            return json.loads(result.stdout)
        except ValueError as error:
            raise GateError('Malformed Beads response') from error

    def show(self, issue):
        value = self.run(['show', issue, '--readonly'])
        if not isinstance(value, list) or len(value) != 1 or value[0].get('id') != issue:
            raise GateError('Ambiguous canonical task')
        return value[0]

    def close(self, issue, actor, reason):
        self.run(['close', issue, '--reason', reason], actor=actor)

    def claim(self, issue, actor, operation):
        self.run(['update', issue, '--claim', '--append-notes', 'delivery-claim-op:'+operation], actor=actor)

    def find_source(self, key):
        return self.run(['list', '--all', '--limit', '0', '--metadata-field', 'delivery_source_key='+key, '--readonly'])

    def create_story(self, title, body, criteria, metadata, actor):
        return self.run(['create', '--title', title, '--type', 'task', '--acceptance', criteria,
                         '--body-file', '-', '--external-ref', 'delivery-story:'+metadata['delivery_source_key'],
                         '--metadata', json.dumps(metadata), '--labels', 'delivery-draft'], actor=actor, body=body)


class GateService:
    def __init__(self, store, beads=None):
        self.store, self.db = store, store.db
        self.beads = beads or Beads(store.project)

    def actor(self, identity):
        if not isinstance(identity, dict):
            raise GateError('Missing native actor binding')
        row = self.db.execute('SELECT * FROM roles WHERE name=?', (identity.get('role'),)).fetchone()
        if not row or row['phase'] != 'active' or not row['thread'] or not row['turn']:
            raise GateError('Inactive native actor')
        spec = json.loads(row['spec'])
        if any(identity.get(key) != value for key, value in
               [('thread', row['thread']), ('turn', row['turn']), ('lane', spec['lane'])]):
            raise GateError('Native actor binding mismatch')
        return {'role': row['name'], 'thread': row['thread'], 'turn': row['turn'],
                'lane': spec['lane'], 'cwd': spec['cwd']}

    def snapshot(self, issue):
        task = self.beads.show(issue)
        criteria = task.get('acceptance_criteria', '')
        if not isinstance(criteria, str) or not criteria.strip():
            raise GateError('Canonical acceptance criteria required')
        dependencies = []
        if not isinstance(task.get('dependencies', []), list):
            raise GateError('Malformed canonical dependencies')
        for dep in task.get('dependencies', []):
            if not isinstance(dep, dict) or not dep.get('id'):
                raise GateError('Malformed dependency entry')
            if dep.get('dependency_type') == 'blocks':
                current = self.beads.show(dep['id'])
                dependencies.append({'id': dep['id'], 'status': current.get('status'),
                                     'updated_at': current.get('updated_at')})
                if current.get('status') != 'closed':
                    raise GateError('Unresolved blocking dependency: '+dep['id'])
            elif dep.get('dependency_type') not in ('parent-child', 'related', 'discovered-from'):
                raise GateError('Unknown dependency semantics')
        if task.get('status') not in ('open', 'in_progress'):
            raise GateError('Task is not open for controlled work')
        return task, digest({'criteria': criteria, 'description': task.get('description'),
                             'dependencies': sorted(dependencies, key=lambda d: d['id'])})

    def events(self, issue):
        result = []
        for row in self.db.execute("SELECT data FROM events WHERE kind='delivery_gate' ORDER BY id"):
            item = json.loads(row['data'])
            if item.get('issue') == issue:
                result.append(item)
        return result

    def record(self, action, issue, actor, seal, **extra):
        value = dict(id=str(uuid.uuid4()), action=action, issue=issue, actor=actor, seal=seal, time=time.time(), **extra)
        self.store.event('delivery_gate', value)
        return value

    def artifact_event(self, path):
        for row in self.db.execute("SELECT id,data FROM events WHERE kind='artifact_saved' ORDER BY id DESC"):
            value = json.loads(row['data'])
            if value.get('path') == str(path):
                return row['id'], value
        return None, None

    def evidence(self, paths, actor):
        if not isinstance(paths, list) or not paths or len(paths) > 30:
            raise GateError('1–30 evidence files required')
        result = []
        root = Path(actor['cwd']).resolve()
        reviews = self.store.root.parent/'reviews'
        for name in paths:
            if not isinstance(name, str):
                raise GateError('Evidence path must be text')
            path = Path(name)
            if not path.is_absolute():
                path = root/path
            if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
                raise GateError('Evidence cannot traverse symlinks')
            path = path.resolve()
            protected = path.parent == reviews and path.suffix == '.md'
            if not path.is_relative_to(root) and not protected:
                raise GateError('Evidence must be inside actor root or a protected coordinator review artifact')
            if not path.is_file() or not 0 < path.stat().st_size <= 2_000_000:
                raise GateError('Missing, empty or oversized evidence')
            item = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            if protected:
                ident, event = self.artifact_event(path)
                expected = {key: actor[key] for key in ('role', 'thread')}
                actual = {key: event.get('actor', {}).get(key) for key in expected} if event else None
                if not event or actual != expected or not event.get('actor', {}).get('turn') or event.get('sha256') != item['sha256']:
                    raise GateError('Protected review evidence requires native author/thread artifact provenance')
                item['artifact_event_id'] = ident
                item['artifact_origin'] = event['actor']
            result.append(item)
        return result

    def verify_evidence(self, record):
        for item in record.get('evidence', []):
            path = Path(item['path'])
            if (not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents) or
                    hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']):
                raise GateError('Evidence changed or disappeared')
            if 'artifact_event_id' in item:
                ident, event = self.artifact_event(path)
                if ident != item['artifact_event_id'] or event.get('sha256') != item['sha256']:
                    raise GateError('Protected artifact provenance changed')

    def head(self, root):
        # Inspection must not execute a worker-editable fsmonitor helper as
        # the coordinator. This per-command setting changes no repository
        # configuration, commit hooks, native trust or worker permissions.
        git = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', '-C', root]
        result = subprocess.run(git+['rev-parse', '--verify', 'HEAD^{commit}'],
                                text=True, capture_output=True, timeout=10)
        if result.returncode or not re.fullmatch(r'[0-9a-f]{40,64}', result.stdout.strip()):
            raise GateError('Cannot resolve product commit')
        self.verify_tracked_bytes(git, root, result.stdout.strip())
        # Cached tree/index comparison never converts worktree bytes. Avoid
        # `git status`: index refresh can execute a repository clean filter.
        staged = subprocess.run(git+['diff-index', '--cached', '--quiet', '--no-ext-diff', '--no-textconv', result.stdout.strip(), '--'],
                                text=True, capture_output=True, timeout=10)
        if staged.returncode:
            raise GateError('Staged product changes are not committed or index inspection failed')
        untracked = subprocess.run(git+['ls-files', '--others', '--exclude-standard', '-z'],
                                   text=True, capture_output=True, timeout=10)
        if untracked.returncode:
            raise GateError('Cannot inspect untracked product files')
        for name in untracked.stdout.split('\0'):
            if name and not (name.startswith('.delivery-evidence/') and '..' not in Path(name).parts):
                raise GateError('Product changes are not committed; only .delivery-evidence/ outputs may be untracked')
        return result.stdout.strip()

    def verify_tracked_bytes(self, git, root, head):
        """Compare raw checkout bytes to HEAD, never trusting index stat caches.

        This intentionally refuses transformed clean-filter/CRLF checkouts and
        unverified gitlinks. No clean/smudge/textconv command is invoked by the
        coordinator. Such repositories need a separately reviewed safe adapter.
        """
        flags = subprocess.run(git+['ls-files', '-v', '-z'], capture_output=True, timeout=10)
        if flags.returncode:
            raise GateError('Cannot inspect product index flags')
        if any(entry[:1].islower() or entry.startswith(b'S ') for entry in flags.stdout.split(b'\0') if entry):
            raise GateError('Product index hides tracked bytes with assume-unchanged/skip-worktree')
        tree = subprocess.run(git+['ls-tree', '-rz', '--full-tree', head], capture_output=True, timeout=10)
        if tree.returncode:
            raise GateError('Cannot inspect committed product tree')
        for entry in tree.stdout.split(b'\0'):
            if not entry:
                continue
            try:
                header, name = entry.split(b'\t', 1)
                mode, kind, expected = header.split(b' ')
                relative = Path(os.fsdecode(name))
            except (ValueError, TypeError) as error:
                raise GateError('Malformed committed tree entry') from error
            if relative.is_absolute() or '..' in relative.parts:
                raise GateError('Unsafe committed tree path')
            path = Path(root)/relative
            if any(parent.is_symlink() for parent in path.parents):
                raise GateError('Tracked product parent became a symlink')
            if kind != b'blob' or mode not in (b'100644', b'100755', b'120000'):
                raise GateError('Unverified submodule or unsupported committed entry requires safe adapter')
            algorithm = hashlib.sha1 if len(expected) == 40 else hashlib.sha256
            if mode == b'120000':
                if not path.is_symlink():
                    raise GateError('Committed symlink type changed')
                payload = os.fsencode(os.readlink(path))
                observed = algorithm(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest().encode()
            else:
                try:
                    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(descriptor, 'rb') as stream:
                        before = os.fstat(stream.fileno())
                        if not stat.S_ISREG(before.st_mode) or bool(before.st_mode & 0o111) != (mode == b'100755'):
                            raise GateError('Committed product file type or executable mode changed')
                        hashed = algorithm(b'blob '+str(before.st_size).encode()+b'\0')
                        remaining = before.st_size
                        while remaining:
                            chunk = stream.read(min(1024*1024, remaining))
                            if not chunk:
                                raise GateError('Product file shortened during inspection')
                            hashed.update(chunk)
                            remaining -= len(chunk)
                        if stream.read(1):
                            raise GateError('Product file grew during inspection')
                        after = os.fstat(stream.fileno())
                        if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                                after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                            raise GateError('Product file changed during inspection')
                        observed = hashed.hexdigest().encode()
                except OSError as error:
                    raise GateError('Cannot safely read committed product bytes') from error
            if observed != expected:
                raise GateError('Product raw bytes differ from committed HEAD and are not committed; index/cache/filter claims are insufficient')

    def call(self, name, args, actor):
        if name not in SCHEMAS or not isinstance(args, dict):
            raise GateError('Unknown controlled gate')
        schema = SCHEMAS[name]
        if set(args) != set(schema['required']):
            raise GateError('Unexpected or missing gate fields')
        if name == 'delivery_task_materialize':
            return self.materialize(args['path'], actor)
        issue = args.get('issue')
        if not isinstance(issue, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', issue):
            raise GateError('Invalid issue identifier')
        with (nullcontext() if self.db.in_transaction else self.store.transaction()):
            actor = self.actor(actor)
            task, seal = self.snapshot(issue)
            action = name.removeprefix('delivery_task_')
            events = self.events(issue)
            finished = {e.get('operation') for e in events if e['action'] in ('claim', 'accepted', 'effect_reconciled')}
            pending = [e for e in events if e['action'] in ('claim_intent', 'accept_intent') and e['operation'] not in finished]
            if action in ('claim', 'accept') and pending:
                raise GateError('Unresolved Beads effect intent requires read-only/operator reconciliation; do not retry')
            if action in ('ready', 'reready'):
                if actor['role'] != 'delivery-manager' or actor['lane'] != 'read-only':
                    raise GateError('Readiness requires bound delivery manager')
                previous_claim = None
                if action == 'ready' and task.get('assignee'):
                    raise GateError('Assigned work requires explicit reready with reconciliation reason')
                if action == 'reready':
                    if not isinstance(args['reason'], str) or not args['reason'].strip():
                        raise GateError('Explicit rereadiness reconciliation reason required')
                    previous_claim = next((e for e in reversed(events) if e['action'] == 'claim'), None)
                    if not previous_claim or task.get('assignee') != previous_claim['actor']['role'] or task.get('status') != 'in_progress':
                        raise GateError('Rereadiness requires canonical existing controlled claim')
                    builder = self.db.execute('SELECT * FROM roles WHERE name=?', (task['assignee'],)).fetchone()
                    if not builder or builder['phase'] not in ('idle', 'prepared') or builder['thread'] != previous_claim['actor']['thread']:
                        raise GateError('Quiesce the bound builder before rereadiness')
                surfaces, assumptions = args['surfaces'], args['assumptions']
                if not isinstance(surfaces, list) or not surfaces or any(
                    not isinstance(s, dict) or set(s) != {'host', 'app', 'mode', 'criterion'} or
                    any(not isinstance(v, str) or not v.strip() for v in s.values()) for s in surfaces):
                    raise GateError('Declare host, app, mode and criterion for each required surface')
                criterion_lines = [re.sub(r'^(?:[-*+] |[0-9]+[.)] )', '', line.strip()).strip()
                                   for line in task['acceptance_criteria'].splitlines()
                                   if line.strip() and not line.lstrip().startswith('#')]
                if not criterion_lines or {s['criterion'] for s in surfaces} != set(criterion_lines):
                    raise GateError('Declare at least one surface for every exact canonical criterion line')
                if not isinstance(assumptions, list) or any(not isinstance(a, dict) or
                    set(a) != {'statement', 'evidence'} or not isinstance(a['statement'], str) or
                    not a['statement'].strip() for a in assumptions):
                    raise GateError('Every assumption requires statement and evidence')
                assumptions = [{'statement': a['statement'], 'evidence': self.evidence(a['evidence'], actor)} for a in assumptions]
                readiness = self.record('ready', issue, actor, seal, readiness=str(uuid.uuid4()),
                                        surfaces=surfaces, assumptions=assumptions,
                                        reason=args.get('reason', 'initial readiness'))
                if previous_claim:
                    self.record('claim', issue, previous_claim['actor'], seal, readiness=readiness['readiness'],
                                reconciled_by=actor, reason=args['reason'])
                return readiness
            ready = next((e for e in reversed(events) if e['action'] == 'ready'), None)
            if not ready or ready['seal'] != seal:
                raise GateError('Readiness missing or stale after criteria/dependency change')
            for assumption in ready['assumptions']:
                self.verify_evidence(assumption)
            active = [e for e in events if e.get('readiness') == ready['readiness'] and e['seal'] == seal]
            claim = next((e for e in reversed(active) if e['action'] == 'claim'), None)
            if action == 'claim':
                if actor['lane'] != 'builder' or claim or task.get('assignee'):
                    raise GateError('Claim requires unassigned task and an unclaimed builder lane')
                operation = str(uuid.uuid4())
                self.journal_intent('claim_intent', issue, actor, seal, operation=operation,
                                    readiness=ready['readiness'])
                self.beads.claim(issue, actor['role'], operation)
                after, after_seal = self.snapshot(issue)
                if after_seal != seal or after.get('assignee') != actor['role'] or after.get('status') != 'in_progress':
                    raise GateError('Beads claim raced; reconcile canonical task before retry')
                return self.record('claim', issue, actor, seal, readiness=ready['readiness'], operation=operation)
            if not claim or task.get('assignee') != claim['actor']['role'] or task.get('status') != 'in_progress':
                raise GateError('No current canonical bound claim')
            head = self.head(claim['actor']['cwd'])
            if args.get('head', head) != head:
                raise GateError('Evidence refers to a stale product commit')
            implementation = next((e for e in reversed(active) if e['action'] == 'implemented' and e.get('head') == head), None)
            common = {'readiness': ready['readiness'], 'head': head}
            if action == 'implemented':
                if actor['role'] != claim['actor']['role'] or actor['thread'] != claim['actor']['thread']:
                    raise GateError('Only the bound claiming builder can submit implementation')
                if type(args['passed']) is not bool:
                    raise GateError('Test result must be boolean')
                return self.record(action, issue, actor, seal, evidence=self.evidence(args['evidence'], actor),
                                   passed=args['passed'], evidence_trust='worker-submitted', **common)
            if not implementation or not implementation['passed']:
                raise GateError('Current passing implementation submission required')
            self.verify_evidence(implementation)
            if action == 'review':
                if actor['lane'] != 'read-only' or actor['role'] == claim['actor']['role'] or actor['thread'] == claim['actor']['thread']:
                    raise GateError('Independent read-only reviewer required')
                if type(args['approved']) is not bool:
                    raise GateError('Review outcome must be boolean')
                return self.record(action, issue, actor, seal, evidence=self.evidence(args['evidence'], actor),
                                   implementation=implementation['id'], approved=args['approved'], **common)
            review = next((e for e in reversed(active) if e['action'] == 'review' and e.get('head') == head and
                           e.get('implementation') == implementation['id']), None)
            if not review or not review['approved']:
                raise GateError('Current independent approval required')
            self.verify_evidence(review)
            if action == 'surface':
                if actor['lane'] != 'read-only' or actor['thread'] == claim['actor']['thread']:
                    raise GateError('Independent surface observer required')
                if args['surface'] not in ready['surfaces'] or args['kind'] != 'real-host-observation':
                    raise GateError('Wrong declared surface or non-host evidence')
                return self.record(action, issue, actor, seal, surface=args['surface'], kind=args['kind'],
                                   evidence=self.evidence(args['evidence'], actor), review=review['id'],
                                   evidence_trust='submitted-not-authenticated', **common)
            observations = [e for e in active if e['action'] == 'surface' and e.get('head') == head and e.get('review') == review['id']]
            for event in observations:
                self.verify_evidence(event)
            missing = [s for s in ready['surfaces'] if not any(e['surface'] == s for e in observations)]
            if action == 'gate_status':
                return dict(issue=issue, head=head, criteria_hash=seal, missing_surfaces=missing,
                            submissions_complete=not missing, accepted=False, task_authority='Beads',
                            acceptance_blockers=['Explicit current operator-terminal attestation required',
                                                 'Surface and CI submissions need operator verification; no automatic host authentication',
                                                 'External user-run Beads/Git mutations are outside coordinator authority'])
            if action == 'accept':
                if actor['role'] != 'delivery-manager' or actor['lane'] != 'read-only':
                    raise GateError('Acceptance requires bound delivery manager')
                if missing:
                    raise GateError('Missing declared surface submissions')
                for role in self.db.execute('SELECT spec,phase FROM roles'):
                    if json.loads(role['spec'])['lane'] == 'builder' and role['phase'] not in ('idle', 'prepared'):
                        raise GateError('Quiesce builder turns before operator acceptance')
                scope = dict(action='delivery-accept', issue=issue, head=head, criteria_hash=seal,
                             evidence_digest=digest({'implementation': implementation, 'review': review,
                                                     'observations': observations, 'readiness': ready}))
                question = {'attestation': 'Accepting attests that I personally verified the current commit, criteria, '
                            'passing CI, no unresolved conflicts, independent review, and actual declared host/app/mode '
                            'observations below. Worker submissions alone are insufficient. This closes only the Beads '
                            'task and authorizes no merge, push or publication.',
                            'scope': scope, 'criteria': task['acceptance_criteria'], 'readiness': ready, 'surfaces': ready['surfaces'],
                            'implementation': implementation, 'review': review, 'observations': observations,
                            'options': ['accept', 'decline', 'cancel']}
                return {'operator_capture_required': True, 'scope': scope, 'question': question}

            raise GateError('Unknown gate action')

    def accept_from_operator(self, issue, actor, binding, receipt, authority):
        """Trusted client only; never register this method as a worker tool.

        The operator must inspect the full displayed attestation, including CI
        and actual host observations. CaptureAuthority binds that exact question
        to one expiring terminal response. Recheck after the potentially long
        operator wait. The local transaction serializes coordinator commands;
        unrelated user-run Beads/Git mutations remain outside this boundary.
        """
        if not isinstance(authority, CaptureAuthority):
            raise GateError('Trusted operator capture authority required')
        with self.store.transaction():
            prepared = self.call('delivery_task_accept', {'issue': issue}, actor)
            if (not isinstance(binding, dict) or binding.get('scope') != prepared['scope'] or
                    binding.get('question') != prepared['question'] or
                    binding.get('source_revision') != prepared['scope']['head'] or
                    binding.get('thread_id') != actor.get('thread') or binding.get('turn_id') != actor.get('turn') or
                    binding.get('method') != 'delivery/gateAcceptance'):
                raise GateError('Operator acceptance binding is stale or mismatched')
            bound = self.actor(actor)
            task, seal = self.snapshot(issue)
            if seal != prepared['scope']['criteria_hash']:
                raise GateError('Criteria changed while confirming acceptance')
            # No coordinator callback can mutate state between this check and
            # close; actual Git movement is checked again immediately below.
            events = self.events(issue)
            claim = next(e for e in reversed(events) if e['action'] == 'claim')
            if self.head(claim['actor']['cwd']) != prepared['scope']['head']:
                raise GateError('Product commit changed while confirming acceptance')
            response = authority.verify_receipt(receipt, binding)
            if response != {'decision': 'accept'}:
                raise GateError('Operator declined or cancelled acceptance')
            operation = str(uuid.uuid4())
            reason = 'delivery-accept-op:'+operation+'; head '+prepared['scope']['head']+'; criteria '+seal
            self.journal_intent('accept_intent', issue, bound, seal, operation=operation,
                                scope=prepared['scope'], question=prepared['question'],
                                binding=binding, receipt_sha256=digest(receipt), close_reason=reason)
            self.beads.close(issue, bound['role'], reason)
            closed = self.beads.show(issue)
            if closed.get('status') != 'closed' or closed.get('close_reason') != reason:
                raise GateError('Canonical close outcome unknown; reconcile before retry')
            self.record('accepted', issue, bound, seal, head=prepared['scope']['head'], operation=operation,
                        evidence_digest=prepared['scope']['evidence_digest'],
                        operator_channel='operator-terminal', authority_scope='coordinator-controlled tasks only')
            return {'issue': issue, 'status': 'closed', 'accepted': True,
                    'authority': 'explicit operator-terminal attestation',
                    'merge_authorized': False, 'external_mutation_guarantee': False}

    def journal_intent(self, action, issue, actor, seal, **extra):
        """Persist authorization before an external effect, even if its outcome rolls back.

        Called only within the controlled command transaction. Reopen that
        transaction after the journal commit so caller exception handling can
        still roll back unconfirmed outcome events. Never replay an effect here.
        """
        if not self.db.in_transaction:
            raise GateError('Effect journal requires coordinator transaction')
        self.record(action, issue, actor, seal, **extra)
        self.db.execute('COMMIT')
        self.db.execute('BEGIN IMMEDIATE')

    def reconcile_effects(self):
        """Read canonical outcomes after interruption. No external mutation/retry."""
        all_events = [json.loads(r['data']) for r in self.db.execute(
            "SELECT data FROM events WHERE kind='delivery_gate' ORDER BY id")]
        finished = {e.get('operation') for e in all_events if e['action'] in ('claim', 'accepted', 'effect_reconciled')}
        results = []
        for intent in all_events:
            if intent['action'] not in ('claim_intent', 'accept_intent') or intent['operation'] in finished:
                continue
            task = self.beads.show(intent['issue'])
            confirmed = False
            if intent['action'] == 'accept_intent':
                confirmed = task.get('status') == 'closed' and task.get('close_reason') == intent['close_reason']
            elif task.get('status') == 'in_progress' and task.get('assignee') == intent['actor']['role']:
                confirmed = 'delivery-claim-op:'+intent['operation'] in task.get('notes', '')
            result = {'operation': intent['operation'], 'issue': intent['issue'],
                      'outcome': 'confirmed-applied' if confirmed else 'unknown-requires-operator-reconcile',
                      'replayed': False}
            if confirmed:
                with self.store.transaction():
                    if intent['action'] == 'claim_intent':
                        self.record('claim', intent['issue'], intent['actor'], intent['seal'],
                                    readiness=intent['readiness'], operation=intent['operation'], recovered=True)
                    self.record('effect_reconciled', intent['issue'], intent['actor'], intent['seal'],
                                operation=intent['operation'], canonical_status=task['status'],
                                kind=intent['action'], verified_authorization=True)
            results.append(result)
        return results

    def materialize(self, relative, identity):
        """Create only a draft task from protected canonical story bytes."""
        with self.store.transaction():
            actor = self.actor(identity)
            if actor['role'] != 'delivery-manager' or actor['lane'] != 'read-only':
                raise GateError('Story materialization requires bound delivery manager')
            if not isinstance(relative, str) or not re.fullmatch(r'stories/[A-Za-z0-9][A-Za-z0-9_.-]*\.md', relative):
                raise GateError('Use a canonical stories/<name>.md path')
            path = self.store.root.parent/relative
            if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file() or path.stat().st_size > 2_000_000:
                raise GateError('Canonical story missing, unsafe or too large')
            payload = path.read_bytes()
            body = payload.decode('utf-8')
            sha = hashlib.sha256(payload).hexdigest()
            _, provenance = self.artifact_event(path)
            if (not provenance or provenance.get('sha256') != sha or
                    provenance.get('actor', {}).get('role') not in ('coordinator', 'product-manager', 'delivery-manager') or
                    not provenance.get('actor', {}).get('thread') or not provenance.get('actor', {}).get('turn')):
                raise GateError('Story requires current coordinator-protected manager artifact provenance')
            plain = re.sub(r'<!--.*?-->', '', body, flags=re.S)
            plain = re.sub(r'\A\s*---\n.*?\n---\n', '', plain, count=1, flags=re.S)
            titles = re.findall(r'^# ([^\n]+)$', plain, flags=re.M)
            sections = re.findall(r'^## Acceptance criteria\s*\n(.*?)(?=^## |\Z)', plain, flags=re.M|re.S|re.I)
            if len(titles) != 1 or len(sections) != 1 or not sections[0].strip() or '<' in titles[0]:
                raise GateError('Story requires one concrete H1 title and one Acceptance criteria section')
            criteria = sections[0].strip()
            if re.search(r'<[^>]+>', criteria):
                raise GateError('Replace acceptance-criteria template placeholders before materialization')
            key = digest({'story_path': relative})
            matches = self.beads.find_source(key)
            if not isinstance(matches, list) or len(matches) > 1:
                raise GateError('Ambiguous canonical source mapping; operator reconciliation required')
            if matches:
                task = self.beads.show(matches[0]['id'])
                metadata = task.get('metadata', {})
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                if (metadata.get('delivery_source_sha256') != sha or task.get('description') != body or
                        task.get('title') != titles[0].strip() or task.get('acceptance_criteria') != criteria):
                    raise GateError('Story or canonical title/criteria changed after materialization; explicitly realign canonical task')
                return {'issue': task['id'], 'reused': True, 'readiness_granted': False, 'source_sha256': sha}
            intents = [json.loads(r['data']) for r in self.db.execute(
                "SELECT data FROM events WHERE kind='delivery_materialize_intent'")]
            if any(e.get('source_key') == key for e in intents):
                return {'outcome': 'unknown-requires-operator-reconcile', 'source_key': key, 'replayed': False}
            operation = str(uuid.uuid4())
            metadata = {'delivery_source_key': key, 'delivery_source_path': relative,
                        'delivery_source_sha256': sha, 'delivery_operation': operation}
            self.store.event('delivery_materialize_intent', dict(metadata, actor=actor, source_key=key))
            self.db.execute('COMMIT')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                created = self.beads.create_story(titles[0].strip(), body, criteria, metadata, actor['role'])
                if not isinstance(created, dict) or not isinstance(created.get('id'), str):
                    raise GateError('Ambiguous canonical create result')
                task = self.beads.show(created['id'])
                if task.get('description') != body or task.get('acceptance_criteria') != criteria or task.get('status') != 'open':
                    raise GateError('Canonical draft creation outcome differs from source')
                result = {'issue': task['id'], 'reused': False, 'readiness_granted': False, 'source_sha256': sha}
                self.store.event('delivery_materialized', dict(result, actor=actor, operation=operation))
                return result
            except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                self.store.event('delivery_materialize_unknown', {'operation': operation, 'source_key': key, 'error': str(error)})
                return {'outcome': 'unknown-requires-operator-reconcile', 'source_key': key, 'replayed': False}
