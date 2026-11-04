# Project Seed (Stage 3): Architecture, Security, Testing Quality & Containerization

## 1. Executive Summary & Intent
The objective of **Stage 3** is to enforce Non-Functional Requirements (NFRs), security, complete testing suites, and containerization onto the Scientific Web Calculator project built in previous stages. 

This stage introduces complete unit test suites targeting critical mathematical edge cases and multi-container Docker packaging to ensure seamless continuous integration. From this stage onward, **code coverage must strictly meet or exceed 80%** across all repository layers.

---

## 2. Key Stage 3 Directives & Legacy Inspection

### 2.1 Backward Compatibility & Pre-Existing Bug Reporting
1. **Preserve Legacy Features:** All functional operations from Stage 1 (Basic Arithmetic) and Stage 2 (Scientific Functions, Memory, and Session History) must remain fully operational.
2. **Pre-Existing Error Detection Protocol:** Before introducing Stage 3 architectural changes, the AI agent/developer **MUST inspect the existing codebase (Stages 1 & 2)**. Any discovered bugs, mathematical inaccuracies, state leakage, or unhandled edge cases must be explicitly reported/documented before applying fixes and new additions.

### 2.2 Quality & Coverage Threshold
- **Code Coverage Requirement ($\ge 80\%$):** Automated unit and integration test suites must achieve **$\ge 80\%$ statement and branch code coverage** across both the FastAPI backend and React/TypeScript frontend.

---

## 3. Core Requirements (Stage 3 Extensions)

### 3.1 Comprehensive Unit & Edge Case Testing
- **Edge Case Coverage:** Implement exhaustive unit tests specifically targeting critical calculation edge cases, including:
  - Division by zero and modulo zero handling.
  - Invalid trigonometric domains (e.g., $\arcsin(x)$ for $\vert{}x\vert{} > 1$).
  - Negative values in logarithms or square roots.
  - Overflow/underflow condition handling and invalid syntax sequences.
- **Frontend Component & State Testing:** Add test suites covering input handling, memory state operations, keyboard events, and history rendering.

### 3.2 Containerization & Dockerization
- **Backend Dockerfile:** Create a multi-stage production Dockerfile for the Python FastAPI application adhering to container security best practices (non-root execution, minimal base image).
- **Frontend Dockerfile:** Create a production Dockerfile for the React/TypeScript frontend using Nginx for efficient static asset serving and client-side routing.
- **Orchestration:** Provide a `docker-compose.yml` file configuring multi-container setup for local development and unified service orchestration.

---

## 4. Instructions for AI Agents
1. **Step 1 — Code Inspection & Audit:** Inspect the codebase from Stages 1 and 2. Report any bugs, edge case omissions, or refactoring needs in an audit log prior to writing code.
2. **Step 2 — Comprehensive Test Suite ($\ge 80\%$ Coverage):** Write backend (`pytest`, `pytest-cov`) and frontend (`vitest`/`jest`) test suites covering standard functionality and all defined mathematical edge cases to fulfill the $\ge 80\%$ code coverage requirement.
3. **Step 3 — Containerization:** Generate production-ready `Dockerfile` definitions for both backend and frontend, along with a top-level `docker-compose.yml`.