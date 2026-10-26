"""Retain publication hashes and observed automatic quota result; no model calls."""
import json
import shutil
from pathlib import Path
from pypdf import PdfReader
from PIL import Image
from kiro_research import DOCS, STAGE, digest, load, stamp, write

publication = load(DOCS / "drive-final-publication.json")
assert publication["status"] == "published_readback_and_layout_verified"
assert publication["new_table_cells_verified"] == 143
readback = load(DOCS / "publication-qa/final-readback.json")
assert len(readback["tables"]) == 4 and len(readback["image_ids"]) == 17
pdf = DOCS / "publication-qa/drive-final.pdf"
reader = PdfReader(pdf)
assert len(reader.pages) == 53
pdf_text = "\n".join(p.extract_text() or "" for p in reader.pages[45:])
for required in ("120", "49", "101,369363", "19506ab6-d54d-41c6-ab8c-0702cb42ac9b", "S2-20"):
    assert required in pdf_text, required
rows = []
for item in publication["new_screenshots"]:
    path = DOCS / "screenshots" / item["file"]
    with Image.open(path) as img:
        assert img.format == "JPEG"
        size = list(img.size)
    rows.append({"path": path.relative_to(DOCS).as_posix(), "format": "JPEG", "pixels": size, "sha256": digest(path.read_bytes())})
for name in ("FINAL_REPORT.json", "FINAL_REPORT.md", "metrics.json", "input-audit.json", "question-audit.json", "publication-qa/drive-final.pdf", "publication-qa/final-readback.json"):
    path = DOCS / name
    rows.append({"path": name, "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size})
write(DOCS / "publication-qa/verified-hashes.json", {"researcher_created": True, "created_at_utc": stamp(), "revision": publication["revision"], "scope": "Published final tables, selected actual/derived screenshots, native-derived metrics and final PDF; no signed download links retained", "files": rows})
quota = STAGE / "shared/quota-monitor/last-result.json"
shutil.copy2(quota, DOCS / "publication-qa/quota-automatic-last-result.json")
assert load(DOCS / "publication-qa/quota-automatic-last-result.json")["timestampUtc"] == "2026-10-23T20:13:22.843Z"
assert load(DOCS / "publication-qa/quota-automatic-last-result.json")["decision"] == "continue"
print(json.dumps({"status": "verified", "pdf_pages": len(reader.pages), "screenshot_hashes": len(publication["new_screenshots"]), "metric_and_document_hashes": len(rows)-len(publication["new_screenshots"])}))
