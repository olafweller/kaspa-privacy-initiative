import {loadTerms} from './fixed_terms.mjs';
import {fileURLToPath} from 'node:url';import path from 'node:path';
// One bounded ordinary funding submission. Never handles an accepted S1.
import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {canonical,transaction} from '@KPI_REPO@/scripts/a0_tn10.mjs';
const r='@KPI_REPO@/.local/g5-preparation',d=path.join(path.dirname(fileURLToPath(import.meta.url)),'live-execution');
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function durable(name,value){const p=d+'/'+name,fd=fs.openSync(p,'wx',0o600);fs.writeFileSync(fd,JSON.stringify(value,null,2));fs.fsyncSync(fd);fs.closeSync(fd);const folder=fs.openSync(d,'r');fs.fsyncSync(folder);fs.closeSync(folder);}
const cfg=read(d+'/live-config.json'),auth=read(d+'/authorization.json'),gate=read(d+'/pre-funding-autonomy-receipt.json'),feeGate=read(d+'/latest-fee-mechanism-report.json'),review=read(d+'/funding-review.json'),raw=read(d+'/funding-transaction.json'),context=read(d+'/funding-full-request.json');
const location=read(d+'/run-location.private.json');const {reserve,feeCap,maximumDebit}=loadTerms(d,location.path+'/public/manifest.json');
assert.equal(cfg.mode,'finite-live-native');assert.equal(cfg.execution_authorized,true);assert.equal(cfg.run_id,auth.run_id);assert.equal(auth.checklist_sha256,sha(d+'/frozen-live-checklist.json'));
assert.equal(gate.run_id,cfg.run_id);assert.equal(gate.passed,true);assert.ok(Date.now()/1000-gate.at>=-2&&Date.now()/1000-gate.at<=300);
assert.equal(feeGate.passed,true);assert.equal(sha(feeGate.receipt_path),feeGate.receipt_sha256);const policy=read(feeGate.receipt_path.replace(/qualification.json$/,'C-policy.json'));assert.ok(Date.now()/1000-policy.observed_at_unix>=-2&&Date.now()/1000-policy.observed_at_unix<=300);
assert.equal(review.native_Full,true);assert.equal(review.body_sha256,sha(d+'/funding-transaction.json'));assert.equal(review.txid,raw.id);assert.equal(raw.id,cfg.locator.s0_txid_hex);assert.equal(raw.outputs[0].value,reserve.toString());assert.equal(raw.outputs[0].scriptPublicKey,cfg.locator.s0_spk_hex);assert.ok(BigInt(review.funding_fee_sompi)<=feeCap&&BigInt(review.wallet_debit_sompi)<=maximumDebit);
const sdk=createRequire(import.meta.url)('@KPI_REPO@/.local/sdk/kaspa-wasm32-sdk/nodejs/kaspa');
const env={};for(const line of fs.readFileSync('@KPI_REPO@/.env.tn10.local','utf8').split(/\r?\n/)){const m=line.match(/^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);if(m)env[m[1]]=m[2].replace(/^(['"])(.*)\1$/,'$2');}assert.equal(env.KASPA_NETWORK,'tn10');
const tx=transaction(raw);assert.deepEqual(canonical(tx),raw);
// Mandatory transport gate runs before RpcClient creation or any submit intent.
const frozen=read(d+'/frozen-live-checklist.json');assert.equal(sha(d+'/installed-runtime-binding.json'),frozen.installed_runtime_binding_sha256);const endpointGate=frozen.prefunding_endpoint_readiness;
const endpointChecker=path.join(path.dirname(fileURLToPath(import.meta.url)),'endpoint_readiness.py');
const sdkProbe=path.join(path.dirname(fileURLToPath(import.meta.url)),'endpoint_sdk_probe.mjs');
assert.equal(endpointGate.endpoint,'ws://127.0.0.1:29211');
assert.equal(sha(endpointChecker),endpointGate.checker_sha256);
assert.equal(sha(sdkProbe),endpointGate.SDK_probe_sha256);
const endpointReceipt=JSON.parse(execFileSync('/usr/bin/python3',[endpointChecker,'--runtime-binding',d+'/installed-runtime-binding.json','--runtime-binding-sha256',frozen.installed_runtime_binding_sha256,'--run-id',cfg.run_id,'--output',d+'/endpoint-before-funding-'+Date.now()+'.json'],{encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:60000}));
assert.equal(endpointReceipt.passed,true);assert.equal(endpointReceipt.run_id,cfg.run_id);
assert.equal(endpointReceipt.submit_RPC_invoked,false);assert.equal(endpointReceipt.endpoint,endpointGate.endpoint);
function assertEndpointFresh(){const age=Date.now()/1000-endpointReceipt.at;assert.ok(age>=-2&&age<=endpointReceipt.expiry_seconds&&age<=30,'stale funding endpoint readiness');}
assertEndpointFresh();
async function boundedConnect(rpc){let timer;try{return await Promise.race([rpc.connect({blockAsyncConnect:true,strategy:sdk.ConnectStrategy.Fallback,timeoutDuration:5000}),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('funding endpoint connection deadline')),10000);})]);}finally{clearTimeout(timer);}}
const rpc=new sdk.RpcClient({url:'ws://127.0.0.1:29211',encoding:sdk.Encoding.SerdeJson,networkId:'testnet-10'});
let submitted=false;
try{
 await boundedConnect(rpc);
 const info=await rpc.getServerInfo();assert.equal(info.networkId,'testnet-10');assert.equal(info.serverVersion,'2.1.0');assert.equal(info.isSynced,true);assert.equal(info.hasUtxoIndex,true);
 const peer=await rpc.getInfo();assert.equal(crypto.createHash('sha256').update(peer.p2pId).digest('hex'),endpointReceipt.SDK_probe.node_p2p_identity_sha256,'funding connection reached stale/wrong native node');
 const current=await rpc.getUtxosByAddresses({addresses:[env.KPI_FUNDING_ADDRESS]});const op=raw.inputs[0].previousOutpoint;
 const matches=current.entries.filter(e=>e.outpoint.transactionId===op.transactionId&&e.outpoint.index===op.index);assert.equal(matches.length,1);assert.equal(BigInt(matches[0].amount??matches[0].utxoEntry?.amount),BigInt(context.entry.amount));
 const fees=await rpc.getFeeEstimate(),rate=Number(review.funding_fee_sompi)/Number(review.SDK_mass),buckets=[fees.estimate.priorityBucket,...fees.estimate.normalBuckets,...fees.estimate.lowBuckets];assert.ok(buckets.some(b=>Number.isFinite(b.feerate)&&b.feerate>=100&&b.feerate*1.25<=rate&&b.estimatedSeconds<=30));
 assertEndpointFresh();
 durable('funding-submission-intent.json',{at:Date.now()/1000,run_id:cfg.run_id,txid:raw.id,body_sha256:review.body_sha256,full_hash:review.full_hash,reserve_sompi:reserve.toString(),fee_sompi:review.funding_fee_sompi,wallet_debit_sompi:review.wallet_debit_sompi,one_attempt:true,allowOrphan:false,checklist_sha256:auth.checklist_sha256});
 submitted=true;const response=await rpc.submitTransaction({transaction:tx,allowOrphan:false});assert.equal(response.transactionId,raw.id);
 durable('funding-submission-response.json',{at:Date.now()/1000,response,scope:'RPC response; C independent durable confirmation required'});
 console.log(JSON.stringify({funding_submission_attempts:1,txid:raw.id,fee_sompi:review.funding_fee_sompi,wallet_debit_sompi:review.wallet_debit_sompi,C_confirmation_still_required:true}));
}catch(e){
 if(submitted){durable('funding-ambiguous-response.json',{at:Date.now()/1000,run_id:cfg.run_id,no_retry:true,exception:e.name});console.log('STOP: funding response ambiguous; no retry; independent C reconciliation required.');}
 else console.log('STOP: funding pre-submit gate rejected; zero submissions.');
 process.exitCode=1;
}finally{await rpc.disconnect();}
