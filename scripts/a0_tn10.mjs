#!/usr/bin/env node
// TN10-only experiment orchestration using the pinned upstream SDK.
// Wallet keys never leave the process except writes to the new ignored wallet file.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Measure public native-wRPC submission frames without retaining packet bodies.
let submissionFrames = null;
const NativeWebSocket = globalThis.WebSocket;
globalThis.WebSocket = class extends NativeWebSocket {
  send(data) {
    if (submissionFrames !== null) {
      const bytes = typeof data === 'string' ? Buffer.from(data) : Buffer.from(data.buffer ?? data, data.byteOffset ?? 0, data.byteLength);
      submissionFrames.push({bytes:bytes.byteLength,sha256:crypto.createHash('sha256').update(bytes).digest('hex')});
    }
    return super.send(data);
  }
};
const k = createRequire(import.meta.url)(path.join(root, '.local/sdk/kaspa-wasm32-sdk/nodejs/kaspa'));
const dir = path.join(root, '.local/a0-tn10');
const envFile = path.join(root, '.env.tn10.local');
const binary = path.join(root, 'poc/a0/target/release/kpi-poc-a0');
const GENESIS = 'f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370';
const RPC = 'ws://127.0.0.1:17210'; // Own pinned node only, no endpoint substitution.
const NODE_SHA256 = 'adf711b68abb2fabbb33cfdaab8f915bb615f8d7d1b33a867328b4672ddd376f';
let stage = 'argument and configuration checks';
const stringify = value => JSON.stringify(value, (_, x) => typeof x === 'bigint' ? x.toString() : x, 2);
const read = name => JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8'));
const exists = name => fs.existsSync(path.join(dir, name));
function save(name, value) {
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  fs.writeFileSync(path.join(dir, name), `${stringify(value)}\n`, { flag: 'wx', mode: 0o600 });
}
function rust(...args) {
  stage = `local validator ${args[0]}`;
  return JSON.parse(execFileSync(binary, ['live', ...args], { encoding: 'utf8', maxBuffer: 8*1024*1024, stdio: ['ignore','pipe','pipe'] }));
}
function env(pathname) {
  // Intentionally no shell evaluation, interpolation or dotenv side effects.
  const result = {};
  for (const line of fs.readFileSync(pathname, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match) continue;
    let value = match[2];
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1,-1);
    else value = value.replace(/\s+#.*$/, '');
    result[match[1]] = value;
  }
  return result;
}
function wallet() {
  const mode = fs.statSync(envFile).mode & 0o777;
  assert.equal(mode, 0o600, 'KPI wallet must have mode 0600');
  const w = env(envFile);
  assert.equal(w.KASPA_NETWORK, 'tn10');
  for (const role of ['FUNDING','RECIPIENT'])
    assert.equal(new k.PrivateKey(w[`KPI_${role}_PRIVATE_KEY`]).toKeypair().toAddress('testnet-10').toString(), w[`KPI_${role}_ADDRESS`]);
  return w;
}
function spk(key) { return key.version.toString(16).padStart(4,'0') + key.script; }
export function canonical(tx) {
  // Do not trust an optional SDK cached ID copied from an input object.
  tx.finalize();
  return {
    version: tx.version, id: tx.id,
    inputs: tx.inputs.map(i => ({ previousOutpoint: {transactionId:i.previousOutpoint.transactionId,index:i.previousOutpoint.index},
      signatureScript:i.signatureScript ?? '',sequence:i.sequence.toString(),sigOpCount:i.sigOpCount,computeBudget:i.computeBudget })),
    outputs: tx.outputs.map(o => ({value:o.value.toString(),scriptPublicKey:spk(o.scriptPublicKey),
      covenant:o.covenant ? {authorizingInput:o.covenant.authorizingInput,covenantId:o.covenant.covenantId.toString()} : null})),
    lockTime:tx.lockTime.toString(),subnetworkId:tx.subnetworkId,gas:tx.gas.toString(),payload:tx.payload,storageMass:tx.storageMass.toString(),
  };
}
export function transaction(raw) {
  // u64 quantities remain BigInt through construction and native wRPC serialization.
  const outputs = raw.outputs.map(o => {
    assert.ok(Object.hasOwn(o,'covenant'),'explicit source covenant metadata required');
    const output = {...o,value:BigInt(o.value)};
    // The upstream JS constructor represents Option::None by absence, not JS null.
    // Canonical readback below MUST restore exactly the original explicit null.
    if (o.covenant === null) delete output.covenant;
    return output;
  });
  const tx = new k.Transaction({...raw, inputs:raw.inputs.map(i => ({...i,sequence:BigInt(i.sequence)})),
    outputs,lockTime:BigInt(raw.lockTime),gas:BigInt(raw.gas),storageMass:BigInt(raw.storageMass)});
  assert.deepEqual(canonical(tx), raw, 'SDK changed a transaction field');
  return tx;
}
function entry(u) {
  const e = u.entry ?? u;
  return {outpoint:{transactionId:e.outpoint.transactionId,index:e.outpoint.index}, amount:e.amount.toString(),
    scriptPublicKeyHex:spk(e.scriptPublicKey),blockDaaScore:e.blockDaaScore.toString(),isCoinbase:e.isCoinbase,
    covenantId:e.covenantId?.toString() ?? null};
}
function ownNode() {
  const pid=fs.readFileSync(path.join(root,'.local/node/pid'),'utf8').trim();
  assert.match(pid,/^[1-9][0-9]*$/);
  const proc=`/proc/${pid}`;
  const executable=fs.realpathSync(`${proc}/exe`);
  assert.equal(executable,path.join(root,'.local/node/bin/kaspad'));
  assert.equal(fs.realpathSync(`${proc}/cwd`),root);
  const sha256=crypto.createHash('sha256').update(fs.readFileSync(executable)).digest('hex');
  assert.equal(sha256,NODE_SHA256);
  const args=fs.readFileSync(`${proc}/cmdline`,'utf8').split('\0').filter(Boolean).slice(1);
  assert.deepEqual(args,['--testnet','--utxoindex','--appdir=.local/node/data','--logdir=.local/node/logs',
    '--rpclisten=127.0.0.1:16210','--rpclisten-borsh=127.0.0.1:17210','--rpclisten-json=127.0.0.1:18210',
    '--listen=127.0.0.1:16211','--maxinpeers=0','--disable-upnp','--ram-scale=0.3','--outpeers=4']);
  const stat=fs.readFileSync(`${proc}/stat`,'utf8');
  const start_ticks=stat.slice(stat.lastIndexOf(')')+2).trim().split(/\s+/)[19];
  return {pid,start_ticks,sha256,args};
}
async function identity(rpc, requireSync=true) {
  stage = 'TN10 identity and synchronization';
  const processIdentity=ownNode();
  const info = await rpc.getServerInfo();
  assert.equal(info.networkId, 'testnet-10', 'wrong network');
  assert.equal(info.serverVersion, '2.1.0', 'wrong node version');
  assert.equal(info.hasUtxoIndex, true);
  if (requireSync) assert.equal(info.isSynced, true, 'node still syncing');
  let header,genesis_method='fresh RPC header, independently hashed';
  try {header=(await rpc.getBlock({hash:GENESIS,includeTransactions:false})).block.header;}
  catch(error) {
    // A pruned node may no longer retain genesis after validated IBD. Accept only
    // an earlier actual RPC header from this exact still-running pinned process.
    assert.match(String(error),/cannot find header/i);
    const anchor=read('node-genesis.json');
    assert.deepEqual(anchor.process,processIdentity,'node changed since genesis observation');
    header=anchor.header;
    genesis_method='retained actual RPC genesis header from same pinned running process before pruning; native consensus validated IBD';
  }
  const h = new k.Header(header);
  assert.equal(h.finalize(), GENESIS, 'independently computed genesis mismatch');
  if(!exists('node-genesis.json')) save('node-genesis.json',{observed_at:new Date().toISOString(),header,genesis_recomputed:h.hash,process:processIdentity});
  const dag = await rpc.getBlockDagInfo();
  assert.equal(dag.network,'testnet-10');
  return {observed_at:new Date().toISOString(),rpc:RPC,info,genesis_header:header,genesis_recomputed:h.hash,genesis_method,process:processIdentity,dag};
}
async function utxos(rpc,address) { return (await rpc.getUtxosByAddresses({addresses:[address]})).entries; }
function reserveContext(u, dag) {
  return {outpoint:u.outpoint,utxoEntry:{amount:u.amount,scriptPublicKeyHex:u.scriptPublicKeyHex,blockDaaScore:u.blockDaaScore,
    isCoinbase:u.isCoinbase,covenantId:u.covenantId},virtualDaaScore:dag.virtualDaaScore.toString(),pastMedianTime:dag.pastMedianTime.toString()};
}
function checkedProof(w, inputName, outputName) {
  const proof = rust('prepare',w.KPI_PROVING_DIRECTORY,path.join(dir,inputName));
  stage = 'SDK transaction field roundtrip';
  const raw = canonical(transaction(proof.transaction));
  assert.deepEqual(raw, proof.transaction);
  save(`${outputName}-transaction.json`, raw);
  const valid = rust('check',w.KPI_PROVING_DIRECTORY,path.join(dir,inputName),path.join(dir,`${outputName}-transaction.json`));
  assert.equal(valid.fee_sompi,20000000);
  save(`${outputName}.json`,proof);
  return proof;
}
const reviewFiles = ['scripts/a0_tn10.mjs','poc/a0/src/main.rs','poc/a0/src/live.rs','poc/a0/src/circuit.rs',
  'poc/a0/Cargo.toml','poc/a0/Cargo.lock','scripts/run_poc_a0.sh','scripts/start_a0_tn10_node.sh',
  'poc/a0/target/release/kpi-poc-a0','.local/node/bin/kaspad',
  '.local/sdk/kaspa-wasm32-sdk/nodejs/kaspa/kaspa.js',
  '.local/sdk/kaspa-wasm32-sdk/nodejs/kaspa/kaspa_bg.wasm'];
