import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFile,readdir,mkdir,symlink,stat,cp,writeFile,chmod} from 'node:fs/promises';
import {join} from 'node:path';
import {root,events,session,hash,payload,invoke,isolated,success,fails,published,rows,canonical} from './helpers.mjs';

test('all twelve events retain exact allowlisted JSONL and SHA256 routing',()=>isolated(async directory=>{
 for(const event of events)success(await invoke(payload(event),directory));
 assert.deepEqual(await readdir(directory),['event-types-v2']);
 assert.deepEqual(await readdir(join(directory,'event-types-v2')),[hash(session)]);
 const output=await published(directory);
 assert.deepEqual(canonical(output.map(x=>x.row)),canonical(events.map(event_type=>({event_type}))));
 assert.ok(output.every(x=>!x.bytes.includes('sentinel')));
 for(const path of [join(directory,'event-types-v2'),join(directory,'event-types-v2',hash(session))])assert.equal((await stat(path)).mode&0o777,0o700);
 success(await invoke(payload('Stop',{session_id:'different-session'}),directory));
 assert.equal((await rows(directory,'different-session')).length,1);
}));

test('32 concurrent invocations publish complete distinct records',()=>isolated(async directory=>{
 const input=Array.from({length:32},(_,i)=>payload('SubagentStop',{agent_id:`${i}-`+'\\"'.repeat(500),agent_type:'t'.repeat(256),agent_transcript_path:'/'+'p'.repeat(4095)}));
 (await Promise.all(input.map(p=>invoke(p,directory)))).forEach(success);
 const output=await rows(directory);assert.equal(output.length,32);
 assert.equal(new Set(output.map(x=>x.agent_id)).size,32);
 for(const row of output){assert.equal(row.event_type,'SubagentStop');assert.equal(row.agent_type,'t'.repeat(256));assert.equal(row.agent_transcript_path,'/'+'p'.repeat(4095));assert.equal(Object.keys(row).length,4);}
}));

test('invalid JSON, UTF8, identifiers and events create nothing',()=>isolated(async directory=>{
 const invalid=['{secret-sentinel','[]','{}',payload('Unknown'),payload('Stop',{session_id:''}),payload('Stop',{session_id:null}),payload('Stop',{session_id:'\u0085'}),payload('Stop',{session_id:'s'.repeat(1025)}),payload('Stop',{session_id:'é'.repeat(513)}),'{"hook_event_name":"Stop","session_id":"s","unknown":1e400}','{"hook_event_name":"Stop","session_id":"s","unknown":"\\ud800"}','{"hook_event_name":"Stop","session_id":"s","unknown":"\\ud800","unknown":"ok"}','{"hook_event_name":"Stop","session_id":"s","unknown":'+'['.repeat(200)+'0'+']'.repeat(200)+'}',Buffer.concat([Buffer.from(payload()),Buffer.from([0xff])]),Buffer.concat([Buffer.from([0xef,0xbb,0xbf]),Buffer.from(payload())])];
 for(const input of invalid)fails(await invoke(input,directory));
 assert.deepEqual(await readdir(directory),[]);
}));

test('session byte boundaries, Unicode whitespace and duplicate keys match input contract',()=>isolated(async directory=>{
 for(const id of ['s'.repeat(1024),'é'.repeat(512),'\ufeff','\u0000','雪'])success(await invoke(payload('Stop',{session_id:id}),directory));
 for(const id of ['s'.repeat(1024),'é'.repeat(512),'\ufeff','\u0000','雪'])assert.equal((await rows(directory,id)).length,1);
 success(await invoke('{"hook_event_name":"Stop","session_id":"first","session_id":"last"}',directory));
 assert.equal((await rows(directory,'first')).length,0);assert.equal((await rows(directory,'last')).length,1);
}));

test('absent, empty, relative and parent-traversal roots fail privately',async()=>{
 for(const directory of [undefined,'','relative-data-sentinel','/tmp/../tmp'])fails(await invoke(payload(),directory));
});

test('exact 1 MiB accepted and one byte over rejected without another record',()=>isolated(async directory=>{
 const base=payload('Stop',{padding:''});const input=payload('Stop',{padding:'x'.repeat(1048576-Buffer.byteLength(base))});
 assert.equal(Buffer.byteLength(input),1048576);success(await invoke(input,directory));fails(await invoke(input+' ',directory));assert.equal((await rows(directory)).length,1);
}));

