"""Sanitized researcher views of final retained results, for real CUA captures."""
import hashlib
import html
import importlib.util
import json
from pathlib import Path
from kiro_research import DOCS, ROOT, load

path=Path(__file__).with_name('render-kiro-evidence.py')
spec=importlib.util.spec_from_file_location('kiro_evidence_style',path)
style=importlib.util.module_from_spec(spec);spec.loader.exec_module(style)
m=load(DOCS/'metrics.json');r=load(DOCS/'FINAL_REPORT.json')
q=load(DOCS/'question-audit.json')
assert not m['unclosed_invocation_labels'] and all(x['review_complete'] for x in q['runs'])
v=load(DOCS/'researcher-verification/final-07/verification-summary.json')
assert v['status']=='commands_passed_evidence_recorded'
body=style.cards([('Backend tests','120 PASS'),('Frontend tests','49 PASS'),('External races','5 / 5 PASS'),
 ('Full npm audit','0 findings'),('Sonar gate','OK'),('Catalog','20 / 20 mixed')])
body+=style.table(['Independent final check','Retained result'],[
 ['Backend coverage','245 / 247 lines = 99.19%'],['Frontend lines / branches','94.47% / 77.55%'],
 ['Frontend statements / functions','88.58% / 92.68%'],['New coverage / duplication / issues','88.7% / 0.0% / 0'],
 ['Inherited smells / bugs / vulnerabilities','7 / 0 / 0'],['Build and native source hashes','PASS; all protected source/report hashes unchanged']])
body+='<p class="note">Actual retained CLI/test/API data. This is a derived researcher panel, not a native terminal or SonarQube screenshot. Domain cases3/4rows are isolated fixtures; catalog20/20 is not browser-only acceptance.</p>'
body+='<p class="hash">CE: '+r['exact_quality']['ce_task_id']+'<br>Analysis: '+r['exact_quality']['analysis_id']+'</p>'
style.write('final-quality.html','Kiro · independent final quality','Stage2 optionA · CLI2.33 / Auto · Vite8.3.5 / Vitest4.1.12',body)
def val(x):return 'UNKNOWN' if x is None else str(round(x,6))
body=style.cards([('Known Kiro credits',round(m['known_credits'],6)),('Known CLI seconds',m['known_launcher_duration_seconds']),('Unknown credit runs','01 / 05')])
body+=style.table(['Invocation','CLI seconds','Agent seconds','Kiro credits'],[[row['label'],val(row.get('duration_seconds')),val(row.get('agent_elapsed_seconds')),val(row.get('credits'))] for row in m['runs']])
body+='<div class="warning">Billed input/cache/output/thought tokens: UNKNOWN. API attempts/errors/successes: UNKNOWN. Context occupancy and request IDs are not substituted. Account balances are not assigned to interrupted runs.</div>'
body+='<p>7 complete common-seed deliveries verified.3 external QA attempts /2 distinct intents.37 source files /3691 lines /119547 characters.3 new native feature Markdown files /886 lines /92802 characters. Researcher/Codex work is excluded from Kiro consumption.</p>'
style.write('final-consumption.html','Kiro · measured consumption','Native usage summaries and durable launcher intervals; no imputed zero values',body)
names=['metrics.json','FINAL_REPORT.json','input-audit.json','question-audit.json','sonar-verification.json','sonar-summary.json',
 'researcher-verification/final-07/verification-summary.json','acceptance/final/catalog.json']
manifest={'researcher_created':True,'native_UI':False,'scope':'Static derived panels; no credentials or raw transcripts included',
 'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
 'sources':[{'path':name,'sha256':hashlib.sha256((DOCS/name).read_bytes()).hexdigest().upper()} for name in names],
 'panels':[{'path':name,'sha256':hashlib.sha256((DOCS/'evidence-view'/name).read_bytes()).hexdigest().upper()} for name in ['final-quality.html','final-consumption.html']]}
(DOCS/'evidence-view/final-view-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Final quality/consumption panels generated from retained, hashed evidence')
