#!/usr/bin/env python3
"""Same-host Docker A/B/C recovery rehearsal; no network or submission capability.

Container namespaces are logical failure domains, not independent machines.
Native C runs TestConsensus with synthetic genesis/skipped PoW. This does not
close live TN10, indexed archive compatibility or physical machine-loss G5.
"""
import argparse
import ast
import base64
import copy
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

import a1_check as c
import a1_recovery as r


IMAGE='sha256:7cac5961174b47c3528c0dc36303c11fff63d9db1f4673f33b7e4279c26bdf25'


def write_json(path,record):
    Path(path).write_bytes(c.canonical_json(record))


def read_receipt(path):
    """Benchmark receipts permit finite float timings; artifacts never do."""
    def unique(pairs):
        result={}
        for key,value in pairs:
            c.require(key not in result,'duplicate benchmark receipt key');result[key]=value
        return result
    record=json.loads(Path(path).read_text(),object_pairs_hook=unique)
    def check(value):
        if isinstance(value,float):c.require(math.isfinite(value),'nonfinite benchmark timing')
        elif isinstance(value,dict):
            for item in value.values():check(item)
        elif isinstance(value,list):
            for item in value:check(item)
    check(record);return record


def software_copy(repo,binary,reference,dest):
    dest.mkdir(mode=0o700)
    for path,name in ((binary,'kpi-poc-a1'),(reference,'a1_reference')):
        shutil.copy2(path,dest/name)
        (dest/name).chmod(0o755)
    for name in ('a1_check.py','a1_recovery.py','a1_recovery_rehearsal.py'):
        shutil.copy2(repo/'scripts'/name,dest/name)
    return {p.name:c.sha(p.read_bytes()) for p in dest.iterdir() if p.is_file()}


def immutable_public_copy(bundle,retained,dest):
    manifest=c.load_json(bundle/'manifest.json')
    dest.mkdir(mode=0o700)
    descriptors=[state['redeem'] for state in manifest['states'].values()]
    for branch in manifest['branches'].values():
        descriptors.extend(branch[field] for field in ('r1cs','pk','vk'))
    for descriptor in descriptors:
        data=c.artifact(bundle,descriptor,'format' in descriptor)
        name=descriptor['path']
        c.require(name not in ('claim-secret.bin','recipient-key.bin') and not name.endswith(('.proof','.transaction.json')),'private/precomputed proof in public allowlist')
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for name in ('manifest.json','disassembly.json','independent-checker-report.json'):
        shutil.copy2(bundle/name,dest/name)
    for name in ('owner-intent.json','setup-receipt.json'):
        shutil.copy2(retained/name,dest/name)
    # The source-to-row map and exact context exports contain no assignments.
    for branch in c.BRANCHES:
        for suffix in ('.context.hex','.layout.json'):
            source=bundle/(branch+suffix)
            if source.is_file():shutil.copy2(source,dest/source.name)
    inventory={'schema':'kpi-a1-recovery-inventory/v1','scope':'same-host-logical-container-rehearsal','files':[]}
    for path in sorted(dest.rglob('*')):
        if path.is_file():
            data=path.read_bytes();inventory['files'].append({'path':str(path.relative_to(dest)),'bytes':str(len(data)),'sha256':c.sha(data)})
    write_json(dest/'inventory.json',inventory)
    return manifest,c.sha((dest/'inventory.json').read_bytes())


def backup_copy(bundle,dest):
    dest.mkdir(mode=0o700)
    for name in ('claim-secret.bin','recipient-key.bin'):
        shutil.copy2(bundle/name,dest/name);(dest/name).chmod(0o600)


def verify_inventory(bundle,expected):
    c.require(c.sha((bundle/'inventory.json').read_bytes())==expected,'independently retained inventory hash mismatch')
    index=c.load_json(bundle/'inventory.json')
    c.keys(index,'schema scope files','recovery inventory')
    c.require(index['schema']=='kpi-a1-recovery-inventory/v1','recovery inventory schema')
    listed=set()
    for descriptor in index['files']:
        c.require(descriptor['path'] not in listed,'duplicate recovery artifact')
        listed.add(descriptor['path']);c.artifact(bundle,descriptor)
    actual={str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file()}-{'inventory.json'}
    c.require(actual==listed,'missing/extra public recovery artifact')
    return index


def rpc_body(body):
    tx=copy.deepcopy(body)
    tx['storageMass']=str(tx.pop('mass'))
    tx['verboseData']={'transactionId':tx.pop('id')}
    tx['verboseData']['hash']=r.full_hash(tx)
    return tx


def planned_s0_locator(manifest,inventory_hash,s0id,checkpoint):
    return {'network':'testnet-10','genesis_hex':manifest['genesis_hex'],'instance_hex':manifest['instance_hex'],'s0_txid_hex':s0id,'s0_index':'0','s0_amount':manifest['states']['s0']['R'],'s0_spk_hex':manifest['states']['s0']['spk_hex'],'s0_covenant':None,'scan_start_hash':checkpoint,'scan_start_blue_score':'0','scan_start_daa_score':'0','artifact_index_sha256':inventory_hash}


