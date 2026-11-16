# E4-SK-07 researcher review package

## Review requested

Please complete T068 by reviewing the approved Stage 4 specification and all 68 task outcomes against [`E4-SK-07-acceptance-matrix.md`](E4-SK-07-acceptance-matrix.md), the final report, and the linked raw evidence. This package was assembled by the implementation agent; it is not human sign-off or independent verification.

## Evidence requiring disposition

1. **AC-45 load profile wording:** the approved `spec.md` specifies 60% balance reads / 30% history reads / 10% encrypted transfers. The E4-SK-07 run instruction instead requested 60% balance reads / 30% internal transfers / 10% history reads. The observed run follows the current user instruction and measured 60.28% / 29.81% / 9.91%; it does not verify AC-45's approved ordering. Either authorize a specification update to align AC-45 or request a new run using the approved ordering.
2. **Performance target:** on the requested profile, 30 users were sustained for 60 seconds; read p95 was 99.42 ms and unexpected errors were 0%, but transfer p95 was 5,277.63 ms against the <500 ms target. Review the transfer contention/latency result before closure or accept a separately scoped performance remediation.
3. **Static findings:** isolated SonarQube reported Quality Gate OK, 4 bugs, 0 vulnerabilities, 93 code smells and 959 minutes technical debt. The Quality Gate result does not mean all findings were individually reviewed; issue-level disposition was not captured in this evidence set.
4. **Coverage:** Sonar reported 0% because no coverage report was imported. Automated test totals are available, but line coverage remains N/D.

## Automated outcomes

- Backend: 138 passed, 1 Starlette/httpx deprecation warning.
- Frontend: 4 files / 20 tests passed; standalone TypeScript check and production build passed.
- Deployment: isolated Docker build and all Stage 4 smoke checks passed, including HTTPS, API transaction, replay/conflict semantics, projection rebuild, HMAC audit and restart persistence. The isolated containers, images, test volume and generated secrets were removed after capture.
- Locust: requested profile executed with 30 users, 5 users/s ramp, 60 s; performance FAIL for transfer p95. No unexpected errors in the final run.
- SonarQube: E4-only isolated analysis completed; ephemeral token was revoked and disposable service/volumes were removed.

## Task state

T061–T067 are backed by implementation, execution, and saved evidence. T068 remains unchecked pending this review. No further implementation or deployment action is requested by this package.
