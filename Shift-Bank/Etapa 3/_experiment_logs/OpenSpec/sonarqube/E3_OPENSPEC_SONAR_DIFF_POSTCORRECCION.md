# Post-correction source inventory and change summary

The analysis source scope remains exactly the baseline scope: 5 backend modules and the same 9 files under `frontend/src` (14 files total). `sonarqube/sonar-project.properties` is unchanged; its SHA-256 remains `c6d52175bc0623c3c5b64fad0dbe705fb9f8e3cbaf3862466bf8e47277f87ee1`. The frozen initial source-hash inventory remains intact. The separate current source inventory is `E3_OPENSPEC_SONAR_SOURCE_HASHES_POSTCORRECTION.json`.

Production files changed:

- `backend/audit.py` — redundant caught exception class removal.
- `backend/banking.py` — named shared literals, shared balance SQL, `_accept_ach` signature cleanup.
- `backend/database.py` — named seed account labels.
- `backend/encryption.py` — redundant caught exception classes removed.
- `backend/main.py` — OpenAPI 401/404 response documentation.
- `frontend/src/App.tsx` — explicit button types.

Tests changed:

- `backend/tests/test_api.py` — generated OpenAPI response test.
- `frontend/tests/button-types.test.mjs` — explicit JSX button type test.

Coverage reports/test logs are under `sonarqube/reports/`. The initial scanner properties, source exclusions, language versions, configured test directories, coverage paths, Sonar Quality Gate, and source scope were not modified. Current source hashes are not SonarQube findings or a claim of final metric change.
