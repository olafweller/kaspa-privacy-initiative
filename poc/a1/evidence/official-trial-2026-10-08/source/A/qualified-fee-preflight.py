"""Fresh read-only qualification. Never constructs/submits/funds a transaction."""
import pathlib,json,subprocess,hashlib,datetime,os,sys,decimal
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import remote
ROOT=pathlib.Path(__file__).resolve().parents[1];A1=pathlib.Path('@KPI_REPO@/.local/worktrees/a1-poc');SDK=pathlib.Path('@KPI_REPO@/.local/sdk');NATIVE=A1/'poc/a1/target/release/kpi-poc-a1';REF=A1/'poc/a1/target/release/a1_reference';PINS=json.loads((ROOT/'source-pins.json').read_text());meta=json.loads((pathlib.Path(__file__).resolve().parent/'live-candidate-run-location.private.json').read_text());run=pathlib.Path(meta['path']);package=json.loads((pathlib.Path(__file__).resolve().parent/'live-candidate-package-report.json').read_text())
def require(c,m):
 if not c:raise ValueError(m)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def execute(args,output):
 p=subprocess.run([str(x) for x in args],capture_output=True,timeout=180);require(p.returncode==0,'pinned read-only fee/SDK check failed (details retained privately)');output.write_bytes(p.stdout)
require(subprocess.check_output(['git','-C',str(A1),'rev-parse','HEAD'],text=True).strip()==PINS['pr22_head'],'source changed');require(sha(run/'bundle/manifest.json')==package['manifest_sha256'],'frozen manifest changed');require(sha(NATIVE)=='3884409aa1a59a24be7979a54ce591727cf5fa81a81527497a72f0ae5d0203e0','native validator changed')
for name,info in PINS['source_files'].items():require(sha(A1/name)==info['sha256'],'pinned source/toolchain changed')
baseline=json.loads((ROOT/'final-qualification/C-policy-baseline.json').read_text())
code=r'''import pathlib,subprocess,json,hashlib,time,sys
sys.path.insert(0,'/opt/kpi-g5-capture');from rpc_local import RPC
p=int(subprocess.check_output(['systemctl','show','kpi-tn10.service','--property=MainPID','--value'],text=True));args=pathlib.Path(f'/proc/{p}/cmdline').read_bytes().split(b'\0');keys={x.split(b'=',1)[0].decode(errors='replace') for x in pathlib.Path(f'/proc/{p}/environ').read_bytes().split(b'\0') if b'=' in x}
policy={'observed_at_unix':time.time(),'node_binary_sha256':hashlib.sha256(pathlib.Path(f'/proc/{p}/exe').read_bytes()).hexdigest(),'external_config_present':any(x==b'-C' or x==b'--configfile' or x.startswith(b'--configfile=') for x in args) or 'KASPAD_CONFIGFILE' in keys,'fee_or_mass_override_flags':[x.decode().split('=')[0] for x in args if x.startswith((b'--minrelay',b'--mempool',b'--maxstandard',b'--mass'))],'fee_or_mass_override_env_present':any('FEE' in k or 'MASS' in k or 'MEMPOOL' in k for k in keys),'scope':'relay/mass rules source-derived for unchanged binary with no config overrides; RPC does not attest policy','secret_values_printed':False}
r=RPC();r.METHODS=set(r.METHODS)|{'getFeeEstimate'};policy['server']=r.call('getServerInfo',{});policy['dag']=r.call('getBlockDagInfo',{});policy['fees']=r.call('getFeeEstimate',{});r.close();print(json.dumps(policy))
'''
policy=json.loads(remote.run('@C_SSH_HOST@',code,90));require(policy['node_binary_sha256']==baseline['node_binary_sha256'],'target binary changed; requalify');require(not policy['external_config_present'] and not policy['fee_or_mass_override_flags'] and not policy['fee_or_mass_override_env_present'],'unqualified policy overrides');info=policy['server'];require(info['serverVersion']=='2.1.0' and info['networkId']=='testnet-10' and info['isSynced'],'target node unqualified')
dest=run/'fee-preflights'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');dest.mkdir(mode=0o700,parents=True)
execute(['node',A1/'scripts/a1_serialization.mjs','--bundle',run/'bundle','--sdk-dir',SDK/'kaspa-wasm32-sdk/nodejs/kaspa','--sdk-archive',SDK/'kaspa-wasm32-sdk-v2.1.0.zip','--validator',NATIVE,'--reference',REF],dest/'sdk.json')
execute(['node',A1/'scripts/a1_fee_quote.mjs','--sdk-dir',SDK/'kaspa-wasm32-sdk/nodejs/kaspa','--sdk-archive',SDK/'kaspa-wasm32-sdk-v2.1.0.zip'],dest/'external-quotes.json')
quotes=json.loads((dest/'external-quotes.json').read_text(),parse_float=decimal.Decimal);quotes['observations'].append({'endpoint':'C-localhost-restricted-administrative-read','observed_at_utc':datetime.datetime.fromtimestamp(policy['observed_at_unix'],datetime.timezone.utc).isoformat(),'status':'observed','info':{'serverVersion':info['serverVersion'],'isSynced':info['isSynced']},'dag':policy['dag'],'fees':policy['fees']})
# Preserve exact fee decimals: serialize the parsed original as JSON numeric
# literals, rather than changing them into strings or binary floating point.
def encode(x):
 if isinstance(x,decimal.Decimal):require(x.is_finite(),'nonfinite fee quote');return str(x)
 if isinstance(x,dict):return '{'+','.join(json.dumps(k)+':'+encode(v) for k,v in x.items())+'}'
 if isinstance(x,list):return '['+','.join(encode(v) for v in x)+']'
 return json.dumps(x)
(dest/'quotes.json').write_text(encode(quotes));(dest/'C-policy.json').write_text(json.dumps(policy,indent=2))
execute(['python3',A1/'scripts/a1_fee_check.py',run/'bundle/manifest.json',run/'bundle/report.json',dest/'sdk.json',dest/'quotes.json',dest/'qualification.json','--bundle',run/'bundle','--validator',NATIVE],dest/'stdout.json')
r=json.loads((dest/'qualification.json').read_text());require(r['funding_authorized'] is False and not r['historical_quote_replay'] and r['original_terms_unchanged'],'fee gate invalid');result={'run_id':meta['run_id'],'passed':True,'funding_authorized':False,'fresh_before_any_future_funding_required':True,'expiry_seconds':300,'fixed_terms_not_changed':True,'branch_headroom_percent':25,'refundable_credit_headroom_percent':10,'native_full_revalidated':True,'policy_scope':policy['scope'],'negative_cases':[x['case'] for x in r['executed_negative_cases']],'receipt_path':str(dest/'qualification.json'),'receipt_sha256':sha(dest/'qualification.json'),'C_policy_sha256':sha(dest/'C-policy.json')};(pathlib.Path(__file__).resolve().parent/'fresh-fee-mechanism-report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
