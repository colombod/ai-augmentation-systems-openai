import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdir,writeFile,readFile,readdir,stat} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {root,isolated,session,hash,payload} from './helpers.mjs';
const id='00000000-0000-4000-8000-000000000000';
function injected(directory,extra=''){
 const script=`import fs from 'node:fs';import crypto from 'node:crypto';import {syncBuiltinESMExports} from 'node:module';crypto.randomUUID=()=>${JSON.stringify(id)};${extra};syncBuiltinESMExports();await import(${JSON.stringify(pathToFileURL(join(root,'dist/core.js')).href)});`;
 return spawnSync(process.execPath,['--input-type=module','-e',script],{input:payload('Stop'),encoding:'utf8',env:{...process.env,PLUGIN_DATA:directory},timeout:4000});
}

test('event-directory collision cannot reuse or overwrite an existing record',()=>isolated(async directory=>{
 const target=join(directory,'event-types-v2',hash(session),id);await mkdir(target,{recursive:true,mode:0o700});await writeFile(join(target,'record.jsonl'),'{"event_type":"SessionStart"}\n',{mode:0o600});
 const result=injected(directory);assert.equal(result.status,1);assert.equal(result.stdout,'');assert.equal(result.stderr,'hook-event-log: operation failed\n');assert.equal(await readFile(join(target,'record.jsonl'),'utf8'),'{"event_type":"SessionStart"}\n');assert.deepEqual(await readdir(target),['record.jsonl']);
}));

for(const point of ['before-publish','after-publish'])test(`failure ${point} preserves only the appropriate publication state`,()=>isolated(async directory=>{
 const extra=point==='before-publish'?"fs.renameSync=()=>{throw new Error('synthetic')}":"const originalRename=fs.renameSync;fs.renameSync=(...args)=>{originalRename(...args);throw new Error('synthetic')}";
 const result=injected(directory,extra);assert.equal(result.status,1);assert.equal(result.stdout,'');assert.equal(result.stderr,'hook-event-log: operation failed\n');
 const target=join(directory,'event-types-v2',hash(session),id);const expected=point==='before-publish'?'pending':'record.jsonl';assert.deepEqual(await readdir(target),[expected]);assert.equal(await readFile(join(target,expected),'utf8'),'{"event_type":"Stop"}\n');assert.equal((await stat(join(target,expected))).nlink,1);
}));

test('partial writes are completed only within the unique pending file',()=>isolated(async directory=>{
 const result=injected(directory,"const originalWrite=fs.writeSync;fs.writeSync=(fd,buffer,offset,length,position)=>originalWrite(fd,buffer,offset,Math.min(length,3),position)");assert.equal(result.status,0,result.stderr);assert.equal(result.stdout,'');assert.equal(result.stderr,'');
 const target=join(directory,'event-types-v2',hash(session),id);assert.deepEqual(await readdir(target),['record.jsonl']);assert.equal(await readFile(join(target,'record.jsonl'),'utf8'),'{"event_type":"Stop"}\n');
}));

for(const point of ['before-publish','after-publish'])test(`process death ${point} leaves a recoverable publication state`,()=>isolated(async directory=>{
 const extra=point==='before-publish'?"fs.renameSync=()=>{process.kill(process.pid,'SIGKILL')}":"const originalRename=fs.renameSync;fs.renameSync=(...args)=>{originalRename(...args);process.kill(process.pid,'SIGKILL')}";
 const result=injected(directory,extra);assert.equal(result.status,null);assert.equal(result.signal,'SIGKILL');assert.equal(result.stdout,'');assert.equal(result.stderr,'');
 const target=join(directory,'event-types-v2',hash(session),id);const expected=point==='before-publish'?'pending':'record.jsonl';assert.deepEqual(await readdir(target),[expected]);assert.equal(await readFile(join(target,expected),'utf8'),'{"event_type":"Stop"}\n');assert.equal((await stat(join(target,expected))).nlink,1);
}));
