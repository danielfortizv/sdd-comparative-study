# Final Kiro baseline synchronization — researcher procedure

The provisional copy is not the final Stage 3 baseline. Do not run this script until the researcher has explicitly confirmed that all Stage 2 Kiro corrections and the Stage 2 experiment are complete.

Script: `E3_KIRO_FINAL_SYNC.ps1` in this directory.

From PowerShell, explicitly invoke it with the closure token after confirmation:

```powershell
Set-Location 'C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_experiment_logs\Kiro\preparacion'
.\E3_KIRO_FINAL_SYNC.ps1 -ResearcherApproval STAGE2-CLOSED
```

The token is an invocation guard, not a substitute for researcher judgment. This preparation did not invoke the script.

Before copying, the script checks that Stage 3 still matches every durable file in `E3_KIRO_PROVISIONAL_SHA256.csv`; additions, removals, or edits cause it to refuse synchronization. It copies the current Stage 2 working tree into a fresh staging directory using the documented exclusions, verifies file hashes and rechecks the source for changes during the copy. If the source changes during copying, the script stops before swapping the destination. It records current Git HEAD and Stage 2 working-tree status.

On success, the existing provisional `Etapa 3/Kiro` directory is renamed to a timestamped `Kiro.provisional-backup_*` sibling, then the verified copy becomes `Etapa 3/Kiro`. The provisional backup is retained; it is not deleted. Unique timestamped final SHA-256 manifest and finalization report files are added to `preparacion`. Existing reports and experiment logs are not overwritten.

If the script refuses because Stage 3 changed, preserve the evidence, inspect the differences, and resolve them with the researcher. Do not bypass the guard or remove the provisional directory to force a sync. Re-run only after the researcher resolves the conflict and confirms Stage 2 closure.
