"""Read-only inventory/rendering of the final native Google Docs PDF export."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pdfplumber


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=Path(__file__).parent / "drive-final.pdf")
    parser.add_argument("--previous-pages", type=int, default=15)
    parser.add_argument("--dpi", type=int, default=144)
    args = parser.parse_args()
    root = args.pdf.parent
    inventory = []
    with pdfplumber.open(args.pdf) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            images = [
                {key: item.get(key) for key in ("x0", "x1", "top", "bottom", "width", "height", "srcsize", "name")}
                for item in page.images
            ]
            nonblank = [char for char in page.chars if char.get("text", "").strip()]
            overflow = [char for char in nonblank if char["x0"] < 71.5 or char["x1"] > page.width - 71.5]
            tables = page.find_tables()
            fonts = Counter(round(char["size"], 2) for char in nonblank)
            inventory.append(
                {
                    "page": index,
                    "width": page.width,
                    "height": page.height,
                    "text_start": text[:240],
                    "images": images,
                    "table_boxes": [list(table.bbox) for table in tables],
                    "font_sizes_character_counts": dict(sorted(fonts.items())),
                    "horizontal_text_margin_overflow_count": len(overflow),
                    "overflow_examples": [{key: char.get(key) for key in ("text", "x0", "x1", "top")} for char in overflow[:12]],
                    "image_margin_overflow": [item for item in images if item["x0"] < 71.5 or item["x1"] > page.width - 71.5],
                    "image_page_overflow": [item for item in images if item["x0"] < 0 or item["x1"] > page.width or item["top"] < 0 or item["bottom"] > page.height],
                }
            )
            (root / f"page-{index:02d}.txt").write_text(text, encoding="utf-8")

    selected = sorted({7, 8} | {row["page"] for row in inventory if row["page"] > args.previous_pages})
    selected = [number for number in selected if number <= len(inventory)]
    binary = shutil.which("pdftoppm")
    if not binary:
        raise RuntimeError("Bundled/system pdftoppm is unavailable")
    for number in selected:
        subprocess.run(
            [binary, "-f", str(number), "-l", str(number), "-singlefile", "-r", str(args.dpi), "-png", str(args.pdf), str(root / f"page-{number:02d}")],
            check=True,
            capture_output=True,
            text=True,
        )
    result = {
        "pdf": str(args.pdf.resolve()),
        "sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest().upper(),
        "bytes": args.pdf.stat().st_size,
        "pages": len(inventory),
        "rendered_pages": selected,
        "dpi": args.dpi,
        "inventory": inventory,
        "note": "Geometry inventory supplements visual PNG review; these flags are not automatic acceptance results.",
    }
    (root / "layout-inventory.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("sha256", "bytes", "pages", "rendered_pages", "dpi")}, indent=2))
    print(json.dumps({"selected_page_overview": [row for row in inventory if row["page"] in selected]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
