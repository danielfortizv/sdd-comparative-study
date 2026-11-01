"""Researcher sequence: enforce reviewed Spec checkpoint before authorized Kiro implementation."""
from pathlib import Path
import subprocess
import sys
import time
import json
import hashlib
from datetime import datetime, timezone

SHARED=Path(__file__).resolve().parent
DOCS=SHARED.parent/'Kiro/docs'
ROOT=DOCS.parent
STATE=DOCS/'authorized-sequence-status.json'

def save(status, **extra):
    STATE.write_text(json.dumps({'researcher_created':True,'updated_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':status,'scope':'Researcher orchestration; no direct app/test/spec edits',**extra},indent=2)+'\n',encoding='utf-8')

def call(name,*args):
    log=DOCS/f'sequence-{name}.log'
    with log.open('ab') as stream:
        result=subprocess.run([sys.executable,str(SHARED/(name+'.py')),*args],stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode: raise RuntimeError(f'{name} exit {result.returncode}; see {log.name}')

try:
    save('waiting_for_native_spec_review',depends_on='03-native-spec-review.run.json')
    deadline=time.monotonic()+14400
    target=DOCS/'03-native-spec-review.run.json'
    while not target.exists():
        if time.monotonic()>deadline: raise RuntimeError('Native spec review timeout; implementation not started')
        time.sleep(2)
    review=json.loads(target.read_text(encoding='utf-8'))
    if review.get('exit_code')!=0 or review.get('verified_configuration')!={'mode':'spec','model':'auto'} or review.get('prompt_result',{}).get('stopReason')!='end_turn':
        raise RuntimeError('Native Spec/Auto review did not complete successfully; implementation not started')
    manifest=json.loads((DOCS/'baseline-copy-manifest.json').read_text(encoding='utf-8'))
    mismatch=[]
    for row in manifest['files']:
        p=ROOT/row['path']
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest().upper()!=row['sha256']:
            mismatch.append(row['path'])
    if mismatch: raise RuntimeError('Spec-only phase changed inherited files: '+str(mismatch))
    feature=ROOT/'.kiro/specs/tetris-stage2-option-a'
    for name in ['requirements.md','design.md','tasks.md']:
        if not (feature/name).exists() or (feature/name).stat().st_size<100: raise RuntimeError('Incomplete native feature artifacts')
    if '- [x]' in (feature/'tasks.md').read_text(encoding='utf-8').lower(): raise RuntimeError('Spec-only checklist claims implementation completion')
    design=(feature/'design.md').read_text(encoding='utf-8')
    if not all(term in design for term in ['450','pytest-cov','total_lines']): raise RuntimeError('Reviewed design is missing required corrections')
    call('archive-kiro-transcripts')
    call('audit-kiro-inputs')
    audit=json.loads((DOCS/'input-audit.json').read_text(encoding='utf-8'))
    entry=next((r for r in audit['runs'] if r['label']=='03-native-spec-review'),None)
    if not entry or not entry.get('complete_seed_in_effective_submission'): raise RuntimeError('Full effective seed for native review not verified')
    call('audit-kiro-questions')
    call('collect-kiro-metrics')
    if not (DOCS/'specification-03-native/manifest.json').exists():
        call('snapshot-kiro','--label','specification-03-native')
    save('native_spec_checkpoint_verified',baseline_files_verified=len(manifest['files']))
    # User cancelled automatic suspension and explicitly requested continuing Kiro.
    # Kiro uses its own authenticated Student credits; this sequence performs no power action.
    call('run-kiro','--phase','implement','--label','04-implement','--clarification-file',str(SHARED/'kiro-implementation-controls.txt'),'--prepare-only')
    save('implementation_running',label='04-implement',transport='Official Kiro ACP, independently verified Spec/Auto before prompt')
    call('run-kiro-acp','--label','04-implement','--phase','implement','--prompt-file',str(DOCS/'04-implement.prompt.txt'),'--execute','--allow-tools')
    call('archive-kiro-transcripts')
    call('audit-kiro-inputs')
    call('audit-kiro-questions')
    call('collect-kiro-metrics')
    call('snapshot-kiro','--label','implementation-04')
    save('implementation_invocation_closed_independent_acceptance_pending',label='04-implement',note='Do not interpret CLI closure as final acceptance or publish a completed result without independent verification')
except Exception as error:
    save('attention_required',reason=str(error),note='No direct app/test/spec fix performed by researcher sequence')
    raise
