"""Coordinator-owned canonical artifact writes for otherwise read-only roles.

These are draft planning/review submissions, never human decisions. Optimistic
content-hash checks serialize coordinator writes; unrelated user clients remain
outside this boundary. Prior bytes are retained in protected revision history.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid

from project import checked_path

TOOLS = [{'type':'function','name':'delivery_artifact_write',
          'description':'Save a draft canonical planning/review artifact with expected hash; no authority or acceptance.',
          'inputSchema':{'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'},
                         'expected_sha256':{'type':['string','null']}},
                         'required':['path','content','expected_sha256'],'additionalProperties':False}}]


class ArtifactError(ValueError):
    pass


class ArtifactService:
    def __init__(self, store):
        self.store, self.db = store, store.db
        self.db.execute('CREATE TABLE IF NOT EXISTS artifact_intents(\n            id TEXT PRIMARY KEY, target TEXT NOT NULL, old_sha TEXT, new_sha TEXT NOT NULL,\n            result TEXT NOT NULL, state TEXT NOT NULL)')
        self.reconcile_all()

    def reconcile_all(self):
        for pending in self.db.execute("SELECT * FROM artifact_intents WHERE state='prepared'").fetchall():
            with self.store.transaction():
                row = self.db.execute("SELECT * FROM artifact_intents WHERE id=? AND state='prepared'",(pending['id'],)).fetchone()
                if not row:
                    continue
                target = checked_path(row['target'])
                if not target.is_relative_to(checked_path(self.store.root.parent)):
                    raise ArtifactError('Artifact intent escaped canonical root')
                data = target.read_bytes() if target.is_file() else None
                actual = hashlib.sha256(data).hexdigest() if data is not None else None
                if actual == row['new_sha']:
                    self.store.event('artifact_saved',json.loads(row['result']))
                    state = 'saved'
                elif actual == row['old_sha']:
                    self.store.event('artifact_write_not_applied',{'intent':row['id'],'path':row['target']})
                    state = 'not-applied'
                else:
                    self.store.event('artifact_write_conflict',{'intent':row['id'],'path':row['target']})
                    state = 'conflict'
                self.db.execute('UPDATE artifact_intents SET state=? WHERE id=?',(state,row['id']))

    @staticmethod
    def sync_directory(path):
        descriptor = os.open(path,os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def write(self, args, actor):
        if not isinstance(args, dict) or set(args) != {'path','content','expected_sha256'}:
            raise ArtifactError('Exact artifact path, content and expected hash required')
        if not isinstance(actor, dict):
            raise ArtifactError('Missing native actor')
        relative = args['path']
        if not isinstance(relative, str) or len(relative) > 240 or '\\' in relative:
            raise ArtifactError('Use a canonical relative planning path')
        path = PurePosixPath(relative)
        if (path.is_absolute() or not path.parts or str(path) != relative or
                any(part in ('.','..') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',part) for part in path.parts)):
            raise ArtifactError('Invalid canonical artifact path')
        parts = path.parts
        allowed = (parts == ('glossary.md',) or
                   (len(parts) == 3 and parts[0] == 'initiatives' and
                    (parts[-1].endswith('.md') or parts[-1] == 'surface.json')) or
                   (len(parts) == 2 and parts[0] in {'personas','interviews','simulations','stories','reviews','sprints'} and parts[-1].endswith('.md')) or
                   (len(parts) == 2 and parts[0] == 'decisions' and re.fullmatch(r'ADR-[0-9]{3,}-[A-Za-z0-9_.-]+\.md',parts[-1])))
        if not allowed:
            raise ArtifactError('Runtime, provider configuration and authority records are not artifact targets')
        content = args['content']
        if not isinstance(content,str) or not content.strip() or len(content.encode('utf-8')) > 2_000_000:
            raise ArtifactError('Artifact must contain 1–2000000 bytes of text')
        if parts[-1] == 'surface.json':
            try:
                if not isinstance(json.loads(content),dict):
                    raise ArtifactError('Surface artifact must be a JSON object')
            except ValueError as error:
                raise ArtifactError('Surface artifact must be a JSON object') from error
        expected = args['expected_sha256']
        if expected is not None and (not isinstance(expected,str) or not re.fullmatch(r'[a-f0-9]{64}',expected)):
            raise ArtifactError('Expected hash must be lowercase SHA256 or null for a new artifact')
        with self.store.transaction():
            role = self.db.execute('SELECT * FROM roles WHERE name=?',(actor.get('role'),)).fetchone()
            if not role or role['phase'] != 'active':
                raise ArtifactError('Inactive native role')
            spec = json.loads(role['spec'])
            if (actor.get('thread') != role['thread'] or actor.get('turn') != role['turn'] or
                    actor.get('lane') != spec['lane'] or spec['lane'] != 'read-only'):
                raise ArtifactError('Native actor binding or lane mismatch')
            managers = {'coordinator','product-manager','delivery-manager'}
            if role['name'] not in managers and parts[0] != 'reviews':
                raise ArtifactError('Reviewers may save review submissions only')
            root = checked_path(self.store.root.parent)
            target = checked_path(root.joinpath(*parts))
            if not target.is_relative_to(root) or (target.exists() and not target.is_file()):
                raise ArtifactError('Invalid target file')
            if target.exists() and target.stat().st_size > 2_000_000:
                raise ArtifactError('Existing artifact exceeds safe revision size')
            old = target.read_bytes() if target.exists() else None
            old_sha = hashlib.sha256(old).hexdigest() if old is not None else None
            if old_sha != expected:
                raise ArtifactError('Artifact revision changed; read it before proposing an update')
            payload = content.encode('utf-8')
            sha = hashlib.sha256(payload).hexdigest()
            history = checked_path(self.store.root/'artifact-revisions')
            history.mkdir(mode=0o700,exist_ok=True)
            self.sync_directory(self.store.root)
            if old is not None:
                archived = checked_path(history/old_sha)
                if archived.exists():
                    if archived.read_bytes() != old:
                        raise ArtifactError('Protected revision history conflict')
                else:
                    with archived.open('xb') as file:
                        file.write(old);file.flush();os.fsync(file.fileno())
                    self.sync_directory(history)
            binding = {key:actor[key] for key in ('role','thread','turn','lane')}
            result = {'path':str(target),'relative_path':relative,'sha256':sha,'previous_sha256':old_sha,
                      'actor':binding,'persistence':'saved','authority':'draft submission; no human consent'}
            intent = str(uuid.uuid4())
            result['intent_id'] = intent
            self.db.execute("INSERT INTO artifact_intents VALUES(?,?,?,?,?,'prepared')",
                            (intent,str(target),old_sha,sha,json.dumps(result)))
            self.store.event('artifact_write_intent',{'id':intent,'path':str(target),'old_sha256':old_sha,'new_sha256':sha,'actor':binding})
        # Intent is committed before the filesystem effect. A crash or SQL error
        # after replacement leaves a recoverable pending intent, never blind retry.
        target.parent.mkdir(parents=True,exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.delivery-write-',dir=target.parent)
        try:
            with os.fdopen(descriptor,'wb') as file:
                file.write(payload);file.flush();os.fsync(file.fileno())
            current = target.read_bytes() if target.exists() else None
            if current != old:
                raise ArtifactError('Artifact changed before save; proposed bytes were not installed')
            os.replace(temporary,target)
            for parent in (target.parent,*target.parent.parents):
                if not parent.is_relative_to(root):
                    break
                self.sync_directory(parent)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)
        self.reconcile_all()
        row = self.db.execute('SELECT state FROM artifact_intents WHERE id=?',(intent,)).fetchone()
        if not row or row['state'] != 'saved':
            raise ArtifactError('Artifact save outcome requires reconciliation')
        return result
