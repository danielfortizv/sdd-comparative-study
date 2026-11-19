"""Reproducible isolated Locust run for Stage 3 OpenSpec."""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
import os
import platform
import secrets
import shutil
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import fastapi
import gevent
import locust
import uvicorn
from locust.env import Environment
from locust.event import Events
from locust.runners import STATE_RUNNING

from loadtest.metrics import ensure_isolated_database, is_steady_sample, observed_distribution, percentile, strict_below
from loadtest import locustfile


REPO = BACKEND.parent
EVIDENCE_DEFAULT = REPO.parent / "_experiment_logs" / "OpenSpec" / "locust"
SECONDS_STEADY = 60.0
USER_COUNT = 30
SPAWN_RATE = 5


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as target:
        target.write(content)


def make_certificate(temp_root: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([
            x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")), x509.DNSName("localhost")
        ]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = temp_root / "run-cert.pem", temp_root / "run-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return cert_path, key_path


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request_json(url: str, context: ssl.SSLContext, token: str | None = None, timeout: float = 1.0):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, context=context, timeout=timeout) as response:
        return response.status, json.loads(response.read() or b"null")


def readiness(base_url: str, context: ssl.SSLContext, admin_token: str) -> dict:
    deadline = time.monotonic() + 30
    last_error = "not yet ready"
    while time.monotonic() < deadline:
        try:
            status, accounts = request_json(f"{base_url}/api/accounts", context)
            audit_status, audit_result = request_json(f"{base_url}/api/admin/audit/verify", context, admin_token)
            if status == 200 and len(accounts) == 2 and audit_status == 200 and audit_result.get("valid"):
                return {"ready_at_utc": utc_now(), "accounts_http_status": status, "audit_http_status": audit_status}
            last_error = "readiness returned an unexpected application response"
        except Exception as exc:
            last_error = type(exc).__name__
        time.sleep(0.1)
    raise RuntimeError(f"Isolated HTTPS app did not become ready: {last_error}")


def rank_summary(samples: list[dict]) -> dict:
    by_name: dict[str, list[float]] = defaultdict(list)
    for sample in samples:
        by_name[sample["name"]].append(sample["response_time_ms"])
    return {
        name: {
            "request_count": len(values),
            "p50_ms": percentile(values, 0.50),
            "p95_ms": percentile(values, 0.95),
            "p99_ms": percentile(values, 0.99),
            "min_ms": min(values),
            "max_ms": max(values),
        }
        for name, values in sorted(by_name.items())
    }


def metrics_for(samples: list[dict], duration_s: float) -> dict:
    distribution = observed_distribution(samples)
    latencies = [sample["response_time_ms"] for sample in samples]
    errors = [sample for sample in samples if sample["unexpected_error"]]
    rejections = [sample for sample in samples if sample["expected_business_rejection"]]
    return {
        "request_count": len(samples),
        "requests_per_second": len(samples) / duration_s if duration_s > 0 else 0.0,
        "p50_ms": percentile(latencies, 0.50), "p95_ms": percentile(latencies, 0.95), "p99_ms": percentile(latencies, 0.99),
        "observed_request_distribution": distribution,
        "by_endpoint": rank_summary(samples),
        "expected_business_rejections": len(rejections),
        "unexpected_errors": len(errors),
        "unexpected_error_rate_percent": (100.0 * len(errors) / len(samples) if samples else None),
    }


def locust_stats(environment: Environment) -> dict:
    return {
        "requests": environment.stats.serialize_stats(),
        "failures": environment.stats.serialize_errors(),
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("x", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def check_expected_rejection_threshold_equality() -> None:
    # Executed as a guard to ensure the report implementation preserves strict SLO semantics.
    if strict_below(200.0, 200.0) or strict_below(500.0, 500.0) or strict_below(1.0, 1.0):
        raise AssertionError("Strict acceptance thresholds must reject equality")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE_DEFAULT)
    parser.add_argument("--run-id", default="RUN_01")
    parser.add_argument("--steady-seconds", type=float, default=SECONDS_STEADY)
    args = parser.parse_args()
    if args.steady_seconds != SECONDS_STEADY:
        parser.error("Approved benchmark requires exactly 60 steady seconds")
    if args.run_id != "RUN_01":
        parser.error("This approved first-run entrypoint only accepts RUN_01; create a separately reviewed entrypoint for later runs")
    check_expected_rejection_threshold_equality()
    evidence_dir = args.evidence_dir.resolve(strict=False)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    report_path = evidence_dir / "E3_OPENSPEC_LOCUST_RUN_01.json"
    if report_path.exists():
        raise FileExistsError(f"Preserving existing first-run report; refusing overwrite: {report_path}")
    started_utc = utc_now()
    run_id = f"RUN_01_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_root = Path(tempfile.mkdtemp(prefix="shift-bank-locust-"))
    db_path = run_root / "synthetic-banking.sqlite3"
    operational_path = BACKEND / "bank.db"
    ensure_isolated_database(db_path, run_root, operational_path)

    # IMPORTANT: configure actual SQLite path before importing database/application modules.
    os.environ["SHIFT_BANK_DB"] = str(db_path)
    encryption_key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    audit_key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    admin_token = secrets.token_urlsafe(32)
    os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = json.dumps({"locust-run-v1": encryption_key})
    os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "locust-run-v1"
    os.environ["SHIFT_BANK_AUDIT_KEY"] = audit_key
    os.environ["SHIFT_BANK_AUDIT_ADMIN_TOKEN"] = admin_token
    os.environ.pop("SHIFT_BANK_ENCRYPTION_KEYS_FILE", None)

    db_hash = None
    server = None
    server_log_path = evidence_dir / f"{run_id}_server.log"
    stdout_path = evidence_dir / f"{run_id}_runner.txt"
    request_samples: list[dict] = []
    user_samples: list[dict] = []
    result = None
    error_text = None
    server_log = server_log_path.open("x", encoding="utf-8")
    runner_log = stdout_path.open("x", encoding="utf-8")

    try:
        sys.path.insert(0, str(BACKEND))
        import database
        database.DB_PATH = db_path
        database.init_db()
        conn = database.get_db_connection()
        try:
            fixture = {
                "database_path": str(db_path),
                "database_inside_unique_temp_root": db_path.is_relative_to(run_root),
                "operational_default_path": str(operational_path),
                "database_is_not_operational_default": db_path.resolve() != operational_path.resolve(),
                "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
                "accounts": [dict(row) for row in conn.execute("SELECT id,balance FROM accounts ORDER BY id")],
                "transfer_limits": dict(conn.execute("SELECT per_transfer,daily FROM transfer_limits WHERE user_id='usr_101'").fetchone()),
                "seeded_transaction_count": conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],
                "initial_audit_entries": conn.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0],
            }
        finally:
            conn.close()
        if not fixture["database_inside_unique_temp_root"] or not fixture["database_is_not_operational_default"]:
            raise RuntimeError("Synthetic database isolation verification failed")
        if [(row["id"], row["balance"]) for row in fixture["accounts"]] != [("acc_checking", "5000000.00"), ("acc_savings", "15000000.00")]:
            raise RuntimeError("Deterministic fixture balances did not match expectations")
        if fixture["seeded_transaction_count"] != 2 or fixture["initial_audit_entries"] != 1:
            raise RuntimeError("Fresh synthetic fixture did not have the expected seeded ledger and audit genesis")

        cert_path, private_key_path = make_certificate(run_root)
        tls_context = ssl.create_default_context(cafile=str(cert_path))
        port = free_port()
        base_url = f"https://127.0.0.1:{port}"
        app_env = dict(os.environ)
        server_command = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port),
                          "--ssl-certfile", str(cert_path), "--ssl-keyfile", str(private_key_path), "--log-level", "warning"]
        server = subprocess.Popen(server_command, cwd=BACKEND, env=app_env, stdout=server_log, stderr=subprocess.STDOUT)
        readiness_result = readiness(base_url, tls_context, admin_token)
        runner_log.write(f"RUN_ID={run_id}\nHTTPS_TARGET={base_url}\nREADINESS={json.dumps(readiness_result)}\n")
        runner_log.flush()

        module_path = str(BACKEND / "loadtest")
        if module_path not in sys.path:
            sys.path.insert(0, module_path)
        events = Events()
        environment = Environment(user_classes=[locustfile.ShiftBankUser], host=base_url, events=events, stop_timeout=5)
        environment.shift_bank_ca_file = str(cert_path)

        def capture_request(**event):
            response = event.get("response")
            context = event.get("context") or {}
            error = event.get("exception")
            request_samples.append({
                "timestamp_utc": dt.datetime.fromtimestamp(event.get("start_time", time.time()), dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "start_time": float(event.get("start_time", time.time())),
                "method": event.get("request_type"), "name": event.get("name"),
                "response_time_ms": float(event.get("response_time", 0.0)),
                "response_length": int(event.get("response_length") or 0),
                "status_code": getattr(response, "status_code", None),
                "expected_business_rejection": bool(context.get("expected_business_rejection")),
                "unexpected_error": error is not None,
                "error_type": type(error).__name__ if error is not None else None,
            })

        events.request.add_listener(capture_request)
        runner = environment.create_local_runner()
        locustfile.workload_counts.clear()
        locustfile.expected_rejections.clear()
        locustfile.successful_transfer_ids.clear()
        ramp_started_epoch = time.time()
        ramp_started_monotonic = time.monotonic()
        runner.start(user_count=USER_COUNT, spawn_rate=SPAWN_RATE)
        spawn_deadline = time.monotonic() + 30
        while time.monotonic() < spawn_deadline:
            active = runner.user_count
            user_samples.append({"timestamp_utc": utc_now(), "elapsed_since_ramp_s": time.monotonic() - ramp_started_monotonic,
                                 "active_users": active, "runner_state": runner.state})
            if active == USER_COUNT and runner.state == STATE_RUNNING:
                break
            gevent.sleep(0.05)
        if runner.user_count != USER_COUNT or runner.state != STATE_RUNNING:
            runner.quit()
            raise RuntimeError("Locust did not verify 30 active users after ramp-up")
        steady_start_epoch = time.time()
        steady_start_monotonic = time.monotonic()
        steady_start_utc = utc_now()
        active_user_min = USER_COUNT
        active_user_max = USER_COUNT
        while time.monotonic() - steady_start_monotonic < SECONDS_STEADY:
            active = runner.user_count
            active_user_min = min(active_user_min, active)
            active_user_max = max(active_user_max, active)
            user_samples.append({"timestamp_utc": utc_now(), "elapsed_since_ramp_s": time.monotonic() - ramp_started_monotonic,
                                 "active_users": active, "runner_state": runner.state})
            if active != USER_COUNT or runner.state != STATE_RUNNING:
                raise RuntimeError("Active Locust users changed during verified steady state")
            gevent.sleep(min(0.25, SECONDS_STEADY - (time.monotonic() - steady_start_monotonic)))
        steady_end_monotonic = time.monotonic()
        steady_end_epoch = time.time()
        steady_end_utc = utc_now()
        runner.quit()
        gevent.sleep(0.2)
        if active_user_min != USER_COUNT or active_user_max != USER_COUNT:
            raise RuntimeError("Steady-state concurrency did not remain at 30 users")

        ramp_duration = steady_start_monotonic - ramp_started_monotonic
        steady_duration = steady_end_monotonic - steady_start_monotonic
        ramp_samples = [item for item in request_samples if item["start_time"] < steady_start_epoch]
        steady_samples = [item for item in request_samples if is_steady_sample(item, steady_start_epoch, steady_end_epoch)]
        end_to_end_duration = steady_end_monotonic - ramp_started_monotonic

        conn = database.get_db_connection()
        try:
            final_accounts = {row["id"]: row["balance"] for row in conn.execute("SELECT id,balance FROM accounts")}
            transaction_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            completed_test_transfers = conn.execute("SELECT COUNT(*) FROM transactions WHERE timestamp>=? AND source_account_id='acc_checking' AND destination_account_id='acc_savings' AND amount='1.00' AND status='COMPLETED'", (dt.datetime.fromtimestamp(ramp_started_epoch, dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),)).fetchone()[0]
            verification = __import__("audit").verify_connection(conn)
            audit_entries = conn.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0]
            audit_successes = conn.execute("SELECT COUNT(*) FROM audit_entries WHERE event_type='internal_transfer_completed' AND outcome='completed'").fetchone()[0]
            audit_rejections = conn.execute("SELECT COUNT(*) FROM audit_entries WHERE event_type='internal_transfer_rejected' AND outcome='rejected'").fetchone()[0]
        finally:
            conn.close()
        expected_transfer_count = len(locustfile.successful_transfer_ids)
        start_checking = 5_000_000_00
        start_savings = 15_000_000_00
        amount_cents = 100
        financial_integrity = {
            "successful_locust_transfer_responses": expected_transfer_count,
            "distinct_successful_transfer_ids": len(set(locustfile.successful_transfer_ids)),
            "database_matching_completed_transfer_count": completed_test_transfers,
            "database_transaction_count_including_two_seed_rows": transaction_count,
            "initial_total_cents": start_checking + start_savings,
            "final_total_cents": int(round(float(final_accounts["acc_checking"]) * 100)) + int(round(float(final_accounts["acc_savings"]) * 100)),
            "expected_checking_balance": f"{(start_checking - expected_transfer_count * amount_cents) / 100:.2f}",
            "actual_checking_balance": final_accounts["acc_checking"],
            "expected_savings_balance": f"{(start_savings + expected_transfer_count * amount_cents) / 100:.2f}",
            "actual_savings_balance": final_accounts["acc_savings"],
            "total_balance_preserved": int(round(float(final_accounts["acc_checking"]) * 100)) + int(round(float(final_accounts["acc_savings"]) * 100)) == start_checking + start_savings,
            "all_locust_transfers_match_db": completed_test_transfers == expected_transfer_count and transaction_count == 2 + expected_transfer_count,
            "audit_chain": verification,
            "audit_entries": audit_entries,
            "expected_audit_entries": 1 + expected_transfer_count + locustfile.expected_rejections["internal_transfer"],
        }
        financial_integrity["audit_success_events_for_transfers"] = audit_successes
        financial_integrity["audit_rejection_events_for_expected_rejections"] = audit_rejections
        financial_integrity["transfer_outcomes_have_audit_events"] = (audit_successes == expected_transfer_count
                                                                       and audit_rejections == locustfile.expected_rejections["internal_transfer"])
        financial_integrity["balances_match_transfer_count"] = (financial_integrity["actual_checking_balance"] == financial_integrity["expected_checking_balance"]
                                                                  and financial_integrity["actual_savings_balance"] == financial_integrity["expected_savings_balance"])
        financial_integrity["audit_count_matches_transfers"] = audit_entries == (1 + expected_transfer_count + locustfile.expected_rejections["internal_transfer"])
        financial_integrity["passed"] = (financial_integrity["total_balance_preserved"] and financial_integrity["all_locust_transfers_match_db"]
                                          and financial_integrity["balances_match_transfer_count"] and verification.get("valid")
                                          and financial_integrity["transfer_outcomes_have_audit_events"]
                                          and financial_integrity["audit_count_matches_transfers"])

        all_metrics = metrics_for(request_samples, end_to_end_duration)
        ramp_metrics = metrics_for(ramp_samples, max(ramp_duration, 1e-9))
        steady_metrics = metrics_for(steady_samples, steady_duration)
        endpoint = steady_metrics["by_endpoint"]
        balance_p95 = endpoint.get("balance_read", {}).get("p95_ms")
        history_p95 = endpoint.get("history_read", {}).get("p95_ms")
        transfer_p95 = endpoint.get("internal_transfer", {}).get("p95_ms")
        error_rate = steady_metrics["unexpected_error_rate_percent"]
        acceptance = {
            "balance_read_p95_below_200ms": strict_below(balance_p95, 200.0),
            "history_read_p95_below_200ms": strict_below(history_p95, 200.0),
            "combined_read_p95_below_200ms": strict_below(percentile([s["response_time_ms"] for s in steady_samples if s["name"] in ("balance_read", "history_read")], 0.95), 200.0),
            "transfer_p95_below_500ms": strict_below(transfer_p95, 500.0),
            "unexpected_error_rate_below_1_percent": strict_below(error_rate, 1.0),
        }
        acceptance["overall_performance_pass"] = all(acceptance.values())
        if not financial_integrity["passed"]:
            acceptance["financial_integrity_pass"] = False
        else:
            acceptance["financial_integrity_pass"] = True

        stats = locust_stats(environment)
        environment_info = {
            "os": platform.platform(), "python": platform.python_version(), "locust": locust.__version__,
            "fastapi": fastapi.__version__, "uvicorn": uvicorn.__version__, "cryptography": __import__("cryptography").__version__,
            "sqlite": sqlite3.sqlite_version, "openssl": ssl.OPENSSL_VERSION,
            "logical_cpu_count": os.cpu_count(), "cpu_and_memory_usage": "not measured; no process sampling tool configured",
            "target": "loopback-only isolated HTTPS FastAPI (one backend process)", "database_setting": "SHIFT_BANK_DB",
            "database_path_was_set_before_import": True, "tls_verification": "enabled; run-local self-signed certificate trusted explicitly by Locust and readiness client",
        }
        result = {
            "run_id": run_id, "status": "complete",
            "started_at_utc": started_utc, "ramp_started_at_utc": dt.datetime.fromtimestamp(ramp_started_epoch, dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "all_users_spawned_at_utc": steady_start_utc, "steady_state_ended_at_utc": steady_end_utc, "finished_at_utc": utc_now(),
            "parameters": {"users": USER_COUNT, "spawn_rate_users_per_second": SPAWN_RATE, "configured_task_weights": {"balance_read": 6, "history_read": 3, "internal_transfer": 1},
                           "steady_state_seconds_required": SECONDS_STEADY, "transfer_amount_cop": "1.00", "wait_time_seconds": {"minimum": 0.1, "maximum": 0.3}},
            "timing": {"ramp_up_seconds_to_verified_30_users": ramp_duration, "steady_state_seconds_observed": steady_duration,
                       "steady_state_active_users_min": active_user_min, "steady_state_active_users_max": active_user_max,
                       "steady_state_sample_boundary": "request start_time in [all_users_spawned_at, steady_state_ended_at)", "end_to_end_seconds": end_to_end_duration},
            "environment": environment_info, "fixture": fixture, "metrics": {"all_phases": all_metrics, "ramp_up_only": ramp_metrics, "steady_state_only": steady_metrics},
            "locust_task_selection_counts": dict(locustfile.workload_counts), "expected_business_rejections_by_endpoint": dict(locustfile.expected_rejections),
            "financial_integrity": financial_integrity, "acceptance": acceptance,
            "artifacts": {}, "locust_raw_stats": stats,
        }
        db_hash = None
    except Exception as exc:
        error_text = f"{type(exc).__name__}: {exc}"
        traceback.print_exc(file=runner_log)
        runner_log.flush()
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        server_log.close()
        runner_log.flush()
        runner_log.close()
        if db_path.exists():
            import hashlib
            digest = hashlib.sha256()
            with db_path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            db_hash = digest.hexdigest()
        # The run-only secrets, certificate/private key, and SQLite files are disposable.
        shutil.rmtree(run_root, ignore_errors=True)

    if result is None:
        result = {"run_id": run_id, "status": "failed", "started_at_utc": started_utc, "error": error_text,
                  "environment": {"python": platform.python_version(), "locust": locust.__version__},
                  "artifacts": {"execution_output": str(stdout_path), "server_log": str(server_log_path)}}
    result.setdefault("artifacts", {})
    result["artifacts"].update({
        "machine_readable_report": str(report_path), "request_samples_csv": str(evidence_dir / f"{run_id}_requests.csv"),
        "locust_stats_csv": str(evidence_dir / f"{run_id}_stats.csv"), "locust_failures_csv": str(evidence_dir / f"{run_id}_failures.csv"),
        "users_timeline_csv": str(evidence_dir / f"{run_id}_users.csv"), "runner_output": str(stdout_path),
        "backend_server_output": str(server_log_path), "database_sha256_before_disposal": db_hash,
    })
    final_report_path = report_path if result.get("status") == "complete" else evidence_dir / f"{run_id}_INCOMPLETE.json"
    write_exclusive(final_report_path, json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_csv(evidence_dir / f"{run_id}_requests.csv", request_samples,
              ["timestamp_utc", "start_time", "method", "name", "response_time_ms", "response_length", "status_code", "expected_business_rejection", "unexpected_error", "error_type"])
    if result.get("locust_raw_stats"):
        stats_rows = result["locust_raw_stats"]["requests"]
        failures = result["locust_raw_stats"]["failures"]
        stat_fields = sorted({key for row in stats_rows for key in row}) or ["name", "method", "num_requests", "num_failures"]
        failure_fields = sorted({key for row in failures for key in row}) or ["name", "error", "occurrences"]
        write_csv(evidence_dir / f"{run_id}_stats.csv", stats_rows, stat_fields)
        write_csv(evidence_dir / f"{run_id}_failures.csv", failures, failure_fields)
    else:
        write_csv(evidence_dir / f"{run_id}_stats.csv", [], ["name", "method", "num_requests", "num_failures"])
        write_csv(evidence_dir / f"{run_id}_failures.csv", [], ["name", "error", "occurrences"])
    write_csv(evidence_dir / f"{run_id}_users.csv", user_samples,
              ["timestamp_utc", "elapsed_since_ramp_s", "active_users", "runner_state"])
    print(json.dumps({"run_id": run_id, "status": result["status"], "report": str(final_report_path),
                      "steady_state_seconds": result.get("timing", {}).get("steady_state_seconds_observed"),
                      "acceptance": result.get("acceptance", {}), "error": result.get("error")}, indent=2))
    return 0 if (result.get("status") == "complete" and result.get("acceptance", {}).get("overall_performance_pass")
                 and result.get("financial_integrity", {}).get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
