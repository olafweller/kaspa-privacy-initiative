// Only TCP and read-only SDK RPCs. No transaction constructors or submission API.
import net from 'node:net';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

export class EndpointFailure extends Error {
  constructor(code) { super(code); this.code = code; }
}
const need = (value, code) => { if (!value) throw new EndpointFailure(code); };
const bound = (promise, ms, code) => {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(new EndpointFailure(code)), ms);
  })]).finally(() => clearTimeout(timer));
};

export async function probeEndpoint({url, expectedUrl, witness, sdkDir, timeoutMs = 5000, now = Date.now()/1000}) {
  need(url === expectedUrl, 'wrong_port_or_endpoint');
  const target = new URL(url);
  need(target.protocol === 'ws:' && target.hostname === '127.0.0.1' && target.pathname === '/' && !target.username && !target.password && !target.search && !target.hash, 'wrong_port_or_endpoint');
  need(witness && now - witness.at >= -2 && now - witness.at <= 15, 'stale_endpoint');
  need(witness.native_JSON_RPC_listener_owned_by_node === true && witness.native_JSON_RPC_direct_unfiltered_route === true && witness.submit_RPC_invoked === false, 'unqualified_write_route');
  const tcp = new net.Socket();
  try {
    await bound(new Promise((resolve, reject) => {
      tcp.once('error', () => reject(new EndpointFailure('no_listener')));
      tcp.connect(Number(target.port), '127.0.0.1', resolve);
    }), timeoutMs, 'no_listener');
  } finally { tcp.destroy(); }
  const sdk = createRequire(import.meta.url)(sdkDir);
  const rpc = new sdk.RpcClient({url, encoding: sdk.Encoding.SerdeJson, networkId: 'testnet-10'});
  const expected = witness.server;
  try {
    await bound(rpc.connect({blockAsyncConnect:true, strategy:sdk.ConnectStrategy.Fallback, timeoutDuration:timeoutMs}), timeoutMs, 'connection_failed_or_dropped');
    const first = await bound(rpc.getServerInfo(), timeoutMs, 'connection_failed_or_dropped');
    need(first.networkId === 'testnet-10' && first.networkId === expected.networkId, 'wrong_network');
    need(first.serverVersion === '2.1.0' && first.serverVersion === expected.serverVersion && first.rpcApiVersion === expected.rpcApiVersion && first.rpcApiRevision === expected.rpcApiRevision, 'wrong_server_identity');
    need(first.isSynced === true && first.hasUtxoIndex === true, 'node_not_synced_or_indexed');
    const info = await bound(rpc.getInfo(), timeoutMs, 'connection_failed_or_dropped');
    need(info.p2pId === witness.info.p2pId && info.serverVersion === witness.info.serverVersion, 'stale_endpoint');
    // A second roundtrip catches disappearance after successful initial connection.
    const last = await bound(rpc.getServerInfo(), timeoutMs, 'connection_failed_or_dropped');
    need(last.networkId === first.networkId && last.serverVersion === first.serverVersion && last.rpcApiVersion === first.rpcApiVersion && last.rpcApiRevision === first.rpcApiRevision, 'stale_endpoint');
    need(last.isSynced === true && last.hasUtxoIndex === true, 'node_not_synced_or_indexed');
    return {passed:true, TCP_listener:true, SDK_websocket_connected:true, endpoint:url, networkId:first.networkId, serverVersion:first.serverVersion, rpcApiVersion:first.rpcApiVersion, rpcApiRevision:first.rpcApiRevision, expected_C_identity_matched:true, node_p2p_identity_sha256:crypto.createHash('sha256').update(info.p2pId).digest('hex'), read_write_submission_route_verified:true, write_capability_basis:'Exact historically used SSH TCP route terminates on the unchanged qualified native JSON RPC listener, owned by the pinned TN10 node; no method-filtering gateway is interposed.', transaction_submitted:false, submit_RPC_invoked:false, allowed_check_RPCs:['getServerInfo','getInfo'], admission_of_a_future_transaction_not_tested:true};
  } catch (e) {
    if (e instanceof EndpointFailure) throw e;
    const failure = new EndpointFailure('connection_failed_or_dropped');
    failure.cause = e; // Kept in memory; production CLI prints only the bounded code.
    throw failure;
  } finally {
    try { await bound(rpc.disconnect(), 1000, 'disconnect_timeout'); } catch {}
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  // This subprocess has a hard exit even if the SDK leaves reconnect handles alive.
  const hard = setTimeout(() => { console.log(JSON.stringify({passed:false, blocker:'hard_endpoint_check_timeout', transaction_submitted:false})); process.exit(2); }, 20000);
  try {
    const input = JSON.parse(fs.readFileSync(process.argv[2]));
    const result = await probeEndpoint(input);
    clearTimeout(hard); console.log(JSON.stringify(result)); process.exit(0);
  } catch (e) {
    clearTimeout(hard); console.log(JSON.stringify({passed:false, blocker:e.code ?? 'endpoint_check_failed', transaction_submitted:false, submit_RPC_invoked:false})); process.exit(1);
  }
}
