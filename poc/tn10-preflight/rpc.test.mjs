import assert from 'node:assert/strict';
import {request} from './rpc.mjs';
const original=globalThis.WebSocket;
const raw='{"id":1,"method":"getServerInfo","params":{"nativeU64":18446744073709551615}}';
let sockets=0;
class NativeProtocol extends EventTarget {
  constructor(url){super();sockets++;assert.equal(url,'ws://127.0.0.1:18210');queueMicrotask(()=>this.dispatchEvent(new Event('open')));}
  send(text){const call=JSON.parse(text);assert.equal(call.id,1);assert.equal(typeof call.id,'number');assert.equal(call.method,'getServerInfo');queueMicrotask(()=>this.dispatchEvent(new MessageEvent('message',{data:raw})));}
  close(){}
}
try {
  globalThis.WebSocket=NativeProtocol;
  assert.equal(await request('getServerInfo'),raw,'native u64 response must remain exact');
  await assert.rejects(request('submitTransaction'),/read-only/);
  await assert.rejects(request('getServerInfo',{},'ws://other:18210'),/local TN10/);
  assert.equal(sockets,1,'mutating/wrong endpoint request must fail before connection');
  console.log('Native numeric RPC ID, exact u64 response and read-only boundary: OK');
} finally {globalThis.WebSocket=original;}
