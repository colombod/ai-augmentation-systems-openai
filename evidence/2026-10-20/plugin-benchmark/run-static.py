from pathlib import Path
import subprocess, concurrent.futures, json
root=Path('/Users/colombod/workspaces/delivery-plugin-openai')
out=root/'evidence/2026-10-20/plugin-benchmark/static-skills';out.mkdir(parents=True,exist_ok=True)
cli='/Users/colombod/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js'
def run(path):
 r=subprocess.run(['node',cli,'analyze',str(path),'--format','json','--output',str(out/(path.name+'.json'))],capture_output=True,text=True)
 return {'skill':path.name,'exit_code':r.returncode,'stderr':r.stderr}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: rows=list(pool.map(run,sorted((root/'plugins/delivery/skills').iterdir())))
(out/'runs.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
