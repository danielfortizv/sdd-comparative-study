"""Produce real-engine snapshots for two additional client timer controls."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent/'Kiro'
sys.path.insert(0,str(ROOT/'backend'))
from app.rules import engine
from app.domain.models import ActivePiece, empty_board
from app.api.schemas import serialize
from app.store import DEFAULT_SEED

cases = {}
for name, terminal in [('level_up',False),('game_over',True)]:
    game = engine.new_game('A',DEFAULT_SEED)
    assert game.next_type == 'O', 'Own default-seed preview changed; recalibrate fixture'
    game.board = empty_board()
    game.board[19] = ['I']*10
    game.board[19][3] = game.board[19][4] = None
    if terminal:
        game.board[0][3] = 'I'
    game.active = ActivePiece(type='O',origin=(18,3),cells=[(18,3),(18,4),(19,3),(19,4)])
    game.total_lines = 9
    game.level = 1
    game.gravity_interval_ms = 500
    initial = serialize(game).model_dump(mode='json')
    engine.move(game,'left') # blocked by the filled bottom row; real no-op
    first = serialize(game).model_dump(mode='json')
    assert first == initial
    engine.move(game,'down') # real lock/clear/score/spawn path
    second = serialize(game).model_dump(mode='json')
    assert (second['score'],second['total_lines'],second['level'],second['gravity_interval_ms']) == (100,10,2,450)
    assert second['status'] == ('game_over' if terminal else 'playing')
    cases[name] = {'initial':initial,'first':first,'second':second}
target = ROOT/'docs/acceptance/queue-timer-fixtures.json'
if target.exists():
    raise RuntimeError('Refusing to overwrite original queue fixture evidence')
paths = list((ROOT/'backend/app').rglob('*.py'))
target.write_text(json.dumps({'researcher_created':True,'seed':DEFAULT_SEED,
    'mechanism':'Canonical O at bottom, one-row hole,9 prior lines; blocked Left followed by Down uses real engine lock/clear/score/spawn. Terminal variant has one occupied top cell blocking the queued O after clear.',
    'source_hashes':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in paths},
    'cases':cases},indent=2)+'\n',encoding='utf-8')
print('Two real-engine frontend transport fixture sequences retained')
