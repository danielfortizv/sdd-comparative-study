"""Researcher-only unchanged copy of Kiro's own Stage 1 brownfield baseline.

Does not run Kiro, Gemini, installers or Git. Never follows reparse points and
never overwrites an existing Stage 2 directory. Application/tests/specification
bytes remain exactly those from Stage 1.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import stat

STAGE = Path(__file__).resolve().parent.parent
CASE = STAGE.parent
BASE = CASE / "Etapa 1" / "Kiro"
DEST = STAGE / "Kiro"
ROOTS = ("backend", "frontend", ".kiro")
ROOT_FILES = ("README.md",)
EXCLUDE = {"docs", "node_modules", ".venv", "venv", "dist", "build", "coverage", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git", ".sonar", ".sonar-user-home", ".agents"}
SENSITIVE = {".env", ".coverage", "credentials.json", "oauth_creds.json", "application_default_credentials.json", "sonar-token.txt", "auth.json", "token.json"}
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def is_reparse(path: Path) -> bool:
    return path.is_symlink() or bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def gather(path: Path, skipped: list[dict]) -> list[Path]:
    relative = path.relative_to(BASE).as_posix()
    if is_reparse(path):
        skipped.append({"path": relative, "reason": "reparse point / symlink / junction not followed"})
        return []
    if path.name in EXCLUDE or path.name in SENSITIVE or path.name.startswith(".env.") or path.name.endswith((".pyc", ".pyo", ".tsbuildinfo")):
        skipped.append({"path": relative, "reason": "dependency, build, cache, evidence, Git or credential exclusion"})
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
    parser.add_argument("--execute", action="store_true", help="Create the new Stage 2 baseline after checking all paths/hashes; preview otherwise")
    args = parser.parse_args()
    if DEST.resolve() != (CASE / "Etapa 2" / "Kiro").resolve() or DEST.exists():
        raise RuntimeError("Only the exact NEW Stage 2/Kiro directory is allowed")
    if not BASE.is_dir() or is_reparse(BASE):
        raise RuntimeError("Original Kiro baseline must be a regular directory")
    skipped: list[dict] = []
    paths = [file for root in ROOTS for file in gather(BASE / root, skipped)] + [BASE / name for name in ROOT_FILES]
    if any(not path.is_relative_to(BASE) or is_reparse(path) for path in paths):
        raise RuntimeError("Copy set escaped its own Stage 1 baseline or contains a reparse point")
    manifest = [{"path": path.relative_to(BASE).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)} for path in paths]
    source = [path for path in paths if path.relative_to(BASE).parts[0] in {"backend", "frontend"} and path.suffix.lower() in SOURCE_EXTS]
    specs = [path for path in paths if path.relative_to(BASE).parts[:2] == (".kiro", "specs") and path.suffix.lower() in {".md", ".json"}]
    metrics = {"source": counts(source), "specification": counts(specs), "source_scope": "UTF-8 BOM removed / universal-newline-normalized text for all .py/.ts/.tsx/.js/.jsx/.css/.html under backend/frontend, including tests/configuration. Dependencies/builds/caches/evidence excluded.", "dependency_manifests": [{"path": path.relative_to(BASE).as_posix(), "sha256": sha(path)} for path in paths if path.name in {"requirements.txt", "package.json", "package-lock.json"}]}
    summary = {"source": str(BASE), "destination": str(DEST), "copied_files": len(paths), "source_metrics": {key: value for key, value in metrics["source"].items() if key != "per_file"}, "specification_metrics": {key: value for key, value in metrics["specification"].items() if key != "per_file"}, "execute": args.execute}
    if args.execute:
        DEST.mkdir()
        docs = DEST / "docs"
        docs.mkdir()
        for path in paths:
            target = DEST / path.relative_to(BASE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            if sha(target) != sha(path):
                raise RuntimeError(f"Byte-preservation check failed: {target}")
        for row in manifest:
            if sha(BASE / row["path"]) != row["sha256"]:
                raise RuntimeError(f"Stage 1 file changed during copy: {row['path']}")
        stamp = datetime.now(timezone.utc).isoformat()
        records = {"baseline-copy-manifest.json": {"researcher_created": True, "created_at_utc": stamp, "source_root": str(BASE), "destination_root": str(DEST), "files": manifest, "skipped": skipped, "all_copied_bytes_verified": True, "stage1_files_unchanged": True, "integration_adjustments": []}, "baseline-metrics.json": {"researcher_created": True, "measured_at_utc": stamp, **metrics}}
        for name, data in records.items():
            (docs / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
