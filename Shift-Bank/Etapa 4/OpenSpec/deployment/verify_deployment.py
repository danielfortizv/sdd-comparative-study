"""Exercise the running local Compose stack without writing confidential payloads."""
from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = Path(__file__).resolve().parent
PROJECT = "shift-bank-e3-openspec-block4"
COMPOSE = ["docker", "compose", "--project-name", PROJECT, "--env-file", str(DEPLOY / ".env.local"), "-f", str(DEPLOY / "compose.yaml")]
BACKEND_CONTAINER = f"{PROJECT}-backend"
BASE = "https://localhost:18443"
TLS_CERT = DEPLOY / "certs" / "dev-cert.pem"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def read_env_file(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value
    return values


def docker(args: list[str], timeout: int = 30, expected: int | None = 0) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if expected is not None and result.returncode != expected:
        raise RuntimeError(f"Command failed with exit {result.returncode}: {' '.join(args[:5])}; stderr={result.stderr[-1200:]}")
    return result


def compose(args: list[str], timeout: int = 30, expected: int | None = 0) -> subprocess.CompletedProcess:
    return docker(COMPOSE + args, timeout=timeout, expected=expected)


def request(path: str, method: str = "GET", body=None, headers=None, timeout: int = 5):
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(BASE + path, data=encoded, method=method, headers=request_headers)
    context = ssl.create_default_context(cafile=str(TLS_CERT))
    try:
        with urllib.request.urlopen(req, context=context, timeout=timeout) as response:
            payload = response.read()
            parsed = json.loads(payload) if payload and response.headers.get_content_type() == "application/json" else payload.decode("utf-8", errors="replace")
            return response.status, parsed, response.headers
    except urllib.error.HTTPError as response:
        payload = response.read()
        try:
            parsed = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            parsed = {}
        return response.code, parsed, response.headers


def add_check(checks: dict, requests: list, name: str, actual, expected, method="CHECK", path="", detail=None):
    passed = actual == expected
    checks[name] = {"status": "PASS" if passed else "FAIL", "actual": actual, "expected": expected}
    requests.append({"timestamp_utc": utc_now(), "method": method, "path": path, "status": actual if isinstance(actual, int) else None,
                     "check": name, "result": checks[name]["status"], "safe_detail": detail})
    return passed


def run_container_startup_probe(name: str, environment_overrides: list[str], expected_text: str) -> dict:
    temp_db = f"/tmp/{PROJECT}-{name}.sqlite3"
    overrides = ["-e", f"SHIFT_BANK_DB={temp_db}"]
    overrides.extend([item for key in environment_overrides for item in ("-e", key)])
    code = "import asyncio,main\nasync def go():\n async with main.lifespan(main.app):\n  await asyncio.sleep(0)\nasyncio.run(go())"
    command = ["docker", "run", "--rm", "--network", "none", "--env-file", str(DEPLOY / ".env.local"),
               *overrides, "--entrypoint", "python", "shift-bank-e3-openspec-backend:local", "-c", code]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    safe_output = (result.stdout + result.stderr).replace("\r", "")
    env_values = read_env_file(DEPLOY / ".env.local")
    for key in ("SHIFT_BANK_ENCRYPTION_KEYS", "SHIFT_BANK_AUDIT_KEY", "SHIFT_BANK_AUDIT_ADMIN_TOKEN"):
        if env_values.get(key):
            safe_output = safe_output.replace(env_values[key], "<redacted>")
    safe_lines = [line.strip() for line in safe_output.splitlines() if line.strip()]
    return {"status": "PASS" if result.returncode != 0 and expected_text in safe_output else "FAIL",
            "expected_safe_failure": expected_text in safe_output, "exit_code": result.returncode,
            "safe_error_lines": safe_lines[-8:], "temporary_database_path": temp_db,
            "secret_values_recorded": False}


def backend_state() -> dict:
    code = r'''import json,sqlite3
from database import get_db_connection,DB_PATH
import audit
c=get_db_connection()
try:
 rows=c.execute("SELECT id,balance FROM accounts ORDER BY id").fetchall()
 tables={"beneficiaries":("name","bank_name","routing_number","account_number"),"ach_transfers":("recipient_name","bank_name","routing_number","account_number"),"recurring_schedules":("recipient_name","bank_name","routing_number","account_number")}
 count=0; plaintext=0
 for table,fields in tables.items():
  for row in c.execute("SELECT * FROM "+table):
   for field in fields:
    value=row[field]
    if value is not None:
     count+=1
     if not value.startswith("sbenc:v1:"): plaintext+=1
 result=audit.verify_connection(c)
 print(json.dumps({"db_path":str(DB_PATH),"balances":{r["id"]:r["balance"] for r in rows},"sensitive_fields_checked":count,"plaintext_sensitive_fields":plaintext,"audit_valid":result["valid"],"audit_entries":result["checked_entries"],"transactions":c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],"ach": [dict(r) for r in c.execute("SELECT id,status,refund_applied,occurrence_id FROM ach_transfers")],"schedules":[dict(r) for r in c.execute("SELECT id,status,next_execution_at,cadence_anchor FROM recurring_schedules")],"occurrences":c.execute("SELECT COUNT(*) FROM recurring_occurrences").fetchone()[0],"recovery_events":c.execute("SELECT COUNT(*) FROM audit_entries WHERE event_type='recurring_schedule_recovered'").fetchone()[0]}))
finally:c.close()'''
    result = compose(["exec", "-T", "backend", "python", "-c", code], timeout=20)
    return json.loads(result.stdout.strip().splitlines()[-1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--http-log", type=Path, required=True)
    args = parser.parse_args()
    env_values = read_env_file(DEPLOY / ".env.local")
    admin_token = env_values["SHIFT_BANK_AUDIT_ADMIN_TOKEN"]
    checks, requests = {}, []
    timestamps = {"verification_started_utc": utc_now()}

    try:
        # Direct HTTP test preserves the 301 response without following it.
        conn = http.client.HTTPConnection("127.0.0.1", 18080, timeout=5)
        conn.request("GET", "/api/history", headers={"Host": "localhost"})
        response = conn.getresponse()
        redirect_status, location = response.status, response.getheader("Location")
        response.read(); conn.close()
        add_check(checks, requests, "http_redirect", (redirect_status, location), (301, "https://localhost:18443/api/history"),
                  "GET", "http://localhost:18080/api/history", location)

        status, html, _ = request("/")
        add_check(checks, requests, "frontend_https", status, 200, "GET", "/")
        if isinstance(html, str):
            assets = re.findall(r"(?:src|href)=\"([^\"]+\.(?:js|css))\"", html)
            asset_statuses = [request(asset)[0] for asset in assets]
        else:
            assets, asset_statuses = [], []
        add_check(checks, requests, "production_assets", bool(assets) and all(code == 200 for code in asset_statuses), True,
                  "GET", "React production asset paths", {"asset_count": len(assets), "statuses": asset_statuses})

        for endpoint in ("/health/live", "/health/ready"):
            health_status, health_body, _ = request(endpoint)
            expected_body = {"status": "alive" if endpoint.endswith("live") else "ready"}
            add_check(checks, requests, endpoint, (health_status, health_body), (200, expected_body), "GET", endpoint)

        status, accounts, _ = request("/api/accounts")
        add_check(checks, requests, "accounts_api", status, 200, "GET", "/api/accounts")
        initial = {row["id"]: row["balance"] for row in accounts}
        expected_initial = {"acc_checking": "5000000.00", "acc_savings": "15000000.00"}
        add_check(checks, requests, "synthetic_initial_balances", initial, expected_initial, "GET", "/api/accounts")

        status, history, _ = request("/api/history")
        add_check(checks, requests, "history_api", status, 200, "GET", "/api/history", {"row_count": len(history)})
        status, body, _ = request("/api/admin/audit/verify")
        add_check(checks, requests, "audit_verification_unauthorized", status, 401, "GET", "/api/admin/audit/verify")
        status, audit_body, _ = request("/api/admin/audit/verify", headers={"Authorization": f"Bearer {admin_token}"})
        add_check(checks, requests, "audit_verification_authorized", status == 200 and audit_body.get("valid"), True,
                  "GET", "/api/admin/audit/verify", {"checked_entries": audit_body.get("checked_entries")})

        status, body, _ = request("/api/transfers", "POST", {})
        add_check(checks, requests, "invalid_request_rejected", status, 422, "POST", "/api/transfers")
        status, rejected, _ = request("/api/transfers", "POST", {"source_account_id": "acc_checking", "destination_account_id": "acc_checking", "amount": "10.00"})
        add_check(checks, requests, "self_transfer_rejected", status, 400, "POST", "/api/transfers")
        status, transfer, _ = request("/api/transfers", "POST", {"source_account_id": "acc_checking", "destination_account_id": "acc_savings", "amount": "100.00"})
        add_check(checks, requests, "valid_internal_transfer", status == 200 and transfer.get("status") == "COMPLETED", True,
                  "POST", "/api/transfers", {"transaction_id": transfer.get("id")})
        transfer_id = transfer["id"]
        status, after_transfer, _ = request("/api/accounts")
        changed = {row["id"]: row["balance"] for row in after_transfer}
        add_check(checks, requests, "internal_transfer_financial_effect", changed,
                  {"acc_checking": "4999900.00", "acc_savings": "15000100.00"}, "GET", "/api/accounts")

        synthetic_recipient = {"name": "Synthetic Container Recipient", "bank_name": "Example Simulation Bank",
                               "routing_number": "012345678", "account_number": "0000123456789"}
        status, beneficiary, _ = request("/api/beneficiaries", "POST", synthetic_recipient)
        add_check(checks, requests, "https_beneficiary_create", status, 201, "POST", "/api/beneficiaries",
                  {"beneficiary_id": beneficiary.get("id")})
        beneficiary_id = beneficiary["id"]
        status, recipients, _ = request("/api/beneficiaries")
        found = next((row for row in recipients if row.get("id") == beneficiary_id), None)
        add_check(checks, requests, "beneficiary_authorized_decryption", status == 200 and found == {"id": beneficiary_id, **synthetic_recipient}, True,
                  "GET", "/api/beneficiaries", {"record_found": found is not None, "sensitive_values_logged": False})

        status, ach, _ = request("/api/ach-transfers", "POST", {"source_account_id": "acc_checking", "amount": "1000000.00", "beneficiary_id": beneficiary_id})
        add_check(checks, requests, "ach_requires_mfa", status == 202 and ach.get("status") == "PENDING_MFA", True,
                  "POST", "/api/ach-transfers", {"transfer_id": ach.get("transfer_id")})
        ach_id = ach["transfer_id"]
        status, before_mfa, _ = request("/api/accounts")
        add_check(checks, requests, "mfa_pending_no_debit", {r["id"]: r["balance"] for r in before_mfa}, changed,
                  "GET", "/api/accounts")
        status, invalid_mfa, _ = request(f"/api/ach-transfers/{ach_id}/confirm", "POST", {"code": "000000"})
        add_check(checks, requests, "invalid_mfa_denied", status, 400, "POST", f"/api/ach-transfers/{ach_id}/confirm")
        status, after_invalid_mfa, _ = request("/api/accounts")
        add_check(checks, requests, "invalid_mfa_no_debit", {r["id"]: r["balance"] for r in after_invalid_mfa}, changed,
                  "GET", "/api/accounts")
        status, confirmation, _ = request(f"/api/ach-transfers/{ach_id}/confirm", "POST", {"code": "123456"})
        add_check(checks, requests, "valid_mfa_authorizes_ach", status == 200 and confirmation.get("status") == "pending", True,
                  "POST", f"/api/ach-transfers/{ach_id}/confirm")
        ach_deadline = time.monotonic() + 50
        ach_state = None
        while time.monotonic() < ach_deadline:
            status, ach_rows, _ = request("/api/ach-transfers")
            ach_state = next((row for row in ach_rows if row.get("id") == ach_id), None)
            if ach_state and ach_state.get("status") == "settled":
                break
            time.sleep(1)
        add_check(checks, requests, "ach_settles_once", status == 200 and ach_state is not None and ach_state.get("status") == "settled", True,
                  "GET", "/api/ach-transfers", {"transfer_id": ach_id, "settlement_observed": ach_state.get("settled_at") if ach_state else None})
        status, after_ach, _ = request("/api/accounts")
        expected_after_ach = {"acc_checking": "3999900.00", "acc_savings": "15000100.00"}
        add_check(checks, requests, "ach_debit_once", {row["id"]: row["balance"] for row in after_ach}, expected_after_ach,
                  "GET", "/api/accounts")

        tomorrow = (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)).isoformat()
        status, schedule, _ = request("/api/recurring-schedules", "POST", {"transfer_type": "internal", "source_account_id": "acc_checking",
                                                                              "destination_account_id": "acc_savings", "amount": "50.00",
                                                                              "frequency": "daily", "start_date": tomorrow})
        add_check(checks, requests, "recurring_schedule_created", status == 200 and schedule.get("status") == "active", True,
                  "POST", "/api/recurring-schedules", {"schedule_id": schedule.get("schedule_id")})
        schedule_id = schedule["schedule_id"]
        for action, expected in (("pause", "paused"), ("resume", "active")):
            status, state, _ = request(f"/api/recurring-schedules/{schedule_id}/{action}", "POST")
            add_check(checks, requests, f"recurring_{action}", status == 200 and state.get("status") == expected, True,
                      "POST", f"/api/recurring-schedules/{schedule_id}/{action}")

        before_restart = backend_state()
        history_count_before_restart = len(request("/api/history")[1])
        database_path = read_env_file(DEPLOY / ".env.local").get("SHIFT_BANK_DB", "/var/lib/shift-bank/bank.db")
        injected = compose(["exec", "-T", "backend", "python", "-c",
                            "import sqlite3; c=sqlite3.connect(" + repr(database_path) + "); r=c.execute(\"UPDATE recurring_schedules SET next_execution_at='2000-01-01T00:00:00Z' WHERE id=?\", (" + repr(schedule_id) + ",)); c.commit(); print(r.rowcount); c.close()"])
        add_check(checks, requests, "due_schedule_restart_precondition", injected.stdout.strip(), "1", "TEST", "synthetic SQLite schedule fixture")
        compose(["stop", "backend"])
        compose(["start", "backend"], timeout=30)

        ready_deadline = time.monotonic() + 60
        ready_after_restart = False
        while time.monotonic() < ready_deadline:
            try:
                ready_after_restart = request("/health/ready")[0] == 200
                if ready_after_restart:
                    break
            except Exception:
                pass
            time.sleep(1)
        add_check(checks, requests, "backend_ready_after_restart", ready_after_restart, True, "GET", "/health/ready")
        restarted_accounts = request("/api/accounts")[1]
        add_check(checks, requests, "balances_persist_after_restart", {row["id"]: row["balance"] for row in restarted_accounts},
                  expected_after_ach, "GET", "/api/accounts")
        status, restarted_history, _ = request("/api/history")
        add_check(checks, requests, "history_persists_after_restart",
                  len(restarted_history) if status == 200 else None,
                  history_count_before_restart, "GET", "/api/history", {"row_count": len(restarted_history)})
        status, restarted_ach, _ = request("/api/ach-transfers")
        persisted_ach = next((row for row in restarted_ach if row.get("id") == ach_id), None)
        add_check(checks, requests, "ach_settlement_persists_after_restart", status == 200 and persisted_ach and persisted_ach.get("status") == "settled", True,
                  "GET", "/api/ach-transfers", {"record_found": persisted_ach is not None})
        status, audit_after_restart, _ = request("/api/admin/audit/verify", headers={"Authorization": f"Bearer {admin_token}"})
        add_check(checks, requests, "audit_valid_after_restart", status == 200 and audit_after_restart.get("valid"), True,
                  "GET", "/api/admin/audit/verify", {"checked_entries": audit_after_restart.get("checked_entries")})

        state_after_restart = backend_state()
        schedule_state = next((row for row in state_after_restart["schedules"] if row["id"] == schedule_id), None)
        add_check(checks, requests, "recurring_due_recovered_without_occurrence",
                  schedule_state is not None and schedule_state["status"] == "active" and schedule_state["next_execution_at"] > utc_now()
                  and state_after_restart["occurrences"] == before_restart["occurrences"], True,
                  "CHECK", "SQLite recurring recovery", {"schedule_status": schedule_state["status"] if schedule_state else None,
                                                          "recovery_events": state_after_restart["recovery_events"]})
        add_check(checks, requests, "stored_sensitive_fields_encrypted",
                  state_after_restart["sensitive_fields_checked"] > 0 and state_after_restart["plaintext_sensitive_fields"] == 0, True,
                  "CHECK", "SQLite encrypted fields", {"fields_checked": state_after_restart["sensitive_fields_checked"], "plaintext_fields": state_after_restart["plaintext_sensitive_fields"]})

        # A second restart proves recovery did not replay the already-recovered due item.
        compose(["restart", "backend"], timeout=30)
        deadline = time.monotonic() + 60
        second_ready = False
        while time.monotonic() < deadline:
            try:
                second_ready = request("/health/ready")[0] == 200
                if second_ready:
                    break
            except Exception:
                pass
            time.sleep(1)
        state_second_restart = backend_state()
        add_check(checks, requests, "second_restart_no_duplicate_recovery_or_occurrence",
                  second_ready and state_second_restart["recovery_events"] == state_after_restart["recovery_events"]
                  and state_second_restart["occurrences"] == state_after_restart["occurrences"], True,
                  "CHECK", "second backend restart", {"recovery_events": state_second_restart["recovery_events"], "occurrences": state_second_restart["occurrences"]})
        add_check(checks, requests, "audit_valid_after_second_restart", state_second_restart["audit_valid"], True, "CHECK", "audit chain")
        add_check(checks, requests, "balances_unchanged_after_second_restart", state_second_restart["balances"], expected_after_ach, "CHECK", "account balances")

        # Service cardinality plus a container_name constraint prevents Compose scaling the scheduler-owning service.
        scale_attempt = compose(["up", "-d", "--scale", "backend=2"], timeout=30, expected=None)
        backend_ps = docker(["docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}",
                             "--filter", "label=com.docker.compose.service=backend"])
        backend_ids = [item for item in backend_ps.stdout.splitlines() if item.strip()]
        scale_was_rejected = scale_attempt.returncode != 0
        add_check(checks, requests, "single_scheduler_service_cannot_scale",
                  scale_was_rejected and len(backend_ids) == 1, True, "CHECK", "docker compose up --scale backend=2",
                  {"scale_exit_code": scale_attempt.returncode, "active_backend_containers": len(backend_ids),
                   "safe_error_summary": "Compose refused scale" if scale_was_rejected else "Compose accepted scale"})

        published = docker(["docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", BACKEND_CONTAINER])
        bindings = json.loads(published.stdout)
        add_check(checks, requests, "backend_not_published_to_host", not any(bool(value) for value in bindings.values()), True,
                  "CHECK", "docker inspect network ports", bindings)
        volume = docker(["docker", "volume", "inspect", "--format", "{{.Name}}", f"{PROJECT}-data"])
        add_check(checks, requests, "persistent_volume_exists", volume.stdout.strip(), f"{PROJECT}-data", "CHECK", "docker volume inspect")

        backend_uid = compose(["exec", "-T", "backend", "id", "-u"]).stdout.strip()
        frontend_uid = compose(["exec", "-T", "frontend", "id", "-u"]).stdout.strip()
        volume_permissions = compose(["exec", "-T", "backend", "stat", "-c", "%u:%g %a", "/var/lib/shift-bank", database_path]).stdout.strip().splitlines()
        add_check(checks, requests, "backend_non_root_and_writable_volume", backend_uid == "10001" and volume_permissions[0].startswith("10001:10001") and volume_permissions[1].startswith("10001:10001"), True,
                  "CHECK", "container UID and SQLite volume owner", {"backend_uid": backend_uid, "volume_owner_modes": volume_permissions})
        add_check(checks, requests, "nginx_non_root", frontend_uid == "101", True, "CHECK", "frontend container UID", {"uid": frontend_uid})
        health_deadline = time.monotonic() + 40
        health = frontend_health = "starting"
        while time.monotonic() < health_deadline:
            health = docker(["docker", "inspect", "--format", "{{.State.Health.Status}}", BACKEND_CONTAINER]).stdout.strip()
            frontend_health = docker(["docker", "inspect", "--format", "{{.State.Health.Status}}", f"{PROJECT}-frontend"]).stdout.strip()
            if health == frontend_health == "healthy":
                break
            time.sleep(2)
        add_check(checks, requests, "container_healthchecks", (health, frontend_health), ("healthy", "healthy"), "CHECK", "docker inspect health")

        missing_encryption = run_container_startup_probe("missing-encryption-key", ["SHIFT_BANK_ENCRYPTION_KEYS=", "SHIFT_BANK_ACTIVE_KEY_VERSION="],
                                                          "Sensitive data protection key")
        checks["missing_encryption_key_fails_startup"] = missing_encryption
        missing_audit = run_container_startup_probe("missing-audit-key", ["SHIFT_BANK_AUDIT_KEY="], "Audit integrity key")
        checks["missing_audit_key_fails_startup"] = missing_audit
        missing_admin = run_container_startup_probe("missing-admin-token", ["SHIFT_BANK_AUDIT_ADMIN_TOKEN="], "Audit verification credentials")
        checks["missing_admin_credential_fails_startup"] = missing_admin

        image_inspection = docker(["docker", "image", "inspect", "shift-bank-e3-openspec-backend:local", "--format", "{{json .Config.Env}}"])
        image_environment = json.loads(image_inspection.stdout)
        embedded_secret_names = [value.split("=", 1)[0] for value in image_environment
                                 if value.split("=", 1)[0] in {"SHIFT_BANK_ENCRYPTION_KEYS", "SHIFT_BANK_AUDIT_KEY", "SHIFT_BANK_AUDIT_ADMIN_TOKEN"}]
        add_check(checks, requests, "secrets_not_baked_into_backend_image", embedded_secret_names, [], "CHECK", "docker image config")
        ignored = ".env.local" in (DEPLOY / ".gitignore").read_text(encoding="utf-8") and (DEPLOY / ".env.local").exists()
        add_check(checks, requests, "local_env_file_is_git_ignored", ignored, True, "CHECK", "deployment/.gitignore")

        final_state = backend_state()
        add_check(checks, requests, "final_audit_verifies", final_state["audit_valid"], True, "CHECK", "final audit chain")
        add_check(checks, requests, "final_financial_invariants", final_state["balances"] == expected_after_ach and final_state["transactions"] == 3,
                  True, "CHECK", "final balances/history")
    except Exception as exc:
        checks["execution"] = {"status": "FAIL", "error_type": type(exc).__name__, "safe_error": str(exc)[:500]}
    finally:
        timestamps["verification_finished_utc"] = utc_now()
        passed = bool(checks) and all(item.get("status") == "PASS" for item in checks.values())
        result = {"run_id": f"DEPLOYMENT_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                  "status": "PASS" if passed else "FAIL", "timestamps": timestamps,
                  "project": PROJECT, "checks": checks, "request_records": requests,
                  "secrets_or_mfa_codes_recorded": False, "commands": {"compose_project": "docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml",
                                                                         "verification_script": "python deployment/verify_deployment.py --output <evidence-json> --http-log <evidence-http-json>"}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.http_log.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        args.http_log.write_text(json.dumps({"timestamps": timestamps, "requests_and_checks": requests}, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "checks": {name: item["status"] for name, item in checks.items()},
                          "evidence": str(args.output)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
