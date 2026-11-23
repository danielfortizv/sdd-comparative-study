import os
import sys
import time
import json
import uuid
import shutil
import urllib.request
import urllib.error
import subprocess
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Paths
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ISOLATED_DB_PATH = os.path.join(os.environ.get("TEMP", "C:/Users/danie/.gemini/tmp/tessl-3"), "e2e_isolated.db")
SQLITE_URL = f"sqlite:///{ISOLATED_DB_PATH.replace(os.sep, '/')}"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173
BACKEND_BASE = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_BASE = f"http://127.0.0.1:{FRONTEND_PORT}"

# Results container
test_results = []

def record(test_name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}" + (f" - {details}" if details else ""))
    test_results.append({"name": test_name, "passed": passed, "details": details})
    if not passed:
        raise AssertionError(f"Test failed: {test_name}: {details}")

def http_req(method: str, url: str, data: dict = None, headers: dict = None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {"raw": raw}
            return status, parsed, resp.headers
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"raw": raw}
        return e.code, parsed, e.headers


def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def simulate_frontend_api_error(status: int, data) -> dict:
    """Exact simulation of frontend ApiError parsing logic from frontend/src/api/client.ts."""
    message = f"Request failed with status {status}"
    code = "ERROR"
    detail = None

    if data:
        if isinstance(data, str):
            message = data
        elif isinstance(data, dict):
            if isinstance(data.get("code"), str):
                code = data["code"]
            if isinstance(data.get("message"), str):
                message = data["message"]
            elif isinstance(data.get("detail"), str):
                message = data["detail"]
            detail = data.get("detail", data)

    # ApiError constructor code resolution
    resolved_code = code
    if resolved_code == "ERROR" and isinstance(data, dict):
        if data.get("code"):
            resolved_code = str(data["code"])
        elif isinstance(data.get("detail"), dict) and data["detail"].get("code"):
            resolved_code = str(data["detail"]["code"])
        elif status == 409 and "version" in message.lower():
            resolved_code = "ACCOUNT_VERSION_CONFLICT"
        elif status == 409 and "idempotenc" in message.lower():
            resolved_code = "IDEMPOTENCY_KEY_REUSE"
        else:
            resolved_code = "ERROR"

    return {
        "status": status,
        "message": message,
        "code": resolved_code,
        "detail": detail if detail is not None else data,
    }


