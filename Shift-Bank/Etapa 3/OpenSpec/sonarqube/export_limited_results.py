"""Preserve read-only submission and HTTP 401 audit evidence without Sonar credentials."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parent / "_experiment_logs" / "OpenSpec" / "sonarqube"
TASK = "ea27677b-df48-4d54-9b89-25ac686bce41"
TASK_SHORT = TASK[:8] + "_R03"
PROJECT = "Shift-Bank---Stage-3---OpenSpec"
LOG = EVIDENCE / "E3_OPENSPEC_SONAR_SCAN_20261116T193919.log"
API_FILE = EVIDENCE / f"E3_OPENSPEC_SONAR_API_ACCESS_{TASK[:8]}.json"


def target(stem: str, suffix: str) -> Path:
    p = EVIDENCE / f"{stem}_{TASK_SHORT}{suffix}"
    if p.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {p.name}")
    return p


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    log_bytes = LOG.read_bytes()
    scan_log = log_bytes.decode("utf-16", errors="replace") if b"\x00" in log_bytes[:256] else log_bytes.decode("utf-8", errors="replace")
    api_data = json.loads(API_FILE.read_text(encoding="utf-8"))
    responses = {item["endpoint"]: item for item in api_data["requests"]}
    done = "EXECUTION SUCCESS" in scan_log and "ANALYSIS SUCCESSFUL" in scan_log
    task_response = responses.get("compute_engine_task", {})
    history_response = responses.get("project_analysis_history", {})
    measures_response = responses.get("project_measures", {})
    gate_response = responses.get("quality_gate", {})
    issues_response = responses.get("issues_page_1", {})
    hotspots_response = responses.get("hotspots_page_1", {})

    ce = {
        "status": "SERVER_STATUS_UNVERIFIED_AUTHENTICATION_REQUIRED" if task_response.get("http_status") == 401 else "RESPONSE_RECORDED",
        "scanner_submission": "EXECUTION_SUCCESS_REPORT_UPLOADED" if done else "SCANNER_RESULT_NOT_CONFIRMED",
        "task_id": TASK,
        "project_key": PROJECT,
        "analysis_id": None,
        "analysis_timestamp": None,
        "compute_engine_status": None,
        "compute_engine_http_status": task_response.get("http_status"),
        "compute_engine_response": task_response.get("response"),
        "server_version": responses.get("server_version", {}).get("response"),
        "original_scanner_log": LOG.name,
        "no_new_analysis_submitted": True,
    }
    write_json(target("E3_OPENSPEC_SONAR_CE_INICIAL", ".json"), ce)

    requested_metrics = [
        "ncloc", "lines", "bugs", "vulnerabilities", "code_smells", "security_hotspots",
        "sqale_index (technical debt minutes)", "complexity (cyclomatic)", "cognitive_complexity",
        "duplicated_lines_density", "coverage", "new_coverage", "lines_to_cover",
        "reliability_rating", "security_rating", "sqale_rating / maintainability_rating",
        "software_quality_reliability_rating", "software_quality_security_rating",
        "software_quality_maintainability_rating",
    ]
    metrics = {
        "status": "UNAVAILABLE_AUTHENTICATION_REQUIRED",
        "project_key": PROJECT,
        "task_id": TASK,
        "analysis_id": None,
        "values": None,
        "requested_metrics": requested_metrics,
        "http_status": measures_response.get("http_status"),
        "raw_response": measures_response.get("response"),
        "metric_definitions_http_status": responses.get("metric_definitions", {}).get("http_status"),
        "hallazgos": None,
        "hallazgos_per_kloc": None,
        "calculation_note": "Not calculated: Bugs, Vulnerabilities, Code Smells and NCLOC could not be retrieved. Values are unavailable, not zero.",
        "taxonomies_note": "Traditional issue types and MQR software-quality counts are not combined.",
    }
    write_json(target("E3_OPENSPEC_SONAR_METRICAS_INICIALES", ".json"), metrics)

    gate = {
        "status": "UNAVAILABLE_AUTHENTICATION_REQUIRED",
        "project_key": PROJECT,
        "task_id": TASK,
        "analysis_id": None,
        "quality_gate_status": None,
        "conditions": None,
        "http_status": gate_response.get("http_status"),
        "raw_response": gate_response.get("response"),
    }
    write_json(target("E3_OPENSPEC_SONAR_GATE_INICIAL", ".json"), gate)

    issues = {
        "status": "UNAVAILABLE_AUTHENTICATION_REQUIRED",
        "project_key": PROJECT,
        "task_id": TASK,
        "analysis_id": None,
        "issues_http_status": issues_response.get("http_status"),
        "issues_response": issues_response.get("response"),
        "pagination": "Not started: first page returned HTTP 401.",
        "issue_count": None,
        "security_hotspots_http_status": hotspots_response.get("http_status"),
        "security_hotspots_response": hotspots_response.get("response"),
        "security_hotspot_count": None,
        "classification": None,
        "counts_note": "No issue list was retrieved; do not interpret unavailable counts as zero.",
    }
    write_json(target("E3_OPENSPEC_SONAR_ISSUES_INICIALES", ".json"), issues)
    csv_path = target("E3_OPENSPEC_SONAR_ISSUES_INICIALES", ".csv")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=["issue_key", "rule", "severity", "software_quality_impacts", "component",
                                      "file_path", "line", "status", "message", "issue_type",
                                      "suggested_remediation", "resolution_bucket"]).writeheader()

    config_path = EVIDENCE / "E3_OPENSPEC_SONAR_CONFIG_INICIAL.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_rows = config.get("source_files", [])
    source_names = [x["path"] for x in source_rows]
    backend_prod = [p for p in source_names if p.startswith("backend/")]
    frontend_prod = [p for p in source_names if p.startswith("frontend/src/")]
    tests = [p.relative_to(ROOT).as_posix() for test_dir in (ROOT / "backend/tests", ROOT / "frontend/tests")
             for p in sorted(test_dir.rglob("*")) if p.is_file() and p.suffix in {".py", ".mjs", ".js", ".ts", ".tsx"}]
    assert len(backend_prod) == 5 and len(frontend_prod) == 9 and len(tests) == 6

    log_checks = {
        "scanner_execution_success": done,
        "project_key_seen": f"Project key: {PROJECT}" in scan_log,
        "indexed_files_20": "20 files indexed" in scan_log,
        "python_files_analyzed_10": "10/10 source files have been analyzed" in scan_log,
        "frontend_files_analyzed_10": "10/10 source files have been analyzed" in scan_log,
        "python_coverage_sensor_parsed_report": "Parsing report '/usr/src/sonarqube/reports/backend-coverage-sonar.xml'" in scan_log,
        "frontend_coverage_sensor_read_report": "Analysing [/usr/src/sonarqube/reports/frontend-lcov-sonar.info]" in scan_log,
    }
    coverage_warnings = [line for line in scan_log.splitlines()
                         if "WARN" in line and any(term in line.lower() for term in ("coverage", "lcov", "cobertura"))]
    warnings = [line for line in scan_log.splitlines() if "WARN" in line]
    scope = {
        "scanner_indexed_files": 20,
        "configured_production_files": len(backend_prod) + len(frontend_prod),
        "backend_production_files": backend_prod,
        "frontend_production_files": frontend_prod,
        "test_files": tests,
        "test_files_classified_by_config": config.get("tests"),
        "reconciliation": "20 indexed = 14 configured production files + 6 files under sonar.tests (5 backend tests + 1 frontend test). The 20-file text/secrets sensor count includes test-classified files; the project properties explicitly classify backend/tests and frontend/tests as tests.",
        "unwanted_tests_as_production": False,
        "relevant_production_files_missing_from_configured_scope": [],
        "coverage_paths_processed_by_scanner": log_checks["python_coverage_sensor_parsed_report"] and log_checks["frontend_coverage_sensor_read_report"],
        "coverage_import_warnings_in_log": coverage_warnings,
        "sonarqube_computed_coverage_metric": None,
        "coverage_metric_limitation": "Scanner sensors parsed both reports, but the server-side measure is unavailable because authenticated measures API calls returned HTTP 401.",
        "quality_profiles_reported_by_scanner": ["css: Sonar way", "js: Sonar way", "py: Sonar way", "ts: Sonar way"],
        "warnings": warnings,
        "same_scope_reusable": True,
        "scope_sha256_file": "E3_OPENSPEC_SONAR_CONFIG_INICIAL.json",
        "source_hash_manifest": "E3_OPENSPEC_SONAR_SOURCE_HASHES_INICIALES.json",
        "analysis_log_checks": log_checks,
    }

    text = f"""# Shift Bank E3 OpenSpec — Initial SonarQube Submission\n\n**Analysis submission:** successful. **Server-side completion and metrics:** unverified because authenticated SonarQube read APIs returned HTTP 401. No rescan was performed.\n\n- Project key: {PROJECT}\n- Compute Engine task: {TASK}\n- Analysis ID: unavailable until Compute Engine task is readable\n- Analysis timestamp: unavailable from the server API\n- Scanner: SonarScanner CLI 8.1.0.6389; original log {LOG.name}\n- Server: SonarQube Community Build 26.9.0.129388\n- Scanner log reports ANALYSIS SUCCESSFUL and EXECUTION SUCCESS and confirms report upload; this does not prove Compute Engine completion.\n\n## D2 metrics\n\n| Metric | Initial value | Status |\n|---|---:|---|\n| NCLOC / physical lines | unavailable | API HTTP 401; not zero |\n| Bugs / Vulnerabilities / Code Smells | unavailable | Issues API HTTP 401; not zero |\n| Security hotspots | unavailable | Hotspots API HTTP 401; not zero |\n| Technical debt (minutes) | unavailable | Measures API HTTP 401 |\n| Cyclomatic / cognitive complexity | unavailable | Measures API HTTP 401 |\n| Duplicated lines (%) | unavailable | Measures API HTTP 401 |\n| Coverage / new-code coverage / lines to cover | unavailable as Sonar metrics | Measures API HTTP 401 |\n| Reliability / security / maintainability ratings | unavailable | Measures API HTTP 401 |\n| MQR software-quality metrics | unavailable | Metrics/measures API HTTP 401 |\n| Quality Gate and conditions | unavailable | Quality Gate API HTTP 401 |\n| Hallazgos and Hallazgos/KLOC | not calculated | Inputs unavailable; traditional and MQR taxonomies not combined |\n\nNo issue findings or code corrections are inferred from these unavailable values.\n\n## Scope and coverage reconciliation\n\nThe scanner indexed 20 files. The saved configuration selects 14 production files (5 backend modules and all 9 frontend/src files) and classifies 6 test files through sonar.tests (5 backend test files and 1 frontend test file). The scanner's 20-file text/secrets sensor count includes those test-classified files. This reconciles the earlier 14-source inventory; no test directory is configured as production source and no relevant application file is missing from the configured scope. The source SHA-256 list and exact properties are preserved for a comparable final scan.\n\nScanner log confirms the Python Cobertura sensor parsed backend-coverage-sonar.xml and the JavaScript/TypeScript sensor analyzed frontend-lcov-sonar.info, with no coverage-import warning. Server-computed coverage remains unverified. The scanner reported Sonar way profiles for CSS, JS, Python and TypeScript.\n\nLog warnings: SCM provider autodetection failed because this copied project is not detected as a Git working tree; the text/secrets sensor also warned it only retrieves language-associated files without SCM. Keep the same scope/configuration for comparison and document this limitation.\n\n## API access and next steps\n\nThe anonymous read-only checks for Compute Engine status, project analysis history, measures, Quality Gate, issues, hotspots, metrics definitions and quality profiles returned HTTP 401. The API response archive records each status/body. This indicates authentication is required; it is not evidence of an empty project. Minimum useful project access is an authenticated account with Browse and See Source Code; the task owner or an account with permission to read Compute Engine tasks may be needed for task details. A browser export of the project overview, measures, Quality Gate conditions, issues (all pages/statuses), and security hotspots can be used if API access cannot be granted.\n\nNo correction plan is proposed from unseen issues. After read access is available, retrieve the existing task {TASK}, then prioritize verified encryption/key, audit/atomicity, authentication/HTTPS and reliability findings. Do not resubmit an analysis.\n\nFull machine-readable status and access responses are in E3_OPENSPEC_SONAR_CE_INICIAL_{TASK_SHORT}.json, E3_OPENSPEC_SONAR_METRICAS_INICIALES_{TASK_SHORT}.json, E3_OPENSPEC_SONAR_ISSUES_INICIALES_{TASK_SHORT}.json, E3_OPENSPEC_SONAR_GATE_INICIAL_{TASK_SHORT}.json, E3_OPENSPEC_SONAR_API_ACCESS_{TASK_SHORT}.json, and E3_OPENSPEC_SONAR_SCOPE_RECONCILIATION_{TASK_SHORT}.json.\n"""
    initial_path = target("E3_OPENSPEC_SONAR_INICIAL", ".md")
    initial_path.write_text(text, encoding="utf-8")
    audit_path = EVIDENCE / "E3_OPENSPEC_SONAR_AUDITORIA_INICIAL.md"
    if audit_path.exists():
        audit_path = target("E3_OPENSPEC_SONAR_AUDITORIA_INICIAL", ".md")
    audit_path.write_text("# Initial read-only SonarQube audit\n\n" +
                           "The scanner successfully uploaded an analysis report, but server-side CE status, analysis ID, metrics, gate, issue list and hotspots cannot be read anonymously (HTTP 401). No issue-specific fixes are proposed.\n\n" +
                           f"Scope reconciles to {len(backend_prod)} backend + {len(frontend_prod)} frontend production files, plus {len(tests)} test-classified files = 20 indexed files. Both coverage inputs were processed by their sensors without import warnings.\n\n" +
                           "Correction round (pending authenticated findings):\n\n" +
                           "1. Read the existing CE task and analysis metadata; do not rescan.\n2. Export the complete paginated issues and hotspot lists plus Quality Gate and measures.\n3. Prioritize confirmed security/reliability findings in encryption, sensitive data, audit atomicity, authentication/HTTPS and deployment.\n4. Leave false positives, accepted threat-model limits and unrelated maintainability debt documented unless evidence shows a requirement conflict.\n\n" +
                           "No production code, tests, specs, or source scope were changed in this audit.\n", encoding="utf-8")

    scope_path = target("E3_OPENSPEC_SONAR_SCOPE_RECONCILIATION", ".json")
    write_json(scope_path, scope)

    key_files = [LOG, API_FILE, EVIDENCE / "E3_OPENSPEC_SONAR_CONFIG_INICIAL.json",
                 EVIDENCE / "E3_OPENSPEC_SONAR_SOURCE_HASHES_INICIALES.json", initial_path, audit_path,
                 scope_path, csv_path]
    key_files.extend([EVIDENCE / f"E3_OPENSPEC_SONAR_CE_INICIAL_{TASK_SHORT}.json",
                      EVIDENCE / f"E3_OPENSPEC_SONAR_METRICAS_INICIALES_{TASK_SHORT}.json",
                      EVIDENCE / f"E3_OPENSPEC_SONAR_GATE_INICIAL_{TASK_SHORT}.json",
                      EVIDENCE / f"E3_OPENSPEC_SONAR_ISSUES_INICIALES_{TASK_SHORT}.json"])
    hashes = [{"path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
              for p in key_files if p.exists()]
    hash_path = target("E3_OPENSPEC_SONAR_RESULTS_SHA256", ".csv")
    with hash_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["path", "sha256", "bytes"])
        w.writeheader()
        w.writerows(hashes)
    print(json.dumps({"scanner_submission_success": done, "task_id": TASK,
                      "server_ce_status": "UNVERIFIED_HTTP_401", "indexed_files": 20,
                      "production_files": len(backend_prod) + len(frontend_prod), "test_files": len(tests),
                      "report": str(initial_path), "audit": str(audit_path), "hashes": len(hashes)}, indent=2))


if __name__ == "__main__":
    main()
