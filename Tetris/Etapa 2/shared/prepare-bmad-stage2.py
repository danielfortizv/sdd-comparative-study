"""Researcher-only exact own-baseline copy; no generated app/spec authorship."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,stat

stage=Path(__file__).resolve().parent.parent;base=stage.parent/'Etapa 1'/'Bmad Method';dest=stage/'Bmad Method'
if dest.exists():raise FileExistsError('Refusing to overwrite BMAD Stage2')
excluded={'node_modules','.venv','venv','dist','build','coverage','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.git','.sonar','.sonar-user-home','docs','render'}
secret={'.env','.coverage','credentials.json','oauth_creds.json','application_default_credentials.json','sonar-token.txt','auth.json','token.json'}
files=[];skipped=[]
def walk(p):
 rel=p.relative_to(base).as_posix()
 if p.is_symlink() or bool(p.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
  skipped.append({'path':rel,'reason':'reparse point not followed'});return
 if p.name in excluded or p.name in secret or p.name.startswith('.env.') or p.name.endswith(('.pyc','.tsbuildinfo')):
  skipped.append({'path':rel,'reason':'dependency/build/cache/evidence/secret/generated-render exclusion'});return
 if p.is_dir():
  for x in sorted(p.iterdir()):walk(x)
 elif p.is_file():files.append(p)
 else:raise RuntimeError('Nonregular baseline path')
for name in ['backend','frontend','_bmad','_bmad-output','.agents','.gemini','.geminiignore']:
 p=base/name
 if p.exists():walk(p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def count(paths):
 rows={}
 for p in paths:
  s=p.read_text(encoding='utf-8-sig');rows[p.relative_to(base).as_posix()]={'lines':len(s.splitlines()),'nonblank_lines':sum(bool(x.strip()) for x in s.splitlines()),'characters':len(s),'sha256':sha(p)}
 n=len(rows);lines=sum(x['lines'] for x in rows.values())
 return {'files':n,'lines':lines,'nonblank_lines':sum(x['nonblank_lines'] for x in rows.values()),'characters':sum(x['characters'] for x in rows.values()),'lines_per_file':round(lines/n,2) if n else 0,'per_file':rows}
source=[p for p in files if p.relative_to(base).parts[0] in ('backend','frontend') and p.suffix in {'.py','.ts','.tsx','.js','.jsx','.css','.html'}]
spec=[p for p in files if p.relative_to(base).parts[0]=='_bmad-output' and p.suffix=='.md' and not p.name.startswith('.')]
manifest=[{'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
dest.mkdir()
for p,row in zip(files,manifest):
 target=dest/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 if sha(target)!=row['sha256']:raise RuntimeError('Copy hash mismatch')
docs=dest/'docs';docs.mkdir()
(docs/'baseline-copy-manifest.json').write_text(json.dumps({'researcher_created':True,'created_at_utc':datetime.now(timezone.utc).isoformat(),'source':str(base),'destination':str(dest),'files':manifest,'skipped':skipped},indent=2)+'\n')
(docs/'baseline-metrics.json').write_text(json.dumps({'source':count(source),'specification':count(spec),'spec_scope':'All six inherited principal Markdown artifacts; dot memlogs and sprintYAML tracked separately; no generated Stage2 spec yet.','source_scope':'Own backend/frontend source, tests and source-like configuration; no dependency/build/cache/evidence.'},indent=2)+'\n')
# Researcher integration routing, explicitly kept separate from feature specs.
for n in ['_bmad/bmm/config.yaml','_bmad/core/config.yaml','.gemini/settings.json']:
 p=dest/n;backup=docs/'baseline-integration'/n;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
 if p.suffix=='.yaml':
  s=p.read_text(encoding='utf-8-sig').replace('"{project-root}/_bmad-output/planning-artifacts"','"{project-root}/_bmad-output/stage2/planning-artifacts"').replace('"{project-root}/_bmad-output/implementation-artifacts"','"{project-root}/_bmad-output/stage2/implementation-artifacts"').replace('output_folder: _bmad-output','output_folder: _bmad-output/stage2')
  p.write_text(s,encoding='utf-8')
 else:
  d=json.loads(p.read_text());d['modelConfigs']={'customAliases':{n:{'modelConfig':{'model':'gemini-3.5-flash'}} for n in ['loop-detection','loop-detection-double-check','llm-edit-fixer','next-speaker-checker']}};p.write_text(json.dumps(d,indent=2)+'\n')
changes=[{'path':n,'before_sha256':sha(docs/'baseline-integration'/n),'after_sha256':sha(dest/n)} for n in ['_bmad/bmm/config.yaml','_bmad/core/config.yaml','.gemini/settings.json']]
(docs/'integration-setup.json').write_text(json.dumps({'researcher_created':True,'reason':'Separate Stage2 native output from immutable inherited specs, pin main/utility model selection; no app/test/feature edits.','bmad_version':'6.12.0','cli_version':'0.60.0','project':'project-d419b4aa-7c3b-4fde-932','new_native_scope':'_bmad-output/stage2','changes':changes},indent=2)+'\n')
for folder in ['planning-artifacts','implementation-artifacts']:(dest/'_bmad-output/stage2'/folder).mkdir(parents=True)
print(json.dumps({'copied_files':len(files),'source':{k:v for k,v in count(source).items() if k!='per_file'},'inherited_specs':{k:v for k,v in count(spec).items() if k!='per_file'},'destination':str(dest)}))
