"""Render local evidence panels from retained measurements and raw logs.

The HTML panels are meant for reproducible browser screenshots. They are not
substitutes for the linked JSON and CLI logs from which they are generated.
"""

from __future__ import annotations

import html
import argparse
import json
import re
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--tool", default="OpenSpec")
ARGS = parser.parse_args()
ROOT = Path(__file__).resolve().parent.parent / ARGS.tool / "docs"
OUT = ROOT / "screenshots"


def h(value) -> str:
    return html.escape(str(value))


def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def log_text(name: str) -> str:
    raw = (ROOT / name).read_text(encoding="utf-8-sig", errors="replace")
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", raw)


def wrap(title: str, subtitle: str, body: str) -> str:
    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>{h(title)}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#09111f;color:#e8f0ff;font:18px/1.45 Segoe UI,Arial,sans-serif;padding:48px}}
h1{{font-size:36px;margin:0 0 8px;color:#65e9f5}}h2{{font-size:23px;color:#a9b9ff;margin:34px 0 14px}}
.sub{{color:#b4c3d9;margin-bottom:30px}}.cards{{display:flex;gap:18px;flex-wrap:wrap}}.card{{background:#14233a;border:1px solid #294362;border-radius:12px;padding:20px;min-width:220px}}
.num{{font-size:30px;font-weight:700;color:#8fffc4}}.lbl{{font-size:14px;color:#bdc9da;text-transform:uppercase;letter-spacing:.07em}}
table{{width:100%;border-collapse:collapse;background:#101e31;font-size:15px}}th,td{{padding:11px 12px;border:1px solid #29415b;text-align:left;vertical-align:top}}th{{background:#18304a;color:#8deeff}}tr:nth-child(even){{background:#15243a}}
.note{{color:#c9d4e5;font-size:14px;margin-top:24px}}pre{{background:#101e31;border:1px solid #29415b;border-radius:8px;padding:18px;white-space:pre-wrap;font:13px/1.35 Consolas,monospace}}
</style><body><h1>{h(title)}</h1><div class="sub">{h(subtitle)}</div>{body}</body></html>"""


def table(headers: list[str], rows: list[list]) -> str:
    head = "".join(f"<th>{h(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{h(item)}</td>" for item in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def card(label: str, value) -> str:
    return f'<div class="card"><div class="num">{h(value)}</div><div class="lbl">{h(label)}</div></div>'


def metrics_panel():
    m = load("metrics.json")
    rows = []
    for run in m["runs"]:
        t = run["tokens"]
        rows.append([
            run["label"], run.get("duration_seconds") or "no medido",
            t.get("input_tokens") if t.get("input_tokens") is not None else "no disponible",
            t.get("cached_tokens") if t.get("cached_tokens") is not None else "no disponible",
            t.get("output_tokens") if t.get("output_tokens") is not None else "no disponible",
            t.get("thought_tokens") if t.get("thought_tokens") is not None else "no disponible",
            run.get("exit_code"),
        ])
    b = m["source_baseline"]
    f = m.get("source_final", m.get("source_current"))
    s = m["spec_stage2"]
    body = '<div class="cards">' + "".join([
        card("intentos de invocación cerrados", m.get("invocation_attempts", m["prompt_count"])),
        card("tiempo conocido de invocaciones, s", round(m["total_duration_seconds"], 1)),
        card("tokens de entrada observados", f'{m["observed_tokens"]["input_tokens"]:,}'),
        card("tokens de salida observados", f'{m["observed_tokens"]["output_tokens"]:,}'),
    ]) + '</div><h2>Sesiones Gemini CLI</h2>' + table(
        ["Invocación", "Segundos", "Entrada", "Caché¹", "Salida candidata", "Pensamiento", "Salida CLI"], rows
    ) + '<h2>Artefactos medidos</h2>' + table(
        ["Alcance", "Archivos", "Líneas", "Caracteres"],
        [["Código base", b["files"], b["lines"], b["characters"]],
         ["Código Etapa 2", f["files"], f["lines"], f["characters"]],
         ["Specs Etapa 2", s["files"], s["lines"], s["characters"]]],
    ) + '<div class="note">¹ Caché es un subconjunto de entrada. Los pensamientos se registran aparte de la salida candidata. Tiempo: suma conocida de invocaciones instrumentadas, no tiempo total de investigación. Fuente: docs/metrics.json, JSON y JSONL originales. Intentos sin estadísticas quedan como «no disponible». Los recuentos de código incluyen pruebas y excluyen dependencias y docs.</div>'
    (OUT / "metrics-panel.html").write_text(wrap(f"Tetris Etapa 2 · Métricas {ARGS.tool}", "Panel local generado desde los archivos originales de evidencia", body), encoding="utf-8")

    api = m.get("known_api_totals", {})
    request_rows = []
    for run in m["runs"]:
        t = run["tokens"]
        request_rows.append([run["label"], *[t.get(key) if t.get(key) is not None else "desconocido" for key in ("api_requests", "api_errors", "api_successful_requests", "recorded_response_count")]])
    request_body = '<div class="cards">' + ''.join([
        card("intentos API conocidos", api.get("api_requests", "—")),
        card("errores API conocidos", api.get("api_errors", "—")),
        card("intentos API exitosos conocidos", api.get("api_successful_requests", "—")),
        card("respuestas JSONL documentadas", m.get("recorded_response_count", "—")),
    ]) + '</div><h2>Solicitudes y respuestas: medidas distintas</h2>' + table(
        ["Invocación", "Intentos API", "Errores API", "Éxitos API", "Respuestas JSONL"], request_rows
    ) + '<div class="note">No se suman intentos API y respuestas JSONL. Los fallos de lanzamiento anteriores al modelo son ceros comprobados. Un JSONL no demuestra intentos fallidos ni necesariamente conserva llamadas auxiliares. Las sesiones sin estadísticas API siguen siendo desconocidas. La caché no se suma de nuevo a entrada. Fuente: docs/metrics.json y los registros originales.</div>'
    (OUT / "requests-panel.html").write_text(wrap(f"Tetris Etapa 2 · Solicitudes {ARGS.tool}", "Auditoría de estadísticas de Gemini CLI; las magnitudes tienen denominadores distintos", request_body), encoding="utf-8")


def sonar_panel():
    before_name = "sonar-initial/sonar-summary.json" if (ROOT / "sonar-initial/sonar-summary.json").exists() else "sonar-baseline/sonar-summary.json"
    before = load(before_name)
    after = load("sonar-summary.json")
    gate = load("sonar-quality-gate.json")["projectStatus"]
    new_coverage = next((x["actualValue"] for x in gate["conditions"] if x["metricKey"] == "new_coverage"), "—")
    frontend = log_text("frontend-test-coverage.log")
    frontend_lines = re.search(r"(?m)^Lines\s*:\s*([\d.]+)%", frontend)
    frontend_tests = re.search(r"(?m)^\s*Tests\s+(\d+) passed", frontend)
    backend = log_text("backend-coverage.log")
    backend_tests = re.search(r"(\d+) passed", backend)
    keys = ["gate", "coverage", "bugs", "vulnerabilities", "security_hotspots", "code_smells", "duplicated_lines_density", "ncloc", "complexity", "cognitive_complexity"]
    rows = [[key, before.get(key, "—"), after.get(key, "—")] for key in keys]
    body = '<div class="cards">' + "".join([
        card("quality gate final", after.get("gate", "—")),
        card("vulnerabilidades finales", after.get("vulnerabilities", "—")),
        card("olores finales", after.get("code_smells", "—")),
        card("cobertura global final", str(after.get("coverage", "—")) + "%"),
        card("cobertura código nuevo", str(new_coverage) + "%"),
    ]) + '</div><h2>Primer escaneo y escaneo final</h2>' + table(["Métrica SonarQube", "Inicial", "Final"], rows)
    acceptance = load("acceptance-api.json")
    passed = sum(item["status"] == "pass" for item in acceptance["cases"])
    body += '<h2>Pruebas</h2><div class="cards">' + "".join([
        card("backend aprobadas", backend_tests.group(1) if backend_tests else "—"),
        card("frontend aprobadas", frontend_tests.group(1) if frontend_tests else "—"),
        card("API externas aprobadas", f"{passed}/{len(acceptance['cases'])}"),
        card("cobertura líneas frontend", (frontend_lines.group(1) + "%") if frontend_lines else "—"),
    ]) + '</div>'
    body += '<pre>' + h("\n".join(backend.splitlines()[-14:])) + '</pre>'
    body += '<div class="note">Panel generado desde la API local SonarQube y los registros de pruebas; no es una captura de la interfaz de SonarQube. API externa: siete controles que cubren ocho IDs, no veinte casos de catálogo. SonarQube no calcula una puntuación de escalabilidad. Fuentes: docs/sonar-initial/*.json, docs/sonar-summary.json, docs/sonar-quality-gate.json, docs/backend-coverage.log, docs/frontend-test-coverage.log y docs/acceptance-api.json. Los informes exact-task y verification vinculan el análisis final con el escaneo enviado.</div>'
    (OUT / "sonar-panel.html").write_text(wrap("Tetris Etapa 2 · SonarQube", "Comparación reproducible de métricas de calidad y pruebas", body), encoding="utf-8")


def tests_panel():
    commands = load("verification-commands.json")
    if isinstance(commands, dict):
        commands = [commands]
    body = table(["Verificación", "Código de retorno", "Archivo original"], [
        [row["name"], row["exit_code"], Path(row["log"]).name] for row in commands
    ])
    for title, filename, tail in [
        ("Backend: cobertura y resultado", "backend-coverage.log", 17),
        ("Frontend: cobertura y resultado", "frontend-test-coverage.log", 30),
        ("Compilación de producción", "frontend-build.log", 12),
    ]:
        body += '<h2>' + h(title) + '</h2><pre>' + h('\n'.join(log_text(filename).splitlines()[-tail:])) + '</pre>'
    audit = load("npm-audit.json")
    body += '<h2>Dependencias npm</h2><pre>' + h(json.dumps(audit.get("metadata", {}).get("vulnerabilities", {}), indent=2)) + '</pre>'
    body += '<div class="note">Visor local de registros originales; no es una captura de una consola. Solo se retiran códigos ANSI de color para legibilidad. Comandos completos, argumentos, fechas y códigos de retorno: docs/verification-commands.json. Los archivos originales no se modifican.</div>'
    (OUT / "tests-panel.html").write_text(wrap(f"Tetris Etapa 2 · Pruebas {ARGS.tool}", "Ejecución independiente del investigador sobre la versión verificada", body), encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    metrics_panel()
    sonar_panel()
    if (ROOT / "verification-commands.json").exists():
        tests_panel()
    print(OUT / "metrics-panel.html")
    print(OUT / "requests-panel.html")
    print(OUT / "sonar-panel.html")
