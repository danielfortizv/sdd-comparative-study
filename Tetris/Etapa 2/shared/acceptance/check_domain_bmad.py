"""Independent researcher acceptance for BMAD's own native contract. No app edits."""
from __future__ import annotations
import argparse, ast, hashlib, inspect, json, random, sys, time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
root=args.root.resolve()
sys.path.insert(0,str(root/'backend'))
from fastapi.testclient import TestClient
from app import main
from app.core import domain as d

FIELDS={'id','status','board','active_piece','score','total_lines','level','gravity_interval_ms','next_piece','hold_piece','can_hold'}
META=['score','total_lines','level','gravity_interval_ms','next_piece','hold_piece','can_hold']
checks=[]
observations=[]
client=TestClient(main.app)

def source_manifest():
    rows=[]
    for parent in [root/'backend/app',root/'frontend/src']:
        for p in sorted(parent.rglob('*')):
            if p.is_file() and p.suffix in {'.py','.ts','.tsx','.css'} and not {'__pycache__','tests'}.intersection(p.relative_to(parent).parts):
                rows.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest().upper()})
    return rows

def require(condition,message):
    if not condition:raise AssertionError(message)

def run(name,fn,scope='ordinary/native'):
    start=time.perf_counter()
    try:
        detail=fn()
        checks.append({'name':name,'scope':scope,'passed':True,'detail':detail,'elapsed_seconds':round(time.perf_counter()-start,6)})
    except Exception as error:
        checks.append({'name':name,'scope':scope,'passed':False,'error':type(error).__name__+': '+str(error),'elapsed_seconds':round(time.perf_counter()-start,6)})

def request(method,path,payload=None,status=200):
    response=client.request(method,path,json=payload) if payload is not None else client.request(method,path)
    value=response.json()
    observations.append({'method':method,'path':path,'request':payload,'status':response.status_code,'response':value})
    require(response.status_code==status,f'{method} {path}: {response.status_code} != {status}')
    if status in {200,201}:
        require(set(value)==FIELDS,'full eleven-field native state required')
        require(len(value['board'])==20 and all(len(row)==10 for row in value['board']),'20x10 board')
        require(all(type(c) is int and 0<=c<=7 for row in value['board'] for c in row),'native integer board')
    return value

def shifted(shape,row,col=None):
    piece=d.get_spawned_piece(shape).model_dump()
    dr=row-piece['origin']['row'];dc=0 if col is None else col-piece['origin']['col']
    piece['origin']={'row':piece['origin']['row']+dr,'col':piece['origin']['col']+dc}
    piece['cells']=[{'row':c['row']+dr,'col':c['col']+dc} for c in piece['cells']]
    return piece

def fixture(**changes):
    payload={'id':'researcher-fixture','status':'playing','board':[[0]*10 for _ in range(20)],'active_piece':shifted('O',5),'score':0,'total_lines':0,'level':1,'gravity_interval_ms':500,'next_piece':'J','hold_piece':None,'can_hold':True}
    payload.update(changes)
    state=d.GameState(**payload)
    main.sessions[state.id]=state
    return state.model_dump()

def action(s,kind,payload=None):
    return request('POST',f"/api/games/{s['id']}/{kind}",payload)

def initialization():
    with patch.object(d.random,'choice',side_effect=['O','I']) as rng:
        s=request('POST','/api/games',status=201)
        require(rng.call_count==2,'newgame exactly two draws')
    require([s[k] for k in META]==[0,0,1,500,'I',None,True],'fresh counters/preview/hold')
    require(s['active_piece']==d.get_spawned_piece('O').model_dump(),'native O at(0,4)')
    return {'draws':2,'id':s['id']}

def canonical():
    baseline=json.loads((root/'docs/baseline-representation-calibration.json').read_text(encoding='utf-8-sig'))
    # The complete baseline table is retained in the calibration evidence.
    require(d.SHAPE_TEMPLATES==baseline['canonical_templates'],'original canonical templates changed')
    require(d.SHAPE_INDICES==baseline['canonical_indices'],'original shape indices changed')
    for name, expected in baseline['protected_functions'].items():
        current=ast.dump(ast.parse(inspect.getsource(getattr(d,name))),include_attributes=False)
        original=ast.dump(ast.parse(expected['source']),include_attributes=False)
        require(current==original,f'protected function changed: {name}')
    require(len(d.SHAPE_TEMPLATES)==7,'seven shapes')
    for shape in d.SHAPE_TEMPLATES:
        p=d.get_spawned_piece(shape)
        require(len(p.cells)==4,'canonical four cells')
        require(p.origin.col==(4 if shape=='O' else 3) and p.origin.row==0,'own canonical origin')
    return {'calibration_file_sha256':hashlib.sha256((root/'docs/baseline-representation-calibration.json').read_bytes()).hexdigest().upper(),'baseline_keys':list(baseline)}

