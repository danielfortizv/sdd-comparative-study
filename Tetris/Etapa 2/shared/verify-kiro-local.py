"""Prepare/run one independent Kiro verification with isolated reports.

This researcher helper never installs dependencies, invokes a model or scans
Sonar. Running it is separate from preparing it. Every native invocation must
already be closed. Application/test/specification files are never edited here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

from kiro_research import DOCS, ROOT, configurations, digest, manifests, source_paths, spec_paths, stamp, write


def open_invocations():
    return sorted(p.name.removesuffix(".started.json") for p in DOCS.glob("*.started.json") if not (DOCS / (p.name.removesuffix(".started.json") + ".run.json")).is_file())


def protected_sources():
    paths = {**source_paths(ROOT), **spec_paths(ROOT), **configurations(ROOT), **manifests(ROOT)}
    for name in ("backend/requirements-dev.txt", "README.md", "backend/README.md", "frontend/README.md"):
        if (ROOT / name).is_file():
            paths[name] = ROOT / name
    return paths


def native_reports():
    # Direct native/research evidence is protected, while this helper's output
    # lives in a child directory. Historical snapshot trees are not traversed.
    paths = {p.relative_to(ROOT).as_posix(): p for p in DOCS.iterdir() if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".log", ".txt", ".xml"}}
    for name in ("backend/.coverage", "backend/coverage.xml"):
        if (ROOT / name).is_file():
            paths[name] = ROOT / name
    coverage = ROOT / "frontend/coverage"
    if coverage.exists():
        for path in coverage.rglob("*"):
            if path.is_file() and not path.is_symlink():
                paths[path.relative_to(ROOT).as_posix()] = path
    return paths


def hashes(paths):
    return {name: {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size} for name, path in sorted(paths.items())}


def changed(before, after):
    return sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))


def read_json(path):
    if not path.is_file():
        return {"status": "unavailable", "path": str(path), "reason": "file not emitted"}
    try:
        return {"status": "parsed", "path": str(path), "data": json.loads(path.read_text(encoding="utf-8-sig"))}
    except (ValueError, OSError) as exc:
        return {"status": "unparseable", "path": str(path), "reason": str(exc)}


def backend_coverage(path):
    if not path.is_file():
        return {"status": "unavailable", "reason": "XML not emitted", "path": str(path)}
    try:
        data = ET.parse(path).getroot()
        return {"status": "parsed", "path": str(path), "line_rate": float(data.attrib["line-rate"]), "lines_covered": int(data.attrib["lines-covered"]), "lines_valid": int(data.attrib["lines-valid"]), "branch_rate": float(data.attrib["branch-rate"]) if "branch-rate" in data.attrib else None, "branches_covered": int(data.attrib["branches-covered"]) if "branches-covered" in data.attrib else None, "branches_valid": int(data.attrib["branches-valid"]) if "branches-valid" in data.attrib else None, "sources": [s.text for s in data.findall("./sources/source")], "scope": "pytest-cov --cov=app; branch counters are interpreted only as emitted, not proof branch instrumentation enabled"}
    except (ValueError, KeyError, OSError, ET.ParseError) as exc:
        return {"status": "unparseable", "path": str(path), "reason": str(exc)}


def audit_summary(path):
    parsed = read_json(path)
    if parsed["status"] != "parsed":
        return parsed
    data = parsed.pop("data")
    parsed.update(vulnerabilities=data.get("metadata", {}).get("vulnerabilities"), dependency_counts=data.get("metadata", {}).get("dependencies"), error=data.get("error"), audit_report_version=data.get("auditReportVersion"))
    parsed["scope"] = "npm audit result from the current installed lock/dependency state; absent fields stay unknown"
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.label):
        raise ValueError("Use a lowercase safe label")
    pending = open_invocations()
    if pending:
        raise RuntimeError("Refusing verification while Kiro invocations remain open: " + ", ".join(pending))
    base = DOCS / "researcher-verification"
    out = base / args.label
    if not out.resolve().is_relative_to(base.resolve()) or out.exists():
        raise FileExistsError("Refusing unsafe path or overwrite")
    python = ROOT / "backend/.venv/Scripts/python.exe"
    npm = shutil.which("npm.cmd")
    node = shutil.which("node.exe") or shutil.which("node")
    if not python.is_file() or not npm or not node:
        raise RuntimeError("Existing Kiro venv, npm.cmd and node required; helper installs nothing")
    out.mkdir(parents=True)
    start = stamp()
    sources_before = hashes(protected_sources())
    reports_before = hashes(native_reports())
    write(out / "source-hashes-before.json", sources_before)
    write(out / "native-report-hashes-before.json", reports_before)
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", COVERAGE_FILE=str(out / ".coverage"))
    commands = []
    def execute(name, argv, cwd, role="verification"):
        pending_now = open_invocations()
        if pending_now:
            raise RuntimeError("New Kiro invocation appeared during verification: " + ", ".join(pending_now))
        stdout, stderr = out / f"{name}.stdout.txt", out / f"{name}.stderr.txt"
        row = {"name": name, "role": role, "argv": [str(a) for a in argv], "cwd": str(cwd), "started_at_utc": stamp(), "stdout": str(stdout), "stderr": str(stderr), "shell": False, "coverage_file_env": env["COVERAGE_FILE"]}
        wall = time.perf_counter()
        try:
            with stdout.open("xb") as a, stderr.open("xb") as b:
                result = subprocess.run(row["argv"], cwd=cwd, env=env, shell=False, stdout=a, stderr=b, timeout=1800)
            row["exit_code"] = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            row.update(exit_code=None, error=str(exc))
        row.update(ended_at_utc=stamp(), duration_seconds=round(time.perf_counter() - wall, 3))
        for path, key in ((stdout, "stdout_sha256"), (stderr, "stderr_sha256")):
            row[key] = digest(path.read_bytes()) if path.exists() else None
        commands.append(row)
        write(out / "commands.json", commands)
        return row
    failure = None
    try:
        execute("python-version", [python, "--version"], ROOT / "backend", "environment")
        execute("python-packages", [python, "-c", "import importlib.metadata as m,json,sys; print(json.dumps({'python':sys.version,'packages':{n:m.version(n) for n in ('pytest','pytest-cov','coverage','fastapi','httpx')}}))"], ROOT / "backend", "environment")
        execute("node-version", [node, "--version"], ROOT / "frontend", "environment")
        execute("npm-version", [npm, "--version"], ROOT / "frontend", "environment")
        execute("backend-tests", [python, "-m", "pytest", "tests", "-q", "--cov=app", "--cov-report=term-missing", "--cov-report=xml:" + str(out / "backend-coverage.xml")], ROOT / "backend")
        execute("frontend-tests", [npm, "test", "--", "--coverage", "--coverage.reportsDirectory=" + str(out / "frontend-coverage"), "--coverage.reporter=text", "--coverage.reporter=lcov", "--coverage.reporter=json-summary", "--reporter=json", "--outputFile=" + str(out / "frontend-test-results.json")], ROOT / "frontend")
        execute("frontend-build", [npm, "run", "build"], ROOT / "frontend")
        execute("npm-audit-all", [npm, "audit", "--json"], ROOT / "frontend")
        execute("npm-audit-production", [npm, "audit", "--json", "--omit=dev"], ROOT / "frontend")
    except Exception as exc:
        failure = str(exc)
    sources_after = hashes(protected_sources())
    reports_after = hashes(native_reports())
    write(out / "source-hashes-after.json", sources_after)
    write(out / "native-report-hashes-after.json", reports_after)
    source_changes, report_changes = changed(sources_before, sources_after), changed(reports_before, reports_after)
    test_json = read_json(out / "frontend-test-results.json")
    if test_json["status"] == "parsed":
        data = test_json.pop("data")
        test_json.update({key: data.get(key) for key in ("success", "numTotalTestSuites", "numPassedTestSuites", "numFailedTestSuites", "numTotalTests", "numPassedTests", "numFailedTests", "numPendingTests", "numTodoTests", "startTime")})
        test_json["scope"] = "Vitest JSON reporter; raw testResults retained in original report; counts are not acceptance-catalog coverage"
    cov_json = read_json(out / "frontend-coverage/coverage-summary.json")
    if cov_json["status"] == "parsed":
        cov_json["total"] = cov_json.pop("data").get("total")
    backend = backend_coverage(out / "backend-coverage.xml")
    audit_all = audit_summary(out / "npm-audit-all.stdout.txt")
    audit_production = audit_summary(out / "npm-audit-production.stdout.txt")
    frontend_lcov_exists = (out / "frontend-coverage/lcov.info").is_file()
    checks = [r for r in commands if r["role"] == "verification"]
    all_zero = len(checks) == 5 and all(r.get("exit_code") == 0 for r in checks)
    pending_after = open_invocations()
    evidence_parsed = backend["status"] == "parsed" and test_json["status"] == "parsed" and cov_json["status"] == "parsed" and frontend_lcov_exists and all(a["status"] == "parsed" and a.get("vulnerabilities") is not None and not a.get("error") for a in (audit_all, audit_production))
    status = "commands_passed_evidence_recorded" if all_zero and all(r.get("exit_code") == 0 for r in commands) and not failure and not source_changes and not report_changes and not pending_after and evidence_parsed else "verification_incomplete_or_failed"
    package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8-sig"))
    installed = {}
    for name in ("vitest", "@vitest/coverage-v8", "vite", "typescript", "react", "react-dom"):
        path = ROOT / "frontend/node_modules" / name / "package.json"
        installed[name] = json.loads(path.read_text(encoding="utf-8-sig")).get("version") if path.exists() else None
    summary = {"researcher_created": True, "label": args.label, "started_at_utc": start, "ended_at_utc": stamp(), "status": status, "error": failure, "all_five_verification_commands_exit_zero": all_zero, "commands": commands, "source_changes": source_changes, "preserved_native_report_changes": report_changes, "unclosed_invocation_labels_after": pending_after, "backend_coverage": backend, "frontend_tests": test_json, "frontend_coverage_summary": cov_json, "frontend_lcov": {"path": str(out / "frontend-coverage/lcov.info"), "exists": frontend_lcov_exists}, "npm_audit_all": audit_all, "npm_audit_production": audit_production, "frontend_declared_versions": {"dependencies": package.get("dependencies"), "devDependencies": package.get("devDependencies")}, "frontend_installed_versions": installed, "executable_paths": {"python": str(python), "node": node, "npm_cmd": npm}, "limits": ["No acceptance20 catalog/API/browser claim and no Sonar scan; those need separate evidence", "Coverage honors current native include/exclude configuration; hash captured; entry/glue exclusions must be disclosed", "Build output dist and tool caches may be regenerated; application/tests/specs/manifests and recorded native report paths must keep their hashes", "No installs, npmci, auditfix or manifest edits; failing commands are retained without automatic retry", "Per-command timeout1800s; a timeout/OS error leaves exit unknown and prevents pass status", "Audit exit1 is a recorded finding, not silently normalized to pass; raw JSON and full stderr retained", "All own coverage/report paths are isolated; COVERAGE_FILE and both frontend reporter directories never target native coverage", "This status describes executed commands and preserved evidence, not final application acceptance"]}
    write(out / "verification-summary.json", summary)
    print(json.dumps({"output": str(out), "status": status, "source_changes": source_changes, "native_report_changes": report_changes, "pending": pending_after}, ensure_ascii=False))
    return 0 if status == "commands_passed_evidence_recorded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
