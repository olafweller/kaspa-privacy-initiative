"""Original pinned fee/native policy with only its excessive-quote test adapted.
The real qualify() and native body checks are unchanged. No quote RPC here.
"""
import hashlib,pathlib,sys
SOURCE=pathlib.Path('@KPI_REPO@/.local/worktrees/a1-poc/scripts/a1_fee_check.py')
SOURCE_SHA256='e0228a996c9b9b5cbf725bd4c16adba8d5814b230faea6a71b6b4e2c72558d88'
OLD="if name == 'too_high_quote': prices['observations'][0]['fees']['estimate']['priorityBucket']['feerate'] = Decimal('1000')"
NEW="if name == 'too_high_quote': prices['observations'][0]['fees']['estimate']['priorityBucket']['feerate'] = Decimal(max(c.decimal(b['fee']) for b in manifest['branches'].values()) + 1)"
def adapt(raw):
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError('original exact fee policy source changed')
 text=raw.decode()
 if text.count(OLD)!=1:raise ValueError('original synthetic negative source changed')
 text=text.replace(OLD,NEW)
 clock_old='Decimal(0) <= age <= Decimal(300)'
 if text.count(clock_old)!=1:raise ValueError('original fee clock bound changed')
 text=text.replace(clock_old,'Decimal(-2) <= age <= Decimal(300)')
 marker="    result['original_terms_unchanged'] = manifest == c.load_json(a.manifest)"
 if text.count(marker)!=1:raise ValueError('original negative receipt marker changed')
 text=text.replace(marker,marker+"\n    result['negative_fixture_adapter'] = {'original_source_sha256': '"+SOURCE_SHA256+"', 'adapter_sha256': '"+hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()+"', 'changed_case': 'too_high_quote', 'real_qualification_policy_changed': False}")
 return text
if __name__=='__main__':
 sys.path.insert(0,str(SOURCE.parent));exec(compile(adapt(SOURCE.read_bytes()),str(SOURCE),'exec'),{'__name__':'__main__','__file__':str(SOURCE)})
