"""Researcher-authored supplemental S2-16 contract check, shared across tools.

This supplements check_api.py v1.1; it does not change that checker's cases or
turn these HTTP controls into additional catalog requirements.
"""
import argparse
import atexit
import json
from datetime import datetime, timezone
from pathlib import Path

from check_api import call, check, board_valid

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
base = args.base_url.rstrip('/')
rows = []
complete = False
required = {'id', 'board', 'status', 'score', 'total_lines', 'level',
            'gravity_interval_ms', 'next_piece', 'hold_piece', 'can_hold'}


def write_report():
    result = {'version': '1.0', 'catalog_id': 'S2-16', 'base_url': base,
              'measured_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'pass' if complete else 'fail',
              'scope': 'supplemental endpoint/status/full-key checks; not extra catalog IDs',
              'controls': rows}
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


atexit.register(write_report)


def verify_state(state):
    check(required <= state.keys(), 'missing common state fields')
    check('activePiece' in state or 'active_piece' in state, 'missing legacy active field')
    check(board_valid(state), 'invalid 20x10 board')
    check(state['next_piece'] in set('IOTJLSZ'), 'invalid preview type')


status, state = call(base, 'POST', '/api/games')
check(status == 201, 'create must return 201')
verify_state(state)
game_id = state['id']
rows.append({'method': 'POST', 'route': '/api/games', 'http_status': status, 'status': 'pass'})
for method, suffix, body in [('GET', '', None), ('POST', '/move', {'direction': 'left'}),
                             ('POST', '/tick', None), ('POST', '/hold', None)]:
    status, state = call(base, method, '/api/games/' + game_id + suffix, body)
    check(status == 200, f'{method} {suffix} must return 200')
    verify_state(state)
    rows.append({'method': method, 'route': '/api/games/{id}' + suffix, 'http_status': status, 'status': 'pass'})
for method, suffix, body in [('GET', '', None), ('POST', '/move', {'direction': 'left'}),
                             ('POST', '/tick', None), ('POST', '/hold', None)]:
    status, _ = call(base, method, '/api/games/research-nonexistent-stage2-id' + suffix, body)
    check(status == 404, f'missing {method} {suffix} must return 404')
    rows.append({'method': method, 'route': '/api/games/{missing-id}' + suffix, 'http_status': status, 'status': 'pass'})
complete = True
