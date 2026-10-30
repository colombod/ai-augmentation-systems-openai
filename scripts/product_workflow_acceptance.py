#!/usr/bin/env python3
"""Maintainer acceptance: actual Delivery repo plus labelled illustrative idea.

Uses the public package commands, not private functions. Writes evidence only
under a new output directory; no model calls, installs or product code edits.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    repo=Path(args.repo).resolve()
    package=repo/'plugins/delivery'
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=False)
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    starter=json.loads((package/'templates/product-input.json').read_text())
    calls=[]

    def run(argv, name, expected=(0,)):
        result=subprocess.run(argv,capture_output=True,text=True,timeout=60)
        item={'command':argv,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        calls.append(item)
        (output/(name+'.json')).write_text(json.dumps(item,indent=2)+'\n')
        if result.returncode not in expected:
            raise RuntimeError(name+': unexpected exit '+str(result.returncode)+' '+result.stderr)
        return json.loads(result.stdout)

    def init(project, initiative, name):
        project.mkdir()
        return run([sys.executable,str(package/'scripts/project.py'),'init','--project',str(project),'--initiative',initiative],name)

    def command(project,*args,brownfield=False,name,expected=(0,)):
        argv=[sys.executable,str(package/'scripts/product.py'),'--project',str(project)]
        if brownfield:
            argv+=['--repo',str(repo)]
        return run(argv+list(args),name,expected)

    def choice(text,basis='proposed',source='Maintainer proposal; not an owner confirmation.'):
        return {'text':text,'basis':basis,'source':source,'revisit':'Revisit when the owner corrects the choice or real-use evidence contradicts it.'}

    def product(customer,promise):
        result=copy.deepcopy(starter['product'])
        result.update(customer=choice(customer),proposition=choice(promise),
            problem=choice('Planning can expand before the first useful customer outcome is established.'),
            current_cost=choice('Unknown: the owner reports wasted effort but no measured time/cost was supplied.','unknown'),
            before_after=choice('Before: guess what matters. After: inspect promises, evidence, cuts and the next observable result.'),
            riskiest_assumption=choice('A stranger can get a useful first result from the packaged skill without its author.','unknown'),
            must_survive=[choice('Greenfield and brownfield are equally important.','owner-stated',
                'User, 2026-10-30: "Brown field and green field are equally important"'),
                choice('Drive to completion and value; preserve agency, value and priorities.','owner-stated',
                'User: "Do not do such mistake and drive this to completion and value"')],
            cuts=[choice('No new service, automatic code deletion, film production or model dependency in this slice.')],
            next_slice=choice('A maintainer can frame a new idea or inspect an existing feature, then obtain a source-bound impact answer and one next done-when check.'))
        shape=result['right_shape']
        shape.update(need={'N1':1,'N2':1,'N3':1,'N4':0},form='skill',engine='LLM',
            reason='The host curates customer promises and choices; deterministic local commands check paths, bytes and impact. No separate model or agent loop.',
            alternatives=['Just prose: lacks repeatable freshness and shared-file checks.',
                'A graph service or persistent agent: unnecessary for this bounded file-level first outcome.'],
            benchmark='This actual-repository command run plus a labelled idea, stale/unknown/share traps in tests, a leave-alone check and no adoption claim. Stop after recording one next slice.')
        return result

    brown=output/'brownfield';init(brown,'delivery-product','brown-init')
    census=command(brown,'inspect',brownfield=True,name='brown-inspect')
    assert census['commit']==head
    data=copy.deepcopy(starter);data.update(mode='brownfield',commit=head,
        product=product('Maintainer of an existing repository preparing a change.',
            'See which customer-visible features a file change can affect before editing.'))
    definitions=[
        ('workspace','Planning workspace initialization and inventory',
         ['plugins/delivery/scripts/project.py'], 'tests/delivery/test_project.py'),
        ('planning','Existing planning and review skill workflows',
         ['plugins/delivery/scripts/project.py']+[str(p.relative_to(repo)) for p in sorted((package/'skills').glob('*/SKILL.md')) if p.parent.name!='product'],
         'tests/delivery/test_package.py'),
        ('product-baseline','Greenfield and brownfield product records, feature impact and handoff',
         ['plugins/delivery/scripts/product.py','plugins/delivery/scripts/project.py','plugins/delivery/skills/product/SKILL.md'],
         'tests/delivery/test_product.py'),
        ('native-team','Persistent local Codex role coordination',
         ['plugins/delivery/scripts/runtime.py','plugins/delivery/scripts/codex_rpc.py','plugins/delivery/scripts/project.py'],
         'tests/delivery/test_runtime.py'),
        ('canonical-artifacts','Controlled canonical planning and review saves',
         ['plugins/delivery/scripts/artifacts.py','plugins/delivery/scripts/project.py'],
         'tests/delivery/test_artifacts.py'),
        ('controlled-review','Identity-bound Beads workflow and human acceptance',
         ['plugins/delivery/scripts/delivery_gates.py','plugins/delivery/scripts/operator_capture.py','plugins/delivery/scripts/runtime.py','plugins/delivery/scripts/project.py'],
         'tests/delivery/test_delivery_gates.py'),
        ('explicit-judge','Explicit Jev/OpenAI advisory judge selection',
         ['plugins/delivery/scripts/judge.js','plugins/delivery/scripts/lib/judge.js','plugins/delivery/scripts/lib/openai-judge.js'],
         'tests/delivery/openai-judge.test.js')]
    data['features']=[]
    for ident,name,code,evidence in definitions:
        feature=copy.deepcopy(starter['features'][0])
        feature.update(id=ident,name=name,state='preview',code=code,
            summary='Available in source preview; source and tests do not establish deployed acceptance.',
            evidence=[{'path':evidence,'note':'Executable test source; actual run is separate evidence, not outside-user use.'},
                {'path':'plugins/delivery/README.md','note':'Declared source preview and host limits; not independent deployment proof.'}],
            unknowns=['Outside-user first value and unprompted return have not been measured.',
                'Hook-event-log is a separate product component, intentionally outside this curated Delivery feature map.'])
        for criterion,card in feature['usefulness'].items():
            card.update(rating='Unknown' if criterion=='Return' else 'Partial',
                grade='Unknown' if criterion=='Return' else 'Claimed',
                evidence='Source and author-run checks only; no outside-user observation.',
                next_check='Observe a maintainer doing their own first task, then a dated unprompted return check.')
        data['features'].append(feature)
    brown_input=output/'brownfield-input.json';brown_input.write_text(json.dumps(data,indent=2)+'\n')
    saved=command(brown,'record','--input',str(brown_input),'--expected-sha256','new',brownfield=True,name='brown-record')
    impact=command(brown,'impact','--path','plugins/delivery/scripts/project.py',brownfield=True,name='brown-impact')
    assert {'workspace','product-baseline','native-team','canonical-artifacts','controlled-review'} <= {f['id'] for f in impact['features']}
    assert impact['freshness']['fresh'] is True
    retirement=command(brown,'retire-plan','--feature','workspace',brownfield=True,name='brown-retire-proposal')
    assert retirement['shared_code_to_preserve']['plugins/delivery/scripts/project.py']
    assert retirement['proposal_only'] and not retirement['exclusive_candidates_not_deletion_permission']
    handoff=command(brown,'handoff',brownfield=True,name='brown-handoff',expected=(1,))
    assert handoff['product']['must_survive'][0]['basis']=='owner-stated'
    assert handoff['unconfirmed_choices']
    assert command(brown,'status',brownfield=True,name='brown-status')['map_sha256']==saved['sha256']

    green=output/'greenfield';init(green,'new-plugin-idea','green-init')
    idea=copy.deepcopy(starter)
    idea['product']=product('Illustrative: maintainer designing a new local plugin capability.',
        'Illustrative: get one useful result with existing local tools before adding an autonomous agent.')
    idea['features'][0].update(name='Illustrative first useful local check',
        summary='Planned concept, not an implementation or a real customer claim.')
    green_input=output/'greenfield-input.json';green_input.write_text(json.dumps(idea,indent=2)+'\n')
    command(green,'inspect',name='green-inspect')
    command(green,'record','--input',str(green_input),'--expected-sha256','new',name='green-record')
    concept=command(green,'handoff',name='green-handoff',expected=(1,))
    assert concept['freshness']['fresh'] is None
    assert not (green/'.git').exists()
    assert concept['features'][0]['state']=='planned'
    summary={'source_commit':head,'brownfield':'Actual Delivery source, seven curated preview features; direct project.py impact answered.',
        'greenfield':'Illustrative idea only; no Git repository or invented code; shared product handoff works.',
        'owner_choice':'Actual user priority retained: greenfield and brownfield equally important.',
        'unconfirmed':'Primary customer, proposition and cuts remain proposed until owner correction/confirmation; no fabricated decision.',
        'usefulness':'Author-run evidence is Claimed, Return Unknown; no Seen or Repeated user evidence.',
        'retirement':'Read-only proposal preserved shared code; no feature retired.',
        'commands':len(calls),'qualification':'Real local command workflow, not host skill invocation, independent user use or authenticated dot integration.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
