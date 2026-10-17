// Read-only final monetary reconciliation. No signing or submission methods.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as JSON from './exact-json.mjs';
const base='/opt/kpi-pr31-cloud-20261017';
const [trial]=process.argv.slice(2);assert(trial?.startsWith(base+'/takeover/trial-')&&!trial.includes('..'));
const read=n=>JSON.parse(fs.readFileSync(trial+'/'+n));
const save=(n,v)=>fs.writeFileSync(trial+'/'+n,JSON.stringify(v,null,2)+'\n',{flag:'wx',mode:0o600});
const identity=read('identity.json'),done=read('complete.json'),sponsor=JSON.parse(fs.readFileSync(base+'/test-wallet.public.json'));
const ws=new WebSocket('ws://127.0.0.1:18210'),pending=new Map(),records=[];let id=0;
ws.onmessage=e=>{const raw=String(e.data),r=JSON.parse(raw),p=pending.get(r.id);if(!p)return;pending.delete(r.id);records.push({method:p.method,request:p.request,raw});r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.params);};
await new Promise((a,b)=>{ws.onopen=a;ws.onerror=b;});
const call=(method,request={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject,method,request});ws.send(JSON.stringify({id:n,method,params:request}));});
const sum=es=>es.reduce((n,e)=>n+BigInt(e.utxoEntry.amount),0n);
try{
 const server=await call('getServerInfo');assert.equal(server.networkId,'testnet-10');assert(server.isSynced);
 const balances={};for(const [role,address]of Object.entries({sponsor:sponsor.address,fee:identity.keys.fee.address,user:identity.keys.user.address}))balances[role]=await call('getUtxosByAddresses',{addresses:[address]});
 const fees=done.feesSompi,fee=n=>BigInt(fees[n]);
 const sponsorStart=sum(read('fund-fee-request.json').utxos.entries);
 assert.equal(sum(balances.sponsor.entries),sponsorStart-2500000000n-fee('fund-fee'));
 const feeWalletFees=['fund-user','seed','bootstrap','prefix-settlement','final-settlement','payout'].reduce((n,label)=>n+fee(label),0n);
 assert.equal(sum(balances.fee.entries),2500000000n-1200000000n-100000000n-50000000n-feeWalletFees);
 assert.equal(sum(balances.user.entries),1200000000n-1000000000n+450000000n-fee('deposit')-fee('withdraw'));
 const totalFees=Object.values(fees).reduce((n,v)=>n+BigInt(v),0n);
 assert.equal(sum(balances.fee.entries)+sum(balances.user.entries)+600000000n+100000000n,
              2500000000n-(totalFees-fee('fund-fee')));
 const canonical={};for(const label of Object.keys(fees)){
  const accepted=read(label+'-accepted.json');const {block}=await call('getBlock',{hash:accepted.header.hash,includeTransactions:false});assert(block.verboseData.isChainBlock);canonical[label]=block.header;
 }
 save('reconciliation.json',{scope:'FINAL_READ_ONLY_NATIVE_ACCOUNTING',server,balances,
  balancesSompi:Object.fromEntries(Object.entries(balances).map(([k,v])=>[k,sum(v.entries)])),
  sponsorStartSompi:sponsorStart,feesSompi:fees,totalFeesSompi:totalFees,canonical,
  feeAndUserPrincipalReconciled:true,stateRentSompi:100000000,reservedNativeSompi:600000000,
  appSpendableSompi:600000000,unpaidClaimsSompi:0});
 console.log('FINAL_ACCOUNTING_RECONCILED');
}finally{save('reconciliation-rpc-v2.json',records);ws.close();}
