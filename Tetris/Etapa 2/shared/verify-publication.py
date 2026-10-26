"""Verifica el snapshot publicado sin instalar dependencias ni ejecutar herramientas IA."""
from pathlib import Path
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    manifest = read_json(ROOT / "publication-manifest.json")
    mismatches = []
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Ruta del manifiesto fuera del snapshot")
        if not path.is_file():
            mismatches.append(entry["path"])
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            mismatches.append(entry["path"])
    if mismatches:
        raise AssertionError(f"Archivos ausentes o distintos: {mismatches}")

    seed = hashlib.sha256((ROOT / "shared" / "seed.md").read_bytes()).hexdigest()
    expected_seed = "63919779dd4104076fbabcb130ce296a160fa840e0b4755a2aa5d90757ada8ef"
    assert seed == expected_seed, "La semilla no coincide con el protocolo congelado"
    runs = {}
    for name in ["OpenSpec", "Spec Kit", "Tessl", "Bmad Method", "Kiro"]:
        docs = ROOT / name / "docs"
        metrics = read_json(docs / "metrics.json")
        sonar = read_json(docs / "sonar-summary.json")
        assert sonar["gate"] == "OK", f"Gate archivado inesperado: {name}"
        runs[name] = len(metrics["runs"])
    assert runs == {"OpenSpec": 10, "Spec Kit": 17, "Tessl": 8, "Bmad Method": 7, "Kiro": 7}
    with (ROOT / "shared" / "report" / "invocaciones.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 49

    report = ROOT / "shared" / "report" / "tetris-etapa2-overleaf.tex"
    text = report.read_text(encoding="utf-8")
    assert text.count(r"\begin{table}") == 19
    assert text.count(r"\includegraphics") == 19  # Cinco gráficas y catorce capturas.
    print(json.dumps({"status": "verified", "files": len(manifest["files"]),
                      "seed_sha256": seed, "runs": runs, "total_attempts": sum(runs.values()),
                      "tables": 19, "charts": 5, "screenshots": 14}, ensure_ascii=False))


if __name__ == "__main__":
    main()
