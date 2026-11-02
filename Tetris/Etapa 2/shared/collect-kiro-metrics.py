"""Measure Kiro Stage 2 using its own baseline and real ACP/native records."""
import argparse
from collections import Counter

from kiro_research import BASE, DOCS, ROOT, changes, configurations, counts, digest, load, manifests, run_measurement, runs, seed_info, source_category, source_paths, spec_paths, stamp, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="metrics.json", help="Research JSON filename inside Kiro/docs")
    args = parser.parse_args()
    if "/" in args.output or "\\" in args.output or not args.output.endswith(".json"):
        raise ValueError("Output must be one JSON filename in Kiro/docs")
    if not (DOCS / "baseline-copy-manifest.json").exists():
        raise RuntimeError("Kiro own baseline manifest is required")
    before, current = source_paths(BASE), source_paths(ROOT)
    original_specs, current_specs = spec_paths(BASE), spec_paths(ROOT)
    inherited = {n: p for n, p in current_specs.items() if n in original_specs}
    new = {n: p for n, p in current_specs.items() if n not in original_specs}
    classifications = load(DOCS / "run-classifications.json", {})
    rows = []
    for run in runs():
        category = classifications.get(run["label"], {})
        rows.append({**run, "classification": category.get("category", "unclassified"), "classification_reason": category.get("reason"), "qa_intent_id": category.get("qa_intent_id"), "retry_of": category.get("retry_of"), "process_exit_success": run.get("exit_code") == 0 if run.get("exit_code") is not None else None, "work_completion_status": category.get("work_completion_status", "not independently adjudicated"), **run_measurement(run)})
    all_runs = runs(include_pending=True)
    duration = [r.get("duration_seconds") for r in rows]
    known_duration = [v for v in duration if isinstance(v, (float, int))]
    def known_total(name):
        return sum(r[name] for r in rows if isinstance(r.get(name), (int, float)))
    _, seed = seed_info()
    categories = Counter(r["classification"] for r in rows)
    external = [r for r in rows if r["classification"] == "postimplementation_external_correction"]
    result = {"researcher_created": True, "measured_at_utc": stamp(), "tool": "Kiro", "schema": "kiro-acp-native-v1", "status": "current measurement snapshot; not final acceptance", **seed,
        "text_count_definition": "UTF-8 BOM removed; universal newlines normalize CRLF to LF; characters are decoded Unicode code points, lines use splitlines including blanks; density is total lines/files. SHA256 covers raw file bytes.",
        "source_scope": "Kiro own backend/frontend source extensions including tests/configuration; dependencies/builds/caches/docs/Git excluded; production-only Sonar metrics have a separate denominator",
        "source_baseline": counts(before), "source_current": counts(current), "source_changes_from_own_stage1": changes(before, current),
        "source_categories": {name: counts({n: p for n, p in current.items() if source_category(n) == name}) for name in ("production", "tests", "configuration_and_support")},
        "configuration_baseline": counts(configurations(BASE)), "configuration_current": counts(configurations(ROOT)), "configuration_changes": changes(configurations(BASE), configurations(ROOT)), "configuration_scope": "explicit pytest/coverage/TypeScript/Vite/Vitest/Sonar configuration files; .ts configuration overlaps source_current and is not added to its total",
        "spec_stage1_baseline": counts(original_specs), "spec_stage1_copy": counts(inherited), "spec_stage1_changes": changes(original_specs, inherited), "spec_stage2": counts(new), "spec_stage2_changes_from_zero": changes({}, new),
        "spec_scope": "all .md/.json under own .kiro/specs; inherited paths recognized from own Stage1 names, new paths counted separately. Native requirements/design/tasks are the Kiro artifacts; no other tool's specifications are generation inputs.",
        "dependency_manifests_baseline": counts(manifests(BASE)), "dependency_manifests_current": counts(manifests(ROOT)), "dependency_manifest_changes": changes(manifests(BASE), manifests(ROOT)),
        "baseline_manifest_sha256": digest((DOCS / "baseline-copy-manifest.json").read_bytes()),
        "invocation_attempts": len(rows), "prompt_count": len(rows), "prompt_count_definition": "closed launcher invocations, including failed startup; actual native user messages and observed model startups recorded separately",
        "model_invocations_observed": sum(r["model_invocation_observed"] for r in rows), "known_launcher_duration_seconds": round(sum(known_duration), 3), "total_duration_seconds": round(sum(known_duration), 3), "duration_coverage": "sum of known closed invocation wall durations only; not whole project elapsed time or paused/resumed session lifetime", "unknown_duration_labels": [r["label"] for r in rows if not isinstance(r.get("duration_seconds"), (int, float))],
        "known_credits": known_total("credits"), "unknown_credit_labels": [r["label"] for r in rows if r.get("credits") is None], "credits_coverage": "known invocation-interval native usage summaries; ACP fallback only when no native summary; credits are Kiro-native units, never converted into inferred tokens/money",
        "known_agent_elapsed_seconds": known_total("agent_elapsed_seconds"), "unknown_agent_elapsed_labels": [r["label"] for r in rows if r.get("agent_elapsed_seconds") is None],
        "input_tokens": None, "cached_tokens": None, "output_tokens": None, "thought_tokens": None, "token_coverage": "not exposed in the observed Kiro billing schema; no zero assumption and no conversion from credits/context composition",
        "api_requests": None, "api_errors": None, "api_successful_requests": None, "api_coverage": "not exposed; recorded request IDs are a different observable with unspecified attempt/error semantics",
        "recorded_request_id_count_known_sum": known_total("recorded_request_id_count"), "recorded_request_id_sum_scope": "sum of known per-invocation distinct request identifiers; not an API attempt total; cross-run repeated IDs require investigation before any unique-session claim",
        "corrections": {"classification_counts": dict(categories), "external_postimplementation_prompt_attempts_closed": len(external), "external_postimplementation_distinct_qa_intents": len({r["qa_intent_id"] for r in external if r.get("qa_intent_id")}), "external_postimplementation_labels": [r["label"] for r in external], "automated_within_invocation_remediation_count": None, "note": "explicit researcher classification only; tool calls/scans or process exit0 do not prove a completed external correction; internal automated remediation is separate and requires source evidence"},
        "runtime_versions_by_closed_invocation": [{"label": r["label"], "runtime": r.get("runtime"), "requested_model": r.get("requested_model"), "observed_mode_selection_values": r["observed_mode_selection_values"], "observed_model_selection_values": r["observed_model_selection_values"], "native_assistant_agent_modes": r["native_assistant_agent_modes"]} for r in rows],
        "runtime_scope": "Version/hash belong to the individual launcher record; updates, login/auth/usage probes and researcher setup are excluded from model invocation totals. Runtime changes remain a comparison limitation.",
        "unclosed_invocation_labels": [r["label"] for r in all_runs if not r["run_closed"]], "pending_invocation_records": [{"label": r["label"], "started": r.get("started"), "runtime": r.get("runtime"), "requested_model": r.get("requested_model")} for r in all_runs if not r["run_closed"]], "runs": rows,
        "provenance_limitations": ["Usage covers Kiro experiment only; researcher/Codex orchestration, helper authoring and review are excluded", "Kiro requested/selected model configuration does not establish resolved backend model or auxiliary model billing", "Tool success flags and runFinished success do not prove raw command exits or acceptance; independent logs/checks are required", "Missing native/ACP data remain unknown; a prelaunch failure is not silently treated as a successful model invocation", "Line/character deltas compare retained states and do not reconstruct cumulative edits"]}
    write(DOCS / args.output, result)
    print({"metrics": str(DOCS / args.output), "closed_invocations": len(rows), "pending": result["unclosed_invocation_labels"], "known_credits": result["known_credits"], "source": {k:v for k,v in result["source_current"].items() if k != "per_file"}, "new_specs": {k:v for k,v in result["spec_stage2"].items() if k != "per_file"}})


if __name__ == "__main__":
    main()
