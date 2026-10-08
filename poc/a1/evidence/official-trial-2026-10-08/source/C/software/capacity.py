"""Finite infrastructure retention guard; no transaction/proof/authority changes."""
import json, os, pathlib, shutil, time

class Capacity:
    def __init__(self, config, clock=time.time, disk=shutil.disk_usage):
        self.config=config;self.path=pathlib.Path(config['database']);self.clock=clock;self.disk=disk
        self.limit=int(config['max_archive_bytes']);self.hard=int(config.get('hard_stop_bytes',self.limit))
        self.warn=int(config.get('high_water_bytes',self.hard*7//9))
        self.reserve=int(config.get('disk_free_guard_bytes',150*1024**3))
        self.wal_reserve=int(config.get('wal_reserve_bytes',8*1024**3))
        assert 0<self.warn<self.hard<=self.limit and self.reserve>0 and 0<self.wal_reserve<self.hard
        self.start=None;self.start_allocated=None;self.rate=float(config.get('design_rate_bytes_per_second',0))
        self.status_path=self.path.parent/'capacity-status.json'
    def bind(self, db):
        size=db.execute('PRAGMA page_size').fetchone()[0]
        pages=(self.hard-self.wal_reserve)//size
        current=db.execute('PRAGMA page_count').fetchone()[0]
        if current>=pages:raise ValueError('archive primary allocation already exceeds finite bound')
        if db.execute('PRAGMA max_page_count='+str(pages)).fetchone()[0]!=pages:raise ValueError('SQLite finite allocation bound rejected')
    def snapshot(self, db):
        at=self.clock();used=sum(p.stat().st_size for p in self.path.parent.glob(self.path.name+'*') if p.is_file())
        allocated=db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]
        if self.start is None:self.start=at;self.start_allocated=allocated
        measured=max(0,(allocated-self.start_allocated)/max(1,at-self.start))
        rate=max(self.rate,measured);free=self.disk(self.path.parent).free;remaining=max(0,self.hard-used)
        terminal=(self.path.parent/'CAPTURE-FAILED.json').exists()
        return {'at':at,'namespace':self.config['namespace'],'current_bytes':used,'allocated_primary_bytes':allocated,
                'limit_bytes':self.limit,'hard_stop_bytes':self.hard,'high_water_bytes':self.warn,
                'percent_of_limit':used*100/self.limit,'estimated_remaining_seconds':remaining/rate if rate>0 else None,
                'measured_primary_growth_bytes_per_second':measured,'conservative_rate_bytes_per_second':rate,
                'free_disk_bytes':free,'disk_free_guard_bytes':self.reserve,'warning':used>=self.warn,
                'capacity_ok':used<self.hard and free>=self.reserve and not terminal,'terminal_failure':terminal,
                'remaining_hard_stop_bytes':remaining,'required_horizon_seconds':self.config.get('required_horizon_seconds',10800),
                'prefunding_capacity_sufficient':used<self.warn and free>=self.reserve and rate>0 and remaining>=rate*self.config.get('required_horizon_seconds',10800) and not terminal,
                'history_discarded':False}
    def publish(self, db, error=None):
        value=self.snapshot(db)
        if error:value['error']=error
        tmp=self.status_path.with_suffix('.tmp');raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
        with tmp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,self.status_path);fd=os.open(self.path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
        return value
    def guard(self, db):
        value=self.publish(db)
        if not value['capacity_ok']:
            marker=self.path.parent/'CAPTURE-FAILED.json'
            if not marker.exists():
                with marker.open('xb') as f:f.write(json.dumps({'at':self.clock(),'reason':'finite archive capacity/disk gate failed','experiment_result':'FAIL if funded; funding forbidden','namespace':self.config['namespace']},sort_keys=True).encode());f.flush();os.fsync(f.fileno())
                fd=os.open(marker.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
            raise ValueError('terminal capture capacity failure; no cursor advance or history discard')
