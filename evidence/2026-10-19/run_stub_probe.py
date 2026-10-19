"""Exercise Codex against a loopback transport stub. No real model or credentials."""
import os,json,subprocess,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
b=Path(os.environ.get('DELIVERY_PROBE_ROOT', '/private/tmp/openai-marketplace-validation'))
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  self.rfile.read(int(self.headers.get('Content-Length',0)))
  item={'id':'msg_probe','type':'message','role':'assistant','content':[{'type':'output_text','text':'MECHANISM_PROBE_OK','annotations':[]}]}
  r={'id':'resp_probe','object':'response','created_at':int(time.time()),'status':'completed','model':'probe','output':[item],'usage':{'input_tokens':1,'output_tokens':1,'total_tokens':2}}
  events=[('response.created',{'response':{**r,'status':'in_progress','output':[]}}),('response.output_item.added',{'output_index':0,'item':{**item,'content':[]}}),('response.output_text.delta',{'item_id':'msg_probe','output_index':0,'content_index':0,'delta':'MECHANISM_PROBE_OK'}),('response.output_item.done',{'output_index':0,'item':item}),('response.completed',{'response':r})]
  body=''.join('event: '+n+'\ndata: '+json.dumps({'type':n,**v})+'\n\n' for n,v in events).encode()
  self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=srv.serve_forever,daemon=True).start()
config=b/'home/config.toml'
s=config.read_text().split('[model_providers.probe]')[0];s=s.replace('model_provider = "probe"\n','');s+='\nmodel_provider = "probe"\n[model_providers.probe]\nname = "Loopback probe"\nbase_url = "http://127.0.0.1:'+str(srv.server_port)+'/v1"\nwire_api = "responses"\nrequires_openai_auth = false\n'
# model_provider must be top-level, not in the preceding plugin table.
s='model_provider = "probe"\n'+s.replace('\nmodel_provider = "probe"\n','\n')
config.write_text(s)
e=dict(os.environ,CODEX_HOME=str(b/'home'),PROBE_LOG=str(b/'hook-events.ndjson'))
try:
 args=['codex','--dangerously-bypass-hook-trust','exec','--skip-git-repo-check','--json','-C',str(b/'fixture'),'-m','probe','Return the mechanism probe marker. Do not call tools.']
 r=subprocess.run(args,env=e,text=True,capture_output=True,timeout=45)
 (b/'stub-cli.stdout.ndjson').write_text(r.stdout);(b/'stub-cli.stderr.log').write_text(r.stderr)
 print(json.dumps({'exit':r.returncode,'stdout':r.stdout[-2000:],'stderr':r.stderr[-1200:]}))
finally:srv.shutdown()
