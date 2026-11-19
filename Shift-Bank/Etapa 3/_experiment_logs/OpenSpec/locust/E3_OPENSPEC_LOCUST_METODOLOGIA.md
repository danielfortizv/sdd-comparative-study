# E3 OpenSpec — Locust benchmark methodology

## Change and purpose

OpenSpec change: `stage3-banking-security-load-deployment` (schema `spec-driven`, OpenSpec 1.11.0). This method implements tasks 3.1–3.4 only. It exercises the real Stage 3 FastAPI application through Locust over local HTTPS and records request-level observations. No Docker deployment, SonarQube, application business-rule changes, or performance tuning was performed.

## Files in the implementation

- `backend/loadtest/locustfile.py`: real HTTP balance and history reads plus internal transfer POSTs. Task weights are 6:3:1; request-event samples, not task weights, determine the reported distribution.
- `backend/loadtest/run_benchmark.py`: synthetic fixture, run-local keys and TLS certificate, application startup/readiness, Locust scheduling, timing, metric collection, final database/audit checks, evidence export, and owned-process cleanup.
- `backend/loadtest/metrics.py`: isolated database guard, nearest-rank percentile, observed distribution, steady-state sample boundary, and strict threshold comparison.
- `backend/loadtest/__init__.py` and `backend/requirements-loadtest.txt`: load-test package and pinned Locust runner dependency.
- `backend/tests/test_loadtest_metrics.py`: unit checks for target isolation, workload weights, actual-distribution calculation, time-window boundary, and strict threshold equality.

## Isolation and security

The application reads its SQLite location from `SHIFT_BANK_DB`; it does not use `DATABASE_URL`. The runner creates a unique `shift-bank-locust-*` temporary directory, calls the isolation guard before use, sets `SHIFT_BANK_DB` to a new SQLite filename inside that directory, and only then imports the database module or starts Uvicorn. The known application default `backend/bank.db` is explicitly excluded. It initializes and checks the deterministic fixture before starting load.

Each run creates separate random 32-byte encryption and audit keys and a separate high-entropy audit-verification token in memory. They are passed only to the benchmark server process and are not emitted in evidence. A one-day self-signed certificate and its private key are stored only in the temporary directory. Locust and the readiness client verify TLS using that specific generated certificate as a trust anchor; certificate verification is not disabled. The private key, secrets, and synthetic SQLite runtime files are removed after the child application exits. Only the synthetic database SHA-256 is retained as a pre-disposal integrity reference.

The application runs as one local Uvicorn process on loopback. Readiness requires both `/api/accounts` and separately authorized `/api/admin/audit/verify` to succeed over HTTPS, with a valid initial audit chain. No production secrets, persistent volumes, historical databases, or real banking data are used.

## Synthetic fixture and business controls

The fixture is freshly initialized by the existing application code: checking COP 5,000,000.00, savings COP 15,000,000.00, inherited per-transfer limit COP 5,000,000.00, inherited daily limit COP 10,000,000.00, two seeded history entries, and one audit genesis entry. The benchmark submits actual COP 1.00 transfers from `acc_checking` to `acc_savings`. That amount is positive, below the inherited MFA threshold, and far below both fixture limits; all transfer validations, SQLite writes, and audit events remain enabled. Rejections are counted and classified separately. A transfer is considered successful only after the real API returns a completed transaction identifier.

## Workload and timing

The runner configures 30 Locust users at a spawn rate of 5 users per second. Task weights are balance reads 6, history reads 3, and actual internal transfers 1. Each user waits a random 0.1–0.3 seconds between tasks. This produces the target workload mix without assuming weights equal observed requests.

Ramp-up timing starts immediately before `LocalRunner.start(30, 5)`. The runner polls Locust's live `user_count` and state every 50 ms and records the first observed state with 30 users and `running`. The full 60-second steady clock begins after that verification. It samples active users during steady state and aborts if the count/state changes. Requests are split by their actual start timestamp into ramp-up and the half-open steady interval `[all_users_spawned_at, steady_state_ended_at)`. Performance acceptance is evaluated on that steady-state sample; ramp and all-phase metrics are retained separately.

Percentiles use nearest-rank over the original event response times. Read acceptance checks balance, history, and combined read p95 strictly below 200 ms. Transfer p95 must be strictly below 500 ms. Unexpected errors divided by all steady-state requests must be strictly below 1%. Expected business rejections are counted separately and remain in the request denominator. Equality fails; unit tests cover equality.

## Run command and evidence

From the project root:

```powershell
python backend\loadtest\run_benchmark.py --run-id RUN_01 --steady-seconds 60
```

The runner refuses to use a different run ID or steady-state duration. It refuses to overwrite the first-run JSON. It writes a machine-readable report, original request event CSV, Locust stats/failures CSV, active-user timeline, timestamped runner output, and backend server output in this evidence directory. The report includes environment versions, fixture assertions, run parameters, p50/p95/p99, endpoint counts, actual request mix, throughput, expected and unexpected errors, acceptance, and final transaction/balance/audit integrity.

The recorded run used Windows 11 build 10.0.26300, Python 3.13.2, Locust 2.47.0, FastAPI 0.142.2, Uvicorn 0.54.0, cryptography 50.0.2, SQLite 3.45.3, and Python's TLS-linked OpenSSL 3.0.15. The system OpenSSL CLI was not used. CPU and memory utilization were not measured because no reliable process sampler was configured; none is inferred.