test('symlink at each writable root level is refused without outside changes', {skip:process.platform==='win32'},()=>isolated(async directory=>{
 const outside=join(directory,'outside');await mkdir(outside,{mode:0o700});await writeFile(join(outside,'sentinel'),'unchanged');
 for(const level of ['ancestor','root','namespace','session']){
  const base=join(directory,level);await mkdir(base,{mode:0o700});let data=join(base,'data');
  if(level==='ancestor'){await symlink(outside,join(base,'alias'));data=join(base,'alias','data');}
  else if(level==='root')await symlink(outside,data);
  else{await mkdir(data,{mode:0o700});if(level==='namespace')await symlink(outside,join(data,'event-types-v2'));else{await mkdir(join(data,'event-types-v2'),{mode:0o700});await symlink(outside,join(data,'event-types-v2',hash(session)));}}
  fails(await invoke(payload(),data));assert.deepEqual(await readdir(outside),['sentinel']);assert.equal(await readFile(join(outside,'sentinel'),'utf8'),'unchanged');
 }
}));

test('nonprivate namespace or session directory rejected without chmod or record',()=>isolated(async directory=>{
 for(const level of ['namespace','session']){
  const data=join(directory,level);await mkdir(join(data,'event-types-v2'),{recursive:true,mode:0o700});
  const unsafe=level==='namespace'?join(data,'event-types-v2'):join(data,'event-types-v2',hash(session));if(level==='session')await mkdir(unsafe,{mode:0o700});
  await chmod(unsafe,0o755);fails(await invoke(payload(),data));assert.equal((await stat(unsafe)).mode&0o777,0o755);assert.deepEqual(await readdir(unsafe),[]);
 }
}));

test('regular file and FIFO namespace targets fail without blocking or mutation', {skip:process.platform==='win32'},()=>isolated(async directory=>{
 for(const kind of ['file','fifo']){
  const data=join(directory,kind);await mkdir(data,{mode:0o700});const target=join(data,'event-types-v2');
  if(kind==='file')await writeFile(target,'unchanged',{mode:0o600});else{const setup=spawnSync('mkfifo',[target]);assert.equal(setup.status,0,setup.stderr?.toString());}
  const result=await invoke(payload(),data);fails(result);assert.ok(result.ms<3000);
  if(kind==='file')assert.equal(await readFile(target,'utf8'),'unchanged');else assert.ok((await stat(target)).isFIFO());
 }
}));

test('new logging leaves legacy records and unrelated files byte-identical',()=>isolated(async directory=>{
 await mkdir(join(directory,'event-types'),{mode:0o700});const legacy=join(directory,'event-types',hash(session)+'.jsonl');const original='{"event_type":"SessionStart"}\n{"event_type":"SubagentStop","agent_id":"old"}\n';
 await writeFile(legacy,original,{mode:0o600});await writeFile(join(directory,'unrelated'),'sentinel');const before=await stat(legacy);
 success(await invoke(payload('Stop'),directory));assert.equal(await readFile(legacy,'utf8'),original);assert.equal((await stat(legacy)).ino,before.ino);assert.equal((await stat(legacy)).mtimeMs,before.mtimeMs);assert.equal(await readFile(join(directory,'unrelated'),'utf8'),'sentinel');assert.deepEqual(await rows(directory),[{event_type:'Stop'}]);
}));

test('idle stdin terminates below registered hook timeout',()=>isolated(async directory=>{
 const result=await invoke('',directory,{idle:true});fails(result);assert.ok(result.ms<3000,`Idle runtime ${result.ms} ms`);assert.deepEqual(await readdir(directory),[]);
}));

test('missing and hung Node workers retain fixed deadline failure',()=>isolated(async directory=>{
 const fixture=join(directory,'fixture');await mkdir(join(fixture,'dist'),{recursive:true});await cp(join(root,'dist/hook.js'),join(fixture,'dist/hook.js'));await writeFile(join(fixture,'package.json'),'{"type":"module"}');
 fails(await invoke(payload(),join(directory,'data'),{root:fixture}));
 await writeFile(join(fixture,'dist/core.js'),'while (true) {}\n');const result=await invoke(payload(),join(directory,'data'),{root:fixture});fails(result);assert.ok(result.ms>=2350&&result.ms<3000,`Hung worker runtime ${result.ms} ms`);
}));

test('registration and compatibility manifest expose all twelve hooks',async()=>{
 const config=JSON.parse(await readFile(join(root,'hooks/hooks.json'),'utf8'));assert.deepEqual(Object.keys(config.hooks).sort(),[...events].sort());
 for(const group of Object.values(config.hooks)){assert.equal(group[0].hooks[0].timeout,3);assert.equal(group[0].hooks[0].command,'node "${PLUGIN_ROOT}/dist/hook.js"');}
 const manifest=JSON.parse(await readFile(join(root,'.codex-plugin/plugin.json'),'utf8'));assert.equal(manifest.hooks,'./hooks/hooks.json');await assert.rejects(stat(join(root,'plugin.json')),{code:'ENOENT'});
});
