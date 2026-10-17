// Finite TN10 jobs through the existing VPS admin terminal and localhost wRPC.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import * as JSON from './exact-json.mjs';
const base='/opt/kpi-pr31-cloud-20261017';
const root=base+'/native-value';
const binary=root+'/host-v2';
const program=root+'/guest-v1.program.bin';
const [stage,trialArg,labelArg]=process.argv.slice(2);
const exec=(args)=>{const p=spawnSync(binary,args,{encoding:'utf8',maxBuffer:64*1024*1024});assert.equal(p.status,0,'builder failed: '+p.stderr);return p.stdout;};
const read=p=>JSON.parse(fs.readFileSync(p));
const save=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx',mode:0o600});
let trial=trialArg;
if(stage==='init'){
 fs.mkdirSync(root+'/secrets',{recursive:true,mode:0o700});
 trial=root+'/trial-'+new Date().toISOString().replaceAll(/[:.]/g,'-')+'-'+crypto.randomBytes(4).toString('hex');fs.mkdirSync(trial,{mode:0o700});
 const k=createRequire(import.meta.url)('/opt/kpi-cloud-https/sdk/kaspa.js');const key=new k.PrivateKey(crypto.randomBytes(32).toString('hex'));
 const secretPath=root+'/secrets/'+path.basename(trial)+'.key';fs.writeFileSync(secretPath,key.toString()+'\n',{flag:'wx',mode:0o600});
 const random=crypto.randomBytes(3);random[0]|=1;const lane='6b'+random.toString('hex')+'00'.repeat(16);
 const p=spawnSync(base+'/kpi-tn10-integration-lift20-v2',['key',lane],{encoding:'utf8'});assert.equal(p.status,0);
 save(trial+'/identity.json',{trial,lane,laneKey:p.stdout.trim(),network:'testnet-10',owner:key.toPublicKey().toXOnlyPublicKey().toString(),userAddress:key.toAddress('testnet-10').toString(),userKeyPath:secretPath});
 console.log(trial);process.exit(0);
}
assert(trial?.startsWith(root+'/trial-')&&!trial.includes('..'));
const identity=read(trial+'/identity.json');assert.equal(identity.trial,trial);
const sponsor=read(base+'/test-wallet.public.json');
const records=[];const pending=new Map();let id=0;
const ws=new WebSocket('ws://127.0.0.1:18210');
ws.onmessage=e=>{const raw=String(e.data);const r=JSON.parse(raw);const p=pending.get(r.id);if(!p)return;pending.delete(r.id);clearTimeout(p.timer);records.push({method:p.method,request:p.request,raw});r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.params);};
await new Promise((a,b)=>{ws.onopen=a;ws.onerror=b;});
const call=(method,request={})=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>reject(Error('RPC timeout; inspect outcome before retry')),60000);pending.set(n,{resolve,reject,timer,method,request});ws.send(JSON.stringify({id:n,method,params:request}));});
const server=async()=>{const s=await call('getServerInfo');assert.equal(s.networkId,'testnet-10');assert.equal(s.isSynced,true);return s;};
async function build(label,fields,user=false){
 const key=user?identity.userKeyPath:base+'/test-wallet.key';const address=user?identity.userAddress:sponsor.address;
 const req={...fields,lane:identity.lane,server:await server(),utxos:await call('getUtxosByAddresses',{addresses:[address]})};save(trial+'/'+label+'-request.json',req);
 exec(['build',key,trial+'/'+label+'-request.json',trial+'/'+label+'-transaction.json',program]);return read(trial+'/'+label+'-transaction.json');
}
async function wait(from,txid,confirmations=3){
 for(let n=0;n<3600;n++){
 const r=await call('getVirtualChainFromBlockV2',{startHash:from,dataVerbosityLevel:'Full',minConfirmationCount:confirmations});assert.equal(r.removedChainBlockHashes.length,0,'reorg; inspect and preserve trial');
 for(const b of r.chainBlockAcceptedTransactions){const t=b.acceptedTransactions.find(t=>t.verboseData.transactionId===txid);if(t)return {header:b.chainBlockHeader,transaction:t};}
 await new Promise(r=>setTimeout(r,250));
 }throw Error('confirmation unresolved; inspect before retry');
}
async function submit(label,t,negative=false){
 await server();let before=(await call('getSink')).sink;
 for(let n=0;n<20;n++){const {block}=await call('getBlock',{hash:before,includeTransactions:false});assert.equal(block.verboseData.isChainBlock,true);before=block.verboseData.selectedParentHash;}
 save(trial+'/'+label+'-submission-intent.json',{id:t.transactionId,before,at:new Date().toISOString()});
 if(negative){try{const result=await call('submitTransaction',{transaction:t.transaction,allowOrphan:false});save(trial+'/'+label+'-UNEXPECTED.json',result);throw Error('negative unexpectedly admitted');}catch(e){assert(!e.message.includes('negative unexpectedly admitted'));save(trial+'/'+label+'-rejected.json',{reason:e.message,id:t.transactionId});return e.message;}}
 const admission=await call('submitTransaction',{transaction:t.transaction,allowOrphan:false});assert.equal(admission.transactionId,t.transactionId);save(trial+'/'+label+'-mempool.json',admission);
 const accepted=await wait(before,t.transactionId);save(trial+'/'+label+'-accepted.json',accepted);console.log(label+' '+t.transactionId);return accepted;
}
function capture(label,start,end){
 const p=spawnSync('/opt/kpi-cloud-https/bin/node',[root+'/capture.mjs',trial+'/'+label+'-capture.json',identity.laneKey,'50',start,end],{encoding:'utf8',maxBuffer:64*1024*1024});save(trial+'/'+label+'-capture-process.json',{status:p.status,stdout:p.stdout,stderr:p.stderr});assert.equal(p.status,0,p.stderr);
 const e=spawnSync(base+'/kpi-tn10-integration-lift20-v2',['export',identity.lane,trial+'/'+label+'-capture.json',read(trial+'/bootstrap-transaction.json').covenantId],{encoding:'utf8',maxBuffer:64*1024*1024});assert.equal(e.status,0,e.stderr);fs.writeFileSync(trial+'/'+label+'-lane.json',e.stdout,{flag:'wx'});
}
try{
 await server();
 if(stage==='prepare'){
  assert(!fs.existsSync(trial+'/bootstrap-submission-intent.json'),'fresh trial required');
  const funding=await submit('fund-user',await build('fund-user',{kind:'fund-user',recipient:identity.owner,amount:1200000000}));
  const seed=await submit('seed',await build('seed',{kind:'activity'}));
  const startProof=await call('getSeqCommitLaneProof',{blockHash:seed.header.hash,laneKey:identity.laneKey});assert(startProof.lane);save(trial+'/start-proof.json',startProof);
  const bootstrap=await build('bootstrap',{kind:'bootstrap',tip:startProof.lane.tip});await submit('bootstrap',bootstrap);
  const deposit=await build('deposit',{kind:'deposit',owner:identity.owner,covenantId:bootstrap.covenantId,amount:1000000000},true);
  const depositAccepted=await submit('deposit',deposit);
  // An accepted but unauthorized app command uses the sponsor's own native input;
  // the witness recovers that sponsor key, which fails the user's lock.
  const previousSponsor=read(trial+'/bootstrap-transaction.json');
  const unauthorized=await build('unauthorized',{kind:'withdraw',owner:identity.owner,recipient:identity.owner,amount:100000000,previousTransaction:previousSponsor.transaction,previousIndex:1});await submit('unauthorized',unauthorized);
  const withdrawal=await build('withdraw',{kind:'withdraw',owner:identity.owner,recipient:identity.owner,amount:400000000,previousTransaction:deposit.transaction,previousIndex:1},true);
  await submit('withdraw',withdrawal);
  const replay=await build('replay',{kind:'replay',payload:withdrawal.transaction.payload});const last=await submit('replay',replay);
  await wait(read(trial+'/replay-submission-intent.json').before,replay.transactionId,10);
  capture('prefix',seed.header.hash,depositAccepted.header.hash);
  capture('final',depositAccepted.header.hash,last.header.hash);
  exec(['prepare',trial+'/prefix-lane.json','empty',bootstrap.covenantId,trial+'/prefix-input.json']);
  const prefix=JSON.parse(exec(['execute',trial+'/prefix-input.json']));save(trial+'/prefix-output.json',prefix);save(trial+'/prefix-state.json',prefix.state);
  exec(['prepare',trial+'/final-lane.json',trial+'/prefix-state.json',bootstrap.covenantId,trial+'/final-input.json']);
  const final=JSON.parse(exec(['execute',trial+'/final-input.json']));save(trial+'/final-output.json',final);
  assert.equal(prefix.events.filter(e=>e.accepted).length,1);assert.equal(prefix.events.at(-1).spendable,1000000000);
  assert.equal(final.events.filter(e=>e.accepted).length,1);assert.equal(final.events.at(-1).spendable,600000000);assert.equal(final.exits.length,1);assert.equal(final.exits[0].amount,400000000);
  const omission=read(trial+'/final-input.json');let removed=0;
  // Native ID was independently checked by the exporter. Remove the withdrawal
  // at its captured accepted-order position; retain both legitimate anchor witnesses.
  const index=final.events.findIndex(e=>e.accepted);let cursor=0;
  for(const b of omission.lane.blocks){b.txs=b.txs.filter(()=>{const keep=cursor++!==index;if(!keep)removed++;return keep;});}
  assert.equal(removed,1);save(trial+'/omission-input.json',omission);
  save(trial+'/prepared.json',{...identity,start:seed.header.hash,prefixEnd:depositAccepted.header.hash,end:last.header.hash,bootstrapId:bootstrap.transactionId,covenantId:bootstrap.covenantId,withdrawalId:withdrawal.transactionId});
  console.log('NATIVE_VALUE_CAPTURE_READY '+trial);
 }else if(stage==='settle'){
  const label=labelArg;assert(['prefix','final','omission'].includes(label));
  const input=read(trial+'/'+label+'-input.json');const meta=read(trial+'/prepared.json');
  const prior=label==='prefix'?read(trial+'/bootstrap-transaction.json'):read(trial+'/prefix-settlement-transaction.json');
  const ce=(await call('getUtxosByAddresses',{addresses:[prior.outputAddresses[0]]})).entries.find(e=>e.outpoint.transactionId===prior.transactionId&&e.outpoint.index===0);assert(ce,'current state covenant not unspent');
  const built=await build(label+'-settlement',{kind:'settlement',input,end:label==='prefix'?meta.prefixEnd:meta.end,receiptPath:trial+'/'+label+'-receipt.bin',covenantUtxo:ce});
  const rejection=await submit(label+'-settlement',built,label==='omission');
  if(label==='omission')assert(/ZK Integrity.*Verification failed|ZkIntegrity/i.test(rejection),'unrelated omission rejection');
 }else if(stage==='auth-negative'){
  const withdrawal=read(trial+'/withdraw-transaction.json');
  const original=await build('auth-receiver-original',{kind:'withdraw',owner:identity.owner,recipient:identity.owner,amount:100000000,previousTransaction:withdrawal.transaction,previousIndex:0},true);
  // The original is a construction control only; broadcast its altered body once.
  const spk=Buffer.from((await call('getUtxosByAddresses',{addresses:[sponsor.address]})).entries[0].utxoEntry.scriptPublicKey,'hex');assert.equal(spk.length,36);assert.equal(spk.readUInt16LE(0),0);assert.equal(spk[2],32);assert.equal(spk[35],0xac);const pub=spk.subarray(3,35).toString('hex');
  exec(['mutate-recipient',trial+'/auth-receiver-original-transaction.json',pub,trial+'/auth-receiver-transaction.json']);
  const reason=await submit('auth-receiver',read(trial+'/auth-receiver-transaction.json'),true);
  assert(/signature script|signature|false/i.test(reason),'unrelated owner-signature rejection');
 }else if(stage==='payout'){
  const final=read(trial+'/final-settlement-transaction.json'),bootstrap=read(trial+'/bootstrap-transaction.json');
  const permission=(await call('getUtxosByAddresses',{addresses:[final.outputAddresses[1]]})).entries.find(e=>e.outpoint.transactionId===final.transactionId&&e.outpoint.index===1);assert(permission);
  const deposit=read(trial+'/deposit-transaction.json');const delegate=(await call('getUtxosByAddresses',{addresses:[bootstrap.depositAddress]})).entries.find(e=>e.outpoint.transactionId===deposit.transactionId&&e.outpoint.index===0);assert(delegate);
  const fields={kind:'payout',covenantId:bootstrap.covenantId,permissionUtxo:permission,delegateUtxo:delegate,recipient:identity.owner,amount:400000000};
  for(const attack of ['underpay','reserve','recipient']){const t=await build('payout-'+attack,{...fields,attack});const reason=await submit('payout-'+attack,t,true);assert(/signature script|script|EqualVerify|verify/i.test(reason),'unrelated bridge rejection');}
  const t=await build('payout',fields);await submit('payout',t);
  await wait(read(trial+'/payout-submission-intent.json').before,t.transactionId,10);
  const recipientUtxos=await call('getUtxosByAddresses',{addresses:[identity.userAddress]});const reserveUtxos=await call('getUtxosByAddresses',{addresses:[bootstrap.depositAddress]});const permissions=await call('getUtxosByAddresses',{addresses:[final.outputAddresses[1]]});
  const payout=recipientUtxos.entries.find(e=>e.outpoint.transactionId===t.transactionId&&e.outpoint.index===0);assert(payout);assert.equal(payout.utxoEntry.amount,450000000);
  const reserve=reserveUtxos.entries.find(e=>e.outpoint.transactionId===t.transactionId&&e.outpoint.index===1);assert(reserve);assert.equal(reserve.utxoEntry.amount,600000000);
  assert(!permissions.entries.some(e=>e.outpoint.transactionId===final.transactionId),'claim not consumed');
  const replay=await build('payout-replay',fields);assert.notEqual(replay.transactionId,t.transactionId,'distinct signed attack transaction required');
  const replayReason=await submit('payout-replay',replay,true);assert(/orphan|missing|unknown|not found|already spent/i.test(replayReason),'unrelated claim replay rejection');
  save(trial+'/payout-result.json',{payout,reserve,permissionConsumed:true,principalSompi:400000000,rentRefundSompi:50000000,spendableSompi:600000000,unpaidClaimsSompi:0,feeSompi:t.feeSompi});
 }else throw Error('unknown stage');
}catch(e){save(trial+'/'+stage+'-'+(labelArg??'job')+'-failure.json',{error:e.message,at:new Date().toISOString()});console.error(e.message);process.exitCode=1;}
finally{save(trial+'/'+stage+'-'+(labelArg??'job')+'-rpc.json',records);ws.close();}
