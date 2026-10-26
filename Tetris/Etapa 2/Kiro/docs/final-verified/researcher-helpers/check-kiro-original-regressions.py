"""Researcher execution of untouched original Stage 1 tests against Stage 2 app.

Writes evidence under Stage2/Kiro/docs/acceptance/original-stage1 only. Original
tests run in place with bytecode, pytest cache and plugin autoload disabled.
Stage 2 app is explicitly imported and its real path asserted before pytest.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

STAGE=Path(__file__).resolve().parent.parent
TOOL=STAGE/'Kiro'
BACKEND=TOOL/'backend'
ORIGINAL=STAGE.parent/'Etapa 1'/'Kiro'/'backend'/'tests'
OUT=TOOL/'docs'/'acceptance'/'original-stage1'
PYTHON=BACKEND/'.venv'/'Scripts'/'python.exe'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def app_hashes():
    return {str(p.relative_to(TOOL)):digest(p) for p in sorted((BACKEND/'app').rglob('*.py'))}


def child():
    sys.path.insert(0,str(BACKEND))
    import app
    import app.main
    import pytest
    actual=Path(app.main.__file__).resolve()
    if not actual.is_relative_to(BACKEND.resolve()):
        raise RuntimeError('Original-test check did not import the Stage 2 application')
    results=[]
    collection=[]
    class EvidencePlugin:
        def pytest_collection_modifyitems(self,items):
            collection.extend({'nodeid':item.nodeid,'test_file':str(item.path),
                               'test_module_file':str(item.module.__file__),
                               'test_function_code_filename':str(item.obj.__code__.co_filename)} for item in items)
        def pytest_runtest_logreport(self,report):
            if report.when=='call' or (report.failed and report.when!='call'):
                results.append({'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome,
                                'failure':str(report.longrepr) if report.failed else None})
    argv=['-q','--import-mode=importlib','-p','no:cacheprovider','-o','addopts=',
          '-c',str(BACKEND/'pytest.ini'),'--rootdir='+str(BACKEND),
          str(ORIGINAL/'test_api.py'),str(ORIGINAL/'test_rules.py')]
    code=pytest.main(argv,plugins=[EvidencePlugin()])
    loaded={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
            if (name=='app' or name.startswith('app.')) and getattr(module,'__file__',None)}
    report={'researcher_created':True,'pytest_argv':argv,'pytest_exit_code':int(code),
            'actual_app_main_file':str(actual),'actual_loaded_app_modules':loaded,
            'all_loaded_app_modules_from_stage2':all(Path(path).is_relative_to(BACKEND.resolve()) for path in loaded.values()),
            'python_pycache_prefix':sys.pycache_prefix,'python_dont_write_bytecode':sys.dont_write_bytecode,
            'all_collected_tests_from_original_source':all(Path(row['test_function_code_filename']).resolve().is_relative_to(ORIGINAL.resolve()) for row in collection),
            'collected_test_count':len(collection),'collection':collection,'results':results,
            'passed':sum(r['outcome']=='passed' for r in results),'failed':sum(r['outcome']=='failed' for r in results)}
    (OUT/'original-tests-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return int(code)


def main():
    if '--child' in sys.argv:
        raise SystemExit(child())
    OUT.mkdir(parents=True,exist_ok=True)
    tests=[ORIGINAL/'__init__.py',ORIGINAL/'test_api.py',ORIGINAL/'test_rules.py']
    tests_before={str(p):digest(p) for p in tests}
    before=app_hashes()
    started=datetime.now(timezone.utc).isoformat()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prior=[OUT/name for name in ['original-tests-results.json','original-tests-run.json','stdout.log','stderr.log'] if (OUT/name).exists()]
    if prior:
        archive=OUT/'previous-runs'/stamp
        archive.mkdir(parents=True,exist_ok=True)
        for path in prior:(archive/path.name).write_bytes(path.read_bytes())
    command=[str(PYTHON),'-B',str(Path(__file__).resolve()),'--child']
    environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
                 'PYTHONPYCACHEPREFIX':str(OUT/'unused-pycache-prefix'),
                 'PYTHONPATH':str(BACKEND)}
    tick=time.monotonic()
    with (OUT/'stdout.log').open('w',encoding='utf-8') as stdout,(OUT/'stderr.log').open('w',encoding='utf-8') as stderr:
        process=subprocess.run(command,cwd=BACKEND,env=environment,stdout=stdout,stderr=stderr)
    tests_after={str(p):digest(p) for p in tests}
    after=app_hashes()
    result=json.loads((OUT/'original-tests-results.json').read_text()) if (OUT/'original-tests-results.json').exists() else {}
    run={'researcher_created':True,'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),
         'duration_seconds':round(time.monotonic()-tick,3),'argv':command,'cwd':str(BACKEND),'exit_code':process.returncode,
         'environment_controls':{k:environment[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONPATH','PYTHONPYCACHEPREFIX']},
         'original_test_hashes_before':tests_before,'original_test_hashes_after':tests_after,
         'original_tests_unchanged':tests_before==tests_after,'stage2_app_hashes_before':before,'stage2_app_hashes_after':after,
         'candidate_source_stable_during_check':before==after,'provisional_while_generation_active':True,
         'scope':'Untouched Stage1 test expectations executed against explicitly imported Stage2 application; external researcher regression evidence',
         'cache_policy':'Python -B and PYTHONDONTWRITEBYTECODE; pytest -p no:cacheprovider; plugin autoload disabled; no coverage report modified'}
    (OUT/'original-tests-run.json').write_text(json.dumps(run,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'test_exit_code':process.returncode,'passed':result.get('passed'),'failed':result.get('failed'),
                      'collected':result.get('collected_test_count'),'actual_app_main_file':result.get('actual_app_main_file'),
                      'all_loaded_app_modules_from_stage2':result.get('all_loaded_app_modules_from_stage2'),
                      'original_tests_unchanged':run['original_tests_unchanged'],'candidate_source_stable_during_check':run['candidate_source_stable_during_check']},indent=2))


if __name__=='__main__':main()
