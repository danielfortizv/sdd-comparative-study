"""Build a Spanish final research report only from complete, current evidence.

Researcher helper: never runs application commands, scanners, models or uploads.
Use --check while QA is open. Default mode refuses to write FINAL_REPORT.md
unless every gate is supported by the supplied local evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STAGE = Path(__file__).resolve().parent.parent
ROOT = STAGE / "Spec Kit"
DOCS = ROOT / "docs"
EXPECTED_CASES = {f"S2-{number:02}" for number in range(1, 21)}
REQUIRED_COMMANDS = {
    "backend-tests-and-coverage", "frontend-tests-and-coverage",
    "frontend-production-build", "frontend-dependency-audit",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def stamp(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 10**11 else value, timezone.utc)
    value = re.sub(r"(\.\d{6})\d+", r"\1", str(value).replace("Z", "+00:00"))
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def fmt(value, decimals=0) -> str:
    if value is None:
        return "no disponible"
    rendered = f"{float(value):,.{decimals}f}"
    return rendered.replace(",", "_").replace(".", ",").replace("_", ".")


def cell(value) -> str:
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return str(value if value is not None else "no disponible").replace("|", "\\|").replace("\n", " ")


def rows(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("rows", "cases", "scenarios", "controls"):
            if isinstance(value.get(key), list):
                return value[key]
    return []


def status(value) -> str:
    return str(value.get("status", value.get("overall_status", ""))).lower() if isinstance(value, dict) else ""


def evidence_path(value: str) -> Path:
    value = str(value).strip().strip("`")
    value = value.split("#", 1)[0].split("::", 1)[0]
    value = re.sub(r":\d+(?:-\d+)?$", "", value)
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [DOCS / path, ROOT / path, STAGE / path]
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])


def evidence_items(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item.get("path", item.get("file", ""))) if isinstance(item, dict) else str(item) for item in value]
    return []


def collect_evidence() -> tuple[dict, list[str]]:
    errors = []
    loaded = {}

    def require(condition, message):
        if not condition:
            errors.append(message)

    def load(name, required=True):
        path = DOCS / name
        if not path.exists():
            if required:
                errors.append("Falta " + name)
            return {}
        try:
            result = json.loads(read(path))
            loaded[name] = result
            return result
        except (ValueError, OSError) as exc:
            errors.append(f"No se pudo leer {name}: {exc}")
            return {}

    metrics = load("metrics.json")
    inputs = load("input-audit.json")
    questions = load("question-audit.json")
    environment = load("environment.json")
    commands = load("verification-commands.json")
    api = load("acceptance-api.json")
    matrix = load("acceptance-matrix.json")
    browser = load("browser-evidence.json")
    contract = load("acceptance-contract.json")
    provenance = load("acceptance-provenance.json")
    sonar = load("sonar-summary.json")
    load("sonar-baseline/sonar-summary.json")
    load("sonar-initial/sonar-summary.json")
    sonar_verification = load("sonar-verification.json")
    exact_task = load("sonar-exact-task.json")
    exact_gate = load("sonar-exact-quality-gate.json")
    latest_task = load("sonar-task.json")
    open_issues = load("sonar-open-issues.json")
    audit = load("npm-audit.json")
    final_corpus = load("bertopic-corpus/final/manifest.json")

    closed = {path.name.removesuffix(".run.json") for path in DOCS.glob("*.run.json")}
    started = {path.name.removesuffix(".started.json") for path in DOCS.glob("*.started.json")}
    open_labels = sorted(started - closed)
    require(not open_labels, "Hay invocaciones abiertas: " + ", ".join(open_labels))
    require(not metrics.get("unclosed_invocation_labels"), "metrics.json declara invocaciones abiertas")
    metric_runs = metrics.get("runs", [])
    require(bool(metric_runs) and {row.get("label") for row in metric_runs} == closed, "metrics.json no cubre exactamente las invocaciones cerradas")
    require(not metrics.get("correction_counts", {}).get("unclassified_labels"), "Hay invocaciones sin categorizar")
    input_by_label = {row.get("label"): row for row in inputs.get("runs", [])}
    require(set(input_by_label) == closed, "input-audit.json no cubre todas las invocaciones cerradas")
    question_labels = {row.get("label") for row in questions.get("runs", [])}
    require(question_labels == closed and not questions.get("pending_run_labels"), "question-audit.json está incompleto o tiene sesiones pendientes")
    require(questions.get("closed_runs_observed_blocking_question_count") is not None, "Falta conteo observado de preguntas")
    loaded["_seed_delivery_notes"] = []
    for row in metric_runs:
        category = row.get("classification", {}).get("category")
        if category in {"initial_implementation", "postimplementation_external_correction"}:
            input_row = input_by_label.get(row["label"], {})
            seed_ok = input_row.get("complete_seed_present") is True
            if not seed_ok and row["label"] == "13-qa-completion-retry":
                # This one no-code resume first persists synthetic CLI context
                # and replayed input. Preserve that first-record deviation while
                # verifying the actual submitted full prompt before model work.
                # Code-producing invocations still require complete first input.
                replay = load("13-input-replay-verification.json")
                stdout = load("13-qa-completion-retry.stdout.json")
                submission = replay.get("matching_actual_submission", {})
                source_hashes = replay.get("source_hashes", {})
                hashes_ok = bool(source_hashes) and all((DOCS / name).is_file() and digest(DOCS / name) == value for name, value in source_hashes.items())
                tool_names = set(stdout.get("stats", {}).get("tools", {}).get("byName", {}))
                no_code = stdout.get("response") == "" and tool_names == {"update_topic"} and stdout.get("stats", {}).get("files") == {"totalLinesAdded": 0, "totalLinesRemoved": 0}
                try:
                    precedes = stamp(submission.get("timestamp")) < stamp(replay.get("first_token_response_timestamp"))
                except (ValueError, TypeError):
                    precedes = False
                seed_ok = status(replay) == "pass" and hashes_ok and no_code and precedes and input_row.get("complete_seed_in_effective_submission") is True and submission.get("complete_seed_present") is True and submission.get("raw_utf8_sha256") == row.get("prompt_sha256")
                if seed_ok:
                    loaded["_seed_delivery_notes"].append("En 13, el primer registro user es contexto sintético/repetición del CLI y no contiene la semilla. El prompt real íntegro, con hash idéntico al previsto, se registró después y antes de la primera respuesta con tokens. Solo hubo update_topic y 0/0 líneas: no produjo trabajo de aplicación. La desviación del primer registro queda preservada; no se relaja el requisito de semilla completa para las correcciones que producen código. Evidencia: 13-input-replay-verification.json.")
            require(seed_ok, "Semilla efectiva no acreditada para " + row["label"])

    seed = STAGE / "shared" / "seed.md"
    require(inputs.get("seed_sha256") == digest(seed), "El hash de la semilla maestra no coincide")
    for row in metric_runs:
        require(row.get("seed_sha256") == digest(seed), "Hash de semilla de invocación distinto: " + row["label"])
    require(environment.get("seed_sha256") == digest(seed), "environment.json no acredita la semilla actual")

    current_files = []
    for scope in ("source_current", "spec_stage2", "spec_stage1_copy"):
        for name, item in metrics.get(scope, {}).get("per_file", {}).items():
            path = ROOT / name
            require(path.exists(), "Artefacto medido ausente: " + name)
            if path.exists():
                require(item.get("sha256") == digest(path), "Métricas desactualizadas: " + name)
                if scope == "source_current":
                    current_files.append(path)
    require(bool(current_files), "No hay manifiesto de fuentes actual")
    latest_source = max((path.stat().st_mtime for path in current_files), default=0)
    frozen = load("generation-08/metrics.json")
    for scope in ("source_baseline", "spec_stage1"):
        before = frozen.get(scope, {}).get("per_file", {})
        after = metrics.get(scope, {}).get("per_file", {})
        require(bool(before) and set(before) == set(after), "Falta comparación original de Etapa 1: " + scope)
        for name in set(before) & set(after):
            require(before[name].get("sha256") == after[name].get("sha256"), "Etapa 1 cambió durante el estudio: " + name)
    require(metrics.get("spec_stage1_copy_change", {}).get("changed_file_count") == 0, "Las specs copiadas de Etapa 1 fueron alteradas")

    command_rows = rows(commands)
    command_by_name = {row.get("name"): row for row in command_rows}
    require(REQUIRED_COMMANDS <= set(command_by_name), "Faltan comandos finales requeridos")
    for name in REQUIRED_COMMANDS & set(command_by_name):
        row = command_by_name[name]
        require(row.get("exit_code") == 0, "Comando no aprobado: " + name)
        path = evidence_path(row.get("log", ""))
        require(path.is_file() and path.stat().st_size > 0, "Falta salida original: " + name)
        try:
            require(stamp(row["started_at_utc"]).timestamp() >= latest_source, "Comando anterior al último cambio de fuente/pruebas: " + name)
        except (ValueError, KeyError, TypeError):
            errors.append("Fecha verificable ausente en comando: " + name)
    vulnerabilities = audit.get("metadata", {}).get("vulnerabilities", {})
    require(vulnerabilities.get("total") == 0 and "error" not in audit, "npm audit no acredita cero vulnerabilidades")

    case_rows = api.get("cases", [])
    expected_checker_ids = {"S2-01", "S2-02", "S2-10", "S2-11", "S2-03/S2-12", "S2-15", "S2-16"}
    require(len(case_rows) == 7 and {row.get("id") for row in case_rows} == expected_checker_ids and all(status(row) == "pass" for row in case_rows), "El checker compartido no tiene sus siete registros aprobados")
    matrix_rows = rows(matrix)
    require(len(matrix_rows) == 20 and {row.get("id") for row in matrix_rows} == EXPECTED_CASES, "La matriz debe contener exactamente los veinte IDs del catálogo")
    for row in matrix_rows:
        require(status(row) == "pass", "Aceptación pendiente/fallida: " + str(row.get("id")))
        require(bool(row.get("mechanism")), "Falta mecanismo: " + str(row.get("id")))
        evidence = evidence_items(row.get("evidence"))
        require(bool(evidence), "Falta evidencia: " + str(row.get("id")))
        for value in evidence:
            require(bool(value) and evidence_path(value).is_file(), f"Referencia de aceptación ausente ({row.get('id')}): {value}")
        if row.get("id") in {"S2-06", "S2-07"}:
            mechanism = str(row.get("mechanism", "")).lower()
            require("domain" in mechanism or "dominio" in mechanism, "Tres/cuatro filas debe identificarse como dominio aislado")
            require(row.get("isolated") is True or row.get("domain_only") is True or "isolat" in mechanism or "aislad" in mechanism, "Falta etiqueta de fixture aislado: " + row["id"])
    require(status(contract) == "pass", "Contrato suplementario S2-16 no aprobado")
    contract_cases = rows(contract)
    require(len(contract_cases) == 9 and all(status(row) == "pass" for row in contract_cases), "El contrato suplementario debe acreditar sus nueve controles HTTP")

    checker = STAGE / "shared" / "acceptance" / "check_api.py"
    checker_files = provenance.get("checker_files", [])
    checker_paths = {evidence_path(item.get("path", "")).resolve(): item for item in checker_files}
    for expected_checker in (checker, STAGE / "shared" / "acceptance" / "check_contract.py"):
        item = checker_paths.get(expected_checker.resolve(), {})
        legacy = provenance.get("checker_sha256", "") if expected_checker == checker else ""
        require(expected_checker.is_file() and str(item.get("sha256", legacy)).upper() == digest(expected_checker), "No se acredita el hash del checker ejecutado: " + expected_checker.name)
    backend_hashes = provenance.get("backend_source_sha256", provenance.get("backend_hashes", {}))
    if provenance.get("backend_app_files"):
        backend_hashes = {item.get("path", ""): item.get("sha256", "") for item in provenance["backend_app_files"]}
    require(isinstance(backend_hashes, dict) and bool(backend_hashes), "Falta mapa de hashes backend en acceptance-provenance.json")
    for name, sha in backend_hashes.items() if isinstance(backend_hashes, dict) else []:
        path = evidence_path(name)
        require(path.is_file() and digest(path) == str(sha).upper(), "Backend de aceptación no coincide: " + name)
    origin = provenance.get("server_origin", provenance.get("base_url"))
    require(bool(origin) and origin == api.get("base_url"), "Origen de servidor API no acreditado")
    require(bool(provenance.get("backend_origin", provenance.get("server_origin"))), "Falta procedencia del proceso backend de aceptación")
    expected_backend_paths = {path.resolve() for path in (ROOT / "backend" / "app").rglob("*.py")}
    actual_backend_paths = {evidence_path(name).resolve() for name in backend_hashes} if isinstance(backend_hashes, dict) else set()
    require(expected_backend_paths == actual_backend_paths, "El manifiesto API no cubre exactamente los archivos backend/app Python actuales")

    observations = browser.get("observations", [])
    captures = browser.get("captures", [])
    require(bool(observations) and all(status(item) == "pass" for item in observations), "Observaciones de navegador ausentes o pendientes")
    require(bool(captures) and any(item.get("kind") == "actual_ui" for item in captures), "Falta captura real de la interfaz")
    for item in captures:
        path = evidence_path(item.get("path", ""))
        require(path.is_file() and path.stat().st_size > 0, "Captura ausente: " + str(item.get("path")))
        require(bool(item.get("caption")) and item.get("kind") in {"actual_ui", "actual_cli", "actual_sonar", "derived_panel"}, "Captura sin descripción/procedencia explícita")
        if item.get("kind") == "derived_panel":
            require(bool(item.get("raw_sources")), "Panel derivado sin fuentes originales")
        for value in evidence_items(item.get("raw_sources")):
            require(evidence_path(value).is_file(), "Fuente original de captura ausente: " + value)

    task = exact_task.get("task", {})
    current_task = latest_task.get("current", {})
    require(task.get("status") == "SUCCESS" and task.get("analysisId"), "El análisis Sonar exacto no está completado")
    require(not latest_task.get("queue") and current_task.get("id") == task.get("id") and current_task.get("status") == "SUCCESS", "El análisis Sonar verificado no es el último análisis completado")
    require(sonar_verification.get("ce_status") == "SUCCESS" and sonar_verification.get("ce_task_id") == task.get("id") and sonar_verification.get("analysis_id") == task.get("analysisId"), "IDs de verificación Sonar inconsistentes")
    require(sonar_verification.get("project_key") == "tetris-stage2-speckit", "Proyecto Sonar inesperado")
    project_status = exact_gate.get("projectStatus", {})
    require(project_status.get("status") == "OK" and not project_status.get("ignoredConditions") and sonar_verification.get("gate_status") == "OK" and sonar.get("gate") == "OK", "Quality gate final no aprobado")
    thresholds = {"new_coverage": 80, "new_duplicated_lines_density": 3, "new_violations": 0}
    conditions = {item.get("metricKey"): item for item in project_status.get("conditions", [])}
    for name, threshold in thresholds.items():
        item = conditions.get(name, {})
        try:
            require(float(item.get("errorThreshold")) == threshold and item.get("status") == "OK", "Condición Sonar alterada o fallida: " + name)
        except (TypeError, ValueError):
            errors.append("Condición Sonar ausente: " + name)
    require(open_issues.get("total") == 0 and not open_issues.get("issues"), "Persisten issues Sonar abiertos")
    for name in ("bugs", "vulnerabilities", "security_hotspots", "code_smells"):
        require(str(sonar.get(name)) == "0", "Métrica Sonar no es cero: " + name)
    report_task = ROOT / ".sonar" / "report-task.txt"
    require(report_task.exists() and sonar_verification.get("report_task_sha256") == digest(report_task), "report-task.txt no corresponde al análisis verificado")
    coverage_inputs = {item.get("path"): item for item in sonar_verification.get("coverage_inputs", [])}
    for name in ("docs/coverage.xml", "frontend/coverage/lcov.info"):
        path = ROOT / name
        item = coverage_inputs.get(name, {})
        require(path.is_file() and path.stat().st_size > 0 and item.get("exists") is True and item.get("sha256") == digest(path), "Cobertura Sonar ausente o desactualizada: " + name)
    production_files = [path for path in current_files if path.relative_to(ROOT).as_posix().startswith(("backend/app/", "frontend/src/"))]
    try:
        require(stamp(sonar_verification["submitted_at"]).timestamp() >= max((path.stat().st_mtime for path in production_files), default=0), "Análisis Sonar anterior a cambios de producción")
    except (ValueError, KeyError, TypeError):
        errors.append("No se puede verificar la fecha del análisis Sonar")

    require(final_corpus.get("label") == "final" and final_corpus.get("markdown_file_count", 0) > 0, "Falta corpus Markdown final")
    for item in final_corpus.get("files", []):
        source = ROOT / item["source"]
        corpus_path = DOCS / "bertopic-corpus" / "final" / item["corpus_path"]
        require(source.exists() and digest(source) == item.get("source_byte_sha256"), "Corpus final no corresponde a specs actuales: " + item["source"])
        require(corpus_path.exists() and digest(corpus_path) == item.get("normalized_utf8_sha256"), "Copia Markdown final alterada: " + item["corpus_path"])
    unified = DOCS / "bertopic-corpus" / "final" / "unified.md"
    require(unified.is_file() and digest(unified) == final_corpus.get("unified_utf8_sha256"), "El corpus final unificado falta o no coincide con su hash")
    for command_name, pattern in [("backend-tests-and-coverage", r"\b\d+ passed\b"), ("frontend-tests-and-coverage", r"Tests\s+\d+ passed")]:
        row = command_by_name.get(command_name, {})
        path = evidence_path(row.get("log", ""))
        if path.is_file():
            clean = re.sub(r"\x1b\[[0-9;]*m", "", read(path))
            require(re.search(pattern, clean) is not None, "La salida no acredita pruebas aprobadas: " + command_name)
    return loaded, errors


def build_report(data: dict) -> str:
    metrics = data["metrics.json"]
    inputs = data["input-audit.json"]
    questions = data["question-audit.json"]
    environment = data["environment.json"]
    sonar = data["sonar-summary.json"]
    gate = data["sonar-exact-quality-gate.json"]["projectStatus"]
    verification = data["sonar-verification.json"]
    matrix = sorted(rows(data["acceptance-matrix.json"]), key=lambda row: row["id"])
    corrections = metrics["correction_counts"]
    lines = ["# Tetris — Etapa 2, opción A: informe verificado de Spec Kit", "", "Estado: implementación local y verificaciones finales completas para la evidencia descrita. No se hizo commit ni push. Este informe distingue la salida de la herramienta, las correcciones y la verificación independiente.", "", "Generado en UTC: " + datetime.now(timezone.utc).isoformat() + ".", "", "## Control y procedencia", "",
        f"Semilla maestra: `{inputs['seed_sha256']}`. Bloque extraído UTF-8/LF: `{inputs['seed_block_utf8_sha256']}`. La semilla común no cambió. Las incidencias de entrega iniciales y el acceso contextual posterior se conservan en `input-audit.json`; la entrada efectiva de implementación y correcciones está verificada.", "",
        f"Entorno registrado: Spec Kit {environment.get('spec_kit')}, Gemini CLI {environment.get('gemini_cli')}, Node {environment.get('node')}, npm {environment.get('npm')}, Python {str(environment.get('shared_python')).removeprefix('Python ')}, SonarQube {environment.get('sonarqube')}. Modelo solicitado: `{environment.get('requested_model')}`. Los modelos auxiliares efectivos aparecen por sesión en la tabla y las estadísticas originales.", "",
        "Las métricas de uso abarcan Gemini CLI y sus roles auxiliares. Excluyen Codex/orquestación del investigador, agentes de revisión de solo lectura, autoría de helpers, trabajo de Drive/UI y verificaciones externas; no son el costo ni los tokens totales del proyecto. Las fuentes actuales incluyen código heredado y cambios generados por Gemini. Helpers, evidencias y este informe son del investigador. La desviación manual documentada en OpenSpec permanece separada en comparaciones.", "", "## Invocaciones, tokens y correcciones", "",
        "Entrada significa prompt e incluye la caché; la caché no se suma de nuevo. Salida candidata y pensamiento se cuentan por separado. Intentos API, errores y éxitos corresponden a estadísticas completas; respuestas JSONL son otra medida y pueden omitir roles auxiliares. Los valores desconocidos se conservan.", "",
        "| Sesión | Entrada | Caché incluida | Salida candidata | Pensamiento |",
        "| --- | ---: | ---: | ---: | ---: |"]
    for row in metrics["runs"]:
        token = row["tokens"]
        lines.append("| " + " | ".join([row["label"], *[fmt(token.get(key)) for key in ("input_tokens", "cached_tokens", "output_tokens", "thought_tokens")]]) + " |")
    for note in data.get("_seed_delivery_notes", []):
        lines += ["", note]
    lines += ["", "| Sesión | Segundos | Intentos API | Errores API | Éxitos API | Respuestas JSONL |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in metrics["runs"]:
        token = row["tokens"]
        lines.append("| " + " | ".join([row["label"], fmt(row.get("duration_seconds"), 3), *[fmt(token.get(key)) for key in ("api_requests", "api_errors", "api_successful_requests", "recorded_response_count")]]) + " |")
    lines += ["", "| Sesión | Modelo auxiliar | Roles declarados | API intentos/errores/éxitos |", "| --- | --- | --- | --- |"]
    for row in metrics["runs"]:
        for name, item in row["tokens"].get("api_by_model", {}).items():
            if name != environment.get("requested_model") or any(role != "main" for role in item.get("roles", [])):
                values = "/".join(fmt(item.get(key)) for key in ("api_requests", "api_errors", "api_successful_requests"))
                lines.append(f"| {row['label']} | {name} | {cell(item.get('roles', []))} | {values} |")
    token = metrics["observed_tokens"]
    api = metrics["known_api_totals"]
    lines += ["", f"Acumulado observado: {fmt(metrics['invocation_attempts'])} intentos de invocación; {fmt(metrics['model_invocations'])} con modelo acreditado. Duración conocida {fmt(metrics['known_duration_seconds'], 3)} s; sesiones con duración desconocida: {cell(metrics['runs_with_unknown_duration'])}. Entrada {fmt(token['input_tokens'])}, caché incluida {fmt(token['cached_tokens'])}, candidata {fmt(token['output_tokens'])}, pensamiento {fmt(token['thought_tokens'])}. API conocida {fmt(api['api_requests'])}/{fmt(api['api_errors'])}/{fmt(api['api_successful_requests'])}; respuestas JSONL {fmt(metrics['recorded_response_count'])}. La duración excluye trabajo externo y no imputa sesiones interrumpidas.", "",
        f"Intentos externos de corrección después de implementar: {fmt(corrections['postimplementation_external_correction_prompts_started'])} iniciados y {fmt(corrections['postimplementation_external_correction_prompts_closed'])} cerrados; {fmt(corrections.get('postimplementation_external_correction_prompts_exit_zero'))} con exit 0 y {fmt(corrections.get('postimplementation_external_correction_prompts_failed_or_interrupted'))} fallidos/interrumpidos. Representan {fmt(corrections.get('distinct_qa_intents_started'))} intenciones QA distintas; un reintento puede compartir intención. Cerrar una invocación no acredita una corrección completada, y exit 0 no sustituye la aceptación independiente. Los reintentos del lanzador y la aclaración previa son categorías distintas; las acciones/rescaneos internos no son prompts externos nuevos.", "",
        "| Categoría registrada | Intentos cerrados | Prompts con modelo observado | Etiquetas |", "| --- | ---: | ---: | --- |"]
    for name, item in corrections["by_category"].items():
        lines.append(f"| {cell(name)} | {item['closed_attempts']} | {item['model_observed_closed_prompts']} | {cell(item['labels'])} |")
    lines += ["", "| Intención QA | Intentos | Exit 0 | Fallidos/interrumpidos |", "| --- | --- | --- | --- |"]
    for name, item in corrections.get("qa_intents", {}).items():
        lines.append(f"| {name} | {cell(item['attempt_labels'])} | {cell(item['closed_exit_zero_labels'])} | {cell(item['closed_failed_or_interrupted_labels'])} |")
    if metrics.get("observed_terminal_api_failures"):
        failure_labels = "; ".join(f"{item['label']}: {item['kind']}" for item in metrics["observed_terminal_api_failures"])
        lines += ["", f"Fallos terminales observados: {failure_labels}. Se conservan como incidencias de infraestructura, no como correcciones completadas. El total API sigue desconocido donde faltan estadísticas completas; no se suma un fallo terminal aislado como si fuese el agregado de errores de la sesión."]
    for row in metrics["runs"]:
        resumed = row["tokens"].get("resumed_scope_verification")
        if resumed:
            comparison_note = "Se contrastaron los contadores CLI con los tokens y las respuestas JSONL únicas dentro del intervalo." if resumed.get("token_comparisons") else "No hubo contadores CLI completos para contrastar; se conservan solo tokens/respuestas JSONL del intervalo y los agregados API son desconocidos."
            model_note = resumed.get("model_attribution", "Los roles auxiliares conservan el alcance declarado por el CLI cuando existe esa evidencia.")
            lines += ["", f"Auditoría de reanudación {row['label']} (reintento de {resumed.get('retry_of')}): {resumed.get('status')}. {comparison_note} El historial anterior no se sumó de nuevo. {model_note}"]
    lines += ["", f"Preguntas bloqueantes observadas: {fmt(questions['closed_runs_observed_blocking_question_count'])}. El resultado procede de revisar texto emitido, no del modo headless. Se mantienen los límites de las sesiones interrumpidas y la separación de aclaraciones originadas por el investigador (`question-audit.json`).", "", "## Tamaño, densidad y cambios de artefactos", "", "Se cuentan líneas físicas y caracteres Unicode tras quitar BOM y normalizar a LF. Densidad = líneas/archivo. Fuente incluye pruebas y configuración textual; Sonar analiza producción con un alcance diferente. Los deltas netos de caracteres reflejan tamaño de estado, no volumen acumulado de edición.", "", "| Alcance | Archivos | Líneas | Caracteres | Líneas/archivo |", "| --- | ---: | ---: | ---: | ---: |"]
    for label, key in [("Código Etapa 1", "source_baseline"), ("Código final Etapa 2", "source_current"), ("Specs Etapa 1", "spec_stage1"), ("Specs nativas Etapa 2", "spec_stage2")]:
        item = metrics[key]
        lines.append(f"| {label} | {fmt(item['files'])} | {fmt(item['lines'])} | {fmt(item['characters'])} | {fmt(item['lines_per_file'], 2)} |")
    lines += ["", "| Comparación | Archivos cambiados | Líneas añadidas/eliminadas | Líneas netas | Caracteres netos |", "| --- | ---: | --- | ---: | ---: |"]
    deltas = [("Código vs Etapa 1", metrics["source_change"]), ("Specs Etapa 2 vs carpeta vacía", metrics["spec_stage2_change_from_empty"]), ("Specs heredadas copiadas", metrics["spec_stage1_copy_change"])]
    qa = metrics.get("qa_change_from_generation08", {})
    deltas += [("Código QA vs generación 08", qa.get("source", {})), ("Specs QA vs generación 08", qa.get("spec_stage2", {}))]
    for label, item in deltas:
        lines.append(f"| {label} | {fmt(item.get('changed_file_count'))} | {fmt(item.get('added_lines'))}/{fmt(item.get('removed_lines'))} | {fmt(item.get('net_lines'))} | {fmt(item.get('net_characters'))} |")
    lines += ["", "La generación 08 congelada conserva el autoinforme inicial y su Sonar ERROR (57,1 % global; 44,9 % nuevo); sus declaraciones de LCOV y 96 % frontend no sustituyen los resultados independientes. Las correcciones posteriores y sus verificaciones se presentan con su propio estado. Las fuentes/especificaciones originales de Etapa 1 y su copia nativa se preservan.", "", "## Ejecución independiente y calidad", "", "Una llamada exitosa al wrapper no acredita una prueba aprobada: los resultados siguientes se apoyan en salidas originales y exit code 0, posteriores a los cambios finales.", "", "| Comprobación | Comando registrado | Salida original |", "| --- | --- | --- |"]
    for row in rows(data["verification-commands.json"]):
        command = str(row.get("executable", "")) + " " + " ".join(row.get("arguments", []))
        lines.append(f"| {cell(row.get('name'))} | {cell(command)} | {cell(row.get('log'))}; exit {row.get('exit_code')} |")
    backend_log = read(evidence_path(next(row["log"] for row in rows(data["verification-commands.json"]) if row["name"] == "backend-tests-and-coverage")))
    frontend_log = read(evidence_path(next(row["log"] for row in rows(data["verification-commands.json"]) if row["name"] == "frontend-tests-and-coverage")))
    frontend_log = re.sub(r"\x1b\[[0-9;]*m", "", frontend_log)
    backend_pass = re.search(r"(\d+) passed", backend_log)
    frontend_pass = re.search(r"Tests\s+(\d+) passed", frontend_log)
    backend_cov = re.search(r"(?m)^TOTAL\s+\d+\s+\d+\s+([\d.]+)%", backend_log)
    frontend_cov = {name: re.search(name + r"\s*:\s*([\d.]+)%", frontend_log) for name in ("Statements", "Branches", "Functions", "Lines")}
    lines += ["", f"Backend: {backend_pass.group(1) if backend_pass else 'ver salida original'} pruebas aprobadas; cobertura de sentencias {backend_cov.group(1) + '%' if backend_cov else 'ver XML/salida original'}. Frontend: {frontend_pass.group(1) if frontend_pass else 'ver salida original'} pruebas aprobadas. Cobertura frontend: " + "; ".join(name + " " + (match.group(1) + "%" if match else "ver salida original") for name, match in frontend_cov.items()) + ". npm audit reporta cero vulnerabilidades.", "",
        f"SonarQube: gate **{gate['status']}**, análisis `{verification['analysis_id']}`, tarea `{verification['ce_task_id']}` con SUCCESS. Se verifican la última tarea, el gate exacto, los hashes actuales XML/LCOV y las condiciones sin cambios: nueva cobertura ≥80 %, duplicación nueva ≤3 % y cero observaciones nuevas.", "", "| Medida Sonar de producción | Línea base | Primer escaneo Etapa 2 | Final |", "| --- | ---: | ---: | ---: |"]
    baseline_sonar = data["sonar-baseline/sonar-summary.json"]
    initial_sonar = data["sonar-initial/sonar-summary.json"]
    lines.append(f"| Quality gate | {cell(baseline_sonar.get('gate'))} | {cell(initial_sonar.get('gate'))} | {cell(sonar.get('gate'))} |")
    for label, key in [("Cobertura global (%)", "coverage"), ("Bugs", "bugs"), ("Vulnerabilidades", "vulnerabilities"), ("Hotspots", "security_hotspots"), ("Code smells", "code_smells"), ("Duplicación (%)", "duplicated_lines_density"), ("Complejidad", "complexity"), ("Complejidad cognitiva", "cognitive_complexity"), ("ncloc", "ncloc"), ("Deuda técnica (min)", "sqale_index"), ("Rating mantenibilidad", "sqale_rating"), ("Rating fiabilidad", "reliability_rating"), ("Rating seguridad", "security_rating")]:
        lines.append(f"| {label} | {cell(baseline_sonar.get(key))} | {cell(initial_sonar.get(key))} | {cell(sonar.get(key))} |")
    new_cov = next((item.get("actualValue") for item in gate.get("conditions", []) if item.get("metricKey") == "new_coverage"), None)
    lines += ["", f"Cobertura nueva final: {cell(new_cov)} %. El OK de línea base carecía de un período nuevo comparable y no se interpreta como aceptación final. Los ratings nativos de Sonar se muestran en su escala numérica (1 equivale a A). La cobertura global no equivale a la cobertura aislada backend/frontend. Sonar no mide escalabilidad; no se calcula una puntuación de escalabilidad ni se infiere rendimiento sin una carga ejecutada.", "", "## Aceptación: veinte escenarios y mecanismos", "", "El checker común devuelve siete registros aprobados que cubren ocho IDs distintos; el control suplementario S2-16 añade nueve comprobaciones HTTP sin añadir IDs al catálogo. La siguiente matriz registra evidencia de API, dominio, pruebas de interfaz y navegador por separado. Los fixtures de tres/cuatro filas son dominio aislado; no se presentan como partidas alcanzables ni como pruebas manuales de UI. No se calcula una tasa de gameplay a partir de estos mecanismos combinados.", "", "| ID | Estado | Mecanismo | Evidencia |", "| --- | --- | --- | --- |"]
    for row in matrix:
        lines.append(f"| {row['id']} | {cell(row['status'])} | {cell(row['mechanism'])} | {cell(evidence_items(row['evidence']))} |")
    lines += ["", "## Capturas y evidencia reproducible", ""]
    for capture in data["browser-evidence.json"]["captures"]:
        lines.append(f"- {capture['caption']} — `{capture['path']}`; procedencia `{capture['kind']}`. Fuentes originales: {cell(evidence_items(capture.get('raw_sources')))}.")
    if not any(capture.get("kind") == "actual_sonar" for capture in data["browser-evidence.json"]["captures"]):
        lines += ["", "No se obtuvo una captura autenticada de la interfaz web de SonarQube: la pantalla solicita iniciar sesión. La evidencia de métricas procede de la API local autenticada y sus registros conservados; los paneles derivados se identifican como tales y no se presentan como consola/interfaz Sonar original."]
    lines += ["", "Los paneles derivados, cuando existen, son visualizaciones de registros y no capturas de la interfaz original de Sonar/CLI. Las observaciones de navegador, hashes del backend/checker y origen del servidor están en `browser-evidence.json` y `acceptance-provenance.json`.", "", "## Corpus y límites del estudio", "", "El corpus final incluye sólo Markdown nativo de la feature, tanto por archivo como unificado, con manifiesto y hashes en `bertopic-corpus/final/`. Excluye JSON/OpenAPI, documentación del investigador, transcritos, templates y código de aplicación. No se ha ajustado un modelo BERTopic ni se atribuyen temas, embeddings o puntajes a esta preparación.", "", "No se estima tiempo humano, costo global, escalabilidad ni actividad oculta. Los transcritos interrumpidos, el uso auxiliar y las diferencias de conservación entre herramientas permanecen documentados. Una afirmación futura sobre otro código requiere repetir las comprobaciones que cambien de alcance.", "", "## Fuentes locales", ""]
    for name in sorted(name for name in data if not name.startswith('_')):
        lines.append("- `" + name + "`")
    lines += ["- `RESEARCH_LOG.md`, `MEASUREMENT_COMPLETENESS.md`, `qa09-final-review.md` y snapshots de generación/corrección.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate evidence and print blockers without writing a final report")
    args = parser.parse_args()
    data, errors = collect_evidence()
    if errors:
        print(json.dumps({"status": "blocked", "final_report_written": False, "errors": errors}, indent=2, ensure_ascii=True))
        return 2
    if args.check:
        print(json.dumps({"status": "ready", "final_report_written": False}, ensure_ascii=False))
        return 0
    report = build_report(data)
    (DOCS / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "written", "path": str(DOCS / "FINAL_REPORT.md"), "sha256": digest(DOCS / "FINAL_REPORT.md")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
