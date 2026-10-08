// Read-only SDK transaction qualification, adapted from the pinned continuation adapter.
// No RpcClient, network, signer, submission or broadcast operation.
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {createRequire} from 'node:module';
const [sdkDir,bodyPath,requestPath,outDir]=process.argv.slice(2);const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const pins={'package.json':'8b61fefaba842c41b805291d95b2f9e81778ec590813a6c34eddcd316659b8d0','kaspa.js':'6d92cb305d0cc2eb26de9e305b7f7a8c17daa130ad478f0b340b50490557dbcf','kaspa_bg.wasm':'c9657568610ae1d305bc2e1cf85208ceba0d1a7893c4057b38caa8add2ffb0f5'};
for(const [n,h]of Object.entries(pins))assert.equal(sha(fs.readFileSync(path.join(sdkDir,n))),h,'SDK file pin');
const sdk=createRequire(import.meta.url)(path.join(sdkDir,'kaspa.js'));assert.equal(JSON.parse(fs.readFileSync(path.join(sdkDir,'package.json'))).version,'2.1.0');
const raw=JSON.parse(fs.readFileSync(bodyPath)),req=JSON.parse(fs.readFileSync(requestPath)),entry=req.entry;
const spk=s=>s.version.toString(16).padStart(4,'0')+s.script;
function canonical(tx){tx.finalize();return {version:tx.version,id:tx.id,inputs:tx.inputs.map(i=>({previousOutpoint:{transactionId:i.previousOutpoint.transactionId,index:i.previousOutpoint.index},signatureScript:i.signatureScript??'',sequence:i.sequence.toString(),sigOpCount:i.sigOpCount,computeBudget:i.computeBudget})),outputs:tx.outputs.map(o=>({value:o.value.toString(),scriptPublicKey:spk(o.scriptPublicKey),covenant:o.covenant?{authorizingInput:o.covenant.authorizingInput,covenantId:o.covenant.covenantId.toString()}:null})),lockTime:tx.lockTime.toString(),subnetworkId:tx.subnetworkId,gas:tx.gas.toString(),payload:tx.payload,storageMass:tx.storageMass.toString()};}
function context(tx){const u=tx.inputs[0].utxo;assert.ok(u,'decoded UTXO context missing');return {amount:u.amount.toString(),scriptPublicKey:spk(u.scriptPublicKey),blockDaaScore:u.blockDaaScore.toString(),isCoinbase:u.isCoinbase,covenantId:u.entry.covenantId?.toString()??null};}
const wantContext={amount:String(entry.amount),scriptPublicKey:entry.scriptPublicKey,blockDaaScore:String(entry.blockDaaScore),isCoinbase:entry.isCoinbase,covenantId:entry.covenantId};
function check(tx){assert.deepEqual(canonical(tx),raw,'SDK changed exact terminal body');assert.deepEqual(context(tx),wantContext,'SDK changed input amount/context');assert.deepEqual({transactionId:tx.inputs[0].utxo.outpoint.transactionId,index:tx.inputs[0].utxo.outpoint.index},raw.inputs[0].previousOutpoint,'SDK changed UTXO outpoint');}
function stable(v){if(Array.isArray(v))return v.map(stable);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])]));return v;}
const safe={...raw,inputs:raw.inputs.map(i=>({transactionId:i.previousOutpoint.transactionId,index:i.previousOutpoint.index,signatureScript:i.signatureScript,sequence:i.sequence,sigOpCount:i.sigOpCount,computeBudget:i.computeBudget,utxo:{...entry,address:null,amount:String(entry.amount),blockDaaScore:String(entry.blockDaaScore)}}))};
const original=sdk.Transaction.deserializeFromSafeJSON(JSON.stringify(safe));check(original);
const wire=original.serializeToSafeJSON();const decoded=sdk.Transaction.deserializeFromSafeJSON(wire);check(decoded);
const numeric=decoded.serializeToJSON();const decodedNumeric=sdk.Transaction.deserializeFromJSON(numeric);check(decodedNumeric);
for(const [name,data]of [['terminal-sdk-safe.json',wire],['terminal-sdk-numeric.json',numeric],['terminal-sdk-decoded.json',JSON.stringify(stable(canonical(decoded)))],['terminal-sdk-decoded-request.json',JSON.stringify(stable({transaction:canonical(decoded),entry}))]])fs.writeFileSync(path.join(outDir,name),data,{flag:'wx',mode:0o600});
console.log(JSON.stringify({roundtrip_valid:true,sdk:{version:'2.1.0',files_sha256:pins},runtime:{version:process.version,sha256:sha(fs.readFileSync(process.execPath))}}));
decodedNumeric.free();decoded.free();original.free();
