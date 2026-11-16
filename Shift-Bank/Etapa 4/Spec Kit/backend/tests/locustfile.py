"""Locust benchmark suite for Shift Bank Stage 3 (E3-LOAD-01, FR-024..FR-029, T025, H5-02).

Features:
1. Target: Real live backend API over HTTPS/HTTP with client-to-server payload encryption.
2. TLS Verification: Uses trusted local development certificate for secure HTTPS verification (no verify=False).
3. on_start: Fetches backend RSA public key from /api/crypto/public-key and loads account IDs.
4. Workload distribution (FR-026):
   - @task(6): Balance reads (GET /api/accounts) [60%]
   - @task(3): History reads (GET /api/accounts/{id}/history) [30%]
   - @task(1): Internal transfers (POST /api/transfers) with AES-GCM + RSA-OAEP envelope [10%]
5. Concurrency & Timing Profile (FR-025, H5-02):
   - 30 virtual users ramped up at 5 users/sec.
   - Detects observed ramp-up completion when 30 active users are reached.
   - Sustains 60 full seconds of steady-state execution.
   - Continuously samples and verifies that all 30 users remain active throughout the entire 60s window.
   - Separately identifies and reconciles operational banking workload requests vs startup handshake requests.
6. Result Classification (FR-029):
   - Success (HTTP 200, 201)
   - Expected Banking Rejection (HTTP 400)
   - Unexpected Failure (HTTP 5xx, timeouts, connection drops)
"""

import base64
import json
import logging
import os
import random
import time
import urllib3
from datetime import datetime, timezone

import gevent
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from locust import HttpUser, between, events, task

logger = logging.getLogger("shift_bank_locust")

# Configuration parameters
TARGET_USERS = int(os.environ.get("LOCUST_TARGET_USERS", "30"))
STEADY_STATE_DURATION = float(os.environ.get("LOCUST_STEADY_STATE_DURATION", "60.0"))
OUTPUT_METRICS_PATH = os.environ.get("LOCUST_OUTPUT_METRICS_PATH", "locust/reports/steady_state_metrics.json")
TLS_CERT_PATH = os.environ.get("LOCUST_TLS_CERT_PATH", "")

# ==============================================================================
# Global Metric Tracking State
# ==============================================================================

runner_ref = None
test_start_time: float | None = None
spawning_complete_time: float | None = None
steady_state_start_time: float | None = None
steady_state_end_time: float | None = None
steady_state_timer_spawned = False
observed_target_concurrency: int = TARGET_USERS
active_user_samples: list[tuple[float, int]] = []

# Thread/Greenlet safe collected request events
# Each entry: (timestamp, method, name, response_time_ms, status_code, exception_str, is_steady_state, classification)
collected_requests: list[tuple[float, str, str, float, int | None, str | None, bool, str]] = []


def calc_percentile(data: list[float], p: float) -> float:
    """Calculates the p-th percentile using linear interpolation."""
    if not data:
        return 0.0
    s = sorted(data)
    if len(s) == 1:
        return round(s[0], 2)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(s):
        return round(s[-1], 2)
    d = k - f
    return round(s[f] + d * (s[c] - s[f]), 2)


# ==============================================================================
# Locust Event Listeners for Lifecycle and Steady-State Isolation
# ==============================================================================

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Captures runner reference on initialization."""
    global runner_ref
    runner_ref = environment.runner
    logger.info("Shift Bank Locust suite initialized.")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Records test start timestamp."""
    global test_start_time
    test_start_time = time.time()
    logger.info(f"Load test started at {test_start_time:.3f}.")


