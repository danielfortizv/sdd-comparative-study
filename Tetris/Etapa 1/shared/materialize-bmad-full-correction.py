"""Materialize the seven complete files emitted by BMAD correction Gemini run."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


TOOL = Path(__file__).resolve().parent.parent / "Bmad Method Full"
SOURCE = TOOL / "docs/full-build-auto-correction.stdout.json"
EXPECTED = {
    "_bmad-output/planning-artifacts/prds/prd-Bmad Method Full-2026-10-05/prd.md",
    "_bmad-output/planning-artifacts/prds/prd-Bmad Method Full-2026-10-05/addendum.md",
    "_bmad-output/planning-artifacts/epics.md",
    "_bmad-output/implementation-artifacts/spec-stage-1-tetris-study.md",
    "_bmad-output/implementation-artifacts/sprint-status.yaml",
    "backend/app/tests/test_domain.py",
    "backend/app/tests/test_api.py",
}


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8-sig")
    headers = list(re.finditer(r"^### File (\d+): `([^`]+)`\s*$", text, re.MULTILINE))
    if len(headers) != len(EXPECTED):
        raise SystemExit(f"Expected {len(EXPECTED)} files, found {len(headers)}")

    planned = []
    for index, header in enumerate(headers):
        segment = text[header.end() : headers[index + 1].start() if index + 1 < len(headers) else len(text)]
        start = re.search(r"^```(?:markdown|yaml|python)\r?\n", segment, re.MULTILINE)
        closes = list(re.finditer(r"^```\s*$", segment, re.MULTILINE))
        if not start or not closes or closes[-1].start() <= start.end():
            raise SystemExit(f"Missing complete fenced block for file {index + 1}")
        content = segment[start.end() : closes[-1].start()].replace("\r\n", "\n")
        if not content.endswith("\n"):
            content += "\n"
        raw_path = Path(header.group(2))
        path = raw_path.resolve()
        if not path.is_relative_to(TOOL.resolve()):
            raise SystemExit(f"Outside tool root: {path}")
        relative = path.relative_to(TOOL).as_posix()
        planned.append((relative, path, content))

    if {relative for relative, _, _ in planned} != EXPECTED:
        raise SystemExit(f"Unexpected paths: {[relative for relative, _, _ in planned]}")

    records = []
    for relative, path, content in planned:
        before = path.read_bytes() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        records.append({
            "path": relative,
            "source": str(SOURCE.relative_to(TOOL)),
            "sha256_before": sha256(before) if before is not None else None,
            "sha256_after": sha256(content.encode("utf-8")),
            "lines": len(content.splitlines()),
        })

    prd = (TOOL / "_bmad-output/planning-artifacts/prds/prd-Bmad Method Full-2026-10-05/prd.md").read_text(encoding="utf-8")
    ids = {int(n) for n in re.findall(r"\bFR-([0-9]+)\b", prd)}
    if ids != set(range(1, 31)):
        raise SystemExit(f"Corrected PRD does not have FR-1..30: {sorted(ids)}")

    manifest = TOOL / "docs/full-build-auto-correction-materialization.json"
    manifest.write_text(json.dumps({"files": records, "unique_prd_fr_ids": 30}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": records, "unique_prd_fr_ids": 30}, indent=2))


if __name__ == "__main__":
    main()
