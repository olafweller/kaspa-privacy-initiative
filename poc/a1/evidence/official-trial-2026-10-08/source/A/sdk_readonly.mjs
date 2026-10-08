// Read-only fee/continuation probes using the exact pinned SDK. No transaction API.
import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';import {createRequire} from 'node:module';
const q=JSON.parse(fs.readFileSync(process.argv[2]));
const sdk=createRequire(import.meta.url)(q.sdkDir);
assert.ok(['fees','continuation'].includes(q.action));
assert.equal(q.url,q.action==='fees'?'ws://127.0.0.1:29211':'ws://127.0.0.1:29210');
const rpc=new sdk.RpcClient({url:q.url,encoding:sdk.Encoding.SerdeJson,networkId:'testnet-10'});
let t;const bound=(p)=>{let x;return Promise.race([p,new Promise((_,r)=>{x=setTimeout(()=>r(new Error('read-only RPC deadline')),5000)})]).finally(()=>clearTimeout(x));};
t=setTimeout(()=>process.exit(2),20000);
try{
 for(const k of ['connect','getServerInfo','getBlockDagInfo',...(q.action==='fees'?['getInfo','getFeeEstimate']:[])])assert.equal(typeof rpc[k],'function','missing SDK capability '+k);
 await bound(rpc.connect({blockAsyncConnect:true,strategy:sdk.ConnectStrategy.Fallback,timeoutDuration:5000}));
 const server=await bound(rpc.getServerInfo());assert.equal(server.networkId,'testnet-10');assert.equal(server.serverVersion,'2.1.0');assert.equal(server.isSynced,true);assert.equal(server.hasUtxoIndex,true);
 const dag=await bound(rpc.getBlockDagInfo());let fees;
 if(q.action==='fees'){
  const info=await bound(rpc.getInfo());assert.equal(crypto.createHash('sha256').update(info.p2pId).digest('hex'),q.node_p2p_identity_sha256);
  fees=await bound(rpc.getFeeEstimate());
 }
 const last=await bound(rpc.getServerInfo());for(const k of ['networkId','serverVersion','rpcApiVersion','rpcApiRevision','isSynced','hasUtxoIndex'])assert.equal(last[k],server[k]);
 console.log(JSON.stringify({passed:true,server,dag,fees,submit_RPC_invoked:false,transaction_submitted:false,SDK_interface_capabilities_matched:true},(_,v)=>typeof v==='bigint'?v.toString():v));
 await bound(rpc.disconnect());clearTimeout(t);process.exit(0);
}catch(e){try{await bound(rpc.disconnect())}catch{}clearTimeout(t);console.log(JSON.stringify({passed:false,error:e.name,reason:e.message,submit_RPC_invoked:false}));process.exit(1)}
