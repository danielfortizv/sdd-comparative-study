"""Freeze Tessl research source/spec/evidence with current-hash validation."""
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--label", required=True)
parser.add_argument("--include-validation", action="store_true")
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9-]+", args.label):
    raise ValueError("Use a lowercase snapshot label")
root = Path(__file__).resolve().parent.parent / "Tessl"
docs = root / "docs"
metrics = json.loads((docs / "metrics.json").read_text(encoding="utf-8-sig"))
target = docs / args.label
if target.exists():
    raise FileExistsError("Refusing to overwrite a Tessl research snapshot")
files = {}
for scope in ("source_current", "dependency_manifests_current", "spec_stage1_copy", "spec_stage2", "integration_manifests_current"):
    files.update(metrics.get(scope, {}).get("per_file", {}))
# Preflight all paths/hashes before creating a partial snapshot.
for name, item in files.items():
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Snapshot source escaped Tessl")
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != item["sha256"]:
        raise ValueError("Regenerate stale metrics before snapshot: " + name)
target.mkdir()
copied = []
for name, item in sorted(files.items()):
    destination = target / "files" / name
    if not destination.resolve().is_relative_to(target.resolve()):
        raise ValueError("Snapshot target escaped its directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / name, destination)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest().upper()
    if digest != item["sha256"]:
        raise ValueError("Source changed while snapshotting: " + name)
    copied.append({"path": destination.relative_to(target).as_posix(), "sha256": digest, "bytes": destination.stat().st_size})
names = ["metrics.json", "input-audit.json", "question-audit.json", "question-audit.md", "baseline-metrics.json", "baseline-copy-manifest.json", "tessl-runtime-pin.json", "run-classifications.json", "01-effective-input-verification.json", "sonar-summary.json", "sonar-metrics.json", "sonar-issues.json", "sonar-open-issues.json", "sonar-quality-gate.json", "sonar-task.json", "sonar-scan.log", "coverage.xml"]
names += ["question-review.json", "RESEARCH_LOG.md", "BASELINE.md", "sonar-verification.json", "sonar-exact-task.json", "sonar-exact-quality-gate.json"]
for name in names:
    path = docs / name
    if path.exists():
        shutil.copy2(path, target / name)
        copied.append({"path": name, "sha256": hashlib.sha256((target / name).read_bytes()).hexdigest().upper(), "bytes": (target / name).stat().st_size})
if args.include_validation:
    evidence_paths = list(docs.glob("*.json")) + list(docs.glob("*.md")) + list(docs.glob("*.log")) + list(docs.glob("*.txt"))
    for folder in ("acceptance", "screenshots", "sonar-baseline", "sonar-attempts", "transition-20261025", "evidence-view", "publication-qa", "bertopic-corpus", "metric-audit"):
        start = docs / folder
        if start.exists():
            evidence_paths.extend(p for p in start.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    evidence_paths.extend(root / n for n in ("frontend/coverage/lcov.info", ".sonar/report-task.txt"))
    for source in sorted(set(evidence_paths)):
        if not source.is_file():
            continue
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError("Evidence escaped Tessl root")
        relative = (Path("validation") / source.relative_to(root)).as_posix()
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        destination.write_bytes(data)
        copied.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest().upper(), "bytes": len(data)})
    shared = Path(__file__).resolve().parent
    helpers = list(shared.glob("*tessl*")) + list((shared / "acceptance").glob("*.py"))
    for source in sorted(set(helpers)):
        if source.is_file():
            destination = target / "researcher-helpers" / source.relative_to(shared)
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            destination.write_bytes(data)
            copied.append({"path": destination.relative_to(target).as_posix(), "sha256": hashlib.sha256(data).hexdigest().upper(), "bytes": len(data)})
for run in metrics.get("runs", []):
    for suffix in (".prompt.txt", ".started.json", ".run.json", ".stdout.json", ".stderr.txt"):
        source = docs / (run["label"] + suffix)
        if source.exists():
            destination = target / "invocations" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            destination.write_bytes(data)
            copied.append({"path": destination.relative_to(target).as_posix(), "sha256": hashlib.sha256(data).hexdigest().upper(), "bytes": len(data)})
archive_manifest = docs / "transcripts-archive/manifest.json"
if archive_manifest.exists():
    rows = json.loads(archive_manifest.read_text(encoding="utf-8-sig"))
    for relative, expected in [("transcripts-archive/manifest.json", None)] + [(r["archive"], r["sha256"]) for r in rows]:
        source = docs / relative
        if not source.resolve().is_relative_to(docs.resolve()) or source.is_symlink():
            raise ValueError("Transcript escaped evidence root")
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if expected and digest != expected:
            raise ValueError("Archived transcript hash mismatch")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        copied.append({"path": relative, "sha256": digest, "bytes": len(data)})
manifest = {"researcher_created": True, "label": args.label, "created_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "Tessl own source/tests, manifests, inherited native copies, new Stage 2 artifacts, integration manifests, retained researcher reports, complete closed-invocation inputs/outputs and immutable native transcript archives. Dependencies/credential files/Git excluded. Private transcripts can contain incidental sensitive strings; public summaries require scoped review. Quality files may describe an earlier analysis; copying alone is not final acceptance.", "metrics_measured_at_utc": metrics["measured_at_utc"], "unclosed_invocation_labels_at_measurement": metrics.get("unclosed_invocation_labels", []), "files": copied}
(target / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"snapshot": str(target), "hashed_files": len(copied)}))