def check_prefunding_checkpoint(checkpoint,point,entry):
    c.require(checkpoint['schema']=='kpi-a1-native-checkpoint/v1' and checkpoint['native_seed_utxo_present'] is True and type(checkpoint['transactions_accepted']) is int and checkpoint['transactions_accepted']==0 and checkpoint['initial_outpoint']==point and checkpoint['initial_entry']==entry,'checkpoint was not captured before transaction acceptance with expected native initial UTXO')
    c.unhex(checkpoint['synthetic_genesis_hash'],32)


def archive_from_native(native,manifest,inventory_hash,dest):
    """Translate exact native stored accepted bodies to v2 Full-shaped fixtures.

    Native accepted_path comes from block storage and acceptance data. This
    conversion does not claim a live RPC integration; coinbase bodies outside
    the tested path are deliberately outside this fixture's discovery scope.
    """
    dest.mkdir(mode=0o700)
    accepted=native['accepted_path'];c.require(accepted,'empty native accepted path')
    funding=accepted[0]['transaction'];s0id=funding['id']
    checkpoint=native['synthetic_genesis_hash'];cursor=checkpoint
    pages=[];entries={}
    for record in accepted:
        tx=rpc_body(record['transaction'])
        point=tx['inputs'][0]['previousOutpoint'];entries[point['transactionId']+':'+str(point['index'])]=record['input_entry']
        accepting=record['accepting_block']
        pages.append({'startHash':cursor,'response':{'removedChainBlockHashes':[],'addedChainBlockHashes':[accepting],'chainBlockAcceptedTransactions':[{'chainBlockHeader':{'hash':accepting},'acceptedTransactions':[tx]}]}})
        cursor=accepting
    current=[];current_entries={}
    for point,entry in native['current_virtual_utxos']:
        key=point['transactionId']+':'+str(point['index']);current_entries[key]=entry
        current.append({'transaction_id':point['transactionId'],'index':str(point['index']),'value':str(entry['amount']),'spk_hex':entry['scriptPublicKey'],'covenant':entry['covenantId']})
    locator=planned_s0_locator(manifest,inventory_hash,s0id,checkpoint)
    write_json(dest/'locator.json',locator);write_json(dest/'pages.json',pages)
    write_json(dest/'entries.json',entries);write_json(dest/'current-utxos.json',current)
    write_json(dest/'current-entries.json',current_entries)
    write_json(dest/'source.json',{'schema':'kpi-a1-synthetic-archive/v1','scope':'native-TestConsensus-path-fixture-not-complete-live-RPC-history','horizon':cursor,'synthetic_genesis_hash':checkpoint,'native_backend':native['backend'],'native_network':native['network'],'live_tn10':False,'rpc_compatibility_demonstrated':False})
    write_json(dest/'native-acceptance.json',native)
    return locator,cursor


def reuse_initial_locator(archive,retained):
    """S1 recovery receives bytes retained during the earlier S0-only case."""
    early=retained.read_bytes();late=(archive/'locator.json').read_bytes()
    c.require(c.canonical_json(c.load_json(retained))==early,'noncanonical retained S0 locator')
    c.require(late==early,'late locator differs from independently retained initial S0 locator')
    (archive/'locator.json').write_bytes(early)
    return c.sha(early)


