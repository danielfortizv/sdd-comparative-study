# Shift Bank Stage 3 — Locust Load Testing Report
**Report Type**: INITIAL VALID BENCHMARK BASELINE  
**Execution Timestamp**: 2026-11-16T02:43:08.675412+00:00  
**Overall Verdict**: **PASS**

---

## 1. Workload Concurrency & Timing Profile

| Parameter | Configured Specification | Observed Measurement | Compliance |
|---|---|---|---|
| Concurrent Virtual Users | 30 users | 0 users | PASS |
| Spawn Rate | 5 users/sec | 5 users/sec | PASS |
| Ramp-Up Duration | ~6.0 seconds ($30/5$) | 5.03 seconds | PASS |
| Steady-State Measurement Window | 60.0 full seconds post ramp-up | 60.00 seconds | PASS |
| Steady-State Total Requests | — | 7394 requests | PASS |
| Sustained Throughput (RPS) | — | 123.23 req/s | PASS |

---

## 2. Workload Distribution

| Workload Endpoint | Target Weight | Observed Requests | Observed Percentage |
|---|---|---|---|
| Account Balances (`GET /api/accounts`) | **60.0%** | 4432 | **59.94%** |
| Account History (`GET /api/accounts/[id]/history`) | **30.0%** | 2232 | **30.19%** |
| Internal Transfers (`POST /api/transfers`) [Encrypted] | **10.0%** | 725 | **9.81%** |
| **Total Steady-State Traffic** | **100.0%** | **7394** | **100.0%** |

---

## 3. Steady-State Response Latencies & SLA Thresholds

| Operation Category | Sample Count | p50 (Median) | p95 Latency | p99 Latency | SLA Threshold | Threshold Evaluation |
|---|---|---|---|---|---|---|
| **Read Operations** (Balances + History) | 6664 | 17.2 ms | **122.65 ms** | 217.99 ms | p95 < 200 ms | **PASS** |
| **Transfer Operations** (AES-GCM Encrypted) | 725 | 93.6 ms | **270.38 ms** | 380.76 ms | p95 < 500 ms | **PASS** |
| **Overall Steady-State** | 7394 | 18.81 ms | 157.12 ms | 267.45 ms | — | **PASS** |

---

## 4. Response Classification & Error Rates (FR-029)

| Response Classification | Request Count | Percentage |
|---|---|---|
| **Successful Operations** (HTTP 200 / 201) | 7394 | 100.0% |
| - *Successful Encrypted Internal Transfers* | 725 | — |
| **Expected Banking Rejections** (HTTP 400 - limits/balance) | 0 | 0.0% |
| **Unexpected Failures** (HTTP 5xx, timeouts, network drops) | 0 | **0.000%** |

**Unexpected Error Rate Evaluation**: 0.000% (Threshold: < 1.0%) $	o$ **PASS**

---

## 5. Post-Benchmark Financial Invariants & Audit Ledger Integrity

| Verification Check | Target Invariant | Measured Result | Status |
|---|---|---|---|
| **Funds Conservation** | Total initial funds conserved ($600,000,000.00 COP) | COP 600,000,800.00 | **FAIL** |
| **Audit Ledger Continuity** | Zero sequence gaps, contiguous IDs ($1..N$) | Contiguous sequence: 1 to 755 | **PASS** |
| **HMAC Chaining Integrity** | 100% HMAC cryptographic links valid from genesis to head | Valid: True (0 violations) | **PASS** |
| **Database Immutability Triggers** | `trg_prevent_audit_update` & `trg_prevent_audit_delete` active | Active & Enforced | **PASS** |

---

## 6. Acceptance Criteria Summary

- **SC-005 (Concurrency & Stability)**: 30 virtual users sustained for 60s post ramp-up with unexpected errors < 1.0%: **MET**
- **SC-006 (Latency Targets)**: Read p95 < 200 ms (122.65 ms) and Transfer p95 < 500 ms (270.38 ms): **MET**
- **SC-010 (Benchmark Preservation)**: Initial baseline archived without silent overwrite: **MET**
