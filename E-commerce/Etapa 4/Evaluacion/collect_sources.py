"""Hash raw empirical sources without calculating study metrics."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

stage = Path(__file__).resolve().parent.parent
evidence = stage / 'Evaluacion'
records = []
def add(path, role, tool=None):
    if path.is_file():
        content = path.read_bytes()
        records.append(dict(path=path.relative_to(stage).as_posix(), tool=tool,
                            role=role, bytes=len(content), sha256=hashlib.sha256(content).hexdigest()))

add(evidence/'SEED-4.md', 'common-seed')
add(evidence/'broker-runtime-metadata.json', 'driver-infrastructure')
add(evidence/'driver-interventions.md', 'driver-provenance')
add(evidence/'driver-scheduling.jsonl', 'driver-scheduling-events')
add(evidence/'driver-final-validation-metadata.json', 'independent-artifact-infrastructure-validation')
add(evidence/'driver-final-validation.txt', 'independent-validation-output')
for tool in ['OpenSpec', 'Kiro', 'Tessl', 'Spec Kit']:
    for path in sorted((evidence/tool).rglob('*')):
        if not path.is_file():
            continue
        name = path.name
        role = ('submitted-prompt' if 'prompt' in name else
                'inherited-source-hashes' if name == 'starting-snapshot.json' else
                'run-provenance' if 'metadata' in name else
                'native-session-events' if path.suffix == '.jsonl' else
                'kiro-session-archive' if path.suffix == '.zip' else
                'independent-local-validation' if 'validation' in name else
                'raw-console-errors' if 'stderr' in name else
                'raw-console-statistics-and-response')
        add(path, role, tool)
    for path in (stage/tool).rglob('*'):
        if path.name not in {'coverage.xml', 'lcov.info'}:
            continue
        if any(part in {'.venv', 'node_modules', '.git'} for part in path.parts):
            continue
        add(path, 'raw-coverage', tool)

manifest = dict(collected_utc=datetime.now(timezone.utc).isoformat(), stage=4,
    scope='Option A: independent services and real RabbitMQ moderation events',
    notes=[
        'No cost, quality, coverage percentage or interaction metrics calculated.',
        'Native raw sessions and console outputs may overlap; ZIP and uncompressed Kiro events are duplicates, not separate usage.',
        'Interrupted sessions can lack final console statistics. Missing telemetry is unavailable, not zero.',
        'Gemini auxiliary model roles must remain separate from the fixed main model.',
        'Follow-up prompts preserve operational recovery and corrections; inspect all attempts.',
        'Local WSL RabbitMQ provisioning and TCP forwarding were driver work, outside tool application generation.',
        'Docker and remote CI execution are not claimed; consult raw native logs and validation records.'
    ], sources=records)
(evidence/'source-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(f'Inventoried {len(records)} empirical source files.')
