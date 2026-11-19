"""Run one authenticated, immutable initial SonarQube analysis and export its API evidence."""
from __future__ import annotations

import base64
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parent / "_experiment_logs" / "OpenSpec" / "sonarqube"
PROJECT = "Shift-Bank---Stage-3---OpenSpec"
SERVER = "http://localhost:9000"
SCANNER_IMAGE = "sdd-sonar-scanner:frozen"
SOURCE_FILES = [
    ROOT / "backend" / name for name in ("main.py", "banking.py", "database.py", "encryption.py", "audit.py")
] + sorted(p for p in (ROOT / "frontend" / "src").rglob("*") if p.is_file())


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_manifest() -> list[dict]:
    return [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
             "bytes": p.stat().st_size} for p in SOURCE_FILES]


def api(path: str, token: str, params: dict | None = None, method: str = "Bearer"):
    query = urllib.parse.urlencode(params or {}, doseq=True)
    url = SERVER + path + ("?" + query if query else "")
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    if method == "Bearer":
        request.add_header("Authorization", "Bearer " + token)
    else:
        request.add_header("Authorization", "Basic " + base64.b64encode((token + ":").encode()).decode())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8").strip()
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            details = json.loads(body)
        except json.JSONDecodeError:
            details = {"message": body[:1000]}
        return exc.code, details


def authenticated_api(path: str, token: str, params: dict | None = None):
    code, result = api(path, token, params, "Bearer")
    if code in {401, 403}:
        code, result = api(path, token, params, "Basic")
        return code, result, "Basic" if code < 400 else f"Bearer_then_Basic_{code}"
    return code, result, "Bearer"


def paginate(path: str, token: str, params: dict, method: str = "Bearer") -> tuple[list[dict], list[dict], int | None, str | None]:
    rows, pages, total = [], [], None
    page = 1
    while True:
        code, response = api(path, token, {**params, "p": page, "ps": 500}, method)
        if code >= 400:
            return rows, pages, total, f"HTTP {code}: {json.dumps(response, ensure_ascii=False)[:1200]}"
        pages.append(response)
        if "issues" in response:
            chunk = response["issues"]
            paging = response.get("paging", {})
            total = paging.get("total", len(chunk))
            rows.extend(chunk)
            if len(rows) >= total or not chunk:
                break
        elif "hotspots" in response:
            chunk = response["hotspots"]
            paging = response.get("paging", {})
            total = paging.get("total", len(chunk))
            rows.extend(chunk)
            if len(rows) >= total or not chunk:
                break
        elif "components" in response:
            chunk = response["components"]
            paging = response.get("paging", {})
            total = paging.get("total", len(chunk))
            rows.extend(chunk)
            if len(rows) >= total or not chunk:
                break
        elif "metrics" in response:
            chunk = response["metrics"]
            paging = response.get("paging", {})
            total = paging.get("total", len(chunk))
            rows.extend(chunk)
            if len(rows) >= total or not chunk:
                break
        else:
            return rows, pages, total, "Unexpected pagination response shape"
        page += 1
    return rows, pages, total, None


def paginate_authenticated(path: str, token: str, params: dict):
    rows, pages, total, error = paginate(path, token, params, "Bearer")
    auth_mode = "Bearer"
    if error and re.search(r"HTTP (401|403)", error):
        rows, pages, total, basic_error = paginate(path, token, params, "Basic")
        auth_mode = "Basic" if not basic_error else "Bearer_then_Basic_failed"
        error = basic_error
    return rows, pages, total, error, auth_mode


def save_unique(name: str, stamp: str) -> Path:
    path = EVIDENCE / name
    if path.exists():
        path = EVIDENCE / f"{Path(name).stem}_{stamp}{Path(name).suffix}"
    return path


def write_unavailable_analysis_artifacts(stamp: str, reason: str) -> dict[str, Path]:
    files = {
        "quality_gate": save_unique("E3_OPENSPEC_SONAR_GATE_INICIAL.json", stamp),
        "metrics": save_unique("E3_OPENSPEC_SONAR_METRICAS_INICIALES.json", stamp),
        "issues": save_unique("E3_OPENSPEC_SONAR_ISSUES_INICIALES.json", stamp),
        "issues_csv": save_unique("E3_OPENSPEC_SONAR_ISSUES_INICIALES.csv", stamp),
    }
    for kind in ("quality_gate", "metrics", "issues"):
        write_json(files[kind], {"status": "NOT_EXECUTED", "analysis_id": None, "reason": reason})
    with files["issues_csv"].open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["issue_key", "rule", "severity", "software_quality_impacts", "component",
                                               "file_path", "line", "status", "message", "issue_type",
                                               "suggested_remediation", "resolution_bucket"])
        writer.writeheader()
    return files


