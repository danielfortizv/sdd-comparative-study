"""Researcher-created, sanitized static evidence views for CUA screenshots.

Reads retained Kiro evidence only. Does not run Kiro, a browser, a web server,
Sonar, Google, Git, application code or tests. Does not modify original reports
or the existing shared/render-evidence.py used by completed tool reports.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

STAGE = Path(__file__).resolve().parent.parent
DOCS = STAGE / "Kiro" / "docs"
OUT = DOCS / "evidence-view"
ORIGINAL = Path(__file__).with_name("render-evidence.py")
ORIGINAL_SHA256 = "3EE4574EE4A90F2B0E83ABBD0C58B11058E1B34D479126CA23D4F1DB71843DA0"
SOURCES: dict[str, dict] = {}
GENERATED_AT = datetime.now(timezone.utc).isoformat()


def h(value) -> str:
    return html.escape(str(value))


def source(relative: str, purpose: str) -> Path:
    path = DOCS / relative
    if not path.is_file():
        raise RuntimeError(f"Required retained evidence is missing: {relative}")
    SOURCES[relative] = {"path": "docs/" + relative, "purpose": purpose, "bytes": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper()}
    return path


def load(relative: str, purpose: str):
    return json.loads(source(relative, purpose).read_text(encoding="utf-8-sig"))


def log(relative: str, purpose: str) -> str:
    raw = source(relative, purpose).read_text(encoding="utf-8-sig", errors="replace")
    # ANSI is removed from the derived display only; raw files are never edited.
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", raw)


def display(value, suffix="") -> str:
    return "unavailable" if value is None else str(value) + suffix


def table(headers: list[str], rows: list[list]) -> str:
    return "<table><thead><tr>" + "".join("<th>"+h(x)+"</th>" for x in headers) + "</tr></thead><tbody>" + "".join("<tr>"+"".join("<td>"+h(x)+"</td>" for x in row)+"</tr>" for row in rows) + "</tbody></table>"


def cards(items: list[tuple[str, object]]) -> str:
    return '<div class="cards">' + "".join('<div class="card"><div class="value">'+h(value)+'</div><div class="label">'+h(label)+'</div></div>' for label,value in items) + '</div>'


def wrap(title: str, subtitle: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{h(title)}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#09111f;color:#e7eef9;font:19px/1.45 Segoe UI,Arial,sans-serif}}
main{{width:960px;max-width:100%;margin:0 auto;padding:30px 34px 36px}}h1{{font-size:34px;line-height:1.18;margin:12px 0;color:#79ebf4}}h2{{font-size:24px;margin:25px 0 12px;color:#c1ceff}}
.tag{{display:inline-block;border:1px solid #a68d45;background:#332b19;border-radius:5px;padding:5px 10px;color:#ffe6a3;font-size:17px;font-weight:700}}.sub{{color:#c6d2e2;margin:12px 0 18px}}.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.card{{background:#15253a;border:1px solid #34506c;border-radius:9px;padding:15px}}.value{{font-size:36px;font-weight:700;color:#9ff3cf;line-height:1.2}}.label{{margin-top:6px;font-size:18px;color:#cfdae8}}
table{{width:100%;border-collapse:collapse;font-size:18px;table-layout:fixed}}th,td{{padding:10px 12px;border:1px solid #36506a;text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{background:#1b344e;color:#a7f0fb}}td{{background:#102033}}tr:nth-child(even) td{{background:#16273c}}
.warning{{border-left:5px solid #e8b457;background:#30291d;padding:14px 16px;margin:18px 0;color:#ffedc7}}.note{{font-size:18px;color:#c6d3e3;margin-top:18px}}code{{font:17px/1.5 Consolas,monospace;overflow-wrap:anywhere;color:#b5e6fe}}
.hash{{font:17px/1.5 Consolas,monospace;overflow-wrap:anywhere}}a{{color:#96e6f2}}nav{{display:flex;gap:20px;flex-wrap:wrap;margin:20px 0;font-size:18px}}.stamp{{margin-top:25px;border-top:1px solid #34506c;padding-top:12px;font-size:16px;color:#b0bfd1}}
@media(max-width:700px){{main{{padding:20px}}.cards{{grid-template-columns:1fr 1fr}}.value{{font-size:29px}}}}
</style></head><body><main><div class="tag">RESEARCHER VIEW · DERIVED FROM RETAINED EVIDENCE</div><h1>{h(title)}</h1><p class="sub">{h(subtitle)}</p>
<nav><a href="baseline.html">Baseline results</a><a href="baseline-provenance.html">Analysis provenance</a><a href="source-hashes.html">Source hashes</a><a href="metrics.html">Current metrics snapshot</a></nav>
{body}<p class="stamp">Generated {h(GENERATED_AT)}. Static researcher display; not a native Kiro CLI, terminal, SonarQube UI or gameplay screenshot. Raw evidence is unchanged.</p></main></body></html>'''


def write(name: str, title: str, subtitle: str, body: str) -> None:
    (OUT / name).write_text(wrap(title, subtitle, body), encoding="utf-8")


def baseline_panels() -> None:
    summary = load("sonar-baseline/sonar-summary.json", "Raw local Sonar API baseline measures")
    verification = load("sonar-baseline/sonar-verification.json", "Exact submitted CE task and analysis ID")
    scan = load("sonar-baseline/scan-command.json", "Scanner exit, version, XML hash and LCOV absence")
    gate = load("sonar-baseline/quality-gate-configuration.json", "Dedicated gate configured thresholds")
    config = load("sonar-baseline/configuration-verification.json", "New-code period and unchanged built-in gate")
    load("sonar-baseline/sonar-exact-task.json", "Raw exact compute-engine status")
    load("sonar-baseline/sonar-exact-quality-gate.json", "Raw evaluated gate conditions for exact analysis")
    frontend = load("baseline-frontend-result.json", "Frontend build exit, unavailable tests/LCOV")
    audit = load("baseline-npm-audit.json", "Original-lock npm vulnerability counts")
    instrument = load("baseline-coverage-instrumentation.json", "Original 23 packages plus separately authorized coverage")
    coverage = ET.parse(source("baseline-coverage.xml", "Fresh backend coverage line counters")).getroot()
    covered, valid = int(coverage.attrib["lines-covered"]), int(coverage.attrib["lines-valid"])
    backend_percent = round(covered / valid * 100, 2) if valid else None
    backend_log = log("baseline-backend-coverage-tests.log", "Instrumented backend pytest result")
    matched = re.search(r"(\d+) passed", backend_log)
    backend_tests = int(matched.group(1)) if matched else None
    build_log = log("baseline-frontend-build.log", "Fresh TypeScript/Vite production build")
    vite = re.search(r"vite v([\d.]+)", build_log)
    vulnerabilities = audit.get("metadata", {}).get("vulnerabilities", {})
    source("baseline-coverage-commands.json", "Exact researcher instrumentation argv, times and exits")
    source("baseline-environment-commands.json", "Exact baseline environment/test/build/audit commands")
    source("baseline-copy-manifest.json", "Unchanged own Stage 1 copy hashes")
    source("sonar-baseline/baseline-closure-verification.json", "Post-scan copied/original hash checks and raw warnings")
    source("sonar-baseline/report-task.txt", "Exact baseline scanner submission")
    if summary.get("project") != "tetris-stage2-kiro" or not scan.get("baseline"):
        raise RuntimeError("Unexpected baseline Sonar project/scope")
    conditions = verification.get("gate_conditions") or []
    body = cards([("Backend tests passed", display(backend_tests)),
                  ("Backend coverage", display(backend_percent, "%")),
                  ("Sonar global coverage", display(summary.get("coverage"), "%")),
                  ("Baseline code smells", display(summary.get("code_smells"))),
                  ("Bugs / vulnerabilities / hotspots", " / ".join(display(summary.get(k)) for k in ("bugs","vulnerabilities","security_hotspots"))),
                  ("npm advisories", display(vulnerabilities.get("total")))])
    body += '<div class="warning"><strong>Baseline only — Stage 2 acceptance is not established.</strong><br>Raw gate '+h(verification.get("gate_status"))+'; evaluated new-code conditions: '+h(len(conditions))+'. The first analysis cannot demonstrate the final 80% / 3% / zero-new-issue requirements.</div>'
    body += table(["Independent baseline check", "Retained result"], [
        ["Production build", "PASS" if frontend.get("build_exit_code")==0 else display(frontend.get("build_exit_code"))],
        ["Frontend runtime", "Vite "+vite.group(1) if vite else "unavailable"],
        ["Frontend tests / LCOV", "Unavailable in inherited baseline; no framework added"],
        ["Backend denominator", f"{covered}/{valid} executable lines; coverage.py rounds to 99%"],
        ["npm audit", f"exit {frontend.get('audit_exit_code')}; {vulnerabilities.get('moderate')} moderate, {vulnerabilities.get('high')} high, {vulnerabilities.get('critical')} critical"],
        ["Coverage environment", f"{instrument.get('original_package_count')} original packages + coverage 7.16.2 researcher instrumentation"],
    ])
    body += '<p class="note">The 72.6% global Sonar denominator includes uninstrumented frontend lines. It differs from backend-only coverage. These are unchanged Stage 1 baseline measurements retained for the Stage 2 comparison.</p>'
    write("baseline.html", "Tetris · Kiro baseline", "Independent researcher checks before Stage 2 application changes; project version "+display(scan.get("project_version")), body)
    provenance = table(["Exact analysis field", "Raw retained value"], [
        ["Project key", verification.get("project_key")], ["Project version", scan.get("project_version")],
        ["Compute-engine task", verification.get("ce_task_id")], ["Compute-engine status", verification.get("ce_status")],
        ["Analysis ID", verification.get("analysis_id")], ["Submitted / executed", str(verification.get("submitted_at"))+" / "+str(verification.get("executed_at"))],
        ["Gate status / evaluated conditions", str(verification.get("gate_status"))+" / "+str(len(conditions))],
        ["New-code period", config.get("new_code_type")], ["Sonar way unchanged", config.get("built_in_gate_unchanged")],
        ["Frontend LCOV", "Unavailable"],
    ])
    provenance += '<h2>Configured gate — separate from evaluated conditions</h2>' + table(["Metric", "Fails when", "Threshold"], [[c.get("metric"),c.get("op"),c.get("error")] for c in gate.get("conditions",[])])
    provenance += '<div class="warning">This first baseline reports no evaluated conditions. It is not final Stage 2 acceptance. The final application analysis must use version 2.0 and current backend XML plus frontend LCOV.</div>'
    provenance += '<p class="note">Full raw source names and SHA-256 values are on the source-hashes page. This table was derived from local API JSON and scanner evidence; no SonarQube login or credentials were extracted.</p>'
    write("baseline-provenance.html", "Kiro · exact baseline analysis", "Reproducible task-to-analysis provenance; a derived researcher view", provenance)


def metrics_panel() -> None:
    if not (DOCS / "metrics.json").exists():
        write("metrics.html", "Kiro · current metrics", "No canonical metrics snapshot available", '<p class="warning">Metrics and usage unavailable. No zero-token or zero-credit assumption.</p>')
        return
    m = load("metrics.json", "Canonical current Kiro experiment metrics snapshot")
    runs = m.get("runs", [])
    known_credit_runs = [row for row in runs if row.get("credits") is not None]
    unknown_credit_runs = [row.get("label") for row in runs if row.get("credits") is None]
    credits = "unavailable" if not known_credit_runs else str(round(sum(row["credits"] for row in known_credit_runs), 6))+" observed"
    if known_credit_runs and unknown_credit_runs:
        credits += f"; {len(unknown_credit_runs)} unknown"
    # Discover only local durable launcher metadata. Do not inspect auth stores,
    # raw model content, or infer usage for an invocation still in progress.
    open_labels = []
    for started in sorted(DOCS.glob("*.started.json")):
        label = started.name.removesuffix(".started.json")
        if not (DOCS / (label+".run.json")).exists():
            open_labels.append(label)
    body = cards([("Closed invocations in snapshot", display(m.get("invocation_attempts"))),
                  ("Known launcher seconds", display(m.get("known_launcher_duration_seconds"))),
                  ("Kiro credits", credits)])
    body += '<div class="warning">Current snapshot, not final acceptance. Token and API counters are shown only when explicitly exposed. Context occupancy, tools, chunks and request IDs are not billed token or API-attempt totals.</div>'
    body += '<p>Canonical snapshot measured: <code>'+h(m.get("measured_at_utc"))+ '</code>.<br>Open durable launcher records at render time: <strong>'+h(", ".join(open_labels) or "none observed")+'</strong>. Open-run usage remains unavailable.</p>'
    body += table(["Invocation / outcome", "Seconds", "Credits", "Input tokens", "Output tokens"], [[
        str(row.get("label"))+" / "+str(row.get("work_completion_status", row.get("exit_code"))),
        display(row.get("duration_seconds")), display(row.get("credits")), display(row.get("input_tokens")),display(row.get("output_tokens"))] for row in runs])
    body += '<h2>Measured artifacts</h2>' + table(["Scope", "Files", "Lines", "Characters"], [[label, data.get("files"),data.get("lines"),data.get("characters")] for label,key in (("Own Stage 1 source","source_baseline"),("Current source snapshot","source_current"),("New Stage 2 native specs","spec_stage2")) for data in [m.get(key,{})]])
    body += '<p class="note">01-specify has unknown usage if its canonical credits/tokens are null; missing values are never replaced with zero. Credits retain their Kiro-native meaning and are not converted into money or inferred tokens. Researcher/Codex work is outside these Kiro usage counters.</p>'
    write("metrics.html", "Kiro · current experiment metrics", str(m.get("status", "Current measured snapshot")), body)


def main() -> None:
    if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest().upper() != ORIGINAL_SHA256:
        raise RuntimeError("Existing shared renderer hash changed; inspect prior report evidence before proceeding")
    OUT.mkdir(parents=True, exist_ok=True)
    baseline_panels()
    metrics_panel()
    rows = []
    for relative, item in sorted(SOURCES.items()):
        rows.append('<tr><td><code>'+h(item["path"])+'</code><br>'+h(item["purpose"])+'</td><td class="hash">'+h(item["sha256"])+'<br>'+h(item["bytes"])+" bytes</td></tr>")
    body = '<p>Hashes identify unchanged raw evidence under Kiro/docs. Only this sanitized static directory needs to be served for CUA screenshots; raw transcripts, credentials and authentication stores are not copied here.</p><table><thead><tr><th>Retained source / meaning</th><th>SHA-256 / size</th></tr></thead><tbody>'+"".join(rows)+'</tbody></table>'
    write("source-hashes.html", "Kiro · raw evidence provenance", "Names and byte hashes; no raw credentials, model transcripts or authentication contents", body)
    manifest = {"researcher_created":True,"generated_at_utc":GENERATED_AT,"kind":"derived_static_researcher_evidence_view","native_ui_screenshot":False,"original_renderer_path":"shared/render-evidence.py","original_renderer_sha256_unchanged":ORIGINAL_SHA256,"renderer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),"sources":list(SOURCES.values()),"panels":[{"path":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest().upper()} for p in sorted(OUT.glob("*.html"))],"privacy_scope":"No credentials/auth stores/raw model transcripts copied; source names and SHA256 metadata only","baseline_is_stage2_acceptance":False}
    (OUT / "view-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output_directory":str(OUT),"panels":[row["path"] for row in manifest["panels"]],"sources_hashed":len(SOURCES),"original_renderer_unchanged":True,"browser_or_server_started":False},indent=2))


if __name__ == "__main__":
    main()
