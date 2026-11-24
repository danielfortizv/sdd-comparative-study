# Iteration 03 security review — metadata only

## Scope and finding
Inspected filesystem metadata, Git tracking/ignore status, deployment references, and evidence text using redacted checks. Neither `.env.local` file was opened for display; no values or hashes of values are reproduced here.

| Location | Exists | Length | UTC modified | Filesystem/Git status |
|---|---:|---:|---|---|
| `Etapa 3/OpenSpec/deployment/.env.local` | Yes | 415 bytes | 2026-11-17 02:11:49Z | Regular file; ignored by `Etapa 3/OpenSpec/deployment/.gitignore`; not tracked (`git ls-files` no match; status `!!`). |
| `Etapa 4/OpenSpec/deployment/.env.local` | Yes | 415 bytes | 2026-11-17 02:11:49Z | Regular file; ignored by `Etapa 4/OpenSpec/deployment/.gitignore`; not tracked (`git ls-files` no match; status `!!`). |

Both have matching metadata and the earlier historical manifest confirms source/destination byte identity. This is a sensitive-file inclusion in the frozen copy even though Git ignores the files. The E4 source manifest contains an entry and content digest for the file; the existing manifest is historical evidence and must not be edited or redistributed without considering that metadata exposure. No secret value or file digest is included in this report.

The repository Git root resolves to the shared comparative-study parent. Scoped Git checks show only the two ignored files; no tracking was found.

## Runtime/configuration dependence
`deployment/compose.yaml` explicitly names `./.env.local` as the backend `env_file`; Compose deployment therefore expects a file at that path in the current configuration. `deployment/generate_local_config.py` creates it and refuses to overwrite an existing one. `deployment/README.md` describes generated local demonstration credentials and says they should stay outside source control. A safe `deployment/.env.example` contains variable names with empty values.

Backend modules consume environment variables directly (`database.py`, `encryption.py`, `audit.py`, `main.py`); encryption also supports a protected key file. The existing backend tests explicitly set test-only environment values in their fixtures. The previously observed frontend test/build results do not depend on `.env.local`. Absence should not affect those frontend checks or the backend test fixtures based on inspected source; this is a static assessment, not a rerun. Removing the file without changing deployment invocation/configuration would break the current Compose env-file expectation. No deployment was run.

Filename-only scan under `Etapa 4` found one `.env.local` (the deployment copy) and no other `.env*`, `.pem`, `.key`, `.p12`, `.pfx`, secret, or credential-named files. This does not detect renamed copies or values embedded in arbitrary files.

## Redacted evidence scan
Scanned 24 regular evidence files using a local text check for non-empty assignments whose variable names indicate encryption keys, audit keys, admin tokens, secrets, or passwords. Reported **zero matching assignments**. The scanner emitted only file names/counts and did not read `.env.local`; it is a limited pattern screen and cannot establish absence of every encoded, split, renamed, or otherwise formatted secret. Existing historical `source-manifest-sha256.json` includes the file path and digest as part of the frozen manifest. The manifest was left unchanged; its digest is not repeated here.

## Safe remediation proposal — approval required
1. Preserve Stage 3 and all original H0 raw evidence and reports exactly as they are. Do not modify the Stage 3 source.
2. Keep the original manifest untouched and label the copied baseline as containing an ignored sensitive runtime file. Restrict access to the existing evidence bundle because its historical manifest records that file's digest.
3. Before further distribution or implementation, obtain explicit researcher/operator approval for isolating the E4 copy. The approved operator should move only the E4 file into an access-controlled quarantine outside source/build/evidence trees, or securely remove only that E4 copy if quarantine is not required. Record authorization, actor, time, destination/disposition, and verification without recording contents. Do not alter E3.
4. For future local runtime, inject configuration from a protected external secret store/environment or an access-controlled file outside the source tree. The current Compose `env_file` path must be addressed in a separately authorized deployment/configuration change or a protected Compose override; do not silently edit it as part of this assessment. Keep only the blank `.env.example` template in the sanitized source copy.
5. Rotate credentials only if the researcher/operator confirms they were reused outside isolated synthetic demonstration, deployed with valuable data, accessible to unauthorized parties, or copied to an uncontrolled location. If rotation is required, follow `backend/SECURITY.md`: retain old encryption-key versions until stored ciphertext has been deliberately re-encrypted and verified; do not invalidate the HMAC chain by replacing its key without an approved chain-verification/transition plan; rotate the separate admin token under controlled access. No rotation was performed or authorized here.
6. After approved isolation, verify metadata/name scans show no `.env.local` or renamed runtime secret in the sanitized E4 source/build/evidence trees; verify Compose receives external configuration without printing it; verify `.env.example` remains blank; check Git tracking and ignored status; run an authorized redacted evidence scan. Do not rerun baseline checks unless a documented change makes their prior results stale. Any sanitized build copy needs a distinct identity and verification record.
7. Preserve the original manifest as historical H0 evidence. If sanitization is authorized, produce a separately named/versioned sanitized manifest (for example `source-manifest-sanitized-I03.json`) describing the sanitized tree, with a documented exclusion entry and its own hash/size totals. Never rewrite the original manifest or claim the sanitized tree is the original H0 copy.

No file was changed, moved, deleted, hashed anew, or read for display in this iteration. Credential use/reuse and any exposure outside this local workspace are unknown; this report cannot decide whether rotation is necessary.
