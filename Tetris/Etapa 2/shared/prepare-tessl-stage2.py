"""Researcher-only, one-time unchanged Stage 1 Tessl -> Stage 2 baseline copy.

No application/test/specification contents are authored by this helper. It never
follows reparse points, overwrites an existing tool directory, or invokes Tessl,
Gemini, Git, package installation, or any generator. The only integration change
is pinning Tessl MCP to the measured existing executable with updates disabled.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from datetime import datetime, timezone

STAGE = Path(__file__).resolve().parent.parent
CASE = STAGE.parent
BASE = CASE / "Etapa 1" / "Tessl"
DEST = STAGE / "Tessl"
RUNTIME = Path("C:/Users/Kevin Alvarez/AppData/Local/tessl/versions/tessl-0.112.0-win32-x64.exe")
ROOTS = ("backend", "frontend", "specs", ".tessl", ".gemini")
FILES = ("AGENTS.md", "tessl.json", ".geminiignore")
EXCLUDED = {"docs", "node_modules", ".venv", "venv", "dist", "build", "coverage", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git", ".sonar", ".sonar-user-home", ".agents"}
SENSITIVE = {".env", ".coverage", "credentials.json", "oauth_creds.json", "application_default_credentials.json", "sonar-token.txt", "auth.json", "token.json"}
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
SKILLS = {
    "tessl__react-dev": ".tessl/plugins/softaworks/agent-toolkit/skills/react-dev",
    "tessl__run-check-server": ".tessl/plugins/maria/fastapi/skills/run-check-server",
    "tessl__scaffold-project": ".tessl/plugins/maria/fastapi/skills/scaffold-project",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def is_reparse(path: Path) -> bool:
    return path.is_symlink() or bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def gather(path: Path, skipped: list[dict]) -> list[Path]:
    relative = path.relative_to(BASE).as_posix()
    if is_reparse(path):
        skipped.append({"path": relative, "reason": "reparse point / junction / symlink not followed"})
        return []
    if path.name in EXCLUDED or path.name in SENSITIVE or path.name.endswith((".pyc", ".pyo", ".tsbuildinfo")) or path.name.startswith(".env."):
        skipped.append({"path": relative, "reason": "dependency, build, cache, evidence or credential exclusion"})
        return []
    if path.is_dir():
        return [file for child in sorted(path.iterdir()) for file in gather(child, skipped)]
    if not path.is_file():
        raise RuntimeError(f"Unexpected non-regular file: {path}")
    return [path]


def counts(paths: list[Path]) -> dict:
    per_file = {}
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        per_file[path.relative_to(BASE).as_posix()] = {"lines": len(lines), "nonblank_lines": sum(bool(line.strip()) for line in lines), "characters": len(text), "sha256": sha(path)}
    total_lines = sum(row["lines"] for row in per_file.values())
    return {"files": len(per_file), "lines": total_lines, "nonblank_lines": sum(row["nonblank_lines"] for row in per_file.values()), "characters": sum(row["characters"] for row in per_file.values()), "lines_per_file": round(total_lines / len(per_file), 2) if per_file else 0, "per_file": per_file}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Create a NEW Stage 2 Tessl directory after safety checks; otherwise preview only")
    parser.add_argument("--resume-incomplete-setup", action="store_true", help="Finish only a verified unchanged partial setup produced by this helper")
    args = parser.parse_args()
    resume = args.execute and args.resume_incomplete_setup
    if DEST.resolve() != (CASE / "Etapa 2" / "Tessl").resolve() or (DEST.exists() and not resume):
        raise RuntimeError("Destination must be the exact NEW Stage 2/Tessl directory")
    if not BASE.is_dir() or is_reparse(BASE) or not RUNTIME.is_file() or is_reparse(RUNTIME):
        raise RuntimeError("Expected regular Stage 1 baseline and pinned runtime must exist")
    skipped: list[dict] = []
    paths = [file for root in ROOTS for file in gather(BASE / root, skipped)] + [BASE / name for name in FILES]
    if any(not path.is_relative_to(BASE) or is_reparse(path) for path in paths):
        raise RuntimeError("Copy set escaped the Stage 1 baseline or contains a reparse point")
    manifest = [{"path": path.relative_to(BASE).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)} for path in paths]
    source = [path for path in paths if path.relative_to(BASE).parts[0] in {"backend", "frontend"} and path.suffix.lower() in SOURCE_EXTS]
    specs = [path for path in paths if path.relative_to(BASE).parts[0] == "specs" and path.suffix.lower() in {".md", ".json"}]
    metrics = {"source": counts(source), "specification": counts(specs), "source_scope": "All .py/.ts/.tsx/.js/.jsx/.css/.html under backend and frontend, including tests and existing vite.config.js/.d.ts config snapshots; excludes dependencies, build directories and caches. Text counts use UTF-8 BOM removal and universal newline normalization.", "dependency_manifests": [{"path": path.relative_to(BASE).as_posix(), "sha256": sha(path)} for path in paths if path.name in {"package.json", "package-lock.json", "pyproject.toml"}]}
    runtime_info = {"runtime_version": "0.112.0", "runtime_path": str(RUNTIME), "runtime_sha256": sha(RUNTIME), "runtime_bytes": RUNTIME.stat().st_size, "npm_bootstrap_version": "0.108.0", "auto_update_environment": {"TESSL_AUTO_UPDATE_INTERVAL_MINUTES": "0", "TESSL_DISABLE_UPDATE": "1"}, "disable_evidence": {"method": "Read-only embedded JavaScript inspection of the exact SHA-pinned executable", "auto_update_predicate_byte_offset": 101023344, "predicate_excerpt": "function $R6(w,A=0,$=!1){if($)return!1;if(A<=0)return!1;", "scheduler_excerpt": "if(G>0&&Q!==f)", "version_status_excerpt": "B=f>0&&!q", "interpretation": "Interval zero disables automatic binary replacement, rather than checking on every invocation. TESSL_DISABLE_UPDATE=1 additionally disables update actions. This does not assert that telemetry or latest-version lookup is disabled."}, "rationale": "Direct versioned executable matches the final installed Stage 1 Tessl runtime; NPM bootstrap version is recorded separately and is not executed."}
    summary = {"source": str(BASE), "destination": str(DEST), "copied_files": len(paths), "source_metrics": {key: value for key, value in metrics["source"].items() if key != "per_file"}, "specification_metrics": {key: value for key, value in metrics["specification"].items() if key != "per_file"}, "runtime": runtime_info, "execute": args.execute}
    if not args.execute:
        print(json.dumps(summary, indent=2))
        return
    # Make directories only after all paths, hashes and exclusions have passed.
    if resume:
        if not DEST.is_dir() or is_reparse(DEST) or (DEST / "docs" / "baseline-copy-manifest.json").exists():
            raise RuntimeError("Resume only supports a regular, incomplete setup before its manifest exists")
        for row in manifest:
            target = DEST / row["path"]
            if row["path"] == ".gemini/settings.json":
                target = DEST / "docs" / "baseline-gemini-settings.json"
            if not target.is_file() or is_reparse(target) or sha(target) != row["sha256"]:
                raise RuntimeError(f"Partial setup baseline differs; refusing recovery: {target}")
        allowed = {row["path"] for row in manifest} | {"docs/baseline-gemini-settings.json"}
        def validate_existing(folder: Path) -> None:
            for item in folder.iterdir():
                relative = item.relative_to(DEST).as_posix()
                if is_reparse(item):
                    if relative not in {f".agents/skills/{name}" for name in SKILLS}:
                        raise RuntimeError(f"Unexpected reparse point in partial setup: {item}")
                elif item.is_dir():
                    validate_existing(item)
                elif relative not in allowed:
                    raise RuntimeError(f"Unexpected file in partial setup: {item}")
        validate_existing(DEST)
    else:
        DEST.mkdir()
    docs = DEST / "docs"
    docs.mkdir(exist_ok=resume)
    if not resume:
        for path in paths:
            target = DEST / path.relative_to(BASE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            if sha(target) != sha(path):
                raise RuntimeError(f"Byte preservation check failed: {target}")
    # Preserve copied settings verbatim as baseline evidence before the allowed
    # local integration adjustment. Application/tests/specifications stay exact.
    settings_path = DEST / ".gemini" / "settings.json"
    if not resume:
        shutil.copy2(settings_path, docs / "baseline-gemini-settings.json")
    settings = json.loads((docs / "baseline-gemini-settings.json").read_text(encoding="utf-8-sig"))
    settings["mcpServers"]["tessl"]["command"] = str(RUNTIME)
    settings["mcpServers"]["tessl"]["env"] = runtime_info["auto_update_environment"]
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    # Create fresh integration junctions whose resolved targets stay in Stage 2.
    junctions = []
    for name, relative_target in SKILLS.items():
        target = DEST / relative_target
        link = DEST / ".agents" / "skills" / name
        if not target.resolve().is_relative_to(DEST.resolve()) or not (target / "SKILL.md").is_file():
            raise RuntimeError("Fresh skill target is invalid or outside Stage 2")
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.exists():
            literal = lambda path: "'" + str(path).replace("'", "''") + "'"
            command = "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path " + literal(link) + " -Target " + literal(target) + " | Out-Null"
            encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], check=True, capture_output=True, text=True)
        if link.resolve() != target.resolve():
            raise RuntimeError(f"Fresh junction does not resolve within Stage 2: {link}")
        junctions.append({"path": str(link), "target": str(target), "verified_resolved_target": str(link.resolve())})
    # Verify Stage 1 itself still has the same bytes after setup.
    for row in manifest:
        if sha(BASE / row["path"]) != row["sha256"]:
            raise RuntimeError(f"Stage 1 baseline changed during setup: {row['path']}")
    stamp = datetime.now(timezone.utc).isoformat()
    records = {"baseline-copy-manifest.json": {"researcher_created": True, "created_at_utc": stamp, "source_root": str(BASE), "destination_root": str(DEST), "files": manifest, "skipped": skipped, "original_stage1_junctions_not_copied": True, "new_stage2_junctions": junctions, "integration_adjustments": [{"path": ".gemini/settings.json", "description": "Pin existing Tessl MCP executable and disable automatic updates; original bytes saved in baseline-gemini-settings.json", "current_sha256": sha(settings_path)}]}, "baseline-metrics.json": {"researcher_created": True, "measured_at_utc": stamp, **metrics}, "tessl-runtime-pin.json": {"researcher_created": True, "measured_at_utc": stamp, **runtime_info}}
    for name, data in records.items():
        (docs / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
