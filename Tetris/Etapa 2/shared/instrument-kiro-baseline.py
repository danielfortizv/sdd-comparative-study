"""Researcher coverage-only addition to Kiro's recreated Stage 2 venv.

Installs coverage==7.16.2 separately from the original 23-package inventory.
Does not modify requirements, app/tests/specs or Stage 1.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

STAGE = Path(__file__).resolve().parent.parent
TOOL = STAGE / "Kiro"
BACKEND = TOOL / "backend"
DOCS = TOOL / "docs"
PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"
ORIGINAL = STAGE.parent / "Etapa 1" / "Kiro"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_CACHE_DIR": str(DOCS / "pip-cache")}
commands = []


def run(args, log):
    start = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    result = subprocess.run([str(PYTHON), "-B", *args], cwd=BACKEND, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (DOCS / log).write_text(result.stdout, encoding="utf-8")
    commands.append({"argv": [str(PYTHON), "-B", *args], "cwd": str(BACKEND), "started_at_utc": start, "ended_at_utc": datetime.now(timezone.utc).isoformat(), "duration_seconds": round(time.monotonic()-tick, 3), "exit_code": result.returncode, "log_path": str(DOCS / log)})
    (DOCS / "baseline-coverage-commands.json").write_text(json.dumps(commands, indent=2)+"\n", encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Coverage setup command failed: {log}")
    return result


inventory_code = "import importlib.metadata,json; print(json.dumps(sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda x:x['name'].lower())))"
before = json.loads(run(["-c", inventory_code], "baseline-coverage-packages-before.json").stdout)
run(["-m", "pip", "install", "--no-deps", "coverage==7.16.2"], "baseline-coverage-install.log")
after = json.loads(run(["-c", inventory_code], "baseline-coverage-packages-after.json").stdout)
canonical = lambda rows: {(row["name"].lower().replace("_", "-"), row["version"]) for row in rows}
added = canonical(after) - canonical(before)
removed = canonical(before) - canonical(after)
if added != {("coverage", "7.16.2")} or removed:
    raise RuntimeError("Unexpected package changes during instrumentation")
run(["-m", "coverage", "run", "--source=app", "-m", "pytest", "-q"], "baseline-backend-coverage-tests.log")
run(["-m", "coverage", "report", "--show-missing"], "baseline-backend-coverage-report.log")
run(["-m", "coverage", "xml", "-o", str(DOCS / "baseline-coverage.xml")], "baseline-coverage-xml.log")
manifest = json.loads((DOCS / "baseline-copy-manifest.json").read_text(encoding="utf-8"))
hashes = [{"path": row["path"], "stage2_matches_baseline": hashlib.sha256((TOOL/row["path"]).read_bytes()).hexdigest().upper()==row["sha256"], "stage1_unchanged": hashlib.sha256((ORIGINAL/row["path"]).read_bytes()).hexdigest().upper()==row["sha256"]} for row in manifest["files"]]
if not all(row["stage2_matches_baseline"] and row["stage1_unchanged"] for row in hashes):
    raise RuntimeError("Source/spec/manifest hashes changed during instrumentation")
report = {"researcher_created": True, "measured_at_utc": datetime.now(timezone.utc).isoformat(), "purpose": "Explicitly authorized researcher instrumentation; not a Kiro implementation change", "original_package_count": len(before), "instrumented_package_count": len(after), "added_packages": [{"name": name, "version": version} for name,version in sorted(added)], "removed_or_changed_original_packages": [], "before_packages": before, "after_packages": after, "requirements_app_tests_specs_edits": [], "coverage_xml": "docs/baseline-coverage.xml", "coverage_xml_sha256": hashlib.sha256((DOCS/"baseline-coverage.xml").read_bytes()).hexdigest().upper(), "frontend_lcov_available": False, "baseline_hashes": hashes, "commands": commands}
(DOCS / "baseline-coverage-instrumentation.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
print(json.dumps({key:report[key] for key in ("original_package_count","instrumented_package_count","added_packages","removed_or_changed_original_packages","coverage_xml","coverage_xml_sha256","frontend_lcov_available")},indent=2))
