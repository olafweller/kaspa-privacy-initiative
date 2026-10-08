import {loadTerms} from './fixed_terms.mjs';
import {fileURLToPath} from 'node:url';import path from 'node:path';
// Independently validate the already signed ordinary wallet funding body.
// A1's parser intentionally accepts version1 transitions only; ordinary v0
// funding uses the previously reviewed unchanged A0 generic Full validator.
import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {createRequire} from 'node:module';import {execFileSync} from 'node:child_process';
import {canonical,transaction} from '@KPI_REPO@/scripts/a0_tn10.mjs';
const r='@KPI_REPO@/.local/g5-preparation',d=path.join(path.dirname(fileURLToPath(import.meta.url)),'live-execution'),a0='@KPI_REPO@';
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const reviewed=JSON.parse(fs.readFileSync(a0+'/.local/a0-tn10/review.json'));
for(const f of ['poc/a0/target/release/kpi-poc-a0','poc/a0/src/live.rs','poc/a0/src/main.rs','poc/a0/Cargo.lock','scripts/a0_tn10.mjs'])assert.equal(sha(a0+'/'+f),reviewed.sha256[f]);
const raw=JSON.parse(fs.readFileSync(d+'/funding-transaction.json')),q=JSON.parse(fs.readFileSync(d+'/funding-full-request.json'));
const context=JSON.parse(fs.readFileSync(d+'/wallet-context-refreshed.json')),meta=JSON.parse(fs.readFileSync(d+'/run-location.private.json'));
const m=JSON.parse(fs.readFileSync(meta.path+'/public/manifest.json'));const {reserve,feeCap,maximumDebit}=loadTerms(d,meta.path+'/public/manifest.json');assert.equal(m.network,'testnet-10');assert.equal(context.server.networkId,'testnet-10');assert.equal(context.server.isSynced,true);
assert.equal(raw.version,0);assert.equal(raw.inputs.length,1);assert.ok(raw.outputs.length<=2);assert.equal(raw.outputs[0].value,reserve.toString());assert.equal(raw.outputs[0].scriptPublicKey,m.states.s0.spk_hex);
assert.ok(raw.outputs.every((o,i)=>o.covenant===null&&(i===0||o.scriptPublicKey===q.entry.scriptPublicKey)));assert.equal(q.entry.isCoinbase,false);assert.equal(q.entry.covenantId,null);
// Ordinary v0 SDK funding uses sequence=0, unlike the version1 continuation.
// Native Full validates the supplied sequence at the actual C DAG context.
assert.equal(raw.lockTime,'0');assert.equal(raw.gas,'0');assert.equal(raw.payload,'');assert.equal(raw.subnetworkId,'00'.repeat(20));assert.equal(raw.inputs[0].sequence,'0');
const op=raw.inputs[0].previousOutpoint;
const available=context.utxos.entries.filter(e=>e.outpoint.transactionId===op.transactionId&&e.outpoint.index===op.index);assert.equal(available.length,1);assert.equal(available[0].utxoEntry.amount,q.entry.amount);
const fee=BigInt(q.entry.amount)-raw.outputs.reduce((s,o)=>s+BigInt(o.value),0n);assert.ok(fee>0n&&fee<=feeCap);assert.ok(reserve+fee<=maximumDebit);
const full=JSON.parse(execFileSync(a0+'/poc/a0/target/release/kpi-poc-a0',['live','check-generic',d+'/funding-generic-context.json',d+'/funding-transaction.json'],{encoding:'utf8',stdio:['ignore','pipe','pipe']}));assert.equal(full.accepted_locally,true);assert.equal(full.transaction_id,raw.id);assert.equal(BigInt(full.fee_sompi),fee);
const independently=JSON.parse(execFileSync('@KPI_REPO@/.local/worktrees/a1-poc/poc/a1/target/release/a1_reference',['--body',d+'/funding-transaction.json'],{encoding:'utf8',stdio:['ignore','pipe','pipe']}));assert.equal(independently.txid,raw.id);
const sdk=createRequire(import.meta.url)(a0+'/.local/sdk/kaspa-wasm32-sdk/nodejs/kaspa');const tx=transaction(raw);assert.deepEqual(canonical(tx),raw);
const populated=new sdk.UtxoEntries([{...q.entry,outpoint:op,amount:BigInt(q.entry.amount),blockDaaScore:BigInt(q.entry.blockDaaScore)}]);
tx.inputs=raw.inputs.map(i=>({...i,sequence:BigInt(i.sequence),utxo:populated.items[0]}));assert.deepEqual(canonical(tx),raw);
const mass=sdk.calculateTransactionMass('testnet-10',tx);assert.ok(mass>0n&&mass<=100000n);
const buckets=[context.fees.estimate.priorityBucket,...context.fees.estimate.normalBuckets,...context.fees.estimate.lowBuckets],rate=Number(fee)/Number(mass);assert.ok(rate>=100&&buckets.some(b=>Number.isFinite(b.feerate)&&b.feerate>=100&&b.feerate*1.25<=rate&&b.estimatedSeconds<=30));
const write=(n,v)=>fs.writeFileSync(d+'/'+n,JSON.stringify(v,null,2),{flag:'wx',mode:0o600});
write('funding-full-validation.json',{...full,Full:true,validator_sha256:sha(a0+'/poc/a0/target/release/kpi-poc-a0'),independent_reference:independently,SDK_mass:mass.toString()});
write('funding-review.json',{at:Date.now()/1000,TN10_only:true,txid:raw.id,full_hash:independently.full_hash,S0_index:0,reserve_sompi:reserve.toString(),funding_fee_sompi:fee.toString(),wallet_debit_sompi:(reserve+fee).toString(),native_Full:true,independent_reference:true,one_input:true,fee_headroom_25_percent:true,SDK_mass:mass.toString(),body_sha256:sha(d+'/funding-transaction.json'),broadcast:false});
console.log(JSON.stringify({funding_Full:true,fee_sompi:fee.toString(),wallet_debit_sompi:(reserve+fee).toString(),mass:mass.toString(),broadcast:false}));
