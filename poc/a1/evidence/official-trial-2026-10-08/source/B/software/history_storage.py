"""Scanner storage adapter. Replays and every native callback are unchanged."""
from collections.abc import MutableMapping
import json,sqlite3,tempfile
import a1_check as c
from history_chunks import canonical
class Groups(MutableMapping):
 def __init__(self,db,refs=None):self.db=db;self.refs={} if refs is None else refs
 def __getitem__(self,k):
  raw=self.db.execute('select data from records where id=?',(self.refs[k],)).fetchone()[0]
  # Records are internal canonical copies of inputs already parsed strictly.
  return json.loads(raw)
 def __setitem__(self,k,v):self.refs[k]=self.db.execute('insert into records(data) values(?)',(canonical(v),)).lastrowid
 def __delitem__(self,k):del self.refs[k]
 def __iter__(self):return iter(self.refs)
 def __len__(self):return len(self.refs)
 def copy(self):return Groups(self.db,self.refs.copy())
class Observations:
 def __init__(self,db):self.db=db;self.refs=[]
 def append(self,v):self.refs.append(self.db.execute('insert into records(data) values(?)',(canonical(v),)).lastrowid)
 def __len__(self):return len(self.refs)
 def __iter__(self):
  for ref in self.refs:yield json.loads(self.db.execute('select data from records where id=?',(ref,)).fetchone()[0])
class Storage:
 def __init__(self):
  self.temp=tempfile.TemporaryDirectory(prefix='kpi-history-storage-')
  self.db=sqlite3.connect(self.temp.name+'/scanner.sqlite',isolation_level=None)
  self.db.execute('pragma cache_size=-4096');self.db.execute('create table records(id integer primary key,data blob not null)')
  self.groups=Groups(self.db);self.observations=Observations(self.db)
 def close(self):self.db.close();self.temp.cleanup()
