"""Freeze an allowlisted local evidence set without replacing existing files.

Researcher infrastructure only. Does not run application tests, scanners, servers,
model sessions, or Drive operations. The report helper is invoked with --check.
"""

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess


target = Path(__file__).resolve().parent
docs = target.parent
tool = docs.parent
stage2 = tool.parent
case = stage2.parent
shared = stage2 / "shared"
python = case / "Etapa 1/_toolchain/venv/Scripts/python.exe"
origins = {}

if target.name != "final-verified" or not (target / "manifest.json").is_file():
    raise ValueError("Expected the newly created snapshot helper directory")
if (target / "evidence-manifest.json").exists():
    raise FileExistsError("Refusing to replace a finalized evidence manifest")

credential_patterns = {
    "sonar_token": r"\bsqu_[A-Za-z0-9]{20,}\b",
    "google_api_key": r"\bAIza[0-9A-Za-z_-]{20,}\b",
    "bearer_literal": r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{20,}",
    "secret_literal": r'''(?i)(?:SONAR_TOKEN|GOOGLE_API_KEY|GEMINI_API_KEY|access_token|refresh_token|client_secret)["']?\s*[:=]\s*["'][^"'$\s][^"'\s]{12,}''',
}


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def put(source, relative, origin_base):
    source = source.resolve()
    origin_base = origin_base.resolve()
    destination = target / relative
    if not source.is_relative_to(origin_base) or not destination.resolve().is_relative_to(target):
        raise ValueError("Evidence path escapes its declared root")
    if not source.is_file():
        raise FileNotFoundError(str(source))
    if any(part.lower() in {"node_modules", ".git", ".venv", "venv"} for part in source.relative_to(origin_base).parts):
        raise ValueError("Dependency or Git directory is not an evidence source")
    data = source.read_bytes()
    if source.suffix.lower() in {".json", ".jsonl", ".py", ".md", ".txt", ".log", ".xml", ".info"}:
        text = data.decode("utf-8-sig", errors="replace")
        for pattern_name, pattern in credential_patterns.items():
            if re.search(pattern, text):
                raise ValueError(f"Potential credential pattern {pattern_name} in {source.name}; no value printed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != data:
            raise FileExistsError(f"Refusing to replace different frozen content: {relative}")
    else:
        shutil.copy2(source, destination)
    if source.read_bytes() != data or destination.read_bytes() != data:
        raise ValueError(f"Source/copy changed during snapshot: {relative}")
    origins[destination.relative_to(target).as_posix()] = {
        "base": "tool_root" if origin_base == tool else "stage2_shared",
        "path": source.relative_to(origin_base).as_posix(),
    }


main_docs = [
    "FINAL_REPORT.md", "metrics.json", "input-audit.json", "input-audit.log",
    "question-audit.json", "question-audit.md", "environment.json",
    "seed-submitted.txt", "report-input-contract.md",
    "measurement-schema-verification.json", "verification-commands.json",
    "backend-coverage.log", "frontend-test-coverage.log", "frontend-build.log",
    "npm-audit.json", "coverage.xml", "acceptance-api.json",
    "acceptance-contract.json", "acceptance-matrix.json",
    "acceptance-provenance.json", "acceptance-review-notes.md",
    "browser-evidence.json", "qa09-final-review.md", "qa12-final-review.md",
    "qa16-final-review.md", "qa17-final-review.md", "QA_FINDINGS.md",
    "sonar-exact-task.json", "sonar-exact-quality-gate.json",
    "sonar-exact-verification.log", "sonar-task.json", "sonar-quality-gate.json",
    "sonar-summary.json", "sonar-metrics.json", "sonar-issues.json",
    "sonar-open-issues.json", "sonar-scan.log", "sonar-verification.json",
    "13-input-replay-verification.json",
]
for name in main_docs:
    put(docs / name, name, tool)

for pattern in (
    "*.run.json", "*.started.json", "*.prompt.txt", "*.request.txt",
    "*.stdout.json", "*.stderr.txt", "*-metric-verification.json",
):
    for source in sorted(docs.glob(pattern)):
        put(source, source.name, tool)

# Only the content-addressed transcript archive is allowed: never gemini-home,
# .gemini authentication/configuration files, dependency trees, or credential stores.
for source in sorted((docs / "transcripts-archive").glob("*")):
    if source.is_file() and (source.name == "manifest.json" or source.suffix == ".jsonl"):
        put(source, f"transcripts-archive/{source.name}", tool)

for source in sorted((docs / "question-audit-through08").rglob("*")):
    if source.is_file():
        put(source, source.relative_to(docs).as_posix(), tool)

for source in sorted((docs / "bertopic-corpus/final").rglob("*")):
    if source.is_file():
        put(source, source.relative_to(docs).as_posix(), tool)

for folder in ("sonar-baseline", "sonar-initial", "sonar-qa16-gate-error"):
    for source in sorted((docs / folder).rglob("*")):
        if source.is_file() and source.suffix.lower() in {".json", ".log", ".txt", ".xml", ".info"}:
            put(source, source.relative_to(docs).as_posix(), tool)

browser = json.loads((docs / "browser-evidence.json").read_text(encoding="utf-8-sig"))
captures = browser["captures"]
if len(captures) != 7:
    raise ValueError("Expected the agreed seven final capture files")
for capture in captures:
    put(docs / capture["path"], capture["path"], tool)
    for raw_path in capture.get("raw_sources", []):
        put(docs / raw_path, raw_path, tool)

put(tool / "frontend/coverage/lcov.info", "coverage-inputs/frontend/lcov.info", tool)
put(tool / ".sonar/report-task.txt", "sonar-report-task.txt", tool)
for name in (
    "seed.md", "collect-spec-kit-metrics.py", "audit-spec-kit-inputs.py",
    "build-spec-kit-report.py", "snapshot-spec-kit.py",
    "acceptance/catalog.md", "acceptance/check_api.py", "acceptance/check_contract.py",
):
    put(shared / name, f"researcher-shared/{name}", shared)

# The root researcher owns these living notes through publication/PDF QA; they
# intentionally are not copied here while their publication status is changing.
check_started = datetime.now(timezone.utc).isoformat()
check = subprocess.run(
    [str(python), str(shared / "build-spec-kit-report.py"), "--check"],
    cwd=case, text=True, capture_output=True,
)
check_stdout = json.loads(check.stdout)
if check.returncode != 0 or check_stdout != {"status": "ready", "final_report_written": False}:
    raise ValueError("Current report readiness check did not pass")
readiness = {
    "started_at_utc": check_started,
    "ended_at_utc": datetime.now(timezone.utc).isoformat(),
    "command": ["Etapa 1/_toolchain/venv/Scripts/python.exe", "Etapa 2/shared/build-spec-kit-report.py", "--check"],
    "working_directory_base": "case_root", "exit_code": check.returncode,
    "stdout": check_stdout, "stderr": check.stderr,
    "final_report_sha256": digest((docs / "FINAL_REPORT.md").read_bytes()),
    "scope": "Researcher evidence readiness only; no app tests/scanners/servers/Drive operations were run by this snapshot step.",
}
(target / "report-readiness-check.json").write_text(json.dumps(readiness, indent=2) + "\n", encoding="utf-8")

notes = """# Final verified local evidence snapshot

This researcher snapshot freezes the completed local Spec Kit Stage 2 experiment,
independent verification and exact Sonar result after invocation 17. The original
`manifest.json` from the snapshot helper remains unchanged. The supplementary
`evidence-manifest.json` hashes every retained file except itself, using paths
relative to this directory and an explicit source-root label.

No application tests, scanner, server, model session or Drive write was run by
this assembly step. `report-readiness-check.json` records the read-only --check.
Dependencies, authentication/credential stores, caches and Git are excluded.
Researchers may not replace this directory to hide later changes.

The final Drive appendix and exported-PDF layout QA were pending at snapshot
assembly time. Living RESEARCH_LOG.md/MEASUREMENT_COMPLETENESS.md are intentionally
outside this frozen technical set while root completes publication status.

Seven captures are retained: three actual UI images and four panels explicitly
derived from the raw sources named in browser-evidence.json. No native Sonar UI
or terminal screenshot is fabricated. S2-06/07 are isolated-domain fixtures.

Gemini CLI usage includes reported auxiliary roles and excludes external research
effort. Duration01/03 and API01/03/11/12 are unknown. Cached tokens are a subset of
input; candidates and thoughts are distinct. Main JSONL response counts are not
API attempts. The final corpus is prepared, not fitted with a BERTopic model.

The current source includes inherited Stage 1 code plus generated changes. Source,
tests and native artifacts are under files/. Coverage input LCOV is separately
under coverage-inputs/; XML is coverage.xml. Unchanged Stage 1 hashes are checked
by the report readiness gate against the separately retained generation-08 state.
"""
(target / "README.md").write_text(notes, encoding="utf-8")

initial = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
for row in initial["files"]:
    relative = f"files/{row['path']}"
    if digest((target / relative).read_bytes()) != row["sha256"]:
        raise ValueError(f"Original frozen source hash changed: {relative}")
    origins[relative] = {"base": "tool_root", "path": row["path"]}

rows = []
for path in sorted(target.rglob("*")):
    if path.is_file() and path.name != "evidence-manifest.json":
        relative = path.relative_to(target).as_posix()
        rows.append({
            "path": relative, "bytes": path.stat().st_size,
            "sha256": digest(path.read_bytes()),
            "source": origins.get(relative, {"base": "snapshot_authored", "path": relative}),
        })
manifest = {
    "label": "final-verified", "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "local implementation and technical evidence verified; final Drive appendix/PDF QA pending at assembly time",
    "scope": "current app/tests/native artifacts/manifests; raw final verification; exact Sonar; API/catalog/browser; closed usage/input/question audits; archived transcripts; final Markdown corpus; seven captures; explicit researcher helpers",
    "exclusions": ["dependencies", "credential/authentication stores", "caches", "Git", "living publication-status notes", "Drive final appendix/PDF not yet verified"],
    "source_bases": {
        "tool_root": "Etapa 2/Spec Kit", "stage2_shared": "Etapa 2/shared",
        "snapshot_authored": "Etapa 2/Spec Kit/docs/final-verified",
    },
    "capture_counts": {"total": len(captures), "actual_ui": sum(c["kind"] == "actual_ui" for c in captures), "derived_panel": sum(c["kind"] == "derived_panel" for c in captures)},
    "files_count": len(rows), "bytes_total": sum(row["bytes"] for row in rows),
    "files": rows,
    "integrity_definition": "SHA-256 of original bytes, not normalized text; manifest excludes itself to avoid a recursive digest",
}
manifest_path = target / "evidence-manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
for row in rows:
    if digest((target / row["path"]).read_bytes()) != row["sha256"]:
        raise ValueError(f"Final copied hash mismatch: {row['path']}")
print(json.dumps({
    "status": "pass", "snapshot": "docs/final-verified", "files_count": len(rows),
    "bytes_total": manifest["bytes_total"], "capture_counts": manifest["capture_counts"],
    "report_readiness": check_stdout, "manifest_sha256": digest(manifest_path.read_bytes()),
    "report_sha256": readiness["final_report_sha256"],
}))
