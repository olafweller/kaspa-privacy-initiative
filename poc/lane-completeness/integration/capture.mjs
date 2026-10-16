// Read-only native JSON wRPC capture. Run ON the VPS; no public RPC needed.
// Raw response strings preserve every u64 (notably nonce and input sequence).
import fs from 'node:fs';
import assert from 'node:assert/strict';

const [out, laneKey, depthText = '50', fixedStart, fixedEnd] = process.argv.slice(2);
assert(out && /^[0-9a-f]{64}$/.test(laneKey), 'capture.mjs NEW_OUTPUT LANE_KEY [DEPTH]');
assert(!fs.existsSync(out), 'refuse to overwrite a capture');
const depth = Number(depthText);
assert(Number.isSafeInteger(depth) && depth >= 20);
const socket = new WebSocket('ws://127.0.0.1:18210');
const records = [];
const pending = new Map();
let id = 0;
socket.onmessage = event => {
  const raw = String(event.data);
  const response = JSON.parse(raw);
  const p = pending.get(response.id);
  if (!p) return;
  pending.delete(response.id);
  clearTimeout(p.timer);
  records.push({label: p.label, method: p.method, request: p.request, raw});
  if (response.error) p.reject(new Error(JSON.stringify(response.error)));
  else p.resolve(response.params);
};
function call(label, method, request = {}) {
  return new Promise((resolve, reject) => {
    const n = ++id;
    const timer = setTimeout(() => {pending.delete(n); reject(new Error(`RPC timeout: ${label}`));}, 60000);
    pending.set(n, {resolve, reject, timer, label, method, request});
    socket.send(JSON.stringify({id: n, method, params: request}));
  });
}
await new Promise((resolve, reject) => {socket.onopen = resolve; socket.onerror = reject;});
let failure;
let intervalBlocks = 20;
try {
  const info = await call('server-before', 'getServerInfo');
  assert.equal(info.networkId, 'testnet-10');
  assert.equal(info.isSynced, true);
  await call('dag-before', 'getBlockDagInfo');
  const {sink} = await call('sink-before', 'getSink');
  let cursor = fixedStart ?? sink;
  let start;
  for (let n = 0; n < (fixedStart ? 1 : depth); n++) {
    const response = await call(`ancestor-${n}`, 'getBlock', {hash: cursor, includeTransactions: false});
    assert.equal(response.block.verboseData.isChainBlock, true);
    start = response.block;
    cursor = start.verboseData.selectedParentHash;
  }
  const vcc = await call('accepted', 'getVirtualChainFromBlockV2', {
    startHash: start.header.hash, dataVerbosityLevel: 'Full', minConfirmationCount: 10,
  });
  assert.equal(vcc.removedChainBlockHashes.length, 0, 'reorg: discard capture');
  assert(vcc.chainBlockAcceptedTransactions.length >= (fixedEnd ? 1 : 20), 'insufficient stable interval');
  // A bounded prefix keeps the retained experiment short despite a moving tip.
  if (fixedEnd) {
    const index = vcc.chainBlockAcceptedTransactions.findIndex(b => b.chainBlockHeader.hash === fixedEnd);
    assert(index >= 0, 'fixed endpoint not sufficiently confirmed');
    intervalBlocks = index + 1;
  }
  const blocks = vcc.chainBlockAcceptedTransactions.slice(0, intervalBlocks);
  const end = blocks.at(-1).chainBlockHeader;
  await call('start-block', 'getBlock', {hash: start.header.hash, includeTransactions: false});
  await call('start-proof', 'getSeqCommitLaneProof', {blockHash: start.header.hash, laneKey});
  await call('end-proof', 'getSeqCommitLaneProof', {blockHash: end.hash, laneKey});
  const endBlock = await call('end-block', 'getBlock', {hash: end.hash, includeTransactions: false});
  assert.equal(endBlock.block.verboseData.isChainBlock, true);
  const again = await call('accepted-recheck', 'getVirtualChainFromBlockV2', {
    startHash: start.header.hash, dataVerbosityLevel: 'Full', minConfirmationCount: 10,
  });
  assert.equal(again.removedChainBlockHashes.length, 0, 'reorg during capture');
  const ids = list => list.slice(0, blocks.length).map(b => [b.chainBlockHeader.hash,
    b.acceptedTransactions.map(t => t.verboseData.transactionId)]);
  assert.deepEqual(ids(again.chainBlockAcceptedTransactions), ids(blocks));
  const after = await call('server-after', 'getServerInfo');
  assert.equal(after.networkId, 'testnet-10');
  assert.equal(after.isSynced, true);
  const lanes = {};
  for (const b of blocks) for (const t of b.acceptedTransactions)
    lanes[t.subnetworkId] = (lanes[t.subnetworkId] ?? 0) + 1;
  console.log(JSON.stringify({scope: 'TN10_LOCAL_RPC_READ_ONLY', start: start.header.hash,
    end: end.hash, blocks: blocks.length, laneKey, lanes}));
} catch (error) {failure = error.message;}
finally {
  socket.close();
  fs.writeFileSync(out, JSON.stringify({kind: 'TN10_NATIVE_JSON_RPC_CAPTURE_V1',
    observedAt: new Date().toISOString(), endpoint: 'ws://127.0.0.1:18210',
    laneKey, intervalBlocks, failure: failure ?? null, records}, null, 2) + '\n', {flag: 'wx'});
}
if (failure) throw new Error(failure);
