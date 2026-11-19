## Purpose

Describe a repeatable local container deployment for the existing simulated banking application with secure transport, durable isolated storage, and predictable background processing.

## ADDED Requirements

### Requirement: Local Docker Compose application deployment
The application MUST be deployable locally with Docker Compose using the existing FastAPI backend and React production assets served through Nginx. The local deployment MUST use HTTPS with development certificates, externally provisioned secrets, and isolated persistent SQLite storage. It MUST NOT require Kubernetes, cloud infrastructure, or a complete CI/CD pipeline.

#### Scenario: Local deployment serves the production application
- **WHEN** the documented Compose services are started with required external secrets and development certificates
- **THEN** Nginx serves the React production application over HTTPS and forwards authorized API traffic to the existing FastAPI backend

#### Scenario: Required secrets or TLS material are absent
- **WHEN** required secrets or development TLS material are missing or invalid
- **THEN** deployment fails safely without generating or committing credentials, private keys, or insecure HTTP fallback

#### Scenario: SQLite storage is isolated and durable
- **WHEN** the containers are recreated using the configured persistent storage
- **THEN** application data remains in the isolated SQLite store and is not stored in the container's ephemeral filesystem

### Requirement: Healthchecks and single scheduler ownership
Compose services MUST expose meaningful healthchecks for readiness and liveness. Exactly one active application scheduler MUST process ACH and recurring payments for a shared database at any time; adding backend replicas or restarting a container MUST NOT start concurrent schedulers for that database.

#### Scenario: Service readiness reflects dependencies
- **WHEN** a service healthcheck is evaluated before its dependencies are ready or after they become unavailable
- **THEN** it reports unhealthy until it can safely serve its documented role

#### Scenario: Scheduler remains singular after restart
- **WHEN** the deployment restarts or backend service count changes
- **THEN** exactly one scheduler remains active for the shared SQLite store

### Requirement: Verify secure operations and persistence after restart
The deployment procedure MUST provide operational checks for HTTPS, banking operations, encryption at rest, MFA, audit-chain verification, and persistence after restart. A deployment MUST NOT be considered accepted unless all checks pass against its isolated local data.

#### Scenario: Operational checks verify deployed security and banking behavior
- **WHEN** an operator runs the deployment acceptance procedure
- **THEN** it verifies HTTPS, a permitted banking operation, encrypted stored sensitive data, inherited MFA, and a valid audit chain

#### Scenario: Restart preserves data and service behavior
- **WHEN** the services are restarted after creating synthetic banking data and an audit entry
- **THEN** data persists, sensitive values remain protected, audit verification succeeds, and banking operations remain available

#### Scenario: Local deployment does not contain prohibited material
- **WHEN** the deployment artifacts are reviewed
- **THEN** no committed private keys, credentials, or real banking data are present
