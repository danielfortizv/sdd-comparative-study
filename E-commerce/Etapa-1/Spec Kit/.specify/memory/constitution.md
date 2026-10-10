<!--
SYNC IMPACT REPORT
==================
- Version change: Initial Setup -> 1.0.0
- List of modified principles:
  - PRINCIPLE_1_NAME -> I. Strict Specification Fidelity
  - PRINCIPLE_2_NAME -> II. No Scope Expansion
  - PRINCIPLE_3_NAME -> III. English as the Sole Language
  - PRINCIPLE_4_NAME -> IV. Review-First Specifications
  - PRINCIPLE_5_NAME -> V. Explicit Implementation Approval
  - (Added) VI. Specification-First Corrections
  - (Added) VII. Component Separation
- Added sections:
  - Technical Stack Constraints
  - Specification-Driven Development Workflow
- Removed sections:
  - None
- Follow-up TODOs:
  - None
-->

# E-Commerce Case - Stage 1 Constitution

## Core Principles

### I. Strict Specification Fidelity
Fidelity to especificacion-semilla-final-en.md as the sole functional source of truth for Stage 1. No other documents or inputs may override this source.

### II. No Scope Expansion
No gold-plating, scope expansion, or invented business rules are permitted. Requirements must be implemented exactly as described, without adding features or technical complexity not requested.

### III. English as the Sole Language
All specifications, source code, comments, documentation, and user-interface text must be written in English.

### IV. Review-First Specifications
All specification artifacts (requirements, design, and plans) must be thoroughly reviewed and verified before any implementation begins.

### V. Explicit Implementation Approval
No application code may be created or modified until explicit implementation approval is granted.

### VI. Specification-First Corrections
Any functional or code-related corrections must first update the specification artifacts before any changes are applied to the code.

### VII. Component Separation
The React and TypeScript frontend and the Python and FastAPI backend must remain separate, independent components.

## Technical Stack Constraints

The React and TypeScript frontend and the Python and FastAPI backend must remain separate, independent components. All source-code identifiers, comments, technical documentation, and user-interface text must be in English. No direct application code, dependency manifests, tests, databases, build configuration, or frontend/backend scaffolding may be created or modified outside the specification workflow.

## Specification-Driven Development Workflow

Before implementing code, the tool must generate and review the native specification artifacts. Once approved, only the approved specification artifacts can be implemented. If corrections are requested, the specifications must be updated first, then applied to the code using the tool's native specification workflow.

## Governance

Amendments to this constitution require documentation, verification, and human approval. The constitution supersedes any other local development practices.

**Version**: 1.0.0 | **Ratified**: 2026-10-06 | **Last Amended**: 2026-10-06
