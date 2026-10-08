"""Validate the existing qualified read-only RPC interface; never extend it."""
import time
REQUIRED = frozenset({'getServerInfo','getBlockDagInfo','getUtxosByAddresses'})
NATIVE_PEER = ('127.0.0.1',18210)

def require(ok, message):
    if not ok: raise ValueError(message)

def validate_rpc(rpc, *, required=REQUIRED, expected_peer=NATIVE_PEER):
    methods=getattr(rpc,'METHODS',None)
    require(isinstance(methods,(set,frozenset)) and required <= methods,'missing required RPC capability')
    require(callable(getattr(rpc,'call',None)) and callable(getattr(rpc,'close',None)),'missing required RPC interface')
    require(rpc.s.getpeername()==expected_peer,'wrong native RPC endpoint')
    info=rpc.call('getServerInfo',{})
    require(info['networkId']=='testnet-10','wrong RPC network')
    require(info['serverVersion']=='2.1.0' and info['isSynced'] is True and info['hasUtxoIndex'] is True,'unqualified RPC identity/sync/index')
    return info

def validate_submission_route(receipt, run_id, now=None):
    now=time.time() if now is None else now
    require(receipt.get('run_id')==run_id and receipt.get('passed') is True,'wrong or failed endpoint gate')
    require(receipt.get('endpoint')=='ws://127.0.0.1:29211','wrong funding endpoint')
    require(-2<=now-receipt['at']<=min(30,receipt['expiry_seconds']),'stale funding endpoint gate')
    p=receipt['SDK_probe']
    require(p.get('read_write_submission_route_verified') is True,'read-only endpoint: submit capability required')
    require(p.get('TCP_listener') is True and p.get('SDK_websocket_connected') is True and p.get('expected_C_identity_matched') is True,'incomplete endpoint gate')
    require(p.get('networkId')=='testnet-10' and p.get('serverVersion')=='2.1.0','wrong funding network/server')
    require(receipt.get('submit_RPC_invoked') is False and p.get('submit_RPC_invoked') is False and p.get('transaction_submitted') is False,'startup check must submit nothing')
    return True
