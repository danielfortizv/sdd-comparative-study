"""Researcher-only Kiro baseline environment and verification commands.

Replicates Kiro's own working Stage 1 Python 3.10.11 package inventory and
installs the unchanged npm lock. Does not author application/tests/specs,
change dependency manifests, use Google/Gemini, or invoke Git/Kiro/Sonar.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

STAGE = Path(__file__).resolve().parent.parent
CASE = STAGE.parent
BASE = CASE / "Etapa 1" / "Kiro"
TOOL = STAGE / "Kiro"
BACKEND = TOOL / "backend"
FRONTEND = TOOL / "frontend"
DOCS = TOOL / "docs"
ORIGINAL_PYTHON = BASE / "backend" / ".venv" / "Scripts" / "python.exe"
PYTHON310 = Path("C:/Users/Kevin Alvarez/AppData/Local/Programs/Python/Python310/python.exe")
VENV = BACKEND / ".venv"
LOCAL_PYTHON = VENV / "Scripts" / "python.exe"
NPM = shutil.which("npm.cmd")
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_CACHE_DIR": str(DOCS / "pip-cache"), "npm_config_cache": str(DOCS / "npm-cache")}
COMMANDS: list[dict] = []


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(name: str, value: object) -> None:
    (DOCS / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(argv: list[str], log_name: str, cwd: Path, allowed_exits=(0,)) -> subprocess.CompletedProcess:
    start = now()
    tick = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (DOCS / log_name).write_text(result.stdout, encoding="utf-8")
    COMMANDS.append({"argv": argv, "cwd": str(cwd), "started_at_utc": start, "ended_at_utc": now(), "duration_seconds": round(time.monotonic() - tick, 3), "exit_code": result.returncode, "log_path": str(DOCS / log_name)})
    save("baseline-environment-commands.json", COMMANDS)
    if result.returncode not in allowed_exits:
        raise RuntimeError(f"Command failed ({result.returncode}); see {DOCS / log_name}")
    return result


def inventory(executable: Path, log: str) -> dict:
    code = "import importlib.metadata,json,platform,sys; print(json.dumps({'python':platform.python_version(),'executable':sys.executable,'packages':sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda x:x['name'].lower())}))"
    return json.loads(run([str(executable), "-B", "-c", code], log, BACKEND).stdout)


def verify_bytes(stage: str) -> dict:
    manifest = json.loads((DOCS / "baseline-copy-manifest.json").read_text(encoding="utf-8"))
    rows = []
    for row in manifest["files"]:
        relative = row["path"]
        copied_hash = hashlib.sha256((TOOL / relative).read_bytes()).hexdigest().upper()
        original_hash = hashlib.sha256((BASE / relative).read_bytes()).hexdigest().upper()
        rows.append({"path": relative, "sha256": copied_hash, "matches_baseline": copied_hash == row["sha256"], "stage1_unchanged": original_hash == row["sha256"]})
    result = {"researcher_created": True, "measured_at_utc": now(), "checkpoint": stage, "status": "pass" if all(row["matches_baseline"] and row["stage1_unchanged"] for row in rows) else "fail", "files": rows}
    save("baseline-hash-verification-" + stage + ".json", result)
    if result["status"] != "pass":
        raise RuntimeError("A copied baseline or Stage 1 byte hash changed")
    return result


def main() -> None:
    if VENV.exists() or (FRONTEND / "node_modules").exists():
        raise RuntimeError("Requires fresh Stage 2 environment directories; refusing overwrite")
    if not ORIGINAL_PYTHON.is_file() or not PYTHON310.is_file() or not NPM:
        raise RuntimeError("Original Python, Python3.10.11 runtime and npm.cmd must exist")
    verify_bytes("before-environment")
    original = inventory(ORIGINAL_PYTHON, "baseline-original-python-inventory.json")
    if original["python"] != "3.10.11":
        raise RuntimeError("Unexpected original Kiro Python version")
    pins = "\n".join(f"{row['name']}=={row['version']}" for row in original["packages"]) + "\n"
    pin_file = DOCS / "baseline-original-python-pins.txt"
    pin_file.write_text(pins, encoding="utf-8")
    run([str(PYTHON310), "-B", "-m", "venv", str(VENV)], "baseline-python-venv-create.log", BACKEND)
    run([str(LOCAL_PYTHON), "-B", "-m", "pip", "install", "--requirement", str(pin_file)], "baseline-python-install.log", BACKEND)
    current = inventory(LOCAL_PYTHON, "baseline-current-python-inventory.json")
    original_after = inventory(ORIGINAL_PYTHON, "baseline-original-python-inventory-after.json")
    canonical = lambda value: {(row["name"].lower().replace("_", "-"), row["version"]) for row in value["packages"]}
    environment = {"researcher_created": True, "measured_at_utc": now(), "original_python": original, "stage2_python": current, "same_python_version": original["python"] == current["python"], "exact_package_inventory_match": canonical(original) == canonical(current), "original_inventory_unchanged": canonical(original) == canonical(original_after), "new_coverage_packages_added": [], "coverage_availability": any(row["name"].lower() == "pytest-cov" for row in current["packages"]), "historical_environment_difference": "Historical Stage 1 docs/backend-test.log used the shared Python3.12.14 toolchain; the tool's own existing venv uses Python3.10.11. This baseline replicates the latter exact inventory and declares the difference.", "app_test_spec_dependency_manifest_edits": [], "pin_file": str(pin_file), "pin_sha256": hashlib.sha256(pin_file.read_bytes()).hexdigest().upper(), "environment_controls": {key: ENV[key] for key in ("PYTHONDONTWRITEBYTECODE", "PIP_DISABLE_PIP_VERSION_CHECK", "PIP_CACHE_DIR", "npm_config_cache")}}
    save("baseline-python-environment.json", environment)
    if not all(environment[key] for key in ("same_python_version", "exact_package_inventory_match", "original_inventory_unchanged")):
        raise RuntimeError("Recreated environment does not exactly match Stage 1 inventory")
    pytest_args = [str(LOCAL_PYTHON), "-B", "-m", "pytest", "-q"]
    if environment["coverage_availability"]:
        pytest_args.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=xml:" + str(DOCS / "baseline-coverage.xml")])
    backend = run(pytest_args, "baseline-backend-tests.log", BACKEND)
    save("baseline-backend-result.json", {"researcher_created": True, "measured_at_utc": now(), "exit_code": backend.returncode, "command": COMMANDS[-1], "coverage_xml_available": environment["coverage_availability"], "coverage_note": "No coverage package in the exact original venv; none installed for baseline" if not environment["coverage_availability"] else "Original instrumentation retained"})
    run([NPM, "ci"], "baseline-npm-ci.log", FRONTEND)
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    frontend_test = {"status": "unavailable", "reason": "Original Kiro frontend has no test script or frontend test framework; no script/framework added for baseline", "executed": False}
    if "test" in package.get("scripts", {}):
        tested = run([NPM, "test", "--", "--run"], "baseline-frontend-tests.log", FRONTEND)
        frontend_test = {"status": "pass", "exit_code": tested.returncode, "executed": True, "command": COMMANDS[-1]}
    build = run([NPM, "run", "build"], "baseline-frontend-build.log", FRONTEND)
    audit = run([NPM, "audit", "--json"], "baseline-npm-audit.json", FRONTEND, allowed_exits=(0, 1))
    save("baseline-frontend-result.json", {"researcher_created": True, "measured_at_utc": now(), "tests": frontend_test, "build_exit_code": build.returncode, "audit_exit_code": audit.returncode, "frontend_lcov_available": (FRONTEND / "coverage" / "lcov.info").is_file()})
    verified = verify_bytes("after-environment")
    print(json.dumps({"python": current["python"], "exact_packages": len(current["packages"]), "backend_exit_code": backend.returncode, "frontend_test": frontend_test, "build_exit_code": build.returncode, "audit_exit_code": audit.returncode, "coverage_xml_available": environment["coverage_availability"], "copied_file_hash_count": len(verified["files"]), "copied_and_stage1_hash_status": verified["status"]}, indent=2))


if __name__ == "__main__":
    main()
