"""Independent Tessl production-path domain/HTTP fixtures; not generated app tests.

Uses the real FastAPI routes, in-memory store, Pydantic serialization and domain
logic. S2-06/07 intentionally prefill completed rows; canonical shapes are never
changed. No fixture here claims ordinary unrotated gameplay can clear 3/4 rows.
"""
import argparse
import copy
import hashlib
import json
import random
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True)
args = parser.parse_args()
stage = Path(__file__).resolve().parents[2]
root = stage / 'Tessl'
output = Path(args.output).resolve()
if output.exists():
    raise FileExistsError('Refusing to overwrite acceptance evidence')
sys.path.insert(0, str(root / 'backend'))
from fastapi.testclient import TestClient
from app.main import app
from app.controllers.games import GAMES
from app.domain.pieces import SHAPES
from app.models.game import ActivePieceModel

SEED = 20260929
random.seed(SEED)
original_shapes = copy.deepcopy(SHAPES)
canonical_types = list(SHAPES)
original_choice = random.choice
records = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def protected_hashes():
    result = {}
    for folder in ('backend/app', 'backend/tests', 'frontend/src'):
        for p in sorted((root / folder).rglob('*')):
            if p.is_file() and p.suffix in {'.py', '.ts', '.tsx', '.js', '.css'} and '__pycache__' not in p.parts:
                result[p.relative_to(root).as_posix()] = digest(p)
    for name in ('docs/coverage.xml', 'frontend/coverage/lcov.info'):
        if (root / name).exists():
            result[name] = digest(root / name)
    return result


before_hashes = protected_hashes()


@contextmanager
def draws(*sequence):
    remaining = list(sequence)
    seen = []

    def choose(options):
        if list(options) != canonical_types:
            return original_choice(options)
        assert remaining, 'Unexpected extra piece draw'
        chosen = remaining.pop(0)
        assert chosen in SHAPES
        seen.append(chosen)
        return chosen

    with patch.object(random, 'choice', choose):
        yield seen


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def perform(client, method, path, payload=None, status=200):
    kwargs = {'json': payload} if payload is not None else {}
    response = client.request(method, path, **kwargs)
    check(response.status_code == status, f'{method} {path}: HTTP {response.status_code}, expected {status}')
    return response.json()


def create(client):
    data = perform(client, 'POST', '/api/games')
    return data, GAMES[data['id']]


def action(client, data, name, payload=None):
    return perform(client, 'POST', f"/api/games/{data['id']}/{name}", payload)


def canonical(state, kind, row, col=3):
    state.active_piece = ActivePieceModel(type=kind, origin=(row, col), cells=[(row+r, col+c) for r, c in SHAPES[kind]])
    check([(r-row, c-col) for r, c in state.active_piece.cells] == SHAPES[kind], 'Noncanonical fixture piece')


def setup_lock(state, rows, lines=0, score=0, level=1):
    state.board = [[None] * 10 for _ in range(20)]
    state.score, state.total_lines, state.level = score, lines, level
    state.gravity_interval_ms = max(100, 500 - 50 * (level - 1))
    if rows <= 2:
        for row in range(20-rows, 20):
            state.board[row] = ['I'] * 10
            state.board[row][3] = state.board[row][4] = None
        canonical(state, 'O', 18)
    else:
        for row in range(20-rows, 20):
            state.board[row] = ['I'] * 10
        canonical(state, 'O', 18-rows)
    state.status = 'playing'
    state.can_hold = False


def run(catalog, name, function, mechanism='Real HTTP/controller/domain/serializer with explicitly controlled valid state'):
    try:
        evidence = function()
        records.append({'catalog_ids': catalog, 'name': name, 'status': 'pass', 'mechanism': mechanism, 'evidence': evidence})
    except Exception as error:
        records.append({'catalog_ids': catalog, 'name': name, 'status': 'fail', 'mechanism': mechanism,
                        'error': str(error), 'traceback': traceback.format_exc()})


