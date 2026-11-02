"""Researcher record of actual CUA observations; does not automate or alter the app."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent.parent / 'Spec Kit'
docs = root / 'docs'
observations = [
    ('UI-01', 'Started a real local game; HUD score=0, lines=0, level=1, gravity=500 ms; Hold EMPTY and enabled. DOM contained exactly 200 board cells, 20 row indices and 10 column indices.'),
    ('UI-02', 'Clicked Hold (C Key): EMPTY disappeared, a canonical occupied Hold preview appeared, and button became disabled until lock. Screenshot records the occupied slot and disabled button.'),
    ('UI-03', 'Restarted to a fresh session with EMPTY Hold; pressed lowercase c; Hold became occupied and disabled.'),
    ('UI-04', 'Restarted independently to EMPTY Hold; pressed shift+c (uppercase C); Hold became occupied and disabled.'),
    ('UI-05', 'Restarted with O at columns 4/5; Left moved its visible columns to 3/4; Right returned them to 4/5. Gravity continued during observation. Down was accepted during play with zero HUD score; exact soft-drop behavior is additionally covered by generated tests, not inferred from wall-clock row changes.'),
    ('UI-06', 'Allowed normal gravity to fill the board: GAME_OVER appeared with modal, Hold disabled, Play Again and Restart Game controls. No board or API state was injected.'),
    ('UI-07', 'Clicked the modal Restart Game: new session ID 9c7b220e..., PLAYING, score/lines=0, level=1, 500 ms, EMPTY Hold and enabled button.'),
    ('UI-08', 'After QA4 optional-chain production changes were applied through Vite HMR, observed GAME_OVER and captured it again; restarted into ac08740a..., captured initial counters/EMPTY Hold, clicked Hold and captured occupied/disabled Hold. Independently restarted into 8239edd4... and ad027087... to repeat c and C successfully. Earlier QA16 observations and images remain retained separately.'),
]
captures = [
    ('app-final-initial.jpg', 'Actual local UI after QA4: initial counters, board, next preview and empty Hold. Gravity continued while capturing.'),
    ('app-final-hold.jpg', 'Actual local UI after QA4: occupied Hold, next preview, board and disabled Hold control before the next lock.'),
    ('app-final-game-over.jpg', 'Actual local UI after QA4: naturally reached game-over state and restart modal.'),
]
data = {
    'status': 'pass',
    'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'url': 'http://127.0.0.1:5173/',
    'method': 'Actual CUA browser interaction and read-only rendered DOM inspection; no fetch mocks, hidden React state access or injected game fixtures.',
    'observations': [{'id': i, 'status': 'pass', 'detail': d} for i, d in observations],
    'captures': [{'path': 'screenshots/' + f, 'caption': c, 'kind': 'actual_ui'} for f, c in captures],
    'frontend_source_files': [{'path': p.relative_to(root).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest().upper()} for p in sorted((root / 'frontend/src').rglob('*')) if p.is_file()],
    'limitations': [
        'Manual browser play did not reach level 2 or the 100 ms floor. Exact timer boundaries and asynchronous request ownership require the fake-clock/deferred-request suite.',
        'Three- and four-row scoring are isolated-domain fixtures, not manually reached browser clears.',
        'Separate derived quality/usage panels must be labeled as derived views of retained raw outputs, never native Sonar UI or terminal screenshots.',
    ],
}
for capture in data['captures']:
    if not (docs / capture['path']).is_file():
        raise SystemExit('Missing actual screenshot: ' + capture['path'])
out = docs / 'browser-evidence.json'
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(out)
