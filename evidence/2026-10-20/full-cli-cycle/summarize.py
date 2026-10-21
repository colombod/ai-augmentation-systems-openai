"""Read-only post-run checks, durable snapshots and measured native usage."""
from pathlib import Path
import collections,hashlib,json,shutil,sqlite3,subprocess,time
BASE=Path(__file__).resolve().parent
initial=json.loads((BASE/'result.json').read_text());cont=json.loads((BASE/'continuation/result.json').read_text());ledger=json.loads((BASE/'continuation/events.json').read_text());events=ledger['events'];product=Path(initial['product']);planning=Path(initial['planning'])
def git(*args):
 p=subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false','-c','core.untrackedCache=false','-C',str(product),*args],capture_output=True,check=True);return p.stdout
head=git('rev-parse','HEAD').decode().strip();snapshot=BASE/'product-snapshot';snapshot.mkdir(exist_ok=True)
files=[]
for name in git('ls-tree','-r','--name-only',head).decode().splitlines():
 path=Path(name)
 if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe fixture tree path')
 payload=git('show',head+':'+name);dest=snapshot/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
 files.append({'path':name,'sha256':hashlib.sha256(payload).hexdigest(),'actual_worktree_matches_commit':(product/path).read_bytes()==payload})
artifacts=[]
for event in events:
 if event['kind']=='artifact_saved':
  value=event['data'];source=Path(value['path']);payload=source.read_bytes();destination=BASE/'canonical-artifact-snapshot'/value['relative_path'];destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(payload)
  artifacts.append({'event_id':event['id'],**value,'current_sha256':hashlib.sha256(payload).hexdigest(),'matches_saved_event':hashlib.sha256(payload).hexdigest()==value['sha256']})
source=product/'.delivery-evidence/builder-tests.txt'
if source.exists():shutil.copy2(source,BASE/'builder-tests.txt')
roles={r['name']:r for r in ledger['roles']};usage_events=collections.defaultdict(list);terminal_turns=collections.defaultdict(list)
for event in events:
 if event['kind']=='thread/tokenUsage/updated':
  value=event['data'];usage_events[value['role']].append({'event_id':event['id'],'time':event['time'],'native':value['native']})
 if event['kind']=='turn_terminal':
  value=event['data'];terminal_turns[value['role']].append({'event_id':event['id'],'thread':value['native']['threadId'],**value['native']['turn']})
usage={}
for role,entries in usage_events.items():
 resets=[];previous=-1
 for e in entries:
  total=e['native']['tokenUsage']['total']['totalTokens']
  if total<previous:resets.append({'event_id':e['event_id'],'previous_total':previous,'current_total':total})
  previous=total
 usage[role]={'native_reported_latest_total':entries[-1]['native']['tokenUsage']['total'],'counter_resets_detected':resets,'usage_event_count':len(entries),'completed_turns':len(terminal_turns[role]),'native_completed_turn_duration_ms':sum(t.get('durationMs',0) for t in terminal_turns[role]),'turns':[{'id':t['id'],'thread':t['thread'],'status':t['status'],'durationMs':t.get('durationMs')} for t in terminal_turns[role]]}
(BASE/'native-token-usage-events.json').write_text(json.dumps(usage_events,indent=2)+'\n')
control=[]
for event in events:
 if event['kind']=='controlled_tool_result':control.append({'event_id':event['id'],'time':event['time'],**event['data']})
errors=[e for e in control if not e['result']['success']]
judge=[e for e in control if e['tool']=='delivery_judge'];root_grade=json.loads((BASE/'root-acceptance/black-box-results.json').read_text());proof=json.loads((BASE/'continuation/queue-proof.json').read_text())
implementation=initial['implementation'];review=initial['review'];surface=initial['surface_submission']
checks={'public_full_roster_five_roles':set(roles)=={'coordinator','product-manager','delivery-manager','builder','reviewer'},'all_roles_actual_completed_native_turns':all(terminal_turns[name] for name in roles),'actual_pm_continuity':json.loads((BASE/'pm-restart-actual-queue-proof.json').read_text())['same_thread'],'canonical_artifact_bytes_match_protected_saves':all(a['matches_saved_event'] for a in artifacts),'actual_committed_worktree_bytes_match':all(f['actual_worktree_matches_commit'] for f in files),'matching_builder_review_surface_head':head==implementation['head']==review['head']==surface['head'],'independent_native_reviewer':review['actor']['thread']!=implementation['actor']['thread'],'root_holdout_21_pass':len(root_grade['cases'])==21 and all(c['passed'] for c in root_grade['cases']),'real_peer_handoff':any(e['tool']=='delivery_send' and e['result']['success'] for e in control),'real_openai_advisory':any('"model": "gpt-6-luna"' in e['result']['contentItems'][0]['text'] and '"answer":' in e['result']['contentItems'][0]['text'] for e in judge),'exact_final_queued_turn_proven':proof['actual_new_turn'] and proof['same_native_thread'] and proof['native_status']=='completed','submissions_complete_unaccepted':cont['gate_status']['submissions_complete'] and not cont['gate_status']['accepted'],'actual_acceptance_refusal':bool(cont['acceptance_refusals']),'beads_still_in_progress':cont['canonical_task']['status']=='in_progress','no_accepted_gate_event':not any(e['kind']=='delivery_gate' and e['data'].get('action')=='accepted' for e in events)}
summary={'kind':'staged real-model public CLI delivery integration through operator acceptance barrier','not_one_prompt_autonomy':True,'not_desktop_or_chatgpt_acceptance':True,'actual_executed_drivers':['runner-initial.py','continuation.py'],'future_runner_not_executed':'runner.py','fixture':initial['fixture'],'product':str(product),'planning':str(planning),'issue':initial['issue'],'head':head,'accepted':False,'checks':checks,'all_checks_pass':all(checks.values()),'walltime_seconds':round(cont['finished_at']-initial['started_at'],3),'initial_driver_seconds':round(initial['finished_at']-initial['started_at'],3),'continuation_seconds':round(cont['finished_at']-cont['started_at'],3),'usage_by_role':usage,'usage_limits':'Raw native cumulative counters as reported. Resets are flagged; these whole-host/context counts do not isolate plugin overhead, establish a no-plugin baseline, measure provider price or prove statistical reliability. Native turn durations can overlap.','product_files':files,'canonical_artifacts':artifacts,'controlled_tool_counts':dict(collections.Counter(e['tool'] for e in control)),'controlled_tool_failures':errors,'initial_harness_error_preserved':initial['error'],'interventions':['corrected malformed optional judge input in a new native coordinator turn','revoked prohibited out-of-sandbox request; exact-turn steer to supported staged-index Git commit and cache cleanup','restarted public serve to consume existing queued final DM message after original harness race'],'separate_root_grade':{'cases':len(root_grade['cases']),'passed':sum(c['passed'] for c in root_grade['cases']),'source_unchanged':root_grade['source_unchanged']},'evidence_trust':'Native command journals + protected actor-bound submissions + actual file/Beads/Git checks; worker surface submissions remain unauthenticated. No real human receipt or hosted CI.'}
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(BASE/'controlled-tool-results.json').write_text(json.dumps(control,indent=2)+'\n');(BASE/'canonical-task.json').write_text(json.dumps(cont['canonical_task'],indent=2)+'\n')
print(json.dumps({'all_checks_pass':summary['all_checks_pass'],'checks':checks,'walltime_seconds':summary['walltime_seconds'],'usage':{name:value['native_reported_latest_total'] for name,value in usage.items()}},indent=2))
