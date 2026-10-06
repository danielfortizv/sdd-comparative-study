"""Copy full BMAD epic/sprint artifacts from preserved Gemini stdout verbatim."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "Bmad Method Full"
SOURCE = ROOT / "docs/full-epics-stories.stdout.json"
OUTPUTS = [
    ("epics.md", "markdown", ROOT / "_bmad-output/planning-artifacts/epics.md"),
    ("sprint-status.yaml", "yaml", ROOT / "_bmad-output/implementation-artifacts/sprint-status.yaml"),
]

source = SOURCE.read_text(encoding="utf-8-sig")
evidence = []
for filename, language, path in OUTPUTS:
    pattern = (
        rf"\*\*Intended File Path:\*\* `\{{project-root\}}/[^`]*{re.escape(filename)}`"
        rf"\s+```{language}\r?\n(.*?)\r?\n```"
    )
    matches = re.findall(pattern, source, re.DOTALL)
    if len(matches) != 1:
        raise SystemExit(f"Expected one fenced artifact for {filename}; found {len(matches)}")
    content = matches[0].replace("\r\n", "\n") + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    evidence.append({
        "path": str(path.relative_to(ROOT)),
        "source": str(SOURCE.relative_to(ROOT)),
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "lines": len(content.splitlines()),
        "characters": len(content),
    })

epics = OUTPUTS[0][2].read_text(encoding="utf-8")
requirements = {int(number) for number in re.findall(r"\bFR-([0-9]+)\b", epics)}
if requirements != set(range(1, 31)):
    raise SystemExit(f"FR coverage mismatch: {sorted(requirements)}")

manifest = ROOT / "docs/full-epics-materialization.json"
manifest.write_text(json.dumps({"artifacts": evidence, "unique_fr_ids": 30}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"artifacts": evidence, "unique_fr_ids": 30}, indent=2))
