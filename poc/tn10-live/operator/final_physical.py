from live import *
r=ROOT/'reconcile-settlement-build/transaction.json';p=ROOT/'payout-build/transaction.json';permission=ROOT/'exit-settlement-build/transaction.json'
state_address=address(r,0);reserve_address=address(p,1);permission_address=address(permission,1)
c=query('final-physical',[T['bobNative']['address'],state_address,reserve_address,permission_address,SPONSOR]);es=c['utxos']['entries']
def point(tx,index):return {'transactionId':read(tx)['transactionId'],'index':index}
def find(pt):return next((e for e in es if e['outpoint']==pt),None)
bob=find(point(p,0));reserve=find(point(p,1));state=find(point(r,0));assert bob and reserve and state
assert bob['utxoEntry']['amount']==450_000_000 and bob['address']==T['bobNative']['address']
assert reserve['utxoEntry']['amount']==600_000_000 and reserve['address']==reserve_address
assert state['utxoEntry']['amount']==100_000_000 and state['utxoEntry']['covenantId']==read(ROOT/'bootstrap-build/transaction.json')['details']['covenantId']
assert find(point(permission,1)) is None and find(point(ROOT/'deposit-build/transaction.json',0)) is None
cp=read(ROOT/'reconcile-checkpoint/checkpoint.json');assert cp['stateOutpoint']==point(r,0)
a=cp['accounting'];assert a['reserve_principal']==a['private_liability']==600_000_000 and a['pending_deposits']==a['unpaid_exits']==a['outstanding_permission_rent_excluded']==0
fees={}
for accepted in ROOT.glob('*-accepted.json'):
 label=accepted.name.removesuffix('-accepted.json');record=ROOT/(label+'-build/transaction.json')
 if record.exists():fees[label]=read(record)['qualification']['feeSompi']
assert sum(fees.values())<=500_000_000
result={'scope':'ACTUAL_TN10_SELECTED_CHAIN_AND_UNSPENT_OUTPUT_OBSERVATION','bob':bob,'reserve':reserve,'stateCovenant':state,'permissionConsumed':True,'originalDepositReserveSpent':True,'finalAccounting':a,'finalCheckpointStateRoot':cp['stateRoot'],'actualAcceptedFeeSompiByTransaction':fees,'actualAcceptedTrialFeesSompi':sum(fees.values()),'sourceFundingFeeSompi':read(ROOT/'funding-transaction.json')['feeSompi'],'feePlanningSompi':500_000_000,'operatorControlsLogicalBob':True,'addresses':{'state':state_address,'reserve':reserve_address,'permission':permission_address,'bob':T['bobNative']['address'],'sponsor':SPONSOR}}
write(ROOT/'final-physical-result.json',result);print(json.dumps(result,indent=2))
