// Finite, operator-authorized native RPC steps. No keys, background executor or retries of submissions.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import * as E from '/opt/kpi-tn10-preflight-20261019/capture-tool/exact-json.mjs';
const ROOT='/opt/kpi-tn10-live-20261019';
const [action,label,file]=process.argv.slice(2);assert(/^[a-z0-9-]+$/.test(label));assert(['query','submit','wait'].includes(action));
const save=(suffix,v)=>{const p=ROOT+'/'+label+'-'+suffix+'.json';const f=fs.openSync(p,'wx',0o600);fs.writeFileSync(f,E.stringify(v,null,2)+'\n');fs.fsyncSync(f);fs.closeSync(f);const d=fs.openSync(ROOT,'r');fs.fsyncSync(d);fs.closeSync(d);};
const read=p=>E.parse(fs.readFileSync(p));
const ws=new WebSocket('ws://127.0.0.1:18210');let id=0;const pending=new Map(),records=[];
ws.onmessage=e=>{const raw=String(e.data),r=E.parse(raw),p=pending.get(r.id);if(!p)return;clearTimeout(p.timer);pending.delete(r.id);records.push({method:p.method,request:p.params,raw});r.error?p.reject(Error(E.stringify(r.error))):p.resolve(r.params);};
await new Promise((a,b)=>{ws.onopen=a;ws.onerror=b;});
const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id,timer=setTimeout(()=>{pending.delete(n);reject(Error('RPC timeout; reconcile outcome without resubmission'));},30000);pending.set(n,{resolve,reject,timer,method,params});ws.send(E.stringify({id:n,method,params}));});
async function context(addresses){const server=await call('getServerInfo');assert.equal(server.networkId,'testnet-10');assert(server.isSynced);const fees=await call('getFeeEstimate');assert(fees.estimate.priorityBucket.feerate<=100,'new fee quote exceeds frozen rate');const utxos=await call('getUtxosByAddresses',{addresses});const {sink}=await call('getSink');const sinkBlock=await call('getBlock',{hash:sink,includeTransactions:false});assert(sinkBlock.block.verboseData.isChainBlock);return {server,fees,utxos,sinkBlock};}
async function wait(intent){for(let i=0;i<120;i++){const r=await call('getVirtualChainFromBlockV2',{startHash:intent.before,dataVerbosityLevel:'Full',minConfirmationCount:10});assert.equal(r.removedChainBlockHashes.length,0,'reorg; halt');for(const b of r.chainBlockAcceptedTransactions){const t=b.acceptedTransactions.find(t=>t.verboseData.transactionId===intent.transactionId);if(t){const a={transactionId:intent.transactionId,header:b.chainBlockHeader,transaction:t,confirmed:10,observedAt:new Date().toISOString()};save('accepted',a);return a;}}await new Promise(r=>setTimeout(r,500));}throw Error('acceptance unresolved; no resubmission');}
try {
 if(action==='query'){const addresses=JSON.parse(file);const c=await context(addresses);save('snapshot',c);console.log(E.stringify(c));}
 else if(action==='wait'){const accepted=await wait(read(file));console.log(E.stringify({accepted:true,transactionId:accepted.transactionId,block:accepted.header.hash}));}
 else {
  assert(file.startsWith(ROOT+'/'));const q=read(file);const {record:r,entries,qualification}=q;
  assert(r&&r.transaction&&/^[0-9a-f]{64}$/.test(r.transactionId));assert.equal(qualification.transactionId,r.transactionId);assert.equal(qualification.allInputScriptsExecuted,true);assert(qualification.feeSompi>0);
  assert.equal(r.transaction.inputs.length,entries.length);
  const addresses=[...new Set(entries.map(e=>e.address))];assert(addresses.every(a=>a.startsWith('kaspatest:')));
  const fresh=await context(addresses);save('fresh',fresh);
  for(let i=0;i<entries.length;i++){const expected=entries[i],point=r.transaction.inputs[i].previousOutpoint;assert.deepEqual(point,expected.outpoint);const actual=fresh.utxos.entries.find(e=>e.outpoint.transactionId===point.transactionId&&e.outpoint.index===point.index);assert(actual,'input absent/spent');assert.deepEqual(actual,expected,'UTXO context changed');}
  let before=fresh.sinkBlock.block.header.hash;for(let i=0;i<20;i++){const b=await call('getBlock',{hash:before,includeTransactions:false});assert(b.block.verboseData.isChainBlock);before=b.block.verboseData.selectedParentHash;}
  const intent={transactionId:r.transactionId,before,at:new Date().toISOString(),allowOrphan:false};save('submission-intent',intent);
  // Exactly one mutation. Never repeat it after errors or a lost response.
  const admission=await call('submitTransaction',{transaction:r.transaction,allowOrphan:false});save('admission',admission);assert.equal(admission.transactionId,r.transactionId);
  const accepted=await wait(intent);console.log(E.stringify({accepted:true,transactionId:r.transactionId,block:accepted.header.hash}));
 }
}catch(e){save('failure',{error:e.message,at:new Date().toISOString(),noAutomaticRetry:true});console.error(e.message);process.exitCode=1;}
finally{save(action+'-rpc',records);ws.close();}