def qualify_old_locator(run):
    """Post-run content/provenance inspection, NOT an unexecuted runtime test.

    The older runner independently constructed per-case locators. Its initial
    S0-only archive was already retained before later S1 native acceptance.
    Qualify equal bytes plus reviewed sequential source, not filesystem times.
    """
    report=read_receipt(run/'report.json');source=run/'software/a1_recovery_rehearsal.py'
    source_bytes=source.read_bytes();source_hash=c.sha(source_bytes)
    c.require(source_hash==report['software_sha256']['a1_recovery_rehearsal.py'],'executed orchestration source pin mismatch')
    tree=ast.parse(source_bytes)
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='rehearse')
    loops=[node for node in ast.walk(function) if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple) and [getattr(x,'id',None) for x in node.target.elts]==['case','steps']]
    c.require(len(loops)==1 and isinstance(loops[0].iter,ast.Tuple),'unexpected orchestration case loop')
    loop=loops[0]
    labels=[node.elts[0].value for node in loop.iter.elts if isinstance(node,ast.Tuple) and isinstance(node.elts[0],ast.Constant)]
    c.require(labels==['orderly-s0','orderly-s1','abrupt-s1'],'S0 locator was not created before later S1 cases')
    calls=[]
    for statement in loop.body:
        for node in ast.walk(statement):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('run_c','archive_from_native','run_b'):
                calls.append(node.func.id)
    c.require(calls==['run_c','archive_from_native','run_b','run_c'],'unexpected acceptance/archive/recovery sequencing')
    early_path=run/'orderly-s0-archive/locator.json';early=early_path.read_bytes();locator=c.load_json(early_path)
    c.require(c.canonical_json(locator)==early,'noncanonical initial S0 locator')
    initial=c.load_json(run/'orderly-s0-archive/native-acceptance.json')
    c.require(len(initial['accepted_path'])==1,'initial archive already contains successor acceptance')
    funding=initial['accepted_path'][0]['transaction']
    c.require(funding['id']==locator['s0_txid_hex'] and locator['s0_index']=='0' and locator['scan_start_hash']==initial['synthetic_genesis_hash'],'initial funding/checkpoint locator mismatch')
    observations=[]
    for case in ('orderly-s1','abrupt-s1'):
        path=run/(case+'-archive')/'locator.json';data=path.read_bytes()
        c.require(data==early,'late locator differs from retained S0-only locator')
        native=c.load_json(run/(case+'-archive')/'native-acceptance.json')
        c.require(len(native['accepted_path'])==2 and native['accepted_path'][0]['transaction']==funding and native['synthetic_genesis_hash']==locator['scan_start_hash'],'later archive funding/checkpoint changed')
        point=native['accepted_path'][1]['transaction']['inputs'][0]['previousOutpoint']
        c.require(point['transactionId']==locator['s0_txid_hex'] and str(point['index'])==locator['s0_index'],'successor does not spend retained S0')
        observations.append({'case':case,'locator_sha256':c.sha(data),'native_acceptance_sha256':c.sha((run/(case+'-archive')/'native-acceptance.json').read_bytes()),'exact_initial_S0_locator_bytes':True})
    return {'schema':'kpi-a1-old-locator-qualification/v1','scope':'post-run inspection of same-host synthetic native fixture','initial_locator_sha256':c.sha(early),'initial_locator':locator,'initial_native_acceptance_sha256':c.sha((run/'orderly-s0-archive/native-acceptance.json').read_bytes()),'executed_orchestration_sha256':source_hash,'reviewed_case_order':labels,'reviewed_loop_source_lines':[loop.lineno,loop.end_lineno],'initial_retention_order_basis':'reviewed sequential pinned source: initial S0-only archive and B complete before later C accepts S1; not filesystem timestamps or hardware attestation','initial_checkpoint_scope':'C synthetic genesis, established before first funding acceptance; public initial locator retained after funding and before later S1 cases; not a live independent indexed-archive checkpoint','later_cases':observations,'late_locator_has_no_additional_successor_information':True,'runtime_explicit_retained_locator_reuse_executed':False,'post_run_byte_equivalence_verified':True,'B_reexecuted':False,'live_TN10':False,'physical_machine_loss':False,'G5_full_closure':False}


def inside(bundle,backup,archive,work):
    """B runs without an original bundle mount, network or a saved S1 pointer."""
    total_started=time.monotonic()
    locator=c.load_json(archive/'locator.json')
    verify_inventory(bundle,locator['artifact_index_sha256'])
    command=['python3','/software/a1_check.py',str(bundle),'--intent',str(bundle/'owner-intent.json'),'--receipt',str(bundle/'setup-receipt.json'),'--reference-binary','/software/a1_reference']
    p=subprocess.run(command,check=True,capture_output=True,text=True)
    checked=json.loads(p.stdout);c.require(checked['parameter_consistency'],'independent artifact check failed')
    subprocess.run(['/software/kpi-poc-a1','check-backup',str(bundle),str(backup/'claim-secret.bin'),str(backup/'recipient-key.bin')],check=True,capture_output=True,text=True)
    manifest=c.load_json(bundle/'manifest.json');source=c.load_json(archive/'source.json')
    scanner=r.Scanner(locator,manifest,r.native_callback('/software/kpi-poc-a1','/software/a1_reference',c.load_json(archive/'entries.json')),locator['artifact_index_sha256'])
    for page in c.load_json(archive/'pages.json'):scanner.page(page,source['horizon'])
    outcome=scanner.reconcile_utxos(c.load_json(archive/'current-utxos.json'),source['horizon'])
    c.require(outcome['lineage_history_complete'] and outcome['state'] in ('s0','s1'),'lineage discovery unavailable/terminal')
    point=outcome['current_outpoint'];key=point[0]+':'+str(point[1])
    actual=c.load_json(archive/'current-entries.json');c.require(key in actual,'current native UTXO context unavailable')
    request={'txid':point[0],'index':str(point[1]),'entry':actual[key]}
    write_json(work/'request.json',request)
    branch=outcome['state']+'_terminal'
    started=time.monotonic()
    p=subprocess.run(['/software/kpi-poc-a1','fresh-terminal',str(bundle),branch,str(backup/'claim-secret.bin'),str(work/'request.json'),str(work/'fresh-terminal.json')],check=True,capture_output=True,text=True)
    fresh=json.loads(p.stdout);elapsed=time.monotonic()-started
    total_elapsed=time.monotonic()-total_started
    c.require(fresh['fresh_proof'] and fresh['native_full'] and total_elapsed<=1800,'fresh terminal proof failed/30-minute total-recovery threshold exceeded')
    report={'scope':'same-host-Docker-recovery-rehearsal','artifact_check':checked['parameter_consistency'],'inventory_sha256':locator['artifact_index_sha256'],'discovery':outcome,'fresh_terminal':fresh,'wall_seconds':total_elapsed,'fresh_proof_wall_seconds':elapsed,'original_bundle_mounted':False,'saved_s1_pointer_supplied':False,'precomputed_exit_supplied':False,'network':'none','live_tn10':False,'physical_machine_loss_demonstrated':False}
    write_json(work/'recovery-report.json',report)
    print(json.dumps(report,indent=2))
    return report


