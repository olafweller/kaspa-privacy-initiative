import json,sys,shlex,subprocess,hashlib,pathlib
from manage import upload,download,gateway,ROOT,REMOTE
ROOT=ROOT.resolve();TRIAL=pathlib.Path('.local/private-native-tn10/trial-20261019-preparation/trial.json').resolve();ROLE=TRIAL.parent
HOST=pathlib.Path('.local/ci-target/release/kpi-private-native-tn10').resolve()
VAL=pathlib.Path('.local/ci-target/release/kpi-tn10-integration').resolve();VSHA='a741467791c295e78647d5a1d7f012fddb0b484a11989e5177fa257d271d8837'
PROGRAM=pathlib.Path('poc/private-native/evidence/guest.program.bin').resolve()
T=json.loads(TRIAL.read_text());SPONSOR=T['sponsorNative']['address'];LANEKEY='e94e9720ed1aaca48f921aa5b15e4ebb02abc181a0149f57a2cf361e521ab86b'
def read(p):return json.loads(pathlib.Path(p).read_text())
def write(p,v):
 with pathlib.Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def host(*args):
 r=subprocess.run([str(HOST),*map(str,args)],capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stderr)
 return r.stdout

def query(label,addresses):
 command=shlex.join(['/opt/kpi-cloud-https/bin/node',REMOTE+'/chain-v4.mjs','query',label,json.dumps(addresses)])
 response=gateway(command);(ROOT/(label+'-query-response.json')).write_text(response)
 c=json.loads(response.strip());write(ROOT/(label+'-snapshot.json'),c);return c

def build(label,kind,fields,addresses=()):
 c=query(label,[SPONSOR,*addresses]);es=c['utxos']['entries'];sponsors=[e for e in es if e['address']==SPONSOR and e['utxoEntry']['covenantId'] is None];assert sponsors,'no sponsor'
 sponsor=max(sponsors,key=lambda e:e['utxoEntry']['amount'])
 r={'trial':T['trial'],'kind':kind,'server':c['server'],'sponsorUtxo':sponsor,'feeRateSompiPerGram':100,**fields}
 req=ROOT/(label+'-request.json');write(req,r);out=ROOT/(label+'-build')
 print(host('build',TRIAL,req,ROLE/'sponsor/native.key',out),end='')
 return out

def submit(label,out):
 r=read(out/'transaction.json');q=read(out/'request.json');es=[v for k,v in q.items() if k.endswith('Utxo')];em={(e['outpoint']['transactionId'],e['outpoint']['index']):e for e in es}
 entries=[em[(i['previousOutpoint']['transactionId'],i['previousOutpoint']['index'])] for i in r['transaction']['inputs']]
 p=ROOT/(label+'-submit.json');write(p,{'record':r,'entries':entries,'qualification':r['qualification']});remote=REMOTE+'/'+p.name
 upload(p,remote);resp=gateway(shlex.join(['/opt/kpi-cloud-https/bin/node',REMOTE+'/chain-v4.mjs','submit',label,remote]));(ROOT/(label+'-submit-response.json')).write_text(resp);print(resp.strip())
 download(REMOTE+'/'+label+'-accepted.json',ROOT/(label+'-accepted.json'));return read(ROOT/(label+'-accepted.json'))

def address(record,index):
 # Standard P2SH/P2PK address from PUBLIC script only, computed on gateway SDK.
 script=read(record)['transaction']['outputs'][index]['scriptPublicKey']
 code="const k=require('/opt/kpi-cloud-https/sdk/kaspa.js');const s="+json.dumps(script)+";console.log(k.addressFromScriptPublicKey(new k.ScriptPublicKey(parseInt(s.slice(0,4),16),s.slice(4)),'testnet').toString());"
 return gateway(shlex.join(['/opt/kpi-cloud-https/bin/node','-e',code])).strip()

def capture(label,start=None,end=None):
 remote=REMOTE+'/'+label+'-capture.json';args=['/opt/kpi-cloud-https/bin/node','--max-old-space-size=4096',REMOTE+'/capture-paginated.mjs',remote,LANEKEY,'50']
 if start:args.append(start)
 if end:args.append(end)
 response=gateway(shlex.join(args));(ROOT/(label+'-capture-response.json')).write_text(response);print(response.strip());p=ROOT/(label+'-capture.json');download(remote,p);return p

