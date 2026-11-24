# SEED-2 — Shift Bank: Functional Complexity and State

Status: PROPOSED COMMON SEED — pending explicit researcher approval.
Date prepared: 2026-11-14
Case study: Shift Bank
Stage: 2 — Functional Complexity and State
Selected option: A

## Objective

Extend the existing Shift Bank application from Stage 1 (brownfield development). Evaluate whether specification-driven development can introduce new banking workflows and persistent state while preserving the established behavior and architecture.

Each evaluated SDD tool MUST work exclusively from its own Stage 1 application. The implementation, artifacts, tests and outcomes from other tools are not implementation templates.

## Required capabilities

1. Simulated third-party ACH/interbank transfers, including saved or ad hoc beneficiaries, input validation, pending/settled/failed states, immediate debit for pending transfers, settlement processing, and exactly-once refunds for failed transfers.
2. Scheduled recurring payments, for both internal and ACH transfers, with daily, weekly and monthly frequency, automatic execution, next due dates, and pause/resume/cancel controls.
3. User-configurable dynamic limits, including per-transfer and per-day limits, enforced consistently for internal, ACH and automatically executed recurring payments.

## Compatibility constraints

- Preserve all observable Stage 1 behavior: accounts, balances, internal transfers, transaction history, simulated MFA, and the already-authenticated mock-user model.
- Preserve the currency, starting-data contract, MFA threshold, PIN/challenge behavior, and existing technology decisions from THIS tool's own Stage 1. Report differences rather than silently imposing another tool's values.
- Retain a Python backend and a React/TypeScript frontend, compatible with the inherited project's frameworks, interfaces, tests and conventions.
- Do not add real bank integrations, real money transfers, registration/login, or Stage 3/4 functionality.
- Prefer technology-independent, testable requirements; resolve business ambiguities explicitly before writing implementation code.
- Make no functional code changes without first modifying and approving the applicable specifications using the SDD tool's native workflow.
- Validate inherited functionality and new behavior with repeatable tests. Record failures and corrections instead of hiding them.

## Normative scope for this prospective run

Use the accompanying `E2_COMMON_FUNCTIONAL_CONTRACT.md` for the detailed requirements (ACH-01..10, REC-01..12, LIM-01..09, HER-01..06) and A01..A21 acceptance scenarios. This seed and its contract must be distributed unchanged to all remaining tools if approved as a common input.

The researcher, not the agent, approves open business decisions, specifications, and authorization to implement.

## Experimental provenance

This document is proposed for the remaining tools on 2026-11-14. It was not used prospectively by the earlier Tessl execution, and must not be represented as its historical seed.
