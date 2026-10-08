"""Systemd hooks use this invocation's binding; never read the global config."""
import sys,os
from lifecycle_binding import load_config,record
if __name__=='__main__':
 phase=sys.argv[1]
 if phase not in ['start','stop']:raise ValueError('invalid lifecycle phase')
 try:cfg=load_config()
 except Exception as e:
  record(phase+'-binding-rejected',{'exception_type':type(e).__name__});raise
 if phase=='start':record('service-start',{'mode':cfg['mode'],'execution_authorized':cfg.get('execution_authorized') is True})
 else:
  record('finalizer-start',{'SERVICE_RESULT':os.environ.get('SERVICE_RESULT'),'EXIT_CODE':os.environ.get('EXIT_CODE'),'EXIT_STATUS':os.environ.get('EXIT_STATUS')})
  from durable_result import finalize_bound
  finalize_bound(cfg)
  record('finalizer-complete',{'mode':cfg['mode'],'execution_authorized':cfg.get('execution_authorized') is True})