def anchor(label,blockhash):
 code="import {request} from '/opt/kpi-tn10-preflight-20261019/tn10-preflight/rpc.mjs';console.log(await request('getBlock',{hash:"+json.dumps(blockhash)+",includeTransactions:false}));"
 response=gateway(shlex.join(['/opt/kpi-cloud-https/bin/node','--input-type=module','-e',code]));write(ROOT/(label+'-anchor.json'),json.loads(response));return json.loads(response)['params']

def settlement(stage,previous,make_checkpoint=True):
 batch=ROOT/(stage+'-batch');t=read(batch/'target.json');b=ROOT/(previous+'-build/transaction.json');a=address(b,0);c=query(stage+'-settlement-state',[a]);point=t['stateOutpoint'];e=next(e for e in c['utxos']['entries'] if e['outpoint']==point)
 fields={'targetPath':str(batch/'target.json'),'targetSha256':hashlib.sha256((batch/'target.json').read_bytes()).hexdigest(),'receiptPath':str(ROOT/(stage+'-receipt.bin')),'stateUtxo':e,'anchorBlock':anchor(stage,t['endBlock']),'selectedParentBlock':c['sinkBlock']}
 out=build(stage+'-settlement','settlement',fields);accepted=submit(stage+'-settlement',out)
 if make_checkpoint:
  cap=capture(stage+'-settlement-acceptance',t['endBlock'],accepted['header']['hash']);print(host('checkpoint',VAL,VSHA,cap,out/'transaction.json',batch/'target.json',ROOT/(stage+'-checkpoint')))
 return accepted

def publish_wallet(role,stage,previous):
 cp=ROOT/(previous+'-checkpoint/checkpoint.json');wallet=ROOT/(role+'-wallet-public')
 names=['credit','invalid-transfer','transfer'] if role=='alice' else ['exit']
 for name in names:
  payload=read(wallet/(name+'-payload.json'))['operationPayloadHex'];out=build('publish-'+name,'publish',{'operationPayloadHex':payload});accepted=submit('publish-'+name,out)
 cap=capture(stage,read(cp)['nextCaptureStart'],accepted['header']['hash']);print(host('freeze',VAL,VSHA,PROGRAM,stage,cap,cp,ROOT/(stage+'-batch')))

def settle_and_exit():
 settlement('credit-transfer','deposit-settlement',False)
 payload=read(ROOT/'bob-wallet-public/exit-payload.json')['operationPayloadHex'];out=build('publish-exit','publish',{'operationPayloadHex':payload});accepted=submit('publish-exit',out)
 target=ROOT/'credit-transfer-batch/target.json';cap=capture('exit',read(target)['endBlock'],accepted['header']['hash'])
 cp=ROOT/'credit-transfer-checkpoint';print(host('checkpoint',VAL,VSHA,cap,ROOT/'credit-transfer-settlement-build/transaction.json',target,cp))
 print(host('freeze',VAL,VSHA,PROGRAM,'exit',cap,cp/'checkpoint.json',ROOT/'exit-batch'))

def submit_negative(label,envelope,action='negative'):
 p=ROOT/(label+'-submit.json');write(p,envelope);remote=REMOTE+'/'+p.name;upload(p,remote)
 response=gateway(shlex.join(['/opt/kpi-cloud-https/bin/node',REMOTE+'/chain-v4.mjs',action,label,remote]));(ROOT/(label+'-response.json')).write_text(response);print(response.strip());download(REMOTE+'/'+label+'-rejected.json',ROOT/(label+'-rejected.json'))

