import hashlib
import json
import shutil
from pathlib import Path


RUN_ID = "OPENSPEC-S1-OFFICIAL-01"
STAGE = Path(r"C:\Users\jeron\OneDrive\Escritorio\uni\implementacion Ecommerce\Caso 3-Ecommerce\Etapa 1")
SOURCE = STAGE / "OpenSpec"
EVIDENCE = STAGE / "Evidencias" / "OpenSpec"
ROOT = STAGE / "Evaluacion" / "independent-tests" / "openspec"
FROZEN = ROOT / "frozen-first-implementation"
TRANSCRIPT = EVIDENCE / "session-aplicacion-correctiva-ronda-2.jsonl"
MANIFEST = ROOT / "first-implementation-manifest.json"

INCLUDED = [
    SOURCE / "backend" / "requirements.txt",
    *sorted((SOURCE / "backend" / "app").glob("*.py")),
    SOURCE / "frontend" / "index.html",
    SOURCE / "frontend" / "package.json",
    SOURCE / "frontend" / "package-lock.json",
    SOURCE / "frontend" / "postcss.config.js",
    SOURCE / "frontend" / "tailwind.config.js",
    SOURCE / "frontend" / "tsconfig.json",
    SOURCE / "frontend" / "vite.config.ts",
    *sorted((SOURCE / "frontend" / "src").rglob("*")),
]
INCLUDED = [path for path in INCLUDED if path.is_file()]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def load_replacements() -> list[dict]:
    replacements = []
    for raw_line in TRANSCRIPT.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        for call in event.get("toolCalls", []):
            if call.get("name") != "replace":
                continue
            args = call.get("args", {})
            relative = args.get("file_path") or args.get("path") or args.get("filePath")
            if relative not in {
                "frontend/src/pages/CheckoutPage.tsx",
                "frontend/src/pages/ConfirmationPage.tsx",
            }:
                continue
            old = args.get("oldContent") or args.get("old_string") or args.get("old_content")
            new = args.get("newContent") or args.get("new_string") or args.get("new_content")
            if not old or not new:
                raise RuntimeError(f"Incomplete replacement evidence for {relative}")
            replacements.append({"path": relative, "old": old, "new": new})
    if len(replacements) != 3:
        raise RuntimeError(f"Expected 3 corrective replacements, found {len(replacements)}")
    return replacements


if FROZEN.exists():
    raise RuntimeError(f"Frozen snapshot already exists: {FROZEN}")

for source_path in INCLUDED:
    relative = source_path.relative_to(SOURCE)
    destination = FROZEN / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)

replacement_audit = []
for replacement in reversed(load_replacements()):
    destination = FROZEN / Path(replacement["path"])
    current = destination.read_text(encoding="utf-8")
    count = current.count(replacement["new"])
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one corrected fragment in {replacement['path']}, found {count}"
        )
    restored = current.replace(replacement["new"], replacement["old"], 1)
    destination.write_text(restored, encoding="utf-8", newline="")
    replacement_audit.append(
        {
            "path": replacement["path"],
            "corrected_fragment_sha256": sha256_bytes(replacement["new"].encode("utf-8")),
            "restored_fragment_sha256": sha256_bytes(replacement["old"].encode("utf-8")),
        }
    )

files = []
for path in sorted(file for file in FROZEN.rglob("*") if file.is_file()):
    data = path.read_bytes()
    files.append(
        {
            "path": path.relative_to(FROZEN).as_posix(),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        }
    )

manifest = {
    "run_id": RUN_ID,
    "tool": "OpenSpec",
    "source_workspace": SOURCE.as_posix(),
    "frozen_snapshot": FROZEN.as_posix(),
    "scope": "First valid implementation before post-implementation corrective round 2",
    "provenance": {
        "official_initial_implementation_transcript": "Evidencias/OpenSpec/session-implementacion-inicial.jsonl",
        "corrective_transcript": "Evidencias/OpenSpec/session-aplicacion-correctiva-ronda-2.jsonl",
        "corrective_transcript_sha256": sha256_bytes(TRANSCRIPT.read_bytes()),
        "method": "Current tree copied without generated artifacts; the three exact corrective replace operations were reversed in reverse chronological order.",
        "reversed_replacements": list(reversed(replacement_audit)),
    },
    "excluded": [
        "frontend/node_modules/**",
        "frontend/dist/**",
        "frontend/build/**",
        "frontend/.vite/**",
        "backend/.venv/**",
        "backend/ecommerce.db",
        "**/__pycache__/**",
        "**/.pytest_cache/**",
        "**/coverage/**",
        "openspec/**",
        ".gemini/**",
        "especificacion-semilla-final-en.md",
        "docs/**",
    ],
    "files": files,
}
MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"files": len(files), "manifest": str(MANIFEST)}, indent=2))
