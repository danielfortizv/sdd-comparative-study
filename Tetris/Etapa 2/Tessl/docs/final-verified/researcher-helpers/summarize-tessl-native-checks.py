"""Index actual native command output; distinguish raw evidence from authored notes."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

r=Path(__file__).resolve().parent.parent/'Tessl'/'docs'
audit=json.loads((r/'native-tool-audit.json').read_text())
runs=[]
for p in r.glob('*.run.json'):
 d=json.loads(p.read_text(encoding='utf-8-sig'));runs.append(d)
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
records=[]
for x in audit['actions']:
 if x['name']!='run_shell_command':continue
 command=(x.get('args') or {}).get('command','')
 outputs=[]
 for block in x.get('result') or []:
  if isinstance(block,dict):
   response=block.get('functionResponse',{}).get('response',{})
   if isinstance(response,dict) and isinstance(response.get('output'),str):outputs.append(response['output'])
 output='\n'.join(outputs)
 label=next((d['label'] for d in runs if x.get('timestamp') and dt(d['started'])<=dt(x['timestamp'])<=dt(d['ended'])),None)
 exits=re.findall(r'\nExit Code:\s*(-?\d+)\s*\nProcess Group PGID:',output)
 checks=[k for k in ('pytest','vitest','npm audit','npm run build','scan-tessl','verify-sonar') if k in command.lower()]
 records.append({'run':label,'timestamp':x['timestamp'],'id':x['id'],'command':command,'checks':checks,'cwd':(x.get('args')or{}).get('dir_path'),'native_tool_status':x['status'],'explicit_reported_process_exit_code':int(exits[-1]) if exits else None,'output_sha256':hashlib.sha256(output.encode()).hexdigest().upper(),'output_characters':len(output),'note':'Tool success is not process/test success; absent explicit exit code stays unknown. Full raw result referenced by native tool audit ID.'})
adjudicated=[]
for p in sorted(r.glob('qa02-*-command.txt')):
 adjudicated.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest().upper(),'classification':'model_authored_measurement_note','use_for_authoritative_timing':False,'reason':'Model manually composed timestamp/duration/exit summaries, including hard-coded timestamps and literal newline escapes. Retain as artifact, derive validated timings from raw native output and independent timed subprocess reports instead.'})
d={'researcher_created':True,'observed_at_utc':datetime.now(timezone.utc).isoformat(),'native_tool_audit_sha256':hashlib.sha256((r/'native-tool-audit.json').read_bytes()).hexdigest().upper(),'commands':records,'model_authored_note_adjudication':adjudicated,'limitation':'This index does not infer successful exit0 from tool-call success or count every internal failed test as an external QA intent. Manual metadata statements are not raw measurements.'}
(r/'native-command-index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'commands':len(records),'with_explicit_nonzero_process_status':sum(x['explicit_reported_process_exit_code'] not in (None,0) for x in records),'model_authored_notes_not_used_as_timing':len(adjudicated)}))
