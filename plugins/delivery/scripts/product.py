#!/usr/bin/env python3
"""One product record for ideas and existing projects. Standard library only.

Curated file links are not a call graph, deployment proof or deletion authority.
No model, service, hooks, Git writes or automatic code deletion are used here.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

from project import checked_path, delivery_root

CRITERIA = ('Job', 'First value', 'Fit', 'Outcome', 'Trust', 'Return')
GATE_CAPS = {'G1':5, 'G2':6, 'G3':5, 'G4':6, 'G5':7, 'G6':6}
METHOD = 'curated file-level feature links; no inferred calls or complete dependency graph'
MAX_RECORD = 4_000_000


def fail(message):
    raise ValueError(message)


def git(repo, *args):
    env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false',
        '-c','core.untrackedCache=false','-C',str(repo),*args],env=env,
        capture_output=True,timeout=30)
    if result.returncode:
        fail('Git inspection failed: '+result.stderr.decode(errors='replace')[:400])
    return result.stdout


def repository(path):
    root = checked_path(path)
    if not root.is_dir() or git(root,'rev-parse','--show-toplevel').decode().strip() != str(root):
        fail('Select an existing Git repository root explicitly')
    return root


def exact_commit(repo, value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}',value):
        fail('Exact full lowercase commit SHA required')
    if git(repo,'rev-parse',value+'^{commit}').decode().strip() != value:
        fail('Commit identity mismatch')
    return value


def tree(repo, commit):
    result = {}
    for entry in git(repo,'ls-tree','-rz','--full-tree',commit).split(b'\0'):
        if entry:
            header, name = entry.split(b'\t',1)
            mode, kind, blob = header.decode().split(' ')
            result[os.fsdecode(name)] = {'mode':mode, 'kind':kind, 'blob':blob}
    return result


def relative(value):
    if not isinstance(value,str) or not value or len(value)>500 or '\\' in value or '\0' in value:
        fail('Use a repository-relative file path')
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(x in ('.','..') for x in path.parts):
        fail('Unsafe or noncanonical repository-relative path')
    return value


def text(value, label):
    if not isinstance(value,str) or not value.strip() or len(value)>16000:
        fail(label+' requires nonempty text (at most 16000 characters)')


def exact_fields(value, fields, label):
    if not isinstance(value,dict) or set(value) != set(fields):
        fail(label+' requires exactly: '+', '.join(fields))


def decision(value):
    exact_fields(value, ('text','basis','source','revisit'), 'Product choice')
    for k in ('text','source','revisit'):
        text(value[k],k)
    if value['basis'] not in ('owner-stated','proposed','unknown'):
        fail('Choice basis must distinguish owner-stated, proposed and unknown')


def placement(value):
    exact_fields(value, ('need','gates','form','autonomy_rung','engine','reason','alternatives','benchmark'), 'Work shape')
    exact_fields(value['need'], ('N1','N2','N3','N4'), 'Autonomy need')
    if any(type(x) is not int or not 0<=x<=3 for x in value['need'].values()):
        fail('Need dimensions are integers 0 to 3')
    exact_fields(value['gates'], GATE_CAPS, 'Autonomy gates')
    for gate in value['gates'].values():
        exact_fields(gate, ('status','reason'), 'Gate')
        if gate['status'] not in ('pass','fail','unknown'):
            fail('Gate status must be pass, fail or unknown')
        text(gate['reason'],'Gate reason')
    if value['form'] not in ('tool','smart-tool','skill','workflow','subagent','agent','harness'):
        fail('Choose an explicit work form')
    if value['engine'] not in ('None','LLM','Decision model','Both'):
        fail('Choose None, LLM, Decision model or Both as engine')
    text(value['reason'],'Shape reason')
    text(value['benchmark'],'Benchmark and stop rule')
    if not isinstance(value['alternatives'],list) or not value['alternatives']:
        fail('Record at least one smaller or rejected alternative')
    for item in value['alternatives']:
        text(item,'Alternative')
    score = sum(value['need'].values())
    need = next(r for cap,r in ((1,1),(3,2),(5,3),(7,5),(9,7),(12,8)) if score<=cap)
    capped = [k for k,g in value['gates'].items() if g['status'] != 'pass']
    ceiling = min([9]+[GATE_CAPS[k] for k in capped])
    if type(value['autonomy_rung']) is not int or not 0<=value['autonomy_rung']<=min(need,ceiling):
        fail('Selected autonomy rung exceeds need or the conservative gate ceiling')
    return {'need_score':score,'need_rung':need,'ceiling':ceiling,
            'maximum_rung':min(need,ceiling),'selected_rung':value['autonomy_rung'],'capped_by':capped,
            'qualification':'arithmetic only; gate truth and form remain human-reviewed judgments'}


def validate(value, repo):
    exact_fields(value, ('schema_version','mode','commit','features','product'), 'Map input')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        fail('Unsupported map schema version')
    if value['mode'] not in ('greenfield','brownfield'):
        fail('Choose greenfield or brownfield explicitly')
    if value['mode']=='greenfield':
        if value['commit'] is not None:
            fail('A concept-only record has no observed code commit')
        commit, files = None, {}
    else:
        if repo is None:
            fail('Brownfield code mapping needs an explicit --repo root')
        commit = exact_commit(repo,value['commit'])
        files = tree(repo,commit)
    product = value['product']
    exact_fields(product, ('customer','problem','current_cost','proposition','before_after',
        'riskiest_assumption','must_survive','cuts','next_slice','right_shape'), 'Product')
    for key in ('customer','problem','current_cost','proposition','before_after','riskiest_assumption','next_slice'):
        decision(product[key])
    for key in ('must_survive','cuts'):
        if not isinstance(product[key],list) or not product[key]:
            fail('Record '+key+' explicitly, including an explicit none/unknown choice when necessary')
        for choice in product[key]:
            decision(choice)
    placement(product['right_shape'])
    if not isinstance(value['features'],list) or not value['features']:
        fail('At least one curated feature required')
    ids = set()
    linked = set()
    for feature in value['features']:
        exact_fields(feature, ('id','name','state','summary','code','evidence','unknowns','usefulness'), 'Feature')
        if not isinstance(feature['id'],str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',feature['id']) or feature['id'] in ids:
            fail('Unique kebab-case feature IDs required')
        ids.add(feature['id'])
        for key in ('name','summary'):
            text(feature[key],key)
        if feature['state'] not in ('shipped','preview','planned','retired'):
            fail('Feature state must distinguish shipped, preview, planned and retired')
        if value['mode']=='greenfield' and (feature['state']!='planned' or feature['code']):
            fail('Concept-only greenfield features are planned, with code absent explicitly')
        if not isinstance(feature['code'],list) or (not feature['code'] and feature['state'] in ('shipped','preview')):
            fail('Existing features require explicit supporting code files')
        if len(set(feature['code'])) != len(feature['code']):
            fail('Duplicate code links')
        paths = list(feature['code'])
        if not isinstance(feature['evidence'],list) or not feature['evidence']:
            fail('Every feature needs evidence with a limitation note')
        for evidence in feature['evidence']:
            exact_fields(evidence, ('path','note'), 'Evidence')
            text(evidence['note'],'Evidence note')
            if evidence['path'] is not None:
                paths.append(evidence['path'])
        for path in paths:
            relative(path)
            item = files.get(path)
            if not item or item['kind'] != 'blob' or item['mode'] not in ('100644','100755'):
                fail('Mapped code/evidence must be a regular tracked file at the snapshot commit: '+path)
            linked.add(path)
        if not isinstance(feature['unknowns'],list):
            fail('Feature unknowns must be an explicit list')
        for unknown in feature['unknowns']:
            text(unknown,'Unknown')
        exact_fields(feature['usefulness'], CRITERIA, 'Usefulness card')
        for card in feature['usefulness'].values():
            exact_fields(card, ('rating','grade','evidence','next_check'), 'Usefulness criterion')
            if card['rating'] not in ('Unknown','Missing','Partial','Solid') or card['grade'] not in ('Unknown','Claimed','Seen','Repeated'):
                fail('Keep usefulness rating separate from evidence grade')
            text(card['evidence'],'Usefulness evidence/unknown')
            text(card['next_check'],'Next evidence check')
    return {'schema_version':1,'mode':value['mode'],'commit':commit,'features':value['features'],'product':product,
            'snapshot':{p:files[p] for p in sorted(linked)},'method':METHOD}


def map_path(project):
    root = delivery_root(project)
    if not root.is_dir():
        fail('Run project.py init for the selected planning project first')
    return checked_path(root/'product-map.json')


def read_map(project, repo):
    path = map_path(project)
    data = path.read_bytes()
    if len(data)>MAX_RECORD:
        fail('Map exceeds four megabytes')
    value = json.loads(data)
    expected = validate({k:value[k] for k in ('schema_version','mode','commit','features','product')},repo)
    if expected != value:
        fail('Map snapshot does not match its recorded commit; re-record from curated inputs')
    return value, hashlib.sha256(data).hexdigest()


def save(project, repo, value, expected_sha):
    result = validate(value,repo)
    data = (json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    if len(data)>MAX_RECORD:
        fail('Map exceeds four megabytes; split the scope before recording')
    path = map_path(project)
    # Serialize local helper writes and retain each previous complete record.
    with checked_path(path.parent/'.product-map.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current = path.read_bytes() if path.exists() else None
        actual = hashlib.sha256(current).hexdigest() if current is not None else 'new'
        if actual != expected_sha:
            fail('Map changed; read current state before writing (expected SHA mismatch)')
        if current is not None:
            prior = json.loads(current)
            if {f['id'] for f in prior['features']} - {f['id'] for f in result['features']}:
                fail('Preserve old feature IDs/history; mark retirement through a reviewed proposal, never silently drop')
            old = {f['id']:f['state'] for f in prior['features']}
            if any(f['state']=='retired' and old.get(f['id']) not in (None,'retired') for f in result['features']):
                fail('This helper records retirement proposals, not human-authorized retirement transitions')
            history = checked_path(path.parent/'product-map-history')
            history.mkdir(exist_ok=True)
            history_file = checked_path(history/(actual+'.json'))
            if history_file.exists():
                if history_file.read_bytes() != current:
                    fail('History conflicts with current record; preserve current bytes and reconcile the history first')
            else:
                atomic_write(history_file,current)
        atomic_write(path,data)
    return {'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'commit':result['commit'],'features':len(result['features'])}


def atomic_write(path, data):
    descriptor, temporary = tempfile.mkstemp(prefix='.product-map-',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect(repo):
    commit = git(repo,'rev-parse','HEAD').decode().strip()
    files = tree(repo,commit)
    docs = [p for p in files if Path(p).name in ('AGENTS.md','README.md','CONTRIBUTING.md') or
            p.startswith(('docs/','.delivery/')) and p.endswith(('.md','.json'))]
    manifests = [p for p in files if Path(p).name in ('plugin.json','package.json','pyproject.toml','Cargo.toml','go.mod','Makefile')]
    staged = git(repo,'diff','--cached','--name-only','--no-renames','--no-ext-diff','--no-textconv','HEAD','--').decode().splitlines()
    return {'repository':str(repo),'commit':commit,'tracked_files':len(files),
        'instructions_and_docs':sorted(docs),'manifests':sorted(manifests),
        'test_paths':sorted(p for p in files if '/tests/' in '/'+p or Path(p).name.startswith('test_')),
        'working_changes':sorted(set(staged)|{p for p,item in files.items() if item['kind']=='blob' and raw_changed(repo,p,item)}),
        'staged_changes':staged,
        'untracked':git(repo,'ls-files','--others','--exclude-standard','-z').decode().split('\0')[:-1],
        'feature_discovery':'Candidate sources only: an agent must inspect them and curate features; no tickets or PRs imported'}


def raw_changed(repo, name, item):
    try:
        path = checked_path(repo/name)
        if item['mode'] not in ('100644','100755') or not path.is_file():
            return True
        before = path.stat()
        if before.st_size>20_000_000:
            return True  # Uninspected/unsupported is never asserted unchanged.
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            return True
        algorithm = hashlib.sha1 if len(item['blob'])==40 else hashlib.sha256
        blob = algorithm(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        return blob != item['blob'] or bool(after.st_mode&0o111) != (item['mode']=='100755')
    except (OSError,ValueError):
        return True


def freshness(value, repo):
    if value['mode']=='greenfield':
        return {'fresh':None,'snapshot_commit':None,'current_commit':None,
                'qualification':'Concept-only record: no code, deployment or customer use has been observed'}
    current = git(repo,'rev-parse','HEAD').decode().strip()
    changed = [p for p,item in value['snapshot'].items() if raw_changed(repo,p,item)]
    committed = git(repo,'diff','--name-only','--no-renames','--no-ext-diff',value['commit'],current,'--').decode().splitlines()
    staged = git(repo,'diff','--cached','--name-only','--no-renames','--no-ext-diff','--no-textconv','HEAD','--').decode().splitlines()
    current_tree = tree(repo,current)
    unmapped_working = [p for p,item in current_tree.items() if p not in value['snapshot'] and item['kind']=='blob' and raw_changed(repo,p,item)]
    untracked = git(repo,'ls-files','--others','--exclude-standard','-z').decode().split('\0')[:-1]
    return {'snapshot_commit':value['commit'],'current_commit':current,
        'commit_matches':current==value['commit'],'changed_mapped_files':sorted(changed),
        'unmapped_committed_changes':sorted(set(committed)-value['snapshot'].keys()),
        'unmapped_working_changes':sorted(unmapped_working),
        'staged_changes':staged,
        'untracked_not_analyzed':untracked,'fresh':current==value['commit'] and not changed and not staged,
        'limitation':'Fresh means snapshot commit and linked raw bytes/modes match; unmapped code and runtime wiring are not proven complete'}


def impact(value, repo, paths):
    paths = sorted({relative(p) for p in paths})
    features = [f for f in value['features'] if f['state']!='retired']
    affected = [{'id':f['id'],'name':f['name'],'state':f['state'],
        'links':sorted(set(paths)&set(f['code']))} for f in features if set(paths)&set(f['code'])]
    return {'question_paths':paths,'features':affected,
        'shared_files':{p:[f['id'] for f in features if p in f['code']] for p in paths if sum(p in f['code'] for f in features)>1},
        'unmapped_paths':[p for p in paths if not any(p in f['code'] for f in features)],
        'freshness':freshness(value,repo),'coverage':METHOD,
        'warning':'Unmapped means unknown, never safe to delete; transitive and dynamic dependencies require inspection'}


def retirement(value, repo, feature_id):
    feature = next((f for f in value['features'] if f['id']==feature_id),None)
    if not feature:
        fail('Unknown feature ID')
    report = impact(value,repo,feature['code'])
    shared = {p:[f['id'] for f in value['features'] if f['id']!=feature_id and f['state']!='retired' and p in f['code']]
              for p in feature['code']}
    shared = {p:ids for p,ids in shared.items() if ids}
    return {'feature':feature_id,'proposal_only':True,'shared_code_to_preserve':shared,
        'exclusive_candidates_not_deletion_permission':sorted(set(feature['code'])-shared.keys()),
        'required_owner_decision':{'choice':'unknown','scope_commit':value['commit'],
            'reason':'Retirement requires an explicit user decision, consumer/migration review and rollback; no action is performed'},
        'impact':report}


def handoff(value, repo):
    product = value['product']
    unresolved = [k for k in ('customer','proposition','next_slice') if product[k]['basis']!='owner-stated']
    unresolved += [k for k in ('must_survive','cuts') if any(d['basis']!='owner-stated' for d in product[k])]
    return {'product':product,'placement':placement(product['right_shape']),
        'unconfirmed_choices':unresolved,'freshness':freshness(value,repo),
        'features':[{k:f[k] for k in ('id','name','state','usefulness','unknowns')} for f in value['features']],
        'authority':'Recorded choices are attributed submissions, not authenticated approvals; proposals never authorize execution or retirement'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',help='Explicit existing product Git root; unnecessary for a greenfield idea')
    parser.add_argument('--project',required=True,help='Canonical planning project, independent of product code')
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('inspect')
    record = sub.add_parser('record');record.add_argument('--input',required=True);record.add_argument('--expected-sha256',required=True)
    sub.add_parser('status');sub.add_parser('handoff')
    change = sub.add_parser('impact');change.add_argument('--path',action='append',required=True)
    retire = sub.add_parser('retire-plan');retire.add_argument('--feature',required=True)
    args = parser.parse_args()
    repo = repository(args.repo) if args.repo else None
    project = checked_path(args.project)
    if args.command=='inspect':
        result = inspect(repo) if repo else {'mode':'greenfield','project':str(project),
            'code':'not supplied; start with the customer, job, promise and cuts',
            'planning_artifacts':__import__('project').inventory(project)}
    elif args.command=='record':
        with Path(args.input).open('rb') as stream:
            data = stream.read(MAX_RECORD+1)
        if len(data)>MAX_RECORD:
            fail('Input exceeds four megabytes')
        result = save(project,repo,json.loads(data),args.expected_sha256)
    else:
        value, sha = read_map(project,repo)
        if args.command=='impact':
            result = impact(value,repo,args.path)
        elif args.command=='retire-plan':
            result = retirement(value,repo,args.feature)
        elif args.command=='handoff':
            result = handoff(value,repo)
        else:
            result = {'freshness':freshness(value,repo),'features':[{k:f[k] for k in ('id','name','state')} for f in value['features']]}
        result['map_sha256'] = sha
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    observed = result.get('freshness') or result.get('impact',{}).get('freshness')
    return 1 if (observed and observed['fresh'] is False) or result.get('unconfirmed_choices') else 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'error':str(error)}),file=sys.stderr)
        raise SystemExit(2)
