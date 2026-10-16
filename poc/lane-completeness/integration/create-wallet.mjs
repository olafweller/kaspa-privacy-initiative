// Fresh test-fee wallet kept on the VPS, never in repository, logs or argv.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root='/opt/kpi-pr31-cloud-20261017';
const k=createRequire(import.meta.url)('/opt/kpi-cloud-https/sdk/kaspa.js');
const rpc=new k.RpcClient({url:'ws://127.0.0.1:17210',networkId:'testnet-10'});
await rpc.connect();
try{
  const server=await rpc.getServerInfo();assert.equal(server.networkId,'testnet-10');assert.equal(server.isSynced,true);
  fs.mkdirSync(root,{recursive:true,mode:0o700});
  if(fs.existsSync(root+'/test-wallet.key')){
    // Only read the public record when resuming; never replace an existing key.
    console.log(fs.readFileSync(root+'/test-wallet.public.json','utf8'));
  }else{
    const key=new k.PrivateKey(crypto.randomBytes(32).toString('hex'));
    fs.writeFileSync(root+'/test-wallet.key',key.toString()+'\n',{flag:'wx',mode:0o600});
    const publicRecord={network:'testnet-10',address:key.toAddress('testnet-10').toString()};
    fs.writeFileSync(root+'/test-wallet.public.json',JSON.stringify(publicRecord)+'\n',{flag:'wx',mode:0o600});
    console.log(JSON.stringify(publicRecord));
  }
}finally{await rpc.disconnect();}
