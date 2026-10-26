"""Archive a normally ended native run, then verify with isolated reports."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from kiro_research import DOCS, stamp, write

parser=argparse.ArgumentParser()
parser.add_argument('--label',required=True)
parser.add_argument('--snapshot',required=True)
parser.add_argument('--verify-label',required=True)
args=parser.parse_args()
if not all(re.fullmatch('[a-z0-9-]+',x) for x in [args.label,args.snapshot,args.verify_label]):
    raise ValueError('Unsafe label')
state=DOCS/(args.label+'.closure-status.json')
shared=Path(__file__).resolve().parent
def save(status,**extra):
    write(state,{'researcher_created':True,'updated_at_utc':stamp(),'label':args.label,
        'status':status,'scope':'No app/test/spec edits; independent checks do not establish browser/catalog acceptance',**extra})
def call(name,*params):
    with (DOCS/(args.label+'.closure-'+name+'.log')).open('ab') as stream:
        result=subprocess.run([sys.executable,str(shared/(name+'.py')),*params],stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(name+' exit '+str(result.returncode))
try:
    save('waiting_for_native_close')
    deadline=time.monotonic()+14400
    path=DOCS/(args.label+'.run.json')
    while not path.exists():
        if time.monotonic()>deadline:
            raise RuntimeError('Native close timeout; no closure inferred')
        time.sleep(2)
    result=json.loads(path.read_text(encoding='utf-8'))
    if result.get('exit_code')!=0 or result.get('prompt_result',{}).get('stopReason')!='end_turn':
        raise RuntimeError('Native invocation did not end normally')
    save('archiving_native_evidence')
    for name in ['archive-kiro-transcripts','audit-kiro-inputs','audit-kiro-questions','collect-kiro-metrics']:
        call(name)
    call('snapshot-kiro','--label',args.snapshot)
    save('independent_local_verification_running',snapshot=args.snapshot)
    call('verify-kiro-local','--label',args.verify_label)
    save('independent_local_verification_closed_browser_catalog_pending',snapshot=args.snapshot,
         report='researcher-verification/'+args.verify_label+'/verification-summary.json')
except Exception as error:
    save('attention_required',reason=str(error))
    raise
