"""Copy the four Gemini-produced markdown artifacts into the OpenSpec change.

The model returned complete file contents in stdout but made no file writes. This
script performs literal extraction; it does not write application source code.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "OpenSpec"
OUTPUT = TOOL / "docs" / "write-artifacts.stdout.txt"
CHANGE = TOOL / "openspec" / "changes" / "tetris-stage1-option-a"

text = OUTPUT.read_text(encoding="utf-8-sig")
pattern = re.compile(
    r"^### Artifact (\d):[^\n]*\n\*\*Required Location:\*\* `([^`]+)`\n\n"
    r"```markdown\n(.*?)\n```\n\n---",
    re.MULTILINE | re.DOTALL,
)
found = {}
for match in pattern.finditer(text):
    number = int(match.group(1))
    relative = Path(match.group(2))
    if relative.parts[:3] != ("openspec", "changes", "tetris-stage1-option-a"):
        raise ValueError(f"Unexpected target: {relative}")
    found[number] = (TOOL / relative, match.group(3) + "\n")

if set(found) != {1, 2, 3, 4}:
    raise ValueError(f"Expected artifacts 1-4, got {sorted(found)}")
for number, (path, body) in sorted(found.items()):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    print(number, path.relative_to(TOOL), len(body.splitlines()), "lines")
