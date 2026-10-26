"""Preserve immutable, content-addressed copies of Tessl Gemini research transcripts."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--tool", default="Tessl")
args = parser.parse_args()
stage = Path(__file__).resolve().parent.parent
docs = stage / args.tool / "docs"
archive = docs / "transcripts-archive"
archive.mkdir(parents=True, exist_ok=True)
manifest_path = archive / "manifest.json"
rows = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
known = {(row["source"], row["sha256"]) for row in rows}
added = 0
for source in sorted((docs / "gemini-home").rglob("session-*.jsonl")):
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest().upper()
    source_name = source.relative_to(docs).as_posix()
    key = (source_name, digest)
    if key in known:
        continue
    target = archive / f"{source.stem}.{digest[:16]}.jsonl"
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest().upper() != digest:
            raise RuntimeError(f"Archive digest mismatch: {target.name}")
    else:
        with target.open("xb") as stream:
            stream.write(data)
    rows.append({"source": source_name, "archive": target.relative_to(docs).as_posix(), "sha256": digest, "bytes": len(data), "copied_at_utc": datetime.now(timezone.utc).isoformat(), "source_modified_at_utc": datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat()})
    known.add(key)
    added += 1
manifest_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"archived_new_snapshots": added, "total_snapshots": len(rows), "manifest": str(manifest_path)}))
