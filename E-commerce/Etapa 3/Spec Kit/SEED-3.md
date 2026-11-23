# Canonical Seed Specification - E-Commerce - Stage 3

## Purpose and scope
Evolve the inherited Stage 2 e-commerce application using Stage 3 Option A: architecture and automated delivery verification. Preserve the catalog, local cart, authentication, simulated checkout, product reviews with images, and moderation.

## Required outcomes
- Add meaningful Playwright or Cypress end-to-end tests against the real frontend and backend. Cover the purchasing journey and the review submission, hidden-pending, moderator approval, and public-visibility journey; include an access-denied check for a regular customer attempting moderation.
- Add a CI pipeline that installs dependencies, runs backend and frontend tests, collects coverage, builds the frontend, and runs the end-to-end checks. Do not publish or deploy to external infrastructure.
- Provide reproducible Docker multi-stage builds and a simple local orchestration command for frontend and backend. Use appropriate container networking and a documented health/readiness strategy.
- Implement bounded API response caching for suitable public read endpoints, with documented expiry and invalidation. Authentication-specific responses and moderation queues must not leak between users or be served from an inappropriate shared cache. Newly approved reviews must become publicly visible correctly.
- Produce backend coverage.xml and frontend lcov.info through documented commands, suitable for later quality analysis. Do not invent a coverage target or claim unexecuted checks passed.

## Constraints and specification workflow
Use the existing React/TypeScript frontend and Python/FastAPI backend. Keep this a local demonstration; avoid paid external services and architecture rewrites. Choose simple coherent defaults for unspecified details, record assumptions in native Stage 3 specs, and proceed without questions or human approval. All prompts, specs, code, comments, documentation and UI text must be in English.
Inspect inherited native specs and code, then generate all native Stage 3 requirements, design and task artifacts before changing implementation code. Keep earlier stages identifiable. Any correction to code must follow a native spec clarification. The researcher accepts reasonable implementation differences between tools and preauthorizes specs and implementation. Do not loop on exact spec comparisons.
Minimize credits: inspect only relevant files, keep specs concise, use focused tests, and stop repeating successful checks. Run the real local tests and production build. Execute Docker validation if Docker is available; otherwise explicitly document that limitation and validate what is possible without claiming a container run. Provide exact PowerShell startup and verification commands plus demo credentials in README.md.
