"""Capture SDK SerdeJson params only on non-forwarding loopback fixture."""
import hashlib,json,pathlib,subprocess,threading
from ws_fixture import Server,Handler
import a1_recovery as recovery
from terminal_sdk_gate import encode,sha,SDK_PINS

def capture(config,directory):
 directory=pathlib.Path(directory);receipt=json.loads((directory/'terminal-sdk-receipt.json').read_text());tx=json.loads((directory/'terminal-sdk-decoded.json').read_text())
 for name,key in [('terminal-sdk-safe.json','serialized_body_sha256'),('terminal-sdk-decoded.json','decoded_body_sha256'),('terminal-sdk-decoded-request.json','decoded_request_sha256')]:
  if sha((directory/name).read_bytes())!=receipt[key]:raise ValueError('terminal SDK file binding')
 node=pathlib.Path(config['terminal_wire_node']);script=pathlib.Path(__file__).with_suffix('.mjs');sdk=pathlib.Path(config.get('terminal_sdk_directory','/software/sdk'))
 if sha(node.read_bytes())!=config['terminal_wire_node_sha256']:raise ValueError('wire Node source pin')
 if sha(script.read_bytes())!=config['terminal_wire_sources_sha256']['terminal_wire.mjs']:raise ValueError('wire adapter source pin')
 for n in ['terminal_wire.py','ws_fixture.py']:
  if sha((script.parent/n).read_bytes())!=config['terminal_wire_sources_sha256'][n]:raise ValueError('wire helper pin')
 for n,pin in SDK_PINS.items():
  if sha((sdk/n).read_bytes())!=pin:raise ValueError('wire SDK pin')
 def callback(q):
  if q['method']=='getServerInfo':result={'rpcApiVersion':1,'rpcApiRevision':0,'serverVersion':'2.1.0','networkId':'testnet-10','hasUtxoIndex':True,'isSynced':True,'virtualDaaScore':'0'}
  else:
   if q['method']!='submitTransaction' or set(q['params'])!={'transaction','allowOrphan'} or q['params']['allowOrphan'] is not False:raise ValueError('fixture request')
   if recovery.canonical_body(q['params']['transaction'])!=recovery.canonical_body(tx) or recovery.full_hash(q['params']['transaction'])!=receipt['full_hash']:raise ValueError('SDK wire changed body')
   result={'transactionId':receipt['txid']}
  return {'id':q['id'],'method':q['method'],'params':result}
 server=Server(('127.0.0.1',0),Handler);server.callback=callback;server.requests=[]
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  child=subprocess.run([str(node),'--experimental-websocket',str(script),str(sdk),str(directory/'terminal-sdk-safe.json'),str(directory/'terminal-sdk-decoded.json'),'ws://127.0.0.1:'+str(server.server_address[1])],capture_output=True,timeout=180)
  if child.returncode:raise ValueError('SDK loopback serialization failed')
 finally:server.shutdown();server.server_close();thread.join(2)
 calls=[q for q in server.requests if q['method']=='submitTransaction']
 if len(calls)!=1:raise ValueError('exactly one NON-FORWARDING fixture call required')
 candidate={'decoded':tx,'request':json.loads((directory/'terminal-sdk-decoded-request.json').read_text()),'params':calls[0]['params'],'sdk_receipt_sha256':sha((directory/'terminal-sdk-receipt.json').read_bytes()),'g5_result_sha256':config['g5_result_sha256']}
 if len(encode({'action':'independent','op':'terminal-submit','run_id':config['run_id'],'candidate':candidate}))+1>16384:raise ValueError('terminal candidate exceeds unchanged gateway envelope')
 return candidate
