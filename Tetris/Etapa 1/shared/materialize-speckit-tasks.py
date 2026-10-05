"""Copy Gemini's generated Spec Kit task checklist into its native path."""

from pathlib import Path

root = Path(__file__).resolve().parents[1] / "Spec Kit"
source = (root / "docs" / "tasks.stdout.txt").read_text(encoding="utf-8-sig")
opening = "```markdown\n"
start = source.find(opening)
end = source.rfind("\n```")
if start < 0 or end <= start:
    raise ValueError("Expected markdown fence missing")
body = source[start + len(opening) : end].strip() + "\n"
target = root / "specs" / "001-build-tetris-core" / "tasks.md"
target.write_text(body, encoding="utf-8")
count = sum(line.startswith("- [ ] T") for line in body.splitlines())
print(f"Wrote {target}: {count} task lines")
