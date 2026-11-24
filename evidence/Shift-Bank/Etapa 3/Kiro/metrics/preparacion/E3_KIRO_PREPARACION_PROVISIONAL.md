# Shift Bank E3 Kiro — provisional preparation

**Status: PROVISIONAL — STAGE 2 CORRECTIONS IN PROGRESS**

## Source and destination

- Source: `Shift-Bank/Etapa 2/Kiro`
- Destination: `Shift-Bank/Etapa 3/Kiro`
- Evidence: `Shift-Bank/Etapa 3/_experiment_logs/Kiro`
- Physical copy completed: **2026-11-16 19:13:40.5358302–19:13:40.6793513 UTC** (destination file creation-time interval; workstation clock).
- Copy method: ordinary independent `Copy-Item` file copies into a previously absent destination. No symlink, junction, hardlink, or shared mutable storage was used.
- 73 files copied. The contemporaneous source hash snapshot and destination comparison recorded 73/73 matches and no detected source hash drift during the copy interval. See `E3_KIRO_PROVISIONAL_SHA256.csv`.

## Stage 2 is still changing

Repository HEAD: `08311b42d1d5745540af459775b4bb24de181947`, branch `ShiftBank`, repository root `C:/Users/danie/Documents2/sdd-comparative-study`.

Stage 2 Kiro is not frozen. Before the copy, the working tree already showed an edited Kiro experiment bitacora and new pre-correction SonarQube exports. A later comparison found **11 files** in the current Stage 2 Kiro tree differ from the provisional copy: the Stage 2 tasks and metadata, backend repository, and eight frontend components. The full path/hash comparison is `E3_KIRO_PROVISIONAL_VS_CURRENT_STAGE2.csv`. The copy is therefore a point-in-time provisional snapshot, not a final or guaranteed coherent Stage 2 closure. The researcher must explicitly confirm Stage 2 completion before running the final synchronization script.

The shared repository also has unrelated working-tree changes in other experiments. No changes were made to Stage 2, its evidence, or other Stage 3 tools by this preparation.

## Inventory and exclusions

The SHA-256 inventory records each copied path, source hash, destination hash, and comparison result. Provisional copy result: **73 MATCH, 0 MISMATCH**. The source inventory is not a statement that Stage 2 corrections are complete.

Excluded: `.venv`, `venv`, `node_modules`, `dist`, `build`, Python/test/scanner caches (`__pycache__`, `.pytest_cache`, `.scannerwork`, `.sonar`, and similar), Git metadata, coverage outputs, experiment/session logs, SQLite databases and `-wal`/`-shm`/journal files, `.env` secrets, key/certificate files, and files at least 100 MB. Source contained `frontend/node_modules`, `frontend/dist`, `.scannerwork`, and a protected `.pytest_cache`; they were excluded. Enumeration emitted access-denied warnings when PowerShell traversed the excluded `.pytest_cache`; it was not copied. No database, WAL, or SHM file exists in the Stage 3 copy.

Kiro's historical specs were retained under `.kiro/specs/shift-bank` and `.kiro/specs/shift-bank-stage2`. No `.kiro/steering` directory or additional Kiro settings/configuration templates were found in the Stage 2 source. The source contains 17 backend `test_*.py` modules. Frontend `package.json` defines a production build but no test script.

## Environment and reproducibility

Detected without installing dependencies:

- Python 3.13.2; globally visible FastAPI 0.142.2, Uvicorn 0.54.0, Pydantic 2.12.5.
- Stage 2 pins FastAPI 0.115.5, Uvicorn 0.32.1, Pydantic 2.10.3 in `backend/requirements.txt`; `requirements-dev.txt` pins pytest 8.3.4 and httpx 0.28.1 and includes runtime requirements. The currently visible global packages differ from the project pins. Use the fresh virtual environment in `E3_KIRO_STARTUP.md`.
- Node.js 24.19.0, npm 11.17.0. The lockfile resolves React/React DOM 18.3.1, Vite 5.4.21, TypeScript 5.9.3, and `@vitejs/plugin-react` 4.7.0. These lockfile values are recorded, not installed or independently tested in this preparation.

Inherited commands (not run in this preparation): from `backend`, `python -m pytest -q`; from `frontend`, `npm ci` and `npm run build`. No test, build, SonarQube scan, database creation, dependency installation, load test, or deployment was run. No Stage 2 or Stage 3 test result or metric is asserted here.

## Seed and missing prerequisites

Canonical seed exists at `Etapa 3/SEED-3.md`, SHA-256 `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`. It is left unchanged.

The named `SHIFT_BANK_E3_PROTOCOLO_REPLICABLE_OTRAS_HERRAMIENTAS.docx`, `Etapas proyecto de grado (1).pdf`, and `Guia Estandarizacion Metricas.pdf` were not found in the accessible repository file search. They were not reconstructed. The parent comparative-study repository's `docs/methodology.md`, `docs/reproducibility.md`, and `docs/evaluation-criteria.md` were available and inspected.

## Next state transition

Do not treat this tree as the approved Stage 3 baseline. After the researcher confirms Stage 2 closure, review any Stage 3 Kiro changes against the provisional manifest, preserve the existing preparation/evidence, and explicitly invoke `E3_KIRO_FINAL_SYNC.ps1` as documented in `E3_KIRO_FINAL_SYNC_USAGE.md`. The script refuses synchronization if the provisional destination has additions, removals, or changed durable files.
