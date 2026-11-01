"""Researcher audit: preserve every original assertion, separately from new tests."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ast,hashlib,json
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
stage=Path(__file__).resolve().parent.parent;root=stage/'Bmad Method';baseline=stage.parent/'Etapa 1/Bmad Method'
rows=[]
for old in sorted((baseline/'backend/app/tests').glob('test_*.py')):
 current=root/old.relative_to(baseline)
 oldtree=ast.parse(old.read_text(encoding='utf-8-sig'));newtree=ast.parse(current.read_text(encoding='utf-8-sig'))
 newfunc={n.name:n for n in ast.walk(newtree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
 for fn in oldtree.body:
  if not isinstance(fn,ast.FunctionDef) or not fn.name.startswith('test_'):continue
  expected=[ast.dump(n,include_attributes=False) for n in ast.walk(fn) if isinstance(n,ast.Assert)]
  found=[ast.dump(n,include_attributes=False) for n in ast.walk(newfunc[fn.name]) if isinstance(n,ast.Assert)] if fn.name in newfunc else []
  remaining=list(found);missing=[]
  for expr in expected:
   if expr in remaining:remaining.remove(expr)
   else:missing.append(expr)
  rows.append({'file':old.relative_to(baseline).as_posix(),'test':fn.name,'original_assertions':len(expected),'current_assertions':len(found),'missing_or_changed':missing,'preserved':not missing,'baseline_file_sha256':hashlib.sha256(old.read_bytes()).hexdigest().upper(),'current_file_sha256':hashlib.sha256(current.read_bytes()).hexdigest().upper()})
result={'researcher_created':True,'audited_at_utc':datetime.now(timezone.utc).isoformat(),'passed':bool(rows) and all(r['preserved'] for r in rows),'original_test_count':len(rows),'preserved_test_count':sum(r['preserved'] for r in rows),'original_assertion_count':sum(r['original_assertions'] for r in rows),'rows':rows,'limitation':'AST assertion preservation only; fixtures/setup may change for the specified queued-piece compatibility. Execution evidence is separate.'}
out=root/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in {'rows','limitation'}}));raise SystemExit(0 if result['passed'] else 1)