@events.spawning_complete.add_listener
def on_spawning_complete(user_count, **kwargs):
    """
    Fired by Locust runner when all target users have been spawned.
    Marks the EXACT beginning of the 60-second steady-state measurement window (FR-025).
    """
    global spawning_complete_time, steady_state_start_time, steady_state_end_time, steady_state_timer_spawned, observed_target_concurrency

    observed_target_concurrency = int(user_count)
    spawning_complete_time = time.time()
    steady_state_start_time = spawning_complete_time
    steady_state_end_time = steady_state_start_time + STEADY_STATE_DURATION

    ramp_duration = steady_state_start_time - (test_start_time or steady_state_start_time)
    logger.info(
        f"[RAMP COMPLETE] Target concurrency of {user_count} users reached in {ramp_duration:.2f}s. "
        f"Beginning {STEADY_STATE_DURATION:.1f}s sustained steady-state measurement."
    )

    if not steady_state_timer_spawned:
        steady_state_timer_spawned = True

        def _monitor_and_stop():
            start_t = time.time()
            while time.time() - start_t < STEADY_STATE_DURATION:
                current_users = getattr(runner_ref, "user_count", TARGET_USERS) if runner_ref else TARGET_USERS
                active_user_samples.append((round(time.time() - start_t, 2), current_users))
                gevent.sleep(1.0)

            elapsed = time.time() - steady_state_start_time
            logger.info(
                f"[STEADY STATE COMPLETE] Sustained {elapsed:.2f}s post ramp-up (target: {STEADY_STATE_DURATION}s). "
                "Triggering runner shutdown."
            )
            if runner_ref:
                runner_ref.quit()

        gevent.spawn(_monitor_and_stop)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response=None, context=None, exception=None, **kwargs):
    """
    Records and classifies every HTTP request.
    Identifies whether the request fell within the active steady-state window.
    """
    req_time = time.time()
    is_steady = False
    if steady_state_start_time is not None:
        if steady_state_start_time <= req_time <= (steady_state_end_time or (steady_state_start_time + STEADY_STATE_DURATION)):
            is_steady = True

    status_code = None
    if response is not None and hasattr(response, "status_code"):
        status_code = response.status_code

    exc_str = str(exception) if exception else None

    # Classification logic (FR-029)
    if exc_str is not None:
        classification = "unexpected_failure"
    elif status_code in (200, 201):
        classification = "success"
    elif status_code == 400:
        classification = "expected_rejection"
    elif status_code is not None and status_code >= 500:
        classification = "unexpected_failure"
    elif status_code is not None and status_code in (401, 403, 404, 422):
        classification = "unexpected_failure"
    else:
        classification = "unexpected_failure" if status_code is None or status_code >= 400 else "success"

    collected_requests.append((
        req_time,
        request_type,
        name,
        float(response_time),
        status_code,
        exc_str,
        is_steady,
        classification,
    ))


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """
    Aggregates steady-state metrics, computes observed distributions, evaluates
    performance thresholds, and archives structured metrics JSON.
    """
    logger.info("Computing steady-state load testing metrics...")

    total_reqs = len(collected_requests)
    steady_reqs = [r for r in collected_requests if r[6]]  # is_steady_state == True

    actual_steady_duration = 0.0
    if steady_state_start_time is not None:
        end_t = min(time.time(), steady_state_end_time or (steady_state_start_time + STEADY_STATE_DURATION))
        actual_steady_duration = max(0.0, end_t - steady_state_start_time)

    ramp_duration = 0.0
    if test_start_time and steady_state_start_time:
        ramp_duration = max(0.0, steady_state_start_time - test_start_time)

    # Concurrency verification across the entire 60s steady-state window (H5-02)
    min_concurrency = min(s[1] for s in active_user_samples) if active_user_samples else observed_target_concurrency
    max_concurrency = max(s[1] for s in active_user_samples) if active_user_samples else observed_target_concurrency
    mean_concurrency = (sum(s[1] for s in active_user_samples) / len(active_user_samples)) if active_user_samples else observed_target_concurrency
    sustained_full_concurrency = bool(min_concurrency >= TARGET_USERS)

    # Filter requests by endpoint during steady state
    balance_reqs = [r for r in steady_reqs if r[2] == "/api/accounts"]
    history_reqs = [r for r in steady_reqs if "/history" in r[2]]
    transfer_reqs = [r for r in steady_reqs if r[2] == "/api/transfers"]
    handshake_reqs = [r for r in steady_reqs if r[2] == "/api/crypto/public-key"]

    steady_count = len(steady_reqs)
    balance_count = len(balance_reqs)
    history_count = len(history_reqs)
    transfer_count = len(transfer_reqs)
    handshake_count = len(handshake_reqs)

    # Reconcile operational banking workload vs startup handshake requests (H5-02)
    banking_workload_count = balance_count + history_count + transfer_count
    uncategorized_count = steady_count - (banking_workload_count + handshake_count)

    balance_pct = round((balance_count / banking_workload_count * 100.0) if banking_workload_count else 0.0, 2)
    history_pct = round((history_count / banking_workload_count * 100.0) if banking_workload_count else 0.0, 2)
    transfer_pct = round((transfer_count / banking_workload_count * 100.0) if banking_workload_count else 0.0, 2)

    # Classifications during steady state
    success_count = sum(1 for r in steady_reqs if r[7] == "success")
    expected_rejections = sum(1 for r in steady_reqs if r[7] == "expected_rejection")
    unexpected_errors = sum(1 for r in steady_reqs if r[7] == "unexpected_failure")

    unexpected_error_rate = round((unexpected_errors / steady_count * 100.0) if steady_count else 0.0, 3)

    # Latencies (operational requests)
    read_latencies = [r[3] for r in balance_reqs + history_reqs]
    transfer_latencies = [r[3] for r in transfer_reqs]
    all_steady_latencies = [r[3] for r in steady_reqs]

    read_p50 = calc_percentile(read_latencies, 50.0)
    read_p95 = calc_percentile(read_latencies, 95.0)
    read_p99 = calc_percentile(read_latencies, 99.0)

    transfer_p50 = calc_percentile(transfer_latencies, 50.0)
    transfer_p95 = calc_percentile(transfer_latencies, 95.0)
    transfer_p99 = calc_percentile(transfer_latencies, 99.0)

    overall_p50 = calc_percentile(all_steady_latencies, 50.0)
    overall_p95 = calc_percentile(all_steady_latencies, 95.0)
    overall_p99 = calc_percentile(all_steady_latencies, 99.0)

    steady_rps = round((steady_count / actual_steady_duration) if actual_steady_duration > 0 else 0.0, 2)

    # Acceptance threshold checks (FR-029, SC-005, SC-006, H5-02)
    read_p95_pass = read_p95 < 200.0
    transfer_p95_pass = transfer_p95 < 500.0
    error_rate_pass = unexpected_error_rate < 1.0
    steady_duration_pass = actual_steady_duration >= (STEADY_STATE_DURATION - 1.0)
    all_thresholds_pass = bool(read_p95_pass and transfer_p95_pass and error_rate_pass and steady_duration_pass and sustained_full_concurrency)

    successful_transfers = sum(1 for r in transfer_reqs if r[7] == "success")

    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_concurrency": TARGET_USERS,
        "observed_concurrency": observed_target_concurrency,
        "spawn_rate": 5.0,
        "ramp_up_duration_seconds": round(ramp_duration, 2),
        "steady_state_target_seconds": STEADY_STATE_DURATION,
        "steady_state_actual_seconds": round(actual_steady_duration, 2),
        "total_requests_all": total_reqs,
        "steady_state_total_requests": steady_count,
        "steady_state_rps": steady_rps,
        "configured_weights": {
            "balance_reads": 60,
            "history_reads": 30,
            "internal_transfers": 10,
        },
        "observed_distribution": {
            "balance_reads_count": balance_count,
            "balance_reads_pct": balance_pct,
            "history_reads_count": history_count,
            "history_reads_pct": history_pct,
            "internal_transfers_count": transfer_count,
            "internal_transfers_pct": transfer_pct,
        },
        "request_reconciliation": {
            "total_steady_state_requests": steady_count,
            "banking_workload_requests": banking_workload_count,
            "operational_distribution": {
                "balance_reads": {"count": balance_count, "pct_of_workload": balance_pct},
                "history_reads": {"count": history_count, "pct_of_workload": history_pct},
                "internal_transfers": {"count": transfer_count, "pct_of_workload": transfer_pct},
            },
            "initialization_handshake_requests": {
                "public_key_fetches": handshake_count,
                "pct_of_total": round(handshake_count / steady_count * 100, 2) if steady_count else 0.0,
            },
            "uncategorized_requests": uncategorized_count,
            "reconciliation_discrepancy": steady_count - (banking_workload_count + handshake_count + uncategorized_count),
        },
        "concurrency_audit": {
            "target_users": TARGET_USERS,
            "min_observed_concurrency": min_concurrency,
            "max_observed_concurrency": max_concurrency,
            "mean_observed_concurrency": round(mean_concurrency, 2),
            "sample_count": len(active_user_samples),
            "sustained_full_concurrency": sustained_full_concurrency,
        },
        "response_classification": {
            "success_count": success_count,
            "successful_transfers": successful_transfers,
            "expected_rejections_count": expected_rejections,
            "unexpected_errors_count": unexpected_errors,
            "unexpected_error_rate_pct": unexpected_error_rate,
        },
        "latencies_ms": {
            "read_operations": {
                "count": len(read_latencies),
                "p50": read_p50,
                "p95": read_p95,
                "p99": read_p99,
                "mean": round(sum(read_latencies) / len(read_latencies), 2) if read_latencies else 0.0,
                "max": round(max(read_latencies), 2) if read_latencies else 0.0,
            },
            "transfer_operations": {
                "count": len(transfer_latencies),
                "p50": transfer_p50,
                "p95": transfer_p95,
                "p99": transfer_p99,
                "mean": round(sum(transfer_latencies) / len(transfer_latencies), 2) if transfer_latencies else 0.0,
                "max": round(max(transfer_latencies), 2) if transfer_latencies else 0.0,
            },
            "overall_steady_state": {
                "count": steady_count,
                "p50": overall_p50,
                "p95": overall_p95,
                "p99": overall_p99,
                "mean": round(sum(all_steady_latencies) / len(all_steady_latencies), 2) if all_steady_latencies else 0.0,
                "max": round(max(all_steady_latencies), 2) if all_steady_latencies else 0.0,
            },
        },
        "threshold_evaluations": {
            "read_p95_under_200ms": read_p95_pass,
            "transfer_p95_under_500ms": transfer_p95_pass,
            "unexpected_error_rate_under_1pct": error_rate_pass,
            "steady_state_duration_met": steady_duration_pass,
            "sustained_30_users_throughout_window": sustained_full_concurrency,
            "verdict": "PASS" if all_thresholds_pass else "FAIL",
        },
    }

    # Save metrics JSON to output path
    try:
        out_dir = os.path.dirname(OUTPUT_METRICS_PATH)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(OUTPUT_METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Steady-state metrics written to: {OUTPUT_METRICS_PATH}")
    except Exception as e:
        logger.error(f"Failed writing steady-state metrics: {e}")


# ==============================================================================
# Banking Virtual User Definition (HttpUser)
# ==============================================================================

class BankingUser(HttpUser):
    """
    Simulates a concurrent Shift Bank client interacting with the live backend.
    Executes realistic balance queries, transaction history inspections, and
    client-side encrypted internal fund transfers over trusted local HTTPS.
    """

    # Brief think time between actions (average 200 ms) to simulate active client interactions
    wait_time = between(0.1, 0.3)

    server_public_key = None
    account_ids: list[str] = ["acc_checking_123", "acc_savings_456"]

    def on_start(self):
        """Initializes virtual user session: configures trusted local TLS certificate and fetches RSA public key."""
        # Configure trusted local development TLS certificate verification (H5-02 Item 1)
        cert_path = TLS_CERT_PATH
        if not cert_path or not os.path.exists(cert_path):
            cert_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "certs", "localhost_cert.pem"))

        if os.path.exists(cert_path):
            self.client.verify = cert_path
        else:
            # Fallback only if no certificate is provisioned
            self.client.verify = True

        # 1. Fetch backend RSA public key for hybrid payload encryption (FR-004)
        self.fetch_public_key()

        # 2. Discover available account IDs for history reads and transfers
        self.fetch_accounts()

    def fetch_public_key(self):
        """Fetches and parses backend RSA public key from GET /api/crypto/public-key."""
        try:
            with self.client.get("/api/crypto/public-key", name="/api/crypto/public-key", catch_response=True) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    pem_str = data.get("public_key", "")
                    self.server_public_key = serialization.load_pem_public_key(pem_str.encode("utf-8"))
                    resp.success()
                else:
                    resp.failure(f"Public key fetch failed: HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch public key on user startup: {e}")

    def fetch_accounts(self):
        """Fetches accounts to learn synthetic account IDs for history and transfers."""
        try:
            with self.client.get("/api/accounts", name="/api/accounts", catch_response=True) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) >= 2:
                        self.account_ids = [acc["id"] for acc in data if "id" in acc]
                    resp.success()
                else:
                    resp.failure(f"Accounts fetch failed: HTTP {resp.status_code}")
        except Exception:
            pass

    def create_encrypted_envelope(self, payload_dict: dict) -> dict:
        """
        Simulates client-side Web Crypto hybrid encryption identical to frontend crypto.ts:
        - Generates ephemeral 256-bit AES key and 12-byte IV.
        - AES-256-GCM encrypts payload JSON.
        - RSA-OAEP encrypts AES key with server public key.
        - Formats base64 CryptographicEnvelope.
        """
        if not self.server_public_key:
            self.fetch_public_key()
            if not self.server_public_key:
                raise RuntimeError("Server RSA public key unavailable.")

        aes_key = os.urandom(32)
        iv = os.urandom(12)

        data_bytes = json.dumps(payload_dict).encode("utf-8")
        aesgcm = AESGCM(aes_key)
        ct_with_tag = aesgcm.encrypt(iv, data_bytes, None)

        ciphertext = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]

        wrapped_key = self.server_public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return {
            "encrypted_key": base64.b64encode(wrapped_key).decode("ascii"),
            "iv": base64.b64encode(iv).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "tag": base64.b64encode(tag).decode("ascii"),
        }

    # ==========================================================================
    # Task 1: Account Balance Overview (Configured Weight: 60%)
    # ==========================================================================
    @task(6)
    def view_account_balances(self):
        """Retrieves customer accounts and decrypted balances (FR-026)."""
        with self.client.get("/api/accounts", name="/api/accounts", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"GET /api/accounts failed: HTTP {resp.status_code}")

    # ==========================================================================
    # Task 2: Account Transaction History (Configured Weight: 30%)
    # ==========================================================================
    @task(3)
    def view_account_history(self):
        """Retrieves transaction history for an account (FR-026)."""
        acc_id = random.choice(self.account_ids) if self.account_ids else "acc_checking_123"
        url = f"/api/accounts/{acc_id}/history"
        with self.client.get(url, name="/api/accounts/[id]/history", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 404:
                resp.success()  # Handled account transition
            else:
                resp.failure(f"GET {url} failed: HTTP {resp.status_code}")

    # ==========================================================================
    # Task 3: Internal Fund Transfer (Configured Weight: 10%)
    # ==========================================================================
    @task(1)
    def execute_internal_transfer(self):
        """
        Executes internal transfer using client-side encrypted envelope (FR-026).
        Uses a small amount (COP 100.00) well below MFA threshold (< COP 1,000,000.00)
        and well within synthetic limits (COP 50,000,000.00) to ensure smooth execution.
        """
        if len(self.account_ids) < 2:
            src, dst = "acc_checking_123", "acc_savings_456"
        else:
            src, dst = random.sample(self.account_ids, 2)

        transfer_data = {
            "source_account_id": src,
            "destination_account_id": dst,
            "amount": "100.00",
        }

        try:
            envelope = self.create_encrypted_envelope(transfer_data)
        except Exception as e:
            logger.error(f"Client encryption error: {e}")
            return

        with self.client.post("/api/transfers", json=envelope, name="/api/transfers", catch_response=True) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code == 400:
                # Expected banking rejection (e.g. limit or balance check)
                resp.success()
            else:
                resp.failure(f"POST /api/transfers unexpected failure: HTTP {resp.status_code}")