def reads():
    s=fixture(score=777,total_lines=23,level=3,gravity_interval_ms=400,hold_piece='L',can_hold=False)
    with patch.object(d.random,'choice',side_effect=AssertionError('GET drew RNG')):
        for _ in range(4):require(request('GET',f"/api/games/{s['id']}")==s,'GET changed state')
    return {'reads':4,'draws':0}

def metadata(kind,direction=None):
    s=fixture(score=777,total_lines=23,level=3,gravity_interval_ms=400,hold_piece='L',can_hold=False)
    with patch.object(d.random,'choice',side_effect=AssertionError('nonlock drew RNG')):
        v=action(s,kind,{'direction':direction} if direction else None)
    require({k:s[k] for k in META}=={k:v[k] for k in META},'dirty metadata reset')
    return {k:v[k] for k in META}

def wall():
    s=fixture(active_piece=shifted('O',5,0),score=777,total_lines=23,level=3,gravity_interval_ms=400,hold_piece='L',can_hold=False)
    with patch.object(d.random,'choice',side_effect=AssertionError('no-op drew RNG')):
        require(action(s,'move',{'direction':'left'})==s,'valid wall collision changed state')

def clearance(n,lines=0,level=1,score=137):
    board=[[0]*10 for _ in range(20)]
    if n in {1,2}:
        for r in range(20-n,20):board[r]=[7 if c not in {4,5} else 0 for c in range(10)]
        row=18
    elif n in {3,4}:
        for r in range(20-n,20):board[r]=[7]*10
        row=18-n
    else:row=18
    s=fixture(board=board,active_piece=shifted('O',row),score=score,total_lines=lines,level=level,gravity_interval_ms=max(100,500-50*(level-1)),can_hold=False,hold_piece='S')
    with patch.object(d.random,'choice',side_effect=['T']) as rng:v=action(s,'tick')
    require(rng.call_count==1,'lock exactly one preview draw')
    require(v['score']==score+[0,100,300,500,800][n]*level,'prelock score multiplier')
    require(v['total_lines']==lines+n,'cumulative lines')
    expected_level=1+(lines+n)//10
    require(v['level']==expected_level,'level threshold')
    require(v['gravity_interval_ms']==max(100,500-50*(expected_level-1)),'progressive gravity/floor')
    require(v['active_piece']==d.get_spawned_piece('J').model_dump() and v['next_piece']=='T','queue consumption and canonical spawn')
    require(v['can_hold'] is True and v['hold_piece']=='S','lock unlocks Hold without resetting occupied slot')
    return {'rows':n,'before':{k:s[k] for k in ['score','total_lines','level']},'after':{k:v[k] for k in ['score','total_lines','level','gravity_interval_ms']},'fixture_origin':s['active_piece']['origin'],'draws':1}

def hold(occupied=False,blocked=False):
    board=[[0]*10 for _ in range(20)]
    if blocked:board[0][3]=7
    s=fixture(board=board,score=777,total_lines=23,level=3,gravity_interval_ms=400,hold_piece='J' if occupied else None,next_piece='T' if occupied else 'J')
    with patch.object(d.random,'choice',side_effect=['S']) as rng:v=action(s,'hold')
    require(rng.call_count==(0 if occupied else 1),'hold draw accounting')
    require(v['hold_piece']=='O' and v['can_hold'] is False,'slot and cooldown')
    require([v[k] for k in META[:4]]==[s[k] for k in META[:4]],'hold changed progression')
    require(v['next_piece']==('T' if occupied else 'S'),'hold preview')
    if blocked:require(v['status']=='game_over' and v['active_piece'] is None,'blocked Hold terminal with no illegal piece')
    else:
        require(v['active_piece']==d.get_spawned_piece('J').model_dump(),'held piece canonical re-entry')
        with patch.object(d.random,'choice',side_effect=AssertionError('cooldown drew RNG')):require(action(v,'hold')==v,'second Hold changed state')
    return {'occupied':occupied,'blocked':blocked,'expected_draws':0 if occupied else 1}

