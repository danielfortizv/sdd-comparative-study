---
name: Load Testing and Performance Verification
description: Performance benchmarking using Locust simulating 30 concurrent users for 60 seconds with 60/30/10 traffic distribution on freshly initialized synthetic database and strict latency SLAs
targets:
  - ../backend/tests/load/locustfile.py
  - ../backend/tests/load/run_load_test.py
---

# Load Testing and Performance Verification

Defines performance benchmarks and automated load verification using Locust to simulate realistic banking workloads, ensure SLA latency thresholds under concurrency, and validate system stability without violating banking validation rules.

## Data Contract

```python
class LoadBenchmarkResult(BaseModel):
    total_users: int                            # Target: 30 concurrent users
    duration_seconds: int                       # Target: 60 seconds sustained
    total_requests: int
    successful_requests: int
    business_rejections_count: int              # Expected 4xx business rule enforcements (reported separately)
    unexpected_failures_count: int              # HTTP 5xx, timeouts, uncaught errors
    unexpected_error_rate_percentage: float     # Target: < 1.0% (applies strictly to unexpected failures)
    read_p95_ms: float                          # Target: < 200 ms
    transfer_p95_ms: float                      # Target: < 500 ms
    passed: bool
```

## Workload Profile & Concurrency

- Load testing runs headlessly using Locust simulating `30` concurrent users sustained for `60` seconds.
  `[@test] ../backend/tests/test_load_performance.py`
- Users spawn at a rate of `5` users per second until 30 active users are reached.
  `[@test] ../backend/tests/test_load_performance.py`
- User task executions introduce realistic user think time (between 0.5 and 1.5 seconds) between consecutive actions.
  `[@test] ../backend/tests/test_load_performance.py`

## Traffic Distribution Ratios

- Task weighting strictly matches the defined production traffic distribution:
  - 60% Balance & Account Queries: `GET /api/accounts` and `GET /api/accounts/{id}` (`@task(60)`).
    `[@test] ../backend/tests/test_load_performance.py`
  - 30% Transaction History Queries: `GET /api/transactions` and `GET /api/transactions?account_id={id}` (`@task(30)`).
    `[@test] ../backend/tests/test_load_performance.py`
  - 10% Internal Transfers: `POST /api/transfers` (`@task(10)`).
    `[@test] ../backend/tests/test_load_performance.py`

## Latency and Reliability SLAs

- Read Latency SLA: 95th percentile ($p95$) response time for balance and transaction queries must be strictly less than 200 milliseconds ($p95 < 200\text{ ms}$).
  `[@test] ../backend/tests/test_load_performance.py`
- Transfer Latency SLA: 95th percentile ($p95$) response time for internal transfer operations (including atomic debit, credit, balance updates, transaction creation, and audit logging) must be strictly less than 500 milliseconds ($p95 < 500\text{ ms}$).
  `[@test] ../backend/tests/test_load_performance.py`
- Error Rate Threshold: Unexpected failures (HTTP 5xx server errors, unhandled exceptions, database deadlocks, or connection timeouts) must account for strictly less than 1.0% ($< 1\%$) of total requests.
  `[@test] ../backend/tests/test_load_performance.py`

## Fresh Synthetic Database & Benchmark Isolation

- Fresh Synthetic Database per Benchmark: Each benchmark run executes against a freshly initialized, dedicated synthetic SQLite database instance (e.g. `shift_bank_load_test.db`). It must never operate on the persistent application database or reuse stale data from previous test runs.
  `[@test] ../backend/tests/test_load_performance.py`
- Preservation of Production Limits and MFA Rules:
  - Production transfer limits ($5,000.00 per-transaction limit, $10,000.00 daily cumulative limit) and mock MFA rules ($1,000.00 threshold) are preserved intact. Modifying or inflating production limits via `PUT /api/limits` merely to achieve passing results is strictly forbidden.
  `[@test] ../backend/tests/test_load_performance.py`
- Initial Seed Balances: Synthetic accounts are seeded with adequate funds (e.g., `$50,000.00` Checking and `$50,000.00` Savings) to prevent artificial account balance depletion during sustained concurrency.
  `[@test] ../backend/tests/test_load_performance.py`
- Workload Calibration:
  - Transfers use micro-transfers of `$1.00` alternating between Checking and Savings. An estimated 150–250 transfers during the 60-second test consume ~$150–$250 in cumulative transfer volume, naturally operating within the unaltered $10,000.00 daily limit.
  - Transfer amount `$1.00` strictly satisfies non-MFA boundary rules ($\le \$1,000.00$) to avoid triggering interactive PIN prompts.
  `[@test] ../backend/tests/test_load_performance.py`
- Strict Adherence to Banking Validations: All transfers execute the full business logic pipeline: balance checks, limit enforcement, debit/credit ledger writes, and cryptographic audit log insertion.
  `[@test] ../backend/tests/test_load_performance.py`

## Error Classification & Performance Reporting

- Separation of Business Rejections vs. Unexpected Failures:
  - Expected Business Rejections: 4xx responses resulting from legitimate banking validation rules (e.g., daily limit breach, insufficient funds, or MFA requirements) are tracked and reported separately as verified business logic enforcements.
  - Unexpected Failures: 5xx server errors, unhandled exceptions, database lock timeouts, or connection drops count toward the unexpected failure rate.
  - The $< 1.0\%$ error rate SLA applies strictly to Unexpected Failures.
  `[@test] ../backend/tests/test_load_performance.py`
- The benchmark runner writes structured metrics summary output (JSON or CSV) upon test completion containing request counts, business rejections, unexpected failures, error rate percentage, and latency percentiles ($p50$, $p90$, $p95$, $p99$).
  `[@test] ../backend/tests/test_load_performance.py`
- Automated test assertions evaluate the benchmark summary and fail if any SLA metric ($p95$ read, $p95$ transfer, unexpected error rate) exceeds its threshold.
  `[@test] ../backend/tests/test_load_performance.py`
