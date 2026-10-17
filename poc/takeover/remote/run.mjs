// Finite fresh TN10 rehearsal. Native signing keys stay on this VPS.
// Every submit has a write-once intent; transport failures are not rejections.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import * as JSON from './exact-json.mjs';
const base='/opt/kpi-pr31-cloud-20261017',root=base+'/takeover';
const binary=root+'/build-v1',program=root+'/aggregate.program.bin';
const [stage,trial,labelArg]=process.argv.slice(2);
const read=p=>JSON.parse(fs.readFileSync(p));
const save=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx',mode:0o600});
const run=(bin,args)=>{const p=spawnSync(bin,args,{encoding:'utf8',maxBuffer:512*1024*1024});assert.equal(p.status,0,p.stderr);return p.stdout;};
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(stage==='init'){
 fs.mkdirSync(root+'/secrets',{recursive:true,mode:0o700});
 const dir=root+'/trial-'+new Date().toISOString().replaceAll(/[:.]/g,'-')+'-'+crypto.randomBytes(4).toString('hex');fs.mkdirSync(dir,{mode:0o700});
 const k=createRequire(import.meta.url)('/opt/kpi-cloud-https/sdk/kaspa.js');
 const keys={};for(const role of ['user','fee']){
  const key=new k.PrivateKey(crypto.randomBytes(32).toString('hex'));
  const keyPath=root+'/secrets/'+path.basename(dir)+'-'+role+'.key';
  fs.writeFileSync(keyPath,key.toString()+'\n',{flag:'wx',mode:0o600});
  keys[role]={keyPath,address:key.toAddress('testnet-10').toString(),owner:key.toPublicKey().toXOnlyPublicKey().toString()};
 }
 const random=crypto.randomBytes(3);random[0]|=1;const lane='6b'+random.toString('hex')+'00'.repeat(16);
 const laneKey=run(base+'/kpi-tn10-integration-lift20-v2',['key',lane]).trim();
 save(dir+'/identity.json',{trial:dir,network:'testnet-10',lane,laneKey,keys,
  builderSha256:hash(binary),programSha256:Object.fromEntries(['transaction','batch','aggregate'].map(n=>[n,hash(root+'/'+n+'.program.bin')]))});
 console.log(dir);process.exit(0);
}
if(stage!=='probe')assert(trial?.startsWith(root+'/trial-')&&!trial.includes('..'));
const identity=stage==='probe'?null:read(trial+'/identity.json');
const sponsor=read(base+'/test-wallet.public.json');
const records=[],pending=new Map();let id=0;
const ws=new WebSocket('ws://127.0.0.1:18210');
ws.onmessage=e=>{const raw=String(e.data),r=JSON.parse(raw),p=pending.get(r.id);if(!p)return;pending.delete(r.id);records.push({method:p.method,request:p.request,raw});r.error?p.reject(Object.assign(Error(JSON.stringify(r.error)),{nativeRpc:true})):p.resolve(r.params);};
ws.onclose=()=>{for(const p of pending.values())p.reject(Error('RPC transport closed; inspect outcome'));pending.clear();};
await new Promise((a,b)=>{ws.onopen=a;ws.onerror=b;});
const call=(method,request={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject,method,request});ws.send(JSON.stringify({id:n,method,params:request}));});
const server=async()=>{const s=await call('getServerInfo');assert.equal(s.networkId,'testnet-10');assert.equal(s.isSynced,true);assert.equal(s.hasUtxoIndex,true);return s;};
async function anchor(){let cursor=(await call('getSink')).sink;let b;for(let i=0;i<21;i++){b=(await call('getBlock',{hash:cursor,includeTransactions:false})).block;assert(b.verboseData.isChainBlock);cursor=b.verboseData.selectedParentHash;}return b;}
async function build(label,fields,role='fee'){
 const wallet=role==='sponsor'?{address:sponsor.address,keyPath:base+'/test-wallet.key'}:identity.keys[role];
 save(trial+'/'+label+'-request.json',{...fields,lane:identity.lane,server:await server(),utxos:await call('getUtxosByAddresses',{addresses:[wallet.address]})});
 run(binary,['build',wallet.keyPath,trial+'/'+label+'-request.json',trial+'/'+label+'-transaction.json',program]);return read(trial+'/'+label+'-transaction.json');
}
async function wait(from,txid,confirmations=10){for(;;){
 const r=await call('getVirtualChainFromBlockV2',{startHash:from,dataVerbosityLevel:'Full',minConfirmationCount:confirmations});assert.equal(r.removedChainBlockHashes.length,0,'reorg: preserve trial');
 for(const b of r.chainBlockAcceptedTransactions){const t=b.acceptedTransactions.find(t=>t.verboseData.transactionId===txid);if(t)return {header:b.chainBlockHeader,transaction:t};}
 await new Promise(r=>setTimeout(r,300));
}}
async function submit(label,t,negative=false){
 await server();const before=(await anchor()).header.hash;
 save(trial+'/'+label+'-submission-intent.json',{id:t.transactionId,before,negative,at:new Date().toISOString()});
 if(negative){let error;try{const result=await call('submitTransaction',{transaction:t.transaction,allowOrphan:false});save(trial+'/'+label+'-UNEXPECTED.json',result);}catch(e){if(!e.nativeRpc)throw e;error=e;}
  assert(error,'negative unexpectedly admitted');save(trial+'/'+label+'-rejected.json',{id:t.transactionId,reason:error.message});return error.message;
 }
 const admission=await call('submitTransaction',{transaction:t.transaction,allowOrphan:false});assert.equal(admission.transactionId,t.transactionId);save(trial+'/'+label+'-mempool.json',admission);
 const accepted=await wait(before,t.transactionId);save(trial+'/'+label+'-accepted.json',accepted);console.log(label+' '+t.transactionId);return accepted;
}
async function unspent(meta,index){return (await call('getUtxosByAddresses',{addresses:[meta.outputAddresses[index]]})).entries.find(e=>e.outpoint.transactionId===meta.transactionId&&e.outpoint.index===index);}
function capture(label,start,end){const stdout=run('/opt/kpi-cloud-https/bin/node',[root+'/capture.mjs',trial+'/'+label+'-capture.json',identity.laneKey,'50',start,end]);save(trial+'/'+label+'-capture-result.json',{stdout});}
try{
 const info=await server();
 if(stage==='probe'){
  const balance=await call('getUtxosByAddresses',{addresses:[sponsor.address]});
  console.log(JSON.stringify({server:info,sponsorSompi:balance.entries.reduce((n,e)=>n+BigInt(e.utxoEntry.amount),0n),sponsorUtxos:balance.entries.length}));
 }else if(stage==='prepare'){
  assert(!fs.existsSync(trial+'/fund-fee-submission-intent.json'),'fresh identity required');
  await submit('fund-fee',await build('fund-fee',{kind:'fund-user',recipient:identity.keys.fee.owner,amount:2500000000},'sponsor'));
  await submit('fund-user',await build('fund-user',{kind:'fund-user',recipient:identity.keys.user.owner,amount:1200000000}));
  const seed=await submit('seed',await build('seed',{kind:'activity'}));
  const sp=await call('getSeqCommitLaneProof',{blockHash:seed.header.hash,laneKey:identity.laneKey});assert(sp.lane);save(trial+'/seed-proof.json',sp);
  const bootstrap=await build('bootstrap',{kind:'bootstrap',tip:sp.lane.tip});await submit('bootstrap',bootstrap);
  const deposit=await build('deposit',{kind:'deposit',owner:identity.keys.user.owner,covenantId:bootstrap.covenantId,amount:1000000000},'user');
  const accepted=await submit('deposit',deposit);
  capture('prefix',seed.header.hash,accepted.header.hash);
  save(trial+'/prepared.json',{start:seed.header.hash,prefixEnd:accepted.header.hash,covenantId:bootstrap.covenantId,depositId:deposit.transactionId});
  console.log('PREFIX_CAPTURE_READY '+trial);
 }else if(stage==='settle'){
  assert(['prefix','final','omission'].includes(labelArg));
  const meta=read(trial+'/prepared.json');const prior=labelArg==='prefix'?read(trial+'/bootstrap-transaction.json'):read(trial+'/prefix-settlement-transaction.json');
  const ce=await unspent(prior,0);assert(ce,'state covenant not unspent');
  const end=labelArg==='prefix'?meta.prefixEnd:read(trial+'/withdraw-accepted.json').header.hash;
  const built=await build(labelArg+'-settlement',{kind:'settlement',end,receiptPath:trial+'/'+labelArg+'-receipt.bin',covenantUtxo:ce});
  const result=await submit(labelArg+'-settlement',built,labelArg==='omission');
  if(labelArg==='omission')assert(/ZK Integrity.*Verification failed|ZkIntegrity/i.test(result),'unrelated omission rejection');
 }else if(stage==='stop'){
  const prior=read(trial+'/prefix-settlement-transaction.json');assert(await unspent(prior,0),'prefix checkpoint is not unspent');
  const stop=await anchor();const proof=await call('getSeqCommitLaneProof',{blockHash:stop.header.hash,laneKey:identity.laneKey});
  assert.equal(proof.lane.tip,prior.newTip);
  save(trial+'/executor-stop.json',{at:new Date().toISOString(),header:stop.header,laneProof:proof,checkpoint:prior.transactionId,state:prior.newState,
   executor:'original finite prepare/checkpoint process has exited',scope:'same owner VPS/node; subsequent replay in a clean Cloud directory'});
  console.log('ORIGINAL_EXECUTOR_STOPPED '+stop.header.blueScore);
 }else if(stage==='withdraw'){
  const stop=read(trial+'/executor-stop.json');let current;
  do{current=await anchor();if(BigInt(current.header.blueScore)-BigInt(stop.header.blueScore)<150n)await new Promise(r=>setTimeout(r,500));}while(BigInt(current.header.blueScore)-BigInt(stop.header.blueScore)<150n);
  const before=await call('getSeqCommitLaneProof',{blockHash:current.header.hash,laneKey:identity.laneKey});assert.equal(before.lane.tip,stop.laneProof.lane.tip);assert.equal(before.lane.blueScore,stop.laneProof.lane.blueScore);
  const deposit=read(trial+'/deposit-transaction.json');
  const withdrawal=await build('withdraw',{kind:'withdraw',owner:identity.keys.user.owner,recipient:identity.keys.user.owner,amount:400000000,previousTransaction:deposit.transaction,previousIndex:1},'user');
  const accepted=await submit('withdraw',withdrawal);
  capture('catchup',stop.header.hash,accepted.header.hash);
  const gap=BigInt(accepted.header.blueScore)-BigInt(stop.header.blueScore);assert(gap>100n);
  save(trial+'/gap.json',{stopBlueScore:stop.header.blueScore,withdrawBlueScore:accepted.header.blueScore,lastLaneTouchBlueScore:before.lane.blueScore,
   stoppedGapBlueScores:gap,lastTouchGapBlueScores:BigInt(accepted.header.blueScore)-BigInt(before.lane.blueScore),beforeWithdrawalLane:before.lane});
  console.log('CATCHUP_CAPTURE_READY '+gap);
 }else if(stage==='payout'){
  const final=read(trial+'/final-settlement-transaction.json'),boot=read(trial+'/bootstrap-transaction.json'),deposit=read(trial+'/deposit-transaction.json');
  const permission=await unspent(final,1);assert(permission);
  const delegate=(await call('getUtxosByAddresses',{addresses:[boot.depositAddress]})).entries.find(e=>e.outpoint.transactionId===deposit.transactionId&&e.outpoint.index===0);assert(delegate);
  const fields={kind:'payout',covenantId:boot.covenantId,permissionUtxo:permission,delegateUtxo:delegate,recipient:identity.keys.user.owner,amount:400000000};
  for(const attack of ['underpay','reserve','recipient']){const reason=await submit('payout-'+attack,await build('payout-'+attack,{...fields,attack}),true);assert(/signature script|script|EqualVerify|verify/i.test(reason),'unrelated bridge rejection');}
  const payout=await build('payout',fields);await submit('payout',payout);
  const paid=await unspent(payout,0),reserve=await unspent(payout,1);assert(paid&&reserve);assert.equal(paid.utxoEntry.amount,450000000);assert.equal(reserve.utxoEntry.amount,600000000);assert(!await unspent(final,1));
  const reason=await submit('payout-replay',await build('payout-replay',fields),true);assert(/orphan|missing|unknown|not found|already spent/i.test(reason),'unrelated spent-input rejection');
  const continuation=await unspent(final,0);assert(continuation);assert.equal(continuation.utxoEntry.amount,100000000);assert.equal(continuation.utxoEntry.covenantId,boot.covenantId);
  const canonical={};for(const label of ['prefix-settlement','final-settlement','payout']){const a=read(trial+'/'+label+'-accepted.json');const b=(await call('getBlock',{hash:a.header.hash,includeTransactions:false})).block;assert(b.verboseData.isChainBlock);canonical[label]=b.header;}
  const labels=['fund-fee','fund-user','seed','bootstrap','deposit','prefix-settlement','withdraw','final-settlement','payout'];
  const fees=Object.fromEntries(labels.map(label=>[label,BigInt(read(trial+'/'+label+'-transaction.json').feeSompi)]));
  const remainingClaims=(await call('getUtxosByAddresses',{addresses:[final.outputAddresses[1]]})).entries;assert.equal(remainingClaims.length,0);
  const reserves=(await call('getUtxosByAddresses',{addresses:[boot.depositAddress]})).entries;assert.equal(reserves.reduce((n,e)=>n+BigInt(e.utxoEntry.amount),0n),600000000n);
  save(trial+'/complete.json',{scope:'LIVE_TN10_RECURSIVE_PUBLIC_ACCOUNT_REHEARSAL',server:await server(),paid,reserve,continuation,canonical,gap:read(trial+'/gap.json'),feesSompi:fees,totalFeesSompi:Object.values(fees).reduce((n,v)=>n+v,0n),
   appSpendableSompi:600000000,unpaidClaimsSompi:0,reservedNativeSompi:600000000,principalSompi:400000000,rentRefundSompi:50000000,independentOperator:false,privacy:false,trueExpiry:false});
  console.log('RECURSIVE_REHEARSAL_COMPLETE '+trial);
 }else throw Error('unknown stage');
}catch(e){if(trial)save(trial+'/'+stage+'-'+(labelArg??'job')+'-failure.json',{error:e.message,at:new Date().toISOString()});console.error(e.message);process.exitCode=1;}
finally{save(stage==='probe'?root+'/probe-'+Date.now()+'.json':trial+'/'+stage+'-'+(labelArg??'job')+'-rpc.json',records);ws.close();}
