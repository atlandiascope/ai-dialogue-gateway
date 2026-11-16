import {test, mock} from 'node:test';
import assert from 'node:assert/strict';
let calls=0, fail=false, rows=[];
mock.module('../netlify/lib/shared.mts',{namedExports:{
 db:{sql:async()=>{calls++;if(fail)throw new Error('database down');return rows;}},
 json:(data,status=200)=>Response.json(data,{status}),
 error:(error,status=400)=>Response.json({error},{status})
}});
const {default:handler}=await import('../netlify/functions/agent-profile.mts');
const run=id=>handler(new Request('https://example.test/api/agents/'+id),{params:{agentId:id}});
test('invalid profile ID is rejected before querying the database',async()=>{
 const res=await run('not-a-uuid');assert.equal(res.status,400);assert.equal(calls,0);
});
test('missing agent is a JSON 404',async()=>{
 const res=await run('00000000-0000-4000-8000-000000000001');assert.equal(res.status,404);
});
test('database outage is a JSON 503 rather than a function crash',async()=>{
 fail=true;const res=await run('00000000-0000-4000-8000-000000000001');assert.equal(res.status,503);assert.ok((await res.json()).error);
});
