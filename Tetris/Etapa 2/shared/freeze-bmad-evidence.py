"""Immutable BMAD candidate/spec checkpoint, with hash manifest and no credentials."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,shutil,os
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
stage=Path(__file__).resolve().parent.parent;root=stage/'Bmad Method';docs=root/'docs';dest=docs/a.label
if dest.exists():raise FileExistsError('Refusing existing snapshot')
paths=set()
baseline=json.loads((docs/'baseline-copy-manifest.json').read_text())
for x in baseline['files']:paths.add(root/x['path'])
for parent in [root/'backend',root/'frontend']:
 if parent.exists():
  for source in parent.rglob('*'):
   if not source.is_file():continue
   relative=source.relative_to(parent)
   if any(part in {'.venv','node_modules','dist','coverage','__pycache__','.pytest_cache','.vite'} for part in relative.parts):continue
   if source.suffix in {'.py','.ts','.tsx','.css','.html','.json','.md','.txt','.toml','.ini','.yaml','.yml','.xml','.lcov'}:paths.add(source)
for parent in [root/'_bmad-output/stage2',docs/'transcripts-archive',docs/'sonar-baseline',docs/'acceptance',docs/'screenshots',docs/'evidence-view',docs/'build-04',docs/'validation']:
 if parent.exists():paths.update(p for p in parent.rglob('*') if p.is_file())
for parent in [docs/'sonar-attempts',*(p for p in docs.glob('build-*') if p.is_dir())]:
 if parent.exists():paths.update(p for p in parent.rglob('*') if p.is_file())
for path in [root/'backend/.coveragerc',root/'frontend/coverage/lcov.info',root/'.sonar/report-task.txt']:
 if path.exists():paths.add(path)
paths.update(p for p in docs.iterdir() if p.is_file() and p.suffix in {'.json','.txt','.md','.log','.xml'})
dest.mkdir();rows=[]
for source in sorted(paths):
 if not source.exists():continue
 if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):raise RuntimeError('Snapshot path escaped tool root')
 relative=source.relative_to(root);target=dest/'files'/relative;target.parent.mkdir(parents=True,exist_ok=True);data=source.read_bytes();target.write_bytes(data);rows.append({'path':target.relative_to(dest).as_posix(),'sha256':hashlib.sha256(data).hexdigest().upper(),'bytes':len(data)})
(dest/'manifest.json').write_text(json.dumps({'researcher_created':True,'label':a.label,'created_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Own baseline plus all current application source/tests/manifests, nativeStage2 artifacts, current integration config, scoped acceptance/screenshots/buildlogs and immutable transcripts; no dependencies/cache/credentials/Git or recursive prior snapshots. Snapshot alone does not prove acceptance.','files':rows},indent=2)+'\n')
print(json.dumps({'snapshot':str(dest),'files':len(rows)}))
