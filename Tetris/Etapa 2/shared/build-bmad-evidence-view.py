"""Researcher-created evidence view, sourced from measured files, not a native CLI UI."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, html, json

root = Path(__file__).resolve().parent.parent / 'Bmad Method'
docs = root / 'docs'
out = docs / 'evidence-view'
out.mkdir(exist_ok=True)
metrics_path = docs / 'metrics.json'
data = json.loads(metrics_path.read_text(encoding='utf-8-sig'))
rows = []
for run in data['runs']:
    counters=run['tokens']
    fmt=lambda key: 'N/D' if counters.get(key) is None else f'{counters[key]:,}'
    rows.append([run['label'], str(run['duration_seconds']) + ' s',fmt('api_requests'),fmt('api_errors'),*[fmt(k) for k in ['input_tokens','cached_tokens','output_tokens','thought_tokens']]])

def table(headers, body):
    return '<table><thead><tr>' + ''.join('<th>'+html.escape(str(x))+'</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in body) + '</tbody></table>'

headers = ['Sesión cerrada', 'CLI', 'API', 'Errores', 'Entrada¹', 'Caché¹', 'Salida', 'Razona.']
stamp = datetime.now(timezone.utc).isoformat()
digest = hashlib.sha256(metrics_path.read_bytes()).hexdigest().upper()
page = '''<!doctype html><html lang="es"><meta charset="utf-8"><title>BMAD · Evidencia de planificación</title><style>
*{box-sizing:border-box}body{margin:0;background:#f2f5fa;color:#12213c;font:17px/1.45 Arial,sans-serif;padding:34px 40px}main{max-width:1170px;margin:auto}h1{font-size:30px;margin:5px 0}h2{font-size:21px;margin:20px 0 8px}.tag{font-size:13px;letter-spacing:1px;color:#416186}p{margin:8px 0}table{border-collapse:collapse;width:100%;background:white;font-size:15px}th,td{padding:11px 10px;text-align:right;border-bottom:1px solid #d7dfeb}th:first-child,td:first-child{text-align:left}th{background:#17355f;color:white}.note{background:#e4edf8;border-left:4px solid #356ba7;padding:12px 16px;margin:14px 0}.foot{font-size:12px;color:#52647d;word-break:break-all}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{background:white;padding:15px;border:1px solid #d7dfeb}b{color:#17355f}
</style><main><div class="tag">TETRIS · ETAPA 2 · BMAD 6.12.0</div><h1>Registro de planificación y consumo</h1><p>Vista del investigador derivada de JSON medidos. No es la interfaz nativa de Gemini ni SonarQube.</p>'''
page += table(headers, rows)
page += '<div class="note">¹ La entrada incluye la caché: no se suman ambas columnas. Sólo sesiones cerradas; una sesión activa queda fuera de estos totales. N/D significa contador no disponible, nunca cero. Las sesiones interrumpidas y los errores se conservan; salida 0 no acredita aceptación.</div>'
page += '<div class="grid"><div class="card"><b>Controles conservados</b><p>Gemini CLI 0.60.0 · gemini-3.5-flash<br>Semilla común sin cambios · Stage 1 propia<br>Desarrollo local · sin commits ni push</p></div><div class="card"><b>Monitor cancelado por el usuario</b><p>Tarea Windows: Disabled<br>Automatización Codex: PAUSED<br>Script: salida previa a consultas y suspensión</p></div></div>'
page += '<p class="foot">Generado UTC: '+stamp+'<br>Fuente: docs/metrics.json; sesiones *.run.json y *.stdout.json<br>SHA-256 métricas: '+digest+'</p></main></html>'
(out / 'planning.html').write_text(page, encoding='utf-8')
if len(rows)>3:
    page=page.replace('</style>','body{padding:22px 30px;font-size:15px;line-height:1.3}h1{font-size:26px}th,td{padding:7px 9px;font-size:13px}.note{font-size:13px;padding:9px 12px;margin:10px 0}.card{font-size:13px;padding:10px}.foot{font-size:11px}</style>').replace('Registro de planificación y consumo','Registro de sesiones y consumo')
    (out / 'planning.html').write_text(page, encoding='utf-8')
(out / 'manifest.json').write_text(json.dumps({'researcher_created':True,'generated_at_utc':stamp,'metrics_sha256':digest,'runs':[p.name for p in sorted(docs.glob('0*.run.json'))],'purpose':'Derived measured evidence, not native CLI or Sonar UI'},indent=2)+'\n')
print(json.dumps({'view':str(out/'planning.html'),'closed_rows':len(rows)}))
