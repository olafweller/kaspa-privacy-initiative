// Run on the existing TN10 gateway, through the existing management route.
// A separate, future release is required for broadcasting; this client cannot.
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

export const METHODS = new Set([
  'getServerInfo', 'getBlockDagInfo', 'getFeeEstimate', 'getBlock', 'getSink',
  'getUtxosByAddresses', 'getSeqCommitLaneProof', 'getVirtualChainFromBlockV2',
]);
export function validate(method, params, url) {
  if (!METHODS.has(method)) throw Error('read-only RPC method required');
  if (url !== 'ws://127.0.0.1:18210') throw Error('existing local TN10 RPC only');
  if (!params || typeof params !== 'object' || Array.isArray(params)) throw Error('RPC object required');
}
export async function request(method, params, url = 'ws://127.0.0.1:18210') {
  validate(method, params, url);
  return await new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    const timer = setTimeout(() => { socket.close(); reject(Error('read-only RPC timeout')); }, 30000);
    socket.addEventListener('open', () => socket.send(JSON.stringify({ id: 'kpi-read-only', method, params })));
    socket.addEventListener('error', () => { clearTimeout(timer); reject(Error('read-only RPC connection failed')); });
    socket.addEventListener('message', e => {
      // Preserve the raw JSON: native u64 fields must never pass through a JS
      // Number conversion. Downstream Rust/Python parse exact integers.
      const raw = String(e.data);
      if (!raw.includes('kpi-read-only')) return;
      clearTimeout(timer); socket.close(); resolve(raw);
    });
  });
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (process.argv.length !== 5) throw Error('METHOD PARAMS_JSON NEW_RESPONSE_FILE');
  const result = await request(process.argv[2], JSON.parse(fs.readFileSync(process.argv[3], 'utf8')));
  const fd = fs.openSync(process.argv[4], 'wx', 0o600);
  try { fs.writeFileSync(fd, result); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}
