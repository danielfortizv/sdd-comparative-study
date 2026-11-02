"""Researcher-only shape/coordinate adapter calibration, not Stage2 acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,sys,json,hashlib,copy,ast
stage=Path(__file__).resolve().parents[2];root=stage/'Bmad Method';sys.path.insert(0,str(root/'backend'))
from app.core.domain import get_spawned_piece,create_new_game,SHAPE_TEMPLATES,SHAPE_INDICES
p=Path(__file__).with_name('check_api_v1_3.py');spec=importlib.util.spec_from_file_location('checker',p);checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
rows=[]
for shape in SHAPE_TEMPLATES:
 state=create_new_game('researcher-calibration').model_dump(mode='json');state['active_piece']=get_spawned_piece(shape).model_dump(mode='json');before=copy.deepcopy(state);view=checker.active_piece(state);checker.centered_spawn(view)
 assert view['type']==shape and view['origin']==[0,4 if shape=='O' else 3]
 assert state==before
 legacy={'active_piece':{'type':shape,'origin':view['origin'],'cells':view['cells']}}
 assert checker.active_piece(legacy)==legacy['active_piece']
 rows.append({'shape':shape,'native_origin':state['active_piece']['origin'],'normalized_view_origin':view['origin'],'status':'pass','raw_state_unchanged':state==before})
src=root/'backend/app/core/domain.py';tree=ast.parse(src.read_text());protected={}
for n in tree.body:
 if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ['get_random_shape','get_spawned_piece']:
  protected[n.name]={'ast_sha256':hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest().upper(),'source':ast.get_source_segment(src.read_text(),n)}
r={'researcher_created':True,'measured_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Adapter-only baseline calibration, not implemented Stage2 acceptance. Functional7records/8IDs unchanged; statuscodes/raw JSON not normalized.','checker_version':'1.3','checker_sha256':hashlib.sha256(p.read_bytes()).hexdigest().upper(),'canonical_templates':SHAPE_TEMPLATES,'canonical_indices':SHAPE_INDICES,'protected_functions':protected,'calibration':rows}
(root/'docs/baseline-representation-calibration.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({'adapter_calibration':'7/7','raw_responses_unchanged':True,'stage2_acceptance':'notrun'}))
