<!--
=== SYNC IMPACT REPORT ===
Version Change: 1.1.0 -> 1.2.0
Bump Rationale: Amended the Governance section to preserve workflow and tool neutrality. Removed the requirement that compliance reviews must be conducted using Spec Kit tools or any other specific software. Compliance reviews may now use any suitable human or automated technique, provided they verify alignment between the approved specifications, planning artifacts, tasks, and implementation.
Modified Principles: None
Added Sections: None
Modified Sections:
  - Governance (redefined the Compliance Review rule to be completely tool-neutral)
Removed Sections: None
Follow-up TODOs: None
==========================
-->

# Shift Bank Constitution

## Core Principles

### I. Specification Authority
Approved specifications are the absolute source of truth for all implementation. Developers MUST NOT
introduce any functionality, APIs, or behaviors outside of the explicitly approved scope. The
approved specification defines the boundary of acceptable work.
*Rationale: To prevent gold-plating and ensure that all stakeholders are aligned on what is being
built.*

### II. Specification-First Changes
Any requirement change, addition, or refinement MUST be formally reflected in the specification
and approved *before* implementation begins. Code changes MUST NEVER precede the specification.
*Rationale: To avoid drift between documentation and the codebase, maintaining a single reliable
source of truth.*

### III. Proportional Implementation
Implementation MUST remain strictly proportional to the requested development stage (e.g., Etapa 1).
Developers MUST prioritize simplicity and avoid unnecessary scope expansion, gold-plating, or
speculative features.
*Rationale: Keeps development fast, focused, and aligned with current phase objectives without
adding maintenance overhead for unused features.*

### IV. Requirement-Driven Validation
Every completed feature MUST be thoroughly validated against the exact approved requirements and
acceptance scenarios documented in the specification. A feature is not complete until all criteria
are verified as met.
*Rationale: Ensures quality and guarantees that the system behaves exactly as agreed upon in the
specification before it is considered done.*

### V. Strict Scope Compliance
No unwritten agreements, assumptions, or hidden features are permitted. If a feature or logic
is not explicitly documented in the approved specification, it MUST NOT be implemented.
*Rationale: Avoids scope creep and maintains transparency across the development process.*

## Verification and Quality Gates

- **Validation Evidence Mapping Rule**: All validation evidence, regardless of the validation
  technique used (e.g., manual walkthroughs, custom verification scripts, or automated tests),
  MUST map directly to the approved requirements or acceptance scenarios defined in the
  specification. Specific verification techniques like unit or integration testing are NOT
  mandated unless they are explicitly required by an approved feature specification.
- **Workflow Neutrality Statement**: Pull requests, unit tests, integration tests, or specific
  review tools are supported but are NOT mandated under this Constitution unless explicitly required
  by an approved feature specification. The development process remains fully compatible with
  experimental or lightweight workflows.
- **Pre-Implementation Alignment**: A general human review MUST be conducted prior to starting
  implementation to ensure that the proposed approach is strictly proportional to the requested
  stage and does not introduce unnecessary scope.
- **Pre-Completion Compliance Review**: A general human review MUST be conducted prior to feature
  completion to verify that the final implementation strictly complies with the approved specification.

## Development & Specification Workflow

1. **Specification Drafting**: Generate or update specifications utilizing the `speckit.specify`
   workflow when requirements change.
2. **Approval & Sign-off**: Obtain explicit stakeholder approval of the specification.
3. **Task Planning**: Deconstruct approved specifications into concrete development tasks using
   the `speckit.tasks` workflow.
4. **Precise Execution**: Implement the requested logic, keeping the codebase simple, stage-proportional,
   and in alignment with the approved specification.
5. **Validation & Verification**: Gather and document validation evidence (using any technique)
   mapping back to the approved requirements and acceptance scenarios before considering the
   feature complete.

## Governance

- **Supreme Authority**: This Constitution is the supreme governing document for the Shift Bank
  project. All development workflows and codebase modifications must comply with it.
- **Amendment Procedure**: Any amendment to this Constitution must be proposed with a clear
  rationale, a corresponding version bump, and a Sync Impact Report.
- **Versioning Policy**: Semantic versioning is strictly applied to governance documentation (MAJOR
  for backward-incompatible rule changes, MINOR for additions/refinements, PATCH for corrections).
- **Compliance Review**: Compliance reviews MUST be conducted regularly to verify full alignment
  between the approved specifications, planning artifacts, tasks, and implementation. These
  reviews may use any suitable human or automated technique, and they are NOT mandated to use Spec
  Kit tools or any other specific software.

**Version**: 1.2.0 | **Ratified**: 2026-09-30 | **Last Amended**: 2026-09-30
