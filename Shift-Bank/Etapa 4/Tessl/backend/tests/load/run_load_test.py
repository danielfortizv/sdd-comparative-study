import os
import sys

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import time
import json
import logging
import tempfile
import subprocess
import urllib.request
from typing import Dict, Any
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("load_benchmark")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def seed_synthetic_load_database(db_file: str) -> None:
    """Initialize schema and seed funded synthetic test accounts in a fresh disposable database."""
    # Import models and Base
    from backend.app.database import Base
    from backend.app.models import User, Account, TransferLimit, MfaState
    from backend.app.services.crypto_service import encrypt_at_rest

    engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 20})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        now = datetime.now(timezone.utc)
        user = User(id=1, name="Alex Morgan", email="alex.morgan@shiftbank.mock")
        db.add(user)
        db.flush()

        # Seed with generous $50,000 balances to support sustained alternating transfers
        checking = Account(
            id=1,
            user_id=1,
            account_number="CHK-1001",
            account_type="checking",
            account_name="Primary Checking",
            balance=50000.00,
            currency="USD",
            created_at=now,
        )
        savings = Account(
            id=2,
            user_id=1,
            account_number="SAV-2001",
            account_type="savings",
            account_name="Standard Savings",
            balance=50000.00,
            currency="USD",
            created_at=now,
        )
        db.add_all([checking, savings])

        # Standard unaltered production limits: per-transaction $5,000.00, daily $10,000.00
        limits = TransferLimit(
            user_id=1,
            per_transaction_limit=5000.00,
            daily_limit=10000.00,
        )
        db.add(limits)

        # Standard MFA state
        mfa = MfaState(user_id=1, failed_attempts=0, is_locked=False, threshold=1000.00)
        db.add(mfa)

        db.commit()
        logger.info(f"Synthetic load testing database seeded at: {db_file}")
    finally:
        db.close()
        engine.dispose()


def wait_for_server_healthy(host: str, port: int, timeout_seconds: int = 15) -> bool:
    """Poll health endpoint until server responds HTTP 200."""
    url = f"http://{host}:{port}/api/health"
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def execute_locust_benchmark(
    host_url: str,
    target_users: int = 30,
    spawn_rate: int = 5,
    steady_state_seconds: int = 60,
) -> Dict[str, Any]:
    """Run Locust programmatically: ramp up to 30 users, reset stats, and measure 60s steady state."""
    from locust.env import Environment
    from backend.tests.load.locustfile import BankingUser, events
    import backend.tests.load.locustfile as lf_module

    # Configure user host
    BankingUser.host = host_url

    env = Environment(user_classes=[BankingUser], events=events)
    runner = env.create_local_runner()

    logger.info(f"Ramping up {target_users} users at {spawn_rate} users/sec...")
    runner.start(target_users, spawn_rate=spawn_rate)

    # 1. Ramp-up phase: wait until all target users are active
    ramp_up_start = time.time()
    while runner.user_count < target_users:
        if time.time() - ramp_up_start > 20:
            break
        time.sleep(0.2)

    logger.info(f"Ramp-up complete ({runner.user_count} active users). Resetting stats for pure steady-state measurement.")
    # 2. Reset stats to measure strictly the 60-second steady state after ramp-up
    runner.stats.reset_all()
    lf_module.business_rejections_count = 0

    measurement_start_time = time.time()
    logger.info(f"Starting 60-second steady-state measurement at {datetime.now(timezone.utc).isoformat()}...")

    # Wait for the full steady-state window
    time.sleep(steady_state_seconds)
    measurement_actual_duration = time.time() - measurement_start_time

    logger.info(f"Steady-state measurement complete ({measurement_actual_duration:.1f}s). Stopping users.")
    runner.stop()

    # 3. Extract and parse statistics
    stats_entries = runner.stats.entries
    total_stats = runner.stats.total

    read_latencies = []
    transfer_latencies = []

    read_count = 0
    balance_count = 0
    history_count = 0
    transfer_count = 0
    unexpected_failures = 0

    for (name, method), stat in stats_entries.items():
        if "GET" in method:
            read_count += stat.num_requests
            read_latencies.extend(stat.response_times.keys())
            if "/accounts" in name:
                balance_count += stat.num_requests
            elif "/transactions" in name:
                history_count += stat.num_requests
        elif "POST" in method and "/transfers" in name:
            transfer_count += stat.num_requests
            transfer_latencies.extend(stat.response_times.keys())
        unexpected_failures += stat.num_failures

    total_requests = total_stats.num_requests
    actual_read_pct = round((read_count / total_requests * 100), 1) if total_requests else 0.0
    actual_balance_pct = round((balance_count / total_requests * 100), 1) if total_requests else 0.0
    actual_history_pct = round((history_count / total_requests * 100), 1) if total_requests else 0.0
    actual_transfer_pct = round((transfer_count / total_requests * 100), 1) if total_requests else 0.0

    # Calculate percentiles from Locust stats
    read_p95 = 0.0
    transfer_p95 = 0.0
    total_p50 = total_stats.get_response_time_percentile(0.50)
    total_p90 = total_stats.get_response_time_percentile(0.90)
    total_p95 = total_stats.get_response_time_percentile(0.95)
    total_p99 = total_stats.get_response_time_percentile(0.99)

    for (name, method), stat in stats_entries.items():
        if "GET" in method and "/accounts" in name:
            read_p95 = max(read_p95, stat.get_response_time_percentile(0.95))
        if "GET" in method and "/transactions" in name:
            read_p95 = max(read_p95, stat.get_response_time_percentile(0.95))
        if "POST" in method and "/transfers" in name:
            transfer_p95 = max(transfer_p95, stat.get_response_time_percentile(0.95))

    unexpected_error_rate = (
        round((unexpected_failures / total_requests * 100), 2) if total_requests else 0.0
    )
    throughput_rps = round(total_requests / measurement_actual_duration, 1)

    # SLA evaluations
    read_sla_passed = read_p95 < 200.0
    transfer_sla_passed = transfer_p95 < 500.0
    error_rate_passed = unexpected_error_rate < 1.0
    overall_passed = read_sla_passed and transfer_sla_passed and error_rate_passed

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_users": target_users,
        "duration_seconds": round(measurement_actual_duration, 1),
        "total_requests": total_requests,
        "successful_requests": total_requests - unexpected_failures,
        "business_rejections_count": lf_module.business_rejections_count,
        "unexpected_failures_count": unexpected_failures,
        "unexpected_error_rate_percentage": unexpected_error_rate,
        "throughput_rps": throughput_rps,
        "traffic_distribution": {
            "read_requests_count": read_count,
            "read_requests_percentage": actual_read_pct,
            "target_read_percentage": "90% (60% balance + 30% tx history)",
            "balance_requests_count": balance_count,
            "balance_requests_percentage": actual_balance_pct,
            "target_balance_percentage": "60%",
            "history_requests_count": history_count,
            "history_requests_percentage": actual_history_pct,
            "target_history_percentage": "30%",
            "transfer_requests_count": transfer_count,
            "transfer_requests_percentage": actual_transfer_pct,
            "target_transfer_percentage": "10%",
        },
        "latencies_ms": {
            "p50": total_p50,
            "p90": total_p90,
            "p95": total_p95,
            "p99": total_p99,
            "read_p95": read_p95,
            "transfer_p95": transfer_p95,
        },
        "sla_evaluations": {
            "read_p95_under_200ms": {
                "threshold_ms": 200.0,
                "actual_ms": read_p95,
                "passed": read_sla_passed,
            },
            "transfer_p95_under_500ms": {
                "threshold_ms": 500.0,
                "actual_ms": transfer_p95,
                "passed": transfer_sla_passed,
            },
            "unexpected_error_rate_under_1_percent": {
                "threshold_percentage": 1.0,
                "actual_percentage": unexpected_error_rate,
                "passed": error_rate_passed,
            },
        },
        "passed": overall_passed,
    }

    return report


