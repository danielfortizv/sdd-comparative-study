# Project Seed (Stage 2): Scientific Web Calculator & Extended State Management

## 1. Executive Summary & Intent
The goal of **Stage 2** is to expand the existing Web Calculator project implemented in Stage 1 into a full-fledged **Scientific Calculator**. This stage introduces advanced mathematical capabilities, interactive session history, and dedicated memory registers.

This document acts as the progressive specification for Stage 2. All implementation changes must build directly upon the codebase generated during Stage 1 without breaking baseline arithmetic functionality, accessibility, or clean architecture patterns.

---

## 2. Key Stage 2 Directives & Legacy Inspection

### 2.1 Backward Compatibility & Pre-Existing Bug Reporting
1. **Preserve Stage 1 Features:** All primary Stage 1 arithmetic features, standard PEMDAS rules, UI layout responsiveness, and accessibility integrations must remain operational and unbroken.
2. **Pre-Existing Error Detection Protocol:** Before applying new Stage 2 modifications, the AI agent/developer **MUST analyze and inspect the Stage 1 implementation codebase**. Any discovered bugs, architectural flaws, decimal precision issues, or missing edge-case handlers must be explicitely reported/documented first so they can be fixed as part of this stage's execution.

---

## 3. Core Functional Requirements (Stage 2 Extensions)

### 3.1 Advanced Mathematical Functions
- **Trigonometric Functions:** Support standard trigonometric calculations: `sin`, `cos`, `tan`, and their inverses (`asin`, `acos`, `atan`). Include support/toggle for **Radians** and **Degrees** modes.
- **Powers & Roots:** Support exponentiation ($x^y$, $x^2$, $10^x$), square roots ($\sqrt{x}$), $n$-th roots ($\sqrt[y]{x}$), and natural logarithms ($\ln$, $\log_{10}$).
- **Mathematical Constants:** Support quick input for standard constants: $\pi$ (Pi) and $e$ (Euler's number).
- **Error Handling:** Handle mathematical domain errors gracefully (e.g., division by zero, square root of negative numbers, logarithm of zero/negative numbers) with user-friendly messages.

### 3.2 Memory Register System
- **Memory Operations:** Implement standard calculator memory functions:
  - `M+`: Add current display/result value to memory.
  - `M-`: Subtract current display/result value from memory.
  - `MR`: Recall current memory value into the active expression/display.
  - `MC`: Clear current memory register.
- **Visual Memory Indicator:** UI must show a visual indicator (e.g., an "M" badge) on screen whenever the memory value is non-zero.

### 3.3 Session Calculation History
- **History Panel/Drawer:** Implement a interactive side drawer or collapsible section displaying the history of evaluated expressions in the current session.
- **Reusability:** Users can click/tap any historical entry to reload either the historical expression or its final result back into the current input area.
- **Session Lifecycle:** History must persist throughout the active user session in state. Provide a "Clear History" button.

---

## 4. UI & Architectural Updates

### 4.1 Enhanced Responsive UI
- **Scientific Layout Grid:** Transition the main display to accommodate the extended button layout for scientific functions and memory controls without overcrowding on mobile screens (e.g., collapsible scientific keypads or responsive grid expansion).
- **Keyboard Mapping Expansion:** Map hotkeys/shortcuts for scientific operations where appropriate (e.g., `^` for power, `p` or custom combinations for constants).

### 4.2 Backend & API API Extensions
- **FastAPI Endpoint Enhancement:** Update `POST /api/v1/evaluate` (or introduce dedicated scientific routing endpoints) to support advanced mathematical functions and constants while maintaining exact precision standards.
- **State Serialization:** Ensure session history and memory values comply with clean request/response data models with explicit TypeScript type definitions on the frontend.

---

## 5. Instructions for AI Agents
1. **Step 1 — Code Inspection:** Scan the current Stage 1 codebase. Document any discovered bugs, missing precision handlers, or refactoring requirements in a summary report before modifying code.
2. **Step 2 — Backend Engine Expansion:** Extend the Python math evaluation engine (`FastAPI`) to support trigonometric, logarithmic, power, and constant evaluation before touching frontend components. Include unit tests (`pytest`) for new scientific functions and angle unit conversions.
3. **Step 3 — State & Memory Logic:** Implement memory and history state managers, ensuring clear synchronization between React state and API responses.
4. **Step 4 — UI & Accessibility Integration:** Integrate the expanded keypad and history drawer into the React/TypeScript frontend with full ARIA accessibility and keyboard shortcut integration.