import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdir,writeFile,readFile,stat,chmod,readdir} from 'node:fs/promises';
import {join} from 'node:path';
import {events,session,hash,payload,invoke,isolated,success,rows,canonical} from './helpers.mjs';

test('subagent fields are scoped to the right events and escaped without content capture',()=>isolated(async directory=>{
 const fields={agent_id:'child-"quoted"-\\-雪',agent_type:'reviewer',agent_transcript_path:'/nonexistent/host transcript.jsonl',parent_agent_id:'EXCLUDED',last_assistant_message:'EXCLUDED',tool_response:'EXCLUDED',event_log_path:'EXCLUDED'};
 for(const event of events)success(await invoke(payload(event,fields),directory));
 const output=await rows(directory);
 const expected=events.map(event_type=>{const record={event_type};if(event_type==='SubagentStart'||event_type==='SubagentStop'){record.agent_id=fields.agent_id;record.agent_type=fields.agent_type;}if(event_type==='SubagentStop')record.agent_transcript_path=fields.agent_transcript_path;return record;});
 assert.deepEqual(canonical(output),canonical(expected));assert.ok(!JSON.stringify(output).includes('EXCLUDED'));assert.deepEqual(await readdir(join(directory,'event-types-v2')),[hash(session)]);
}));

test('invalid optional metadata is omitted without losing the event',()=>isolated(async directory=>{
 const generic=[null,42,false,[],{unknown:'excluded'},'','  ','\u0085','bad\nfield','bad\u0085field','bad\u0000field','bad\u007ffield'];let count=0;
 for(const [field,limit] of [['agent_id',1024],['agent_type',256],['agent_transcript_path',4096]]){
  const invalid=[...generic,'/'+'x'.repeat(limit),'/'+'é'.repeat(limit/2)];if(field==='agent_transcript_path')invalid.push('relative/transcript.jsonl');
  for(const value of invalid){success(await invoke(payload('SubagentStop',{[field]:value}),directory));count++;}
 }
 assert.deepEqual(await rows(directory),Array.from({length:count},()=>({event_type:'SubagentStop'})));
}));

test('optional metadata accepts exact UTF8 byte limits and preserves BOM characters',()=>isolated(async directory=>{
 const fields={agent_id:'é'.repeat(512),agent_type:'é'.repeat(128),agent_transcript_path:'/'+'p'.repeat(4095)};
 success(await invoke(payload('SubagentStop',fields),directory));success(await invoke(payload('SubagentStart',{agent_id:'\ufeff',agent_type:'\ufeff'}),directory));
 assert.deepEqual(canonical(await rows(directory)),canonical([{event_type:'SubagentStop',...fields},{event_type:'SubagentStart',agent_id:'\ufeff',agent_type:'\ufeff'}]));
}));

test('transcript references never read, alter or create the referenced file',()=>isolated(async directory=>{
 const data=join(directory,'data');await mkdir(data,{mode:0o700});const transcript=join(directory,'host.jsonl');await writeFile(transcript,'TRANSCRIPT_CONTENT_MUST_NOT_APPEAR',{mode:0o000});
 const missing=join(directory,'must-not-be-created.jsonl');
 for(const path of [transcript,missing])success(await invoke(payload('SubagentStop',{agent_id:'child',agent_transcript_path:path}),data));
 assert.equal((await stat(transcript)).mode&0o777,0);assert.ok(!JSON.stringify(await rows(data)).includes('TRANSCRIPT_CONTENT_MUST_NOT_APPEAR'));await assert.rejects(stat(missing),{code:'ENOENT'});
 await chmod(transcript,0o600);assert.equal(await readFile(transcript,'utf8'),'TRANSCRIPT_CONTENT_MUST_NOT_APPEAR');assert.deepEqual(await readdir(join(data,'event-types-v2')),[hash(session)]);
}));
