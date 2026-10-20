## Interaction 002 — BMAD Workflow Discovery

### Purpose

Determine the appropriate first BMAD workflow for the Shift Bank Stage 1 project before beginning planning or implementation.

### Tool / Skill

- BMAD skill: `bmad-help`
- BMAD version: 6.12.2
- Module: BMM
- Gemini CLI: 0.62.0
- Model: gemini-3.5-flash

### Input

A high-level description of the Shift Bank Stage 1 application was provided, including:

- Authenticated mock user
- Account visualization and balances
- Internal transfers between owned accounts
- Transaction history
- Sensitive transfers protected by mock MFA
- Python backend
- React + TypeScript frontend
- Explicitly excluded banking functionality
- Requirement to identify ambiguities and edge cases
- No implementation or application source modifications permitted

### Execution

`bmad-help` inspected:

- `_bmad/config.toml`
- `_bmad/_config/bmad-help.csv`
- `_bmad-output`
- Current workspace contents

### Findings

BMAD identified the following areas requiring clarification before architecture and implementation:

1. Mock authentication and identity representation
2. Account structure and currencies
3. MFA threshold and challenge behavior
4. Monetary precision
5. Transfer atomicity
6. Ledger/movement immutability
7. Self-to-self transfers
8. Zero/negative amounts
9. Insufficient funds
10. Duplicate/concurrent submissions
11. MFA expiration/abandonment
12. Incorrect MFA codes
13. Empty transaction history
14. Transaction ordering

### Workflow Recommendation

BMAD recommended the following planning sequence:

1. `bmad-product-brief` — Optional
2. `bmad-prd` — Required first gate
3. `bmad-ux` — Recommended
4. `bmad-architecture` — Required
5. `bmad-create-epics-and-stories` — Required
6. `bmad-sprint-planning` — Required
7. `bmad-build` — Implementation

### Decision

The next BMAD workflow will be:

`bmad-prd`

The product brief will be skipped unless later determined necessary, because the project concept and scope are already sufficiently defined.

### Scope Protection

- Application source modified: No
- Existing application code created: No
- Existing requirements/design/tasks modified: No
- BMAD planning artifacts created: No
- `_bmad-output`: Empty
- Implementation started: No

### Outcome

Interaction completed successfully.

BMAD recommends entering the PRD phase as the first formal planning gate.

