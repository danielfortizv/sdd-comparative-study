"""Run an independent check with retained output, durations and protected hashes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import time
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--label',required=True)
p.add_argument('--cwd',default='.')
p.add_argument('command',nargs=argparse.REMAINDER)
a=p.parse_args()
root=Path(__file__).resolve().parent.parent/'Tessl'
out=root/'docs'/'acceptance'/a.label
out.mkdir(parents=True,exist_ok=False)
def hashes():
 result={}
 for folder in ('backend/app','backend/tests','frontend/src'):
  for f in (root/folder).rglob('*'):
   if f.is_file() and '__pycache__' not in f.parts and f.suffix in {'.py','.tsx','.ts','.css'}:result[f.relative_to(root).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest().upper()
 for name in ('docs/coverage.xml','frontend/coverage/lcov.info'):
  f=root/name
  if f.exists():result[name]=hashlib.sha256(f.read_bytes()).hexdigest().upper()
 return result
command=a.command[1:] if a.command and a.command[0]=='--' else a.command
if command and (root/command[0]).is_file():command[0]=str((root/command[0]).resolve())
before=hashes();start=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
with (out/'stdout.log').open('w',encoding='utf-8') as stdout,(out/'stderr.log').open('w',encoding='utf-8') as stderr:
 try:
  result=subprocess.run(command,cwd=root/a.cwd,stdout=stdout,stderr=stderr)
  code=result.returncode;error=None
 except Exception as exc:code=None;error=repr(exc)
after=hashes()
report={'researcher_created':True,'label':a.label,'argv':command,'cwd':str(root/a.cwd),'started_at_utc':start,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-tick,3),'exit_code':code,'launch_error':error,'hashes_before':before,'hashes_after':after,'changed_protected_paths':[n for n in sorted(set(before)|set(after)) if before.get(n)!=after.get(n)]}
(out/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('hashes_before','hashes_after')}))
raise SystemExit(code if code is not None else 127)
