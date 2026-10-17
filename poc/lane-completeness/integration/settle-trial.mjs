import * as exactJSON from './exact-json.mjs';
// Real-proof settlement of one prepared trial; never use a development redeem.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root = '/opt/kpi-pr31-cloud-20261017';
const [trial] = process.argv.slice(2);
assert(trial?.startsWith(root + '/trial-') && !trial.includes('..'));
const prepared = exactJSON.parse(fs.readFileSync(path.join(trial, 'prepared.json')));
const input = exactJSON.parse(fs.readFileSync(path.join(trial, 'input.json')));
const bootstrap = exactJSON.parse(fs.readFileSync(path.join(trial, 'bootstrap-transaction.json')));
assert([root+'/kpi-tn10-integration-lift19-v2',root+'/kpi-tn10-integration-lift20-v2'].includes(prepared.builderBinary),'explicit circuit-specific builder required');
const wallet = exactJSON.parse(fs.readFileSync(root + '/test-wallet.public.json'));
const save = (name, value) => fs.writeFileSync(path.join(trial, name), exactJSON.stringify(value, null, 2) + '\n', {flag: 'wx', mode: 0o600});
assert(!fs.existsSync(path.join(trial, 'settlement-submission-intent.json')), 'inspect previous submission before any retry');
const ws = new WebSocket('ws://127.0.0.1:18210');
let id = 0; const pending = new Map(); const records = [];
ws.onmessage = e => {const raw=String(e.data);const r=exactJSON.parse(raw);const p=pending.get(r.id);if(!p)return;
  pending.delete(r.id);clearTimeout(p.timer);records.push({method:p.method,request:p.request,raw});
  r.error?p.reject(new Error(exactJSON.stringify(r.error))):p.resolve(r.params);};
await new Promise((a,b)=>{ws.onopen=a;ws.onerror=b;});
const call=(method,request={})=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>reject(Error('RPC timeout; remote outcome may be unknown')),60000);
  pending.set(n,{resolve,reject,timer,method,request});ws.send(exactJSON.stringify({id:n,method,params:request}));});
async function server(){const s=await call('getServerInfo');assert.equal(s.networkId,'testnet-10');assert.equal(s.isSynced,true);return s;}
async function build(label, invalidState) {
  const s=await server();
  const cov=await call('getUtxosByAddresses',{addresses:[bootstrap.covenantAddress]});
  const entry=cov.entries.find(e=>e.outpoint.transactionId===prepared.bootstrapId&&e.outpoint.index===0);
  assert(entry,'original covenant must still be unspent');
  const request={kind:'settlement',invalidState,input,end:prepared.end,receiptPath:path.join(trial,'full.receipt.bin'),covenantUtxo:entry,
    server:s,utxos:await call('getUtxosByAddresses',{addresses:[wallet.address]}),feeEstimate:await call('getFeeEstimate')};
  save(label+'-request.json',request);
  const r=spawnSync(prepared.builderBinary,['build',prepared.lane,root+'/test-wallet.key',path.join(trial,label+'-request.json'),
    path.join(trial,label+'-transaction.json'),root+'/guest.program.bin'],{encoding:'utf8',maxBuffer:32*1024*1024});
  save(label+'-builder-process.json',{status:r.status,stdout:r.stdout,stderr:r.stderr});
  assert.equal(r.status,0,'real proof and covenant-state validation must pass before submission');
  return exactJSON.parse(fs.readFileSync(path.join(trial,label+'-transaction.json')));
}
try {
  const invalid=await build('invalid-settlement',true);
  save('invalid-settlement-submission-intent.json',{transactionId:invalid.transactionId,at:new Date().toISOString()});
  let rejection;
  try {const accepted=await call('submitTransaction',{transaction:invalid.transaction,allowOrphan:false});
    save('invalid-settlement-UNEXPECTED-ACCEPTANCE.json',accepted);throw Error('invalid settlement unexpectedly accepted');
  } catch(error) {
    assert(/ZkIntegrity|Verification failed/i.test(error.message),'negative failed for an unrelated reason: '+error.message);
    rejection=error.message;save('invalid-settlement-rejected.json',{rejected:true,reason:rejection,transactionId:invalid.transactionId});
  }
  const valid=await build('settlement',false);
  let before=(await call('getSink')).sink;
  for(let depth=0;depth<20;depth++){
    const {block}=await call('getBlock',{hash:before,includeTransactions:false});
    assert.equal(block.verboseData.isChainBlock,true);before=block.verboseData.selectedParentHash;
  }
  save('settlement-submission-intent.json',{transactionId:valid.transactionId,before,at:new Date().toISOString()});
  const admission=await call('submitTransaction',{transaction:valid.transaction,allowOrphan:false});
  assert.equal(admission.transactionId,valid.transactionId);save('settlement-mempool.json',admission);
  let acceptance;
  const deadline=Date.now()+900000;
  while(Date.now()<deadline) {
    const r=await call('getVirtualChainFromBlockV2',{startHash:before,dataVerbosityLevel:'Full',minConfirmationCount:10});
    assert.equal(r.removedChainBlockHashes.length,0,'reorg while observing settlement; inspect before retry');
    for(const b of r.chainBlockAcceptedTransactions){const tx=b.acceptedTransactions.find(t=>t.verboseData.transactionId===valid.transactionId);
      if(tx){acceptance={acceptingHeader:b.chainBlockHeader,transaction:tx};break;}}
    if(acceptance)break;
    await new Promise(r=>setTimeout(r,250));
  }
  assert(acceptance,'settlement confirmation unresolved; inspect before retry');save('settlement-accepted.json',acceptance);
  const successor=await call('getUtxosByAddresses',{addresses:[valid.successorAddress]});
  const utxo=successor.entries.find(e=>e.outpoint.transactionId===valid.transactionId&&e.outpoint.index===0);
  assert(utxo,'confirmed continuation UTXO missing');
  assert.equal(utxo.utxoEntry.amount,100000000);
  assert.equal(utxo.utxoEntry.covenantId,prepared.covenantId);
  const old=await call('getUtxosByAddresses',{addresses:[bootstrap.covenantAddress]});
  assert(!old.entries.some(e=>e.outpoint.transactionId===prepared.bootstrapId),'old covenant still spendable');
  save('settlement-result.json',{scope:'REAL_RISC_ZERO_PROOF_ACCEPTED_ON_TN10',developmentMode:false,network:'testnet-10',
    validTransactionId:valid.transactionId,invalidTransactionId:invalid.transactionId,invalidRejection:rejection,
    acceptingBlock:acceptance.acceptingHeader.hash,continuation:utxo,oldCovenantSpent:true,feeSompi:valid.feeSompi,
    newState:valid.newState,server:await server()});
  console.log('REAL_SETTLEMENT_CONFIRMED '+valid.transactionId);
}catch(error){save('settlement-failure.json',{at:new Date().toISOString(),error:error.message});console.error(error.message);process.exitCode=1;}
finally{save('settlement-rpc-records.json',records);ws.close();}
