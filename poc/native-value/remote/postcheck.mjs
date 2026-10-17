// Read-only final state, balance and node checks, with exact original RPC strings.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as JSON from './exact-json.mjs';
const root='/opt/kpi-pr31-cloud-20261017';const [trial]=process.argv.slice(2);
assert(trial?.startsWith(root+'/native-value/trial-')&&!trial.includes('..'));
const read=name=>JSON.parse(fs.readFileSync(trial+'/'+name));
const final=read('final-settlement-transaction.json'),bootstrap=read('bootstrap-transaction.json');
const identity=read('identity.json'),sponsor=JSON.parse(fs.readFileSync(root+'/test-wallet.public.json'));
const ws=new WebSocket('ws://127.0.0.1:18210');const records=[];const pending=new Map();let id=0;
ws.onmessage=e=>{const raw=String(e.data),r=JSON.parse(raw),p=pending.get(r.id);if(!p)return;pending.delete(r.id);clearTimeout(p.timer);records.push({method:p.method,request:p.request,raw});r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.params);};
await new Promise((a,b)=>{ws.onopen=a;ws.onerror=b;});
const call=(method,request={})=>new Promise((resolve,reject)=>{const n=++id,timer=setTimeout(()=>reject(Error('read-only RPC timeout')),60000);pending.set(n,{resolve,reject,timer,method,request});ws.send(JSON.stringify({id:n,method,params:request}));});
const save=(name,v)=>fs.writeFileSync(trial+'/'+name,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
try{
 const server=await call('getServerInfo');assert.equal(server.networkId,'testnet-10');assert.equal(server.isSynced,true);
 const state=await call('getUtxosByAddresses',{addresses:[final.outputAddresses[0]]});
 const continuation=state.entries.find(e=>e.outpoint.transactionId===final.transactionId&&e.outpoint.index===0);assert(continuation);assert.equal(continuation.utxoEntry.amount,100000000);assert.equal(continuation.utxoEntry.covenantId,bootstrap.covenantId);
 const reserve=await call('getUtxosByAddresses',{addresses:[bootstrap.depositAddress]});assert.equal(reserve.entries.reduce((s,e)=>s+BigInt(e.utxoEntry.amount),0n),600000000n);
 const claims=await call('getUtxosByAddresses',{addresses:[final.outputAddresses[1]]});assert.equal(claims.entries.length,0);
 const balances={sponsor:await call('getUtxosByAddresses',{addresses:[sponsor.address]}),user:await call('getUtxosByAddresses',{addresses:[identity.userAddress]})};
 const canonical={};
 for(const label of ['prefix-settlement','final-settlement','payout']){
  const accepted=read(label+'-accepted.json');const {block}=await call('getBlock',{hash:accepted.header.hash,includeTransactions:false});assert.equal(block.verboseData.isChainBlock,true);canonical[label]=block.header;
 }
 const labels=['fund-user','seed','bootstrap','deposit','unauthorized','withdraw','replay','prefix-settlement','final-settlement','payout'];
 const fees=Object.fromEntries(labels.map(label=>[label,BigInt(read(label+'-transaction.json').feeSompi)]));
 const sum=values=>values.reduce((s,v)=>s+v,0n);
 save('postcheck.json',{server,continuation,reserve,claims,canonical,balances,
   balancesSompi:Object.fromEntries(Object.entries(balances).map(([k,r])=>[k,sum(r.entries.map(e=>BigInt(e.utxoEntry.amount)))])),
   feesSompi:fees,totalFeesSompi:sum(Object.values(fees)),
   userSpendableAppSompi:600000000,unpaidClaimsSompi:0,reservedNativeSompi:600000000,
   privacy:false,independentRecovery:false});
 console.log('FINAL_PUBLIC_STATE_AND_BACKING_CHECKED');
}finally{save('postcheck-rpc.json',records);ws.close();}
