"""Honest derived visualization of exact Sonar evidence; no native UI impersonation."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,html,json
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
docs=Path(__file__).resolve().parent.parent/'Bmad Method/docs';out=docs/'evidence-view';out.mkdir(exist_ok=True)
paths={name:docs/name for name in ['sonar-verification.json','sonar-exact-quality-gate.json','sonar-metrics.json','scan-command.json']}
data={name:json.loads(path.read_text(encoding='utf-8-sig')) for name,path in paths.items()}
v=data['sonar-verification.json'];gate=data['sonar-exact-quality-gate.json']['projectStatus'];measures={x['metric']:x.get('value') for x in data['sonar-metrics.json']['component']['measures']}
rows=''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in [c['metricKey'],c.get('actualValue','N/D'),c['comparator']+' '+c['errorThreshold'],c['status']])+'</tr>' for c in gate['conditions'])
metrics=''.join('<div><span>'+html.escape(label)+'</span><b>'+html.escape(str(measures.get(key,'N/D')))+'</b></div>' for label,key in [('Cobertura global %','coverage'),('Bugs','bugs'),('Smells','code_smells'),('Vulnerabilidades','vulnerabilities'),('Duplicación global %','duplicated_lines_density'),('Deuda (min)','sqale_index'),('Complejidad','complexity'),('Cognitiva','cognitive_complexity')])
page='''<!doctype html><html lang="es"><meta charset="utf-8"><title>BMAD · Sonar exacto</title><style>*{box-sizing:border-box}body{margin:0;padding:30px 45px;background:#f3f6fa;color:#14223c;font:17px/1.45 Arial}h1{font-size:29px;margin:5px 0 10px}p{margin:9px 0}.tag{font-size:13px;color:#426184;letter-spacing:1px}table{border-collapse:collapse;width:100%;background:white;margin:15px 0}th,td{padding:10px 15px;text-align:left;border-bottom:1px solid #d5dfeb}th{background:#17355f;color:white}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.metrics div{background:white;padding:10px 14px;border:1px solid #d5dfeb}.metrics span{display:block;font-size:14px;color:#536580}.metrics b{font-size:24px}.note{background:#e5edf8;padding:12px 16px;margin-top:15px;font-size:15px}.foot{font-size:12px;color:#586b85;word-break:break-all}</style><div class="tag">TETRIS · ETAPA 2 · BMAD · EVIDENCIA MEDIDA</div>'''
page+='<h1>Quality gate: '+html.escape(gate['status'])+'</h1><p>Vista del investigador derivada de la API autenticada. No es el panel nativo de SonarQube.</p>'
page+='<table><thead><tr><th>Condición nueva</th><th>Medición</th><th>Falla si</th><th>Resultado</th></tr></thead><tbody>'+rows+'</tbody></table><div class="metrics">'+metrics+'</div>'
page+='<div class="note">Proyecto tetris-stage2-bmad · candidato fijo 2.0 contra baseline 1.0. Cobertura global y cobertura nueva son distintas. El aviso heredado de random.choice se conserva por el control experimental; no se presenta como incidencia nueva ni se oculta.</div>'
page+='<p class="foot">CE '+html.escape(v['ce_status'])+' · análisis '+html.escape(v['analysis_id'])+'<br>Verificado UTC '+html.escape(v['verified_at_utc'])+'<br>SHA-256 gate '+hashlib.sha256(paths['sonar-exact-quality-gate.json'].read_bytes()).hexdigest().upper()+'</p>'
target=out/(a.label+'.html')
if target.exists():raise FileExistsError('Refusing overwrite')
target.write_text(page,encoding='utf-8');(out/(a.label+'.json')).write_text(json.dumps({'researcher_created':True,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'verification':v,'source_hashes':{name:hashlib.sha256(path.read_bytes()).hexdigest().upper() for name,path in paths.items()}},indent=2)+'\n')
print(json.dumps({'view':str(target),'gate':gate['status'],'analysis':v['analysis_id']}))
