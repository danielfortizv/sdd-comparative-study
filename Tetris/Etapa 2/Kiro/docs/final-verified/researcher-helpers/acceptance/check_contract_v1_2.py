"""Supplemental S2-16 HTTP contract checks, researcher instrumentation v1.2.

Same nine controls as v1.1, with report writing in a normal finally block.
This avoids reliance on __file__ during interpreter shutdown. Earlier versions
remain immutable. Exact status codes are observed, never normalized.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from check_api_v1_2 import board_valid, call, check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--created-status', type=int, choices=(200, 201), default=201)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    source = Path(__file__).resolve()
    rows = []
    complete = False
    required = {'id', 'board', 'status', 'score', 'total_lines', 'level',
                'gravity_interval_ms', 'next_piece', 'hold_piece', 'can_hold'}

    def request(method, path, route, expected_status, body=None, state_expected=True):
        row = {'method': method, 'route': route, 'requested_path': path,
               'expected_http_status': expected_status, 'actual_http_status': None,
               'status': 'pending'}
        rows.append(row)
        try:
            status, state = call(base, method, path, body)
            row.update(actual_http_status=status, http_status=status)
            check(status == expected_status, f'{method} {route} HTTP {status}; expected {expected_status}')
            if state_expected:
                check(required <= state.keys(), 'missing common state fields')
                check('activePiece' in state or 'active_piece' in state, 'missing legacy active field')
                check(board_valid(state), 'invalid 20x10 board')
                check(state['next_piece'] in set('IOTJLSZ'), 'invalid preview type')
            row['status'] = 'pass'
            return state
        except Exception as error:
            row.update(status='fail', detail=f'{type(error).__name__}: {error}')
            raise

    try:
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
    finally:
        sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest().upper()
        result = {
            'version': '1.2', 'researcher_created': True, 'catalog_id': 'S2-16',
            'base_url': base, 'measured_at_utc': datetime.now(timezone.utc).isoformat(),
            'checker_sha256': sha(source),
            'imported_api_checker_version': '1.2',
            'imported_api_checker_sha256': sha(source.with_name('check_api_v1_2.py')),
            'parent_version': '1.1',
            'parent_version_sha256': sha(source.with_name('check_contract_v1_1.py')),
            'instrumentation_change': 'Normal finally writes report before interpreter shutdown; same nine controls.',
            'expected_create_http_status': args.created_status,
            'observed_create_http_status': next((r['actual_http_status'] for r in rows if r['route'] == '/api/games'), None),
            'http_status_normalization': False,
            'status': 'pass' if complete else 'fail',
            'scope': 'Supplemental endpoint/status/full-key checks; not extra catalog IDs.',
            'controls': rows,
        }
        Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': result['status'], 'controls': len(rows), 'output': args.output}))


if __name__ == '__main__':
    main()
