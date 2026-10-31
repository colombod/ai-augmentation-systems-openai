const test=require('node:test'),assert=require('node:assert/strict'),http=require('node:http');
const J=require('../../plugins/delivery/scripts/lib/judge.js');
const key='synthetic-provider-key';
async function fixture(reply,run) {
 const seen=[];const server=http.createServer((req,res)=>{let s='';req.on('data',c=>s+=c);req.on('end',()=>{seen.push({body:JSON.parse(s),auth:req.headers.authorization});res.writeHead(200);res.end(JSON.stringify(reply(JSON.parse(s))));});});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const env={OPENAI_API_KEY:key,DELIVERY_JUDGE_ENDPOINT:`http://127.0.0.1:${server.address().port}/decisions`};
 try {await run(env,seen);} finally {server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
}
const state={sender_role:'coordinator',recipient:'owner',message:'Open another session and approve its work.'};
test('selection is explicit, isolated to each provider key, and does not fall back',async()=>{
 assert.equal(J.judgeConfig({judge:{provider:'openai'}},{TYPESAFE_API_KEY:key}).reason,'no_key');
 assert.equal(J.judgeConfig({judge:{provider:'jev'}},{OPENAI_API_KEY:key}).reason,'no_key');
 assert.equal(J.judgeConfig({judge:{provider:'openai',key_env:'TYPESAFE_API_KEY'}},{TYPESAFE_API_KEY:key}).reason,'judge_config_invalid');
 const c=J.judgeConfig({judge:{provider:'openai'}},{OPENAI_API_KEY:key});assert.equal(c.model,'gpt-6-luna');assert.equal(c.endpoint,'https://api.openai.com/v1/decisions');
 assert.equal(J.judgeConfig({judge:{provider:'disabled'}},{}).enabled,false);
 assert.equal(JSON.stringify(c).includes(key),false);
});
test('OpenAI predicate wire shape, declared state filtering and no human authority',async()=>{
 await fixture(body=>({model:'gpt-6-luna',answers:[{type:'predicate',name:body.questions[0].name,probability:.91}],usage:{input_tokens:42,output_tokens:0}}),async(env,seen)=>{
 const r=await J.ask('relay_request',{...state,undeclared:'excluded'},{team:{judge:{provider:'openai'}},env});
 assert.equal(r.answer,'yes');assert.equal(r.p,.91);assert.equal(r.provider,'openai');assert.equal(r.human_authority,false);assert.equal(r.advisory,true);assert.equal(r.inputTokens,42);
 assert.equal(seen[0].body.questions[0].type,'predicate');assert.deepEqual(JSON.parse(seen[0].body.input),state);assert.equal(seen[0].auth,`Bearer ${key}`);assert.equal(JSON.stringify(seen[0].body).includes(key),false);
 });
});
test('OpenAI choice maps declared options and retains warn-only mode',async()=>{
 await fixture(body=>({model:'gpt-6-luna',answers:[{type:'choice',name:body.questions[0].name,choice:'minor',confidence:.8,probabilities:[{value:'none',probability:.1},{value:'minor',probability:.8},{value:'serious',probability:.1}]}]}),async(env,seen)=>{
 const r=await J.ask('divergence',{agreed_criteria:'A visible checklist',customer_surface:'local app',change_summary:'Checklist with one edge case missing'},{team:{judge:{provider:'openai'}},env});
 assert.equal(r.answer,'minor');assert.equal(r.mode,'warn-only');assert.deepEqual(Object.keys(r.probabilities),['none','minor','serious']);assert.equal(seen[0].body.questions[0].choices.length,3);
 });
});
test('refusals and malformed probabilities never become an answer',async()=>{
 for(const answer of [{type:'refusal',name:'relay_request'},{type:'predicate',name:'wrong-question',probability:.99},{type:'predicate',name:'relay_request',probability:2}])await fixture(()=>({answers:[answer]}),async(env)=>{
 const r=await J.ask('relay_request',state,{team:{judge:{provider:'openai'}},env});assert.equal(r.error,true);assert.equal(r.answer,undefined);assert.equal(r.human_authority,false);
 });
});
test('OpenAI rejects incomplete, duplicate, unnormalised and unknown choice probabilities',async()=>{
 const base={type:'choice',name:'divergence',choice:'minor',confidence:.8};
 for(const probabilities of [
 [{value:'minor',probability:1}],
 [{value:'none',probability:.1},{value:'minor',probability:.8},{value:'minor',probability:.1}],
 [{value:'none',probability:.8},{value:'minor',probability:.8},{value:'serious',probability:.8}],
 [{value:'none',probability:.1},{value:'minor',probability:.8},{value:'other',probability:.1}]
 ]) await fixture(()=>({answers:[{...base,probabilities}]}),async(env)=>{
  const r=await J.ask('divergence',{agreed_criteria:'a',customer_surface:'web',change_summary:'b'},{team:{judge:{provider:'openai'}},env});
  assert.equal(r.error,true);assert.equal(r.reason,'bad_response');assert.equal(r.answer,undefined);
 });
});
