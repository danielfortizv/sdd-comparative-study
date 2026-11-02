"""Researcher-derived HTML view of retained Tessl baseline and usage evidence."""
import hashlib
import html
import json
from pathlib import Path
from datetime import datetime, timezone

docs = Path(__file__).resolve().parent.parent / 'Tessl/docs'
paths = ['metrics.json', 'sonar-baseline/baseline-verification.json', 'transition-20261025/project-change.json', 'transition-20261025/baseline-reverification.json']
values = [json.loads((docs / p).read_text(encoding='utf-8-sig')) for p in paths]
metrics, sonar, transition, integrity = values
assert integrity['status'] == 'unchanged'
assert transition['new_project_model_invocations'] == 0
out = docs / 'evidence-view'
out.mkdir(exist_ok=True)
m = sonar['measures']
rows = [
 ('Sonar coverage / duplication', f"{m['coverage']}% / {m['duplicated_lines_density']}%"),
 ('Inherited bugs / smells / vulnerabilities', f"{m['bugs']} / {m['code_smells']} / {m['vulnerabilities']}"),
 ('Debt / complexity / cognitive complexity', f"{m['sqale_index']} min / {m['complexity']} / {m['cognitive_complexity']}"),
 ('Sonar ncloc / lines', f"{m['ncloc']} / {m['lines']}"),
 ('Source baseline', '19 files / 1,299 lines / 37,962 Unicode characters'),
 ('Retained input / cached tokens', '574,303 including 409,971 cached; not added twice'),
 ('Candidate output / thought tokens', '8,458 / 12,390'),
 ('Known API requests / errors / successes', '19 / 2 / 17; session 02 counters unknown'),
 ('CLI time / attempts', '405.215 known seconds / 2 closed launches'),
]
table=''.join('<tr><th>'+html.escape(k)+'</th><td>'+html.escape(v)+'</td></tr>' for k,v in rows)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Tessl baseline and resumption evidence</title><style>
*{box-sizing:border-box}body{margin:0;background:#091222;color:#eaf1fa;font:15px system-ui,sans-serif}main{max-width:1080px;margin:22px auto;padding:20px 26px;background:#102136;border:1px solid #29445d;border-radius:12px}.tag{font-size:11px;color:#ffe09b;letter-spacing:.07em}h1{font-size:27px;margin:9px 0;color:#80e6ed}p{line-height:1.4;margin:8px 0;color:#cad9e8}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}.card{padding:11px 14px;background:#1b3349;border:1px solid #35556c;border-radius:8px}.card strong{display:block;font-size:26px;color:#9ceacb}.card span{font-size:12px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;border-bottom:1px solid #31516a;padding:6px 9px}th{width:49%;font-weight:500;color:#bde5f2}.note{font-size:12px;color:#ffdb96}.ids{font:11px ui-monospace,monospace;color:#afc8de;margin-top:13px}</style><main>
<div class="tag">RESEARCHER VIEW · DERIVED FROM RETAINED RAW EVIDENCE · BASELINE ONLY</div>
<h1>Tessl · resumption and baseline</h1>
<p>Own Stage 1 code preserved. Requested Gemini 3.5 Flash / CLI 0.60.0 / Tessl 0.112.0.</p>
<div class="cards"><div class="card"><strong>42 / 42</strong><span>Source/spec hashes match both stages</span></div><div class="card"><strong>0</strong><span>New-project model invocations; OAuth pending</span></div><div class="card"><strong>PT1H</strong><span>Quota task reactivated; normal run exit 0</span></div></div>
<table>'''+table+'''</table><p class="note">Baseline gate OK has zero evaluated new-code conditions: this is not Stage 2 acceptance. No frontend baseline LCOV. S2245 on random.choice remains open; no finding suppression.</p>
<p class="note">Historical known usage excludes missing session 02 counters and researcher/Codex setup. Credentials are excluded from this view.</p>
<div class="ids">CE: '''+html.escape(sonar['ce_task_id'])+''' · Analysis: '''+html.escape(sonar['analysis_id'])+'''<br>Raw evidence: metrics.json · sonar-baseline/baseline-verification.json · transition-20261025/</div></main></html>'''
(out / 'resume-baseline.html').write_text(page,encoding='utf-8')
manifest={'researcher_created':True,'created_at_utc':datetime.now(timezone.utc).isoformat(),'view':'resume-baseline.html','sources':[{'path':p,'sha256':hashlib.sha256((docs/p).read_bytes()).hexdigest().upper()} for p in paths],'note':'Derived researcher view, not native Sonar/CLI UI. Baseline only, implementation not started. Historical metrics and unknowns retained.'}
(out/'resume-baseline-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print({'output':str(out/'resume-baseline.html'),'hashed_sources':len(paths)})
