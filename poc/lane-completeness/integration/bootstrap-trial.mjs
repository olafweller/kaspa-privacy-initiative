import * as exactJSON from './exact-json.mjs';
// Bootstrap ONLY AFTER the actual captured workload has been execution-profiled.
// This is a public-input catch-up checkpoint, not proof of arbitrary bootstrap history.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root='/opt/kpi-pr31-cloud-20261017';
const [trial]=process.argv.slice(2);
assert(trial?.startsWith(root+'/trial-')&&!trial.includes('..'));
const meta=exactJSON.parse(fs.readFileSync(path.join(trial,'input-prepared.json')));
const profile=exactJSON.parse(fs.readFileSync(path.join(trial,'execution-profile.json')));
assert.equal(profile.scope,'EXECUTION_ONLY_NO_CRYPTOGRAPHIC_PROOF');
assert.equal(profile.segments.length,1,'only single-segment monolithic experiment supported');
const circuit=profile.segments[0].po2;
assert([19,20].includes(circuit),'unsupported monolithic shape: do not lock a covenant');
const binary=root+'/kpi-tn10-integration-lift'+circuit+'-v2';
const input=exactJSON.parse(fs.readFileSync(path.join(trial,'profile-input.json')));
const wallet=exactJSON.parse(fs.readFileSync(root+'/test-wallet.public.json'));
const save=(name,value)=>fs.writeFileSync(path.join(trial,name),exactJSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600});
const records=[];let id=0;const pending=new Map();const ws=new WebSocket('ws://127.0.0.1:18210');
ws.onmessage=e=>{const raw=String(e.data);const r=exactJSON.parse(raw);const p=pending.get(r.id);if(!p)return;pending.delete(r.id);clearTimeout(p.timer);records.push({method:p.method,request:p.request,raw});r.error?p.reject(Error(exactJSON.stringify(r.error))):p.resolve(r.params)};
await new Promise((a,b)=>{ws.onopen=a;ws.onerror=b});
const call=(method,request={})=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>reject(Error('RPC timeout; inspect before retry')),60000);pending.set(n,{resolve,reject,timer,method,request});ws.send(exactJSON.stringify({id:n,method,params:request}))});
const execute=args=>{const r=spawnSync(binary,args,{encoding:'utf8',maxBuffer:32*1024*1024});if(r.status!==0)throw Error(r.stderr);return r.stdout};
try{
  const server=await call('getServerInfo');assert.equal(server.networkId,'testnet-10');assert.equal(server.isSynced,true);
  for(const hash of [meta.start,meta.end]){const {block}=await call('getBlock',{hash,includeTransactions:false});assert.equal(block.verboseData.isChainBlock,true,'captured endpoint reorganized')}
  const request={kind:'bootstrap',tip:Buffer.from(input.old_tip).toString('hex'),server,
    utxos:await call('getUtxosByAddresses',{addresses:[wallet.address]}),feeEstimate:await call('getFeeEstimate')};
  save('bootstrap-request.json',request);
  execute(['build',meta.lane,root+'/test-wallet.key',path.join(trial,'bootstrap-request.json'),path.join(trial,'bootstrap-transaction.json'),root+'/guest.program.bin']);
  const built=exactJSON.parse(fs.readFileSync(path.join(trial,'bootstrap-transaction.json')));
  let before=(await call('getSink')).sink;
  for(let depth=0;depth<20;depth++){const {block}=await call('getBlock',{hash:before,includeTransactions:false});assert.equal(block.verboseData.isChainBlock,true);before=block.verboseData.selectedParentHash}
  save('bootstrap-submission-intent.json',{transactionId:built.transactionId,before,circuit,at:new Date().toISOString()});
  const admission=await call('submitTransaction',{transaction:built.transaction,allowOrphan:false});assert.equal(admission.transactionId,built.transactionId);save('bootstrap-mempool.json',admission);
  let acceptance;const deadline=Date.now()+900000;
  while(Date.now()<deadline){const r=await call('getVirtualChainFromBlockV2',{startHash:before,dataVerbosityLevel:'Full',minConfirmationCount:10});assert.equal(r.removedChainBlockHashes.length,0,'bootstrap observation checkpoint lost');
    acceptance=r.chainBlockAcceptedTransactions.find(b=>b.acceptedTransactions.some(t=>t.verboseData.transactionId===built.transactionId));if(acceptance)break;await new Promise(r=>setTimeout(r,200));}
  assert(acceptance,'bootstrap outcome unresolved; inspect instead of rebroadcast');save('bootstrap-accepted.json',acceptance.chainBlockHeader);
  const realInput=execute(['export',meta.lane,path.join(trial,'capture.json'),built.covenantId]);
  fs.writeFileSync(path.join(trial,'input.json'),realInput,{flag:'wx',mode:0o600});
  save('prepared.json',{...meta,status:'CIRCUIT_MATCHED_BOOTSTRAP_REAL_PROOF_PENDING',builderBinary:binary,circuit,
    covenantId:built.covenantId,bootstrapId:built.transactionId});
  console.log(exactJSON.stringify({stage:'CIRCUIT_MATCHED_BOOTSTRAP',circuit,bootstrapId:built.transactionId,trial}));
}catch(error){save('bootstrap-failure.json',{error:error.message});console.error(error.message);process.exitCode=1}
finally{save('bootstrap-rpc-records.json',records);ws.close()}
