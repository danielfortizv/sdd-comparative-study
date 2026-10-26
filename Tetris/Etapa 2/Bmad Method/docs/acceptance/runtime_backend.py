"""Researcher-owned isolated runtime. Optional declared fixtures; app sources untouched."""
from pathlib import Path
import argparse,hashlib,json,random,sys
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8020);p.add_argument('--scenario',choices=['ordinary','threshold','gameover'],default='ordinary');p.add_argument('--label',required=True);a=p.parse_args()
if not a.label.replace('-','').replace('_','').isalnum():raise ValueError('Invalid label')
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'backend'))
from app import main
from app.core import domain as d
import uvicorn
random.seed(20260929)
original=main.create_new_game
calls=0
def create_with_declared_fixture(game_id):
 global calls
 state=original(game_id);calls+=1
 if calls!=1 or a.scenario=='ordinary':
  with (root/f'docs/acceptance/runtime-{a.label}-creates.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps({'at_utc':datetime.now(timezone.utc).isoformat(),'create_number':calls,'state':state.model_dump()})+'\n')
  return state
 piece=d.get_spawned_piece('O').model_dump();piece['origin']={'row':18,'col':4};piece['cells']=[{'row':18,'col':4},{'row':18,'col':5},{'row':19,'col':4},{'row':19,'col':5}]
 board=[[0]*10 for _ in range(20)]
 changes={'active_piece':d.ActivePiece(**piece),'board':board,'next_piece':'J'}
 if a.scenario=='threshold':
  board[19]=[7 if c not in {4,5} else 0 for c in range(10)]
  changes.update(score=900,total_lines=9,level=1,gravity_interval_ms=500)
 else:board[0][3]=7
 state=state.model_copy(update=changes)
 with (root/f'docs/acceptance/runtime-{a.label}-creates.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps({'at_utc':datetime.now(timezone.utc).isoformat(),'create_number':calls,'state':state.model_dump()})+'\n')
 return state
main.create_new_game=create_with_declared_fixture
record={'researcher_created':True,'started_at_utc':datetime.now(timezone.utc).isoformat(),'scenario':a.scenario,'port':a.port,'rng_seed':20260929,'fixture_only_first_create':a.scenario!='ordinary','generated_source_modified':False,'runtime_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),'fixture_note':'threshold: canonical O at18,4, single row gap,900score/9lines then actual lock crosses10; gameover: canonical O bottomlock, Jnextspawnblocked at0,3. Further creates use unchanged originalcreate.'}
(root/f'docs/acceptance/runtime-{a.label}.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
uvicorn.run(main.app,host='127.0.0.1',port=a.port,log_level='warning')