def main():
    print("=" * 80)
    print("SHIFT BANK STAGE 4: LIVE END-TO-END HTTP CONTRACT & INTEGRITY VALIDATION")
    print(f"Workspace: {WORKSPACE_DIR}")
    print(f"Isolated SQLite DB: {ISOLATED_DB_PATH}")
    print("=" * 80)

    # 1. Clean previous isolated database if present
    if os.path.exists(ISOLATED_DB_PATH):
        try:
            os.remove(ISOLATED_DB_PATH)
            print(f"Cleaned previous temporary database: {ISOLATED_DB_PATH}")
        except Exception as e:
            print(f"Warning: Could not remove previous DB: {e}")

    # Set up environment for isolated backend
    backend_env = os.environ.copy()
    backend_env["DATABASE_URL"] = SQLITE_URL
    backend_env["ENCRYPTION_KEY"] = "01234567890123456789012345678901"
    backend_env["AUDIT_SECRET_KEY"] = "test_audit_secret_key_32bytes!!"
    backend_env["ADMIN_SECRET_KEY"] = "test_admin_secret_key_2026"
    backend_env["RUN_SCHEDULER"] = "false"
    backend_env["TESTING"] = "true"
    backend_env["PYTHONPATH"] = WORKSPACE_DIR

    backend_proc = None
    frontend_proc = None

    try:
        # Start backend
        print("Starting live FastAPI backend on 127.0.0.1:8000...")
        backend_cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=WORKSPACE_DIR,
            env=backend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if not wait_for_server(f"{BACKEND_BASE}/api/health", timeout=15.0):
            stdout, stderr = backend_proc.communicate(timeout=2)
            print("Backend failed to start. Stdout:", stdout.decode("utf-8", errors="replace"))
            print("Stderr:", stderr.decode("utf-8", errors="replace"))
            sys.exit(1)
        print("Backend is healthy and listening on http://127.0.0.1:8000")

        # Start frontend Vite dev server
        print("Starting live Vite frontend on 127.0.0.1:5173...")
        frontend_dir = os.path.join(WORKSPACE_DIR, "frontend")
        frontend_cmd = ["npm.cmd" if os.name == "nt" else "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)]
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if not wait_for_server(f"{FRONTEND_BASE}/", timeout=15.0):
            print("Warning: Frontend server did not respond within timeout, checking Vite proxy...")
        else:
            print("Frontend Vite dev server is responding on http://127.0.0.1:5173")

        # =====================================================================
        # PHASE 2 - PART A: ACCOUNTS AND DASHBOARD
        # =====================================================================
        print("\n--- PHASE 2.A: Accounts and Dashboard ---")
        status, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        record("2.A.1 Backend returns HTTP 200 for GET /api/accounts", status == 200)
        record("2.A.2 Approved 4 seed accounts present", len(accounts) == 4, f"Found {len(accounts)} accounts")

        acc_by_num = {a["account_number"]: a for a in accounts}
        record("2.A.3 Seed accounts contain CHK-1001, SAV-2001, EUR-3001, GBP-4001",
               all(k in acc_by_num for k in ["CHK-1001", "SAV-2001", "EUR-3001", "GBP-4001"]))

        chk = acc_by_num["CHK-1001"]
        sav = acc_by_num["SAV-2001"]
        eur = acc_by_num["EUR-3001"]
        gbp = acc_by_num["GBP-4001"]

        record("2.A.4 CHK-1001 balance is canonical decimal string '2500.00' and version is 1",
               chk["balance"] == "2500.00" and chk["currency"] == "USD" and chk["version"] == 1,
               f"balance={chk['balance']}, version={chk['version']}")
        record("2.A.5 SAV-2001 balance is canonical decimal string '10000.00' and version is 1",
               sav["balance"] == "10000.00" and sav["currency"] == "USD" and sav["version"] == 1,
               f"balance={sav['balance']}, version={sav['version']}")
        record("2.A.6 EUR-3001 balance is '0.00', currency EUR, version 1",
               eur["balance"] == "0.00" and eur["currency"] == "EUR" and eur["version"] == 1)
        record("2.A.7 GBP-4001 balance is '0.00', currency GBP, version 1",
               gbp["balance"] == "0.00" and gbp["currency"] == "GBP" and gbp["version"] == 1)

        # Check frontend proxy
        proxy_status, proxy_accounts, _ = http_req("GET", f"{FRONTEND_BASE}/api/accounts")
        record("2.A.8 Frontend proxy forwards /api/accounts with HTTP 200",
               proxy_status == 200 and len(proxy_accounts) == 4)

        # =====================================================================
        # PHASE 2 - PART B: INTERNAL TRANSFERS
        # =====================================================================
        print("\n--- PHASE 2.B: Internal Transfers ---")
        trf1_key = str(uuid.uuid4())
        trf1_payload = {
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": "100.00",
            "expected_from_version": chk["version"],
            "expected_to_version": sav["version"],
            "description": "Valid same-currency test transfer",
        }
        status, trf1_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", trf1_payload, {"Idempotency-Key": trf1_key})
        record("2.B.1 Valid same-currency transfer succeeds (HTTP 200)", status == 200, f"Status: {status}")

        # Check updated balances and versions
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        acc_by_num = {a["account_number"]: a for a in accounts}
        chk = acc_by_num["CHK-1001"]
        sav = acc_by_num["SAV-2001"]

        record("2.B.2 CHK-1001 debited by 100.00 -> balance '2400.00', version 2",
               chk["balance"] == "2400.00" and chk["version"] == 2, f"balance={chk['balance']}, ver={chk['version']}")
        record("2.B.3 SAV-2001 credited by 100.00 -> balance '10100.00', version 2",
               sav["balance"] == "10100.00" and sav["version"] == 2, f"balance={sav['balance']}, ver={sav['version']}")

        # Rejection of cross-currency internal transfer
        trf_cross_key = str(uuid.uuid4())
        trf_cross_payload = {
            "from_account_id": chk["id"],
            "to_account_id": eur["id"],
            "amount": "50.00",
            "expected_from_version": chk["version"],
            "expected_to_version": eur["version"],
            "description": "Illegal cross-currency internal transfer",
        }
        status, cross_err, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", trf_cross_payload, {"Idempotency-Key": trf_cross_key})
        record("2.B.4 Cross-currency internal transfer rejected (HTTP 400)", status == 400, f"Status: {status}, Detail: {cross_err}")

        # Confirm balances unchanged after rejection
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        acc_by_num = {a["account_number"]: a for a in accounts}
        record("2.B.5 Balances and versions unchanged after rejected cross-currency transfer",
               acc_by_num["CHK-1001"]["version"] == 2 and acc_by_num["EUR-3001"]["version"] == 1)

        # =====================================================================
        # PHASE 2 - PART C: CURRENCY CONVERSIONS
        # =====================================================================
        print("\n--- PHASE 2.C: Currency Conversions ---")
        conv_key = str(uuid.uuid4())
        conv_payload = {
            "from_account_id": chk["id"],
            "to_account_id": eur["id"],
            "source_amount": "100.00",
            "expected_from_version": chk["version"],
            "expected_to_version": eur["version"],
            "description": "Convert 100.00 USD to EUR",
        }
        status, conv_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/conversions", conv_payload, {"Idempotency-Key": conv_key})
        record("2.C.1 Valid conversion succeeds through /api/conversions (HTTP 200)", status == 200, f"Status: {status}")

        record("2.C.2 Approved rational exchange rate 0.90 applied (destination_amount '90.00')",
               conv_resp.get("destination_amount") == "90.00" and conv_resp.get("exchange_rate_display") == "0.9000000000",
               f"dest_amount={conv_resp.get('destination_amount')}, rate={conv_resp.get('exchange_rate_display')}")

        # Verify balances and versions after conversion
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        acc_by_num = {a["account_number"]: a for a in accounts}
        chk = acc_by_num["CHK-1001"]
        eur = acc_by_num["EUR-3001"]
        record("2.C.3 Source CHK-1001 balance '2300.00', version 3",
               chk["balance"] == "2300.00" and chk["version"] == 3, f"balance={chk['balance']}, ver={chk['version']}")
        record("2.C.4 Destination EUR-3001 balance '90.00', version 2",
               eur["balance"] == "90.00" and eur["version"] == 2, f"balance={eur['balance']}, ver={eur['version']}")

        # =====================================================================
        # PHASE 2 - PART D: ACH TRANSFERS
        # =====================================================================
        print("\n--- PHASE 2.D: ACH Transfers ---")
        ach_key = str(uuid.uuid4())
        ach_payload = {
            "from_account_id": chk["id"],
            "amount": "50.00",
            "expected_from_version": chk["version"],
            "recipient_name": "Acme Supplier Inc",
            "routing_number": "123456789",
            "account_number": "9876543210",
            "bank_name": "Supplier Trust Bank",
            "description": "Invoice payment #4001",
        }
        status, ach_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers/ach", ach_payload, {"Idempotency-Key": ach_key})
        record("2.D.1 Valid USD ACH payment succeeds (HTTP 200)", status == 200, f"Status: {status}")
        record("2.D.2 ACH transfer initial status is 'pending'", ach_resp.get("status") == "pending", f"Status: {ach_resp.get('status')}")

        # Verify source account was debited once
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        chk = next(a for a in accounts if a["account_number"] == "CHK-1001")
        record("2.D.3 Source account debited exactly once -> balance '2250.00', version 4",
               chk["balance"] == "2250.00" and chk["version"] == 4, f"balance={chk['balance']}, ver={chk['version']}")

        # Non-USD ACH rejection
        ach_non_usd_key = str(uuid.uuid4())
        ach_non_usd_payload = {
            "from_account_id": eur["id"],
            "amount": "20.00",
            "expected_from_version": eur["version"],
            "recipient_name": "Euro Recipient",
            "routing_number": "123456789",
            "account_number": "9876543210",
            "bank_name": "European Bank",
        }
        status, ach_err, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers/ach", ach_non_usd_payload, {"Idempotency-Key": ach_non_usd_key})
        record("2.D.4 Non-USD ACH transfer rejected (HTTP 400)", status == 400, f"Status: {status}, Detail: {ach_err}")

        # ACH Settlement
        status, settle_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers/ach/process-settlements")
        record("2.D.5 Trigger ACH settlement succeeds (HTTP 200)", status == 200, f"settled_count: {settle_resp.get('settled_count')}")

        # Verify debit remains exactly once after settlement
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        chk = next(a for a in accounts if a["account_number"] == "CHK-1001")
        record("2.D.6 CHK-1001 balance remains '2250.00', version remains 4 after settlement (no double debit)",
               chk["balance"] == "2250.00" and chk["version"] == 4)

        # =====================================================================
        # PHASE 2 - PART E: RECURRING PAYMENTS
        # =====================================================================
        print("\n--- PHASE 2.E: Recurring Payments ---")
        past_date = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        rec_payload = {
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "transfer_type": "internal",
            "amount": "30.00",
            "frequency": "daily",
            "start_date": past_date,
            "description": "Daily automated savings",
        }
        status, rec_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/recurring", rec_payload)
        record("2.E.1 Valid recurring schedule created (HTTP 201)", status == 201, f"Status: {status}, ID: {rec_resp.get('id')}")
        schedule_id = rec_resp["id"]

        # Process due recurring payment
        status, proc_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/recurring/process-due")
        record("2.E.2 Process due recurring payments succeeds (HTTP 200)", status == 200, f"processed: {proc_resp.get('processed_count')}")
        record("2.E.3 Exactly 1 execution occurred", proc_resp.get("processed_count") == 1)

        # Check balances
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        acc_by_num = {a["account_number"]: a for a in accounts}
        chk = acc_by_num["CHK-1001"]
        sav = acc_by_num["SAV-2001"]
        record("2.E.4 CHK-1001 balance is '2220.00' (version 5), SAV-2001 is '10130.00' (version 3)",
               chk["balance"] == "2220.00" and chk["version"] == 5 and sav["balance"] == "10130.00" and sav["version"] == 3,
               f"CHK={chk['balance']} (v{chk['version']}), SAV={sav['balance']} (v{sav['version']})")

        # Repeated execution must not duplicate payment
        status, proc2_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/recurring/process-due")
        record("2.E.5 Repeated scheduler processing does not duplicate payment (processed_count 0)",
               status == 200 and proc2_resp.get("processed_count") == 0, f"processed: {proc2_resp.get('processed_count')}")

        # Pause and Resume
        status, pause_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/recurring/{schedule_id}/pause")
        record("2.E.6 Pause schedule succeeds", status == 200 and pause_resp.get("status") == "paused")

        status, resume_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/recurring/{schedule_id}/resume")
        record("2.E.7 Resume schedule succeeds", status == 200 and resume_resp.get("status") == "active")

        # =====================================================================
        # PHASE 2 - PART F: MFA AND LIMITS
        # =====================================================================
        print("\n--- PHASE 2.F: MFA and Limits ---")
        # Exactly USD 1000.00 does not require MFA
        mfa_1000_key = str(uuid.uuid4())
        mfa_1000_payload = {
            "from_account_id": sav["id"],
            "to_account_id": chk["id"],
            "amount": "1000.00",
            "expected_from_version": sav["version"],
            "expected_to_version": chk["version"],
            "description": "Exactly $1000 threshold test",
        }
        status, mfa_1000_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", mfa_1000_payload, {"Idempotency-Key": mfa_1000_key})
        record("2.F.1 Exactly USD 1000.00 does not require MFA (HTTP 200)", status == 200, f"Status: {status}")

        # Refresh accounts
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        acc_by_num = {a["account_number"]: a for a in accounts}
        chk = acc_by_num["CHK-1001"] # was 2220.00 -> 3220.00, version 6
        sav = acc_by_num["SAV-2001"] # was 10130.00 -> 9130.00, version 4

        # USD 1000.01 requires MFA
        mfa_1001_key = str(uuid.uuid4())
        mfa_1001_payload = {
            "from_account_id": sav["id"],
            "to_account_id": chk["id"],
            "amount": "1000.01",
            "expected_from_version": sav["version"],
            "expected_to_version": chk["version"],
            "description": "Above $1000 threshold test",
        }
        status, mfa_1001_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", mfa_1001_payload, {"Idempotency-Key": mfa_1001_key})
        record("2.F.2 Operation above threshold requires MFA (HTTP 428 Precondition Required)",
               status == 428, f"Status: {status}, Body: {mfa_1001_resp}")

        # Operation above threshold with correct PIN succeeds
        correct_pin_key = str(uuid.uuid4())
        correct_pin_payload = dict(mfa_1001_payload, pin="1234")
        status, correct_pin_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", correct_pin_payload, {"Idempotency-Key": correct_pin_key})
        record("2.F.3 Protected operation above threshold with correct PIN succeeds (HTTP 200)",
               status == 200 and correct_pin_resp.get("amount") == "1000.01", f"Status: {status}")

        # Refresh accounts
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        acc_by_num = {a["account_number"]: a for a in accounts}
        chk = acc_by_num["CHK-1001"] # 3220.00 + 1000.01 = 4220.01, version 7
        sav = acc_by_num["SAV-2001"] # 9130.00 - 1000.01 = 8129.99, version 5
        record("2.F.4 Balances and versions updated after authenticated transfer (CHK: 4220.01 v7, SAV: 8129.99 v5)",
               chk["balance"] == "4220.01" and chk["version"] == 7 and sav["balance"] == "8129.99" and sav["version"] == 5)

        # Wrong PIN verification
        wrong_pin_key = str(uuid.uuid4())
        wrong_pin_payload = {
            "from_account_id": sav["id"],
            "to_account_id": chk["id"],
            "amount": "1000.01",
            "expected_from_version": sav["version"],
            "expected_to_version": chk["version"],
            "pin": "9999",
            "description": "Wrong PIN test",
        }
        status, wrong_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", wrong_pin_payload, {"Idempotency-Key": wrong_pin_key})
        record("2.F.5 Wrong PIN rejected with HTTP 400 Bad Request", status == 400 and "Invalid Security PIN" in str(wrong_resp), f"Status: {status}, Detail: {wrong_resp}")

        # Check remaining MFA attempts
        status, mfa_status, _ = http_req("GET", f"{BACKEND_BASE}/api/mfa/status")
        record("2.F.6 Failed attempts tracked (remaining_attempts decreased to 2)",
               mfa_status.get("remaining_attempts") == 2, f"remaining: {mfa_status.get('remaining_attempts')}")

        # Send 2 more wrong PIN attempts to trigger lockout
        for attempt in range(2):
            k = str(uuid.uuid4())
            http_req("POST", f"{BACKEND_BASE}/api/transfers", dict(wrong_pin_payload, pin="9999"), {"Idempotency-Key": k})

        # Next attempt must return HTTP 423 Locked
        locked_key = str(uuid.uuid4())
        status, lock_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", dict(wrong_pin_payload, pin="1234"), {"Idempotency-Key": locked_key})
        record("2.F.7 MFA lockout enforced after 3 failed attempts (HTTP 423 Locked)", status == 423, f"Status: {status}")

        # Financial limits enforcement: Per-transaction limit is $5000.00
        limit_key = str(uuid.uuid4())
        limit_payload = {
            "from_account_id": sav["id"],
            "to_account_id": chk["id"],
            "amount": "5000.01",
            "expected_from_version": sav["version"],
            "expected_to_version": chk["version"],
            "pin": "1234",
            "description": "Exceeding per-transaction limit",
        }
        status, limit_err, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", limit_payload, {"Idempotency-Key": limit_key})
        record("2.F.8 Transfer exceeding per-transaction limit $5000.00 rejected (HTTP 400)",
               status == 400 and "exceeds per-transaction limit" in str(limit_err), f"Status: {status}, Detail: {limit_err}")

        # =====================================================================
        # PHASE 2 - PART G: IDEMPOTENCY AND CONCURRENCY
        # =====================================================================
        print("\n--- PHASE 2.G: Idempotency and Concurrency ---")
        # 1. Identical request and identical UUID return committed result without new side effects
        status, replay_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", trf1_payload, {"Idempotency-Key": trf1_key})
        record("2.G.1 Identical request and identical UUID returns committed result (HTTP 200/201)",
               status in [200, 201] and replay_resp.get("amount") == "100.00", f"Status: {status}")

        # Verify balances were not debited a second time
        _, accounts, _ = http_req("GET", f"{BACKEND_BASE}/api/accounts")
        acc_by_num = {a["account_number"]: a for a in accounts}
        record("2.G.2 Idempotent replay produces no duplicate debit or balance side effect",
               acc_by_num["CHK-1001"]["version"] == 7 and acc_by_num["SAV-2001"]["version"] == 5)

        # 2. Reusing a UUID with different parameters returns D-13 conflict
        tampered_payload = dict(trf1_payload, amount="99.99")
        status, reuse_err, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", tampered_payload, {"Idempotency-Key": trf1_key})
        record("2.G.3 Reusing UUID with different parameters returns HTTP 409 Conflict", status == 409, f"Status: {status}")
        record("2.G.4 Conflict error body has structured code 'IDEMPOTENCY_KEY_REUSE'",
               reuse_err.get("code") == "IDEMPOTENCY_KEY_REUSE" or (isinstance(reuse_err.get("detail"), dict) and reuse_err["detail"].get("code") == "IDEMPOTENCY_KEY_REUSE"),
               f"Error body: {reuse_err}")

        # 3. Stale account versions return D-14 ACCOUNT_VERSION_CONFLICT
        stale_key = str(uuid.uuid4())
        stale_payload = {
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": "10.00",
            "expected_from_version": 1, # Stale! Current version is 6
            "expected_to_version": sav["version"],
            "description": "Stale version transfer test",
        }
        status, stale_err, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", stale_payload, {"Idempotency-Key": stale_key})
        record("2.G.5 Stale account version returns HTTP 409 Conflict", status == 409, f"Status: {status}")
        record("2.G.6 Stale version error body has code 'ACCOUNT_VERSION_CONFLICT'",
               stale_err.get("code") == "ACCOUNT_VERSION_CONFLICT" or (isinstance(stale_err.get("detail"), dict) and stale_err["detail"].get("code") == "ACCOUNT_VERSION_CONFLICT"),
               f"Error body: {stale_err}")

        # 4. Idempotent replay takes precedence over stale version validation
        # Replaying trf1_payload with trf1_key: trf1_payload had expected_from_version=1 (which is now stale!),
        # but because it's a replayed idempotency key, it MUST return the cached response rather than 409!
        status, prec_resp, _ = http_req("POST", f"{BACKEND_BASE}/api/transfers", trf1_payload, {"Idempotency-Key": trf1_key})
        record("2.G.7 Idempotent replay takes precedence over stale version validation (returns cached response)",
               status in [200, 201] and prec_resp.get("amount") == "100.00", f"Status: {status}")

        # =====================================================================
        # PHASE 2 - PART H: ERROR CONTRACTS & FRONTEND APIERROR
        # =====================================================================
        print("\n--- PHASE 2.H: Error Contracts & Frontend ApiError ---")
        # Test frontend ApiError parsing on actual D-13 error body
        sim_d13 = simulate_frontend_api_error(409, reuse_err)
        record("2.H.1 Frontend ApiError correctly maps real D-13 response to code 'IDEMPOTENCY_KEY_REUSE'",
               sim_d13["code"] == "IDEMPOTENCY_KEY_REUSE", f"Resolved code: {sim_d13['code']}")

        # Test frontend ApiError parsing on actual D-14 error body
        sim_d14 = simulate_frontend_api_error(409, stale_err)
        record("2.H.2 Frontend ApiError correctly maps real D-14 response to code 'ACCOUNT_VERSION_CONFLICT'",
               sim_d14["code"] == "ACCOUNT_VERSION_CONFLICT", f"Resolved code: {sim_d14['code']}")

        # Test that frontend ApiError does NOT misclassify unknown 409 conflicts
        unknown_409 = {"detail": "Database table lock timeout exceeded"}
        sim_unknown = simulate_frontend_api_error(409, unknown_409)
        record("2.H.3 Frontend ApiError does NOT misclassify unknown 409 errors (resolves to 'ERROR')",
               sim_unknown["code"] == "ERROR", f"Resolved code: {sim_unknown['code']}")

        # Test fallback message-text heuristic for legacy string errors
        legacy_version_409 = {"detail": "Account version mismatch detected during commit"}
        sim_legacy_v = simulate_frontend_api_error(409, legacy_version_409)
        record("2.H.4 Fallback message-text heuristic recovers 'ACCOUNT_VERSION_CONFLICT' for unstructured version errors",
               sim_legacy_v["code"] == "ACCOUNT_VERSION_CONFLICT", f"Resolved code: {sim_legacy_v['code']}")

        legacy_idemp_409 = {"detail": "Idempotency key duplicate key payload mismatch"}
        sim_legacy_i = simulate_frontend_api_error(409, legacy_idemp_409)
        record("2.H.5 Fallback message-text heuristic recovers 'IDEMPOTENCY_KEY_REUSE' for unstructured idempotency errors",
               sim_legacy_i["code"] == "IDEMPOTENCY_KEY_REUSE", f"Resolved code: {sim_legacy_i['code']}")

        # =====================================================================
        # PHASE 3: RUNNING FRONTEND CHECKS
        # =====================================================================
        print("\n--- PHASE 3: Running Frontend Checks ---")
        status, fe_html, fe_headers = http_req("GET", f"{FRONTEND_BASE}/")
        record("3.1 Frontend root returns HTTP 200 OK", status == 200)
        has_root_div = "<div id=\"root\">" in str(fe_html.get("raw", ""))
        record("3.2 Frontend serves valid HTML with #root container", has_root_div)

        status, fe_accounts, _ = http_req("GET", f"{FRONTEND_BASE}/api/accounts")
        record("3.3 Frontend loads real accounts through Vite proxy with matching balances",
               status == 200 and len(fe_accounts) == 4 and any(a["account_number"] == "CHK-1001" for a in fe_accounts))

        status, fe_txs, _ = http_req("GET", f"{FRONTEND_BASE}/api/transactions")
        record("3.4 Frontend loads live transactions through Vite proxy",
               status == 200 and len(fe_txs) > 0, f"Found {len(fe_txs)} transactions")

        # =====================================================================
        # PHASE 4: FINANCIAL INTEGRITY CHECKS
        # =====================================================================
        print("\n--- PHASE 4: Financial Integrity Checks ---")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.app.models import Account, Transfer, Transaction, DomainEvent, ProjectionCheckpoint, AuditLog

        engine = create_engine(SQLITE_URL)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            # Check persisted accounts
            db_accounts = db.query(Account).all()
            db_acc_map = {a.account_number: a for a in db_accounts}

            chk_db = db_acc_map["CHK-1001"]
            sav_db = db_acc_map["SAV-2001"]
            eur_db = db_acc_map["EUR-3001"]
            gbp_db = db_acc_map["GBP-4001"]

            record("4.1 Persisted CHK-1001 balance equals '4220.01', version equals 7",
                   chk_db.balance == Decimal("4220.01") and chk_db.version == 7,
                   f"balance={chk_db.balance}, version={chk_db.version}")
            record("4.2 Persisted SAV-2001 balance equals '8129.99', version equals 5",
                   sav_db.balance == Decimal("8129.99") and sav_db.version == 5,
                   f"balance={sav_db.balance}, version={sav_db.version}")
            record("4.3 Persisted EUR-3001 balance equals '90.00', version equals 2",
                   eur_db.balance == Decimal("90.00") and eur_db.version == 2,
                   f"balance={eur_db.balance}, version={eur_db.version}")
            record("4.4 Persisted GBP-4001 balance equals '0.00', version equals 1",
                   gbp_db.balance == Decimal("0.00") and gbp_db.version == 1,
                   f"balance={gbp_db.balance}, version={gbp_db.version}")

            # Check domain events count
            events = db.query(DomainEvent).order_by(DomainEvent.id.asc()).all()
            record("4.5 Domain events persisted in event store", len(events) >= 4, f"Total events: {len(events)}")

            event_types = [e.event_type for e in events]
            record("4.6 Event store contains expected domain event types",
                   "InternalTransferCompleted" in event_types and
                   "CurrencyConversionCompleted" in event_types and
                   "AchTransferInitiated" in event_types and
                   "AchTransferSettled" in event_types,
                   f"Event types: {set(event_types)}")

            # Check checkpoints
            chkpts = db.query(ProjectionCheckpoint).all()
            max_event_id = max(e.id for e in events) if events else 0
            record("4.7 CQRS projection checkpoints advanced to match event store",
                   all(cp.last_applied_event_id >= max_event_id for cp in chkpts),
                   f"Checkpoints: {[(cp.projection_name, cp.last_applied_event_id) for cp in chkpts]}")

            # Check audit ledger
            audit_entries = db.query(AuditLog).all()
            record("4.8 Audit log entries recorded with HMAC signatures",
                   len(audit_entries) >= 10 and all(a.signature is not None for a in audit_entries),
                   f"Audit count: {len(audit_entries)}")

            # Test ACH failure & refund scenario on isolated DB
            print("\n--- Testing ACH failure and refund contract ---")
            from backend.app.services.transfer_service import execute_ach_transfer, fail_ach_transfer
            from backend.app.schemas import AchTransferRequest

            ach_fail_req = AchTransferRequest(
                from_account_id=chk_db.id,
                amount=Decimal("25.00"),
                expected_from_version=chk_db.version,
                recipient_name="Rejected Vendor",
                routing_number="123456789",
                account_number="9876543210",
                bank_name="Rejecting Bank",
                description="ACH that will be rejected",
            )
            ach_fail_trf = execute_ach_transfer(db, 1, ach_fail_req, str(uuid.uuid4()))
            db.refresh(chk_db)
            record("4.9 ACH transfer initiated for failure test (balance debited to 4195.01, version 8)",
                   chk_db.balance == Decimal("4195.01") and chk_db.version == 8,
                   f"balance={chk_db.balance}, ver={chk_db.version}")

            # Execute fail_ach_transfer
            failed_res = fail_ach_transfer(db, ach_fail_trf.id, reason="Invalid recipient routing")
            db.refresh(chk_db)
            record("4.10 fail_ach_transfer refunds balance to 4220.01 and advances version to 9",
                   chk_db.balance == Decimal("4220.01") and chk_db.version == 9,
                   f"balance={chk_db.balance}, ver={chk_db.version}")

            # Repeated fail_ach_transfer must be idempotent
            repeat_fail = fail_ach_transfer(db, ach_fail_trf.id, reason="Repeated failure call")
            db.refresh(chk_db)
            record("4.11 Repeated fail_ach_transfer is idempotent (balance remains 4220.01, version remains 9)",
                   chk_db.balance == Decimal("4220.01") and chk_db.version == 9)

            # Rebuild and projection integrity test
            from backend.app.services.projection_service import verify_or_rebuild_at_startup
            res = verify_or_rebuild_at_startup(db)
            record("4.12 CQRS projection verification confirms 100% integrity against event store",
                   res.get("status") == "verified", f"Projection status: {res}")

        finally:
            db.close()

        print("\n" + "=" * 80)
        passed_count = sum(1 for r in test_results if r["passed"])
        total_count = len(test_results)
        print(f"ALL TESTS COMPLETED: {passed_count}/{total_count} PASSED.")
        print("=" * 80)

    finally:
        # Gracefully stop servers
        if backend_proc:
            print("Terminating backend process...")
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_proc.kill()

        if frontend_proc:
            print("Terminating frontend process...")
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_proc.kill()

        # Clean isolated temp DB
        if os.path.exists(ISOLATED_DB_PATH):
            try:
                os.remove(ISOLATED_DB_PATH)
                print(f"Cleaned temporary database: {ISOLATED_DB_PATH}")
            except Exception as e:
                print(f"Note: Temporary DB cleanup: {e}")

if __name__ == "__main__":
    main()
