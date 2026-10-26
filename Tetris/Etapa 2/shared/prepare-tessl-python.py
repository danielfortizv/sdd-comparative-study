"""Researcher environment setup; copy no application/test/specification content.

Inspect the original Tessl venv read-only, recreate its exact installed package
versions in a fresh Stage 2 venv, preserve the failed shared-Python baseline,
then run the unchanged Stage 1 tests with coverage instrumentation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

STAGE = Path(__file__).resolve().parent.parent
CASE = STAGE.parent
TOOL = STAGE / "Tessl"
DOCS = TOOL / "docs"
BACKEND = TOOL / "backend"
ORIGINAL_PYTHON = CASE / "Etapa 1" / "Tessl" / "backend" / ".venv" / "Scripts" / "python.exe"
BASE_PYTHON = CASE / "Etapa 1" / "_toolchain" / "venv" / "Scripts" / "python.exe"
VENV = BACKEND / ".venv"
LOCAL_PYTHON = VENV / "Scripts" / "python.exe"
COMMANDS: list[dict] = []
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_CACHE_DIR": str(DOCS / "pip-cache")}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(name: str, value: object) -> None:
    (DOCS / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(args: list[str], log_name: str, cwd: Path = BACKEND) -> subprocess.CompletedProcess:
    started = now()
    tick = time.monotonic()
    process = subprocess.run(args, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (DOCS / log_name).write_text(process.stdout, encoding="utf-8")
    COMMANDS.append({"argv": args, "cwd": str(cwd), "started_at_utc": started, "ended_at_utc": now(), "duration_seconds": round(time.monotonic() - tick, 3), "exit_code": process.returncode, "log_path": str(DOCS / log_name)})
    save("baseline-python-setup-commands.json", COMMANDS)
    if process.returncode:
        raise RuntimeError(f"Command failed ({process.returncode}); see {DOCS / log_name}")
    return process


def inventory(executable: Path, log: str) -> dict:
    code = "import importlib.metadata,json,platform,sys; print(json.dumps({'python':platform.python_version(),'executable':sys.executable,'packages':sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda x:x['name'].lower())}))"
    return json.loads(run([str(executable), "-B", "-c", code], log).stdout)


def verify_baseline() -> dict:
    metrics = json.loads((DOCS / "baseline-metrics.json").read_text(encoding="utf-8"))
    rows = []
    for scope in ("source", "specification"):
        for relative, baseline in metrics[scope]["per_file"].items():
            path = TOOL / relative
            actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            rows.append({"scope": scope, "path": relative, "sha256": actual, "matches_copied_stage1": actual == baseline["sha256"]})
    result = {"researcher_created": True, "measured_at_utc": now(), "status": "pass" if all(row["matches_copied_stage1"] for row in rows) else "fail", "files": rows}
    save("baseline-pre-gemini-hash-verification.json", result)
    if result["status"] != "pass":
        raise RuntimeError("Source or specification baseline changed before Gemini generation")
    return result


def main() -> None:
    if VENV.exists():
        raise RuntimeError("Only a NEW Stage 2 virtual environment is supported; refusing overwrite")
    for stem, suffix in (("coverage", "log"), ("result", "json")):
        original = DOCS / f"baseline-backend-{stem}.{suffix}"
        archived = DOCS / f"baseline-shared-python-failed-{stem}.{suffix}"
        if original.exists():
            if archived.exists():
                raise RuntimeError(f"Refusing to overwrite failed baseline evidence: {archived}")
            shutil.copy2(original, archived)
    source_inventory = inventory(ORIGINAL_PYTHON, "baseline-original-python-inventory.json")
    if source_inventory["python"] != "3.12.14":
        raise RuntimeError("Unexpected original Python version")
    pins = "\n".join(f"{row['name']}=={row['version']}" for row in source_inventory["packages"]) + "\n"
    requirement_path = DOCS / "baseline-original-python-pins.txt"
    requirement_path.write_text(pins, encoding="utf-8")
    run([str(BASE_PYTHON), "-B", "-m", "venv", str(VENV)], "baseline-python-venv-create.log")
    run([str(LOCAL_PYTHON), "-B", "-m", "pip", "install", "--requirement", str(requirement_path)], "baseline-python-install.log")
    current_inventory = inventory(LOCAL_PYTHON, "baseline-current-python-inventory.json")
    original_after = inventory(ORIGINAL_PYTHON, "baseline-original-python-inventory-after.json")
    canonical = lambda data: {(row["name"].lower().replace("_", "-"), row["version"]) for row in data["packages"]}
    identical = canonical(source_inventory) == canonical(current_inventory)
    original_unchanged = canonical(source_inventory) == canonical(original_after)
    manifest = {"researcher_created": True, "measured_at_utc": now(), "original_python": source_inventory, "stage2_python": current_inventory, "same_python_version": source_inventory["python"] == current_inventory["python"], "exact_package_inventory_match": identical, "original_inventory_unchanged": original_unchanged, "new_coverage_packages_added": [], "coverage_note": "coverage and pytest-cov were already present in the original Tessl environment and are replicated at their exact versions", "app_test_spec_dependency_manifest_edits": [], "pin_file": str(requirement_path), "pin_sha256": hashlib.sha256(requirement_path.read_bytes()).hexdigest().upper(), "environment_controls": {key: ENV[key] for key in ("PYTHONDONTWRITEBYTECODE", "PIP_DISABLE_PIP_VERSION_CHECK", "PIP_CACHE_DIR")}, "source_hash_verification": verify_baseline()}
    save("baseline-python-environment.json", manifest)
    if not identical or not original_unchanged or not manifest["same_python_version"]:
        raise RuntimeError("Recreated environment does not exactly match original")
    test = run([str(LOCAL_PYTHON), "-B", "-m", "pytest", "-q", "--cov=app", "--cov-report=term-missing", "--cov-report=xml:" + str(DOCS / "baseline-coverage.xml")], "baseline-backend-coverage.log")
    result = {"researcher_created": True, "measured_at_utc": now(), "exit_code": test.returncode, "command": COMMANDS[-1], "coverage_xml": str(DOCS / "baseline-coverage.xml"), "environment_manifest": str(DOCS / "baseline-python-environment.json"), "prior_shared_python_failure_preserved": True, "source_hash_verification": verify_baseline()}
    save("baseline-backend-result.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "source_hash_verification"}, indent=2))


if __name__ == "__main__":
    main()
