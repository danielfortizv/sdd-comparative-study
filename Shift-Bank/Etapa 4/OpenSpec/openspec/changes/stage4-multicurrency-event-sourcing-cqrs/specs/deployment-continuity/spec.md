## Purpose

Defines operational continuity for the inherited FastAPI, React, SQLite, and Compose/Nginx/TLS deployment after financial events and projections are introduced.

## ADDED Requirements

### Requirement: Preserve supported application and deployment stack
The Stage 4 system MUST retain FastAPI, React/TypeScript, SQLite, and the existing Compose/Nginx/HTTPS deployment capability. Durable domain events, projections, audit state, and idempotency records MUST persist across supported restart and container-recreation workflows. Exactly one active scheduler MUST own ACH and recurring work for a shared SQLite database. Required keys, certificates, and private configuration MUST be provisioned externally and MUST NOT be committed or generated as a deployment side effect.

#### Scenario: Restart preserves event and projection state
- **WHEN** the application restarts or its containers are recreated with the configured persistent SQLite storage
- **THEN** event history, projections, account versions, idempotency results, and audit verification remain available and consistent

#### Scenario: Required TLS or secret material is absent
- **WHEN** required TLS material or externally provisioned secret configuration is unavailable
- **THEN** secure deployment readiness fails without generating credentials, committing private material, or falling back to plaintext HTTP

#### Scenario: Scheduler remains singular across restart and scaling
- **WHEN** services sharing the SQLite database restart or backend service count changes
- **THEN** exactly one active scheduler processes ACH and recurring work for that database

#### Scenario: Deployment compatibility is documented without an unverified claim
- **WHEN** specification acceptance evidence is reviewed without an actual deployment run
- **THEN** deployment status is recorded as NOT VERIFIED rather than PASS
