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

import a1_check as c


def command(args,cwd):
    p=subprocess.run(list(map(str,args)),cwd=cwd,check=True,capture_output=True,text=True)
    return p.stdout.strip()


def observe(repo,binary,reference_binary,output,retained,rustup):
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
    # Persist the pre-run event before launching; retention never depends on final export.
    invocation=[str(binary),'experiment',str(output)]
    before={'schema':'kpi-a1-observer-event/v1','event':'before-setup','source_commit':source,'binary_sha256':binary_hash,'reference_binary_sha256':reference_hash,'cargo_lock_sha256':lock_hash,'compiler':toolchain,'invocation':invocation,'started_unix_seconds':str(int(time.time())),'scope':'same-host-automated-observation-no-human-ceremony'}
    (retained/'before-setup.json').write_bytes(c.canonical_json(before))
    p=subprocess.run(invocation,cwd=repo,check=False,stdout=subprocess.PIPE,stderr=None,text=True)
    (retained/'experiment-stdout.json').write_text(p.stdout)
    c.require(p.returncode==0,'experiment failed: no setup observation receipt')
    c.require(source==command(['git','rev-parse','HEAD'],repo) and command(['git','status','--porcelain'],repo)=='','source changed during observed run')
    c.require(binary_hash==c.sha(binary.read_bytes()) and reference_hash==c.sha(reference_binary.read_bytes()),'binary changed during observed setup')
    c.require(lock_hash==c.sha((repo/'poc/a1/Cargo.lock').read_bytes()),'lock changed during observed setup')
    manifest=c.load_json(output/'manifest.json');intent=c.load_json(output/'owner-intent.json')
    c.require(manifest['pins']['kpi_source_commit']==source and manifest['pins']['checker_source_commit']==source and manifest['pins']['cargo_lock_sha256']==lock_hash,'observed source/build pin mismatch')
    c.require(intent['pins']==manifest['pins'],'retained intent/build pin mismatch')
    (retained/'owner-intent.json').write_bytes(c.canonical_json(intent))
    # Production CLI writes this intent before its first setup. Observation source
    # review must confirm that ordering; separately supplied human consent is still
    # required before any future funding, not inferred from fixture intent.
    branches={};key_check=c.key_validator(reference_binary)
    with tempfile.TemporaryDirectory(prefix='kpi-a1-observed-reference-') as refs:
        c.independent_references(reference_binary,intent,manifest,refs)
        for name in c.BRANCHES:
            branch=manifest['branches'][name]
            matrices=c.artifact(output,branch['r1cs'],True)
            reference=(Path(refs)/(name+'.r1cs')).read_bytes()
            c.parse_r1cs(matrices);c.parse_r1cs(reference)
            c.require(matrices==reference,'independently reconstructed setup relation mismatch')
            pk=c.artifact(output,branch['pk']);vk=c.artifact(output,branch['vk'])
            c.require(key_check(pk,vk),'opaque key encoding/mapping invalid')
            branches[name]={'context_sha256':c.sha(c.unhex(branch['context_hex'])),'r1cs_sha256':c.sha(matrices),'pk_sha256':c.sha(pk),'vk_sha256':c.sha(vk)}
            (retained/(name+'.reference.r1cs')).write_bytes(reference)
    observation=before|{'event':'setup-and-reference-comparison-completed','finished_unix_seconds':str(int(time.time())),'branches':branches,'setup_provenance_limit':'observed circuit-specific setup invocation using reviewed source; no mathematical proof of CRS correctness or erasure; shared host and pinned Arkworks gadget','funding_authorized':False}
    observation_bytes=c.canonical_json(observation)
    (retained/'observation.json').write_bytes(observation_bytes)
    receipt={'schema':'kpi-a1-setup-observation/v1','scope':'local-unfunded-fixture','observer':'same-host automated observer; separately wired reference compiler; observation_sha256='+c.sha(observation_bytes),'build_pins':manifest['pins'],'branches':branches,'setup_randomness_retained':False}
    (retained/'setup-receipt.json').write_bytes(c.canonical_json(receipt))
    print(json.dumps({'observed':True,'source_commit':source,'observation_sha256':c.sha(observation_bytes),'receipt_sha256':c.sha(c.canonical_json(receipt)),'scope':'same-host-unfunded-experiment','independent_machine':False,'human_review':False,'funding_authorized':False},indent=2))
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--reference-binary',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--retained',type=Path,required=True)
    p.add_argument('--rustup',default='/home/olaf/.cargo/bin/rustup')
    a=p.parse_args();observe(a.repo,a.binary,a.reference_binary,a.output,a.retained,a.rustup)


if __name__=='__main__':main()
