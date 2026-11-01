"""Freeze researcher evidence and Kiro source/spec states without overwriting."""
import argparse
import re
import shutil

from kiro_research import DOCS, ROOT, digest, load, stamp, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--allow-pending", action="store_true", help="Preserve a partial snapshot explicitly; never final acceptance")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]+", args.label):
        raise ValueError("Use a lowercase snapshot label")
    metrics = load(DOCS / "metrics.json")
    if not metrics:
        raise RuntimeError("Collect Kiro metrics first")
    pending = metrics.get("unclosed_invocation_labels", [])
    if pending and not args.allow_pending:
        raise RuntimeError("Invocation still pending; close/collect or explicitly preserve partial snapshot")
    target = DOCS / args.label
    if target.exists():
        raise FileExistsError("Refusing to overwrite a Kiro snapshot")
    files = {}
    for scope in ("source_current", "spec_stage1_copy", "spec_stage2", "dependency_manifests_current", "configuration_current"):
        files.update(metrics[scope]["per_file"])
    for name, item in files.items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()) or path.is_symlink():
            raise ValueError("Snapshot path escaped Kiro")
        if digest(path.read_bytes()) != item["sha256"]:
            raise ValueError("Stale metrics/source changed before snapshot: " + name)
    target.mkdir()
    copied = []
    seen = set()
    def copy(source, relative, expected=None):
        if str(relative) in seen:
            return
        if source.is_symlink():
            raise ValueError("Refusing symlink evidence: " + str(source))
        before = digest(source.read_bytes())
        destination = target / relative
        if not destination.resolve().is_relative_to(target.resolve()):
            raise ValueError("Snapshot target escaped its directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        sha = digest(destination.read_bytes())
        if sha != before or digest(source.read_bytes()) != before:
            raise ValueError("Evidence changed while snapshotting: " + str(source))
        if expected and sha != expected:
            raise ValueError("Source changed while snapshotting: " + str(source))
        copied.append({"path": destination.relative_to(target).as_posix(), "bytes": destination.stat().st_size, "sha256": sha})
        seen.add(str(relative))
    for name, item in sorted(files.items()):
        copy(ROOT / name, "files/" + name, item["sha256"])
    for name in ("README.md", "backend/README.md", "frontend/README.md", "frontend/coverage/lcov.info"):
        if (ROOT / name).is_file():
            copy(ROOT / name, "files/" + name)
    names = ("metrics.json", "input-audit.json", "question-audit.json", "question-audit.md", "question-review.json", "baseline-metrics.json", "baseline-copy-manifest.json", "baseline-hash-verification-after-environment.json", "baseline-coverage-instrumentation.json", "run-classifications.json", "kiro-runtime-pin.json", "kiro-cli-provenance.json", "kiro-schema-validation.json", "BASELINE.md", "MEASUREMENT_PROTOCOL.md", "RESEARCH_LOG.md", "sonar-summary.json", "sonar-metrics.json", "sonar-issues.json", "sonar-open-issues.json", "sonar-quality-gate.json", "sonar-task.json", "sonar-scan.log", "coverage.xml")
    for name in names:
        if (DOCS / name).exists():
            copy(DOCS / name, name)
    for run in metrics.get("runs", []):
        for suffix in (".prepared.json", ".started.json", ".run.json", ".prompt.txt", ".stdout.jsonl", ".stderr.txt", ".rpc.jsonl"):
            source = DOCS / (run["label"] + suffix)
            if source.exists():
                copy(source, "invocations/" + source.name)
    if (DOCS / "ACP_DRIVER.md").exists():
        copy(DOCS / "ACP_DRIVER.md", "ACP_DRIVER.md")
    for source in sorted(DOCS.glob("*-baseline-preservation.json")):
        copy(source, source.name)
    archive = load(DOCS / "transcripts-archive/manifest.json", [])
    if archive:
        copy(DOCS / "transcripts-archive/manifest.json", "transcripts-archive/manifest.json")
        for row in archive:
            copy(DOCS / row["archive"], row["archive"], row["sha256"])
    if args.label == "final-verified":
        final_report = load(DOCS / "FINAL_REPORT.json")
        publication = load(DOCS / "drive-final-publication.json")
        if not final_report or not publication or publication.get("status") != "published_readback_and_layout_verified":
            raise RuntimeError("Final report and verified publication required")
        # Preserve research artifacts, not caches or earlier snapshot directories.
        for source in sorted(DOCS.iterdir()):
            if source.is_file() and source.suffix in {".json", ".jsonl", ".md", ".txt", ".log", ".xml"}:
                copy(source, source.name)
        directories = ("acceptance", "screenshots", "evidence-view", "researcher-verification", "publication-qa", "instrumentation-initial", "sonar-attempt-1-fail", "sonar-attempt-2-fail", "sonar-attempt-3-pass", "sonar-baseline", "researcher-setup")
        for directory in directories:
            for source in sorted((DOCS / directory).rglob("*")):
                if source.is_file() and not any(p in {"__pycache__", "node_modules", ".venv", ".pytest_cache"} for p in source.parts) and source.suffix not in {".exe", ".pyc"}:
                    copy(source, source.relative_to(DOCS).as_posix())
        shared = DOCS.parent.parent / "shared"
        for source in sorted(shared.iterdir()):
            if source.is_file() and ("kiro" in source.name or source.name in {"seed.md", "protocol.md", "render-evidence.py", "codex-quota-monitor.mjs", "codex-quota-monitor.README.md", "register-codex-quota-monitor.ps1", "run-codex-quota-monitor.ps1"}):
                copy(source, "researcher-helpers/" + source.name)
        for source in sorted((shared / "acceptance").rglob("*")):
            if source.is_file() and source.suffix in {".py", ".md", ".json", ".ts", ".tsx"} and "__pycache__" not in source.parts:
                copy(source, "researcher-helpers/acceptance/" + source.relative_to(shared / "acceptance").as_posix())
        for name in ("reactivation-20261023.json", "suspension-disabled.json", "suspension-disabled-before-reactivation-20261023.json"):
            if (shared / "quota-monitor" / name).is_file():
                copy(shared / "quota-monitor" / name, "quota-monitor/" + name)
    write(target / "manifest.json", {"researcher_created": True, "created_at_utc": stamp(), "label": args.label, "metrics_measured_at_utc": metrics["measured_at_utc"], "unclosed_invocation_labels_at_measurement": pending, "scope": "own Kiro source/spec/dependency state and retained native/researcher evidence. Final-verified additionally freezes acceptance, screenshots, publication QA, initial instrumentation, Sonar attempts and researcher helpers. Dependencies, executables, auth files, caches and Git excluded. Private transcript evidence may contain incidental sensitive strings; public summaries require scoped review. Acceptance conclusions are in FINAL_REPORT, not inferred from the act of copying.", "files": copied})
    print({"snapshot": str(target), "hashed_files": len(copied), "pending": pending})


if __name__ == "__main__":
    main()
