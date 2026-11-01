"""Assemble independently verified Kiro evidence; never edit app/tests/specs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime
from kiro_research import BASE, DOCS, ROOT, load, stamp, write

SHARED=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest().upper()
def require(condition,message):
    if not condition: raise RuntimeError(message)

verification=load(DOCS/'researcher-verification/final-07/verification-summary.json')
require(verification.get('status')=='commands_passed_evidence_recorded','Independent local verification incomplete')
require(verification['frontend_tests']['numPassedTests']==49 and verification['frontend_tests']['numFailedTests']==0,'Unexpected frontend verification')
backend_log=(DOCS/'researcher-verification/final-07/backend-tests.stdout.txt').read_text(errors='replace')
require(bool(re.search(r'120 passed',backend_log)),'Backend120 not proven')
api=load(DOCS/'acceptance/final/api.json')
contract=load(DOCS/'acceptance/final/contract.json')
domain=load(DOCS/'acceptance/final/domain.json')
require(len(api['cases'])==7 and all(r['status']=='pass' for r in api['cases']),'API acceptance incomplete')
require(contract['status']=='pass' and len(contract['controls'])==9,'Contract controls incomplete')
require(domain['status']=='pass' and len(domain['records'])==15,'Domain controls incomplete')
races=load(DOCS/'acceptance/hook-races-freshness.json')
require(races['status']=='pass','Original races not independently closed')
queue_path=DOCS/'acceptance/queued-timer-runs/20261023T194625580785Z/run.json'
queued=load(queue_path)
require(queued['native_json_fresh'] and queued['inputs_and_lcov_unchanged'] and queued['tests']['numPassedTests']==2 and queued['tests']['numFailedTests']==0,'Queued timer controls incomplete')
legacy=load(DOCS/'acceptance/original-stage1/original-tests-results.json')
legacy_run=load(DOCS/'acceptance/original-stage1/original-tests-run.json')
require(legacy['collected_test_count']==39 and legacy['passed']==38 and legacy['failed']==1,'Unexpected untouched legacy outcome')
require(legacy_run['original_tests_unchanged'] and legacy_run['candidate_source_stable_during_check'],'Legacy provenance changed')
require('test_state_payload_shape' in json.dumps([r for r in legacy['results'] if 'failed' in str(r)]),'Expected legacy schema failure not retained')

gate=load(DOCS/'sonar-verification.json')
summary=load(DOCS/'sonar-summary.json')
require(gate['ce_status']=='SUCCESS' and gate['gate_status']=='OK' and gate['ce_task_id']=='19506ab6-d54d-41c6-ab8c-0702cb42ac9b','Current exact Sonar task not proven')
require(all(c['status']=='OK' for c in gate['gate_conditions']),'Sonar conditions failed')
for item in gate['coverage_inputs']:
    require(sha(ROOT/item['path'])==item['sha256'],'Native coverage changed after quality analysis')
for audit in [verification['npm_audit_all'],verification['npm_audit_production']]:
    require(audit['vulnerabilities']['total']==0,'Current dependency audit has findings')

# Root has read all40 complete public Say messages in two batches. This is
# explicit manual adjudication for this known run only, never regex inference.
question_audit=load(DOCS/'question-audit.json')
review=load(DOCS/'question-review.json',{})
q07=next(r for r in question_audit['runs'] if r['label']=='07-queued-timer-qa')
require(len(q07['natural_say_messages'])==40 and not q07['non_tool_approval_pending_interactions'],'07 review inventory changed')
for message in q07['natural_say_messages']:
    review[message['message_id']]={'is_blocking_clarification':False,
        'is_nonblocking_review_confirmation_reference':False,'reviewed_at_utc':stamp(),
        'reason':'Root read complete public Say in two batches: progress/diagnostic explanation, specification revision, implementation or result report; no actual researcher clarification/confirmation requested. Reasoning/tool output excluded and self-reported completion independently checked.'}
write(DOCS/'question-review.json',review)

trace_path=DOCS/'acceptance/final/browser-trace.jsonl'
trace=[json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
creates=[r for r in trace if r['kind']=='create']
require(len(creates)>=3 and all(r['seed']==20260929 for r in creates),'Browser fixture/default seed provenance missing')
require(any(r.get('state',{}).get('score')==100 and r.get('state',{}).get('total_lines')==10 and r.get('state',{}).get('level')==2 for r in trace if isinstance(r.get('state'),dict)),'Actual browser engine crossing missing')
require(any(not r['controlled_fixture'] and (r['state']['score'],r['state']['total_lines'],r['state']['level'])==(0,0,1) for r in creates),'Real restart defaults not recorded')
require(any(r.get('state',{}).get('status')=='game_over' for r in trace if isinstance(r.get('state'),dict)),'Browser game over not recorded')
shots=['final-controlled-level-up.jpg','final-hold-key-immediate.jpg','final-hold-button.jpg','final-game-over.jpg']
for name in shots:
    require((DOCS/'screenshots'/name).read_bytes().startswith(b'\xff\xd8'),'Expected actual JPEG capture missing')
browser={'researcher_created':True,'verified_at_utc':stamp(),'source':'Actual in-app-browser UI actions and CUA full-page screenshots',
    'fixture':'Original app/routes/rules with researcher runtime data for first2StrictMode creates; real canonical O lock crosses9->10. Subsequent restarts use original defaults. Fixture server then stopped; normal app.main backend restarted.',
    'observed':{'initial_controlled_hud':[0,9,1],'post_lock_hud':[100,10,2],
       'restart_hud':[0,0,1],'restart_hold_empty':True,'C_key_holds_J_next_I_and_disables_button':True,
       'Hold_button_holds_J_next_I_and_disables_button':True,'game_over_shown_and_all_mutations_disabled':True,
       'soft_drop_UI_key_events_in_game_over_run':160,'document_title':'Tetris - Stage 2'},
    'screenshots':[{'path':'docs/screenshots/'+n,'sha256':sha(DOCS/'screenshots'/n)} for n in shots],
    'trace_sha256':sha(trace_path),'trace_records':len(trace),
    'limits':['Exact450ms/queue safety is established by fake-timer transport tests; a screenshot alone is not timing proof.',
       'Two clip captures were discarded because the screenshot backend applied dimensions without the intended origin. Full-page JPEGs are retained; viewport was never changed.',
       'One later Hold image was captured after a natural lock and is not used as proof of immediate disable. Immediate C/button captures were synchronized using visible state, with no injected browser state.']}
write(DOCS/'acceptance/final/browser-observations.json',browser)

names=['Nuevo juego','Lectura pura','Bloqueo sin filas','Una fila','Dos filas','Tres filas','Cuatro filas',
 'Cruce9->10','Suelo de gravedad100ms','Primer Hold','Rechazo segundo Hold','Hold tras bloqueo',
 'Spawn reservado bloqueado','Inmutabilidad terminal','Reinicio','Contrato API','HUD y controles','Gravedad y concurrencia','Regresión','Build']
rows=[]
for number,name in enumerate(names,1):
    key=f'S2-{number:02d}'
    if number in [1,2,10,11,12,15,16]:
        mechanism='HTTP real, contrato200 conservado'
        evidence=['acceptance/final/api.json','acceptance/final/contract.json']
    elif number in [3,4,5,8,9,13,14]:
        mechanism='Engine/serializer reales, estado controlado y piezas canónicas'
        evidence=['acceptance/final/domain.json']
    elif number in [6,7]:
        mechanism='Fixture aislado de dominio: filas completas prefijadas, O canónica; no se afirma alcanzabilidad en juego sin rotación'
        evidence=['acceptance/final/domain.json']
    elif number==17:
        mechanism='Navegador real: HUD, teclaC, botónHold, reserva,preview y bloqueo'
        evidence=['acceptance/final/browser-observations.json']
    elif number==18:
        mechanism='49 tests nativos +5 controles externos de transporte/tiempo; captura y traza de cruce real'
        evidence=['acceptance/hook-races-freshness.json',str(queue_path.relative_to(DOCS)),'acceptance/final/browser-observations.json']
    elif number==19:
        mechanism='120 pruebas actuales;38legacy originales aprobadas,1igualdad cerrada incompatible retenida; colisiones/tablero/movimiento/bloqueo'
        evidence=['researcher-verification/final-07/verification-summary.json','acceptance/original-stage1/original-tests-results.json','acceptance/final/domain.json']
    else:
        mechanism='npm run build independiente, dependencias/versiones y hashes retenidos'
        evidence=['researcher-verification/final-07/verification-summary.json']
    rows.append({'id':key,'scenario':name,'status':'pass','mechanism':mechanism,'evidence':evidence})
write(DOCS/'acceptance/final/catalog.json',{'researcher_created':True,'verified_at_utc':stamp(),
    'catalog_count':20,'passed':20,'cases':rows,'rate_scope':'20/20 criterios con mecanismos mixtos; no es tasa exclusiva de navegador. S2-06/07 son fixtures aislados de dominio y se separan de aceptación de gameplay normal.'})

baseline=load(DOCS/'baseline-copy-manifest.json')
require(all(sha(BASE/r['path'])==r['sha256'] for r in baseline['files']),'An original Stage1 baseline file changed')
require(all(sha(ROOT/r['path'])==r['sha256'] for r in baseline['files'] if r['path'].startswith('.kiro/specs/')),'Inherited native specs changed')
for rel in ['backend/app/store.py','backend/app/rules/pieces.py']:
    require(sha(ROOT/rel)==sha(BASE/rel),'Own generator/default seed changed')
write(DOCS/'final-baseline-preservation.json',{'researcher_created':True,'verified_at_utc':stamp(),
    'original_files_verified':len(baseline['files']),'all_original_hashes_match':True,
    'inherited_specs_byte_identical':True,'own_default_seed':20260929,'own_shapes_7bag_store_byte_identical':True})
classes=load(DOCS/'run-classifications.json')
classes['07-queued-timer-qa']['work_completion_status']='Independent code/tests/build/audit/quality/API/domain/concurrency/browser catalog verified; publication tracked separately'
write(DOCS/'run-classifications.json',classes)
for helper in ['audit-kiro-questions','collect-kiro-metrics']:
    subprocess.run([sys.executable,str(SHARED/(helper+'.py'))],check=True)
m=load(DOCS/'metrics.json')
inputs=load(DOCS/'input-audit.json')
require(not m['unclosed_invocation_labels'],'An invocation remains open')
require(all(r['complete_seed_in_effective_submission'] for r in inputs['runs']) and len(inputs['runs'])==7,'Full seed delivery incomplete')
for name,item in m['source_current']['per_file'].items():
    require(sha(ROOT/name)==item['sha256'],'Current source differs from metrics')
report={'researcher_created':True,'verified_at_utc':stamp(),'status':'implementation_and20_catalog_verified','publication_tracking_path':'drive-final-publication.json',
    'tool':'Kiro','stage':2,'option':'A','catalog':'acceptance/final/catalog.json','catalog_passed':20,
    'native_generated_tests':{'backend_instances':120,'frontend_instances':49},
    'independent_concurrency_tests':{'original_races_passed':3,'queued_timers_passed':2},
    'domain_records_passed':15,'API_records_passed':7,'contract_controls_passed':9,
    'backend_coverage':verification['backend_coverage'],'frontend_coverage':verification['frontend_coverage_summary']['total'],
    'sonar':summary,'exact_quality':gate,'native_metrics_path':'metrics.json','native_metrics_sha256':sha(DOCS/'metrics.json'),
    'known_credits':m['known_credits'],'unknown_credit_labels':m['unknown_credit_labels'],
    'known_CLI_seconds':m['known_launcher_duration_seconds'],'unknown_CLI_labels':m['unknown_duration_labels'],
    'known_agent_seconds':m['known_agent_elapsed_seconds'],'tokens':'not exposed; unknown, not zero',
    'API_attempts_errors_successes':'not exposed; requestIds are identifiers only',
    'source':{k:v for k,v in m['source_current'].items() if k!='per_file'},
    'native_feature_specs':{k:v for k,v in m['spec_stage2'].items() if k!='per_file'},
    'external_QA_attempts':m['corrections']['external_postimplementation_prompt_attempts_closed'],
    'distinct_external_QA_intents':m['corrections']['external_postimplementation_distinct_qa_intents'],
    'publication_document':'https://docs.google.com/document/d/1JRZvjK8-fdFitwbiKLe2NhOsk1FZNCa_TclgnFwdjao',
    'limitations':['Two interrupted-run credit totals remain unknown; account deltas are not substituted.',
       'Resolved backend model/auxiliary per-role usage are unknown under Auto. CLI01 used2.25;02 onward2.33.',
       'Original legacy closed-schema test fails as required new fields extend it;38 functional tests pass unchanged.',
       'Sonar0new violations coexists with7inherited smells; no scalability/load score inferred.',
       'Sonar93.2%, frontend94.47%lines/88.58%statements and backend245/247 use different denominators.',
       'Researcher/Codex helpers, verification, browser work and documentation are excluded from Kiro credits/time.'],
    'no_repository_uploads_or_commits':True}
write(DOCS/'FINAL_REPORT.json',report)
def value(v): return 'ND' if v is None else str(round(v,6)) if isinstance(v,float) else str(v)
text=['# Kiro — Tetris Etapa2, opciónA','',
 'Implementación local y20 criterios del catálogo verificados con mecanismos declarados. Publicación documental registrada por separado.','',
 '## Verificación','',
 '-120 pruebas backend y49frontend aprobadas en repetición independiente;build aprobado;auditorías npmglobal/producción0.',
 '-5controles externos de concurrencia aprobados;15registros de dominio,7registrosHTTP y9controles de contrato aprobados.',
 '-Semilla común íntegra acreditada en7/7 entradas;PRNG propio20260929 yshapes/7bag/store conservados.',
 '-Cobertura backend245/247=99.19%;frontend88.58%sentencias,77.55%ramas,92.68%funciones,94.47%líneas;7módulosLCOVincluidomain.tsx.',
 f'-SonarCE{gate["ce_task_id"]} SUCCESS;análisis{gate["analysis_id"]},gateOK:88.7%coberturanueva,0%duplicación,0violacionesnuevas. Global93.2%;7smellsheredados,0bugs/vulnerabilidades/hotspots;deuda23min;complejidad153/cognitiva114;ratingsA.','',
 '## Invocaciones yconsumo nativo','',
 '|Invocación|sCLI|sagente|CréditosKiro|requestIds observados|','|---|---:|---:|---:|---:|']
for r in m['runs']:
    text.append('|'+ '|'.join([r['label'],value(r.get('duration_seconds')),value(r.get('agent_elapsed_seconds')),value(r.get('credits')),value(r.get('recorded_request_id_count'))])+'|')
text += ['',f'Créditos conocidos:{m["known_credits"]};01/05desconocidos. TiempoCLI conocido:{m["known_launcher_duration_seconds"]}s;05desconocido. Tiempoagente conocido:{round(m["known_agent_elapsed_seconds"],3)}s;01/05desconocidos. Son sumas de intervalos acreditados, no duración total del proyecto. Tokens input/cache/output/thought e intentos/errores/éxitosAPI:ND;no cero ni inferidos de contexto.3intentos QA externos para2intenciones;los2ciclosSonar internos conocidos de04se separan.','',
 '## Artefactos y comparación con baseline','',
 '|Alcance|Archivos|Líneas|CaracteresUnicode/LF|','|---|---:|---:|---:|',
 f'|FuentepropiaStage1|{m["source_baseline"]["files"]}|{m["source_baseline"]["lines"]}|{m["source_baseline"]["characters"]}|',
 f'|FuenteStage2incluyetests/config|{m["source_current"]["files"]}|{m["source_current"]["lines"]}|{m["source_current"]["characters"]}|',
 f'|Specsheredadas|{m["spec_stage1_copy"]["files"]}|{m["spec_stage1_copy"]["lines"]}|{m["spec_stage1_copy"]["characters"]}|',
 f'|FeatureMDnativoStage2|{m["spec_stage2"]["files"]}|{m["spec_stage2"]["lines"]}|{m["spec_stage2"]["characters"]}|','',
 'Densidad fuente99.76líneas/archivo;feature295.33. Deltafuente+2552/-68líneas,neto+2484líneas/+85906caracteres, no volumen acumulado de edición. Manifiestos/config se separan sin sumarlos dos veces. FuenteproductivaSonarncloc784/líneas1292 tiene otro denominador. CorpusBERTopic previsto:solo los3MDnativosdel feature;no se entrenómodelo de temas.','',
 '## Catálogo común','',
 '|ID|Caso|Estado|Mecanismo|','|---|---|---|---|']
text += ['|'+ '|'.join([r['id'],r['scenario'],r['status'],r['mechanism']])+'|' for r in rows]
text += ['', 'S2-06/07se prueban con fixtures aislados, no como jugadas normales alcanzables sin rotación. El20/20es un catálogo de mecanismos mixtos;no se publica una tasa exclusiva de navegador. Evidencias exactas por ID enacceptance/final/catalog.json.','',
 '## Límites, desviaciones e historial','',
 '-01interrumpido por cambio de cuenta;02Auto/Vibe pese aflagSpec;03enadelanteSpec/Auto acreditado porACPantes de prompt. Auto no revela el modelo resuelto.',
 '-05interrumpido sin cierre;ended/duración/exit quedan desconocidos. Seusa únicamente límite superior observado para auditar registros retenidos;no se factura el periodo fuera de línea.',
 '-04adaptó una igualdad de claves del testStage1 trasrevisarspecs. Las39pruebas originales intactas dan38pass/1faildeesquema cerrado;no se afirman39sin cambios.',
 '-04remediófindingsestilísticos sin revisión previa de specs, según Sayretenido;esa parte no acredita spec-first.07sí revisó3artefactosantes de código.',
 '-Se conservan los fallosdeconcurrencia previos, dos análisisSonarfallidos, auditoríasvulnerables, intentos de preparación/sandboxyreportes actuales porseparado.',
 '-CLIcambió2.25->2.33;toolchainfrontendcambióVite5.4.11->8.3.5/Vitest4.1.12,plugin6.1.2;React18.3.1/TS5.6.3/Python3.10.11preservados. Las versiones yfechas limitancomparaciones causales entreherramientas.',
 '-MonitorWindowsreactivado por usuarioel23deoctubre,PT1H,Ready;registrosenshared/quota-monitor. Seconsulta sin inferencia;datosdesconocidos nunca equivalen a0. No sehan usado restablecimientos.',
 '-Todo el códigocontinúa local;sin commits ni subidas. Tessl yBMAD permanecen pausados hasta nueva autorización/credenciales.',
 '', '## Archivos para reproducir','',
 '`metrics.json`, `input-audit.json`, `question-audit.json`, `RESEARCH_LOG.md`, `researcher-verification/final-07/verification-summary.json`, `acceptance/final/catalog.json`, `sonar-verification.json`, `stage2-frontend-result-07.json`, capturas ytranscripts identificados porhash. Las fuentes/specs/evidencias se congelan en el snapshot final después de verificar la publicación.']
(DOCS/'FINAL_REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'catalog':20,'credits_known':m['known_credits'],'source_files':m['source_current']['files'],'native_spec_files':m['spec_stage2']['files']}))
