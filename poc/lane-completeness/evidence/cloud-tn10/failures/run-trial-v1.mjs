// One fresh TN10 trial: seed a lane, bootstrap, publish three KPI operations,
// capture exact accepted input. Proving/settlement are separate explicit stages.
// Run under systemd-run on the VPS to survive terminal or laptop disappearance.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';

const root = '/opt/kpi-pr31-cloud-20261017';
const binary = root + '/kpi-tn10-integration';
const program = root + '/guest.program.bin';
const wallet = JSON.parse(fs.readFileSync(root + '/test-wallet.public.json'));
assert.equal(wallet.network, 'testnet-10');
const trial = path.join(root, 'trial-' + new Date().toISOString().replaceAll(/[:.]/g, '-') + '-' + crypto.randomBytes(4).toString('hex'));
fs.mkdirSync(trial, {mode: 0o700});
const save = (name, value) => fs.writeFileSync(path.join(trial, name), JSON.stringify(value, null, 2) + '\n', {flag: 'wx', mode: 0o600});
const random = crypto.randomBytes(3); random[0] |= 1;
const lane = '4b' + random.toString('hex') + '00'.repeat(16);
function execute(args) {
  const r = spawnSync(binary, args, {encoding: 'utf8', maxBuffer: 32 * 1024 * 1024});
  if (r.status !== 0) throw Error('builder failed: ' + r.stderr);
  return r.stdout;
}
const laneKey = execute(['key', lane]).trim();
const identity = {trial, lane, laneKey, address: wallet.address, network: 'testnet-10'};
save('identity.json', identity);
console.log(JSON.stringify(identity));
const ws = new WebSocket('ws://127.0.0.1:18210');
let id = 0; const pending = new Map(); const records = [];
ws.onmessage = e => {
  const raw = String(e.data); const r = JSON.parse(raw); const p = pending.get(r.id);
  if (!p) return; pending.delete(r.id); clearTimeout(p.timer);
  records.push({method: p.method, request: p.request, raw});
  r.error ? p.reject(new Error(JSON.stringify(r.error))) : p.resolve(r.params);
};
await new Promise((resolve, reject) => {ws.onopen = resolve; ws.onerror = reject;});
const call = (method, request = {}) => new Promise((resolve, reject) => {
  const n = ++id; const timer = setTimeout(() => reject(Error('RPC timeout; inspect before retry: ' + method)), 60000);
  pending.set(n, {resolve, reject, timer, method, request});
  ws.send(JSON.stringify({id: n, method, params: request}));
});
async function server() {
  const result = await call('getServerInfo');
  assert.equal(result.networkId, 'testnet-10'); assert.equal(result.isSynced, true);
  return result;
}
async function prepare(label, fields) {
  const request = {...fields, server: await server(),
    utxos: await call('getUtxosByAddresses', {addresses: [wallet.address]}),
    feeEstimate: await call('getFeeEstimate')};
  save(label + '-request.json', request);
  execute(['build', lane, root + '/test-wallet.key', path.join(trial, label + '-request.json'), path.join(trial, label + '-transaction.json'), program]);
  return JSON.parse(fs.readFileSync(path.join(trial, label + '-transaction.json')));
}
async function waitAccepted(from, txid, confirmations = 3) {
  const deadline = Date.now() + 900000;
  while (Date.now() < deadline) {
    const result = await call('getVirtualChainFromBlockV2', {startHash: from, dataVerbosityLevel: 'Full', minConfirmationCount: confirmations});
    assert.equal(result.removedChainBlockHashes.length, 0, 'reorg: inspect and start a fresh trial');
    for (const b of result.chainBlockAcceptedTransactions)
      if (b.acceptedTransactions.some(t => t.verboseData.transactionId === txid)) return b.chainBlockHeader;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw Error('acceptance observation unresolved; inspect stored intent and node before retry');
}
async function submit(label, built) {
  await server();
  const before = (await call('getSink')).sink;
  save(label + '-submission-intent.json', {transactionId: built.transactionId, before, at: new Date().toISOString()});
  const result = await call('submitTransaction', {transaction: built.transaction, allowOrphan: false});
  assert.equal(result.transactionId, built.transactionId);
  save(label + '-mempool.json', result);
  const header = await waitAccepted(before, built.transactionId);
  save(label + '-accepted.json', header);
  console.log(JSON.stringify({stage: label, transactionId: built.transactionId, acceptingBlock: header.hash, feeSompi: built.feeSompi}));
  return header;
}
try {
  await server();
  const seed = await submit('seed', await prepare('seed', {kind: 'activity', number: 0}));
  const proof = await call('getSeqCommitLaneProof', {blockHash: seed.hash, laneKey});
  assert(proof.lane, 'seed must activate lane');
  save('start-proof.json', proof);
  const bootstrap = await prepare('bootstrap', {kind: 'bootstrap', tip: proof.lane.tip});
  await submit('bootstrap', bootstrap);
  let end;
  for (const number of [1, 2, 3]) {
    end = await submit('operation-' + number, await prepare('operation-' + number, {kind: 'activity', number}));
    assert(end.blueScore - proof.lane.blueScore <= 100, 'original guest interval exceeded; preserve this trial');
  }
  await waitAccepted(seed.hash, JSON.parse(fs.readFileSync(path.join(trial, 'operation-3-transaction.json'))).transactionId, 10);
  const capture = spawnSync('/opt/kpi-cloud-https/bin/node', [root + '/capture-v2.mjs', path.join(trial, 'capture.json'), laneKey, '50', seed.hash, end.hash], {encoding: 'utf8', maxBuffer: 32 * 1024 * 1024});
  save('capture-process.json', {status: capture.status, stdout: capture.stdout, stderr: capture.stderr});
  assert.equal(capture.status, 0);
  const input = execute(['export', lane, path.join(trial, 'capture.json'), bootstrap.covenantId]);
  fs.writeFileSync(path.join(trial, 'input.json'), input, {flag: 'wx'});
  save('prepared.json', {status: 'REAL_INPUT_CAPTURED_PROOF_AND_SETTLEMENT_PENDING', start: seed.hash, end: end.hash, covenantId: bootstrap.covenantId,
    bootstrapId: bootstrap.transactionId, lane, laneKey, trial});
  console.log('CAPTURE_PREPARED ' + trial);
} catch (error) {
  save('failure.json', {at: new Date().toISOString(), error: error.message});
  console.error(error.message); process.exitCode = 1;
} finally {save('rpc-records.json', records); ws.close();}
