"""BMAD-specific scopes, shared validated CLI counter parser, no application import."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,hashlib,os,re
stage=Path(__file__).resolve().parent.parent;root=stage/'Bmad Method';docs=root/'docs';base=stage.parent/'Etapa 1'/'Bmad Method'
spec=importlib.util.spec_from_file_location('research_measurements',stage/'shared/collect-tessl-metrics.py');lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
lib.DOCS=docs;lib.CURRENT=root;lib.BASE=base;lib.RUN_CATEGORIES={};lib.QA_INTENTS={};lib.load_classifications()
skip={'node_modules','.venv','venv','dist','build','coverage','__pycache__','.pytest_cache','.git','docs','.sonar','.sonar-user-home'}
def select(start,source_root,extensions,mode=None):
 result={}
 if not start.exists():return result
 for folder,dirs,names in os.walk(start,followlinks=False):
  dirs[:]=[n for n in dirs if n not in skip and not (Path(folder)/n).is_symlink() and not(mode=='inherited' and Path(folder)==start and n=='stage2')]
  for n in names:
   p=Path(folder)/n
   if p.suffix not in extensions or p.is_symlink():continue
   if mode in ('inherited','native') and (n.startswith('.') or n.startswith(('review-','validation-','lint-'))):continue
   result[p.relative_to(source_root).as_posix()]=p
 return result
def source(r):return {**select(r/'backend',r,lib.SOURCE_EXTS),**select(r/'frontend',r,lib.SOURCE_EXTS)}
before=source(base);after=source(root)
oldspec=select(base/'_bmad-output',base,{'.md'},'inherited');copy=select(root/'_bmad-output',root,{'.md'},'inherited');new=select(root/'_bmad-output/stage2',root,{'.md'},'native')
allnative=select(root/'_bmad-output/stage2',root,{'.md','.yaml','.json','.html'})
diag={n:p for n,p in allnative.items() if n not in new}
catalog=lib.transcript_catalog();runs=[];open_runs=[]
for p in sorted(docs.glob('*.run.json')):
 d=json.loads(p.read_text(encoding='utf-8-sig'));runs.append({**d,'classification':lib.classification(d),'tokens':lib.stats_for_run(d,catalog),'tool_actions':lib.cli_tool_actions(d),'metadata_sha256':hashlib.sha256(p.read_bytes()).hexdigest().upper()})
closed={x['label'] for x in runs}
for p in sorted(docs.glob('*.started.json')):
 d=json.loads(p.read_text(encoding='utf-8-sig'))
 if d['label'] not in closed:open_runs.append({**d,'classification':lib.classification(d),'state':'pending','tokens':{'model_started_observed':None},'note':'Not included in closed usage/time totals.'})
known={k:sum(x['tokens'][k] for x in runs if x['tokens'].get(k) is not None) for k in ['input_tokens','cached_tokens','output_tokens','thought_tokens','api_requests','api_errors','api_successful_requests']}
manifest=json.loads((docs/'baseline-copy-manifest.json').read_text());original_bad=[x['path'] for x in manifest['files'] if hashlib.sha256((base/x['path']).read_bytes()).hexdigest().upper()!=x['sha256']]
ids=[]
for n,p in new.items():
 if p.name=='prd.md':ids+=re.findall(r'^\s*(?:-\s*)?\*\*(FR-\d+)\s*:',p.read_text(encoding='utf-8-sig'),re.M)
result={'researcher_created':True,'tool':'Bmad Method Stage2','measured_at_utc':datetime.now(timezone.utc).isoformat(),'source_scope':'Own backend/frontend source including tests and source-like configuration; dependencies/builds/cache/evidence excluded. BOM stripped, LF normalized, physical lines/Unicodecharacters; density=lines/files, notquality.','native_spec_scope':'Principal nativeStage2Markdown under _bmad-output/stage2, excluding dotmemlogs/review-/validation-/lint- diagnostics. InheritedsixMarkdown tracked separately; YAML/status/reviews counted separately as workflow artifacts.','source_baseline':lib.counts(before),'source_current':lib.counts(after),'source_change':lib.diff(before,after),'spec_stage1':lib.counts(oldspec),'spec_stage1_copy':lib.counts(copy),'spec_stage1_copy_change':lib.diff(oldspec,copy),'spec_stage2':lib.counts(new),'workflow_artifacts':lib.counts(diag),'declared_new_prd_functional_ids':sorted(set(ids),key=lambda x:int(x.split('-')[-1])),'identifier_scope':'Declaration syntax candidates only; atomicity/quality not inferred from a count.','baseline_integrity':{'original_stage1_unchanged':not original_bad,'original_hash_mismatches':original_bad},'runs':runs,'unclosed_invocation_labels':[x['label'] for x in open_runs],'open_runs':open_runs,'known_duration_seconds':round(sum(x['duration_seconds'] for x in runs),3),'known_tokens':{k:known[k] for k in ['input_tokens','cached_tokens','output_tokens','thought_tokens']},'known_api_totals':{k:known[k] for k in ['api_requests','api_errors','api_successful_requests']},'unknown_counter_runs':[x['label'] for x in runs if x['tokens'].get('input_tokens') is None],'recorded_main_response_count':sum(x['tokens'].get('recorded_response_count') or 0 for x in runs),'correction_counts':lib.correction_counts(runs,open_runs),'counter_scope':'Closed CLI stats include all models/roles; prompt input includes cache, do not add cache again. Absent counters remain unknown. JSONLresponses deduplicated by response identity/time interval, no duplicate archive count. Process exit0/tool success are not feature/test acceptance. Model-authored documenttimestamps are not measured execution time.','parser_provenance':{'shared_counter_parser':'collect-tessl-metrics.py (researcher infrastructure only)','sha256':hashlib.sha256((stage/'shared/collect-tessl-metrics.py').read_bytes()).hexdigest().upper(),'no_other_tool_app_or_spec_imported':True}}
result['unknown_api_counter_runs']=[x['label'] for x in runs if x['tokens'].get('api_requests') is None]
result['api_counter_scope']='Known sums only; runs listed in unknown_api_counter_runs are excluded, not counted as zero.'
for stem in ('implementation-04-initial-partial','implementation-initial','implementation-03-initial'):
 snap=docs/stem/'files'
 if snap.exists():result['qa_change_from_initial_implementation']={'snapshot':stem,'source':lib.diff(source(snap),after),'native_spec':lib.diff(select(snap/'_bmad-output/stage2',snap,{'.md'},'native'),new)};break
target=docs/'metrics.json';temp=docs/'metrics.json.tmp';temp.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');temp.replace(target)
print(json.dumps({'closed_invocations':len(runs),'pending':result['unclosed_invocation_labels'],'known_duration_seconds':result['known_duration_seconds'],'known_tokens':result['known_tokens'],'known_api_totals':result['known_api_totals'],'source':{k:v for k,v in result['source_current'].items() if k!='per_file'},'native_specs':{k:v for k,v in result['spec_stage2'].items() if k!='per_file'},'original_unchanged':not original_bad},indent=2))
