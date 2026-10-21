// Two bounded synthetic classifications. No repository content, paths or personal data.
const fs=require('node:fs');
const J=require('../../../plugins/delivery/scripts/lib/judge.js');
(async()=>{
 const state={candidate:'Repair an existing checklist item that cannot be unchecked',linked_item:'Previously shipped checklist',context:'An existing control fails when a person tries to undo a completed item'};
 const rows=[];
 for(const provider of ['jev','openai']){
  const start=Date.now();
  const result=await J.ask('is_fix',state,{team:{judge:{provider}},timeoutMs:10000});
  rows.push({provider,elapsed_ms:Date.now()-start,result});
 }
 fs.writeFileSync(__dirname+'/live-judge-smoke.json',JSON.stringify({synthetic_state:state,calibration:'One smoke case per provider; not provider calibration or blocking policy acceptance',runs:rows},null,2)+'\n');
 console.log(JSON.stringify(rows.map(({provider,result})=>({provider,answered:result.answer!==undefined,reason:result.reason||null,model:result.model||null}))));
})();
