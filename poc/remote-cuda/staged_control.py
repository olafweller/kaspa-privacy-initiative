"""Run on B using its existing service token, never a RunPod account key."""
import argparse
import json
import os
from pathlib import Path
import urllib.request
from common import NoRedirect,json_request,request,sha,lease_check
from staged_policy import check,unpack
from watchdog import save_archive


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','approve','submit','download'])
    p.add_argument('--lease',type=Path,required=True);p.add_argument('--package',type=Path,required=True)
    p.add_argument('--stage');p.add_argument('--target',type=Path);p.add_argument('--expected-target-sha');p.add_argument('--archive',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();lease=json.loads(a.lease.read_text());lease_check(lease);policy=check(a.package)
    assert lease['trial']==policy['trial'];token=os.environ['KPI_GPU_TOKEN'];url=lease['serviceUrl']
    if a.action=='status':result=json_request(url+'/v1/status',token)
    elif a.action=='approve':
        assert sha(a.target.read_bytes())==a.expected_target_sha
        t=json.loads(a.target.read_text());assert t['trial']==policy['trial'] and t['stage']==a.stage
        result=json_request(url+'/v1/targets',token,'POST',{'trial':policy['trial'],'stage':a.stage,'targetSha256':a.expected_target_sha})
    elif a.action=='submit':
        data=a.archive.read_bytes();unpack(data,a.expected_target_sha,policy,a.stage)
        req=urllib.request.Request(url+'/v1/stages/'+a.stage,data=data,method='POST',headers={
            'Authorization':'Bearer '+token,'User-Agent':'kpi-remote-cuda/1.0','Accept':'application/json',
            'Content-Type':'application/gzip','X-KPI-Target-Sha256':a.expected_target_sha,'X-KPI-Package-Sha256':sha(data)})
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as reply:result=json.loads(reply.read(65536))
    else:
        status=json_request(url+'/v1/status',token);data=request(url+'/v1/artifacts',token)
        assert sha(data)==status['artifact']['sha256'] and len(data)==status['artifact']['bytes'],'snapshot changed; poll status again'
        a.output.mkdir(parents=True,exist_ok=True);save_archive(a.output,data)
        result={'archiveSha256':sha(data),'bytes':len(data),'cpuVerified':False}
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
