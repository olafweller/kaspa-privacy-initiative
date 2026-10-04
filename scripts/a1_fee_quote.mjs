#!/usr/bin/env node
// Read-only public TN10 quotes: these are the ONLY RPC methods this script invokes.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const UPSTREAM = '01b532e8b553523216471682649693af92f0fd16';
const ARCHIVE_SHA256 = 'ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124';
const FILE_PINS = {
  'kaspa.js': '6d92cb305d0cc2eb26de9e305b7f7a8c17daa130ad478f0b340b50490557dbcf',
  'kaspa_bg.wasm': 'c9657568610ae1d305bc2e1cf85208ceba0d1a7893c4057b38caa8add2ffb0f5',
  'package.json': '8b61fefaba842c41b805291d95b2f9e81778ec590813a6c34eddcd316659b8d0',
};
const ENDPOINTS = [
  'wss://electron-10.kaspa.blue/kaspa/testnet-10/wrpc/borsh',
  'wss://vector-10.kaspa.green/kaspa/testnet-10/wrpc/borsh',
];
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const options = {
  '--sdk-dir': path.join(root, '.local/sdk/kaspa-wasm32-sdk/nodejs/kaspa'),
  '--sdk-archive': path.join(root, '.local/sdk/kaspa-wasm32-sdk-v2.1.0.zip'),
};
for (let i = 2; i < process.argv.length; i += 2) {
  const flag = process.argv[i];
  assert.ok(Object.hasOwn(options, flag) && process.argv[i + 1], 'usage: node scripts/a1_fee_quote.mjs [--sdk-dir DIR] [--sdk-archive ZIP]');
  options[flag] = path.resolve(process.argv[i + 1]);
}
const digest = filename => crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
assert.equal(digest(options['--sdk-archive']), ARCHIVE_SHA256, 'official SDK archive hash');
for (const [name, expected] of Object.entries(FILE_PINS)) {
  assert.equal(digest(path.join(options['--sdk-dir'], name)), expected, `extracted SDK hash: ${name}`);
}
const metadata = JSON.parse(fs.readFileSync(path.join(options['--sdk-dir'], 'package.json'), 'utf8'));
assert.equal(metadata.version, '2.1.0', 'SDK version');
const sdk = createRequire(import.meta.url)(path.join(options['--sdk-dir'], 'kaspa.js'));

async function bounded(promise) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('read-only RPC timeout (12 seconds)')), 12000);
    })]);
  } finally {
    clearTimeout(timer);
  }
}

const observations = [];
for (const endpoint of ENDPOINTS) {
  const rpc = new sdk.RpcClient({ url: endpoint, networkId: 'testnet-10' });
  try {
    await bounded(rpc.connect({ blockAsyncConnect: true, timeoutDuration: 12000 }));
    const info = await bounded(rpc.getInfo());
    const dag = await bounded(rpc.getBlockDagInfo());
    assert.equal(dag.network, 'testnet-10', 'external source network');
    assert.equal(info.isSynced, true, 'external source synced');
    assert.equal(info.serverVersion, '2.1.0', 'source version requires requalification if changed');
    const fees = await bounded(rpc.getFeeEstimate());
    const buckets = [fees.estimate.priorityBucket, ...fees.estimate.normalBuckets, ...fees.estimate.lowBuckets];
    assert.ok(buckets.length > 0 && buckets.every(bucket => Number.isFinite(bucket.feerate)
      && bucket.feerate > 0 && Number.isFinite(bucket.estimatedSeconds) && bucket.estimatedSeconds >= 0), 'finite positive fee buckets');
    observations.push({ endpoint, observed_at_utc: new Date().toISOString(), status: 'observed', info, dag, fees });
  } catch (error) {
    observations.push({ endpoint, observed_at_utc: new Date().toISOString(), status: 'failed', error: String(error) });
    process.exitCode = 1;
  } finally {
    await rpc.disconnect();
  }
}
const output = {
  schema: 'kpi-a1-fee-observation/v1',
  scope: 'Read-only external TN10 fee estimates; no submission, inclusion guarantee, node configuration attestation, or archive qualification.',
  network: 'testnet-10',
  pins: { rusty_kaspa_commit: UPSTREAM, sdk_version: metadata.version,
    sdk_archive_sha256: ARCHIVE_SHA256, extracted_files_sha256: FILE_PINS },
  rpc_methods: ['getInfo', 'getBlockDagInfo', 'getFeeEstimate'],
  source_default_relay_floor_sompi_per_gram: '100',
  headroom_rule: 'Use max(source default relay floor, chosen current quote); require fixed fee >= ceil(5 * rate * normalized_overall_mass_including_storage / 4), using exact rational arithmetic.',
  observations,
};
console.log(JSON.stringify(output, (_, value) => typeof value === 'bigint' ? value.toString() : value, 2));
