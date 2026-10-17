// Read-only recapture and resegmentation BEFORE proving/settling, no rebroadcast.
// Retains every original file; no guest or funded covenant identity changes.
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import * as JSON from './exact-json.mjs';
const base='/opt/kpi-pr31-cloud-20261017',root=base+'/native-value';
const [trial]=process.argv.slice(2);assert(trial?.startsWith(root+'/trial-')&&!trial.includes('..'));
const read=p=>JSON.parse(fs.readFileSync(trial+'/'+p));
const save=(p,v)=>fs.writeFileSync(trial+'/'+p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const meta=read('prepared.json');const pivot=read('unauthorized-accepted.json').header.hash;
const run=(bin,args)=>{const p=spawnSync(bin,args,{encoding:'utf8',maxBuffer:64*1024*1024});assert.equal(p.status,0,p.stderr);return p.stdout;};
assert(!fs.existsSync(trial+'/prefix-settlement-submission-intent.json'),'cannot resegment settled state');
for(const [label,start,end]of[['prefix2',meta.start,pivot],['final2',pivot,meta.end]]){
 const out=run('/opt/kpi-cloud-https/bin/node',[root+'/capture.mjs',trial+'/'+label+'-capture.json',meta.laneKey,'50',start,end]);
 save(label+'-capture-output.json',{stdout:out});
 const lane=run(base+'/kpi-tn10-integration-lift20-v2',['export',meta.lane,trial+'/'+label+'-capture.json',meta.covenantId]);fs.writeFileSync(trial+'/'+label+'-lane.json',lane,{flag:'wx'});
}
fs.mkdirSync(trial+'/original-segmentation',{mode:0o700});
for(const name of ['prefix-input.json','final-input.json','omission-input.json','prefix-output.json','prefix-state.json','final-output.json','prepared.json'])fs.renameSync(trial+'/'+name,trial+'/original-segmentation/'+name);
run(root+'/host-v1',['prepare',trial+'/prefix2-lane.json','empty',meta.covenantId,trial+'/prefix-input.json']);
const prefix=JSON.parse(run(root+'/host-v1',['execute',trial+'/prefix-input.json']));save('prefix-output.json',prefix);save('prefix-state.json',prefix.state);
run(root+'/host-v1',['prepare',trial+'/final2-lane.json',trial+'/prefix-state.json',meta.covenantId,trial+'/final-input.json']);
const final=JSON.parse(run(root+'/host-v1',['execute',trial+'/final-input.json']));save('final-output.json',final);
assert.deepEqual(prefix.events.map(e=>e.accepted),[true,false]);assert.deepEqual(final.events.map(e=>e.accepted),[true,false]);
const omission=read('final-input.json');let removed=0;
for(const b of omission.lane.blocks){b.txs=b.txs.filter(()=>removed++!==0);}
assert(removed===2);save('omission-input.json',omission);
save('prepared.json',{...meta,prefixEnd:pivot,resegmentedBeforeProving:true,originalSegmentation:'original-segmentation'});
save('recut-result.json',{reason:'Actual final profile had [20,17] segments; choose an allowed earlier checkpoint without changing guest/covenant or dropping any L1 command.',prefixEnd:pivot,allCommandsRetained:true});
console.log('READ_ONLY_RECUT_READY '+trial);
