"""Researcher-only external hook race acceptance run with source/LCOV provenance."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

TOOL=Path(__file__).resolve().parent.parent/'Kiro'
OUT=TOOL/'docs'/'acceptance'
def hashes():
    names=['frontend/src/useGame.ts','frontend/src/api.ts','frontend/src/App.tsx',
           'docs/acceptance/hook-races.external.test.ts','docs/acceptance/vitest.external.config.mjs',
           'frontend/coverage/lcov.info']
    return {name:hashlib.sha256((TOOL/name).read_bytes()).hexdigest().upper() if (TOOL/name).is_file() else None for name in names}
before=hashes()
started=datetime.now(timezone.utc).isoformat()
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
for name in ['hook-races-vitest.json','hook-races-observations.json','hook-races.stdout.log','hook-races.stderr.log']:
    path=OUT/name
    if path.is_file():
        archive=OUT/'previous-runs'/stamp
        archive.mkdir(parents=True,exist_ok=True)
        (archive/name).write_bytes(path.read_bytes())
command=['node',str(TOOL/'frontend/node_modules/vitest/vitest.mjs'),'run','--config',str(OUT/'vitest.external.config.mjs'),
         '--reporter=json','--outputFile='+str(OUT/'hook-races-vitest.json')]
environment={**os.environ,'RACE_OBSERVATIONS_PATH':str(OUT/'hook-races-observations.json')}
tick=time.monotonic()
with (OUT/'hook-races.stdout.log').open('w',encoding='utf-8') as stdout,(OUT/'hook-races.stderr.log').open('w',encoding='utf-8') as stderr:
    result=subprocess.run(command,cwd=TOOL,env=environment,stdout=stdout,stderr=stderr)
after=hashes()
summary=json.loads((OUT/'hook-races-vitest.json').read_text(encoding='utf-8-sig'))
report={'researcher_created':True,'purpose':'External acceptance reproduction, not generated application tests',
        'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-tick,3),
        'argv':command,'cwd':str(TOOL),'exit_code':result.returncode,'coverage_enabled':False,
        'hashes_before':before,'hashes_after':after,'source_hashes_unchanged':all(before[n]==after[n] for n in before if n.startswith('frontend/src/')),
        'lcov_hash_unchanged':before['frontend/coverage/lcov.info']==after['frontend/coverage/lcov.info'],
        'versions':{name:json.loads((TOOL/'frontend/node_modules'/name/'package.json').read_text())['version'] for name in ['vitest','@testing-library/react']},
        'tests':{'total':summary.get('numTotalTests'),'passed':summary.get('numPassedTests'),'failed':summary.get('numFailedTests')},
        'findings_provisional_while_generation_active':True,'source_change_policy':'If source hashes differ, evidence is not attributed to one stable candidate; rerun after the active generation closes',
        'notes':['Initial discovery-only attempt produced zero tests; retained in attempt01-no-tests-discovered.json. Config root was corrected only within docs/acceptance.','All final runs disable coverage and use the installed frontend Vitest; no application tests/config or source are patched.']}
(OUT/'hook-races-run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['exit_code','source_hashes_unchanged','lcov_hash_unchanged','tests','versions']},indent=2))
