# Project Seed: Basic Web Calculator

## 1. Executive Summary & Intent
The goal of this project is to build a modern, daily-use, responsive web calculator. The application must accurately evaluate complex, chained arithmetic expressions while strictly adhering to standard order of operations (**PEMDAS**) and maintaining high decimal precision. 

This document serves as the single source of truth for all AI agents and developers to ensure consistent implementation across all architecture layers.

---

## 2. Core Functional Requirements

### 2.1 Arithmetic & Logic Engine
- **Expression Parsing:** Must support chained arithmetic expressions (e.g., `12.5 + 3 * (4 - 1.5) / 2`).
- **Precedence Rules:** Standard **PEMDAS** rules apply (Parentheses, Exponents, Multiplication, Division, Addition, Subtraction).
- **Decimal Precision:** All calculations must avoid floating-point representation errors (e.g., `0.1 + 0.2` must strictly evaluate to `0.3`).
- **Error Handling:** Gracefully handle edge cases such as division by zero, invalid operator sequences, and unclosed parentheses with descriptive error messages.

### 2.2 User Interface & Experience
- **Daily-Use Calculator Design:** UI must mimic a physical, standard desktop calculator with clear display areas for both the full input expression and the live/final result.
- **Responsive Layout:** Layout must seamlessly adapt to mobile, tablet, and desktop screen sizes without horizontal overflow or clipped buttons.
- **Accessibility (a11y):**
  - **Keyboard Integration:** Full keyboard support (number keys, standard operators `+`, `-`, `*`, `/`, `Enter` or `=` for evaluate, `Backspace` for clear/delete, and `Escape` for reset).
  - **Visual Readability:** High-contrast colors, clear button labeling, active/focus state indicators, and legible typography.
  - **Screen Reader Support:** Accessible ARIA attributes (`aria-label`, `role="button"`, `aria-live` regions for expression outputs).

---

## 3. Technical Architecture & Tech Stack

### 3.1 Backend Service
- **Framework:** Python 3.11+ using **FastAPI**.
- **Role:** Expose a REST API endpoint (e.g., `POST /api/v1/evaluate`) responsible for parsing, validating, and calculating expressions.
- **Precision:** Use Python's built-in `decimal` module (or standard AST expression evaluation) to ensure exact precision rather than standard float arithmetic.
- **Testing:** Include unit tests (using `pytest`) covering PEMDAS sequence correctness and edge-case error responses.

### 3.2 Frontend Client
- **Tech Stack:** **React** with **TypeScript** (built with Vite or Next.js/React framework).
- **Role:** Manage input and UI state, render component tree, handle keyboard/click events via React event hooks, call the FastAPI REST API, and display calculation states.
- **Type Safety:** Define strict TypeScript interfaces for API request payloads, success responses, and error state structures.

---

## 4. Non-Functional Requirements & Coding Standards
- **Clean Architecture:** Strict separation between UI rendering state and backend math evaluation.
- **RESTful Principles:** Clear, JSON-based payload structures for requests and error outputs.
- **Consistency:** Ensure UI components, API routes, and tests are modular, well-documented, typed, and self-contained.

---

## 5. Instructions for AI Agents
When generating code for this repository:
1. Always start by implementing or updating the backend math engine before updating frontend components.
2. Maintain strict adherence to decimal precision logic—never use raw standard float division in calculation routines.
3. Ensure all generated React component markup includes proper keyboard hooks, strict TypeScript props/interfaces, and accessibility attributes out of the box.