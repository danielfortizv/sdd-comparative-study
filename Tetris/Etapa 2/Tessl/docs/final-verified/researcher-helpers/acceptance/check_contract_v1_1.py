"""Researcher-authored supplemental S2-16 contract check, shared across tools.

Version 1.1 imports check_api_v1_2 and adds --created-status (default 201,
Tessl 200) while recording actual statuses without normalization. The original
check_contract.py v1.0 and check_api.py v1.1 remain unchanged.
These HTTP controls are supplemental evidence for S2-16, not extra catalog IDs.
"""
import argparse
import atexit
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from check_api_v1_2 import call, check, board_valid

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--created-status', type=int, choices=(200, 201), default=201,
                    help="Exact expected create HTTP status from this tool's own Stage 1 contract; default 201, Tessl 200")
args = parser.parse_args()
base = args.base_url.rstrip('/')
rows = []
complete = False
required = {'id', 'board', 'status', 'score', 'total_lines', 'level',
            'gravity_interval_ms', 'next_piece', 'hold_piece', 'can_hold'}


def write_report():
    result = {'version': '1.1', 'researcher_created': True,
              'catalog_id': 'S2-16', 'base_url': base,
              'measured_at_utc': datetime.now(timezone.utc).isoformat(),
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
              'imported_api_checker_version': '1.2',
              'imported_api_checker_sha256': hashlib.sha256(Path(__file__).with_name('check_api_v1_2.py').read_bytes()).hexdigest().upper(),
              'parent_version': '1.0',
              'parent_version_sha256': 'D56C6289EC858B160A467676B44DCEDE45DC4D852D439F9213D63EC109FB45A4',
              'expected_create_http_status': args.created_status,
              'observed_create_http_status': next((row.get('actual_http_status') for row in rows if row['route'] == '/api/games'), None),
              'http_status_normalization': False,
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


def request(method, path, route, expected_status, body=None, state_expected=True):
    row = {'method': method, 'route': route, 'requested_path': path,
           'expected_http_status': expected_status, 'actual_http_status': None,
           'status': 'pending'}
    rows.append(row)
    try:
        status, state = call(base, method, path, body)
        row['actual_http_status'] = status
        # Retain the original row key as an alias for consumers of v1.0 output.
        row['http_status'] = status
        check(status == expected_status, f'{method} {route} HTTP {status}; expected {expected_status}')
        if state_expected:
            verify_state(state)
        row['status'] = 'pass'
        return state
    except Exception as error:
        row['status'] = 'fail'
        row['detail'] = f'{type(error).__name__}: {error}'
        raise


state = request('POST', '/api/games', '/api/games', args.created_status)
game_id = state['id']
for method, suffix, body in [('GET', '', None), ('POST', '/move', {'direction': 'left'}),
                             ('POST', '/tick', None), ('POST', '/hold', None)]:
    request(method, '/api/games/' + game_id + suffix, '/api/games/{id}' + suffix, 200, body)
for method, suffix, body in [('GET', '', None), ('POST', '/move', {'direction': 'left'}),
                             ('POST', '/tick', None), ('POST', '/hold', None)]:
    request(method, '/api/games/research-nonexistent-stage2-id' + suffix,
            '/api/games/{missing-id}' + suffix, 404, body, state_expected=False)
complete = True
