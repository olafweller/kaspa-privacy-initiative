import sqlite3,json,zlib,hashlib
from live_schema_rehearsal import require
def read(request,run):
    action=request['action']
    db=sqlite3.connect('file:'+str(run/'history.sqlite')+'?mode=ro',uri=True)
    try:
        if action == 'status':
            require(set(request) == {'action'}, 'status request fields')
            metadata = {k:json.loads(v) for k,v in db.execute('select key,value from metadata')}
            return {'metadata':metadata, 'pages':db.execute('select count(*) from pages').fetchone()[0],
                    'bodies':db.execute('select count(*) from bodies').fetchone()[0]}
        if action == 'page':
            require(set(request) == {'action','seq'} and type(request['seq']) is int and 1<=request['seq']<2**63, 'page request')
            row = db.execute('select seq,start,cursor,horizon,response_sha,response,previous_digest,digest,request from pages where seq=?', (request['seq'],)).fetchone()
            require(row is not None, 'run-log retained page missing')
            seq,start,cursor,horizon,checksum,blob,previous,digest,raw_request = row
            raw = zlib.decompress(blob)
            require(hashlib.sha256(raw).hexdigest() == checksum, 'run-log page checksum')
            return {'seq':seq,'startHash':start,'cursor':cursor,'queried_horizon':horizon,
                    'response_sha256':checksum,'previous_digest':previous,'digest':digest,
                    'request':json.loads(raw_request) if raw_request else {'dataVerbosityLevel':'Full','minConfirmationCount':0},
                    'response':json.loads(raw)}
        if action == 'observations':
            require(set(request)=={'action','after','before'} and all(type(request[k]) is int and request[k]>=0 for k in ['after','before']) and 0<=request['before']-request['after']<=128,'observation request')
            rows=db.execute('SELECT page_seq,horizon,response_sha,response FROM utxo_observations WHERE page_seq>? AND page_seq<=? ORDER BY seq',(request['after'],request['before'])).fetchall()
            return {'observations':[{'page_seq':seq,'horizon':h,'sha256':check,'response':json.loads(zlib.decompress(blob))} for seq,h,check,blob in rows]}
        raise ValueError('run-log read operation forbidden')
    finally:
        db.close()
