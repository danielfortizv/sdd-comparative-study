"""Independent researcher domain acceptance; never modifies generated application files."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tool-root', type=Path, default=Path(__file__).resolve().parents[2]/'Kiro')
parser.add_argument('--output', type=Path)
args = parser.parse_args()
root=args.tool_root.resolve()
sys.path.insert(0,str(root/'backend'))
from app.rules import engine, pieces
from app.domain.models import ActivePiece, empty_board
from app.api.schemas import serialize

records=[]
def snapshot(game):
    return (serialize(game).model_dump(mode='json'),game.rng.getstate(),deepcopy(game.bag))

def place(game,kind,origin):
    game.active=ActivePiece(type=kind,origin=origin,cells=[(origin[0]+r,origin[1]+c) for r,c in pieces.SHAPES[kind]])

def setup(rows,lines=0):
    game=engine.new_game('external-domain-fixture',123456)
    game.board=empty_board()
    game.score=0
    game.total_lines=lines
    game.level=1+lines//10
    game.gravity_interval_ms=max(100,500-50*(game.level-1))
    if rows==1:
        game.board[19]=['J']*10
        for c in range(3,7):game.board[19][c]=None
        place(game,'I',(19,3))
    elif rows==2:
        for r in (18,19):
            game.board[r]=['J']*10
            for c in (3,4):game.board[r][c]=None
        place(game,'O',(18,3))
    elif rows in (3,4):
        # Explicitly unreachable prefilled complete rows; active piece stays canonical.
        for r in range(20-rows,20):game.board[r]=['J']*10
        place(game,'O',(18-rows,3))
    else:place(game,'O',(18,3))
    return game

def run(case,description,kind,fn):
    try:
        details=fn()
        records.append(dict(id=case,description=description,fixture_mechanism=kind,status='pass',details=details))
    except Exception as error:
        records.append(dict(id=case,description=description,fixture_mechanism=kind,status='fail',error=f'{type(error).__name__}: {error}'))

awards=[0,100,300,500,800]
def scoring(rows,lines):
    game=setup(rows,lines)
    previous_level=game.level
    preview=game.next_type
    with patch.object(pieces,'next_type',wraps=pieces.next_type) as draw:
        engine.tick(game)
        assert draw.call_count==1,f'normal lock draws={draw.call_count}'
    assert game.score==awards[rows]*previous_level,(game.score,rows,previous_level)
    assert game.total_lines==lines+rows
    assert game.level==1+(lines+rows)//10
    assert game.gravity_interval_ms==max(100,500-50*(game.level-1))
    assert game.active.type==preview
    assert game.next_type in pieces.ALL_TYPES
    assert game.can_hold is True
    assert len(game.board)==20 and all(len(row)==10 for row in game.board)
    return dict(rows=rows,pre_lines=lines,pre_level=previous_level,score=game.score,
                total_lines=game.total_lines,level=game.level,gravity_ms=game.gravity_interval_ms,
                next_draw_count=1)

for n in range(5):
    run(f'S2-{3+n:02}',f'Lock clearing {n} rows at initial level',
        'isolated_domain_prefilled_complete_rows' if n>=3 else 'canonical_piece_controlled_board',
        lambda n=n:scoring(n,0))
    run(f'S2-{3+n:02}',f'Pre-lock multiplier for {n} rows at level3',
        'isolated_domain_prefilled_complete_rows' if n>=3 else 'canonical_piece_controlled_board',
        lambda n=n:scoring(n,20))
run('S2-08','Nine to ten lines scores with level1 then level2/450ms',
    'canonical_piece_controlled_board',lambda:scoring(1,9))
run('S2-09','Gravity floor above level9','canonical_piece_controlled_board',lambda:scoring(1,120))

def hold_cycle():
    game=setup(0)
    outgoing=game.active.type
    preview=game.next_type
    with patch.object(pieces,'next_type',wraps=pieces.next_type) as draw:
        engine.hold(game)
        assert draw.call_count==1
        assert game.hold_type==outgoing and game.active.type==preview and game.can_hold is False
        assert game.active.origin==(0,3)
        before=snapshot(game)
        engine.hold(game)
        assert snapshot(game)==before and draw.call_count==1
        # Canonical O at the bottom guarantees a lock on the next tick.
        place(game,'O',(18,3))
        engine.tick(game)
        assert game.can_hold is True
        preview_before=game.next_type
        outgoing=game.active.type
        held=game.hold_type
        before_rng=game.rng.getstate()
        before_bag=deepcopy(game.bag)
        count=draw.call_count
        engine.hold(game)
        assert game.active.type==held and game.hold_type==outgoing
        assert game.active.origin==(0,3) and game.can_hold is False
        assert game.next_type==preview_before and draw.call_count==count
        assert game.rng.getstate()==before_rng and game.bag==before_bag
    return dict(first_hold_draws=1,rejected_hold_mutations=0,occupied_swap_draws=0,hold_reset_after_lock=True)
run('S2-10/11/12','First/rejected Hold and occupied swap after actual lock','canonical_piece_controlled_board',hold_cycle)

def blocked_hold():
    game=setup(0)
    game.hold_type='O'
    game.can_hold=True
    place(game,'I',(19,3))
    game.board[0][3]='J'
    preview=game.next_type
    rng=game.rng.getstate()
    with patch.object(pieces,'next_type',wraps=pieces.next_type) as draw:
        engine.hold(game)
        assert draw.call_count==0
    assert game.status=='game_over' and game.active is None
    assert game.next_type==preview and game.rng.getstate()==rng
    before=snapshot(game)
    engine.tick(game)
    for direction in ('left','right','down'):engine.move(game,direction)
    engine.hold(game)
    assert snapshot(game)==before
    return dict(status=game.status,active=None,preview_unchanged=True,game_over_actions_unchanged=True)
run('S2-13/14','Blocked held-piece spawn and immutable terminal actions','controlled_spawn_obstruction',blocked_hold)

def soft_drop():
    game=engine.new_game('external-soft-drop',654321)
    before=game.score
    engine.move(game,'down')
    assert game.score==before
    # Soft drop that locks and clears awards only the line-clear score.
    game=setup(1)
    engine.move(game,'down')
    assert game.score==100 and game.total_lines==1
    return dict(nonlocking_drop_points=0,locking_one_line_award=100)
run('S2-19','Soft drop retains locking/clearing with no additional points','canonical_piece_controlled_board',soft_drop)

files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest().upper()
       for p in sorted((root/'backend/app').rglob('*.py'))}
result=dict(researcher_created=True,profile='Kiro own engine API',checker_version='1.0',
            measured_at_utc=datetime.now(timezone.utc).isoformat(),
            status='pass' if all(r['status']=='pass' for r in records) else 'fail',records=records,
            source_sha256=files,checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
            scope='Independent domain evidence. Not HTTP/UI evidence, not 20 acceptance cases passed. Three/four rows explicitly isolated and unreachable in ordinary play.')
destination=args.output or root/'docs/acceptance-domain.json'
destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],records=len(records),failed=[r['id'] for r in records if r['status']=='fail'])))
raise SystemExit(0 if result['status']=='pass' else 1)
