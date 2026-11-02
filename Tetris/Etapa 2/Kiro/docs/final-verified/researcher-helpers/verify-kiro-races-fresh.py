"""Final independent race run; reject stale JSON, absent tests and source drift."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SHARED = Path(__file__).resolve().parent
DOCS = SHARED.parent / 'Kiro/docs'
opened = [p.stem for p in DOCS.glob('*.started.json')
          if not p.with_name(p.name.replace('.started.json', '.run.json')).exists()]
if opened:
    raise RuntimeError('Generation still open: ' + str(opened))
start = time.time()
code = None
error = None
try:
    child = subprocess.run([sys.executable, str(SHARED/'run-kiro-race-harness.py')], timeout=360)
    code = child.returncode
except subprocess.TimeoutExpired:
    error = 'researcher_harness_timeout; no acceptance result attributed'
end = time.time()
def read(name):
    try:
        return json.loads((DOCS/'acceptance'/name).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}
native = read('hook-races-vitest.json')
run = read('hook-races-run.json')
fresh = isinstance(native.get('startTime'), (int,float)) and start-2 <= native['startTime']/1000 <= end
run_start = run.get('started_at_utc')
run_fresh = bool(run_start) and start-2 <= datetime.fromisoformat(run_start).timestamp() <= end
executed = native.get('numTotalTests') == 3
stable = run.get('source_hashes_unchanged') is True and run.get('lcov_hash_unchanged') is True
passed = (code == 0 and not error and fresh and run_fresh and executed and stable
          and native.get('numPassedTests') == 3 and native.get('numFailedTests') == 0)
report = {'researcher_created': True, 'started_at_utc':datetime.fromtimestamp(start,timezone.utc).isoformat(),
    'ended_at_utc':datetime.fromtimestamp(end,timezone.utc).isoformat(),
    'duration_seconds':round(end-start,3),'harness_process_exit':code,'error':error,
    'native_result_fresh':fresh,'wrapper_result_fresh':run_fresh,'three_tests_executed':executed,
    'sources_and_lcov_stable':stable,'tests':{k:native.get(k) for k in ['numTotalTests','numPassedTests','numFailedTests']},
    'status':'pass' if passed else 'fail_or_instrumentation_incomplete',
    'scope':'Three external real-hook concurrency controls for S2-18; not the full catalog. Stale/absent reports never pass.'}
(DOCS/'acceptance/hook-races-freshness.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
sys.exit(0 if passed else 1)
