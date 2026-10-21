import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'plugins/delivery/scripts'))
from artifacts import ArtifactService,ArtifactError
from runtime import Store


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.root=Path(self.temporary.name).resolve()
        (self.root/'.delivery').mkdir()
        self.store=Store(self.root)
        self.service=ArtifactService(self.store)
        self.actors={}
        for name,lane in [('product-manager','read-only'),('reviewer','read-only'),('builder','builder')]:
            spec={'cwd':str(self.root),'lane':lane}
            self.store.db.execute("INSERT INTO roles VALUES(?,?,?,?,'active',NULL)",(name,json.dumps(spec),'thread-'+name,'turn-'+name))
            self.actors[name]={'role':name,'thread':'thread-'+name,'turn':'turn-'+name,'lane':lane}

    def tearDown(self):
        self.store.db.close();self.temporary.cleanup()

    def write(self,path='initiatives/example/brief.md',content='First draft',expected=None,who='product-manager'):
        return self.service.write({'path':path,'content':content,'expected_sha256':expected},self.actors[who])

    def test_saves_actual_canonical_bytes_and_journals_native_actor(self):
        r=self.write()
        self.assertEqual(Path(r['path']).read_text(),'First draft')
        event=json.loads(self.store.db.execute("SELECT data FROM events WHERE kind='artifact_saved'").fetchone()[0])
        self.assertEqual(event['actor'],self.actors['product-manager'])
        self.assertEqual(event['sha256'],hashlib.sha256(b'First draft').hexdigest())
        self.assertIn('no human consent',r['authority'])

    def test_revision_cas_preserves_prior_content_and_rejects_stale_overwrite(self):
        first=self.write()
        second=self.write(content='Revised draft',expected=first['sha256'])
        self.assertEqual((self.store.root/'artifact-revisions'/first['sha256']).read_text(),'First draft')
        with self.assertRaises(ArtifactError):self.write(content='Stale overwrite',expected=first['sha256'])
        with self.assertRaises(ArtifactError):self.write(content='Silent replace')
        self.assertEqual(Path(second['path']).read_text(),'Revised draft')

    def test_native_actor_lane_turn_and_status_are_rechecked(self):
        for who in ['builder']:
            with self.assertRaises(ArtifactError):self.write(who=who)
        self.actors['product-manager']['turn']='stale'
        with self.assertRaises(ArtifactError):self.write()
        self.actors['product-manager']['turn']='turn-product-manager'
        self.store.db.execute("UPDATE roles SET phase='idle' WHERE name='product-manager'")
        with self.assertRaises(ArtifactError):self.write()

    def test_reviewers_can_save_only_review_submissions(self):
        r=self.write(path='reviews/example-review.md',who='reviewer')
        self.assertTrue(Path(r['path']).is_file())
        with self.assertRaises(ArtifactError):self.write(who='reviewer')

    def test_protected_paths_traversal_and_noncanonical_aliases_are_refused(self):
        paths=['runtime/coordinator.sqlite','team.json','judge-config.json','decisions/dec-001.json',
               '../outside.md','/absolute.md','initiatives/example/../../runtime/state.md',
               'initiatives//example/brief.md','initiatives/example/./brief.md','reviews\\escape.md',
               '.hidden.md','personas/.secret.md']
        for path in paths:
            with self.subTest(path=path):
                with self.assertRaises(ArtifactError):self.write(path=path)

    def test_symlink_parent_or_target_never_changes_external_files(self):
        outside=self.root/'outside';outside.mkdir();protected=outside/'brief.md';protected.write_text('Preserve')
        (self.root/'.delivery/initiatives').mkdir()
        (self.root/'.delivery/initiatives/example').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):self.write()
        self.assertEqual(protected.read_text(),'Preserve')

    def test_history_tampering_stops_revision_before_overwriting_current_file(self):
        first=self.write();history=self.store.root/'artifact-revisions';history.mkdir(exist_ok=True)
        (history/first['sha256']).write_text('Corrupt')
        with self.assertRaises(ArtifactError):self.write(content='Replace',expected=first['sha256'])
        self.assertEqual(Path(first['path']).read_text(),'First draft')

    def test_invalid_or_empty_content_and_bad_surface_are_refused(self):
        for content in ['', ' ', 12]:
            with self.assertRaises(ArtifactError):self.write(content=content)
        for content in ['invalid json','[]','null']:
            with self.assertRaises(ArtifactError):self.write(path='initiatives/example/surface.json',content=content)
        result=self.write(path='initiatives/example/surface.json',content='{"host":"synthetic"}')
        self.assertEqual(json.loads(Path(result['path']).read_text()),{'host':'synthetic'})

    def test_saved_event_failure_recovers_committed_intent_without_rewriting_bytes(self):
        first=self.write()
        real=self.store.event
        def fail_saved(kind,data):
            if kind=='artifact_saved':raise RuntimeError('synthetic event failure')
            real(kind,data)
        with patch.object(self.store,'event',side_effect=fail_saved):
            with self.assertRaises(RuntimeError):self.write(content='Installed before failure',expected=first['sha256'])
        self.assertEqual(Path(first['path']).read_text(),'Installed before failure')
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM artifact_intents WHERE state='prepared'").fetchone()[0],1)
        ArtifactService(self.store)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM artifact_intents WHERE state='prepared'").fetchone()[0],0)
        rows=self.store.db.execute("SELECT data FROM events WHERE kind='artifact_saved' ORDER BY id").fetchall()
        self.assertEqual(len(rows),2)
        self.assertEqual(json.loads(rows[-1][0])['sha256'],hashlib.sha256(b'Installed before failure').hexdigest())
        self.assertEqual((self.store.root/'artifact-revisions'/first['sha256']).read_text(),'First draft')

    def test_crash_before_replace_is_recorded_not_replayed(self):
        first=self.write()
        with patch('artifacts.os.replace',side_effect=OSError('synthetic rename failure')):
            with self.assertRaises(OSError):self.write(content='Not installed',expected=first['sha256'])
        ArtifactService(self.store)
        self.assertEqual(Path(first['path']).read_text(),'First draft')
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM artifact_intents WHERE state='not-applied'").fetchone()[0],1)
