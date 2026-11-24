# Shift Bank E3 OpenSpec — Hito 7 Initial SonarQube Baseline

**Status: NOT EXECUTED — credential required.** This is preparation and coverage evidence, not a SonarQube measurement. No static-analysis findings or quality rating are claimed.

## Server, scanner and history

The local server returned version 26.9.0.129388. The frozen scanner image exists as sdd-sonar-scanner:frozen (image sha256:a3f4215076706c95a17a68c19322ee916e40a3acd081a8c1a1e839e0194afa57); docker run --rm sdd-sonar-scanner:frozen --version reported SonarScanner CLI 8.1.0.6389. A container using host.docker.internal:host-gateway reached the server. Anonymous project-history API access returned HTTP 401, so no historical analysis metadata could be retrieved without authentication. No scan was started and no pre-existing analysis was overwritten.

The named variable SONAR_TOKEN_OPENSPEC3 was absent from process, user and machine environment scopes. No matching Windows credential was found. A hidden PowerShell secure-string prompt was opened, but no credential was supplied; the prompt was interrupted without starting the scanner. The token value was never entered into chat, printed, logged, or saved. Authenticated analysis-history, issues and hotspot APIs remain unqueried.

## Frozen analysis scope

The reusable properties are in E3_OPENSPEC_SONAR_PROPERTIES_INICIAL.properties and the JSON configuration is in E3_OPENSPEC_SONAR_CONFIG_INICIAL.json. They select five backend production modules and all frontend/src assets; backend/tests and frontend/tests are classified as tests. Venvs, node_modules, build/cache/scanner output, SQLite files and sidecars, secrets/certificates, deployment, Locust harness and experiment logs are excluded. Fourteen selected source files and their SHA-256 hashes are recorded in E3_OPENSPEC_SONAR_SOURCE_HASHES_INICIALES.json. Python 3.13, Node 24.19.0, coverage paths, the frozen scanner image/digest, scanner/server versions and exclusions are recorded. Reuse this exact configuration and scope for the later final analysis. No separate metric guide was present in the OpenSpec Stage 3 evidence directories; the Hito 7/Hito 8 sequence is recorded in the OpenSpec bitacora and the Hallazgos formula follows the approved request.

## Genuine test coverage prepared

Backend command: python -m coverage run --data-file=../sonarqube/reports/.coverage-backend --source=main,banking,database,encryption,audit -m unittest discover -s tests -v; 53 tests passed. Coverage.py 7.17.3 measured 883/989 executable lines, 89.28%, across audit.py (89%), banking.py (93%), database.py (92%), encryption.py (89%) and main.py (77%). Raw and scanner-normalized Cobertura XML are preserved.

Frontend command: npm.cmd exec --yes --package=c8 -- c8 --reporter=lcovonly --reports-dir=../sonarqube/reports/frontend-coverage --include=src/api.mjs --include=src/validation.mjs --include=src/refreshPolling.mjs -- node --test tests/*.test.mjs; 8 tests passed using isolated c8 12.0.0, with no package manifest/lockfile edits. LCOV records 100% line coverage for the three imported .mjs modules. The existing tests do not import App.tsx or main.tsx, so React UI coverage is unmeasured and is not claimed. Node 24 built-in coverage output is also preserved.

Coverage was generated, but it has not yet been imported by SonarQube. No coverage warning or scanner result exists.

## Findings, limitations and next step

Issue lists, security hotspots, metrics, Quality Gate and Compute Engine status are NOT EXECUTED; the accompanying JSON files explicitly encode that state and contain no fabricated zero counts. No issue-specific correction plan is proposed from unseen findings. After SONAR_TOKEN_OPENSPEC3 is available in the local Codex process environment, run sonarqube/run_initial_baseline.py. It checks analysis history before scanning, passes the value through the SONAR_TOKEN environment variable to Docker, polls Compute Engine, and exports paginated API results without logging the token. If issue or hotspot APIs remain unauthorized after Bearer and Basic attempts, preserve the exact limitation and do not infer findings.