def docker_run(image,name,software,mounts,command,expected=True):
    args=['docker','run','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}','--env','PYTHONDONTWRITEBYTECODE=1','--env','RAYON_NUM_THREADS=4','--tmpfs','/tmp:rw,exec,size=1073741824','--mount',f'type=bind,src={software},dst=/software,readonly']
    for source,dest,readonly in mounts:
        args+=['--mount',f'type=bind,src={source},dst={dest}'+(',readonly' if readonly else '')]
    args += [image]+command
    p=subprocess.run(args,capture_output=True,text=True)
    if expected and p.returncode:
        raise c.Invalid('isolated process failed: '+p.stderr[-3000:])
    return p


def remove_container(name):
    # Only exact unique names created by this run, never a broad Docker prune.
    subprocess.run(['docker','rm',name],check=True,capture_output=True,text=True)


def inventory_faults(public,expected,dest):
    """Each retained dependency fails closed when missing or changed.

    Mutate one dedicated disposable copy, never the retained public snapshot.
    This is an inventory-boundary test, not repeated native artifact parsing.
    """
    shutil.copytree(public,dest)
    records=[]
    index=verify_inventory(dest,expected)
    for descriptor in index['files']:
        path=dest/descriptor['path'];saved=path.read_bytes()
        for mutation in ('missing','corrupt'):
            try:
                if mutation=='missing':path.unlink()
                else:path.write_bytes((bytes([saved[0]^1])+saved[1:]) if saved else b'x')
                try:verify_inventory(dest,expected)
                except (c.Invalid,FileNotFoundError):pass
                else:raise c.Invalid('dependency fault unexpectedly accepted')
                records.append({'path':descriptor['path'],'mutation':mutation,'rejected':True,'enforcement':'independently retained inventory'})
            finally:path.write_bytes(saved)
    verify_inventory(dest,expected)
    return records


def export_public_evidence(run,bundle,dest):
    """Copy a narrow public receipt allowlist, checking the actual claim secret.

    No private backup, executable, proving/verifying key or R1CS is copied.
    The inventory retains their hashes, not their bytes. Proofs and native
    accepted transaction bodies are public fixture evidence, not live spends.
    """
    c.require(not dest.exists(),'new public evidence directory required')
    secret=(bundle/'claim-secret.bin').read_bytes()
    c.require(len(secret)==32,'claim backup size for publication scan')
    patterns=(secret,secret.hex().encode(),base64.b64encode(secret))
    sources=[(run/'report.json','report.json')]
    c.require(not any(pattern in (run/'report.json').read_bytes() for pattern in patterns),'private claim secret found in public evidence candidate')
    report=read_receipt(run/'report.json')
    if report.get('reused_negative_receipt'):
        previous=run/'previous-negative-report.json'
        c.require(c.sha(previous.read_bytes())==report['reused_negative_receipt']['report_sha256'],'reused negative receipt hash mismatch')
        sources.append((previous,'previous-negative-report.json'))
    for name in ('inventory.json','manifest.json','owner-intent.json','setup-receipt.json'):
        sources.append((run/'public'/name,'public-'+name))
    for name in ('retained-initial-s0-locator.json','pre-funding-checkpoint.json','timeline.json'):
        path=run/name
        if path.is_file():sources.append((path,name))
    for case in ('orderly-s0','orderly-s1','abrupt-s1'):
        for name in ('locator.json','pages.json','entries.json','current-utxos.json','current-entries.json','source.json','native-acceptance.json'):
            sources.append((run/(case+'-archive')/name,case+'/archive/'+name))
        for name in ('request.json','fresh-terminal.json','recovery-report.json'):
            sources.append((run/(case+'-work')/name,case+'/recovery/'+name))
        sources.append((run/(case+'-terminal-chain')/'native-result.json',case+'/terminal-native-acceptance.json'))
        replay=run/(case+'-terminal-chain')/'native-timing-replay.json'
        if replay.is_file():sources.append((replay,case+'/terminal-native-timing-replay.json'))
    checked=[]
    # Check all candidates before making any publication copy.
    for path,relative in sources:
        c.require(path.is_file() and not path.is_symlink(),'missing/nonregular public receipt')
        data=path.read_bytes()
        c.require(not any(pattern in data for pattern in patterns),'private claim secret found in public evidence candidate')
        checked.append((relative,data))
    dest.mkdir(mode=0o755)
    records=[]
    for relative,data in checked:
        path=dest/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        records.append({'path':relative,'bytes':str(len(data)),'sha256':c.sha(data)})
    scan={'schema':'kpi-a1-public-evidence-scan/v1','actual_claim_secret_encodings_checked':['raw32','hex','base64'],'private_claim_secret_found':False,'private_backup_or_artifact_binary_included':False,'scope':'public native-fixture receipts; no live TN10/G5 physical-machine claim','files':records}
    write_json(dest/'publication-scan.json',scan)
    return scan


