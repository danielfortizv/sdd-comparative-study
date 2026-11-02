"""Researcher orchestration of authorized external QA; no power or app edits."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

SHARED = Path(__file__).resolve().parent
ROOT = SHARED.parent / 'Kiro'
DOCS = ROOT / 'docs'
STATE = DOCS / 'qa-sequence-status.json'


def save(status, **extra):
    STATE.write_text(json.dumps({'researcher_created': True,
        'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'status': status,
        'scope': 'Authorized external QA orchestration; app/test/spec changes exclusively through Kiro',
        **extra}, indent=2) + '\n', encoding='utf-8')


def call(name, *args):
    with (DOCS / f'qa-sequence-{name}.log').open('ab') as stream:
        result = subprocess.run([sys.executable, str(SHARED / (name + '.py')), *args],
                                stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'{name} exit {result.returncode}')


try:
    if (DOCS / '05-qa.started.json').exists():
        raise RuntimeError('05 already started; refusing duplicate invocation')
    save('waiting_for_04_checkpoint', label='05-qa')
    deadline = time.monotonic() + 3600
    while True:
        state = json.loads((DOCS / 'authorized-sequence-status.json').read_text(encoding='utf-8'))
        if state['status'] == 'implementation_invocation_closed_independent_acceptance_pending':
            break
        if state['status'] == 'attention_required':
            raise RuntimeError('04 orchestration requires attention; no QA prompt sent')
        if time.monotonic() > deadline:
            raise RuntimeError('04 checkpoint wait expired; no QA prompt sent')
        time.sleep(2)
    run = json.loads((DOCS / '04-implement.run.json').read_text(encoding='utf-8'))
    if run.get('exit_code') != 0 or run.get('prompt_result', {}).get('stopReason') != 'end_turn':
        raise RuntimeError('04 did not close normally')
    if not (DOCS / 'implementation-04/manifest.json').is_file():
        raise RuntimeError('04 source/spec/evidence checkpoint missing')
    call('run-kiro-race-harness')
    race = json.loads((DOCS / 'acceptance/hook-races-run.json').read_text(encoding='utf-8'))
    if race['tests']['total'] != 3 or not race['source_hashes_unchanged'] or not race['lcov_hash_unchanged']:
        raise RuntimeError('External harness did not validate a stable candidate')
    target = DOCS / 'quality-before-05'
    target.mkdir()
    names = ['stage2-backend-coverage.log', 'stage2-backend-result.json',
        'stage2-frontend-test.log', 'stage2-frontend-build.log', 'stage2-frontend-result.json',
        'stage2-npm-audit.json', 'stage2-npm-audit-production.json', 'coverage.xml',
        'scan-command.json', 'report-task.txt', 'sonar-verification.json',
        'sonar-exact-task.json', 'sonar-exact-quality-gate.json', 'sonar-summary.json',
        'sonar-metrics.json', 'sonar-open-issues.json', 'sonar-scan.log',
        'BROWSER_04_PROVISIONAL.md', 'acceptance-api-04-provisional.json',
        'acceptance-contract-04-provisional-v1_2.json']
    for name in names:
        if (DOCS / name).is_file():
            shutil.copy2(DOCS / name, target / name)
    for name in ['acceptance', 'sonar-attempt-1-fail', 'sonar-attempt-2-fail']:
        if (DOCS / name).is_dir():
            shutil.copytree(DOCS / name, target / name)
    shutil.copy2(ROOT / 'frontend/vite.config.ts', target / 'frontend-vite.config.ts')
    shutil.copy2(ROOT / 'frontend/coverage/lcov.info', target / 'frontend-lcov.info')
    manifest = [{'path': p.relative_to(target).as_posix(), 'bytes': p.stat().st_size,
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest().upper()}
        for p in sorted(target.rglob('*')) if p.is_file()]
    (target / 'manifest.json').write_text(json.dumps({'researcher_created': True,
        'purpose': 'Immutable pre-QA quality/acceptance evidence, separate from implementation-04 source snapshot',
        'files': manifest}, indent=2) + '\n', encoding='utf-8')
    save('qa_running', label='05-qa', previous_snapshot='implementation-04',
         pre_qa_evidence='quality-before-05/manifest.json', race_result=race['tests'])
    call('run-kiro-acp', '--label', '05-qa', '--phase', 'clarify', '--prompt-file',
         str(DOCS / '05-qa.prompt.txt'), '--execute', '--allow-tools')
    call('archive-kiro-transcripts')
    call('audit-kiro-inputs')
    call('audit-kiro-questions')
    call('collect-kiro-metrics')
    call('snapshot-kiro', '--label', 'qa-05')
    save('qa_invocation_closed_independent_acceptance_pending', label='05-qa')
except Exception as error:
    save('attention_required', reason=str(error), note='No direct app/test/spec repair or power action performed')
    raise
