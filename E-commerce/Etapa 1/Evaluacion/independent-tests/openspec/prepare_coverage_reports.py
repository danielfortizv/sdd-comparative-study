import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent

lcov_source = root / "coverage-frontend" / "lcov.info"
lcov_target = root / "coverage-frontend-sonar.lcov"
lines = []
for line in lcov_source.read_text(encoding="utf-8").splitlines():
    if line.startswith("SF:"):
        source = line[3:].replace("\\", "/")
        line = f"SF:frontend/{source}"
    lines.append(line)
lcov_target.write_text("\n".join(lines) + "\n", encoding="utf-8")

xml_path = root / "coverage-backend.xml"
tree = ET.parse(xml_path)
xml_root = tree.getroot()
sources = xml_root.find("sources")
if sources is not None:
    for child in list(sources):
        sources.remove(child)
    ET.SubElement(sources, "source").text = str(root / "frozen-first-implementation")
for class_node in xml_root.findall(".//class"):
    filename = class_node.get("filename", "")
    if not filename.startswith("backend/"):
        class_node.set("filename", f"backend/app/{filename}")
tree.write(xml_path, encoding="utf-8", xml_declaration=True)

frontend = json.loads((root / "coverage-frontend" / "coverage-summary.json").read_text(encoding="utf-8"))["total"]["lines"]
backend = json.loads((root / "coverage-backend.json").read_text(encoding="utf-8"))["totals"]
covered = frontend["covered"] + backend["covered_lines"]
total = frontend["total"] + backend["num_statements"]
summary = {
    "frontend": {"covered_lines": frontend["covered"], "executable_lines": frontend["total"], "line_coverage_percent": frontend["pct"]},
    "backend": {"covered_lines": backend["covered_lines"], "executable_lines": backend["num_statements"], "line_coverage_percent": backend["percent_covered"]},
    "combined": {"covered_lines": covered, "executable_lines": total, "line_coverage_percent": round(covered * 100 / total, 4)},
}
(root / "coverage-summary-combined.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