def payout_and_freeze():
 settlement('exit','credit-transfer-settlement',False)
 permission_record=ROOT/'exit-settlement-build/transaction.json';deposit_record=ROOT/'deposit-build/transaction.json'
 pa=address(permission_record,1);ra=address(deposit_record,0);c=query('payout-inputs',[pa,ra])
 pe=next(e for e in c['utxos']['entries'] if e['outpoint']=={'transactionId':read(permission_record)['transactionId'],'index':1})
 re=next(e for e in c['utxos']['entries'] if e['outpoint']=={'transactionId':read(deposit_record)['transactionId'],'index':0})
 fields={'publicStatePath':str(ROOT/'exit-batch/state.bin'),'exitId':read(ROOT/'bob-wallet-public/exit-payload.json')['operationId'],'permissionTransactionPath':str(permission_record),'permissionUtxo':pe,'reserveUtxo':re}
 out=build('payout','payout',fields);r=read(out/'transaction.json');q=read(out/'request.json');entries=[pe,re,q['sponsorUtxo']]
 positive={'record':r,'entries':entries,'qualification':r['qualification']};source=ROOT/'payout-positive-control.json';write(source,positive)
 binary=pathlib.Path('.local/ci-target/release/examples/payout-negative').resolve()
 for attack in ['underpay','reserve','recipient']:
  result=subprocess.run([str(binary),str(source),str(ROLE/'sponsor/native.key'),attack],capture_output=True,text=True);assert result.returncode==0,result.stderr
  env=json.loads(result.stdout);write(ROOT/('payout-'+attack+'-local.json'),env);submit_negative('payout-'+attack,env)
 accepted=submit('payout',out)
 replay=build('payout-replay','payout',fields);r2=read(replay/'transaction.json');q2=read(replay/'request.json');assert r2['transactionId']!=r['transactionId']
 submit_negative('payout-replay',{'record':r2,'entries':[pe,re,q2['sponsorUtxo']],'qualification':r2['qualification'],'originalPayoutId':r['transactionId']},'replay')
 target=ROOT/'exit-batch/target.json';cap=capture('reconcile',read(target)['endBlock'],accepted['header']['hash']);cp=ROOT/'exit-checkpoint'
 print(host('checkpoint',VAL,VSHA,cap,permission_record,target,cp));print(host('freeze',VAL,VSHA,PROGRAM,'reconcile',cap,cp/'checkpoint.json',ROOT/'reconcile-batch'))

if __name__=='__main__':
 action=sys.argv[1]
 if action=='activate':out=build('activate','activate',{});submit('activate',out)
 elif action=='seed':c=capture('seed');print(host('seed',VAL,VSHA,c,ROOT/'seed.json'))
 elif action=='bootstrap':
  seed=ROOT/'seed.json';out=build('bootstrap','bootstrap',{'seedPath':str(seed),'seedSha256':hashlib.sha256(seed.read_bytes()).hexdigest()});submit('bootstrap',out)
 elif action=='initialize':
  b=ROOT/'bootstrap-build/transaction.json';a=address(b,0);c=query('initialize-state',[a]);e=next(e for e in c['utxos']['entries'] if e['outpoint']['transactionId']==read(b)['transactionId'] and e['outpoint']['index']==0)
  out=build('initialize','initialize',{'bootstrapPath':str(b),'stateUtxo':e});accepted=submit('initialize',out)
  cap=capture('initialize-acceptance',read(ROOT/'seed.json')['endBlock'],accepted['header']['hash'])
  print(host('checkpoint',VAL,VSHA,cap,out/'transaction.json',b,ROOT/'initialize-checkpoint'))
 elif action=='deposit':
  b=ROOT/'initialize-build/transaction.json';a=address(b,0);c=query('deposit-state02',[a]);e=next(e for e in c['utxos']['entries'] if e['outpoint']['transactionId']==read(b)['transactionId'] and e['outpoint']['index']==0)
  cp=ROOT/'initialize-checkpoint/checkpoint.json';out=build('deposit','deposit',{'covenantId':read(b)['details']['covenantId'],'checkpointPath':str(cp),'stateUtxo':e});accepted=submit('deposit',out)
  cap=capture('deposit',read(cp)['nextCaptureStart'],accepted['header']['hash']);print(host('freeze',VAL,VSHA,PROGRAM,'deposit',cap,cp,ROOT/'deposit-batch'))
 elif action=='payout-and-freeze':payout_and_freeze()
 elif action=='settle-and-exit':settle_and_exit()
 elif action=='publish-wallet':publish_wallet(sys.argv[2],sys.argv[3],sys.argv[4])
 elif action=='settle':settlement(sys.argv[2],sys.argv[3])
 else:raise ValueError(action)
