// Pinned SDK serialization to a NON-FORWARDING localhost fixture only.
// Existing network-free terminal_sdk.mjs qualification remains unchanged.
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {createRequire} from 'node:module';
const [sdkDir,safePath,bodyPath,url]=process.argv.slice(2);assert.match(url,/^ws:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}$/);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const pins={'package.json':'8b61fefaba842c41b805291d95b2f9e81778ec590813a6c34eddcd316659b8d0','kaspa.js':'6d92cb305d0cc2eb26de9e305b7f7a8c17daa130ad478f0b340b50490557dbcf','kaspa_bg.wasm':'c9657568610ae1d305bc2e1cf85208ceba0d1a7893c4057b38caa8add2ffb0f5'};
for(const[n,h]of Object.entries(pins))assert.equal(sha(fs.readFileSync(path.join(sdkDir,n))),h);
const sdk=createRequire(import.meta.url)(path.join(sdkDir,'kaspa.js'));const raw=JSON.parse(fs.readFileSync(bodyPath));
const spk=s=>s.version.toString(16).padStart(4,'0')+s.script;
function canonical(tx){tx.finalize();return {version:tx.version,id:tx.id,inputs:tx.inputs.map(i=>({previousOutpoint:{transactionId:i.previousOutpoint.transactionId,index:i.previousOutpoint.index},signatureScript:i.signatureScript??'',sequence:i.sequence.toString(),sigOpCount:i.sigOpCount,computeBudget:i.computeBudget})),outputs:tx.outputs.map(o=>({value:o.value.toString(),scriptPublicKey:spk(o.scriptPublicKey),covenant:o.covenant?{authorizingInput:o.covenant.authorizingInput,covenantId:o.covenant.covenantId.toString()}:null})),lockTime:tx.lockTime.toString(),subnetworkId:tx.subnetworkId,gas:tx.gas.toString(),payload:tx.payload,storageMass:tx.storageMass.toString()};}
const tx=sdk.Transaction.deserializeFromSafeJSON(fs.readFileSync(safePath,'utf8'));assert.deepEqual(canonical(tx),raw);const decoded=sdk.Transaction.deserializeFromSafeJSON(tx.serializeToSafeJSON());assert.deepEqual(canonical(decoded),raw);const numeric=sdk.Transaction.deserializeFromJSON(tx.serializeToJSON());assert.deepEqual(canonical(numeric),raw);
const rpc=new sdk.RpcClient({url,encoding:sdk.Encoding.SerdeJson,networkId:'testnet-10'});await rpc.connect({blockAsyncConnect:true,timeoutDuration:3000});await rpc.submitTransaction({transaction:decoded,allowOrphan:false});await rpc.disconnect();numeric.free();decoded.free();tx.free();process.exit(0);