def main() -> int:
    token = os.environ.get("SONAR_TOKEN_OPENSPEC3", "")
    if not token:
        print("SONAR_TOKEN_OPENSPEC3 is unavailable; token value is never requested from standard chat input.")
        return 2
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()
    before_hashes = source_manifest()
    config_props = ROOT / "sonarqube" / "sonar-project.properties"
    properties = config_props.read_text(encoding="utf-8")
    config = json.loads((ROOT / "sonarqube" / "config-initial.json").read_text(encoding="utf-8"))
    config.update({"properties": properties, "properties_sha256": hashlib.sha256(config_props.read_bytes()).hexdigest(),
                   "coverage_tools": {"coverage_py": "7.17.3", "frontend_reporter": "c8 12.0.0",
                                      "node_native_coverage": "Node 24.19.0 built-in test coverage"},
                   "source_files": before_hashes, "source_file_count": len(before_hashes),
                   "frontend_coverage_scope": ["frontend/src/api.mjs", "frontend/src/refreshPolling.mjs", "frontend/src/validation.mjs"],
                   "scanner_execution": {"image": SCANNER_IMAGE,
                                         "image_id": "sha256:a3f4215076706c95a17a68c19322ee916e40a3acd081a8c1a1e839e0194afa57",
                                         "host_mapping": "host.docker.internal:host-gateway",
                                         "credential_transport": "inherited environment variable SONAR_TOKEN; never a command-line value",
                                         "command_arguments": ["-Dproject.settings=/usr/src/sonarqube/sonar-project.properties", "-Dsonar.verbose=true"]},
                   "scan_started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    config_path = save_unique("E3_OPENSPEC_SONAR_CONFIG_INICIAL.json", stamp)
    write_json(config_path, config)
    manifest_path = save_unique("E3_OPENSPEC_SONAR_SOURCES_INICIALES.json", stamp)
    write_json(manifest_path, {"files": before_hashes, "sha256_algorithm": "SHA-256", "captured_before_scan": True})

    version_status, server_version = api("/api/server/version", token)
    server_version = server_version if version_status == 200 else {"http_status": version_status, "response": server_version}
    history_status, history, auth_mode = authenticated_api("/api/project_analyses/search", token,
                                                               {"project": PROJECT, "ps": 100})
    history_path = save_unique("E3_OPENSPEC_SONAR_PREEXISTING_ANALYSES.json", stamp)
    write_json(history_path, {"http_status": history_status, "auth_mode": auth_mode,
                              "analyses": history if history_status == 200 else None,
                              "response": history if history_status != 200 else None,
                              "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    if history_status not in {200, 404}:
        print(f"Cannot establish pre-scan history state (HTTP {history_status}); stopping before scan to preserve historical analyses.")
        write_unavailable_analysis_artifacts(stamp, f"Pre-scan history could not be authenticated (HTTP {history_status}); no analysis was started.")
        return 3

    log_path = save_unique(f"E3_OPENSPEC_SONAR_SCANNER_{stamp}.log", stamp)
    command = ["docker", "run", "--rm", "--add-host=host.docker.internal:host-gateway",
               "--env", "SONAR_TOKEN", "--env", "SONAR_HOST_URL=http://host.docker.internal:9000",
               "--volume", f"{ROOT}:/usr/src", "--workdir", "/usr/src", SCANNER_IMAGE,
               "-Dproject.settings=/usr/src/sonarqube/sonar-project.properties", "-Dsonar.verbose=true"]
    env = os.environ.copy()
    env["SONAR_TOKEN"] = token
    start = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    task_id = None
    exit_code = 127
    try:
        with log_path.open("w", encoding="utf-8", newline="\n") as log:
            log.write("Command: docker run --rm --add-host=host.docker.internal:host-gateway --env SONAR_TOKEN "
                      "--env SONAR_HOST_URL=http://host.docker.internal:9000 --volume <project-root>:/usr/src "
                      "--workdir /usr/src sdd-sonar-scanner:frozen "
                      "-Dproject.settings=/usr/src/sonarqube/sonar-project.properties -Dsonar.verbose=true\n")
            log.flush()
            proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            assert proc.stdout is not None
            for line in proc.stdout:
                if token in line:
                    line = line.replace(token, "<redacted>")
                print(line, end="")
                log.write(line)
                log.flush()
            exit_code = proc.wait()
    except Exception as exc:
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"Safe runner error: {type(exc).__name__}: {str(exc).replace(token, '<redacted>')}\n")

    task_file = ROOT / ".scannerwork" / "report-task.txt"
    task_info = {}
    if task_file.exists():
        for line in task_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                task_info[k.strip()] = v.strip()
        task_id = task_info.get("ceTaskId")

    ce_responses = []
    ce_final = None
    if task_id:
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            code, ce_final, auth_mode = authenticated_api("/api/ce/task", token, {"id": task_id})
            ce_responses.append({"http_status": code, "response": ce_final, "auth_mode": auth_mode,
                                 "observed_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            if code >= 400 or ce_final.get("task", {}).get("status") in {"SUCCESS", "FAILED", "CANCELED"}:
                break
            time.sleep(3)
    ce_path = save_unique("E3_OPENSPEC_SONAR_CE_INICIAL.json", stamp)
    write_json(ce_path, {"scanner_exit_code": exit_code, "task_id": task_id, "task_info": task_info,
                         "polls": ce_responses, "final": ce_final, "scanner_log": log_path.name})

    analysis_id = (ce_final or {}).get("task", {}).get("analysisId")
    outputs: dict[str, Path] = {"config": config_path, "source_manifest": manifest_path, "preexisting_analyses": history_path,
                                "scanner_log": log_path, "compute_engine": ce_path}
    if analysis_id:
        code, analyses, method = authenticated_api("/api/project_analyses/search", token, {"project": PROJECT, "ps": 100})
        all_analyses = analyses.get("analyses", []) if code == 200 else []
        analysis = next((item for item in all_analyses if item.get("key") == analysis_id), None)
        code_gate, gate, gate_auth = authenticated_api("/api/qualitygates/project_status", token, {"analysisId": analysis_id})
        gate_path = save_unique("E3_OPENSPEC_SONAR_GATE_INICIAL.json", stamp)
        write_json(gate_path, {"analysis_id": analysis_id, "http_status": code_gate, "auth_mode": gate_auth,
                               "response": gate, "conditions": gate.get("projectStatus", {}).get("conditions", []) if code_gate == 200 else []})
        outputs["quality_gate"] = gate_path

        metric_defs, metric_pages, metric_total, metric_error, metric_auth = paginate_authenticated("/api/metrics/search", token, {})
        if metric_error:
            metric_defs, metric_pages = [], []
        wanted = {"ncloc", "lines", "bugs", "vulnerabilities", "code_smells", "sqale_index", "technical_debt",
                  "cognitive_complexity", "complexity", "duplicated_lines_density", "coverage", "new_coverage",
                  "reliability_rating", "security_rating", "sqale_rating", "maintainability_rating"}
        available = [item.get("key") for item in metric_defs
                     if item.get("key") in wanted or "software_quality" in item.get("key", "")]
        measures_status, measures, measures_auth = authenticated_api("/api/measures/component", token,
                                                                       {"component": PROJECT, "metricKeys": available,
                                                                        "analysisId": analysis_id})
        if measures_status >= 400:
            measures_status, measures, measures_auth = authenticated_api("/api/measures/component", token,
                                                                           {"component": PROJECT, "metricKeys": available})
            measure_query_fallback = "analysisId parameter unsupported; query used latest analysis and cross-checked analysis history"
        else:
            measure_query_fallback = None
        metrics_path = save_unique("E3_OPENSPEC_SONAR_METRICAS_INICIALES.json", stamp)
        write_json(metrics_path, {"analysis_id": analysis_id, "analysis": analysis,
                                  "analysis_http_status": code, "analysis_auth_mode": method,
                                  "metrics_http_status": measures_status, "metrics_auth_mode": measures_auth,
                                  "metric_definitions_auth_mode": metric_auth,
                                  "metric_query_fallback": measure_query_fallback,
                                  "requested_metric_keys": available, "available_metric_definitions": metric_defs,
                                  "metric_definitions_pages": metric_pages, "metric_definitions_total": metric_total,
                                  "metric_definitions_error": metric_error, "measures_response": measures,
                                  "measures_bound_to_analysis_id": measures_status == 200 and
                                  measures.get("component", {}).get("analysis", {}).get("key") == analysis_id})
        outputs["metrics"] = metrics_path

        profile_code, profiles, profile_auth = authenticated_api("/api/qualityprofiles/search", token, {"project": PROJECT})
        raw_issue_pages, active_issues, resolved_issues, issue_errors = [], [], [], []
        issue_auth_modes = []
        for resolved, bucket in (("false", active_issues), ("true", resolved_issues)):
            rows, pages, total, error, issue_auth = paginate_authenticated("/api/issues/search", token,
                                                                            {"componentKeys": PROJECT, "resolved": resolved})
            issue_auth_modes.append(issue_auth)
            bucket.extend(rows)
            raw_issue_pages.extend([{"resolved": resolved, "page": i + 1, "response": page} for i, page in enumerate(pages)])
            if error:
                issue_errors.append({"resolved": resolved, "error": error})

        all_issues, seen = [], set()
        for issue in active_issues + resolved_issues:
            key = issue.get("key")
            if key not in seen:
                all_issues.append(issue)
                seen.add(key)
        rule_keys = sorted({item.get("rule") for item in all_issues if item.get("rule")})
        rules = {}
        rule_errors = []
        for key in rule_keys:
            rule_code, rule, rule_auth = authenticated_api("/api/rules/show", token, {"key": key})
            if rule_code == 200:
                rules[key] = rule.get("rule", rule)
            else:
                rule_errors.append({"rule": key, "http_status": rule_code, "response": rule})

        hot_rows, hot_pages, hot_total, hot_error, hot_auth = paginate_authenticated("/api/hotspots/search", token,
                                                                                       {"projectKey": PROJECT})
        summary = {"active_issue_count": len(active_issues), "resolved_issue_count": len(resolved_issues),
                   "by_type_active": {kind: sum(item.get("type") == kind for item in active_issues)
                                      for kind in ("BUG", "VULNERABILITY", "CODE_SMELL")},
                   "security_hotspots": len(hot_rows) if not hot_error else None}
        issues_path = save_unique("E3_OPENSPEC_SONAR_ISSUES_INICIALES.json", stamp)
        issue_http_status = 200
        if issue_errors:
            status_match = re.search(r"HTTP (\d+)", issue_errors[0]["error"])
            issue_http_status = int(status_match.group(1)) if status_match else None
        issue_data = {"status": "COMPLETE" if not issue_errors and not hot_error else "PARTIAL",
                      "analysis_id": analysis_id, "issues_query_http_status": issue_http_status,
                      "active_issues": active_issues, "resolved_issues": resolved_issues, "all_unique_issues": all_issues,
                      "raw_issue_pages": raw_issue_pages, "issues_errors": issue_errors,
                      "issues_auth_modes": issue_auth_modes,
                      "rules": rules, "rule_detail_errors": rule_errors,
                      "hotspot_pages": hot_pages, "security_hotspots": hot_rows,
                      "hotspot_total": hot_total, "hotspot_error": hot_error, "hotspots_auth_mode": hot_auth,
                      "classification_summary": summary, "quality_profiles_http_status": profile_code,
                      "quality_profiles_auth_mode": profile_auth, "quality_profiles": profiles,
                      "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        write_json(issues_path, issue_data)
        outputs["issues"] = issues_path
        csv_path = save_unique("E3_OPENSPEC_SONAR_ISSUES_INICIALES.csv", stamp)
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            fields = ["issue_key", "rule", "severity", "software_quality_impacts", "component", "file_path", "line",
                      "status", "message", "issue_type", "suggested_remediation", "resolution_bucket"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for issue in all_issues:
                rule = rules.get(issue.get("rule"), {})
                impacts = issue.get("impacts", [])
                writer.writerow({"issue_key": issue.get("key"), "rule": issue.get("rule"),
                                 "severity": issue.get("severity"),
                                 "software_quality_impacts": "; ".join(f"{i.get('softwareQuality')}:{i.get('severity')}" for i in impacts),
                                 "component": issue.get("component"), "file_path": issue.get("path") or issue.get("component"),
                                 "line": issue.get("line"), "status": issue.get("status"), "message": issue.get("message"),
                                 "issue_type": issue.get("type"),
                                 "suggested_remediation": rule.get("remediation", "") or rule.get("remediationFunction", ""),
                                 "resolution_bucket": "active" if issue in active_issues else "resolved"})
        outputs["issues_csv"] = csv_path

        component_rows, component_pages, component_total, component_error, component_auth = paginate_authenticated(
            "/api/components/tree", token, {"component": PROJECT, "qualifiers": "FIL"})
        outputs["components"] = save_unique("E3_OPENSPEC_SONAR_COMPONENTS_INICIALES.json", stamp)
        write_json(outputs["components"], {"analysis_id": analysis_id, "auth_mode": component_auth, "components": component_rows,
                                           "pages": component_pages, "total": component_total, "error": component_error})

        metrics_resp = measures.get("component", {}).get("measures", []) if measures_status == 200 else []
        metrics_map = {m.get("metric"): m.get("value") for m in metrics_resp}
        issue_counts = summary["by_type_active"]
        ncloc = float(metrics_map.get("ncloc") or 0)
        findings = (issue_counts["BUG"] + issue_counts["VULNERABILITY"] + issue_counts["CODE_SMELL"]
                    if not issue_errors else None)
        findings_per_kloc = findings / (ncloc / 1000) if findings is not None and ncloc else None
        metrics_path = outputs["metrics"]
        metrics_record = json.loads(metrics_path.read_text(encoding="utf-8"))
        metrics_record["normalized_metrics"] = metrics_map
        metrics_record["derived"] = {"Hallazgos": findings, "Hallazgos_per_KLOC": findings_per_kloc,
                                      "counts_taxonomy": issue_counts,
                                      "counts_complete": not issue_errors,
                                      "legacy_issue_counts_and_MQR_are_not_added_together": True,
                                      "latest_project_analysis_matches_analysis_id": bool(all_analyses and
                                          all_analyses[0].get("key") == analysis_id)}
        write_json(metrics_path, metrics_record)
    else:
        outputs.update(write_unavailable_analysis_artifacts(
            stamp, "The scan did not produce an analysis ID; metrics, gate and issues were not retrieved."))

    after_hashes = source_manifest()
    hash_stable = before_hashes == after_hashes
    write_json(save_unique("E3_OPENSPEC_SONAR_SOURCE_HASH_CHECK.json", stamp),
               {"before_scan": before_hashes, "after_scan": after_hashes, "unchanged": hash_stable})

    for local, evidence_name in ((ROOT / "sonarqube" / "reports" / "backend-coverage.xml", "E3_OPENSPEC_COVERAGE_BACKEND_RAW.xml"),
                                 (ROOT / "sonarqube" / "reports" / "backend-coverage-sonar.xml", "E3_OPENSPEC_COVERAGE_BACKEND_SONAR.xml"),
                                 (ROOT / "sonarqube" / "reports" / "backend-test-output.txt", "E3_OPENSPEC_SONAR_BACKEND_TESTS.txt"),
                                 (ROOT / "sonarqube" / "reports" / "frontend-coverage" / "lcov.info", "E3_OPENSPEC_COVERAGE_FRONTEND_C8_RAW.lcov"),
                                 (ROOT / "sonarqube" / "reports" / "frontend-lcov-sonar.info", "E3_OPENSPEC_COVERAGE_FRONTEND_SONAR.lcov"),
                                 (ROOT / "sonarqube" / "reports" / "frontend-c8-test-output.txt", "E3_OPENSPEC_SONAR_FRONTEND_TESTS_C8.txt"),
                                 (ROOT / "sonarqube" / "reports" / "frontend-node-test-coverage.txt", "E3_OPENSPEC_SONAR_FRONTEND_NODE_COVERAGE.txt")):
        if local.exists():
            dest = save_unique(evidence_name, stamp)
            shutil.copy2(local, dest)
            outputs["evidence_" + dest.stem] = dest

    summary_path = save_unique("E3_OPENSPEC_SONAR_RUN_METADATA.json", stamp)
    write_json(summary_path, {"scan_started_utc": start, "scan_finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                              "scanner_exit_code": exit_code, "scanner_log": str(log_path), "server_version": server_version,
                              "preexisting_analysis_http_status": history_status, "preexisting_analysis_file": str(history_path),
                              "compute_engine_task_id": task_id, "compute_engine_status": (ce_final or {}).get("task", {}).get("status"),
                              "analysis_id": analysis_id, "source_hashes_unchanged": hash_stable,
                              "outputs": {k: str(v) for k, v in outputs.items()}})
    hash_rows = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
                 for path in outputs.values() if path.exists()]
    hash_rows.append({"path": summary_path.name, "sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
                      "bytes": summary_path.stat().st_size})
    hashes_path = save_unique("E3_OPENSPEC_SONAR_EVIDENCE_SHA256.csv", stamp)
    with hashes_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "sha256", "bytes"])
        writer.writeheader()
        writer.writerows(hash_rows)
    print(json.dumps({"scanner_exit_code": exit_code, "compute_engine_status": (ce_final or {}).get("task", {}).get("status"),
                      "analysis_id": analysis_id, "source_hashes_unchanged": hash_stable,
                      "evidence_directory": str(EVIDENCE)}, indent=2))
    return 0 if exit_code == 0 and (ce_final or {}).get("task", {}).get("status") == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
