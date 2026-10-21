import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'plugins/delivery/scripts'))
from codex_rpc import CodexRPC
try:
    rpc=CodexRPC(str(ROOT),lambda m:None)
    result={'compatibility':rpc.compatibility}
    rpc.close()
except Exception as error:
    result={'error':str(error)}
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
