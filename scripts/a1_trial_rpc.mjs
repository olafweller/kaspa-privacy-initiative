// Private stdin/stdout bridge for a1_trial.py. No connection in sdk-check mode.
// SDK and funding handling follow a1_serialization.mjs and a0_tn10.mjs.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';

export const pins = {
  'kaspa.js':'6d92cb305d0cc2eb26de9e305b7f7a8c17daa130ad478f0b340b50490557dbcf',
  'kaspa_bg.wasm':'c9657568610ae1d305bc2e1cf85208ceba0d1a7893c4057b38caa8add2ffb0f5',
  'package.json':'8b61fefaba842c41b805291d95b2f9e81778ec590813a6c34eddcd316659b8d0',
};
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
// Pinned WASM responses expose Option::None as an own undefined property.
// Preserve it as JSON null; JSON.stringify's default would erase Full fields.
// Genuinely absent properties stay absent and the strict scanner rejects them.
export const stringify = x => JSON.stringify(x, (_, v) => v === undefined ? null : typeof v === 'bigint' ? v.toString() : v);
const spk = s => s.version.toString(16).padStart(4,'0') + s.script;
export function diagnostic(p,error) {
  const secrets=new Set();
  const collect=v=>{
    if(v&&typeof v==='object') for(const [name,value] of Object.entries(v)) {
      if(/secret|private.?key|password|token|seed|mnemonic/i.test(name)&&typeof value==='string'&&value) secrets.add(value);
      else if(value&&typeof value==='object') collect(value);
    }
  };
  collect(p);
  collect(process.env);
  if(p?.wallet) {try {collect(JSON.parse(fs.readFileSync(p.wallet)));} catch {}}
  for(const filename of p?.secret_files??[]) {try {
    const raw=fs.readFileSync(filename);if(raw.length) for(const value of [raw.toString('hex'),raw.toString('hex').toUpperCase(),raw.toString('base64'),JSON.stringify([...raw])]) secrets.add(value);
  } catch {}}
  const redact=value=>{
    let text=Buffer.isBuffer(value)?value.toString('utf8'):String(value??'');
    for(const secret of [...secrets].sort((a,b)=>b.length-a.length)) text=text.split(secret).join('[REDACTED]');
    return text.replace(/(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])/gi,'[REDACTED-32-BYTE-HEX]');
  };
  const directory=p?.run_dir??p?.run??path.resolve('.local','diagnostic-run-'+crypto.randomUUID());
  fs.mkdirSync(directory,{recursive:true,mode:0o700});
  const filename=path.join(directory,'error-js-'+crypto.randomUUID()+'.private.json');
  const chain=[];let current=error;
  while(current) {
    chain.push({type:redact(current.constructor?.name??typeof current),name:redact(current.name??''),message:redact(current.message??current),
      traceback:redact(current.stack??new Error('Non-Error throw; bridge stack').stack),stdout:redact(current.stdout),stderr:redact(current.stderr)});
    current=current.cause;
  }
  const record={schema:'kpi-a1-error/v1',type:chain[0]?.type,message:chain[0]?.message,traceback:chain[0]?.traceback,
    causes:chain,locals_captured:false,secrets_redacted:true};
  const fd=fs.openSync(filename,'wx',0o600);
  try {fs.writeFileSync(fd,stringify(record)+'\n');fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
  return filename;
}
export function canonical(tx) {
  tx.finalize();
  return {version:tx.version,id:tx.id,inputs:tx.inputs.map(i=>({previousOutpoint:{transactionId:i.previousOutpoint.transactionId,index:i.previousOutpoint.index},
    signatureScript:i.signatureScript??'',sequence:i.sequence.toString(),sigOpCount:i.sigOpCount,computeBudget:i.computeBudget})),
    outputs:tx.outputs.map(o=>({value:o.value.toString(),scriptPublicKey:spk(o.scriptPublicKey),covenant:o.covenant?
      {authorizingInput:o.covenant.authorizingInput,covenantId:o.covenant.covenantId.toString()}:null})),
    lockTime:tx.lockTime.toString(),subnetworkId:tx.subnetworkId,gas:tx.gas.toString(),payload:tx.payload,storageMass:tx.storageMass.toString()};
}
export function decode(k, raw, entry) {
  const safe={...raw,inputs:raw.inputs.map(i=>({transactionId:i.previousOutpoint.transactionId,index:i.previousOutpoint.index,
    signatureScript:i.signatureScript,sequence:i.sequence,sigOpCount:i.sigOpCount,computeBudget:i.computeBudget,
    utxo:{...entry,address:null,amount:String(entry.amount),blockDaaScore:String(entry.blockDaaScore)}}))};
  const tx=k.Transaction.deserializeFromSafeJSON(JSON.stringify(safe));
  const decoded=k.Transaction.deserializeFromSafeJSON(tx.serializeToSafeJSON());
  const numeric=k.Transaction.deserializeFromJSON(decoded.serializeToJSON());
  for(const t of [tx,decoded,numeric]) {
    assert.deepEqual(canonical(t),raw,'SDK body changed');
    const u=t.inputs[0].utxo;
    assert.deepEqual({amount:u.amount.toString(),scriptPublicKey:spk(u.scriptPublicKey),blockDaaScore:u.blockDaaScore.toString(),
      isCoinbase:u.isCoinbase,covenantId:u.entry.covenantId?.toString()??null},
      {...entry,amount:String(entry.amount),blockDaaScore:String(entry.blockDaaScore)},'SDK entry changed');
    assert.deepEqual({transactionId:u.outpoint.transactionId,index:u.outpoint.index},raw.inputs[0].previousOutpoint);
  }
  tx.free(); numeric.free(); return decoded;
}
function normalizeUtxo(u) {
  const e=u.entry??u;
  return {outpoint:{transactionId:e.outpoint.transactionId,index:e.outpoint.index},entry:{amount:e.amount.toString(),
    scriptPublicKey:spk(e.scriptPublicKey),blockDaaScore:e.blockDaaScore.toString(),isCoinbase:e.isCoinbase,
    covenantId:e.covenantId?.toString()??null}};
}
export async function execute(p, rpcFactory = (k,url)=>new k.RpcClient({url,networkId:'testnet-10'})) {
  try {return await executeInner(p,rpcFactory);}
  catch(error) {
    const filename=diagnostic(p,error);
    console.error('Full private SDK/RPC diagnostic: '+filename);
    const wrapped=error instanceof Error?error:new Error('Non-Error SDK/RPC throw',{cause:error});
    wrapped.diagnostic_path=filename;throw wrapped;
  }
}
async function executeInner(p, rpcFactory) {
  for(const [n,h] of Object.entries(pins)) assert.equal(sha(fs.readFileSync(path.join(p.sdk_dir,n))),h,'SDK pin');
  const k=createRequire(import.meta.url)(path.join(p.sdk_dir,'kaspa.js'));
  if(p.op==='sdk-check') {
    const tx=decode(k,p.transaction,p.entry);const body=canonical(tx);tx.free();return {transaction:body,sdk_files:pins};
  }
  assert.equal(p.network,'testnet-10');
  const url=new URL(p.rpc_url);
  assert.ok(['ws:','wss:'].includes(url.protocol) && ['127.0.0.1','localhost','[::1]'].includes(url.hostname),'use C loopback or an SSH tunnel');
  const rpc=rpcFactory(k,p.rpc_url); // Tests inject synthetic chain assertions; CLI never does.
  try {
    await rpc.connect({blockAsyncConnect:true,strategy:'retry',timeoutDuration:120000});
    const info=await rpc.getServerInfo();
    assert.equal(info.networkId,'testnet-10');assert.equal(info.serverVersion,'2.1.0');
    assert.equal(info.isSynced,true);assert.equal(info.hasUtxoIndex,true);
    const dag=await rpc.getBlockDagInfo();assert.equal(dag.network,'testnet-10');
    // The validated C node is trusted for chain assertions, not a light client.
    const address=s=>k.addressFromScriptPublicKey(s,'testnet-10').toString();
    const utxos=async scripts=>(await rpc.getUtxosByAddresses({addresses:scripts.map(address)})).entries.map(normalizeUtxo);
    if(p.op==='checkpoint') {
      const block=(await rpc.getBlock({hash:dag.sink,includeTransactions:false})).block;
      assert.equal(block.header.hash,dag.sink);assert.equal(block.verboseData.isChainBlock,true);
      return {hash:dag.sink,blue_score:block.header.blueScore,daa_score:block.header.daaScore,utxos:await utxos(p.scripts)};
    }
    if(p.op==='page') return await rpc.getVirtualChainFromBlockV2({startHash:p.start,dataVerbosityLevel:'Full',minConfirmationCount:0});
    if(p.op==='snapshot') return {horizon:dag.sink,utxos:await utxos(p.scripts)};
    if(p.op==='survives') {
      const delta=await rpc.getVirtualChainFromBlockV2({startHash:p.start,dataVerbosityLevel:'None',minConfirmationCount:0});
      assert.equal(delta.removedChainBlockHashes.length,0,'reorg: stop this trial');return {survives:true};
    }
    if(p.op==='submit') {
      let tx;
      if(p.entry) tx=decode(k,p.transaction,p.entry);
      else {
        const raw=p.transaction;
        tx=new k.Transaction({...raw,inputs:raw.inputs.map(i=>({...i,sequence:BigInt(i.sequence)})),
          outputs:raw.outputs.map(o=>({...o,value:BigInt(o.value),covenant:undefined})),
          lockTime:BigInt(raw.lockTime),gas:BigInt(raw.gas),storageMass:BigInt(raw.storageMass)});
        assert.deepEqual(canonical(tx),raw);
      }
      let result;
      try {result=await rpc.submitTransaction({transaction:tx,allowOrphan:false});}
      catch(error) {
        // Submission contains public transaction bytes, never the wallet/claim
        // secret. Retain the error privately; transport loss is NOT rejection.
        const error_path=diagnostic(p,error);
        console.error('Full private submission diagnostic: '+error_path);
        tx.free();return {status:'rpc-error',transactionId:p.transaction.id,error_path,submission_attempted:true,definitive_rejection:false};
      }
      assert.equal(result.transactionId,p.transaction.id);tx.free();return result;
    }
    if(p.op==='fund-plan') {
      assert.equal(fs.statSync(p.wallet).mode&0o777,0o600,'private wallet mode');
      const wallet=JSON.parse(fs.readFileSync(p.wallet));assert.equal(wallet.network,'testnet-10');
      const key=new k.PrivateKey(wallet.private_key),from=key.toKeypair().toAddress('testnet-10').toString();
      const to=address(p.spk);assert.notEqual(from,to);
      const available=(await rpc.getUtxosByAddresses({addresses:[from]})).entries;
      const generator=new k.Generator({entries:available,outputs:[{address:to,amount:BigInt(p.amount)}],changeAddress:from,
        priorityFee:500000n,networkId:'testnet-10'});
      const pending=await generator.next();assert.ok(pending);assert.ok(!(await generator.next()),'one funding transaction required');pending.sign([key]);
      const tx=pending.transaction;let raw=canonical(tx);assert.equal(raw.version,0);
      const entries=raw.inputs.map(i=>normalizeUtxo(available.find(u=>{
        const e=u.entry??u;return e.outpoint.transactionId===i.previousOutpoint.transactionId && e.outpoint.index===i.previousOutpoint.index;
      })));assert.ok(new Set(entries.map(x=>`${x.outpoint.transactionId}:${x.outpoint.index}`)).size===entries.length);
      const exact=x=>{const n=BigInt(x);assert.ok(n>=0n&&n<=BigInt(Number.MAX_SAFE_INTEGER));return Number(n);};
      const mass=k.calculateStorageMass('testnet-10',entries.map(x=>exact(x.entry.amount)),raw.outputs.map(o=>exact(o.value)));
      assert.notEqual(mass,undefined);tx.storageMass=mass;raw=canonical(tx);
      const matches=raw.outputs.map((o,index)=>({o,index})).filter(({o})=>o.scriptPublicKey===p.spk&&BigInt(o.value)===BigInt(p.amount)&&o.covenant===null);
      assert.equal(matches.length,1);assert.ok(raw.outputs.length<=2&&raw.outputs.every(o=>o.covenant===null &&
        (o.scriptPublicKey===p.spk&&BigInt(o.value)===BigInt(p.amount)||o.scriptPublicKey===spk(k.payToAddressScript(from)))));
      const fee=entries.reduce((s,x)=>s+BigInt(x.entry.amount),0n)-raw.outputs.reduce((s,o)=>s+BigInt(o.value),0n);
      assert.ok(fee>0n && fee<=10000000n,'funding fee exceeds inherited 0.1 test KAS cap');
      const context={entries:entries.map(x=>({outpoint:x.outpoint,amount:x.entry.amount,scriptPublicKeyHex:x.entry.scriptPublicKey,
        blockDaaScore:x.entry.blockDaaScore,isCoinbase:x.entry.isCoinbase,covenantId:x.entry.covenantId})),
        virtualDaaScore:dag.virtualDaaScore,pastMedianTime:dag.pastMedianTime};
      fs.writeFileSync(p.context_file,stringify(context),{flag:'wx',mode:0o600});
      fs.writeFileSync(p.body_file,stringify(raw),{flag:'wx',mode:0o600});
      const checked=JSON.parse(execFileSync(p.funding_validator,['live','check-generic',p.context_file,p.body_file],{encoding:'utf8',stdio:['ignore','pipe','pipe']}));
      assert.equal(BigInt(checked.fee_sompi),fee);return {transaction:raw,index:matches[0].index,fee:fee.toString(),native_full:true};
    }
    throw Error('unknown RPC operation');
  } finally {await rpc.disconnect();}
}
if(process.argv[1]===new URL(import.meta.url).pathname) {
  let p;
  try {p=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(stringify(await execute(p)));}
  catch(error) {
    const filename=error.diagnostic_path??diagnostic(p,error);
    console.error('A1 SDK/RPC operation failed. Full private diagnostic: '+filename+'. No automatic resubmission.');process.exitCode=1;
  }
}
