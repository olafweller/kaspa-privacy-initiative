"""Bounded authenticated evidence; no consensus, accounting or native validation rules."""
import hashlib,json,os,re
from pathlib import Path
import a1_check as c
LIMIT=66*1024*1024
TARGET=65*1024*1024
SCHEMA='kpi-ordered-history-chunks/v1'

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def durable(path,data):
 with Path(path).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 Path(path).chmod(0o440)

def binding(checkpoint,run_id,commit):
 c.require(isinstance(run_id,str) and re.fullmatch('[a-zA-Z0-9-]{1,128}',run_id),'history run id')
 return {'run_id':run_id,'checkpoint_sha256':digest(canonical(checkpoint)),
         'checkpoint_seq':checkpoint['seq'],'checkpoint_cursor':checkpoint['cursor'],
         'checkpoint_digest':checkpoint['digest'],'commit_seq':commit['seq'],
         'commit_cursor':commit['cursor'],'commit_digest':commit['digest']}

class Writer:
 def __init__(self,directory,checkpoint,run_id,commit,target=TARGET):
  c.require(type(target) is int and 2<target<=TARGET,'unsafe chunk target')
  self.directory=Path(directory);self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
  self.bind=binding(checkpoint,run_id,commit);self.target=target
  self.rows=[];self.parts=[];self.size=2;self.chunks=[];self.pages=[];self.events=0;self.bodies=0
  self.original=hashlib.sha256();self.original.update(b'[');self.original_bytes=1
  self.cursor=checkpoint['cursor'];self.previous=checkpoint['digest'];self.seq=checkpoint['seq']+1
 def add(self,row):
  c.require(row['seq']==self.seq and row['startHash']==self.cursor and row['previous_digest']==self.previous,'page/cursor/hash-chain gap')
  response=row['response'];raw=canonical(response)
  c.require(digest(raw)==row['response_sha256'],'response checksum')
  want=digest(canonical({'start':row['startHash'],'cursor':row['cursor'],'horizon':row['queried_horizon'],'response_sha':row['response_sha256'],'previous_digest':row['previous_digest']}))
  c.require(row['digest']==want,'page digest')
  page={'startHash':row['startHash'],'response':response};token=canonical(page)
  c.require(len(token)+2<=self.target,'individual page exceeds bounded chunk target')
  if self.parts and self.size+1+len(token)>self.target:self.flush()
  if self.pages:self.original.update(b',');self.original_bytes+=1
  self.original.update(token);self.original_bytes+=len(token)
  count=sum(len(g['acceptedTransactions']) for g in response['chainBlockAcceptedTransactions'])
  events=len(response['addedChainBlockHashes'])+len(response['removedChainBlockHashes'])
  self.pages.append({k:row[k] for k in ['seq','startHash','cursor','queried_horizon','response_sha256','previous_digest','digest']})
  self.rows.append({'seq':row['seq'],'start':row['startHash'],'end':row['cursor'],'events':events,'bodies':count})
  self.parts.append(token);self.size+=len(token)+(1 if len(self.parts)>1 else 0)
  self.cursor=row['cursor'];self.previous=row['digest'];self.seq+=1
 def flush(self):
  if not self.parts:return
  index=len(self.chunks);name='page-'+str(index)+'.json';raw=b'['+b','.join(self.parts)+b']'
  c.require(len(raw)<=self.target<LIMIT,'chunk size limit')
  event_count=sum(r['events'] for r in self.rows);bodies=sum(r['bodies'] for r in self.rows)
  self.chunks.append({'index':index,'name':name,'bytes':len(raw),'sha256':digest(raw),
   'first_cursor':self.rows[0]['start'],'last_cursor':self.rows[-1]['end'],
   'first_page_seq':self.rows[0]['seq'],'last_page_seq':self.rows[-1]['seq'],
   'first_event':self.events,'last_event_exclusive':self.events+event_count,
   'page_count':len(self.rows),'accepted_body_count':bodies})
  durable(self.directory/name,raw);self.events+=event_count;self.bodies+=bodies
  self.parts=[];self.rows=[];self.size=2
 def finish(self):
  self.flush();self.original.update(b']');self.original_bytes+=1
  c.require(self.seq==self.bind['commit_seq']+1 and self.cursor==self.bind['commit_cursor'] and self.previous==self.bind['commit_digest'],'incomplete frozen history')
  manifest={'schema':SCHEMA,**self.bind,'chunk_target_bytes':TARGET,'per_file_limit_bytes':LIMIT,
   'page_count':len(self.pages),'event_count':self.events,'accepted_body_count':self.bodies,
   'semantic_pages_bytes':self.original_bytes,'semantic_pages_sha256':self.original.hexdigest(),
   'chunks':self.chunks,'pages':self.pages}
  raw=canonical(manifest);c.require(len(raw)<LIMIT,'manifest size limit');durable(self.directory/'history-manifest.json',raw)
  fd=os.open(self.directory,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
  return manifest,digest(raw)

def iter_pages(directory,checkpoint,run_id,commit,manifest_sha256,progress=None):
 directory=Path(directory);mp=directory/'history-manifest.json'
 c.require(not mp.is_symlink() and mp.stat().st_size<LIMIT,'unsafe manifest file')
 c.require(digest(mp.read_bytes())==manifest_sha256,'wrong manifest hash')
 m=c.load_json(mp)
 c.require(m['schema']==SCHEMA and all(m[k]==v for k,v in binding(checkpoint,run_id,commit).items()),'wrong run/checkpoint/commit manifest')
 c.require(m['per_file_limit_bytes']==LIMIT and m['chunk_target_bytes']==TARGET,'manifest limit changed')
 expected={'history-manifest.json'}|{x['name'] for x in m['chunks']}
 actual={p.name for p in directory.iterdir() if p.name.startswith('page') or p.name=='history-manifest.json'}
 c.require(actual==expected and len(m['chunks'])+1==len(expected),'missing/extra/duplicate chunk')
 cursor=checkpoint['cursor'];previous=checkpoint['digest'];seq=checkpoint['seq']+1;event=0;bodytotal=0;position=0;original=hashlib.sha256(b'[');original_bytes=1
 for index,record in enumerate(m['chunks']):
  name='page-'+str(index)+'.json'
  c.require(record['index']==index and record['name']==name,'reordered chunk')
  p=directory/name;c.require(not p.is_symlink() and p.is_file() and p.stat().st_size==record['bytes'] and 0<record['bytes']<=TARGET<LIMIT,'chunk byte bound/size')
  raw=p.read_bytes();c.require(digest(raw)==record['sha256'],'chunk hash mismatch')
  pages=c.load_json(p);c.require(isinstance(pages,list) and pages and canonical(pages)==raw,'noncanonical chunk')
  c.require(record['page_count']==len(pages) and record['first_page_seq']==seq and record['last_page_seq']==seq+len(pages)-1 and record['first_cursor']==cursor and record['first_event']==event,'chunk range overlap/gap')
  chunkbodies=0
  for page in pages:
   c.keys(page,'startHash response','chunk page')
   c.require(position<len(m['pages']),'extra page');meta=m['pages'][position]
   c.require(meta['seq']==seq and meta['startHash']==page['startHash']==cursor and meta['previous_digest']==previous,'cursor/page gap')
   response=page['response'];responsehash=digest(canonical(response));c.require(responsehash==meta['response_sha256'],'page response mismatch')
   want=digest(canonical({'start':cursor,'cursor':meta['cursor'],'horizon':meta['queried_horizon'],'response_sha':responsehash,'previous_digest':previous}))
   c.require(meta['digest']==want,'page hash-chain mismatch')
   token=canonical(page)
   if position:original.update(b',');original_bytes+=1
   original.update(token);original_bytes+=len(token)
   event+=len(response['addedChainBlockHashes'])+len(response['removedChainBlockHashes'])
   chunkbodies+=sum(len(g['acceptedTransactions']) for g in response['chainBlockAcceptedTransactions'])
   cursor=meta['cursor'];previous=meta['digest'];seq+=1;position+=1
   yield page
  bodytotal+=chunkbodies
  c.require(record['last_cursor']==cursor and record['last_event_exclusive']==event and record['accepted_body_count']==chunkbodies,'chunk event/body/cursor range')
  if progress:progress(position)
 original.update(b']');original_bytes+=1
 c.require(position==m['page_count']==len(m['pages']) and seq==commit['seq']+1 and cursor==commit['cursor'] and previous==commit['digest'],'incomplete history horizon')
 c.require(event==m['event_count'] and bodytotal==m['accepted_body_count'] and original_bytes==m['semantic_pages_bytes'] and original.hexdigest()==m['semantic_pages_sha256'],'semantic history mismatch')
