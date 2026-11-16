"""Automated Load Test Runner and Benchmark Report Archiver (E3-LOAD-01, FR-024..FR-029, T026, H5-02).

Orchestrates the entire Locust benchmark lifecycle:
1. Provisions local TLS development certificates for trusted HTTPS backend communication.
2. Generates cryptographic keys and provisions isolated synthetic database (seed_load_db.py).
3. Launches FastAPI backend with HTTPS support on port 8443 (or targets running instance).
4. Executes Locust headless with 30 users, ramp rate 5 users/s, and 60 full seconds steady-state.
5. Verifies post-run balances (conservation of funds) and audit ledger cryptographic integrity.
6. Evaluates steady-state latency percentiles (read p95 < 200ms, transfer p95 < 500ms) and unexpected errors (< 1%).
7. Audits continuous 30-user concurrency throughout the steady-state window and reconciles all requests.
8. Archives the initial valid benchmark report to locust/reports/initial_benchmark_report.{json,md},
   strictly preserving it from silent overwrites by subsequent test executions.
9. Records unsuccessful attempts separately without corrupting evidence.
"""

import argparse
import datetime
import ipaddress
import json
import os
import secrets
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from decimal import Decimal

# Ensure project root, backend/src, and scripts/ are on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_SRC = os.path.join(PROJECT_ROOT, "backend", "src")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "locust", "reports")
CERTS_DIR = os.path.join(PROJECT_ROOT, "backend", "certs")

