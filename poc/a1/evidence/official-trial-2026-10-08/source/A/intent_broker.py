"""Only durable A write capability: one current pre-submit immutable intent."""
import socket,pathlib,json,os
from launcher_common import BASE
from controller_access import query,load_binding,require

def binding():
 cfg,channel,_=load_binding(worker=True)
 return cfg,channel,intent_directory(cfg)

def intent_directory(cfg):return BASE/'private/intents'/cfg['run_id']

def commit(raw,cfg,directory):
 if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('bounded intent only')
 intent=json.loads(raw);require(intent['run_id']==cfg['run_id'] and intent['worker_source_sha256']==cfg['worker_source_sha256'],'wrong current intent binding')
 fields={'run_id','intended_txid','full_hash','body_sha256','safe_wire_sha256','compute_budget','native_masses','fee','exact_inputs_sha256','exact_outputs_sha256','manifest_sha256','inventory_sha256','scope','S0_locator_sha256','worker_source_sha256','attempt_nonce'};require(set(intent)==fields,'intent field mismatch')
 # C validates the complete existing whitelist/bindings. Claim the write-once
 # attempt before sending to C; any later failure remains a terminal stop.
 intent={k:v for k,v in intent.items() if k not in {'body_sha256','safe_wire_sha256','exact_inputs_sha256','exact_outputs_sha256'}}
 file=directory/'pre-submit-intent.json';data=json.dumps(intent,sort_keys=True,separators=(',',':')).encode();fd=os.open(file,os.O_EXCL|os.O_CREAT|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 d=os.open(directory,os.O_DIRECTORY)
 try:os.fsync(d)
 finally:os.close(d)
 receipt=query('intent',{'intent':intent});require(receipt['intent_committed'],'independent intent not committed')
 return {'intent_committed':True,'C_receipt_digest':receipt['intent_digest'],'live_authorized':receipt['live_authorized']}

def main():
 cfg,channel,directory=binding();directory.mkdir(parents=True,mode=0o700,exist_ok=True)
 sock=socket.socket(socket.AF_UNIX);sock.bind(channel['intent_socket']);os.chmod(channel['intent_socket'],0o600);sock.listen(2)
 while True:
  conn,_=sock.accept()
  try:response=commit(conn.makefile('rb').readline(8193),cfg,directory)
  except Exception:response={'error':'one-shot pre-submit intent rejected; stop, no retry'}
  conn.sendall(json.dumps(response).encode()+b'\n');conn.close()

if __name__=='__main__':main()
