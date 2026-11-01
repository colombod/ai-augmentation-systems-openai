import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdir,writeFile,readFile,stat,link,symlink,chmod} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {root,isolated} from './helpers.mjs';

// Inject exact race boundaries in a separate process, exercising the shipped module.
// No production test switch or global process cwd change is introduced.
for(const stage of ['before-open','after-open','after-chdir','after-cwd-open']) {
 test(`directory substitution ${stage} never redirects a relative write`,()=>isolated(async directory=>{
  await mkdir(join(directory,'victim'),{mode:0o700});await mkdir(join(directory,'outside'),{mode:0o700});await writeFile(join(directory,'outside','sentinel'),'unchanged');
  const script=`import fs from 'node:fs';import {syncBuiltinESMExports} from 'node:module';
const base=${JSON.stringify(directory)},stage=${JSON.stringify(stage)};
const nativeOpen=fs.openSync,nativeChdir=process.chdir.bind(process);let swapped=false;
function swap(){if(swapped)return;swapped=true;fs.renameSync(base+'/victim',base+'/parked');fs.symlinkSync(base+'/outside',base+'/victim');}
fs.openSync=function(name,...rest){if(name==='victim'&&stage==='before-open')swap();const fd=nativeOpen.call(fs,name,...rest);if(name==='victim'&&stage==='after-open')swap();if(name==='.'&&stage==='after-cwd-open'&&process.cwd()===base+'/victim')swap();return fd;};
process.chdir=function(name){nativeChdir(name);if(name==='victim'&&stage==='after-chdir')swap();};
syncBuiltinESMExports();const {enterRoot}=await import(${JSON.stringify(pathToFileURL(join(root,'dist/filesystem.js')).href)});
let accepted=false;try{enterRoot(base+'/victim');fs.writeFileSync('marker','pinned',{flag:'wx',mode:0o600});accepted=true;}catch{}
console.log(JSON.stringify({accepted,swapped}));`;
  const result=spawnSync(process.execPath,['--input-type=module','-e',script],{encoding:'utf8',timeout:4000});assert.equal(result.status,0,result.stderr);assert.equal(result.stderr,'');const observation=JSON.parse(result.stdout);assert.equal(observation.swapped,true);
  assert.equal(await readFile(join(directory,'outside','sentinel'),'utf8'),'unchanged');await assert.rejects(stat(join(directory,'outside','marker')),{code:'ENOENT'});
  const expected=stage==='after-chdir'||stage==='after-cwd-open';assert.equal(observation.accepted,expected);
  if(expected)assert.equal(await readFile(join(directory,'parked','marker'),'utf8'),'pinned');else await assert.rejects(stat(join(directory,'parked','marker')),{code:'ENOENT'});
 }));
}

test('parent rename does not redirect the next child traversal',()=>isolated(async directory=>{
 await mkdir(join(directory,'parent','child'),{recursive:true,mode:0o700});await mkdir(join(directory,'outside','child'),{recursive:true,mode:0o700});
 const script=`import fs from 'node:fs';import {enterRoot,enterChild} from ${JSON.stringify(pathToFileURL(join(root,'dist/filesystem.js')).href)};
enterRoot(${JSON.stringify(join(directory,'parent'))});fs.renameSync(${JSON.stringify(join(directory,'parent'))},${JSON.stringify(join(directory,'parked'))});fs.symlinkSync(${JSON.stringify(join(directory,'outside'))},${JSON.stringify(join(directory,'parent'))});enterChild('child');fs.writeFileSync('marker','pinned',{flag:'wx',mode:0o600});`;
 const result=spawnSync(process.execPath,['--input-type=module','-e',script],{encoding:'utf8',timeout:4000});assert.equal(result.status,0,result.stderr);assert.equal(result.stderr,'');assert.equal(await readFile(join(directory,'parked','child','marker'),'utf8'),'pinned');await assert.rejects(stat(join(directory,'outside','child','marker')),{code:'ENOENT'});
}));

test('readable-object guard rejects hardlinks, symlinks, public modes and FIFOs',()=>isolated(async directory=>{
 const original=join(directory,'original');await writeFile(original,'unchanged',{mode:0o600});await link(original,join(directory,'hardlink'));await symlink(original,join(directory,'symlink'));await writeFile(join(directory,'public'),'unchanged',{mode:0o600});await chmod(join(directory,'public'),0o644);const fifo=spawnSync('mkfifo',[join(directory,'fifo')]);assert.equal(fifo.status,0);
 const script=`import {enterRoot,openRegular} from ${JSON.stringify(pathToFileURL(join(root,'dist/filesystem.js')).href)};import {closeSync} from 'node:fs';enterRoot(${JSON.stringify(directory)});const result={};for(const name of ['original','hardlink','symlink','public','fifo']){try{const fd=openRegular(name);closeSync(fd);result[name]=true;}catch{result[name]=false;}}console.log(JSON.stringify(result));`;
 const result=spawnSync(process.execPath,['--input-type=module','-e',script],{encoding:'utf8',timeout:3000});assert.equal(result.status,0,result.stderr);assert.deepEqual(JSON.parse(result.stdout),{original:false,hardlink:false,symlink:false,public:false,fifo:false});assert.equal(await readFile(original,'utf8'),'unchanged');
}));
