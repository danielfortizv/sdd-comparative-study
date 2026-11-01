"""Snapshot this tool's generated source/specs without dependencies or secrets."""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--label", required=True)
args = parser.parse_args()
if not args.label or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in args.label):
    raise ValueError("Use a simple lowercase snapshot label")
root = Path(__file__).resolve().parent.parent / "Spec Kit"
docs = root / "docs"
metrics = json.loads((docs / "metrics.json").read_text(encoding="utf-8-sig"))
target = docs / args.label
if target.exists():
    raise FileExistsError("Refusing to replace an existing research snapshot")
target.mkdir()
names = set()
for scope in ("source_current", "dependency_manifests_current", "spec_stage2"):
    names.update(metrics.get(scope, {}).get("per_file", {}))
rows = []
for name in sorted(names):
    source = root / name
    destination = target / "files" / name
    if not source.resolve().is_relative_to(root.resolve()) or not destination.resolve().is_relative_to(target.resolve()):
        raise ValueError("Snapshot path escaped the intended tool directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    rows.append({"path": name, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest().upper(), "bytes": destination.stat().st_size})
for name in ("metrics.json", "input-audit.json", "sonar-summary.json", "sonar-metrics.json", "sonar-issues.json", "sonar-quality-gate.json", "sonar-task.json", "sonar-scan.log", "coverage.xml"):
    if (docs / name).exists():
        shutil.copy2(docs / name, target / name)
(target / "manifest.json").write_text(json.dumps({"label": args.label, "created_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "application/tests, dependency manifests, Stage 2 native artifacts and available measurement reports; dependencies, caches, credentials and Git excluded", "files": rows}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"snapshot": str(target), "source_spec_files": len(rows)}))