def normal_obstruction():
    b=[[0]*10 for _ in range(20)];b[0][3]=7
    s=fixture(board=b,active_piece=shifted('O',18),score=777,total_lines=23,level=3,gravity_interval_ms=400,hold_piece='L')
    with patch.object(d.random,'choice',side_effect=['T']) as rng:v=action(s,'tick')
    require(rng.call_count==1 and v['status']=='game_over' and v['active_piece'] is None,'normal obstructed spawn')
    with patch.object(d.random,'choice',side_effect=AssertionError('terminal drew RNG')):
        for kind,payload in [('tick',None),('hold',None),('move',{'direction':'left'}),('move',{'direction':'right'}),('move',{'direction':'down'})]:require(action(v,kind,payload)==v,'terminal mutation')
        require(request('GET',f"/api/games/{v['id']}")==v,'terminal read mutation')

def errors():
    s=fixture()
    request('POST',f"/api/games/{s['id']}/move",{'direction':'rotate'},422)
    request('POST',f"/api/games/{s['id']}/move",{},422)
    for method,ending in [('GET',''),('POST','/tick'),('POST','/hold'),('POST','/move')]:
        request(method,'/api/games/missing-researcher-id'+ending,{'direction':'left'} if ending=='/move' else None,404)

def restart():
    old=fixture(score=777,total_lines=23,level=3,gravity_interval_ms=400,hold_piece='L',can_hold=False)
    with patch.object(d.random,'choice',side_effect=['S','Z']) as rng:new=request('POST','/api/games',status=201)
    require(rng.call_count==2 and new['id']!=old['id'],'fresh UUID/two draws')
    require([new[k] for k in META]==[0,0,1,500,'Z',None,True],'restart reset')

random.seed(20260929)
before=source_manifest()
run('native-seven-shape-calibration',canonical)
run('initialization-two-draws',initialization)
run('repeated-reads-zero-draws',reads)
for kind,direction in [('move','left'),('move','right'),('move','down'),('tick',None)]:run(f'dirty-metadata-{kind}-{direction}',lambda k=kind,v=direction:metadata(k,v))
run('legal-wall-no-op-200',wall)
for n in range(5):run(f'clear-{n}-prelock-multiplier',lambda n=n:clearance(n),scope='isolated completed-row domain fixture' if n in {3,4} else 'ordinary/native')
run('threshold-nine-to-ten',lambda:clearance(1,9,1))
run('threshold-nine-to-eleven',lambda:clearance(2,9,1))
run('gravity-floor-at-level-nine',lambda:clearance(1,79,8))
run('gravity-floor-beyond-level-nine',lambda:clearance(1,199,20))
run('empty-hold-and-rejection',lambda:hold(False,False))
run('occupied-hold-and-rejection',lambda:hold(True,False))
run('blocked-empty-hold',lambda:hold(False,True))
run('blocked-occupied-hold',lambda:hold(True,True))
run('blocked-normal-spawn-and-terminal-invariance',normal_obstruction)
run('invalid-direction-and-missing-game-contract',errors)
run('restart-all-fields',restart)
after=source_manifest()
require(before==after,'researcher check changed application sources')
result={'researcher_created':True,'version':'1.0','tool':'BMAD','captured_at_utc':datetime.now(timezone.utc).isoformat(),'seed':20260929,'passed':all(c['passed'] for c in checks),'checks':checks,'total':len(checks),'passed_count':sum(c['passed'] for c in checks),'http_observations':observations,'source_hashes_before':before,'source_hashes_after':after,'source_unchanged':before==after,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),'limitation':'Independent native TestClient/domain fixtures; not live browser or whole shared acceptance catalog. N3/N4 isolated precompleted rows are not ordinary-play reachability evidence.'}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'checks':len(checks),'passed_count':result['passed_count'],'failures':[c for c in checks if not c['passed']],'output':str(args.output)}))
sys.exit(0 if result['passed'] else 1)
