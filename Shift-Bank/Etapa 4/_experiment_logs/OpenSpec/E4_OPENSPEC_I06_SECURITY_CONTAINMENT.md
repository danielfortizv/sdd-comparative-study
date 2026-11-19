# Iteration 06 security containment

## Authorization and action
Researcher authorization in the Iteration 06 prompt explicitly approved moving only the E4 `deployment/.env.local` to `C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\deployment.env.local`, with restricted ACLs; Stage 3 must remain unchanged; no credential rotation; historical evidence preserved.

Preflight verified the exact E4 source was a regular non-reparse file (415 bytes), the destination did not exist, the private destination directories did not exist, and each path ancestor from `C:\` through `AppData\Local` was not a reparse point. The destination path is under the current user's `LOCALAPPDATA`. The E3 source was verified separately and was outside the move operation.

The destination directories were created with protected ACLs for the current Windows user, SYSTEM, and Builtin Administrators. Only after checking the directory ACLs was the E4 file moved (not copied). The file ACL was then protected and verified. Metadata-only post-check found:

| Check | Result |
|---|---|
| E4 original path `Etapa 4/OpenSpec/deployment/.env.local` | Absent |
| Approved external destination | Present, regular file, 415 bytes, not a reparse point |
| Base directory, secrets directory, destination file owner | Current Windows user |
| ACL inheritance | Disabled/protected on all three objects |
| Explicit access rules | Exactly current user, SYSTEM, Administrators; full control; no inherited ACEs |
| E3 `Etapa 3/OpenSpec/deployment/.env.local` | Present; metadata and SDDL matched pre-operation snapshot |
| Secret content | Never displayed, logged, read for verification, or hashed in this operation |

The move operation completed successfully. No credential rotation occurred. No Docker/Compose command or deployment was run.

## Additional sensitive deployment artifacts found
While creating the sanitized manifest, path/metadata inspection found that the original 80-file manifest also included `deployment/certs/dev-cert.pem` (1,070 bytes) and `deployment/certs/dev-key.pem` (1,704 bytes). Both remain present in E3 and E4; neither was opened, hashed, moved, or modified. The private key is generated local TLS material. The researcher approved moving only `.env.local`, so this report does not move or otherwise remediate the certificate/key. They are excluded from the sanitized inventory and remain a separate E4 security exception requiring explicit direction before distribution/runtime use.

The local Compose file still names `./.env.local` as a required service `env_file`. It will need a separately approved protected-configuration approach before Compose is usable from the sanitized tree. A future access-controlled Compose override may point the service `env_file` at the absolute protected external path, or an approved external secret/environment mechanism may be adopted. The current Compose file was not changed. No secret value is stored in this evidence.

## Historical vs sanitized inventories
The original H0 `inventory.md`, `source-manifest-sha256.json`, and raw reports remain unchanged and continue to describe the initial copied state (80 files / 441,008 bytes, including the E4 `.env.local` and generated TLS files). The new `E4_OPENSPEC_I06_SANITIZED_MANIFEST.json` and `E4_OPENSPEC_I06_SANITIZED_INVENTORY.md` are separately versioned. They include the 77 retained nonsensitive original-manifest files (437,819 bytes) and exclude `.env.local`, `dev-cert.pem`, and `dev-key.pem`. Each retained source and E4 file was rehashed and matches its original recorded digest; no generated dependencies, build output, cache, virtualenv or runtime DB was added.

This is a sanitized **inventory subset**, not a statement that every file currently under E4 has been sanitized: the TLS certificate and private key remain physically in E4 pending authorization. No app source or inherited test file changed; the sanitized hashes for retained files confirm equality with the original H0 copies. The deliberate exclusions are not defects in those retained source files.

## Scope limits
Stage 3 was not modified. No application code, tests, specifications, balances, transactions, database, Compose file, credentials, historical evidence, or other tool workspace was modified. The only filesystem move was the researcher-approved E4 `.env.local` move. Original hashes for all excluded sensitive/generated files are not repeated here.
