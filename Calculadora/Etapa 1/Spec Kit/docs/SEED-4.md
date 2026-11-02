# Project Seed (Stage 4): Breaking Point / Drastic Migration to Reverse Polish Notation (RPN)

## 1. Executive Summary & Intent
The goal of **Stage 4** is to subject the Spec-Driven Development (SDD) workflow to a drastic architectural refactor / breaking change. 

In this stage, the underlying evaluation engine must undergo a **drastic engine migration**: transitioning from traditional infix expression parsing to **Reverse Polish Notation (RPN / Postfix Notation)**. The application must adapt to process calculations using stack-based RPN evaluation while keeping the test suite, containerization setup, and quality standards intact.

---

## 2. Key Stage 4 Directives & Legacy Inspection

### 2.1 Backward Compatibility & Pre-Existing Bug Reporting
1. **Preserve High Quality & Docker Compatibility:** All Docker configurations and security best practices from Stage 3 must be preserved and updated to reflect the new architecture. Code coverage must strictly remain **$\ge 80\%$**.
2. **Pre-Existing Error Detection Protocol:** Before performing the RPN refactor, the AI agent/developer **MUST audit the existing repository (Stages 1–3)**. Any identified bugs, architectural flaws, or test coverage gaps must be documented and reported before executing the migration.

---

## 3. Core Functional Requirements (Stage 4 Extensions)

### 3.1 Core Engine Refactor to RPN (Reverse Polish Notation)
- **RPN Parser & Stack Evaluator Engine:** Re-architect the core mathematical evaluation engine in the FastAPI backend to parse expressions using the **Shunting Yard Algorithm** to convert user inputs into Postfix/RPN tokens, and evaluate them via a dedicated stack-based execution engine.
- **Preserve High-Precision Math:** Ensure that all stack push/pop operations maintain exact decimal precision (`Decimal` logic established in Stage 1) without converting values to floating-point representation.
- **Scientific RPN Execution:** Extend stack evaluation to support all scientific operators, memory registers, and functions introduced in Stage 2 (e.g., pushing operands to stack, applying unary functions like $\sin$, $\ln$, $\sqrt{x}$, and binary operators).

### 3.2 UI & Mode Adaptation for RPN
- **RPN / Standard Dual Mode:** Update the React UI to accommodate RPN input workflows (e.g., dedicated `ENTER` key for pushing values to the stack, displaying active stack levels $X, Y, Z, T$, or dynamically converting standard mathematical expressions to RPN postfix representation).
- **Stack Display:** Add a visual indicator/view showing the current state of the evaluation stack in real-time.

---

## 4. Non-Functional & Testing Requirements

### 4.1 Test Suite Refactoring & Maintenance ($\ge 80\%$ Coverage)
- **Unit Test Migration:** Update and refactor backend and frontend test suites to validate RPN tokenization, stack push/pop operations, stack operator evaluation, and error handling (e.g., stack underflow, insufficient operands).
- **Coverage Enforcement:** Ensure total repository statement and branch code coverage remains strictly at or above **80%**.
- **Docker Verification:** Ensure that both backend and frontend Docker containers build and run cleanly under the new RPN engine architecture.

---

## 5. Instructions for AI Agents
1. **Step 1 — Legacy Code Audit:** Perform an inspection of Stages 1–3. Document any bugs, edge case defects, or test gaps in an initial report before starting the migration.
2. **Step 2 — RPN Engine Refactor:** Rewrite the backend evaluation engine to utilize Shunting Yard conversion and stack-based RPN evaluation while keeping high-precision decimal operations intact.
3. **Step 3 — UI & Stack Visualizer Updates:** Update React frontend interfaces to support RPN stack operations, visual stack displays, and `ENTER` key actions.
4. **Step 4 — Test Refactoring & Container Verification:** Refactor unit test suites to reflect RPN execution rules, verify that overall code coverage remains $\ge 80\%$, and confirm clean build and execution inside the Docker environment.