"""Researcher-only visual acceptance fixture; original app/routes/rules unchanged.

First two creates (React development StrictMode) start one real lock away from
9->10 lines. Later creates use untouched defaults, allowing a real UI Restart.
Do not use this fixture server as the normal delivered game server.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent / 'Kiro'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise RuntimeError('Refusing to overwrite browser fixture trace')
    sys.path.insert(0, str(ROOT/'backend'))
    import uvicorn
    from app import store
    from app.main import app
    from app.domain.models import ActivePiece, empty_board

    def record(kind, **values):
        with args.output.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'researcher_created':True,
                'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                'monotonic_seconds':time.monotonic(),'kind':kind,**values})+'\n')

    def state(game):
        return {name:getattr(game,name) for name in
            ['id','status','score','total_lines','level','gravity_interval_ms','next_type','hold_type','can_hold']} | {
            'active_type':game.active.type if game.active else None,
            'active_origin':game.active.origin if game.active else None}

    original_create = store.create
    creates = itertools.count(1)

    def controlled_create(seed=store.DEFAULT_SEED):
        game = original_create(seed)
        ordinal = next(creates)
        controlled = ordinal <= 2
        if controlled:
            game.board = empty_board()
            game.board[19] = ['I']*10
            game.board[19][3] = game.board[19][4] = None
            game.active = ActivePiece(type='O', origin=(18,3), cells=[(18,3),(18,4),(19,3),(19,4)])
            game.score = 0
            game.total_lines = 9
            game.level = 1
            game.gravity_interval_ms = 500
        record('create', ordinal=ordinal, controlled_fixture=controlled,
               seed=seed, state=state(game))
        return game

    store.create = controlled_create

    @app.middleware('http')
    async def observe(request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        parts = request.url.path.strip('/').split('/')
        game = store.get(parts[2]) if len(parts)>=3 and parts[:2]==['api','games'] else None
        record('http', method=request.method, path=request.url.path,
               status=response.status_code, duration_ms=round((time.monotonic()-started)*1000,3),
               state=state(game) if game else None)
        return response

    paths = list((ROOT/'backend/app').rglob('*.py'))
    record('fixture_start', scope='Runtime test data only; no app/routes/rules files edited',
           mechanism='First2creates: canonical O at(18,3), bottom row filled except3/4, total_lines9, level1, gravity500. Real tick/lock/score performs crossing. Create3+ uses untouched default.',
           source_hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in paths},
           researcher_fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper())
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False)


if __name__ == '__main__':
    main()
