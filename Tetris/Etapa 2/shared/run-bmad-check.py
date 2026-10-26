"""Researcher command recorder. No shell interpretation or fabricated result summaries."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,subprocess,time,json,os,hashlib
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--cwd',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
command=a.command[1:] if a.command[:1]==['--'] else a.command
if not command:raise ValueError('No command')
requested_command=list(command)
candidate=a.cwd/command[0]
if not Path(command[0]).is_absolute() and ('/' in command[0] or '\\' in command[0]) and candidate.is_file():command[0]=str(candidate.resolve())
a.output.mkdir(parents=True,exist_ok=True)
log=a.output/(a.label+'.log');meta=a.output/(a.label+'.json')
if log.exists() or meta.exists():raise FileExistsError('Refusing overwrite')
env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',NO_COLOR='1')
start=datetime.now(timezone.utc);clock=time.perf_counter()
with log.open('wb') as stream:
 try:
  run=subprocess.run(command,cwd=a.cwd,stdout=stream,stderr=subprocess.STDOUT,env=env)
  code=run.returncode
 except OSError as error:
  stream.write(str(error).encode());code=127
record={'researcher_created':True,'label':a.label,'cwd':str(a.cwd.resolve()),'command':command,'requested_command':requested_command,'recorder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),'started_at_utc':start.isoformat(),'ended_at_utc':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.perf_counter()-clock,6),'exit_code':code,'log_path':str(log.resolve()),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest().upper()}
meta.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));raise SystemExit(code)
