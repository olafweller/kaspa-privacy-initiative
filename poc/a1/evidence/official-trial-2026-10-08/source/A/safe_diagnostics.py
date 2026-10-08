"""Closed diagnostic schema: no exception text, private pointers or hashes."""
import json
ROLES={'A','B','C'}
STAGES={'prefunding','final','handoff','remote','child','collector','transport','launcher'}
CODES={'RETIRED_OR_UNKNOWN_ROLE','BINDING_MODE','BINDING_PROFILE','CONFIG_BINDING','SOURCE_PINS','NATIVE_PINS','SDK_PINS','NODE_PIN','PLATFORM_DRIFT','BASELINE_BINDING','UNIT_RUNNING','UNIT_ENABLED','UNIT_RESTART','NODE_IDENTITY','NODE_OOM','B_CMDLINE','CAPTURE_BINDING','CAPTURE_READY','CAPTURE_CAPACITY','CAPTURE_LIFETIME','WATCH_LIMIT','NODE_SERVER','LEASE_ROUTE','EVENT_PHASE','ARM_PHASE','ARTIFACT_BINDING','RECOVERY_OUTPUT','TARGET_ELIGIBILITY','ACCEPTANCE_NATIVE','SANDBOX','HANDOFF_BINDING','HANDOFF_STALE','HANDOFF_DIGEST','FUNDING_TERMS','DURABILITY','PARTIAL_DURABILITY','TRANSPORT_FAILED','COLLECTION_FAILED','CHILD_FAILED','CHILD_TIMEOUT','UNEXPECTED_FAILURE','PACKAGE_BLOCKED'}
class GuardFailure(ValueError):
 def __init__(self,role,stage,code):
  self.role=role if role in ROLES else 'A';self.stage=stage if stage in STAGES else 'remote';self.code=code if code in CODES else 'UNEXPECTED_FAILURE'
  super().__init__(self.role+'/'+self.stage+'/'+self.code)
 def envelope(self):return {'schema':'kpi-safe-guard-failure/v1','role':self.role,'stage':self.stage,'code':self.code,'passed':False}
def require(ok,role,stage,code):
 if not ok:raise GuardFailure(role,stage,code)
def decode_failure(raw,role,stage):
 try:
  v=json.loads(raw)
  if set(v)=={'schema','role','stage','code','passed'} and v['schema']=='kpi-safe-guard-failure/v1' and v['passed'] is False and v['role'] in ROLES and (role is None or v['role']==role) and v['stage'] in STAGES and v['code'] in CODES:return GuardFailure(v['role'],v['stage'],v['code'])
 except Exception:pass
 return GuardFailure(role or 'A',stage,'UNEXPECTED_FAILURE')
def safe_exception(exc,role='A',stage='launcher'):
 return exc if isinstance(exc,GuardFailure) else GuardFailure(role,stage,'UNEXPECTED_FAILURE')

def child_main(main):
 try:return main()
 except BaseException as exc:
  print(json.dumps(safe_exception(exc).envelope()));raise SystemExit(1)