function reviewGate() {
  const review = read('review.json');
  assert.equal(review.approved_for_test_funding,true);
  for (const file of reviewFiles) assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex'),review.sha256[file],`review stale: ${file}`);
}
async function buildFunding(rpc,keyHex,from,to,amount,dag,label,suppliedEntries) {
  stage = 'funding wallet address verification';
  assert.equal(new k.PrivateKey(keyHex).toKeypair().toAddress('testnet-10').toString(),from);
  assert.ok(from.startsWith('kaspatest:') && to.startsWith('kaspatest:'));
  const available = suppliedEntries ?? await utxos(rpc,from);
  const generator = new k.Generator({entries:available,outputs:[{address:to,amount}],changeAddress:from,
    priorityFee:500000n,networkId:'testnet-10'});
  const pending = await generator.next();
  assert.ok(pending,'no spendable funding inputs');
  assert.ok(!(await generator.next()), 'experiment requires one funding transaction');
  pending.sign([new k.PrivateKey(keyHex)]);
  const tx = pending.transaction;
  const raw = canonical(tx);
  const targetScript=spk(k.payToAddressScript(to)),changeScript=spk(k.payToAddressScript(from));
  assert.notEqual(targetScript,changeScript);
  assert.equal(raw.outputs.filter(o=>o.scriptPublicKey===targetScript && BigInt(o.value)===amount && o.covenant===null).length,1);
  assert.ok(raw.outputs.length<=2 && raw.outputs.every(o=>o.covenant===null &&
    (o.scriptPublicKey===targetScript && BigInt(o.value)===amount || o.scriptPublicKey===changeScript)), 'unexpected funding output');
  // The source/recipient keys are never passed to the validator or evidence files.
  const availableMap = new Map(available.map(u => {const e=entry(u);return [`${e.outpoint.transactionId}:${e.outpoint.index}`,e];}));
  const entries = raw.inputs.map(i=>availableMap.get(`${i.previousOutpoint.transactionId}:${i.previousOutpoint.index}`));
  assert.ok(entries.every(Boolean));
  const total = entries.reduce((sum,e)=>sum+BigInt(e.amount),0n);
  const outputTotal = raw.outputs.reduce((sum,o)=>sum+BigInt(o.value),0n);
  const fee = total-outputTotal;
  assert.ok(fee>0n && fee<=10000000n,'funding fee exceeds 0.1 test KAS cap');
  save(`${label}-context.json`,{entries,virtualDaaScore:dag.virtualDaaScore,pastMedianTime:dag.pastMedianTime});
  save(`${label}-transaction.json`,raw);
  const checked = rust('check-generic',path.join(dir,`${label}-context.json`),path.join(dir,`${label}-transaction.json`));
  assert.equal(BigInt(checked.fee_sompi),fee);
  return {tx:transaction(raw),raw,fee_sompi:fee.toString()};
}
async function submit(rpc,raw,label) {
  stage = `${label} submission`;
  assert.ok(!exists(`${label}-submission.json`),'submission already recorded; inspect/resume manually');
  const before = await rpc.getBlockDagInfo();
  const started = Date.now();
  // Durable intent makes an ambiguous RPC failure a manual inspection boundary.
  // create_new prevents automatic resubmission after a crash or lost response.
  save(`${label}-submission-intent.json`,{transaction_id:raw.id,start_hash:before.sink,started_at:new Date(started).toISOString()});
  let response;
  submissionFrames = [];
  try { response = await rpc.submitTransaction({transaction:transaction(raw),allowOrphan:false}); }
  finally { if (!response) submissionFrames = null; }
  const frames = submissionFrames; submissionFrames = null;
  assert.equal(response.transactionId,raw.id);
  const record = {started_at:new Date(started).toISOString(),started_ms:started,returned_at:new Date().toISOString(),
    transaction_id:raw.id,response,start_hash:before.sink,wrpc_submission_frames:frames,
    frame_scope:'WebSocket application message payload including native wRPC envelope; excludes WebSocket/TCP framing'};
  save(`${label}-submission.json`,record);
  return record;
}
async function acceptedBody(rpc, acceptance, expected) {
  const accepting = (await rpc.getBlock({hash:acceptance.acceptingBlockHash,includeTransactions:true})).block;
  const hashes = [...new Set([acceptance.acceptingBlockHash, accepting.verboseData.selectedParentHash, ...accepting.verboseData.mergeSetBluesHashes])];
  for (const hash of hashes) {
    const block = hash===acceptance.acceptingBlockHash ? accepting : (await rpc.getBlock({hash,includeTransactions:true})).block;
    for (const raw of block.transactions) {
      if (raw.verboseData?.transactionId !== expected.id) continue;
      const tx = canonical(new k.Transaction(raw));
      assert.deepEqual(tx,expected,'accepted transaction differs from locally validated SDK transaction');
      return {containing_block_hash:hash,accepting_block_hash:acceptance.acceptingBlockHash,transaction:tx};
    }
  }
  throw new Error('accepted transaction body not located in accepting mergeset');
}
async function observe(rpc,id,startHash,address,expectedScript,expectedAmount,timeoutMs=120000) {
  stage = 'accepted transaction and exact UTXO observation';
  const started=Date.now(); let cursor=startHash; let accepted;
  while(Date.now()-started<timeoutMs) {
    const chain=await rpc.getVirtualChainFromBlock({startHash:cursor,includeAcceptedTransactionIds:true,minConfirmationCount:20});
    if (accepted && chain.removedChainBlockHashes.includes(accepted.acceptingBlockHash)) accepted=undefined;
    for(const item of chain.acceptedTransactionIds) if(item.acceptedTransactionIds.includes(id)) accepted=item;
    // Keep original anchor so reorg/acceptance is reevaluated every time within this small window.
    const outputs=(await utxos(rpc,address)).map(entry).filter(e=>e.outpoint.transactionId===id && e.scriptPublicKeyHex===expectedScript && BigInt(e.amount)===expectedAmount && e.covenantId===null);
    if(accepted && outputs.length===1) return {observed_at:new Date().toISOString(),accepted,recipient_utxo:outputs[0],
      confirmation_policy:'minConfirmationCount=20: accepting-block blue-score distance from sink >20; later observation required',dag:await rpc.getBlockDagInfo()};
    await new Promise(resolve=>setTimeout(resolve,1500));
  }
  throw new Error('acceptance/UTXO observation timed out; inspect saved transaction before retrying');
}
async function main(command) {
  if(command==='wallet') {
    assert.equal(execFileSync('git',['check-ignore','.env.tn10.local'],{cwd:root,encoding:'utf8'}).trim(),'.env.tn10.local');
    assert.ok(!fs.existsSync(envFile),'KPI wallet already exists');
    const keys=Object.fromEntries(['FUNDING','RECIPIENT'].map(role=>{const key=new k.PrivateKey(crypto.randomBytes(32).toString('hex'));return [role,key];}));
    const base=path.join(os.homedir(),'.local/share/kpi-a0');fs.mkdirSync(base,{recursive:true,mode:0o700});
    const proving=path.join(base,`tn10-${crypto.randomUUID()}`);
    const lines=['KASPA_NETWORK=tn10',`KPI_PROVING_DIRECTORY=${proving}`];
    for(const [role,key] of Object.entries(keys)) lines.push(`KPI_${role}_PRIVATE_KEY=${key.toString()}`,`KPI_${role}_ADDRESS=${key.toKeypair().toAddress('testnet-10').toString()}`);
    fs.writeFileSync(envFile,`${lines.join('\n')}\n`,{flag:'wx',mode:0o600});
    const w=wallet();
    const manifest=rust('init',proving,w.KPI_RECIPIENT_ADDRESS); save('manifest.json',manifest);
    console.log('Dedicated TN10 wallet and externally persisted claim/key created; no funds sent.');return;
  }
  const rpc=new k.RpcClient({url:RPC,networkId:'testnet-10'});
  await rpc.connect({timeoutDuration:15000});
  try {
    const node=await identity(rpc,!['identity','prefund','funding-fixture'].includes(command));
    if(command==='identity'){save(`identity-${Date.now()}.json`,node);console.log(stringify(node));return;}
    const w=wallet(); const manifest=read('manifest.json');
    assert.equal(manifest.recipient_address,w.KPI_RECIPIENT_ADDRESS);
    if(command==='funding-fixture') {
      const available=[{address:w.KPI_FUNDING_ADDRESS,outpoint:{transactionId:'43'.repeat(32),index:0},
        amount:1200000000n,scriptPublicKey:k.payToAddressScript(w.KPI_FUNDING_ADDRESS),blockDaaScore:0n,isCoinbase:false}];
      const plan=await buildFunding(rpc,w.KPI_FUNDING_PRIVATE_KEY,w.KPI_FUNDING_ADDRESS,manifest.reserve_address,1020000000n,
        node.dag,'funding-fixture',available);
      save('funding-fixture.json',{transaction_id:plan.raw.id,fee_sompi:plan.fee_sompi,scope:'synthetic supplied UTXO only; no broadcast'});
      console.log('Signed funding fixture passed native SDK roundtrip and full validator; no broadcast.');return;
    }
    if(command==='prefund') {
      if (!exists('prefund-node.json')) save('prefund-node.json',node);
      if (!exists('prefund-context.json')) save('prefund-context.json',reserveContext({outpoint:{transactionId:'42'.repeat(32),index:7},amount:'1020000000',
        scriptPublicKeyHex:manifest.reserve_spk_hex,blockDaaScore:node.dag.virtualDaaScore.toString(),isCoinbase:false,covenantId:null},node.dag));
      checkedProof(w,'prefund-context.json','prefund');
      console.log('Reloaded claim/key and exact SDK roundtrip accepted by full validator. No funding performed.');return;
    }
    if(command==='bootstrap') {
      assert.ok(exists('prefund.json'),'prefunding proof/serialization gate required');
      reviewGate();
      const sourcePath=process.argv[3];assert.ok(sourcePath,'funding source env path required');
      const source=env(sourcePath); assert.ok(['tn10','testnet-10'].includes(source.KASPA_NETWORK),'source must explicitly select TN10');
      const plan=await buildFunding(rpc,source.KASPA_USER_PRIVATE_KEY??source.TN12_USER_PRIVATE_KEY,source.KASPA_USER_ADDRESS??source.TN12_USER_ADDRESS,
        w.KPI_FUNDING_ADDRESS,1200000000n,node.dag,'bootstrap');
      const submission=await submit(rpc,plan.raw,'bootstrap');
      const expected=plan.raw.outputs.find(o=>o.value==='1200000000' && o.scriptPublicKey===spk(k.payToAddressScript(w.KPI_FUNDING_ADDRESS)));assert.ok(expected);
      const accepted=await observe(rpc,plan.raw.id,submission.start_hash,w.KPI_FUNDING_ADDRESS,expected.scriptPublicKey,1200000000n);
      save('bootstrap-acceptance.json',accepted);console.log(stringify({bootstrap_txid:plan.raw.id,fee_sompi:plan.fee_sompi,accepted}));return;
    }
    if(command==='fund') {
      assert.ok(exists('bootstrap-acceptance.json'));reviewGate();
      const plan=await buildFunding(rpc,w.KPI_FUNDING_PRIVATE_KEY,w.KPI_FUNDING_ADDRESS,manifest.reserve_address,1020000000n,node.dag,'funding');
      const matches=plan.raw.outputs.map((o,index)=>({o,index})).filter(({o})=>o.value==='1020000000'&&o.scriptPublicKey===manifest.reserve_spk_hex&&o.covenant===null);
      assert.equal(matches.length,1);
      const outpoint={transactionId:plan.raw.id,index:matches[0].index};
      save('planned-reserve-context.json',reserveContext({outpoint,amount:'1020000000',scriptPublicKeyHex:manifest.reserve_spk_hex,
        blockDaaScore:node.dag.virtualDaaScore.toString(),isCoinbase:false,covenantId:null},node.dag));
      const futureRelease=checkedProof(w,'planned-reserve-context.json','planned-release');
      const feeEstimate=await rpc.getFeeEstimate();save('funding-release-fee-estimate.json',feeEstimate);
      assert.ok(Number(futureRelease.fee_sompi)/futureRelease.compute_mass_grams >= feeEstimate.estimate.priorityBucket.feerate,
        'do not fund while the fixed reserve-release fee is below the priority estimate');
      // No byte of the reviewed/signed funding transaction is changed after proving its exact output spendable.
      const submission=await submit(rpc,plan.raw,'funding');
      const accepted=await observe(rpc,plan.raw.id,submission.start_hash,manifest.reserve_address,manifest.reserve_spk_hex,1020000000n);
      save('funding-acceptance.json',accepted);console.log(stringify({funding_txid:plan.raw.id,reserve_outpoint:outpoint,fee_sompi:plan.fee_sompi,accepted}));return;
    }
    if(command==='release-prepare') {
      const funded=read('funding-acceptance.json').recipient_utxo;
      const matches=(await utxos(rpc,manifest.reserve_address)).map(entry).filter(e=>e.outpoint.transactionId===funded.outpoint.transactionId&&e.outpoint.index===funded.outpoint.index);
      assert.equal(matches.length,1,'funded reserve is missing or already spent');
      save('live-reserve-context.json',reserveContext(matches[0],node.dag));
      const proof=checkedProof(w,'live-reserve-context.json','release');
      console.log(stringify({reserve_outpoint:funded.outpoint,release_txid:proof.transaction.id,proving_ms:proof.proving_ms,fee_sompi:proof.fee_sompi}));return;
    }
    if(command==='release') {
      reviewGate();
      const proof=read('release.json'); const reserve=read('live-reserve-context.json');
      const unspent=(await utxos(rpc,manifest.reserve_address)).map(entry).find(e=>e.outpoint.transactionId===reserve.outpoint.transactionId&&e.outpoint.index===reserve.outpoint.index);
      assert.ok(unspent,'reserve already spent');
      save('release-current-context.json',reserveContext(unspent,node.dag));
      rust('check',w.KPI_PROVING_DIRECTORY,path.join(dir,'release-current-context.json'),path.join(dir,'release-transaction.json'));
      const feeEstimate=await rpc.getFeeEstimate();save('release-fee-estimate.json',feeEstimate);
      assert.ok(Number(proof.fee_sompi)/proof.compute_mass_grams >= feeEstimate.estimate.priorityBucket.feerate,'fixed fee is below priority estimate');
      const submission=await submit(rpc,proof.transaction,'release');
      const accepted=await observe(rpc,proof.transaction.id,submission.start_hash,manifest.recipient_address,manifest.recipient_spk_hex,1000000000n);
      assert.ok(!(await utxos(rpc,manifest.reserve_address)).map(entry).some(e=>e.outpoint.transactionId===reserve.outpoint.transactionId&&e.outpoint.index===reserve.outpoint.index));
      accepted.broadcast_to_observation_ms=Date.now()-submission.started_ms;
      save('release-acceptance.json',accepted);
      save('release-accepted-body.json',await acceptedBody(rpc,accepted.accepted,proof.transaction));
      console.log(stringify(accepted));return;
    }
    if(command==='replay') {
      assert.ok(exists('release-acceptance.json'));
      const proof=read('release.json'); const outcomes=[];
      save('distinct-replay-transaction.json',proof.distinct_replay_transaction);
      const local=rust('check',w.KPI_PROVING_DIRECTORY,path.join(dir,'live-reserve-context.json'),path.join(dir,'distinct-replay-transaction.json'));
      for(const [name,raw] of [['exact',proof.transaction],['distinct',proof.distinct_replay_transaction]]) {
        try{outcomes.push({name,transaction_id:raw.id,response:await rpc.submitTransaction({transaction:transaction(raw),allowOrphan:false})});}
        catch(e){outcomes.push({name,transaction_id:raw.id,error:String(e)});}
      }
      save('replay.json',{observed_at:new Date().toISOString(),distinct_local_validation:local,outcomes});
      assert.ok(outcomes.find(o=>o.name==='distinct')?.error,'distinct spent-input transaction unexpectedly accepted');
      console.log(stringify(outcomes));return;
    }
    if(command==='recheck') {
      const proof=read('release.json'), submission=read('release-submission.json');
      const accepted=await observe(rpc,proof.transaction.id,submission.start_hash,manifest.recipient_address,manifest.recipient_spk_hex,1000000000n);
      const reserve=read('live-reserve-context.json');
      const remaining=(await utxos(rpc,manifest.reserve_address)).map(entry).filter(e=>e.outpoint.transactionId===reserve.outpoint.transactionId&&e.outpoint.index===reserve.outpoint.index);
      assert.equal(remaining.length,0);
      assert.equal((await utxos(rpc,manifest.recipient_address)).map(entry).filter(e=>e.outpoint.transactionId===proof.distinct_replay_transaction.id).length,0,'unexpected second payout');
      save(`recheck-${Date.now()}.json`,{...accepted,reserve_unspent:false,elapsed_since_broadcast_ms:Date.now()-submission.started_ms});
      console.log(stringify(accepted));return;
    }
    throw new Error('Unknown command');
  } finally { await rpc.disconnect(); }
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main(process.argv[2]).catch(() => {
  // Never print SDK exceptions from secret parsing/signing or raw env contents.
  console.error(`A0 TN10 command failed during ${stage}. No automatic retry. Inspect public artifacts and checks before resuming.`);
  process.exitCode=1;
});
