import sys,json,os
from pathlib import Path
p=json.load(sys.stdin)
log=Path(os.environ["PROBE_LOG"])
with log.open("a") as f:f.write(json.dumps({k:p.get(k) for k in ["hook_event_name","session_id","turn_id","tool_name","source"]})+"\n")
