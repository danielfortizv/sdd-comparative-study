"""Researcher BMAD baseline environment, timed subprocess evidence; no app edits."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,os,time,json,hashlib
stage=Path(__file__).resolve().parent.parent;root=stage/'Bmad Method';docs=root/'docs';old=stage.parent/'Etapa 1'/'Bmad Method'
base=Path('C:/Users/Kevin Alvarez/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe');local=root/'backend/.venv/Scripts/python.exe';original=old/'backend/.venv/Scripts/python.exe'
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_CACHE_DIR':str(docs/'pip-cache')};rows=[]
def run(label,args,cwd=root,check=True):
 t=time.monotonic();start=datetime.now(timezone.utc).isoformat();p=subprocess.run([str(x) for x in args],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace');(docs/(label+'.log')).write_text(p.stdout,encoding='utf-8');rows.append({'label':label,'argv':[str(x) for x in args],'cwd':str(cwd),'started_at_utc':start,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-t,3),'exit_code':p.returncode});(docs/'baseline-environment-commands.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows[-1]),flush=True)
 if check and p.returncode:raise RuntimeError(label+' failed; evidence retained')
 return p
inventory="import json,platform,importlib.metadata;print(json.dumps({'python':platform.python_version(),'packages':sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda x:x['name'].lower())}))"
if local.exists():raise FileExistsError('Refusing existing environment')
orig=json.loads(run('baseline-original-environment',[original,'-B','-c',inventory]).stdout)
pins=docs/'baseline-original-python-pins.txt';pins.write_text('\n'.join(x['name']+'=='+x['version'] for x in orig['packages'])+'\n')
run('baseline-venv-create',[base,'-m','venv',root/'backend/.venv'])
run('baseline-package-install',[local,'-m','pip','install','-r',pins])
current=json.loads(run('baseline-replicated-environment',[local,'-B','-c',inventory]).stdout)
assert orig==current,'Original package inventory not replicated'
instrument=stage.parent/'Etapa 1/_toolchain/venv/Scripts/python.exe'
cv=json.loads(run('baseline-coverage-tool-versions',[instrument,'-B','-c',"import importlib.metadata,json;print(json.dumps({x:importlib.metadata.version(x) for x in ['coverage','pytest-cov']}))"]).stdout)
run('baseline-coverage-install',[local,'-m','pip','install','--no-deps',*[k+'=='+v for k,v in cv.items()]])
run('baseline-backend',[local,'-B','-m','pytest','app/tests','-q','--cov=app','--cov-report=term-missing','--cov-report=xml:'+str(docs/'baseline-coverage.xml')],root/'backend')
node=Path('C:/Program Files/nodejs/node.exe');npm=node.parent/'node_modules/npm/bin/npm-cli.js'
run('baseline-npm-ci',[node,npm,'ci','--no-fund','--no-audit'],root/'frontend')
run('baseline-frontend-build',[node,npm,'run','build'],root/'frontend')
run('baseline-npm-audit',[node,npm,'audit','--json'],root/'frontend',False)
manifest=json.loads((docs/'baseline-copy-manifest.json').read_text());bad=[]
for x in manifest['files']:
 if x['path'].startswith(('backend/','frontend/','_bmad-output/')) and hashlib.sha256((root/x['path']).read_bytes()).hexdigest().upper()!=x['sha256']:bad.append(x['path'])
assert not bad,bad
(docs/'baseline-environment.json').write_text(json.dumps({'researcher_created':True,'original':orig,'replicated_before_instrumentation':current,'instrumentation_added':cv,'source_spec_hashes_unchanged':not bad,'baseline_frontend_test_runner':None,'note':'No inherited frontend tests/test runner; do not invent a passing frontend suite. Baseline audit exit1 is retained, not hidden.'},indent=2)+'\n')
