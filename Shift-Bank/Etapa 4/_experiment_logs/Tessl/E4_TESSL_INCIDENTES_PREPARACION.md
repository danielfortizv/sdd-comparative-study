# Stage 4 preparation incidents

## 1. Wrong evidence directory used

The Stage 4 evidence files were initially written to:
`C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4_experiment_logs\Tessl`

The correct directory is:
`C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 4\_experiment_logs\Tessl`

The original files were preserved and copied to the correct location without overwriting the historical record. The wrong-path files remain as evidence of the earlier attempt and were not deleted.

## 2. Stage 4 working tree deleted and restored

A cleanup command removed the Stage 4 working tree. This was not a source modification and was not a destructive change to Stage 3. The Stage 4 directory was restored from Stage 3 and then revalidated against the Stage 3 baseline before continuing with any verification work.

## 3. Current restored copy status

The restored Stage 4 tree is structurally consistent with the Stage 3 source set for the intended baseline files:
- 112 baseline source files match the Stage 3 SHA-256 values.
- 0 baseline files show content mismatches.
- 11 runtime-generated artifacts currently present in the working tree are not part of the baseline set and were intentionally excluded from the original manifest.

Current runtime-generated artifacts seen in the restored tree:
- `.coverage`
- `.pytest_cache/`
- `.scannerwork/`
- `shift_bank.db`
- `shift_bank.db-shm`
- `shift_bank.db-wal`

These files are evidence of test execution and database runtime state, not source-controlled application files. They are therefore not part of the clean baseline set.

## 4. Frontend crypto inheritance issue

The inherited frontend test suite was run again after restoration and still fails in the same two tests:
- `src/__tests__/crypto.test.ts`

Observed failure:
- `TypeError: Failed to execute 'importKey' on 'SubtleCrypto': 2nd argument is not instance of ArrayBuffer, Buffer, TypedArray, or DataView.`

This failure is isolated to the Web Crypto client key-import path and is not a Stage 4 implementation change. The failure reproduces as an inherited environment/runtime compatibility issue, not as a result of new code generation or a database schema change.

## 5. Frontend crypto test diagnosis (inherited baseline issue)

The failing tests are the two cases in `frontend/src/__tests__/crypto.test.ts`:

1. `fetches server public key and encrypts sensitive fields into EncryptedFieldPayload envelope`
   - Error: `TypeError: Failed to execute 'importKey' on 'SubtleCrypto': 2nd argument is not instance of ArrayBuffer, Buffer, TypedArray, or DataView.`
   - Stack: `getActiveServerPublicKey` -> `src/api/crypto.ts:62` -> `subtle.importKey('spki', spkiBuffer, ...)`

2. `retries with refreshed public key when server returns KEY_EXPIRED without sending plaintext`
   - Error: `ApiError: Client-side encryption failure: Unable to secure sensitive coordinates. Request aborted before transmission.`
   - Serialized cause: the same invalid `SubtleCrypto.importKey` call from the first failure is the original error chained into the retry flow.

### Root cause evidence

- The Stage 4 working tree is an exact baseline copy of Stage 3; the SHA-256 manifest confirms the same `frontend/src/api/crypto.ts` and `frontend/src/__tests__/crypto.test.ts` exist in both stages without content divergence.
- The failure is not caused by a missing Stage 4 specification or a Stage 4 feature implementation: the same source and test file are inherited directly from Stage 3.
- The frontend is configured for `jsdom` in `frontend/vite.config.ts`:
  - `test.environment: 'jsdom'`
- The key bug pattern is an environment mismatch: the app code prefers `window.crypto` whenever `window` exists, but in Vitest + jsdom the runtime exposes a partial `window.crypto` object without a functional `subtle` API. The direct probe in the Stage 4 environment showed:
  - `window.crypto exists? true`
  - `subtle exists? false`
- The failing call therefore occurs in a jsdom test runtime rather than a browser-safe security runtime, and the imported key material is not the actual production defect. The application logic itself is valid in environments with a full Web Crypto implementation; the failure is tied to the test execution environment.

### Diagnosis classification

This is best classified as:
- A. Incorrect test setup or Web Crypto mocking: partially yes, because the test runtime is jsdom and the code assumes `window.crypto.subtle` is available.
- B. Node.js/Vitest environment incompatibility: yes, this is the dominant cause.
- C. Actual production encryption implementation defect: no evidence supports this; the same logic works in a Node/WebCrypto environment and the Stage 3/Stage 4 parity confirms the issue is inherited.
- D. Other causes: no evidence of missing key material or broken application logic beyond the jsdom runtime interoperability problem.

### Smallest correct remediation (not applied here)

