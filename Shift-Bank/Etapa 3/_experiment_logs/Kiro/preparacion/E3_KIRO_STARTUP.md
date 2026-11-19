# E3 Kiro startup instructions

**Current state: PROVISIONAL — STAGE 2 CORRECTIONS IN PROGRESS.** Do not start Kiro Stage 3 discovery until Stage 2 is closed and the researcher has explicitly run the final synchronization procedure.

## 1. Finalize the baseline first

After the researcher confirms Stage 2 closure, follow `E3_KIRO_FINAL_SYNC_USAGE.md`. Confirm the final report and SHA-256 manifest exist before opening Kiro. Do not run tests against a Stage 2 database.

## 2. Create a fresh backend environment

In PowerShell:

```powershell
Set-Location 'C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro\backend'
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes `requirements.txt` and pins the Stage 2 test dependencies. No installation was run during preparation.

## 3. Run inherited backend regression tests only on disposable databases

The inherited `tests/conftest.py` fixture assigns every test a unique SQLite file under pytest's temporary `tmp_path`, patches both `app.config.DB_PATH` and `app.db.DB_PATH`, and removes the database and SQLite sidecars during teardown.

Before running tests, confirm that the Stage 3 copy has no database:

```powershell
if (Test-Path '.\shift_bank.db') { throw 'Unexpected Stage 3 database; stop and inspect before testing.' }
Get-ChildItem -Path . -Recurse -File -Include *.db,*.sqlite,*.sqlite3
```

The listing should be empty. Do not point tests at `Etapa 2/Kiro`, a copied historical database, or a persistent baseline. Then run from `backend`:

```powershell
python -m pytest -q
```

Afterward, repeat the database listing. It should still be empty because test databases are temporary. The app's default `backend/shift_bank.db` is created by application startup; do not start Uvicorn for this regression check. The Stage 2 source path is never used by these commands.

## 4. Install frontend dependencies and build

In a separate PowerShell session:

```powershell
Set-Location 'C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro\frontend'
npm ci
npm run build
```

The inherited frontend has no test script in `package.json`; record that fact rather than claiming a frontend test run.

## 5. Open the Kiro workspace

Launch the Kiro IDE and use **File → Open Folder** to open:

```text
C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Kiro
```

Confirm the open workspace is Stage 3 Kiro, not the Stage 2 source. Keep the shared seed outside the application copy and do not edit it.

## 6. Start Kiro's native Specs workflow

After final synchronization, open the unchanged common seed at:

```text
C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\SEED-3.md
```

In Kiro, use the native **Specs** workflow to create a new Stage 3 spec. Provide the seed's text unchanged as the initial feature description/context. Let Kiro conduct clarification and create its native requirements first. Do not paste in another tool's specifications or implementation approach.

Required researcher checkpoints:

1. Review and approve the meaning/trust boundary, protected fields, keys, and migration expectations for encryption.
2. Review and approve audit events and the required immutability/tamper-resistance guarantee.
3. Review and approve the load profile, measurement method, and numerical acceptance criteria.
4. Review and approve the deployment target, HTTPS, secrets, persistence, and scheduler operation.
5. Approve Kiro's requirements and then its design/tasks before authorizing any implementation.

No Stage 3 implementation, load test, or deployment may begin before the applicable human approvals. Record the approvals in Kiro's experiment evidence; do not infer approval from an unanswered question or elapsed time.
