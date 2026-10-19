import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as exactJSON from '../lane-completeness/integration/exact-json.mjs';
const source=fs.readFileSync(new URL('./capture.mjs',import.meta.url),'utf8');
const body=source.slice(source.indexOf('async function complete('),source.indexOf('await new Promise((resolve, reject)'));
const block=h=>({chainBlockHeader:{hash:h,nonce:18446744073709551615n},acceptedTransactions:[{verboseData:{transactionId:'tx-'+h}}]});
const page=hashes=>({removedChainBlockHashes:[],addedChainBlockHashes:hashes,chainBlockAcceptedTransactions:hashes.map(block)});
async function run(pages){const records=[],calls=[];const call=async(label,method,request)=>{calls.push(request.startHash);return pages.shift();};const complete=new Function('assert','exactJSON','records','call',body+';return complete;')(assert,exactJSON,records,call);return {result:await complete('accepted','a','d'),records,calls};}
const r=await run([page(['b','c']),page(['d','e'])]);
assert.deepEqual(r.calls,['a','c']);assert.deepEqual(r.result.addedChainBlockHashes,['b','c','d']);
assert.deepEqual(exactJSON.parse(r.records[0].raw).params,r.result);assert.equal(r.result.chainBlockAcceptedTransactions[2].chainBlockHeader.nonce,18446744073709551615n);
await assert.rejects(run([page(['b']),page(['b'])]),/duplicate/);
await assert.rejects(run([{...page(['b']),removedChainBlockHashes:['a']}]),/reorg/);
await assert.rejects(run([page([])]),/empty page/);
await assert.rejects(run([{...page(['b']),addedChainBlockHashes:['wrong']}]),/Expected values/);
console.log('Native pagination: full endpoint, exact u64, continuation, duplicate/reorg/empty/mismatched-page rejection: PASS');