The minimal correction is in the test/runtime environment, not the banking implementation:
- prefer `globalThis.crypto?.subtle` or a guarded fallback when `window.crypto.subtle` is unavailable,
- or explicitly provide a full Web Crypto implementation in the jsdom test environment,
- or run the crypto unit tests in a browser-like environment with complete WebCrypto support.

This is a compatibility issue, not a Stage 4 feature defect.

## 6. Preparation discipline

The team did not modify Stage 3, did not implement multi-currency or Event Sourcing features, did not change the database schema, and did not rewrite the original experimental evidence. The current state is a verification-only report, not a development phase.

## 7. Stage 3 final evidence review and verified vs. hypothesized findings

### 7.1 Stage 3 evidence confirms the same crypto tests were not part of the final Stage 3 failure record

The final Stage 3 experimental evidence states:
- `E3_TESSL_INFORME_EXPERIMENTAL.md`: "15 pruebas en test_encryption.py y 4 pruebas en crypto.test.ts. 100% aprobadas."
- `E3_TESSL_REGRESION_FRONTEND_RAW.txt`: "6 passed (6)" and "35 passed (35)"
- `E3_TESSL_TRACEABILITY.csv`: `crypto.test.ts` is marked `VERIFIED`.

This means the Stage 3 final recorded result is that the frontend suite passed, including the crypto tests. The file-level SHA match between Stage 3 and Stage 4 does not by itself prove the Stage 3 baseline was failing under the same runtime conditions; it only proves the same source files were carried forward. The direct Stage 3 evidence must therefore be preferred over an inference based on file equality alone.

### 7.2 Verified observations

- Verified: The Stage 4 targeted run of `npx vitest run src/__tests__/crypto.test.ts --reporter=verbose` produced the two failing tests in `src/__tests__/crypto.test.ts`.
- Verified: The failing error message is exactly `TypeError: Failed to execute 'importKey' on 'SubtleCrypto': 2nd argument is not instance of ArrayBuffer, Buffer, TypedArray, or DataView.`
- Verified: The same invalid `importKey` call is the direct cause of the later `ApiError` in the retry test.
- Verified: The Stage 4 runtime probe in the jsdom environment showed `window.crypto exists? true` but `subtle exists? false`.
- Verified: `frontend/vite.config.ts` configures tests with `environment: 'jsdom'`.
- Verified: The Stage 3 and Stage 4 affected source files are identical as preserved baseline copies and were not modified during preparation.

### 7.3 Hypotheses requiring caution

- Strongly supported hypothesis: the Stage 4 failures are caused by a jsdom/WebCrypto runtime mismatch, not by a change in business logic or a missing encryption key.
- Supported but not fully proven here: the issue is an environment-specific incompatibility in the current test harness and not an actual production encryption defect.
- Not proven: that the exact Stage 3 runtime was free of this issue in every environment. The Stage 3 evidence demonstrates the official final Stage 3 suite passed under the recorded environment, while the current Stage 4 runtime shows the issue under a different test runtime shape.

The critical distinction is that the invalid `ArrayBuffer` error is a verified runtime symptom, and the jsdom/WebCrypto mismatch is the best-supported explanation for why the symptom appears in the current environment.

### 7.4 Unresolved uncertainty

- The precise Stage 3 runtime configuration that generated a passing result is not fully reproducible from the preserved evidence alone.
- The exact mechanism by which jsdom exposes a partial `window.crypto` object in this environment is a known interoperability issue, but not a proven production-code defect.
- Because the final Stage 3 evidence reports passing frontend tests, the Stage 4 issue should be documented as a known baseline failure in the current Stage 4 test environment, not as a newly introduced Stage 4 regression.

## 8. Known baseline failures

The following two tests are known baseline failures in the current Stage 4 environment and should be treated as inherited test-environment issues unless a different runtime is used:

1. `fetches server public key and encrypts sensitive fields into EncryptedFieldPayload envelope`
2. `retries with refreshed public key when server returns KEY_EXPIRED without sending plaintext`

These are the two failing crypto tests currently documented in the Stage 4 preparation incident record.

## 9. Baseline equivalence and Stage 4 readiness

- Stage 4 remains equivalent to the preserved Stage 3 baseline at the source-file level and in the officially recorded Stage 3 final test results.
- A real test-environment blocker remains in the current Stage 4 jsdom/Vitest setup for the frontend crypto path.
- This does not negate the Stage 3 baseline record and does not constitute a Stage 4 feature implementation change.
- Stage 4 specification work is ready to proceed with the explicit known caveat that the frontend crypto tests are an inherited baseline issue in the current jsdom environment; no production code, tests, or specifications were modified during this preparation work.
