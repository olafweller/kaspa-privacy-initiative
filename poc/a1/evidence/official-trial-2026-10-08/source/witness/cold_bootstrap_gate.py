"""On-demand checks around the unchanged existing no-submit startup pipeline.

Only reads local files/imports; route validation never opens SSH. An actual
future explicit start receipt and freshly reviewed facts are required before
the pipeline may stage or acquire its prefix. No funding path is added.
"""
from pathlib import Path
import hashlib, importlib.util, json, sys, time

W=Path(__file__).resolve().parent
T=W.parent
P=T/'package-standby-cwd'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def require(v, m):
    if not v:raise ValueError(m)
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def validate():
    release=read(W/'ROOT-STANDBY-CWD-RELEASE.json');plan=read(P/'STAGE-PLAN.json')
    require(release['cold_gate_source_sha256']==sha(__file__) and release['plan_sha256']==sha(P/'STAGE-PLAN.json'),'exact future bootstrap gate/release')
    Q=next(p for p in W.parents if (p/'AGENTS.md').is_file())/'.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z'
    require(set(release['transport_source_pins'])=={'dedicated_remote.py','remote_safety.py','safe_diagnostics.py','platform_baseline.py'},'complete reviewed transport dependency source pins')
    for name,pin in release['transport_source_pins'].items():require(sha(Q/name)==pin,'actual startup transport dependency source pin')
    require(not plan['source_qualification_pending'] and not plan['coherent_envelope_pending'],'qualified final cold package required')
    receipt=W/'FUTURE-EXPLICIT-START.private.json'
    require(sha(receipt)==release['explicit_start_receipt_sha256'],'exact new explicit start receipt')
    start=read(receipt)
    smoke=(release.get('preparation_smoke_authorized') is True and plan.get('namespace_override') is not None and start.get('preparation_smoke_authorized') is True and start['explicit_user_start'] is False and start['scope']=='preparation-smoke-no-submit')
    production=(start['explicit_user_start'] is True and start['scope']=='cold-bootstrap-no-submit' and plan.get('namespace_override') is None)
    require((production or smoke) and start['base_instance_id']==plan['base_instance_id'] and start['planned_live_run_id']==plan['planned_live_run_id'] and start['standby_run_id']==plan['standby_run_id'],'new-run explicit start identity')
    require((production or smoke) and start['funding_authorized'] is start['terminal_execution_authorized'] is False,'bootstrap scope only')
    facts=W/'FRESH-START-FACTS.private.json';require(sha(facts)==release['fresh_start_facts_sha256'],'reviewed current facts')
    v=read(facts);require(v['passed'] is True and (production and v['explicit_start'] is True or smoke and v.get('preparation_smoke') is True and v['explicit_start'] is False) and v['base_instance_id']==plan['base_instance_id'],'fresh facts identity')
    require(0<=time.time()-v['observed_at']<=120,'facts must be freshly acquired at future start')
    require(sha(Path('/proc/sys/kernel/random/boot_id'))==v['A_boot_identity_sha256'],'current A boot identity')
    require(v['C_node_binding'] and v['C_node_binding']['rpc_port']==18210 and v['C_authorized_keys_preimage_sha256']==plan['C_authorized_keys_preimage_sha256'],'actual current C process/auth')
    require(v['never_funded_current_chain'] is True and v['storage_mount_UID_route_source_guards_passed'] is True,'current unused BASE/route/storage guards')
    for role in ['B','C']:
        root=P/role;require(sha(root/'package-pins.json')==plan['package_ledger_sha256'][role],'role package ledger')
        for n,h in read(root/'package-pins.json')['files'].items():require(sha(root/n)==h,'role package file')
        cfg=read(root/'config.template.json');require(cfg['A_boot_identity_sha256']==v['A_boot_identity_sha256'],'fresh config A identity')
        require(all(cfg.get(k) is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']),'unarmed bootstrap flags')
    require(not (T/'package/A/live-execution').exists(),'no E/live state before actual bootstrap PASS')
    return True

def route(binding, cfg):
    release=read(W/'ROOT-STANDBY-CWD-RELEASE.json')
    p=W/'cold_route_preflight.py';require(sha(p)==release['cold_route_source_sha256'],'exact route preflight source')
    guard=load('cold_actual_route_guard',p)
    helper=T/'package/A/controller_access.py'
    return guard.check(helper.parent,sha(helper),binding,cfg)

def route_before_prefix():
    # Fresh credentials exist now; derive exact provisional forced-command
    # digest from the actual pinned existing manifest builder. No authorization
    # line or service is installed until the final authenticated prefix binds.
    binding=read(W/'STANDBY-INSTALL-BINDING.private.json');cfg=read(P/'C/config.template.json');plan=read(P/'STAGE-PLAN.json')
    sys.path.insert(0,str(P/'C'))
    b=load('cold_actual_install_builder',P/'C/build_install_manifest.py')
    output=b.build('C',cfg,sha(P/'C/config.template.json'),plan['C_source_root'],plan['C_state_root'])
    binding.update(standby_run_id=cfg['run_id'],planned_live_run_id=plan['planned_live_run_id'],A_credential_root=str(T/'package/A/private'))
    binding['C'].update(config=cfg,config_sha256=sha(P/'C/config.template.json'),socket_root=output['manifest']['socket_root'])
    binding['A_controller_route'].update(run_id=cfg['run_id'],config_sha256=sha(P/'C/config.template.json'),forced_command_sha256=output['forced_command_sha256']['controller'])
    result=route(binding,cfg)
    with (W/'A-COLD-ROUTE-BEFORE-PREFIX.json').open('xb') as f:f.write(encode(result))
    return result

def route_after_bind():
    binding=read(W/'STANDBY-CWD-INSTALL-BINDING.private.json')
    return route(binding,binding['C']['config'])
