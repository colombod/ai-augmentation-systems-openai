"""Synthetic local Beads + real Git + OS PTY acceptance plumbing, no model calls.
The PTY response is automated, not a person's approval of product work.
"""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SOURCE_HASHES = {name: hashlib.sha256((ROOT/'plugins/delivery/scripts'/name).read_bytes()).hexdigest() for name in ['delivery_gates.py', 'operator_capture.py', 'artifacts.py']}
spec = importlib.util.spec_from_file_location('gate_fixture', ROOT/'tests/delivery/test_delivery_gates.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from delivery_gates import Beads, GateService
from artifacts import ArtifactService
from operator_capture import CaptureAuthority, question_digest
fixture = module.DeliveryGatesTests()
fixture.setUp()
observations = []
try:
    def run(*args):
        result = subprocess.run(list(args), cwd=fixture.planning, text=True, capture_output=True, timeout=90)
        if result.returncode:
            raise RuntimeError(result.stderr)
        return result.stdout
    run('git', 'init', '-q')
    run('bd', 'init', '--prefix', 'gatelive', '--skip-agents', '--skip-hooks', '--non-interactive')
    service = GateService(fixture.store)
    story = '# Make the fixture useful\n\n## Goal\nSynthetic observable fixture outcome.\n\n## Acceptance criteria\nCriterion A\n\n## Out of scope\nReal product acceptance.\n'
    ArtifactService(fixture.store).write({'path': 'stories/fixture.md', 'content': story,
                                         'expected_sha256': None}, fixture.actors['delivery-manager'])
    materialized = service.call('delivery_task_materialize', {'path': 'stories/fixture.md'}, fixture.actors['delivery-manager'])
    issue = materialized['issue']
    reused = service.call('delivery_task_materialize', {'path': 'stories/fixture.md'}, fixture.actors['delivery-manager'])
    assert reused['issue'] == issue and reused['reused'], reused
    observations.extend([{'action': 'materialize', 'result': materialized}, {'action': 'materialize-retry', 'result': reused}])
    def gate(action, actor='delivery-manager', **args):
        result = service.call('delivery_task_'+action, {'issue': issue, **args}, fixture.actors[actor])
        observations.append({'action': action, 'result': result})
        return result
    gate('ready', surfaces=[fixture.surface], assumptions=[])
    gate('claim', 'builder')
    head = fixture.git('rev-parse', 'HEAD')
    gate('implemented', 'builder', head=head, evidence=['.delivery-evidence/test-output'], passed=True)
    gate('review', 'reviewer', head=head, evidence=['.delivery-evidence/review-output'], approved=True)
    gate('surface', 'reviewer', head=head, surface=fixture.surface, kind='real-host-observation',
         evidence=['.delivery-evidence/host-output'])
    fixture.store.db.execute("UPDATE roles SET phase='idle',turn=NULL WHERE name='builder'")
    prepared = gate('accept')
    actor = fixture.actors['delivery-manager']
    binding = {'request_id': 'synthetic-gate-request', 'native_request_id': 'synthetic-gate-1',
               'thread_id': actor['thread'], 'turn_id': actor['turn'], 'method': 'delivery/gateAcceptance',
               'item_id': 'synthetic-item', 'source_revision': head, 'scope': prepared['scope'],
               'question': prepared['question'], 'question_digest': question_digest(prepared['question'])}
    authority = CaptureAuthority()
    receipt = fixture.receipt(authority, binding)
    accepted = service.accept_from_operator(issue, actor, binding, receipt, authority)
    canonical = Beads(fixture.planning).show(issue)
    assert canonical['status'] == 'closed', canonical
    assert canonical['assignee'] == 'builder', canonical
    output = {'source_sha256': SOURCE_HASHES,
              'test_type': 'synthetic OS PTY terminal response, real Beads and Git; no human/product acceptance',
              'observations': observations, 'accept_result': accepted, 'canonical_task': canonical,
              'limitations': ['No native Codex model/desktop/ChatGPT was exercised',
                              'CI and host observations are fixture text explicitly operator-attested by automated PTY input',
                              'No merge/push/global external mutation guarantee']}
    (Path(__file__).parent/'live-beads-roundtrip.json').write_text(json.dumps(output, indent=2))
    print(json.dumps({'issue': issue, 'canonical_status': canonical['status'], 'accepted': accepted}, indent=2))
finally:
    fixture.tearDown()