def finalize_persisted_run(run,previous,replace=False):
    """Finish a receipt after a reporter-only failure, without claiming reruns.

    B reports/proofs are immutable completed v2 runs. C timings below are
    explicitly new acceptance replays of those same fresh transactions.
    """
    source_hash=c.sha(Path(__file__).read_bytes())
    if (run/'report.json').exists():
        c.require(replace,'already completed run')
        saved=run/'report-before-refinalization.json'
        c.require(not saved.exists(),'receipt already refinalized')
        shutil.copy2(run/'report.json',saved)
    software=run/'software';manifest=c.load_json(run/'public/manifest.json')
    hashes={p.name:c.sha(p.read_bytes()) for p in software.iterdir() if p.is_file()}
    inventory_hash=c.sha((run/'public/inventory.json').read_bytes())
    verify_inventory(run/'public',inventory_hash)
    prior=read_receipt(previous)
    c.require(prior['public_inventory_sha256']==inventory_hash and prior['image_sha256']==IMAGE,'unrelated prior suite')
    expected_cases={'missing-pk','corrupt-pk','wrong-secret','missing-history','pagination-gap','reordered-history','duplicate-page','poisoned-history'}
    c.require(len(prior['negative_cases'])==8 and {x['case'] for x in prior['negative_cases']}==expected_cases and all(x['rejected'] for x in prior['negative_cases']),'incomplete prior suite')
    for name in ('a1_check.py','a1_recovery.py','a1_reference'):
        c.require(prior['software_sha256'][name]==hashes[name],'prior checker changed')
    shutil.copy2(previous,run/'previous-negative-report.json')
    results=[];negatives=[]
    prefix='kpi-a1-finalize-'+uuid.uuid4().hex[:12]
    for case in ('orderly-s0','orderly-s1','abrupt-s1'):
        report=read_receipt(run/(case+'-work')/'recovery-report.json')
        c.require(report['artifact_check'] and report['discovery']['lineage_history_complete'] and report['fresh_terminal']['native_full'] and report['wall_seconds']<=1800,'incomplete B receipt')
        chain=run/(case+'-terminal-chain');fresh=c.load_json(run/(case+'-work')/'fresh-terminal.json')
        old=c.load_json(chain/'native-result.json')
        c.require(old['accepted_path'][-1]['transaction']['id']==fresh['id'],'persisted terminal not accepted')
        name=prefix+'-'+case+'-c';started=time.monotonic()
        try:
            p=docker_run(IMAGE,name,software,[(chain,'/chain',False)],['/software/kpi-poc-a1','native-path','/chain/request.json'])
            elapsed=time.monotonic()-started;accepted=json.loads(p.stdout)
        finally:remove_container(name)
        last=accepted['accepted_path'][-1]['transaction'];expected=manifest['branches'][report['discovery']['state']+'_terminal']['outputs'][0]
        c.require(last['id']==fresh['id'] and len(last['outputs'])==1 and r.rpc_uint(last['outputs'][0]['value'])==r.rpc_uint(expected['value']) and last['outputs'][0]['scriptPublicKey']==expected['spk_hex'] and last['outputs'][0]['covenant'] is None,'replayed terminal acceptance/payout mismatch')
        write_json(chain/'native-timing-replay.json',{'wall_seconds':elapsed,'scope':'new C native acceptance replay after reporter-only JSON float defect','native_result':accepted})
        results.append({'case':case,'recovery':report,'native_terminal_accepted':True,'payout_sompi':expected['value'],'archive_pages':1 if case=='orderly-s0' else 2,'no_original_mount_in_B_or_C':True,'terminal_C_acceptance_wall_seconds':elapsed,'C_timing_scope':'new acceptance replay; original acceptance receipt separately retained','original_A_removed_before_S1_pointer':case=='abrupt-s1'})
    faults=inventory_faults(run/'public',inventory_hash,run/('dependency-fault-refinalization-public' if replace else 'dependency-fault-finalization-public'))
    for label in ('missing-recipient-key','wrong-recipient-key'):
        name=prefix+'-'+label+'-b'
        try:p=docker_run(IMAGE,name,software,[(run/'public','/bundle',True),(run/(label+'-backup'),'/backup',True)],['/software/kpi-poc-a1','check-backup','/bundle','/backup/claim-secret.bin','/backup/recipient-key.bin'],False)
        finally:remove_container(name)
        c.require(p.returncode!=0,'backup negative accepted')
        negatives.append({'case':label,'rejected':True,'returncode':p.returncode,'rejecting_process':'clean-B-private-backup-check','error':p.stderr.splitlines()[-1] if p.stderr else ''})
    for record in prior['negative_cases']:
        record=copy.deepcopy(record);record['error']=record['error'].splitlines()[-1];record['receipt_origin']='previous-v1-run';negatives.append(record)
    c.require(c.sha(Path(__file__).read_bytes())==source_hash,'finalizer source changed during execution')
    summary={'schema':'kpi-a1-container-recovery-rehearsal/v1','scope':'same-physical-host-isolated-Docker-A-B-C','image_sha256':IMAGE,'software_sha256':hashes,'public_inventory_sha256':inventory_hash,'cases':results,'negative_cases':negatives,'dependency_fault_cases':faults,'reused_negative_receipt':{'report_sha256':c.sha(previous.read_bytes()),'software_sha256':prior['software_sha256'],'scope':'previous v1 Docker B run; not re-executed with v2 software'},'receipt_finalized_after_reporter_only_float_decoder_failure':True,'receipt_finalizer_sha256':source_hash,'terminal_spendability_A_locally_demonstrated':True,'native_fixture_lineage_B_locally_demonstrated':True,'live_RPC_archive_compatibility':False,'physical_machine_loss':False,'live_TN10':False,'G5_full_closure':False,'G6_authorized':False}
    write_json(run/'report.json',summary);return summary


