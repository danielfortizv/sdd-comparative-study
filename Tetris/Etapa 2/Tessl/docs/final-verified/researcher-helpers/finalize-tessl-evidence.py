"""Adjudicate final acceptance from retained measurements and browser observations."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

stage=Path(__file__).resolve().parent.parent;r=stage/'Tessl'/'docs';tool=r.parent
def read(n):return json.loads((r/n).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
metrics=read('metrics.json');repeat=read('acceptance/08-independent-final-retry/report.json');scan=read('scan-command.json');sonar=read('sonar-verification.json');summary=read('sonar-summary.json');domain=read('acceptance/08-independent-final-retry/domain.json');api=read('acceptance/08-live-api/api.json');contract=read('acceptance/08-live-contract/contract.json');questions=read('question-audit.json');inputs=read('input-audit.json')
assert not metrics['unclosed_invocation_labels']
assert repeat['all_commands_pass'] and repeat['source_unchanged']
assert all(sha(tool/n)==digest for n,digest in repeat['source_hashes_after'].items()),'Source changed after independent final repeat'
assert scan['source_unchanged_during_scan'] and scan['exit_code']==0
assert all(sha(tool/x['path'])==x['sha256'] for x in scan['source_hashes_after'])
assert sonar['gate_status']=='OK' and sonar['ce_status']=='SUCCESS'
assert domain['passed']==17 and domain['failed']==0
assert all(x['status']=='pass' for x in api['cases']) and len(api['cases'])==7
assert contract['status']=='pass' and len(contract['controls'])==9
assert all(x['status']=='pass' for x in contract['controls'])
test_counts={}
for label,total in [('frontend',17),('races',6),('falsey',1)]:
 d=read('acceptance/08-independent-final-retry/'+label+'-vitest.json');assert d['numTotalTests']==total and d['numPassedTests']==total and d['numFailedTests']==0;test_counts[label]=total
assert repeat['coverage']['frontend']['main_tsx_included']
for entry in sonar['coverage_inputs']:
 assert sha(tool/entry['path'])==entry['sha256']
assert metrics['baseline_integrity']['original_stage1_unchanged']
assert not metrics['spec_stage1_copy_change']['changed_files']
original=stage.parent/'Etapa 1'/'Tessl'
assert sha(original/'backend/tests/test_game.py')==sha(tool/'backend/tests/test_game.py')
assert sha(original/'backend/app/domain/pieces.py')==sha(tool/'backend/app/domain/pieces.py')
old_assert=[x.strip() for x in (original/'frontend/src/components/TetrisBoard.test.tsx').read_text().splitlines() if 'expect(' in x]
new_assert=[x.strip() for x in (tool/'frontend/src/components/TetrisBoard.test.tsx').read_text().splitlines() if 'expect(' in x]
assert old_assert==new_assert

browser_files=['browser-hold-key.ax.txt','browser-hold-button.ax.txt','browser-restart.ax.txt','browser-threshold.ax.txt','browser-gameover.ax.txt','browser-terminal-actions.ax.txt','browser-gameover-restart.ax.txt']
ax={n:(r/'acceptance'/n).read_text(encoding='utf-8') for n in browser_files}
for n in browser_files[:2]:assert 'HOLD PIECE USED' in ax[n] and 'button (disabled) Hold Piece' in ax[n]
for n in ['browser-restart.ax.txt','browser-gameover-restart.ax.txt']:
 for text in ['HOLD PIECE AVAILABLE','Status: PLAYING','Score: 0','Lines: 0','Level: 1','Gravity: 500']:assert text in ax[n]
for text in ['Score: 1000','Lines: 10','Level: 2','Gravity: 450']:assert text in ax['browser-threshold.ax.txt']
for n in ['browser-gameover.ax.txt','browser-terminal-actions.ax.txt']:
 assert 'Status: GAME_OVER' in ax[n] and 'button (disabled) Hold Piece' in ax[n] and 'Active Piece: None' in ax[n]
threshold=read('acceptance/browser-threshold-state.json');terminal=read('acceptance/browser-gameover-state.json')
assert [threshold[k] for k in ['score','total_lines','level','gravity_interval_ms']]==[1000,10,2,450]
assert terminal['status']=='game_over' and terminal['active_piece'] is None

catalog=[]
for number in range(1,21):
 cid=f'S2-{number:02d}'
 evidence=[]
 for item in domain['results']:
  if cid in item['catalog_ids']:evidence.append({'path':'acceptance/08-independent-final-retry/domain.json','record':item['name']})
 for item in api['cases']:
  if cid in item['id'].split('/'):evidence.append({'path':'acceptance/08-live-api/api.json','record':item['id']})
 if number==16:evidence.append({'path':'acceptance/08-live-contract/contract.json','controls':9})
 if number==17:evidence.extend([{'path':'acceptance/browser-hold-key.ax.txt'},{'path':'acceptance/browser-hold-button.ax.txt'},{'path':'screenshots/final-hold-key.jpg'},{'path':'screenshots/final-hud-button.jpg'}])
 if number==18:evidence.extend([{'path':'acceptance/08-independent-final-retry/races-vitest.json','tests':6},{'path':'acceptance/08-independent-final-retry/falsey-vitest.json','tests':1},{'path':'screenshots/final-threshold-fixture.jpg'}])
 if number==19:evidence.extend([{'path':'acceptance/08-independent-final-retry/backend.stdout.log','original_backend_tests':9},{'path':'acceptance/08-independent-final-retry/frontend-vitest.json','original_frontend_tests':2}])
 if number==20:evidence.append({'path':'acceptance/08-independent-final-retry/build.stdout.log'})
 assert evidence,cid+' lacks evidence'
 catalog.append({'id':cid,'status':'pass','isolated_completed_row_fixture':number in (6,7),'evidence':evidence})
assert metrics['correction_counts']['distinct_qa_intents_started']==2
assert metrics['correction_counts']['postimplementation_external_correction_prompts_closed']==3
assert all(x['complete_seed_in_effective_submission'] for x in inputs['runs'])
assert questions['closed_runs_observed_blocking_question_count']==0 and not questions['manual_review_required_closed_labels']
report={'researcher_created':True,'finalized_at_utc':datetime.now(timezone.utc).isoformat(),'status':'accepted_with_declared_limits','candidate':'08-qa02','independent_repeat':'acceptance/08-independent-final-retry/report.json','catalog':catalog,'catalog_passed':20,'catalog_total':20,'ordinary_or_user_facing_catalog_cases':18,'isolated_completed_row_cases':['S2-06','S2-07'],'native_tests':{'backend':23,'frontend':17,'original_backend_tests_preserved':9,'original_frontend_tests_preserved':2},'external_controls':{'domain':17,'live_api_records':7,'live_api_catalog_ids':8,'supplemental_contract_controls':9,'races_original':6,'falsey_extra':1},'sonar':{'analysis_id':sonar['analysis_id'],'ce_task_id':sonar['ce_task_id'],'gate_status':sonar['gate_status'],'conditions':sonar['gate_conditions'],'overall_metrics':summary},'source_and_coverage_current':True,'pieces_unchanged':True,'prompt_seed_sha256':inputs['seed_sha256'],'all_effective_inputs_contain_seed':True,'browser_evidence':[{'path':'acceptance/'+n,'sha256':sha(r/'acceptance'/n)} for n in browser_files],'limits':['Production pieces.py keeps inherited unseeded random.choice; common seed means identical prompt. Researcher fixtures use20260929/explicit canonical sequences.','Tessl remote skill search unauthenticated; actual pinned local MCP/plugin workflow retained, no invented native generator.','Historical CLI auxiliary loop detector used gemini-3-flash-preview in05/07; main model3.5Flash; aliases corrected in08. Past calls not erased.','02token/APIcounters unavailable after BILLING_DISABLED; known totals are not a complete billing total.','Internal05/07fixes without prior spec revision are recorded workflow deviations; initial spec-before-code order alone is not blanket compliance.','Four qa02-command.txt summaries contain model-authored timing metadata; not used as authoritative measurements.','Native session_notes retains an old present-tense ERROR paragraph despite completed checkboxes; final exact-task JSON is authoritative. Document quality is not declared perfect.','Sonar retains inherited S2245 game PRNG vulnerability and9smells; newviolations0 does not mean zero total findings.','No Sonar scalability score or BERTopic model score is invented; corpus is prepared for later analysis.','Inherited browser tab title and welcome message still mentionStage1; visible application HUD identifiesStage2. Cosmetic legacy labels are retained.'],'artifacts':{n:sha(r/n) for n in ['metrics.json','input-audit.json','question-audit.json','scan-command.json','sonar-verification.json','sonar-summary.json','acceptance/08-independent-final-retry/report.json']}}
(r/'final-acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
lines=['# Tessl — Etapa2, opciónA: informe del investigador','','Implementación local aceptada contra el catálogo común de20criterios, con los mecanismos y límites de este informe. Sin commits ni push.','', '## Verificación final','',f"- Backend23/23, frontend17/17, dominio17/17, HTTP7/7 registros y contrato9/9controles; concurrencia6/6 +caso adicional1/1.",f"- Sonar gateOK, análisis `{sonar['analysis_id']}`; cobertura nueva82.7%, duplicación nueva0%, incidencias nuevas0.",' - Instalación desde lockfile, build y auditorías completa/producción aprobadas. Fuente y XML/LCOV vinculados por SHA-256.','','## Métricas cerradas','',f"CLI conocido: {metrics['known_duration_seconds']}s. Tokens: {json.dumps(metrics['observed_tokens'])}. Entrada incluye caché. API: {json.dumps(metrics['known_api_totals'])}. Intento02sin contadores, nunca sustituido por cero.",f"Correcciones externas: {metrics['correction_counts']['postimplementation_external_correction_prompts_closed']} intentos para {metrics['correction_counts']['distinct_qa_intents_started']} objetivos(Q01/Q02).",'', '## Catálogo común','', '| Criterio | Resultado | Mecanismo |','|---|---|---|']
for item in catalog:lines.append(f"| {item['id']} | PASS | {'Fixture aislado de filas completas' if item['isolated_completed_row_fixture'] else ' / '.join(sorted({e['path'].split('/')[-1] for e in item['evidence']}))} |")
lines.extend(['','## Límites y procedencia','']+['- '+x for x in report['limits']]+['','## Archivos principales','','- `final-acceptance.json`:criterios y vínculos exactos.','- `metrics.json`:contadores por sesión/modelo, diffs y densidades.','- `native-command-index.json`:salidas originales y notas de medición adjudicadas.','- `RESEARCH_LOG.md`:cronología, incidentes y desviaciones.','- `bertopic-corpus/`:Markdown separado/unificado, sin modelado.','','La bitácora central de Drive conserva tablas, capturas, fallos y controles. No se han añadido credenciales a los informes.'])
(r/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'catalog':'20/20','isolated_cases':2,'gate':sonar['gate_status'],'source_current':True,'files':['final-acceptance.json','FINAL_REPORT.md']}))
