<!--
Sync Impact Report:
- Version change: null -> 1.0.0 (Initial adoption)
- List of modified principles:
  - PRINCIPLE_1: I. Exact Decimal Precision (Initial)
  - PRINCIPLE_2: II. Strict PEMDAS Parsing (Initial)
  - PRINCIPLE_3: III. Comprehensive Accessibility (a11y) & Physical UX (Initial)
  - PRINCIPLE_4: IV. RESTful Clean Architecture (Initial)
  - PRINCIPLE_5: V. Test-Driven Validation (Initial)
- Added sections:
  - Core Principles
  - Tech Stack & Platform Constraints
  - Agent Implementation Workflow
  - Governance
- Removed sections: None
- Follow-up TODOs: None (all placeholders resolved successfully)
-->

# Basic Web Calculator Constitution

## Core Principles

### I. Exact Decimal Precision
All calculations MUST strictly avoid floating-point representation errors (e.g., `0.1 + 0.2`
must evaluate to `0.3`). Raw standard float division or arithmetic MUST NEVER be used in
calculation routines. Instead, the backend calculation engine MUST use Python's built-in
`decimal` module or standard AST expression evaluation to ensure absolute numerical precision.
**Rationale**: High numerical accuracy is the core requirement of any calculator; discrepancies
due to standard IEEE 754 float representation violate the functional integrity of the app.

### II. Strict PEMDAS Parsing
The arithmetic engine MUST evaluate chained expressions (e.g., `12.5 + 3 * (4 - 1.5) / 2`)
adhering strictly to standard PEMDAS precedence rules (Parentheses, Exponents, Multiplication,
Division, Addition, Subtraction). The engine MUST gracefully handle edge cases such as
division by zero, invalid operator sequences, and unclosed parentheses, returning clear and
descriptive error messages in the API response.
**Rationale**: Users expect standard mathematical rules. Ambiguous or incorrect evaluation
sequences are unacceptable.

### III. Comprehensive Accessibility (a11y) & Physical UX
The frontend client MUST mimic a daily-use physical desktop calculator with clear display areas
for both the full input expression and the live/final result. The client MUST support full
keyboard integration (number keys, operators `+`, `-`, `*`, `/`, `Enter` or `=` for evaluate,
`Backspace` for clear/delete, and `Escape` for reset). It MUST feature high-contrast colors,
active/focus state indicators, and complete screen reader support using ARIA attributes (e.g.,
`aria-label`, `role="button"`, and `aria-live` regions).
**Rationale**: The calculator must be usable by everyone, regardless of assistive technology,
and feel tactile and intuitive like a physical device.

### IV. RESTful Clean Architecture
There MUST be a strict separation of concerns between the frontend UI rendering state and the
backend mathematical evaluation engine. The frontend React client is responsible for UI state,
event handling, and API communication. It MUST delegate all arithmetic operations and validation
to the FastAPI backend via structured REST API endpoints using JSON payloads.
**Rationale**: Keeping calculation logic on the backend ensures a single source of truth,
simplifying the code and making testing and maintenance highly consistent.

### V. Test-Driven Validation
AI agents and developers MUST implement or update the backend math engine and its unit tests (using
`pytest`) before updating frontend components. Every math-engine change or API endpoint modification
must be verified with comprehensive tests covering precedence correctness, division by zero, and
invalid syntax.
**Rationale**: Testing ensures that calculation logic remains robust against regression as new
features or layouts are implemented in the frontend client.

## Tech Stack & Platform Constraints
- **Backend Service**: Python 3.11+ using the FastAPI framework.
- **Frontend Client**: React with TypeScript, built with Vite or Next.js.
- **Type Safety**: Explicit TypeScript definitions for all API request payloads, success
  responses, and error state structures. Implicit `any` or raw un-typed casts MUST NOT be used.
- **Error Payloads**: All API errors must return standard JSON-based payloads with clear error
  messages.

## Agent Implementation Workflow
1. **Backend First**: Always implement, extend, or update the backend evaluation engine and its
   `pytest` unit tests before making modifications to the React UI or client-side assets.
2. **Accessibility-First UI**: Ensure all React component markups include proper
   keyboard hooks, focus outlines, and accessibility properties out of the box.
3. **Responsive Layouts**: Layouts MUST adapt seamlessly to mobile, tablet, and desktop viewports
   without horizontal overflow or clipped buttons.

## Governance
This Constitution is the supreme authority for this project. All design, code, and test changes
must comply with it. Amendments to this Constitution require updating the version number, adding
a Sync Impact Report, and updating the `LAST_AMENDED_DATE` metadata.

**Versioning Policy**:
- **MAJOR**: Backward-incompatible governance or principle changes.
- **MINOR**: Adding or materially expanding a principle/section.
- **PATCH**: Clarifications, formatting, or typoes fixes.

**Version**: 1.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-09-28
