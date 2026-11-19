# Iteration 03 researcher checkpoint

## Security containment
The Stage 3 and Stage 4 `deployment/.env.local` files are each 415 bytes, regular files, and ignored by Git through their local `.gitignore`; neither is tracked. The Stage 4 baseline nonetheless included the file, contrary to the previous inventory exclusion statement. Compose currently requires it as its backend `env_file`; the application otherwise reads externally supplied environment values (and encryption can use an external key file). Existing frontend build/tests do not depend on the file; backend tests set test configuration explicitly. No checks were rerun.

Approval is required before quarantining/removing the E4 copy or altering Compose configuration. Leave Stage 3 untouched. Do not use or expose the values. Rotation is conditional on researcher/operator confirmation of reuse, deployment with valuable data, unauthorized access, or uncontrolled exposure; preserve old encryption keys for ciphertext and handle audit-key rotation so the existing chain remains verifiable. No rotation or containment mutation occurred.

The filename-only E4 scan found one `.env.local` and no other credential/certificate-named files. A redacted credential-assignment scan of 24 evidence files found no matching assignments. This is not a proof against renamed/encoded/split secrets. The original manifest includes a digest for `.env.local`; historical evidence remains untouched. Any future sanitized manifest must be new and versioned.

## H0 and H1 handoff
H0 results remain those in I02: 80/80 hashes match, 441,008 bytes; inherited backend 54/54; frontend 9/9 and build pass; native strict all-target validation 6/6 pass. Overall H0 is PARTIAL because of the sensitive-file inclusion and missing canonical-reference verification. Iteration 03 did not rerun baseline checks.

Six I02 analysis/plan artifacts exist and were reviewed without modification. D-01..D-14 readiness is summarized in `E4_OPENSPEC_I03_H1_HANDOFF.md`; it is based on supplied decisions and inherited source, not confirmed against absent canonical references and not researcher approval. Four D-02 alternatives are compared there; none is chosen.

## References
Locally available: `SEED-4_AnexoA_replicacion.md`, 4,240 bytes / 24 lines, with the expected objective, compatibility scope, unresolved decisions and verifiability sections and a complete ending. It is the replication annex, not the canonical `SEED-4.md`; equivalence cannot be claimed.

Missing locally: `SEED-4.md`; `Guia_replicacion_Etapa4_Shift_Bank_SDD.docx`; `Guia Estandarizacion Metricas.pdf`; `Etapas proyecto de grado (1).pdf`. Safest intended placement for researcher-provided originals: `Etapa 4/_reference_inputs/OpenSpec/`, outside `Etapa 4/OpenSpec/` and outside evidence outputs; keep read-only and do not duplicate or edit existing normative files. Record provenance and SHA-256 only after the researcher identifies the canonical original.

## Telemetry available for Iteration 03
- Session ID: N/D. No session identifier in the interaction register or accessible session metadata.
- Tool/model identity: Codex CLI family is stated by the experiment setup; exact effective model: N/D.
- Wall-clock duration: N/D (no start/end telemetry).
- Agent processing duration: N/D.
- Tool calls: 5 `functions.exec` command batches observed for this iteration; underlying individual shell command count not normalized.
- Human prompts/interventions: 1 researcher task prompt observed; no follow-up intervention observed.
- Input/output/cache tokens: N/D.
- Estimated cost: N/D.
- No Stage 3 telemetry was used or mixed into this record. Historical transcripts were not modified.

## Approval checkpoint — no approval inferred
Researcher review is required for: (1) E4-only runtime-file quarantine/removal/configuration plan; (2) whether credentials were reused, deployed, or exposed and whether rotation is required; (3) D-02 legacy balance/history/currency/identity policy and related limits/MFA/ACH treatment; (4) provision/confirmation of missing canonical documents; (5) D-01..D-14 and artifact-plan approval before any H2 specification work. Financial migration, specification authoring, and Stage 4 implementation remain unauthorized.

No code, specifications, financial data, credentials, or historical evidence were modified in Iteration 03. The two `.env.local` files were not modified, moved, deleted, displayed, or hashed anew.
