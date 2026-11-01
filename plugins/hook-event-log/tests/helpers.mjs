import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdtemp, realpath, rm, readdir, readFile, stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
export const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export const events=['SessionStart','SessionEnd','UserPromptSubmit','PreToolUse','PostToolUse','PermissionRequest','SubagentStart','SubagentStop','PreCompact','PostCompact','Stop','Interrupt'];
export const failure='hook-event-log: event could not be recorded\n';
export const session='session-sentinel-must-never-appear';
export const hash=value=>createHash('sha256').update(value).digest('hex');
export const payload=(event='PreToolUse',extra={})=>JSON.stringify({hook_event_name:event,session_id:session,prompt:'secret-sentinel',tool_input:{secret:'secret-sentinel'},...extra});
export function invoke(data,directory,options={}) {
 return new Promise((accept,reject)=>{
  const env={...process.env};delete env.PLUGIN_DATA;
  if(directory!==undefined)env.PLUGIN_DATA=directory;
  const started=performance.now();
  const child=spawn(process.execPath,[join(options.root??root,'dist/hook.js')],{env,stdio:['pipe','pipe','pipe']});
  let stdout='',stderr='';
  child.stdout.on('data',b=>stdout+=b);child.stderr.on('data',b=>stderr+=b);
  child.stdin.on('error',()=>{});child.on('error',reject);
  child.on('close',(code,signal)=>accept({code,signal,stdout,stderr,ms:performance.now()-started}));
  if(!options.idle)child.stdin.end(data);
  const timer=setTimeout(()=>{child.kill('SIGKILL');reject(Error('Hook exceeded test watchdog'));},6000);
  child.on('close',()=>clearTimeout(timer));
 });
}
export async function isolated(fn){const directory=await realpath(await mkdtemp(join(tmpdir(),'hook-contract-')));try{return await fn(directory);}finally{await rm(directory,{recursive:true,force:true});}}
export function success(r){assert.equal(r.code,0,r.stderr);assert.equal(r.signal,null);assert.equal(r.stdout,'');assert.equal(r.stderr,'');}
export function fails(r){assert.equal(r.code,1);assert.equal(r.signal,null);assert.equal(r.stdout,'');assert.equal(r.stderr,failure);}
export async function published(directory,sessionId=session){
 const base=join(directory,'event-types-v2',hash(sessionId));
 let names;try{names=await readdir(base);}catch(e){if(e.code==='ENOENT')return [];throw e;}
 const result=[];
 for(const name of names.sort()){
  assert.match(name,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  const dir=join(base,name),path=join(dir,'record.jsonl');
  let bytes;try{bytes=await readFile(path,'utf8');}catch(e){if(e.code==='ENOENT')continue;throw e;}
  assert.ok(bytes.endsWith('\n'));assert.equal(bytes.split('\n').length,2);
  const info=await stat(path);assert.equal(info.nlink,1);assert.equal(info.mode&0o777,0o600);
  assert.equal((await stat(dir)).mode&0o777,0o700);
  if(process.geteuid)assert.equal(info.uid,process.geteuid());
  result.push({path,bytes,row:JSON.parse(bytes)});
 }
 return result;
}
export async function rows(directory,sessionId=session){return (await published(directory,sessionId)).map(x=>x.row);}
export function canonical(rows){return rows.map(x=>JSON.stringify(x,Object.keys(x).sort())).sort();}
