'use strict';
// Bounded synthetic cases only. Uses keys in native environment, never serializes them.
const fs=require('node:fs'),path=require('node:path');
const J=require('../../../plugins/delivery/scripts/lib/judge.js');
const cases=[
 {id:'relay-positive',question:'relay_request',expected:'yes',state:{sender_role:'Product Manager',recipient:'owner',message:'Open the builder session and approve the pending operation there.'}},
 {id:'relay-negative',question:'relay_request',expected:'no',state:{sender_role:'Product Manager',recipient:'owner',message:'The builder is implementing the checklist. I will report when verification finishes.'}},
 {id:'relay-own-decision',question:'relay_request',expected:'no',state:{sender_role:'coordinator',recipient:'owner',message:'Should the checklist start empty or include a sample item? You can answer here.'}},
 {id:'relay-owner-only',question:'relay_request',expected:'no',state:{sender_role:'coordinator',recipient:'owner',message:'Sign in to your own account to grant the requested consent. Only you can grant it.'}},
 {id:'fix-positive',question:'is_fix',expected:'yes',state:{candidate:'Repair disappearing checklist items after reload',linked_item:'Reported defect in the shipped checklist',context:'Customers lose saved items after reloading the existing application.'}},
 {id:'fix-negative',question:'is_fix',expected:'no',state:{candidate:'Add a new calendar view',linked_item:'New feature request',context:'The current application has never included a calendar.'}},
 {id:'divergence-none',question:'divergence',expected:'none',state:{agreed_criteria:'Customers can save and reload checklist items in the local desktop application.',customer_surface:'local desktop application',change_summary:'Saving and reloading was implemented and verified in the local desktop application.'}},
 {id:'divergence-serious',question:'divergence',expected:'serious',state:{agreed_criteria:'Customers can save and reload checklist items in the local desktop application.',customer_surface:'local desktop application',change_summary:'Only a browser demonstration was tested. The desktop application has not been tested.'}},
 {id:'divergence-minor',question:'divergence',expected:'minor',state:{agreed_criteria:'Customers can save and reload checklist items, including empty item titles.',customer_surface:'local desktop application',change_summary:'Customers can save and reload ordinary checklist items in the desktop application. One edge case remains: empty titles are rejected.'}},
 {id:'tone-neutral',question:'tone_violation',expected:'none',state:{sender_role:'coordinator',message:'The checklist saves correctly. Desktop verification remains open.'}}
];
async function main(){
 const output={started:new Date().toISOString(),kind:'synthetic smoke benchmark; not protected calibration',cases,results:[],notes:['Single run per case; not statistical reliability or model-comparison evidence.','No calibration records are produced. No human authority is inferred.']};
 for(const provider of ['jev','openai']){
  const cfg=J.judgeConfig({judge:{provider}},process.env);
  for(const c of cases){
   const r=await J.evaluate(c.question,c.state,{config:cfg,timeoutMs:30000});
   output.results.push({provider,case:c.id,expected:c.expected,correct:r.answer===c.expected,result:r});
   fs.writeFileSync(path.join(__dirname,'live-benchmark.json'),JSON.stringify(output,null,2)+'\n');
   console.log(JSON.stringify({provider,case:c.id,answer:r.answer||null,reason:r.reason||null,latencyMs:r.latencyMs||null,correct:r.answer===c.expected}));
  }
 }
 output.finished=new Date().toISOString();fs.writeFileSync(path.join(__dirname,'live-benchmark.json'),JSON.stringify(output,null,2)+'\n');
}
main().catch(()=>{console.error('benchmark failed; inspect preserved partial results');process.exitCode=1;});
