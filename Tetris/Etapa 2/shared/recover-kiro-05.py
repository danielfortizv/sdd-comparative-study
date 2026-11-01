"""Researcher recovery record for an absent interrupted transport, not a run result."""
import hashlib
import json
from pathlib import Path
from kiro_research import DOCS, ROOT, load, source_paths, stamp, write

target = DOCS / '05-qa.run.json'
if target.exists():
    raise RuntimeError('05 closure already exists; refusing overwrite')
record = load(DOCS / '05-qa.started.json')
observed = stamp()
record.update(
    researcher_reconstructed_closure=True,
    ended=None, duration_seconds=None, exit_code=None, transport_exit_code=None,
    observation_end_upper_bound_utc=observed,
    actual_process_end_time_utc=None,
    closure_status='interrupted_transport_absent_at_recovery',
    closure_evidence='Researcher inspected Windows process inventory on October23; owned native PID and driver/orchestration commands were absent. No native runFinished or wrapper result remained.',
    interruption_cause='unknown; execution stopped during the gap after last retained activity on October21, no cause inferred',
    timing_scope='Observed absence bounds the retained native interval only. Actual end/duration/exit status are unknown; the off-line gap is not billed or agent elapsed time.',
    usage_scope='Final native usage summary absent unless explicitly found in retained records; account balance delta is not attributed to this run.',
)
write(target, record)
previous = load(DOCS / 'qa-sequence-status.json')
write(DOCS / 'qa-sequence-interrupted-05-before-recovery.json', previous)
write(DOCS / 'qa-sequence-status.json', {'researcher_created': True,
    'updated_at_utc': observed, 'status': 'interrupted_transport_absent_at_recovery',
    'label': '05-qa', 'next_step': 'Fresh immutable06 retry of the same external QA intent; preserve full seed and native spec-first revision'})
classes = load(DOCS / 'run-classifications.json')
classes['05-qa'].update(work_completion_status='interrupted before implementation; actual end/duration/exit and final consumption unknown')
classes['06-qa-retry'] = {'category':'postimplementation_external_correction',
    'reason':'Fresh retry of interrupted05, same external QA intent and full frozen seed. Complete native specification revision before application/tests/security/coverage fixes.',
    'work_completion_status':'prepared; no completed acceptance claimed',
    'qa_intent_id':'kiro-stage2-qa-01', 'retry_of':'05-qa', 'resumed':False}
write(DOCS / 'run-classifications.json', classes)
old = load(DOCS / 'metrics.json')['source_current']['per_file']
current = {name: hashlib.sha256(path.read_bytes()).hexdigest().upper()
           for name,path in source_paths(ROOT).items()}
changed = [name for name in sorted(set(old)|set(current))
           if old.get(name,{}).get('sha256') != current.get(name)]
write(DOCS / '05-interruption-recovery.json', {'researcher_created':True,
    'observed_at_utc':observed,'native_process_confirmed_absent':True,
    'ended':None,'duration_seconds':None,'exit_code':None,
    'source_changed_since04':changed,
    'source_file_count_current':len(current),
    'note':'Feature specs may contain partial native05 revisions; source comparison does not include those Markdown files. Original05 prompt/streams are preserved.'})
print(json.dumps({'recovered':'05-qa','unknown':['actual end','wall duration','exit code','final consumption'],
    'source_changed_since04':changed}))