def rehearse(repo,bundle,retained,binary,reference,output,image,reuse_negatives=None):
    c.require(not output.exists(),'new rehearsal output directory required')
    output.mkdir(mode=0o700)
    actual=subprocess.run(['docker','image','inspect',image,'--format','{{.Id}}'],check=True,capture_output=True,text=True).stdout.strip()
    c.require(actual==IMAGE,'unexpected recovery image digest')
    software=output/'software';software_hashes=software_copy(repo,binary,reference,software)
    public=output/'public';manifest,inventory_hash=immutable_public_copy(bundle,retained,public)
    private=output/'private-backup';backup_copy(bundle,private)
    funding=c.load_json(bundle/'synthetic-funding.validate.json')
    s0=c.load_json(bundle/'s0_continue.validate.json')
    prefix='kpi-a1-'+uuid.uuid4().hex[:12]
    results=[];containers=[];timeline=[];checkpoint=None
    def event(label,**fields):
        timeline.append({'ordinal':len(timeline),'event':label,**fields})
        write_json(output/'timeline.json',{'schema':'kpi-a1-recovery-topology-timeline/v1','scope':'executed same-host Docker program order; not a hardware timestamp attestation','events':timeline})
    def run_c(case,transactions):
        chain=output/(case+'-chain');chain.mkdir(mode=0o700)
        write_json(chain/'request.json',{'initial_entry':funding['entry'],'transactions':transactions})
        name=prefix+'-'+case+'-c';containers.append(name)
        started=time.monotonic()
        p=docker_run(image,name,software,[(chain,'/chain',False)],['/software/kpi-poc-a1','native-path','/chain/request.json'])
        elapsed=time.monotonic()-started
        native=json.loads(p.stdout);write_json(chain/'native-result.json',native)
        c.require(checkpoint is not None and native['synthetic_genesis_hash']==checkpoint['synthetic_genesis_hash'],'accepted native path checkpoint differs from retained pre-funding checkpoint')
        event('C-native-path-accepted',case=case,transactions=len(transactions),native_receipt_sha256=c.sha((chain/'native-result.json').read_bytes()))
        return native,chain,elapsed
    def run_b(case,archive,bundle_dir=public,backup_dir=private,expected=True):
        work=output/(case+'-work');work.mkdir(mode=0o700)
        name=prefix+'-'+case+'-b';containers.append(name)
        p=docker_run(image,name,software,[(bundle_dir,'/bundle',True),(backup_dir,'/backup',True),(archive,'/archive',True),(work,'/work',False)],['python3','/software/a1_recovery_rehearsal.py','inside','--bundle','/bundle','--backup','/backup','--archive','/archive','--work','/work'],expected)
        if expected:
            report=json.loads(p.stdout);write_json(work/'container-result.json',report)
            return report,work
        c.require(p.returncode!=0,'negative recovery unexpectedly succeeded')
        return {'case':case,'rejected':True,'returncode':p.returncode,'rejecting_process':'clean-B','error':p.stderr[-1200:]},work
    try:
        # C observes its actual initialized native genesis/UTXO before either
        # accepting funding or allowing A to generate the continuation proof.
        checkpoint_dir=output/'checkpoint-c';checkpoint_dir.mkdir(mode=0o700)
        initial_point=funding['transaction']['inputs'][0]['previousOutpoint']
        write_json(checkpoint_dir/'request.json',{'initial_outpoint':initial_point,'initial_entry':funding['entry']})
        checkpoint_name=prefix+'-pre-funding-checkpoint-c';containers.append(checkpoint_name)
        p=docker_run(image,checkpoint_name,software,[(checkpoint_dir,'/checkpoint',True)],['/software/kpi-poc-a1','native-checkpoint','/checkpoint/request.json'])
        checkpoint=json.loads(p.stdout)
        check_prefunding_checkpoint(checkpoint,initial_point,funding['entry'])
        write_json(output/'pre-funding-checkpoint.json',checkpoint)
        retained_locator=output/'retained-initial-s0-locator.json'
        write_json(retained_locator,planned_s0_locator(manifest,inventory_hash,funding['transaction']['id'],checkpoint['synthetic_genesis_hash']))
        event('pre-funding-C-checkpoint-and-planned-S0-locator-retained',checkpoint_sha256=c.sha((output/'pre-funding-checkpoint.json').read_bytes()),locator_sha256=c.sha(retained_locator.read_bytes()),accepted_transaction_count=0)
        # A creates a fresh continuation, and has no code or file receiving S1's
        # pointer/history. Its original input mount is absent from both B and C.
        original=output/'original-a';original.mkdir(mode=0o700)
        write_json(original/'request.json',{'txid':s0['transaction']['inputs'][0]['previousOutpoint']['transactionId'],'index':str(s0['transaction']['inputs'][0]['previousOutpoint']['index']),'entry':s0['entry']})
        a_name=prefix+'-original-a';containers.append(a_name)
        a=docker_run(image,a_name,software,[(bundle,'/original',True),(original,'/a',False)],['/software/kpi-poc-a1','fresh-continue','/original','/original/claim-secret.bin','/a/request.json','/a/continuation.json'])
        write_json(original/'created.json',json.loads(a.stdout))
        event('A-fresh-continuation-created-after-checkpoint')
        continuation=c.load_json(original/'continuation.json')
        for case,steps in (('orderly-s0',[funding['transaction']]),('orderly-s1',[funding['transaction'],continuation]),('abrupt-s1',[funding['transaction'],continuation])):
            native,chain,initial_acceptance_seconds=run_c(case,steps)
            if case=='abrupt-s1':
                remove_container(a_name);containers.remove(a_name)
                c.require(not (original/'s1-pointer.json').exists(),'original S1 pointer was recorded')
                event('original-A-removed-after-S1-acceptance-before-pointer',saved_S1_pointer=False)
            archive=output/(case+'-archive')
            archive_from_native(native,manifest,inventory_hash,archive)
            locator_hash=reuse_initial_locator(archive,retained_locator)
            event('B-archive-reuses-pre-funding-retained-S0-locator',case=case,locator_sha256=locator_hash)
            report,work=run_b(case,archive)
            fresh=c.load_json(work/'fresh-terminal.json')
            accepted,final_chain,terminal_acceptance_seconds=run_c(case+'-terminal',steps+[fresh])
            last=accepted['accepted_path'][-1]['transaction']
            c.require(last['id']==fresh['id'],'fresh terminal missing from native acceptance')
            expected=manifest['branches'][report['discovery']['state']+'_terminal']['outputs'][0]
            c.require(len(last['outputs'])==1 and r.rpc_uint(last['outputs'][0]['value'])==r.rpc_uint(expected['value']) and last['outputs'][0]['scriptPublicKey']==expected['spk_hex'] and last['outputs'][0]['covenant'] is None,'wrong accepted fresh terminal payout')
            results.append({'case':case,'recovery':report,'native_terminal_accepted':True,'payout_sompi':expected['value'],'archive_pages':len(steps),'no_original_mount_in_B_or_C':True,'initial_C_acceptance_wall_seconds':initial_acceptance_seconds,'terminal_C_acceptance_wall_seconds':terminal_acceptance_seconds,'original_A_removed_before_S1_pointer':case=='abrupt-s1','initial_S0_locator_sha256':locator_hash,'locator_source':'pre-funding C checkpoint and planned S0 transaction, retained before A continuation; exact old bytes copied after comparison, no accepted-S1-derived locator supplied'})
        base_archive=output/'abrupt-s1-archive'
        negatives=[]
        dependency_faults=inventory_faults(public,inventory_hash,output/'dependency-fault-public')
        # Backup ownership is a separate boundary from public artifact integrity.
        for label,mutation in (('missing-recipient-key','missing'),('wrong-recipient-key','wrong')):
            damaged=output/(label+'-backup');shutil.copytree(private,damaged)
            path=damaged/'recipient-key.bin'
            if mutation=='missing':path.unlink()
            else:path.write_bytes(bytes(32));path.chmod(0o600)
            name=prefix+'-'+label+'-b';containers.append(name)
            p=docker_run(image,name,software,[(public,'/bundle',True),(damaged,'/backup',True)],['/software/kpi-poc-a1','check-backup','/bundle','/backup/claim-secret.bin','/backup/recipient-key.bin'],False)
            c.require(p.returncode!=0,'recipient backup negative unexpectedly accepted')
            negatives.append({'case':label,'rejected':True,'returncode':p.returncode,'rejecting_process':'clean-B-private-backup-check','error':p.stderr.splitlines()[-1] if p.stderr else ''})
        reused=None
        if reuse_negatives:
            prior=read_receipt(reuse_negatives)
            expected_cases={'missing-pk','corrupt-pk','wrong-secret','missing-history','pagination-gap','reordered-history','duplicate-page','poisoned-history'}
            c.require(prior['schema']=='kpi-a1-container-recovery-rehearsal/v1' and prior['image_sha256']==actual and prior['public_inventory_sha256']==inventory_hash and len(prior['negative_cases'])==8 and {x['case'] for x in prior['negative_cases']}==expected_cases and all(x['rejected'] for x in prior['negative_cases']),'invalid/unrelated prior negative suite')
            for name in ('a1_check.py','a1_recovery.py','a1_reference'):
                c.require(prior['software_sha256'][name]==software_hashes[name],'prior negative checker/reference changed')
            shutil.copy2(reuse_negatives,output/'previous-negative-report.json')
            reused={'report_sha256':c.sha(reuse_negatives.read_bytes()),'software_sha256':prior['software_sha256'],'scope':'previous v1 Docker B run; not re-executed with v2 software'}
            for record in prior['negative_cases']:
                record=copy.deepcopy(record);record['error']=record['error'].splitlines()[-1];record['receipt_origin']='previous-v1-run';negatives.append(record)
        for label,mutation in (() if reuse_negatives else (('missing-pk','missing'),('corrupt-pk','corrupt'))):
            damaged=output/(label+'-public');shutil.copytree(public,damaged)
            path=damaged/manifest['branches']['s1_terminal']['pk']['path']
            if mutation=='missing':path.unlink()
            else:
                data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
            report,_=run_b(label,base_archive,bundle_dir=damaged,expected=False);negatives.append(report)
        if not reuse_negatives:
            damaged=output/'wrong-secret-backup';shutil.copytree(private,damaged)
            (damaged/'claim-secret.bin').write_bytes(bytes(32));(damaged/'claim-secret.bin').chmod(0o600)
            report,_=run_b('wrong-secret',base_archive,backup_dir=damaged,expected=False);negatives.append(report)
        for label,mutate in (() if reuse_negatives else (('missing-history',lambda pages:pages.clear()),('pagination-gap',lambda pages:pages.pop(0)),('reordered-history',lambda pages:pages.reverse()),('duplicate-page',lambda pages:pages.append(copy.deepcopy(pages[0]))),('poisoned-history',lambda pages:pages[-1]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][0]['outputs'][0].update(value='1')))):
            damaged=output/(label+'-archive');shutil.copytree(base_archive,damaged)
            pages=c.load_json(damaged/'pages.json');mutate(pages);write_json(damaged/'pages.json',pages)
            report,_=run_b(label,damaged,expected=False);negatives.append(report)
        summary={'schema':'kpi-a1-container-recovery-rehearsal/v1','scope':'same-physical-host-isolated-Docker-A-B-C','image_sha256':actual,'software_sha256':software_hashes,'public_inventory_sha256':inventory_hash,'cases':results,'negative_cases':negatives,'dependency_fault_cases':dependency_faults,'reused_negative_receipt':reused,'terminal_spendability_A_locally_demonstrated':True,'native_fixture_lineage_B_locally_demonstrated':True,'live_RPC_archive_compatibility':False,'physical_machine_loss':False,'live_TN10':False,'G5_full_closure':False,'G6_authorized':False}
        write_json(output/'report.json',summary)
        print(json.dumps(summary,indent=2));return summary
    finally:
        for name in containers:
            subprocess.run(['docker','rm',name],capture_output=True,text=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    outside=sub.add_parser('run')
    for name in ('repo','bundle','retained','binary','reference-binary','output'):outside.add_argument('--'+name,type=Path,required=True)
    outside.add_argument('--image',default=IMAGE)
    outside.add_argument('--reuse-negative-report',type=Path)
    child=sub.add_parser('inside')
    for name in ('bundle','backup','archive','work'):child.add_argument('--'+name,type=Path,required=True)
    export=sub.add_parser('export-public')
    for name in ('run','bundle','output'):export.add_argument('--'+name,type=Path,required=True)
    finalize=sub.add_parser('finalize-receipt')
    for name in ('run','previous-report'):finalize.add_argument('--'+name,type=Path,required=True)
    finalize.add_argument('--replace-receipt',action='store_true',help='retain existing receipt before explicitly refinalizing it')
    qualify=sub.add_parser('qualify-old-locator')
    for name in ('run','output'):qualify.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.action=='inside':inside(a.bundle,a.backup,a.archive,a.work)
    elif a.action=='export-public':print(json.dumps(export_public_evidence(a.run.resolve(),a.bundle.resolve(),a.output.resolve()),indent=2))
    elif a.action=='finalize-receipt':print(json.dumps(finalize_persisted_run(a.run.resolve(),a.previous_report.resolve(),a.replace_receipt),indent=2))
    elif a.action=='qualify-old-locator':
        c.require(not a.output.exists(),'new qualification receipt required')
        result=qualify_old_locator(a.run.resolve());write_json(a.output,result);print(json.dumps(result,indent=2))
    else:rehearse(a.repo.resolve(),a.bundle.resolve(),a.retained.resolve(),a.binary.resolve(),a.reference_binary.resolve(),a.output.resolve(),a.image,a.reuse_negative_report)


if __name__=='__main__':main()
