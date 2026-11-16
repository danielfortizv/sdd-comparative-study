# Copy exclusions and skipped links

- Source: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 1\Spec Kit`
- Destination: `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit`
- Generated: `2026-11-14T11:55:43.799604-05:00`
- Method: Python `os.walk(..., followlinks=False)` plus raw-byte SHA-256; eligible files copied with `shutil.copy2`. Paths in manifests use deterministic POSIX separators. Symbolic links and Windows reparse points are not followed.

## Exclusion policy

- Excluded dependency/build/cache directories: `.git`, `node_modules`, `.venv`, `venv`, `env`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `dist`, `build`, `coverage`, `htmlcov`, `.scannerwork`, `.vite`, `.next`, `.nuxt`, `.parcel-cache`, `playwright-report`, `test-results`.
- Excluded `.env*` secrets (except `.env.example`), `.coverage`, Python bytecode, logs/temp/swap/dump/trace files, and mutable SQLite database/WAL/SHM files.
- Preserved source, tests, historical specs, Spec Kit templates/scripts/integration metadata, `.gemini` slash-command files, dependency manifests and lockfiles.

## Observed exclusions

- generated/dependency/cache directory (.pytest_cache): 9 files under 2 excluded entries
  - `.pytest_cache` (directory; 5 file(s))
  - `backend/.pytest_cache` (directory; 4 file(s))
- generated/dependency/cache directory (.ruff_cache): 4 files under 1 excluded entries
  - `.ruff_cache` (directory; 4 file(s))
- generated/dependency/cache directory (__pycache__): 5 files under 2 excluded entries
  - `backend/src/__pycache__` (directory; 4 file(s))
  - `backend/tests/__pycache__` (directory; 1 file(s))
- generated/dependency/cache directory (dist): 3 files under 1 excluded entries
  - `frontend/dist` (directory; 3 file(s))
- generated/dependency/cache directory (node_modules): 8440 files under 1 excluded entries
  - `frontend/node_modules` (directory; 8440 file(s))
- mutable SQLite database or journal: 1 files under 1 excluded entries
  - `backend/shift_bank.db` (file; 1 file(s))

## Skipped symbolic links / reparse points

- None observed.

## First-copy comparison

- Source-eligible files: 59
- Destination files: 59
- Comparison counts: copied=59, missing=0, changed=0, unexpected=0

## Tracked Stage 1 SQLite state review

- `backend/shift_bank.db` is a Git-tracked Stage 1 file. It was excluded from the Stage 2 copy because it is mutable runtime state.
- The Stage 1 DB was inspected read-only and remained unchanged (`git diff --quiet HEAD -- <path>` returned 0).
- Observed Stage 1 DB SHA-256: `2FCD0C707E161807AC2AE54752D821ED0A95E1082F61BB5EDB6E10921FD5038A`.
- The DB currently has two accounts (Checking: `4000000.00` COP; Savings: `16000000.00` COP) and five transfer rows. The code-defined fresh database seed in `backend/src/database.py` instead creates Checking at `5000000.00` COP, Savings at `15000000.00` COP, and two historical transfers.
- Thus, the currently persisted Stage 1 runtime state is not reproduced by the code seed. The source DB remains intact in Stage 1, but its additional/mutated state was not carried into Stage 2. A researcher decision is required if a future Stage 2 migration is expected to preserve that runtime history rather than start from the reproducible code seed.
- The Stage 2 regression tests created and used a separate database under the Stage 2 copy. See `E1_DATABASE_READONLY_INSPECTION.txt`.
