"""Clearly labelled researcher view of frozen observed evidence, never a native CLI/UI imitation."""
from datetime import datetime,timezone
import hashlib
import html
import json
from pathlib import Path

r=Path(__file__).resolve().parent.parent/'Tessl'/'docs'
out=r/'evidence-view';out.mkdir(exist_ok=True)
sources=['05-implement.run.json','05-implement.stdout.json','06-qa01.run.json','06-qa01.stdout.json','acceptance/05-domain-authorized/domain.json','acceptance/05-races-configured-vitest.json','implementation-05-initial/sonar-verification.json','implementation-05-initial/metrics.json']
data={n:json.loads((r/n).read_text(encoding='utf-8-sig')) for n in sources}
models=[]
for label in ('05-implement','06-qa01'):
 for model,m in data[label+'.stdout.json']['stats']['models'].items():
  t=m['tokens'];api=m['api'];models.append([label,model,f"{t['prompt']:,}",f"{t['cached']:,}",f"{t['candidates']:,}",f"{t['thoughts']:,}",str(api['totalRequests']),str(api['totalErrors'])])
def table(headers,rows):return '<table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'
css='''body{font:17px system-ui;margin:0;background:#eef2f8;color:#15223b}main{margin:30px auto;max-width:1150px;background:white;border-radius:16px;padding:28px}h1{font-size:28px;margin:8px 0 12px}h2{font-size:21px}.label{color:#36537c;letter-spacing:.08em;font-weight:700;font-size:13px}.note{color:#43536b;font-size:15px;line-height:1.5}.cards{display:flex;gap:18px;margin:20px 0}.card{padding:18px;background:#f1f5fa;flex:1;border-radius:10px}.value{font-size:32px;font-weight:750}.fail{color:#a52035}.pass{color:#126547}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px 8px;text-align:left;border-bottom:1px solid #d6deeb}th{background:#e5ecf6}.small{font-size:13px;color:#4f6076}'''
header='<div class="label">VISTA DERIVADA DEL INVESTIGADOR · NO ES LA UI NATIVA DEL CLI NI DE SONARQUBE</div><h1>Tessl · Etapa 2 · Candidato inicial y corrección Q01</h1>'
usage=header+'<p class="note">Cierre medido de 05 y 06. La ejecución 07 está pendiente y no se suma. Proyecto Google: project-d419b4aa-7c3b-4fde-932.</p>'+table(['Ejecución','Modelo observado','Entrada¹','Caché¹','Salida','Pensamiento','API','Errores'],models)+'<div class="cards"><div class="card"><div class="small">05 · CLI</div><div class="value">1.607,145 s</div></div><div class="card"><div class="small">06 · CLI</div><div class="value">193,479 s</div></div><div class="card"><div class="small">Intento correctivo</div><div class="value">Q01</div></div></div><p class="note">¹ Entrada incluye caché. No sumar caché de nuevo. Detector auxiliar del CLI con 3 Flash preview en 05 registrado por separado. 06 terminó sin respuesta final después de errores de red/429; sus especificaciones cambiaron, la aplicación no quedó corregida.</p><p class="small">Contadores del CLI, no importe facturado ni duración humana. El consumo desconocido de 02 no se reemplaza por cero.</p>'
domain=data['acceptance/05-domain-authorized/domain.json'];race=data['acceptance/05-races-configured-vitest.json'];sonar=data['implementation-05-initial/sonar-verification.json']
rows=[(a['fullName'],a['status'].upper()) for suite in race['testResults'] for a in suite['assertionResults']]
quality=header+'<div class="cards"><div class="card"><div class="small">Dominio / HTTP externo</div><div class="value pass">17 / 17</div></div><div class="card"><div class="small">Concurrencia externa</div><div class="value fail">4 / 6</div></div><div class="card"><div class="small">Sonar · quality gate</div><div class="value fail">ERROR</div></div></div>'+table(['Prueba externa de interfaz','Resultado'],rows)+'<p class="note">Sonar del candidato 05: cobertura nueva 82,2 %, duplicación nueva 0 % y 7 incidencias nuevas. El candidato no se considera terminado. Se preserva el fallo y se corrige mediante especificación previa.</p><p class="small">Los escenarios de 3/4 filas usan fixtures aislados con filas completas y O canónica. Las pruebas externas no modificaron fuente ni XML/LCOV. Los intentos fallidos del arnés se conservan separados.</p>'
for name,body in [('checkpoint-05-06-usage.html',usage),('checkpoint-05-06-quality.html',quality)]:
 (out/name).write_text('<!doctype html><html lang="es"><meta charset="utf-8"><title>Tessl · evidencia derivada</title><style>'+css+'</style><main>'+body+'</main></html>',encoding='utf-8')
manifest={'researcher_created':True,'created_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Frozen initial candidate05 and closed spec-only06; not final07 acceptance','sources':[{'path':n,'sha256':hashlib.sha256((r/n).read_bytes()).hexdigest().upper()} for n in sources]}
(out/'checkpoint-05-06-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'written':2,'sources':len(sources)}))
