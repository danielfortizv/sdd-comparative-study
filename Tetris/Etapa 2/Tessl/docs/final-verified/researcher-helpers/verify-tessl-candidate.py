"""Independent repeat of native checks on a closed candidate, with fresh coverage."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
stage=Path(__file__).resolve().parent.parent;root=stage/'Tessl';docs=root/'docs';out=docs/'acceptance'/a.label
open_runs=[f.name for f in docs.glob('*.started.json') if not (docs/(f.name.removesuffix('.started.json')+'.run.json')).exists()]
if open_runs:raise RuntimeError('Refusing independent final repeat while model edits are active: '+str(open_runs))
out.mkdir(parents=True,exist_ok=False)
node=Path('C:/Program Files/nodejs/node.exe');npm=node.parent/'node_modules/npm/bin/npm-cli.js';python=root/'backend/.venv/Scripts/python.exe'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest().upper()
def source_hashes():
 result={}
 for folder in ('backend/app','backend/tests','frontend/src'):
  for f in sorted((root/folder).rglob('*')):
   if f.is_file() and '__pycache__' not in f.parts and f.suffix in {'.py','.ts','.tsx','.css'}:result[f.relative_to(root).as_posix()]=sha(f)
 for n in ('frontend/package.json','frontend/package-lock.json','frontend/vite.config.ts','backend/pyproject.toml','.gemini/settings.json'):
  if (root/n).exists():result[n]=sha(root/n)
 return result
before=source_hashes();records=[];start=datetime.now(timezone.utc).isoformat()
def run(label,argv,cwd):
 tick=time.monotonic();when=datetime.now(timezone.utc).isoformat();code=None;error=None
 with (out/(label+'.stdout.log')).open('w',encoding='utf-8') as stdout,(out/(label+'.stderr.log')).open('w',encoding='utf-8') as stderr:
  try:code=subprocess.run([str(v) for v in argv],cwd=cwd,stdout=stdout,stderr=stderr,timeout=240).returncode
  except Exception as exc:error=repr(exc)
 row={'label':label,'argv':[str(v) for v in argv],'cwd':str(cwd),'started_at_utc':when,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-tick,3),'exit_code':code,'error':error};records.append(row)
 (out/'checks.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:row[k] for k in ('label','duration_seconds','exit_code','error')}),flush=True)
 return code==0 and error is None
ok=run('npm-ci',[node,npm,'ci','--no-fund','--no-audit'],root/'frontend')
if ok:
 checks=[('backend',[python,'-m','pytest','--cov=app','--cov-report=xml:../docs/coverage.xml','tests/'],root/'backend'),
 ('frontend',[node,root/'frontend/node_modules/vitest/vitest.mjs','run','--coverage','--reporter=default','--reporter=json','--outputFile='+str(out/'frontend-vitest.json')],root/'frontend'),
 ('build',[node,npm,'run','build'],root/'frontend'),
 ('audit-all',[node,npm,'audit','--json'],root/'frontend'),
 ('audit-production',[node,npm,'audit','--omit=dev','--json'],root/'frontend'),
 ('domain',[python,stage/'shared/acceptance/check_domain_tessl.py','--output',out/'domain.json'],root),
 ('races',[node,root/'frontend/node_modules/vitest/vitest.mjs','run','--config',docs/'acceptance/vitest.external.config.mjs','--reporter=json','--outputFile='+str(out/'races-vitest.json')],root),
 ('falsey',[node,root/'frontend/node_modules/vitest/vitest.mjs','run','--config',docs/'acceptance/vitest.falsey.config.mjs','--reporter=json','--outputFile='+str(out/'falsey-vitest.json')],root)]
 for label,argv,cwd in checks:ok=run(label,argv,cwd) and ok
after=source_hashes();changed=[n for n in sorted(set(before)|set(after)) if before.get(n)!=after.get(n)]
coverage={}
f=docs/'coverage.xml'
if f.exists():
 x=ET.parse(f).getroot();coverage['backend']={'lines_valid':x.attrib.get('lines-valid'),'lines_covered':x.attrib.get('lines-covered'),'line_rate':x.attrib.get('line-rate'),'sha256':sha(f),'mtime_utc':datetime.fromtimestamp(f.stat().st_mtime,timezone.utc).isoformat()}
f=root/'frontend/coverage/lcov.info'
if f.exists():
 sf=[line[3:] for line in f.read_text().splitlines() if line.startswith('SF:')]
 coverage['frontend']={'source_files':sf,'main_tsx_included':any(v.replace('\\','/').endswith('main.tsx') for v in sf),'sha256':sha(f),'mtime_utc':datetime.fromtimestamp(f.stat().st_mtime,timezone.utc).isoformat()}
report={'researcher_created':True,'scope':'Independent repeat; browser acceptance and final exact-task Sonar still separate','label':a.label,'started_at_utc':start,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'all_commands_pass':ok,'source_hashes_before':before,'source_hashes_after':after,'changed_source_paths':changed,'source_unchanged':not changed,'coverage':coverage,'checks':records,'runner_sha256':sha(Path(__file__))}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if ok and not changed else 1)