def run_full_benchmark(
    target_users: int = 30,
    spawn_rate: int = 5,
    duration_seconds: int = 60,
    port: int = 8009,
) -> Dict[str, Any]:
    """Execute end-to-end benchmark on isolated synthetic environment and export results."""
    # 1. Create dedicated disposable database in temporary directory
    temp_dir = tempfile.mkdtemp(prefix="shiftbank_load_")
    db_file = os.path.join(temp_dir, "load_synthetic.db")

    logger.info(f"Isolated benchmark database initialized at: {db_file}")
    seed_synthetic_load_database(db_file)

    # 2. Configure environment variables for the backend server process
    server_env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_file}",
        "ENCRYPTION_KEY": "01234567890123456789012345678901",
        "AUDIT_SECRET_KEY": "load_test_audit_secret_key_32b!",
        "ADMIN_SECRET_KEY": "load_test_admin_secret_key_2026",
        "RUN_SCHEDULER": "false",  # Disable background scheduler during load test to eliminate noise
        "TESTING": "false",
    }

    server_process = None
    try:
        # 3. Start isolated FastAPI backend server on target port
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ]
        logger.info(f"Starting backend server: {' '.join(cmd)}")
        server_process = subprocess.Popen(cmd, env=server_env)

        # 4. Wait for server readiness
        healthy = wait_for_server_healthy("127.0.0.1", port, timeout_seconds=15)
        if not healthy:
            raise RuntimeError(f"Backend server failed to start or report healthy on port {port}")
        logger.info(f"Backend server healthy on http://127.0.0.1:{port}")

        # 5. Run Locust benchmark
        host_url = f"http://127.0.0.1:{port}"
        report = execute_locust_benchmark(
            host_url=host_url,
            target_users=target_users,
            spawn_rate=spawn_rate,
            steady_state_seconds=duration_seconds,
        )

        # 6. Export report to JSON
        output_dir = os.path.dirname(os.path.abspath(__file__))
        report_path = os.path.join(output_dir, "load_benchmark_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Benchmark results exported to: {report_path}")
        return report

    finally:
        # 7. Clean up server and disposable database
        if server_process:
            logger.info("Terminating load test backend server process...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()

        try:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(temp_dir)
        except Exception as e:
            logger.warning(f"Cleanup of temporary files: {e}")


if __name__ == "__main__":
    result = run_full_benchmark()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)
