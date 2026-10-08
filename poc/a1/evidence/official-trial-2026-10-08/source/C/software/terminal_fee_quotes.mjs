// C-only read-only fee collector. Endpoints come from frozen C policy, never B.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';import {createRequire} from 'node:module';
const[sdkDir,policyPath]=process.argv.slice(2);const p=JSON.parse(fs.readFileSync(policyPath));const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
for(const[n,h]of Object.entries(p.sdk_files_sha256))assert.equal(sha(fs.readFileSync(path.join(sdkDir,n))),h);assert.ok(p.external_fee_endpoints.length>=1&&p.external_fee_endpoints.length<=3);
const s=createRequire(import.meta.url)(path.join(sdkDir,'kaspa.js'));const observations=[];
for(const endpoint of p.external_fee_endpoints){assert.match(endpoint,/^wss:\/\/[^/]+\/.*testnet-10.*$/);const rpc=new s.RpcClient({url:endpoint,encoding:s.Encoding.Borsh,networkId:'testnet-10'});try{await rpc.connect({blockAsyncConnect:true,timeoutDuration:3000});const info=await rpc.getInfo();const dag=await rpc.getBlockDagInfo();const fees=await rpc.getFeeEstimate();observations.push({endpoint,observed_at_utc:new Date().toISOString(),status:'observed',info,dag,fees});}finally{await rpc.disconnect();}}
console.log(JSON.stringify({schema:'kpi-a1-fee-observation/v1',network:'testnet-10',pins:{rusty_kaspa_commit:p.rusty_kaspa_commit},observations},(_,v)=>typeof v==='bigint'?v.toString():v));
