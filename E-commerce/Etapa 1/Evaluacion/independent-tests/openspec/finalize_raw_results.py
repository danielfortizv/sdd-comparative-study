import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
results = root / "sonarqube-results"
results.mkdir(exist_ok=True)

mapping = {
    "sonar-ce-task.json": "ce-task.json",
    "sonar-measures.json": "measures.json",
    "sonar-coverage-measures.json": "coverage-measures.json",
    "sonar-quality-gate.json": "quality-gate.json",
    "sonar-issues.json": "issues.json",
    "sonar-hotspots.json": "hotspots.json",
    "sonar-plugins.json": "plugins.json",
    "sonar-system-status.json": "system-status.json",
}
for source, target in mapping.items():
    shutil.copy2(root / source, results / target)

raw_issues = json.loads((results / "issues.json").read_text(encoding="utf-8-sig"))
inventory = []
for issue in raw_issues.get("issues", []):
    impacts = issue.get("impacts") or []
    inventory.append({
        "file": issue.get("component", "").split(":", 1)[-1],
        "line": issue.get("line") or issue.get("textRange", {}).get("startLine"),
        "rule": issue.get("rule"),
        "severity": issue.get("severity"),
        "type": issue.get("type"),
        "message": issue.get("message"),
        "effort": issue.get("effort"),
        "impacts": impacts,
        "software_quality": [impact.get("softwareQuality") for impact in impacts],
    })
(results / "issue-inventory.json").write_text(
    json.dumps({"total": len(inventory), "issues": inventory}, indent=2) + "\n",
    encoding="utf-8",
)

manifest = json.loads((root / "first-implementation-manifest.json").read_text(encoding="utf-8"))
snapshot = root / "frozen-first-implementation"
unchanged, changed, missing = [], [], []
for item in manifest["files"]:
    path = snapshot / item["path"]
    if not path.exists():
        missing.append(item["path"])
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if digest == item["sha256"].upper():
        unchanged.append(item["path"])
    else:
        changed.append({"path": item["path"], "expected": item["sha256"], "actual": digest})
integrity = {
    "manifest_sha256": hashlib.sha256((root / "first-implementation-manifest.json").read_bytes()).hexdigest().upper(),
    "total_manifest_files": len(manifest["files"]),
    "unchanged_count": len(unchanged),
    "changed_count": len(changed),
    "missing_count": len(missing),
    "unchanged": unchanged,
    "changed": changed,
    "missing": missing,
}
(root / "post-scan-hash-check.json").write_text(json.dumps(integrity, indent=2) + "\n", encoding="utf-8")

hash_targets = [
    root / "first-implementation-manifest.json",
    root / "post-scan-hash-check.json",
    root / "sonar-scanner-official.log",
    root / "coverage-backend.xml",
    root / "coverage-backend.json",
    root / "coverage-frontend-sonar.lcov",
    root / "coverage-frontend" / "coverage-summary.json",
    root / "coverage-summary-combined.json",
    root / "pytest-results.txt",
    root / "vitest-results.txt",
] + sorted(results.glob("*.json"))
hash_lines = []
for path in hash_targets:
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    hash_lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
(root / "results-sha256.txt").write_text("\n".join(hash_lines) + "\n", encoding="utf-8")
