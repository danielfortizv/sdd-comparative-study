# Focused SonarQube corrections executed

## Baseline verification

Before source edits, all 14 initial production source hashes matched `E3_OPENSPEC_SONAR_CONFIG_INICIAL.json`. The extracted CE task ID and project key matched the original baseline; status was SUCCESS and analysis ID was `5242ca1c-0d7b-4acc-961a-e538fb54f1f1`. Original extraction files were not edited. Their SHA-256 values are recorded separately.

## Changes

- `frontend/src/App.tsx`: explicitly set `type="submit"` on intended form submissions and `type="button"` on navigation, dismissal, edit/delete, schedule-control, and cancellation actions. This preserves submit behavior while preventing accidental form submission by controls.
- `frontend/tests/button-types.test.mjs`: added TypeScript AST regression to require every JSX button to declare `button` or `submit`.
- `backend/banking.py`: centralized repeated insufficient-funds/MFA/beneficiary messages and account-balance SQL; parameterized the existing insufficient-funds transaction failure reason with the same text. Removed unused `rec`/`bid` arguments from `_accept_ach` and call sites. This does not change authorization, validation, balance calculations, audit transactions, or ACH lifecycle.
- `backend/database.py`: centralized the two existing Spanish seed account labels without changing persisted values.
- `backend/audit.py`, `backend/encryption.py`: removed redundant exception subclasses already covered by `ValueError`; decoding/integrity failures continue to fail closed.
- `backend/main.py`: documented existing audit verification 401 and recurring-action 404 response codes in OpenAPI.
- `backend/tests/test_api.py`: added regression for those generated OpenAPI responses.

Baseline issues addressed in code: all five S9011 Bugs; seven S1192 findings; two S1172 findings; three S5713 findings; and two S8415 findings (19 baseline issue keys). This is a source-level correction count, not a post-scan result. The final scan has not run, so no issue reduction or quality improvement is claimed.

## Initial execution failures and corrections

- First focused backend invocation used `python -m unittest test_api test_banking test_encryption test_audit -v` from `backend/`; discovery could not import those bare module names. Corrected to `python -m unittest discover -s tests -p test_api.py -v` and the analogous banking discovery command; both passed.
- Initial frontend coverage invocation could not reach `registry.npmjs.org` in the sandbox (`EACCES`). Re-ran the same approved c8 command with network escalation; it completed, and no dependency manifest was changed.
- The final exception cleanup was followed by another full backend coverage run; all 54 tests passed.

No application specification, OpenSpec task checkbox, deployment file, test expectation, database, Sonar configuration, or scanner scope was changed.
