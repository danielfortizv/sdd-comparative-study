"""Researcher-only local server: real application, declared optional runtime fixtures."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import sys

p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);p.add_argument('--scenario',choices=['normal','threshold','gameover'],default='normal');p.add_argument('--record',required=True);a=p.parse_args()
root=Path(__file__).resolve().parent.parent/'Tessl'
sys.path.insert(0,str(root/'backend'))
random.seed(20260929)
from app.main import app
from app.domain.pieces import SHAPES
from app.models.game import ActivePieceModel
from app.controllers.games import router as games_router
import uvicorn

record=Path(a.record).resolve();record.parent.mkdir(parents=True,exist_ok=True)
if record.exists():raise FileExistsError('Refuse to overwrite server evidence')
def write(event):
 with record.open('a',encoding='utf-8') as f:f.write(json.dumps({'at_utc':datetime.now(timezone.utc).isoformat(),**event})+'\n')
write({'researcher_created':True,'pid':os.getpid(),'port':a.port,'scenario':a.scenario,'seed':20260929,'production_generator_seeded_by_wrapper':True,'generated_files_edited':False,'pieces_sha256':hashlib.sha256((root/'backend/app/domain/pieces.py').read_bytes()).hexdigest().upper(),'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),'fixture_limit':'First two creations account for React StrictMode; restart thereafter uses ordinary real creation. Canonical shapes unchanged.'})
if a.scenario!='normal':
 count=[0]
 route=next(r for r in games_router.routes if getattr(r,'path','')=='/api/games' and 'POST' in getattr(r,'methods',set()))
 original=route.dependant.call
 def create_fixture():
  state=original();count[0]+=1
  if count[0]<=2:
   state.board=[[None]*10 for _ in range(20)]
   origin=(17,3) if a.scenario=='threshold' else (0,3)
   state.active_piece=ActivePieceModel(type='O',origin=origin,cells=[(origin[0]+r,origin[1]+c) for r,c in SHAPES['O']])
   state.next_piece='I';state.can_hold=True;state.hold_piece=None
   if a.scenario=='threshold':
    state.total_lines=9;state.score=900;state.level=1;state.gravity_interval_ms=500
    state.board[19]=['J' if c not in (3,4) else None for c in range(10)]
   else:state.board[2][3]='J';state.board[2][4]='J'
   write({'event':'fixture_applied','creation_number':count[0],'state':state.model_dump(mode='json')})
  else:write({'event':'ordinary_restart','creation_number':count[0],'game_id':state.id})
  return state
 # This FastAPI version stores an _IncludedRouter and clones routes lazily.
 # Set endpoint for the future clone and dependant.call for an existing route.
 route.endpoint=create_fixture
 route.dependant.call=create_fixture
uvicorn.run(app,host='127.0.0.1',port=a.port,access_log=True)