with TestClient(app) as client:
    def new_game():
        with draws('O', 'I') as seen:
            data, state = create(client)
            check(data['score'] == data['total_lines'] == 0 and data['level'] == 1, 'Initial counters')
            check(data['gravity_interval_ms'] == 500 and data['hold_piece'] is None and data['can_hold'] is True, 'Initial gravity/Hold')
            check(data['active_piece']['type'] == 'O' and data['next_piece'] == 'I', 'Active/preview draw order')
            check(data['active_piece']['origin'] == [0, 3], 'Inherited origin')
            check(len(seen) == 2, 'Exactly two initial draws')
            check(len(data['board']) == 20 and all(len(r) == 10 and all(c is None for c in r) for r in data['board']), 'Initial board')
            return {'draws': seen, 'state': data}
    run(['S2-01'], 'initial state and exact two canonical draws', new_game)

    def peek():
        with draws('O', 'I') as seen:
            data, _ = create(client)
            first = perform(client, 'GET', f"/api/games/{data['id']}")
            second = perform(client, 'GET', f"/api/games/{data['id']}")
            check(data == first == second and len(seen) == 2, 'Reads mutated state or RNG')
            return {'equal_full_states': True, 'draws_after_two_reads': len(seen)}
    run(['S2-02'], 'complete read-state and preview immutability', peek)

    def scoring(rows, lines=0, score=0, level=1):
        with draws('O', 'I', 'J') as seen:
            data, state = create(client)
            setup_lock(state, rows, lines, score, level)
            result = action(client, data, 'tick')
            expected_score = score + {0:0, 1:100, 2:300, 3:500, 4:800}[rows] * level
            check(result['score'] == expected_score, 'Pre-lock scoring multiplier')
            check(result['total_lines'] == lines+rows, 'Cleared row count')
            new_level = 1 + (lines+rows)//10
            check(result['level'] == new_level, 'Level formula')
            check(result['gravity_interval_ms'] == max(100, 500-50*(new_level-1)), 'Gravity formula/floor')
            check(result['active_piece']['type'] == 'I' and result['next_piece'] == 'J', 'Preview consumption on normal lock')
            check(result['can_hold'] is True and len(seen) == 3, 'Hold reset/exact one subsequent draw')
            check(len(result['board']) == 20 and all(len(r)==10 for r in result['board']), 'Board dimensions after clear')
            return {'rows': rows, 'pre_lock_level': level, 'score_before': score, 'score_after': result['score'],
                    'total_lines_after': result['total_lines'], 'level_after': result['level'],
                    'interval_after': result['gravity_interval_ms'], 'draws': seen,
                    'fixture': 'Canonical O with already-complete settled rows' if rows>=3 else 'Canonical O, reachable row-completion geometry'}
    run(['S2-03'], 'zero-row lock, preview and Hold reset', lambda: scoring(0))
    run(['S2-04'], 'one-row scoring production path', lambda: scoring(1))
    run(['S2-05'], 'two-row scoring production path', lambda: scoring(2))
    run(['S2-06'], 'three-row isolated scoring rule', lambda: scoring(3), 'Isolated domain fixture: three already-complete rows, canonical O; not ordinary gameplay')
    run(['S2-07'], 'four-row isolated scoring rule', lambda: scoring(4), 'Isolated domain fixture: four already-complete rows, canonical O; not ordinary gameplay')
    run(['S2-08'], 'threshold nine to ten uses old level', lambda: scoring(1, lines=9, score=250, level=1))
    run(['S2-08'], 'threshold nine to eleven uses old level', lambda: scoring(2, lines=9, level=1))
    run(['S2-09'], 'gravity floor at high level', lambda: scoring(1, lines=89, level=9))

    def first_and_rejected_hold():
        with draws('O', 'I', 'Z') as seen:
            data, _ = create(client)
            held = action(client, data, 'hold')
            check(held['hold_piece'] == 'O' and held['active_piece']['type'] == 'I' and held['next_piece'] == 'Z', 'First Hold exchange')
            check(held['active_piece']['origin'] == [0,3] and held['can_hold'] is False, 'First Hold origin/unavailability')
            rejected = action(client, data, 'hold')
            check(rejected == held and len(seen) == 3, 'Rejected Hold mutated state or consumed preview')
            return {'draws': seen, 'rejected_full_state_unchanged': True, 'held_type': held['hold_piece']}
    run(['S2-10','S2-11'], 'first Hold plus repeated rejection', first_and_rejected_hold)

    def swap_after_lock():
        with draws('O', 'I', 'Z', 'J') as seen:
            data, state = create(client)
            action(client, data, 'hold')
            canonical(state, 'I', 19)
            locked = action(client, data, 'tick')
            check(locked['can_hold'] is True and locked['active_piece']['type'] == 'Z', 'Lock failed to unlock Hold')
            swapped = action(client, data, 'hold')
            check(swapped['active_piece']['type'] == 'O' and swapped['hold_piece'] == 'Z', 'Occupied Hold swap')
            check(swapped['next_piece'] == locked['next_piece'] == 'J' and len(seen)==4, 'Swap consumed preview')
            check(swapped['active_piece']['origin']==[0,3] and swapped['can_hold'] is False, 'Swap origin/availability')
            return {'draws': seen, 'swap_draws': 0, 'preview_preserved': swapped['next_piece']}
    run(['S2-12'], 'Hold unlock and occupied swap without a draw', swap_after_lock)

    def blocked_hold(occupied):
        with draws('O','I','J') as seen:
            data, state = create(client)
            state.board = [[None]*10 for _ in range(20)]
            state.board[0][3] = 'T'
            canonical(state,'O',17)
            state.hold_piece = 'I' if occupied else None
            state.can_hold = True
            result = action(client,data,'hold')
            check(result['status']=='game_over' and result['active_piece'] is None, 'Blocked Hold did not terminate legally')
            expected_draws = 2 if occupied else 3
            check(len(seen)==expected_draws, 'Blocked Hold preview draw count')
            check(result['next_piece']==('I' if occupied else 'J'), 'Blocked Hold preview semantics')
            return {'occupied_hold':occupied,'draws':seen,'active_piece':None,'status':result['status']}
    run(['S2-13'], 'blocked occupied Hold spawn', lambda: blocked_hold(True))
    run(['S2-13'], 'blocked empty Hold spawn consumes one preview', lambda: blocked_hold(False))

    def terminal_row_zero():
        with draws('I','O') as seen:
            data,state=create(client)
            state.board=[[None]*10 for _ in range(20)]
            for col in range(3,7): state.board[1][col]='T'
            canonical(state,'I',0)
            result=action(client,data,'tick')
            check(result['status']=='game_over' and result['active_piece'] is None, 'Row-zero terminal rule')
            check(result['next_piece']=='O' and len(seen)==2, 'Row-zero terminal branch invented preview draw')
            unchanged=[action(client,data,'tick'),action(client,data,'hold')]
            unchanged += [action(client,data,'move',{'direction':direction}) for direction in ['left','right','down']]
            check(all(x==result for x in unchanged) and len(seen)==2, 'Game-over action mutated full state or RNG')
            return {'draws':seen,'terminal_preview':'O','all_five_mutations_full_state_unchanged':True}
    run(['S2-14','S2-19'], 'row-zero terminal preview and all game-over mutations', terminal_row_zero)

    def blocked_normal_spawn():
        with draws('O','I','J') as seen:
            data,state=create(client)
            setup_lock(state,0)
            state.board[0][3]='T'
            result=action(client,data,'tick')
            check(result['status']=='game_over' and result['active_piece'] is None, 'Blocked normal spawn')
            check(result['next_piece']=='J' and len(seen)==3, 'Blocked normal spawn did not consume exactly one preview')
            return {'draws':seen,'status':'game_over','preview_after_attempt':'J'}
    run(['S2-14'], 'blocked normal spawn consumes preview exactly once', blocked_normal_spawn)

    def restart():
        with draws('O','I','Z','J') as seen:
            old,state=create(client)
            state.score=9999; state.total_lines=77; state.level=8; state.gravity_interval_ms=150
            state.hold_piece='L'; state.can_hold=False; state.status='game_over'
            state.board[19]=['T']*10
            fresh,_=create(client)
            check(fresh['id']!=old['id'],'Restart must create a new session')
            check(fresh['score']==fresh['total_lines']==0 and fresh['level']==1 and fresh['gravity_interval_ms']==500,'Restart counters')
            check(fresh['hold_piece'] is None and fresh['can_hold'] is True and fresh['status']=='playing','Restart Hold/status')
            check(all(c is None for row in fresh['board'] for c in row),'Restart dirty board')
            check(fresh['active_piece']['type']=='Z' and fresh['next_piece']=='J' and len(seen)==4,'Restart draw control')
            return {'draws':seen,'new_id':True,'reset_all_stage2_fields':True}
    run(['S2-15'], 'restart from completely dirty terminal state', restart)

check(SHAPES == original_shapes, 'Application/fixtures mutated canonical SHAPES')
after_hashes = protected_hashes()
changed = sorted(k for k in set(before_hashes)|set(after_hashes) if before_hashes.get(k)!=after_hashes.get(k))
report={'researcher_created':True,'harness_version':'Tessl-domain-v1.0','measured_at_utc':datetime.now(timezone.utc).isoformat(),
        'seed':SEED,'source_root':str(root),'mechanism':'Real TestClient HTTP, native controller/store, domain logic and serializer. Explicit controlled states; no generated source edits.',
        'isolated_rows_note':'S2-06/07 use pre-completed settled rows and canonical O, not reachable ordinary gameplay.',
        'results':records,'passed':sum(r['status']=='pass' for r in records),'failed':sum(r['status']=='fail' for r in records),
        'source_and_coverage_unchanged':not changed,'changed_protected_files':changed,'protected_hashes_before':before_hashes,
        'protected_hashes_after':after_hashes,'harness_sha256':digest(Path(__file__))}
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':report['passed'],'failed':report['failed'],'source_and_coverage_unchanged':not changed,'output':str(output)}))
sys.exit(0 if report['failed']==0 and not changed else 1)
