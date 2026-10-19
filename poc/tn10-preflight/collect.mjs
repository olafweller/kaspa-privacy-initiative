import fs from 'node:fs';
import {request} from './rpc.mjs';
const dir=process.argv[2];
async function call(name,method,params={}){const raw=await request(method,params);fs.writeFileSync(dir+'/'+name+'.json',raw,{flag:'wx',mode:0o600});const r=JSON.parse(raw);if(r.error)throw Error('read-only RPC error '+name);return r.params;}
await call('server','getServerInfo');await call('dag','getBlockDagInfo');await call('fees','getFeeEstimate');
const sink=await call('sink','getSink');await call('sink-block','getBlock',{hash:sink.sink,includeTransactions:false});
await call('lane','getSeqCommitLaneProof',{blockHash:sink.sink,laneKey:'e94e9720ed1aaca48f921aa5b15e4ebb02abc181a0149f57a2cf361e521ab86b'});
await call('funding','getUtxosByAddresses',{addresses:["kaspatest:qqchzl8lfw36ecqxwa869862dd6rf5d5ae8ctehzthwnr5y3swhvxyu4607hp", "kaspatest:qr0vtpqz65x4jp6m3gcp5y9l8xjzpudwn7swvamqtv8s9kxrclyfzemtwvwh4", "kaspatest:qqdqypkn5tvv3h0tfkaze387eehw44dwytrr35ndfyzelmaqtpe5vt8gapjhu"]});
console.log(JSON.stringify({readOnly:true,saved:fs.readdirSync(dir).filter(x=>x.endsWith('.json'))}));
