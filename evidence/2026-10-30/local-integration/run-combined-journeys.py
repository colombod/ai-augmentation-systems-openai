import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

repo=Path('/workspace/delivery-integration');out=Path('/tmp/delivery-integration-evidence')
package=repo/'plugins/delivery';head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
calls=[]

def run(name,argv,accepted=(0,)):
 r=subprocess.run(argv,capture_output=True,text=True,timeout=60)
 calls.append({'name':name,'argv':argv,'stdout':r.stdout,'stderr':r.stderr,'exit_code':r.returncode})
 if r.returncode not in accepted:raise AssertionError(calls[-1])
 return json.loads(r.stdout)

results={}
with tempfile.TemporaryDirectory(prefix='delivery-integration-journeys-') as temporary:
 base=Path(temporary)
 for mode in ['brownfield','greenfield']:
  project=base/mode;project.mkdir()
  run(mode+'-init',[sys.executable,str(package/'scripts/project.py'),'init','--project',str(project),'--initiative','integration'])
  def product(name,*args,accepted=(0,)):
   argv=[sys.executable,str(package/'scripts/product.py'),'--project',str(project)]
   if mode=='brownfield':argv+=['--repo',str(repo)]
   return run(mode+'-'+name,argv+list(args),accepted)
  outline={'product':{'customer':'Proposed maintainers','proposition':'Proposed evidence-backed change decisions',
                      'must_survive':['Preserve owner intent and shared code'], 'cuts':['No automatic deletion']},
           'features':[{'id':'coordination','name':'Native coordination source','code':['plugins/delivery/scripts/runtime.py']},
                       {'id':'controlled-work','name':'Controlled workflow source','code':['plugins/delivery/scripts/delivery_gates.py']}]}
  if mode=='greenfield':
   for feature in outline['features']:feature.pop('code')
  outline_path=project/'outline.json';outline_path.write_text(json.dumps(outline))
  draft=product('draft','draft','--outline',str(outline_path))
  assert all(f['state']=='planned' for f in draft['features'])
  assert all(card['rating']=='Unknown' and card['grade']=='Unknown' for f in draft['features'] for card in f['usefulness'].values())
  assert draft['product']['customer']['basis']=='proposed'
  assert not (project/'.delivery/product-map.json').exists()
  draft_path=project/'draft.json';draft_path.write_text(json.dumps(draft))
  saved=product('record','record','--input',str(draft_path),'--expected-sha256','new')
  target='plugins/delivery/scripts/operator_capture.py' if mode=='brownfield' else 'future.py'
  direct=product('direct','impact','--path',target)
  graph=product('transitive','impact','--path',target,'--transitive')
  assert direct['features']==graph['features']==[]
  retirement=product('retirement','retire-plan','--feature','coordination','--transitive')
  handoff=product('handoff','handoff',accepted=(1,))
  assert handoff['unconfirmed_choices'] and 'authority' in handoff
  assert retirement['proposal_only'] and retirement['required_owner_decision']['choice']=='unknown'
  assert saved['sha256']==handoff['map_sha256']
  if mode=='brownfield':
   assert draft['commit']==head and graph['transitive']['freshness']['fresh']
   assert {f['id'] for f in graph['transitive']['features']}=={'coordination','controlled-work'}
   assert retirement['transitive']['shared_code_to_preserve'][target]==['controlled-work']
   # Use the combined runtime's synthetic active role to test its write boundary,
   # not a native host or actual authenticated operator.
   sys.path.insert(0,str(package/'scripts'))
   from runtime import Store
   from artifacts import ArtifactService,ArtifactError
   store=Store(project)
   spec={'cwd':str(project),'lane':'read-only'}
   store.db.execute("INSERT INTO roles VALUES(?,?,?,?,'active',NULL)",('product-manager',json.dumps(spec),'thread-test','turn-test'))
   actor={'role':'product-manager','thread':'thread-test','turn':'turn-test','lane':'read-only'}
   before=(project/'.delivery/product-map.json').read_bytes()
   try:
    ArtifactService(store).write({'path':'product-map.json','content':'{}','expected_sha256':saved['sha256']},actor)
    raise AssertionError('Native role unexpectedly acquired product-map write lane')
   except ArtifactError as error:denial=str(error)
   assert (project/'.delivery/product-map.json').read_bytes()==before
   store.db.close()
   results['runtime_product_map_boundary']={'denied':True,'reason':denial,'record_unchanged':True,'qualification':'Synthetic active actor/API boundary; not live native role execution'}
  else:
   assert draft['commit'] is None and all(not f['code'] for f in draft['features'])
   assert not graph['transitive']['available'] and 'reason' in graph['transitive']
  results[mode]={'compact_draft_to_record':True,'direct_and_optional_impact':True,'retirement_proposal':True,
                 'handoff_preserves_proposed_choices_and_unknown_usefulness':True}

# Preserve implementation identities across the automatically merged code files.
def functions(data):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(data).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
def source(sha,path):return subprocess.check_output(['git','-C',str(repo),'show',sha+':'+path])
path='plugins/delivery/scripts/product.py'
draft_funcs=functions(source('6c95dc4311b13b084f6b9a87e56c2e8aa128902e',path))
graph_funcs=functions(source('d02db2f5de2a39a721f59d3080c3f56abee61071',path))
expected={**draft_funcs,**graph_funcs};actual=functions((repo/path).read_bytes())
assert {k:v for k,v in expected.items() if k!='main'}=={k:v for k,v in actual.items() if k!='main'}
identical={}
for path in ['runtime.py','delivery_gates.py','supervision.py','verification.py']:
 relative='plugins/delivery/scripts/'+path
 assert source('33146a95c2e1bd1ce0c1a0b6215a88be4cb44de4',relative)==(repo/relative).read_bytes()
 identical[path]=hashlib.sha256((repo/relative).read_bytes()).hexdigest()
results.update(integration_commit=head,public_commands=len(calls),source_functions_preserved=True,supervision_files_unchanged=identical,
               qualification='Unshipped local integration; deterministic helper/API checks only; no live models, dot authentication or coordinated native execution')
(out/'combined-journey-commands.json').write_text(json.dumps(calls,indent=2)+'\n')
(out/'combined-journeys.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
