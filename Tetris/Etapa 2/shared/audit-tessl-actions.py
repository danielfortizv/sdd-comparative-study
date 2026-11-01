"""Retain deduplicated native tool evidence and observable edit/check ordering."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

docs=Path(__file__).resolve().parent.parent/'Tessl'/'docs'
rows={}
for p in sorted((docs/'gemini-home').rglob('session-*.jsonl')):
 session=p.stem
 for line in p.open(encoding='utf-8-sig',errors='replace'):
  try:d=json.loads(line)
  except ValueError:continue
  session=d.get('sessionId',session)
  for m in [d]+[v for v in d.get('$set',{}).values() if isinstance(v,dict)]:
   for call in m.get('toolCalls',[]):
    key=(session,call.get('id'))
    if not key[1]:continue
    old=rows.get(key)
    row={'session_id':session,'id':call['id'],'timestamp':m.get('timestamp'),'call_timestamp':call.get('timestamp'),'name':call.get('name'),'args':call.get('args'),'status':call.get('status'),'result':call.get('result'),'source':p.relative_to(docs).as_posix()}
    if not old or len(json.dumps(row))>=len(json.dumps(old)):rows[key]=row
ordered=sorted(rows.values(),key=lambda x:x.get('timestamp') or '')
out=docs/'native-tool-audit.json'
report={'researcher_created':True,'observed_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Native recorded tool calls/results only; pending sessions are not usage closure. No reasoning text. Raw local evidence is private and must be screened before publication.','actions':ordered}
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
summary=[]
for x in ordered:
 args=x.get('args') or {};path=args.get('file_path',args.get('path'))
 if x['name'] in ('replace','write_file','write_file_text','edit_file'):
  summary.append({'timestamp':x['timestamp'],'name':x['name'],'path':path,'category':'native_spec_edit' if path and path.replace('\\','/').startswith('specs/stage2/') else 'other_edit','status':x['status']})
 elif x['name']=='run_shell_command':
  command=args.get('command','')
  if any(s in command.lower() for s in ('pytest','vitest','npm run build','npm audit','scan-tessl','verify-sonar','fetch-sonar')):
   summary.append({'timestamp':x['timestamp'],'name':x['name'],'command':command,'cwd':args.get('dir_path'),'status':x['status'],'raw_result_reference':x['id']})
(docs/'native-action-timeline.json').write_text(json.dumps({'observed_at_utc':report['observed_at_utc'],'raw_audit_sha256':hashlib.sha256(out.read_bytes()).hexdigest().upper(),'events':summary},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'unique_tool_calls':len(ordered),'edit_check_events':len(summary),'last_events':summary[-5:]},indent=2))
