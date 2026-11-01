"""External two-case timer run with unique reports and production provenance."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parent.parent/'Kiro'
DOCS=ROOT/'docs/acceptance'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
target=DOCS/'queued-timer-runs'/stamp
target.mkdir(parents=True)
names=['frontend/src/useGame.ts','frontend/src/api.ts','frontend/coverage/lcov.info',
       'docs/acceptance/queued-timers.external.test.ts','docs/acceptance/vitest.queued-timers.config.mjs','docs/acceptance/queue-timer-fixtures.json']
def hashes():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper() for name in names}
before=hashes()
started=time.time()
argv=['node',str(ROOT/'frontend/node_modules/vitest/vitest.mjs'),'run','--config',str(DOCS/'vitest.queued-timers.config.mjs'),
      '--reporter=json','--outputFile='+str(target/'vitest.json')]
with (target/'stdout.log').open('w',encoding='utf-8') as out,(target/'stderr.log').open('w',encoding='utf-8') as err:
    result=subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=out,stderr=err,timeout=360)
finished=time.time()
native=json.loads((target/'vitest.json').read_text(encoding='utf-8-sig'))
after=hashes()
report={'researcher_created':True,'scope':'Two external real-hook/manual-queue timer controls, not additional catalog IDs',
 'started_at_utc':datetime.fromtimestamp(started,timezone.utc).isoformat(),'ended_at_utc':datetime.fromtimestamp(finished,timezone.utc).isoformat(),
 'duration_seconds':round(finished-started,3),'argv':argv,'cwd':str(ROOT),'exit_code':result.returncode,'coverage_enabled':False,
 'native_json_fresh':started-2<=native['startTime']/1000<=finished,
 'hashes_before':before,'hashes_after':after,'inputs_and_lcov_unchanged':before==after,
 'tests':{k:native.get(k) for k in ['numTotalTests','numPassedTests','numFailedTests']}}
(target/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':str(target/'run.json'),'tests':report['tests'],'stable':before==after,'fresh':report['native_json_fresh']}))
