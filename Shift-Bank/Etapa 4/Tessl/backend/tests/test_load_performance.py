import os
import json
import pytest

REPORT_PATH = os.path.join(
    os.path.dirname(__file__), "load", "load_benchmark_report.json"
)


def test_load_benchmark_report_sla_compliance():
    """Asserts that the Locust load benchmark report satisfies all specified SLAs and criteria."""
    if not os.path.exists(REPORT_PATH):
        pytest.skip(
            "Benchmark report not found. Run python backend/tests/load/run_load_test.py first."
        )

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    # 1. Workload profile
    assert report["total_users"] == 30, "Benchmark must simulate exactly 30 concurrent users"
    assert report["duration_seconds"] >= 60.0, "Measurement must sustain 60s steady state"

    # 2. Traffic distribution mix
    traffic = report["traffic_distribution"]
    assert traffic["read_requests_count"] > 0
    assert traffic["transfer_requests_count"] > 0
    # Allow reasonable statistical variance around 90/10 ratio
    assert 75.0 <= traffic["read_requests_percentage"] <= 98.0
    assert 2.0 <= traffic["transfer_requests_percentage"] <= 25.0

    # 3. Latency SLAs
    read_p95 = report["latencies_ms"]["read_p95"]
    transfer_p95 = report["latencies_ms"]["transfer_p95"]
    assert (
        read_p95 < 200.0
    ), f"Read p95 latency must be strictly under 200ms, actual: {read_p95}ms"
    assert (
        transfer_p95 < 500.0
    ), f"Transfer p95 latency must be strictly under 500ms, actual: {transfer_p95}ms"

    # 4. Reliability SLA (Unexpected error rate < 1.0%)
    unexpected_error_rate = report["unexpected_error_rate_percentage"]
    assert (
        unexpected_error_rate < 1.0
    ), f"Unexpected error rate must be < 1.0%, actual: {unexpected_error_rate}%"

    # 5. Overall status
    assert report["passed"] is True, "Overall benchmark SLA evaluation must pass"
