"""Archive only experiment ACP streams and their identified native Kiro sessions."""
import argparse
from pathlib import Path

from kiro_research import DOCS, digest, load, native_session_paths, stamp, stream_for_run, stream_session_ids, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", action="append", default=[], help="Additional exact experiment session ID; never archives unrelated sessions")
    args = parser.parse_args()
    archive = DOCS / "transcripts-archive"
    archive.mkdir(exist_ok=True)
    manifest_path = archive / "manifest.json"
    rows = load(manifest_path, [])
    existing = {(r["source"], r["sha256"]) for r in rows}
    sources = []
    sids = set(args.session_id)
    for path in sorted(DOCS.glob("*.stdout.jsonl")):
        label = path.name.removesuffix(".stdout.jsonl")
        sources.append((path, "acp_stream", label, None))
        sids.update(stream_session_ids(stream_for_run(label)))
    for sid, path in native_session_paths(sorted(sids)):
        sources.append((path, "native_session", None, sid))
        if (path.parent / "messages.jsonl").exists():
            sources.append((path.parent / "messages.jsonl", "native_messages", None, sid))
    added = 0
    for path, kind, label, sid in sources:
        data = path.read_bytes()
        sha = digest(data)
        key = (str(path), sha)
        if key in existing:
            continue
        stem = label if kind == "acp_stream" else sid
        suffix = ".jsonl" if path.suffix == ".jsonl" else ".json"
        target = archive / f"{stem}.{kind}.{sha[:16]}{suffix}"
        if target.exists():
            if digest(target.read_bytes()) != sha:
                raise RuntimeError("Archive hash collision/mismatch")
        else:
            with target.open("xb") as stream:
                stream.write(data)
        rows.append({"source": str(path), "archive": target.relative_to(DOCS).as_posix(), "sha256": sha, "bytes": len(data), "kind": kind, "run_label": label, "session_id": sid, "copied_at_utc": stamp()})
        existing.add(key)
        added += 1
    write(manifest_path, rows)
    print({"added_snapshots": added, "all_snapshots": len(rows), "identified_sessions": sorted(sids), "manifest": str(manifest_path)})


if __name__ == "__main__":
    main()
