"""Copy the reviewed BMAD rerun and current evidence into the Tetris repo tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git", ".venv", ".pytest_cache", ".sonar", ".sonar-user-home",
    "__pycache__", "node_modules", "gemini-home", "dist", "build", ".cache",
    "coverage", "htmlcov", "tmp",
}
EXCLUDED_NAMES = {
    ".coverage", ".env", "credentials.json",
    "application_default_credentials.json", "sonar-token.txt",
}
SHARED_FILES = (
    "bmad-full-metrics.json",
    "collect-bmad-full-metrics.py",
    "materialize-bmad-full-correction.py",
    "materialize-bmad-full-epics.py",
    "scan-bmad-full.ps1",
    "verify-bmad-full-acceptance.py",
    "export-bmad-full-to-repo.py",
    "report/auditoria-bmad-calculadora-tetris.md",
    "report/bmad-full-overleaf-addendum.tex",
    "report/guion-tetris-etapa1-asesor.md",
    "report/tetris-etapa1-overleaf.tex",
    "report/vista-bmad-full-overleaf.png",
)


def approved_file(path: Path, base: Path) -> bool:
    relative = path.relative_to(base)
    names = [part.casefold() for part in relative.parts]
    if any(part in EXCLUDED_DIRS for part in names[:-1]):
        return False
    name = names[-1]
    if name in EXCLUDED_NAMES or name.startswith(".env."):
        return False
    if path.is_symlink() or path.suffix.casefold() in {".pem", ".key", ".p12"}:
        return False
    return True


def copy_file(source: Path, target: Path) -> dict[str, object]:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {
        "path": target.as_posix(),
        "bytes": source.stat().st_size,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path, help="Existing repo Tetris/Etapa 1 directory")
    args = parser.parse_args()
    destination = args.destination.resolve()
    if not destination.is_dir() or destination.name != "Etapa 1" or destination.parent.name != "Tetris":
        raise SystemExit("Destination must be the existing repository Tetris/Etapa 1 directory")

    records = [copy_file(ROOT / "PROGRESS.md", destination / "PROGRESS.md")]
    for relative in SHARED_FILES:
        source = ROOT / "shared" / relative
        if not source.is_file():
            raise SystemExit(f"Missing selected evidence: {source}")
        records.append(copy_file(source, destination / "shared" / relative))

    rerun = ROOT / "Bmad Method Full"
    for source in sorted(rerun.rglob("*")):
        if not source.is_file() or not approved_file(source, rerun):
            continue
        records.append(copy_file(source, destination / "Bmad Method Full" / source.relative_to(rerun)))

    summary = {
        "source": "Bmad Method Full plus selected Stage 1 evidence",
        "file_count": len(records),
        "total_bytes": sum(int(record["bytes"]) for record in records),
        "excluded_directories": sorted(EXCLUDED_DIRS),
        "files": [
            {"path": str(Path(record["path"]).relative_to(destination)), "sha256": record["sha256"]}
            for record in records
        ],
    }
    manifest = destination / "shared" / "bmad-full-repo-export-manifest.json"
    manifest.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": summary["file_count"], "total_bytes": summary["total_bytes"]}))


if __name__ == "__main__":
    main()
