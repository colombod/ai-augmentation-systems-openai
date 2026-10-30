#!/usr/bin/env python3
"""Public-command proof on Delivery source plus a labelled no-code concept.

Uses one new planning directory; never edits product code, installs software or
executes source blobs to infer dependencies. Only explicit packaged helper
commands run. This is deterministic CLI evidence, not a model
workflow, authenticated owner decision, native host or deployment/adoption proof.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    repo = args.repo.resolve();output = args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    package = repo/'plugins/delivery'
    commit = subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    calls = []

    def run(name,argv):
        result = subprocess.run(argv,capture_output=True,text=True,timeout=60)
        calls.append({'name':name,'argv':argv,'stdout':result.stdout,'stderr':result.stderr,'exit_code':result.returncode})
        if result.returncode:
            raise AssertionError(calls[-1])
        return json.loads(result.stdout)

    brown = output/'brownfield';green = output/'greenfield'
    for project in (brown,green):
        project.mkdir()
        run(project.name+'-init',[sys.executable,str(package/'scripts/project.py'),'init','--project',str(project),'--initiative','dependency-proof'])

    def product(name, project, *args):
        command = [sys.executable,str(package/'scripts/product.py'),'--project',str(project)]
        if project==brown:
            command += ['--repo',str(repo)]
        return run(name,command+list(args))

    template = json.loads((package/'templates/product-input.json').read_text())
    data = copy.deepcopy(template)
    data.update(mode='brownfield',commit=commit,features=[])
    for identity,name,anchor,summary in [
        ('native-coordination','Native coordination source','runtime.py','Persist native roles and route controlled work; source preview, no new host proof.'),
        ('controlled-work','Controlled task workflow source','delivery_gates.py','Control task review/acceptance evidence; source preview, no inferred human authority.')]:
        feature = copy.deepcopy(template['features'][0])
        feature.update(id=identity,name=name,state='preview',summary=summary,
                       code=['plugins/delivery/scripts/'+anchor],
                       evidence=[{'path':'plugins/delivery/scripts/'+anchor,'note':'Curated source anchor at exact commit; possible imports, not deployment or user evidence.'}])
        data['features'].append(feature)
    source_input = output/'brownfield-input.json';source_input.write_text(json.dumps(data,indent=2)+'\n')
    product('record-brownfield',brown,'record','--input',str(source_input),'--expected-sha256','new')
    target = 'plugins/delivery/scripts/operator_capture.py'
    direct = product('direct-impact',brown,'impact','--path',target)
    reached = product('dependency-impact',brown,'impact','--path',target,'--transitive')
    retirement = product('retirement-proposal',brown,'retire-plan','--feature','native-coordination','--transitive')
    assert direct['features']==reached['features']==[]
    graph = reached['transitive']
    assert graph['snapshot_commit']==commit and graph['freshness']['fresh']
    assert {feature['id'] for feature in graph['features']}=={'native-coordination','controlled-work'}
    assert graph['shared_files'][target]==['native-coordination','controlled-work']
    for feature in graph['features']:
        via = feature['via'][0]
        assert via['hops']==1 and via['chain'][0]['to']==target and via['chain'][0]['line']>0
    assert retirement['transitive']['shared_code_to_preserve'][target]==['controlled-work']
    assert target not in retirement['transitive']['exclusive_candidates_not_deletion_permission']
    assert retirement['proposal_only'] and retirement['required_owner_decision']['choice']=='unknown'

    concept = output/'greenfield-input.json';concept.write_text(json.dumps(template,indent=2)+'\n')
    product('record-illustrative-greenfield',green,'record','--input',str(concept),'--expected-sha256','new')
    future = product('greenfield-optional-reach',green,'impact','--path','future.py','--transitive')
    assert not future['transitive']['available'] and future['freshness']['fresh'] is None
    summary = {'source_commit':commit,'question':'Which recorded feature promises may a change to '+target+' affect?',
               'direct_matches':0,'dependency_matches':2,'shared_dependency_preserved':True,
               'shortest_chains':{f['id']:f['via'][0]['chain'] for f in graph['features']},
               'greenfield':'Illustrative concept, planned code absent; optional graph unavailable with reason; no readiness gate.',
               'commands':len(calls),'model_calls':0,
               'qualification':'Actual repository, public deterministic commands and possible source imports only; source blobs parsed for reach; no deployment, adoption, native runtime or model quality proof.'}
    (output/'commands.json').write_text(json.dumps(calls,indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
