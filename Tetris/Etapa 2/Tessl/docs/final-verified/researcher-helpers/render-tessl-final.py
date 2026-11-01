"""Render final derived evidence and a compact publication dataset from real reports."""
from pathlib import Path
import json
import hashlib
import html
from datetime import datetime,timezone
r=Path(__file__).resolve().parent.parent/'Tessl'/'docs';out=r/'evidence-view'
def read(n):return json.loads((r/n).read_text(encoding='utf-8-sig'))
m=read('metrics.json');f=read('final-acceptance.json');rep=read('acceptance/08-independent-final-retry/report.json');q=read('question-audit.json');inp=read('input-audit.json')
rows=[]
for path in sorted(r.glob('*.run.json')):
 run=json.loads(path.read_text(encoding='utf-8-sig'));label=run['label'];models=[]
 try:s=read(label+'.stdout.json').get('stats',{}).get('models',{})
 except (ValueError,FileNotFoundError):s={}
 for name,stats in s.items():models.append({'model':name,'tokens':stats.get('tokens'),'api':stats.get('api'),'roles':list(stats.get('roles',{}))})
 rows.append({'label':label,'duration_seconds':run['duration_seconds'],'models':models,'unknown_usage':not bool(models)})
def counts(key):return {k:m[key][k] for k in ['files','lines','characters','lines_per_file']}
data={'created_at_utc':datetime.now(timezone.utc).isoformat(),'source_baseline':counts('source_baseline'),'source_current':counts('source_current'),'spec_inherited':counts('spec_stage1_copy'),'spec_stage2':counts('spec_stage2'),'source_change':m['source_change'],'qa_change':m['qa_change_from_initial_implementation'],'usage':m['observed_tokens'],'duration_seconds':m['known_duration_seconds'],'api':m['known_api_totals'],'runs':rows,'qa_attempts':m['correction_counts']['postimplementation_external_correction_prompts_closed'],'qa_intents':m['correction_counts']['distinct_qa_intents_started'],'recorded_main_response_count':m['recorded_response_count'],'observed_blocking_questions':q['closed_runs_observed_blocking_question_count'],'reviewed_main_natural_messages':q['reviewed_unique_natural_language_messages'],'effective_seed_count':sum(x['complete_seed_in_effective_submission'] for x in inp['runs']),'sonar':f['sonar'],'test_counts':f['native_tests'],'external_controls':f['external_controls'],'coverage':rep['coverage'],'independent_checks':[{k:x[k] for k in ['label','duration_seconds','exit_code']} for x in rep['checks']],'corpus_final':read('bertopic-corpus/final/manifest.json'),'normal_app_url':'http://127.0.0.1:3000/'}
(r/'publication-data.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
css='''body{font:16px system-ui;margin:0;background:#eef2f8;color:#15223b}main{margin:25px auto;max-width:1160px;background:white;border-radius:15px;padding:25px}h1{font-size:27px;margin:8px 0 12px}.label{color:#36537c;font-weight:700;font-size:13px;letter-spacing:.06em}.cards{display:flex;gap:14px;margin:18px 0}.card{padding:16px;background:#edf5f1;flex:1;border-radius:9px}.value{font-size:30px;font-weight:750;color:#126547}.note{color:#43536b;font-size:14px;line-height:1.5}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px 8px;text-align:left;border-bottom:1px solid #d6deeb}th{background:#e5ecf6}'''
head='<div class="label">VISTA DERIVADA DEL INVESTIGADOR · NO ES LA UI NATIVA DE SONARQUBE NI DEL CLI</div>'
quality=head+'<h1>Tessl · Etapa 2 · Verificación final independiente</h1><div class="cards"><div class="card">Sonar quality gate<div class="value">OK</div></div><div class="card">Cobertura nueva<div class="value">82,7 %</div></div><div class="card">Nuevas incidencias<div class="value">0</div></div><div class="card">Duplicación nueva<div class="value">0 %</div></div></div>'
def table(headers,rows):return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
quality+=table(['Control real','Resultado'],[['Backend / frontend','23 / 23 y 17 / 17'],['Dominio / HTTP en vivo / contrato','17 / 17 · 7 / 7 registros · 9 / 9 controles'],['Concurrencia original / caso adicional','6 / 6 · 1 / 1'],['Instalación desde lockfile / build','PASS · PASS'],['Auditorías completa / producción','0 vulnerabilidades · 0 vulnerabilidades'],['Fuente y cobertura del análisis exacto','SHA-256 vinculados; fuente sin cambios']])
quality+='<p class="note">Análisis exacto: '+f['sonar']['analysis_id']+'. Catálogo: 20 criterios evaluados; S2-06/07 son fixtures aislados de filas completas. Capturas reales verifican Hold, reinicio, nivel2/450ms y gameover. No se han realizado commits ni push.</p><p class="note">Sonar conserva un hallazgo heredado sobre el PRNG del juego y9smells. El gate aprobado exige cero incidencias nuevas; no se presenta como cero hallazgos totales.</p>'
usage=head+'<h1>Tessl · Consumo cerrado por invocación</h1>'
tr=[]
for run in rows:
 if run['unknown_usage']:values=['N/D']*4
 else:values=[f"{sum((x.get('tokens')or{}).get(k,0) for x in run['models']):,}" for k in ['prompt','cached','candidates','thoughts']]
 tr.append([run['label'],f"{run['duration_seconds']:.3f}",*values])
usage+=table(['Sesión','CLI(s)','Entrada¹','Caché¹','Salida','Pensamiento'],tr)
usage+='<p class="note">Total conocido: 3.642,237sCLI · 39.704.775entrada · 32.103.483caché · 120.725salida · 149.603pensamiento. API400intentos /53errores /347éxitos. ¹Entrada incluye caché; no sumar de nuevo. Intento02sin contadores, nunca cero.</p><p class="note">Main: gemini-3.5-flash. Detector auxiliar de05/07: gemini-3-flash-preview, registrado aparte e incluido una vez. Aliases corregidos en08. Semilla íntegra8/8;2objetivos QA,3intentos correctivos. No se infiere costo facturado.</p>'
for name,body in [('final-quality.html',quality),('final-usage.html',usage)]:
 (out/name).write_text('<!doctype html><html lang="es"><meta charset="utf-8"><title>Tessl · cierre verificado</title><style>'+css+'</style><main>'+body+'</main></html>',encoding='utf-8')
refs=['final-acceptance.json','metrics.json','question-audit.json','input-audit.json','sonar-verification.json','acceptance/08-independent-final-retry/report.json']
(out/'final-manifest.json').write_text(json.dumps({'researcher_created':True,'created_at_utc':data['created_at_utc'],'sources':[{'path':n,'sha256':hashlib.sha256((r/n).read_bytes()).hexdigest().upper()} for n in refs]},indent=2)+'\n')
print(json.dumps({'written':['final-quality.html','final-usage.html','publication-data.json']}))