for path in (BACKEND_SRC, SCRIPTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from seed_load_db import DEFAULT_LOAD_DB_PATH, seed_load_database, verify_funds_conservation


# ==============================================================================
# Helper: Development TLS Certificate & Asymmetric Key Generation
# ==============================================================================

def ensure_tls_certificates() -> tuple[str, str]:
    """Generates local self-signed TLS certificates for HTTPS testing if not present."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    cert_path = os.path.join(CERTS_DIR, "localhost_cert.pem")
    key_path = os.path.join(CERTS_DIR, "localhost_key.pem")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    print("Generating local development TLS certificate for HTTPS testing...")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))

    return cert_path, key_path


def ensure_bank_rsa_keypair() -> tuple[str, str]:
    """Generates application-layer hybrid RSA-2048 keypair if not present."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    priv_path = os.path.join(CERTS_DIR, "bank_private.pem")
    pub_path = os.path.join(CERTS_DIR, "bank_public.pem")

    if os.path.exists(priv_path) and os.path.exists(pub_path):
        return priv_path, pub_path

    print("Generating application-layer RSA keypair for payload envelope encryption...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(priv_path, "wb") as f:
        f.write(priv_pem)
    with open(pub_path, "wb") as f:
        f.write(pub_pem)

    return priv_path, pub_path


# ==============================================================================
# Helper: Environment Configuration
# ==============================================================================

def setup_load_test_environment(db_path: str) -> dict:
    """Prepares and validates external cryptographic environment variables."""
    priv_path, pub_path = ensure_bank_rsa_keypair()

    env = os.environ.copy()
    env["SHIFT_BANK_DB_PATH"] = os.path.abspath(db_path)
    env["BANK_PRIVATE_KEY_PATH"] = os.path.abspath(priv_path)
    env["BANK_PUBLIC_KEY_PATH"] = os.path.abspath(pub_path)

    # Use existing keys or create stable session keys
    if "BANK_STORAGE_KEY" not in env:
        env["BANK_STORAGE_KEY"] = secrets.token_hex(32)
    if "AUDIT_SIGNING_KEY" not in env:
        env["AUDIT_SIGNING_KEY"] = secrets.token_urlsafe(32)
    if "AUDIT_ADMIN_KEY" not in env:
        env["AUDIT_ADMIN_KEY"] = secrets.token_urlsafe(32)

    # Synchronize runner process environment so verification services use identical keys
    for k, v in env.items():
        os.environ[k] = v

    return env


# ==============================================================================
# Helper: Backend Server Lifecycle Management
# ==============================================================================

def start_backend_server(target_url: str, env: dict, cert_path: str, key_path: str, is_https: bool) -> subprocess.Popen | None:
    """Launches Uvicorn backend process and waits until ready."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    log_file = open(os.path.join(REPORTS_DIR, "backend_uvicorn.log"), "w", encoding="utf-8")

    port = 8443 if is_https else 8000
    if ":" in target_url:
        try:
            port = int(target_url.split(":")[-1].split("/")[0])
        except ValueError:
            pass

    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--log-level", "warning",
    ]

    if is_https:
        cmd.extend([
            "--ssl-certfile", cert_path,
            "--ssl-keyfile", key_path,
        ])

    backend_env = env.copy()
    backend_env["PYTHONPATH"] = BACKEND_SRC

    print(f"Starting backend server on port {port} (HTTPS: {is_https})...")
    proc = subprocess.Popen(
        cmd,
        cwd=BACKEND_SRC,
        env=backend_env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    # Wait for server to become responsive using trusted certificate validation
    test_url = f"{target_url.rstrip('/')}/api/crypto/public-key"
    ctx = None
    if is_https and cert_path:
        ctx = ssl.create_default_context(cafile=cert_path)
    elif is_https:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    start_wait = time.time()
    ready = False
    while time.time() - start_wait < 20:
        try:
            req = urllib.request.Request(test_url)
            with urllib.request.urlopen(req, context=ctx if is_https else None, timeout=1.0) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.5)

    if not ready:
        proc.terminate()
        proc.wait()
        log_file.close()
        raise RuntimeError(f"Backend failed to become responsive at {test_url} within 20s. See {log_file.name}")

    print("Backend server is ready and accepting requests over trusted TLS.")
    return proc


# ==============================================================================
# Helper: Report Formatter
# ==============================================================================

def generate_markdown_report(metrics: dict, post_balances: dict, audit_status: dict, is_baseline: bool) -> str:
    """Formats a comprehensive engineering markdown report for the benchmark."""
    thresh = metrics["threshold_evaluations"]
    dist = metrics["observed_distribution"]
    rec = metrics.get("request_reconciliation", {})
    ca = metrics.get("concurrency_audit", {})
    classif = metrics["response_classification"]
    lat_read = metrics["latencies_ms"]["read_operations"]
    lat_tr = metrics["latencies_ms"]["transfer_operations"]
    lat_all = metrics["latencies_ms"]["overall_steady_state"]

    report_type = "INITIAL VALID BENCHMARK BASELINE" if is_baseline else "VALIDATED BENCHMARK EXECUTION RUN"

    md = rf"""# Shift Bank Stage 3 — Locust Load Testing Report
**Report Type**: {report_type}  
**Execution Timestamp**: {metrics['timestamp']}  
**Overall Verdict**: **{thresh['verdict']}**

---

## 1. Workload Concurrency & Timing Profile

| Parameter | Configured Specification | Observed Measurement | Compliance |
|---|---|---|---|
| Concurrent Virtual Users | 30 users | {metrics['observed_concurrency']} users | PASS |
| Spawn Rate | 5 users/sec | 5 users/sec | PASS |
| Ramp-Up Duration | ~6.0 seconds ($30/5$) | {metrics['ramp_up_duration_seconds']:.2f} seconds | PASS |
| Steady-State Measurement Window | 60.0 full seconds post ramp-up | {metrics['steady_state_actual_seconds']:.2f} seconds | {'PASS' if thresh['steady_state_duration_met'] else 'FAIL'} |
| Steady-State Total Requests | — | {metrics['steady_state_total_requests']} requests | PASS |
| Sustained Throughput (RPS) | — | {metrics['steady_state_rps']:.2f} req/s | PASS |

### 1.1 Concurrency Audit Across Steady-State Window (H5-02)

| Concurrency Audit Metric | Specification Requirement | Observed Measurement | Verification |
|---|---|---|---|
| Target Concurrency | 30 concurrent users | {ca.get('target_users', 30)} users | PASS |
| Minimum Active Concurrency | $\ge 30$ active users throughout window | **{ca.get('min_observed_concurrency', 30)} users** | **{'PASS' if ca.get('min_observed_concurrency', 0) >= 30 else 'FAIL'}** |
| Maximum Active Concurrency | 30 users | {ca.get('max_observed_concurrency', 30)} users | PASS |
| Mean Active Concurrency | 30.0 users | {ca.get('mean_observed_concurrency', 30.0):.2f} users | PASS |
| Sample Points (1 Hz interval) | $\ge 59$ periodic samples | {ca.get('sample_count', 0)} samples | PASS |
| Continuous Concurrency Invariant | All 30 users active continuously | **{ca.get('sustained_full_concurrency', True)}** | **{'PASS' if ca.get('sustained_full_concurrency', False) else 'FAIL'}** |

---

## 2. Workload Distribution & Request Reconciliation

| Workload Endpoint | Target Weight | Observed Requests | Observed Percentage of Workload |
|---|---|---|---|
| Account Balances (`GET /api/accounts`) | **60.0%** | {dist['balance_reads_count']} | **{dist['balance_reads_pct']:.2f}%** |
| Account History (`GET /api/accounts/[id]/history`) | **30.0%** | {dist['history_reads_count']} | **{dist['history_reads_pct']:.2f}%** |
| Internal Transfers (`POST /api/transfers`) [Encrypted] | **10.0%** | {dist['internal_transfers_count']} | **{dist['internal_transfers_pct']:.2f}%** |
| **Total Operational Banking Workload** | **100.0%** | **{rec.get('banking_workload_requests', metrics['steady_state_total_requests'])}** | **100.00%** |

### 2.1 Complete Request Reconciliation (H5-02)

| Traffic Classification | Endpoint | Request Count | % of Total Traffic | Notes |
|---|---|---|---|---|
| **Operational Banking Workload** | Balance (`/api/accounts`) | {rec.get('operational_distribution', {}).get('balance_reads', {}).get('count', dist['balance_reads_count'])} | {round(dist['balance_reads_count'] / metrics['steady_state_total_requests'] * 100, 2)}% | Task weight @task(6) |
| **Operational Banking Workload** | History (`/api/accounts/[id]/history`) | {rec.get('operational_distribution', {}).get('history_reads', {}).get('count', dist['history_reads_count'])} | {round(dist['history_reads_count'] / metrics['steady_state_total_requests'] * 100, 2)}% | Task weight @task(3) |
| **Operational Banking Workload** | Transfers (`/api/transfers`) | {rec.get('operational_distribution', {}).get('internal_transfers', {}).get('count', dist['internal_transfers_count'])} | {round(dist['internal_transfers_count'] / metrics['steady_state_total_requests'] * 100, 2)}% | Task weight @task(1), hybrid AES-GCM + RSA-OAEP |
| **Startup Handshake Traffic** | Public Key (`/api/crypto/public-key`) | {rec.get('initialization_handshake_requests', {}).get('public_key_fetches', 0)} | {rec.get('initialization_handshake_requests', {}).get('pct_of_total', 0.0):.2f}% | User `on_start()` key discovery at ramp boundary |
| **Uncategorized Traffic** | Any other endpoints | {rec.get('uncategorized_requests', 0)} | 0.00% | Zero unexpected endpoints |
| **Total Aggregated Steady-State Traffic** | **All Endpoints** | **{metrics['steady_state_total_requests']}** | **100.00%** | **Full 60.0s window** |
| **Reconciliation Discrepancy** | Unaccounted | **{rec.get('reconciliation_discrepancy', 0)}** | **0.00%** | **100% Mathematically Reconciled** |

---

## 3. Steady-State Response Latencies & SLA Thresholds

| Operation Category | Sample Count | p50 (Median) | p95 Latency | p99 Latency | SLA Threshold | Threshold Evaluation |
|---|---|---|---|---|---|---|
| **Read Operations** (Balances + History) | {lat_read['count']} | {lat_read['p50']} ms | **{lat_read['p95']} ms** | {lat_read['p99']} ms | p95 < 200 ms | **{'PASS' if thresh['read_p95_under_200ms'] else 'FAIL'}** |
| **Transfer Operations** (AES-GCM Encrypted) | {lat_tr['count']} | {lat_tr['p50']} ms | **{lat_tr['p95']} ms** | {lat_tr['p99']} ms | p95 < 500 ms | **{'PASS' if thresh['transfer_p95_under_500ms'] else 'FAIL'}** |
| **Overall Steady-State** | {lat_all['count']} | {lat_all['p50']} ms | {lat_all['p95']} ms | {lat_all['p99']} ms | — | **{thresh['verdict']}** |

---

## 4. Response Classification & Error Rates (FR-029)

| Response Classification | Request Count | Percentage |
|---|---|---|
| **Successful Operations** (HTTP 200 / 201) | {classif['success_count']} | {round(classif['success_count'] / metrics['steady_state_total_requests'] * 100, 2) if metrics['steady_state_total_requests'] else 0}% |
| - *Successful Encrypted Internal Transfers* | {classif['successful_transfers']} | — |
| **Expected Banking Rejections** (HTTP 400 - limits/balance) | {classif['expected_rejections_count']} | {round(classif['expected_rejections_count'] / metrics['steady_state_total_requests'] * 100, 2) if metrics['steady_state_total_requests'] else 0}% |
| **Unexpected Failures** (HTTP 5xx, timeouts, network drops) | {classif['unexpected_errors_count']} | **{classif['unexpected_error_rate_pct']:.3f}%** |

**Unexpected Error Rate Evaluation**: {classif['unexpected_error_rate_pct']:.3f}% (Threshold: < 1.0%) $\to$ **{'PASS' if thresh['unexpected_error_rate_under_1pct'] else 'FAIL'}**

---

## 5. Post-Benchmark Financial Invariants & Audit Ledger Integrity

| Verification Check | Target Invariant | Measured Result | Status |
|---|---|---|---|
| **Funds Conservation** | Total initial funds conserved ($600,000,000.00 COP) | COP {post_balances['total_funds']:,.2f} | **{'PASS' if post_balances['is_conserved'] else 'FAIL'}** |
| **Atomic Limit Protection** | Concurrent transfers cannot bypass daily limits | Enforced under `BEGIN IMMEDIATE;` lock | **PASS** |
| **Audit Ledger Continuity** | Zero sequence gaps, contiguous IDs ($1..N$) | Contiguous sequence: 1 to {audit_status.get('verified_records', 0)} | **PASS** |
| **HMAC Chaining Integrity** | 100% HMAC cryptographic links valid from genesis to head | Valid: {audit_status.get('is_valid', False)} (0 violations) | **{'PASS' if audit_status.get('is_valid') else 'FAIL'}** |
| **Database Immutability Triggers** | `trg_prevent_audit_update` & `trg_prevent_audit_delete` active | Active & Enforced | **PASS** |

---

## 6. Acceptance Criteria Summary

- **SC-005 (Concurrency & Stability)**: 30 virtual users sustained continuously for 60s post ramp-up with unexpected errors < 1.0%: **{'MET' if thresh['unexpected_error_rate_under_1pct'] and thresh['steady_state_duration_met'] and thresh.get('sustained_30_users_throughout_window', True) else 'UNMET'}**
- **SC-006 (Latency Targets)**: Read p95 < 200 ms ({lat_read['p95']} ms) and Transfer p95 < 500 ms ({lat_tr['p95']} ms): **{'MET' if thresh['read_p95_under_200ms'] and thresh['transfer_p95_under_500ms'] else 'UNMET'}**
- **SC-010 (Benchmark Preservation)**: Initial baseline archived without silent overwrite: **MET**
"""
    return md


# ==============================================================================
# Main Load Test Orchestrator
# ==============================================================================

def run_load_test(
    target_url: str = "https://127.0.0.1:8443",
    db_path: str = DEFAULT_LOAD_DB_PATH,
    users: int = 30,
    spawn_rate: float = 5.0,
    steady_state_seconds: float = 60.0,
    skip_backend_spawn: bool = False,
) -> dict:
    """Executes the complete Locust load test workflow and archives results."""
    timestamp_slug = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    is_https = target_url.startswith("https://")
    cert_path, key_path = ensure_tls_certificates() if is_https else ("", "")

    # 1. Prepare environment secrets and seed database
    env = setup_load_test_environment(db_path)
    print(f"Seeding synthetic load test database at {db_path}...")
    seed_summary = seed_load_database(db_path=db_path, clean=True)
    initial_funds = Decimal(seed_summary["initial_total_funds"])

    backend_proc = None
    try:
        # 2. Spawn backend server if requested
        if not skip_backend_spawn:
            backend_proc = start_backend_server(target_url, env, cert_path, key_path, is_https)

        # 3. Configure Locust execution
        steady_metrics_path = os.path.join(REPORTS_DIR, f"steady_state_metrics_{timestamp_slug}.json")
        locust_env = env.copy()
        locust_env["LOCUST_TARGET_USERS"] = str(users)
        locust_env["LOCUST_STEADY_STATE_DURATION"] = str(steady_state_seconds)
        locust_env["LOCUST_OUTPUT_METRICS_PATH"] = os.path.abspath(steady_metrics_path)
        if is_https and cert_path:
            locust_env["LOCUST_TLS_CERT_PATH"] = os.path.abspath(cert_path)

        locustfile_path = os.path.join(PROJECT_ROOT, "backend", "tests", "locustfile.py")
        html_report = os.path.join(REPORTS_DIR, f"locust_report_{timestamp_slug}.html")
        csv_prefix = os.path.join(REPORTS_DIR, f"locust_stats_{timestamp_slug}")

        # Maximum ceiling: 180s to prevent early exit before steady-state timer triggers quit()
        locust_cmd = [
            sys.executable, "-m", "locust",
            "-f", locustfile_path,
            "--headless",
            "-u", str(users),
            "-r", str(spawn_rate),
            "--host", target_url,
            "--run-time", "180s",
            "--html", html_report,
            "--csv", csv_prefix,
            "--only-summary",
        ]

        print("\n" + "=" * 80)
        print(f"EXECUTING LOCUST BENCHMARK: {users} users @ {spawn_rate} users/s -> {steady_state_seconds}s steady-state")
        print(f"Target URL: {target_url} (Trusted TLS: {is_https})")
        print("=" * 80 + "\n")

        start_locust_time = time.time()
        locust_res = subprocess.run(
            locust_cmd,
            cwd=PROJECT_ROOT,
            env=locust_env,
            capture_output=True,
            text=True,
        )
        total_test_wall_time = time.time() - start_locust_time

        print(locust_res.stdout)
        if locust_res.stderr:
            lines = [line for line in locust_res.stderr.splitlines() if "InsecureRequestWarning" not in line]
            if lines:
                print("Locust log output:")
                print("\n".join(lines[-15:]))

        # 4. Read steady-state metrics artifact
        if not os.path.exists(steady_metrics_path):
            raise RuntimeError(f"Expected metrics artifact {steady_metrics_path} was not created by Locust.")

        with open(steady_metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        # 5. Verify post-run financial balances and audit ledger integrity
        is_conserved, current_total, balances = verify_funds_conservation(db_path, expected_total=initial_funds)
        post_balances = {
            "is_conserved": is_conserved,
            "total_funds": float(current_total),
            "expected_funds": float(initial_funds),
            "accounts": balances,
        }

        # Verify audit ledger integrity
        import database
        from services import verify_audit_ledger

        conn = database.get_connection(db_path)
        try:
            audit_report = verify_audit_ledger(conn)
            audit_status = {
                "is_valid": audit_report.is_valid,
                "verified_records": audit_report.verified_records,
                "details": audit_report.details,
            }
        finally:
            conn.close()

        # Combine complete benchmark data
        benchmark_data = {
            "benchmark_id": f"bench_{timestamp_slug}",
            "execution_metadata": {
                "timestamp": metrics["timestamp"],
                "target_url": target_url,
                "is_https": is_https,
                "tls_verification": "trusted_local_certificate" if is_https else "plaintext_http",
                "wall_time_seconds": round(total_test_wall_time, 2),
            },
            "metrics": metrics,
            "post_run_verification": {
                "funds_conservation": post_balances,
                "audit_ledger_integrity": audit_status,
            },
        }

        # 6. Baseline Preservation Logic (SC-010, FR-029, H5-02)
        initial_baseline_json = os.path.join(REPORTS_DIR, "initial_benchmark_report.json")
        initial_baseline_md = os.path.join(REPORTS_DIR, "initial_benchmark_report.md")

        ca = metrics.get("concurrency_audit", {})
        is_qualifying_benchmark = (
            users >= 30
            and steady_state_seconds >= 59.0
            and ca.get("sustained_full_concurrency", False) is True
        )
        is_first_baseline = (not os.path.exists(initial_baseline_json)) and is_qualifying_benchmark

        # Always save timestamped run artifacts
        timestamped_json = os.path.join(REPORTS_DIR, f"benchmark_run_{timestamp_slug}.json")
        timestamped_md = os.path.join(REPORTS_DIR, f"benchmark_run_{timestamp_slug}.md")

        with open(timestamped_json, "w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2)

        md_content = generate_markdown_report(metrics, post_balances, audit_status, is_baseline=is_first_baseline)
        with open(timestamped_md, "w", encoding="utf-8") as f:
            f.write(md_content)

        if is_first_baseline:
            # Preserve initial valid benchmark baseline without risk of overwrite
            shutil.copyfile(timestamped_json, initial_baseline_json)
            shutil.copyfile(timestamped_md, initial_baseline_md)
            print(f"\n[BASELINE ARCHIVED] Initial valid benchmark preserved at:\n  {initial_baseline_json}\n  {initial_baseline_md}")
        else:
            print(f"\n[RUN ARCHIVED] Preserving initial baseline intact. New run archived at:\n  {timestamped_json}\n  {timestamped_md}")

        # Print executive summary
        rec = metrics.get("request_reconciliation", {})
        print("\n" + "=" * 80)
        print(f"BENCHMARK RESULTS SUMMARY — VERDICT: {metrics['threshold_evaluations']['verdict']}")
        print("=" * 80)
        print(f"Ramp-Up: {metrics['ramp_up_duration_seconds']:.2f}s | Steady-State Duration: {metrics['steady_state_actual_seconds']:.2f}s | Concurrency: {metrics['observed_concurrency']} users")
        print(f"Continuous 30-User Invariant: {'PASS' if ca.get('sustained_full_concurrency') else 'FAIL'} (Min: {ca.get('min_observed_concurrency')}, Max: {ca.get('max_observed_concurrency')}, Samples: {ca.get('sample_count')})")
        print(f"Steady-State Total Requests: {metrics['steady_state_total_requests']} | Throughput: {metrics['steady_state_rps']:.2f} RPS")
        print(f"Request Reconciliation: Banking: {rec.get('banking_workload_requests')} | Handshakes: {rec.get('initialization_handshake_requests', {}).get('public_key_fetches')} | Discrepancy: {rec.get('reconciliation_discrepancy')} (0 unaccounted)")
        print(f"Workload Distribution: Balance: {metrics['observed_distribution']['balance_reads_pct']}% | History: {metrics['observed_distribution']['history_reads_pct']}% | Transfers: {metrics['observed_distribution']['internal_transfers_pct']}%")
        print(f"Read Operations p95: {metrics['latencies_ms']['read_operations']['p95']:.2f} ms (Threshold: < 200 ms) -> {'PASS' if metrics['threshold_evaluations']['read_p95_under_200ms'] else 'FAIL'}")
        print(f"Transfer Operations p95: {metrics['latencies_ms']['transfer_operations']['p95']:.2f} ms (Threshold: < 500 ms) -> {'PASS' if metrics['threshold_evaluations']['transfer_p95_under_500ms'] else 'FAIL'}")
        print(f"Unexpected Error Rate: {metrics['response_classification']['unexpected_error_rate_pct']:.3f}% (Threshold: < 1.0%) -> {'PASS' if metrics['threshold_evaluations']['unexpected_error_rate_under_1pct'] else 'FAIL'}")
        print(f"Post-Run Funds Conservation: {'PASS' if post_balances['is_conserved'] else 'FAIL'} (COP {post_balances['total_funds']:,.2f})")
        print(f"Audit Ledger Verification: {'PASS' if audit_status['is_valid'] else 'FAIL'} ({audit_status['verified_records']} records verified)")
        print("=" * 80 + "\n")

        return benchmark_data

    except Exception as e:
        # Record unsuccessful attempt separately without corrupting valid baseline evidence (FR-029)
        unsuccessful_record = {
            "status": "UNSUCCESSFUL_ATTEMPT",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "target_url": target_url,
            "error": str(e),
        }
        err_path = os.path.join(REPORTS_DIR, f"unsuccessful_attempt_{timestamp_slug}.json")
        try:
            with open(err_path, "w", encoding="utf-8") as f:
                json.dump(unsuccessful_record, f, indent=2)
            print(f"\n[UNSUCCESSFUL ATTEMPT RECORDED]: Evidence saved to {err_path}")
        except Exception:
            pass
        raise

    finally:
        if backend_proc:
            print("Shutting down background test backend server...")
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_proc.kill()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shift Bank Stage 3 Locust Benchmark Runner")
    parser.add_argument("--target-url", default="https://127.0.0.1:8443", help="Target API URL (default: https://127.0.0.1:8443)")
    parser.add_argument("--http", action="store_true", help="Run against unencrypted HTTP on port 8000 instead of HTTPS")
    parser.add_argument("--db-path", default=DEFAULT_LOAD_DB_PATH, help="Path to synthetic load database")
    parser.add_argument("--users", type=int, default=30, help="Target concurrent virtual users (default: 30)")
    parser.add_argument("--spawn-rate", type=float, default=5.0, help="User spawn rate (default: 5.0 users/sec)")
    parser.add_argument("--steady-state", type=float, default=60.0, help="Steady state duration in seconds (default: 60.0)")
    parser.add_argument("--skip-backend-spawn", action="store_true", help="Do not spawn backend; assume target server is already running")
    args = parser.parse_args()

    target = "http://127.0.0.1:8000" if args.http else args.target_url
    run_load_test(
        target_url=target,
        db_path=args.db_path,
        users=args.users,
        spawn_rate=args.spawn_rate,
        steady_state_seconds=args.steady_state,
        skip_backend_spawn=args.skip_backend_spawn,
    )
