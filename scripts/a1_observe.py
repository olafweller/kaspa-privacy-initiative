#!/usr/bin/env python3
"""Same-host automated observation of an unfunded experimental setup run.

This records the clean pinned invocation and independently reconstructs the
three R1CS matrices afterwards. It is not a human review, multiparty ceremony,
independent machine, proof of toxic-waste deletion, or authorization to fund.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
import os

import a1_check as c


def command(args,cwd):
    p=subprocess.run(list(map(str,args)),cwd=cwd,check=True,capture_output=True,text=True)
    return p.stdout.strip()


def observe(repo,binary,reference_binary,output,retained,rustup,testnet_terms=None):
    repo=Path(repo).resolve();binary=Path(binary).resolve();reference_binary=Path(reference_binary).resolve()
    output=Path(output).resolve();retained=Path(retained).resolve()
    c.require(not output.exists() and not retained.exists(),'new external output/retained directories required')
    c.require(not output.is_relative_to(repo) and not retained.is_relative_to(repo),'observation and setup outputs must be outside repository')
    source=command(['git','rev-parse','HEAD'],repo)
    c.require(command(['git','status','--porcelain'],repo)=='','setup source must be clean and committed')
    toolchain=command([rustup,'run','1.91.0','rustc','--version'],repo)
    c.require(toolchain.startswith('rustc 1.91.0 '),'wrong compiler toolchain')
    binary_hash=c.sha(binary.read_bytes());reference_hash=c.sha(reference_binary.read_bytes())
    lock_hash=c.sha((repo/'poc/a1/Cargo.lock').read_bytes())
    retained.mkdir(mode=0o700)
    terms_bytes=None if testnet_terms is None else Path(testnet_terms).read_bytes()
    if terms_bytes is not None:
        (retained/'testnet-terms.json').write_bytes(terms_bytes)
    # Persist the pre-run event before launching; retention never depends on final export.
    # Fixture harness by default; the separate testnet constructor takes explicit terms.
    invocation=[str(binary),'experiment',str(output)] if testnet_terms is None else [str(binary),'testnet-10',str(output),str(Path(testnet_terms).resolve())]
    before={'schema':'kpi-a1-observer-event/v1','event':'before-setup','source_commit':source,'binary_sha256':binary_hash,'reference_binary_sha256':reference_hash,'cargo_lock_sha256':lock_hash,'compiler':toolchain,'invocation':invocation,'started_unix_seconds':str(int(time.time())),'scope':'same-host-automated-observation-no-human-ceremony'}|({} if terms_bytes is None else {'testnet_terms_sha256':c.sha(terms_bytes)})
    (retained/'before-setup.json').write_bytes(c.canonical_json(before))
    child_env=dict(os.environ);child_env['KPI_A1_RETAIN_INTENT']=str(retained/'owner-intent.json')
    p=subprocess.run(invocation,cwd=repo,env=child_env,check=False,stdout=subprocess.PIPE,stderr=None,text=True)
    (retained/'experiment-stdout.json').write_text(p.stdout)
    c.require(p.returncode==0,'experiment failed: no setup observation receipt')
    c.require(source==command(['git','rev-parse','HEAD'],repo) and command(['git','status','--porcelain'],repo)=='','source changed during observed run')
    c.require(binary_hash==c.sha(binary.read_bytes()) and reference_hash==c.sha(reference_binary.read_bytes()),'binary changed during observed setup')
    c.require(lock_hash==c.sha((repo/'poc/a1/Cargo.lock').read_bytes()),'lock changed during observed setup')
    manifest=c.load_json(output/'manifest.json');intent=c.load_json(output/'owner-intent.json')
    human=['A1 UNFUNDED LOCAL FIXTURE — DO NOT FUND (public recipient fixture key 1)' if testnet_terms is None else 'A1 TESTNET-10 INSTANCE — TEST KAS ONLY (fresh private recipient key)',
           'Single-party setup; same-host automated observation; not audited or production-safe.',
           'Protocol: '+manifest['protocol'], 'Network genesis: '+manifest['genesis_hex'],
           'Instance: '+manifest['instance_hex'],'Claim commitment: '+manifest['claim_commitment_hex'],
           'Recipient: '+manifest['recipient']['address'],'Full recipient SPK: '+manifest['recipient']['spk_hex'],
           'Public input order: '+', '.join(manifest['abi']['public_inputs']),
           'Witness: tag_hi(32), tag_lo(32), proof(128), raw selector(1), redeem(last)']
    for name,state in manifest['states'].items():
        human.append(f"{name}: stage={state['stage']} R={state['R']} L={state['L']} B={state['B']} sompi; full SPK={state['spk_hex']}")
    for name,b in manifest['branches'].items():
        human += [f"{name}: stage={b['stage']} context_mode={b['mode']} selector_witness={b['selector_hex']} fee={b['fee']} sompi",
                  '  Context SHA256: '+b['context_sha256'],'  Complete context bytes: '+b['context_hex']]
        for kind in ('r1cs','pk','vk'):
            human.append(f"  {kind}: {b[kind]['path']} bytes={b[kind]['bytes']} SHA256={b[kind]['sha256']}")
        human.append('  Ordered outputs (all covenant=None): '+json.dumps(b['outputs'],sort_keys=True))
    human.append('Exact source/toolchain pins: '+json.dumps(manifest['pins'],sort_keys=True))
    (output/'human-manifest.txt').write_text('\n'.join(human)+'\n')
    c.require(manifest['pins']['kpi_source_commit']==source and manifest['pins']['checker_source_commit']==source and manifest['pins']['cargo_lock_sha256']==lock_hash,'observed source/build pin mismatch')
    c.require(intent['pins']==manifest['pins'],'retained intent/build pin mismatch')
    if terms_bytes is None:
        c.require(intent['scope']=='local-unfunded-fixture','fixture scope')
    else:
        supplied=json.loads(terms_bytes)
        c.require(intent['scope']=='testnet-10-test-kas' and isinstance(supplied,dict) and set(supplied)==set(intent['terms']) and all(str(int(v))==intent['terms'][k] for k,v in supplied.items()),'testnet intent scope/terms differ from supplied terms')
        c.require(Path(testnet_terms).read_bytes()==terms_bytes,'terms file changed during observed setup')
    c.require((retained/'owner-intent.json').is_file() and c.load_json(retained/'owner-intent.json')==intent,'intent was not independently retained by pre-setup hook')
    # Source-reviewed hook writes this independent copy before its first setup.
    # Separately supplied human consent remains required before future funding.
    branches={};counts={};key_check=c.key_validator(reference_binary)
    with tempfile.TemporaryDirectory(prefix='kpi-a1-observed-reference-') as refs:
        c.independent_references(reference_binary,intent,manifest,refs)
        for name in c.BRANCHES:
            branch=manifest['branches'][name]
            matrices=c.artifact(output,branch['r1cs'],True)
            reference=(Path(refs)/(name+'.r1cs')).read_bytes()
            counts[name]=c.parse_r1cs(matrices);c.parse_r1cs(reference)
            c.require(matrices==reference,'independently reconstructed setup relation mismatch')
            pk=c.artifact(output,branch['pk']);vk=c.artifact(output,branch['vk'])
            c.require(key_check(pk,vk),'opaque key encoding/mapping invalid')
            branches[name]={'context_sha256':c.sha(c.unhex(branch['context_hex'])),'r1cs_sha256':c.sha(matrices),'pk_sha256':c.sha(pk),'vk_sha256':c.sha(vk)}
            (retained/(name+'.reference.r1cs')).write_bytes(reference)
    observation=before|{'event':'setup-and-reference-comparison-completed','finished_unix_seconds':str(int(time.time())),'branches':branches,'setup_provenance_limit':'observed circuit-specific setup invocation using reviewed source; no mathematical proof of CRS correctness or erasure; shared host and pinned Arkworks gadget','funding_authorized':False}
    observation_bytes=c.canonical_json(observation)
    (retained/'observation.json').write_bytes(observation_bytes)
    receipt={'schema':'kpi-a1-setup-observation/v1','scope':intent['scope'],'observer':'same-host automated observer; separately wired reference compiler; observation_sha256='+c.sha(observation_bytes),'build_pins':manifest['pins'],'branches':branches,'setup_randomness_retained':False}
    (retained/'setup-receipt.json').write_bytes(c.canonical_json(receipt))
    scripts={name:c.artifact(output,manifest['states'][name]['redeem']) for name in ('s0','s1')}
    disassembly=c.canonical_json({name:c.disassemble(data) for name,data in scripts.items()})
    checker_report=c.canonical_json(c.expected_report(counts,scripts))
    (output/'disassembly.json').write_bytes(disassembly)
    (output/'independent-checker-report.json').write_bytes(checker_report)
    manifest['inspection']['script_disassembly_sha256']=c.sha(disassembly)
    manifest['inspection']['checker_report_sha256']=c.sha(checker_report)
    manifest['inspection']['setup_observation_receipt_sha256']=c.sha(c.canonical_json(receipt))
    # This fixture has no live checkpoint. Record a plainly synthetic local
    # observation locator, never claim independent TN10 archival capability.
    if manifest['recovery']['retention_start_hash']=='unfunded-no-chain-checkpoint':
        manifest['recovery']['retention_start_hash']='01'*32
        manifest['recovery']['source_id']='synthetic-local-fixture-archive'
        manifest['recovery']['retention_policy']='synthetic offline pages only; independently operated live TN10 archive pending'
    (output/'manifest.json').write_bytes(c.canonical_json(manifest))
    # Recompile from independent intent during final checking, not self-generated
    # expected values. Inspection-file construction above is only preparation.
    with tempfile.TemporaryDirectory(prefix='kpi-a1-final-reference-') as refs:
        c.independent_references(reference_binary,intent,manifest,refs)
        checked=c.check_bundle(output,intent,refs,receipt,key_check)
    final_hash=c.sha((output/'manifest.json').read_bytes())
    (retained/'final-artifact-manifest.json').write_bytes(c.canonical_json({'manifest_sha256':final_hash,'checker_report_sha256':c.sha(checker_report),'scope':intent['scope'],'funding_authorized':False}))
    print(json.dumps({'observed':True,'parameter_consistency':checked['parameter_consistency'],'source_commit':source,'manifest_sha256':final_hash,'observation_sha256':c.sha(observation_bytes),'receipt_sha256':c.sha(c.canonical_json(receipt)),'scope':'same-host-unfunded-experiment','independent_machine':False,'human_review':False,'live_archive_qualified':False,'funding_authorized':False},indent=2))
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--reference-binary',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--retained',type=Path,required=True)
    p.add_argument('--rustup',default='/home/olaf/.cargo/bin/rustup')
    p.add_argument('--testnet-terms',type=Path,help='run the testnet-only constructor with these integer-sompi terms')
    a=p.parse_args();observe(a.repo,a.binary,a.reference_binary,a.output,a.retained,a.rustup,a.testnet_terms)


if __name__=='__main__':main()
