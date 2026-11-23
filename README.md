# Comparative Study of Spec-Driven Development in AI-Assisted Software Engineering

Repository for an undergraduate thesis at Universidad de los Andes comparing five approaches to Spec-Driven Development (SDD) in AI-assisted software engineering.

## SDD Approaches

- OpenSpec
- GitHub Spec Kit (stored in implementation directories as `Spec Kit`)
- Tessl
- BMad Method
- Kiro

## Purpose

This repository preserves the case implementations, shared seeds, tool artifacts, generated code, tests, execution evidence, and research documents for an exploratory comparison of SDD approaches. It records specific experimental runs and does not claim that LLM-generated outputs can be reproduced exactly.

## Repository Structure

| Path | Contents |
| --- | --- |
| [`Calculadora/`](Calculadora/) | Calculator case implementations across Etapas 1-4. See the [case overview](Calculadora/README.md). |
| [`E-commerce/`](E-commerce/) | E-commerce case implementations across Etapas 1-4. |
| [`Shift-Bank/`](Shift-Bank/) | Banking case implementations across Etapas 1-4. See the [case overview](Shift-Bank/README.md). |
| [`Tetris/`](Tetris/) | Tetris case implementations across Etapas 1-4. See the [case overview](Tetris/README.md). |
| [`docs/`](docs/) | [Study methodology](docs/methodology.md), [evaluation criteria](docs/evaluation-criteria.md), and [reproducibility documentation](docs/reproducibility.md), including the shared change-control matrix. |
| [`seeds/`](seeds/) | Shared seed inputs organized by development stage and case study; see the [seeds README](seeds/README.md). |
| [`evidence/`](evidence/) | Prompt logs, screenshots, video recordings, and supporting metrics organized by case, stage, and tool; see the [evidence README](evidence/README.md). |
| [`package.json`](package.json), [`package-lock.json`](package-lock.json) | Shared JavaScript dependencies and their lockfile. |

Budget limitations prevented some case studies from completing planned BMad Method implementations at different stages. As a result, BMad Method is absent from some case-stage combinations. All four case directories contain implementations organized across Etapas 1-4; tool coverage varies by case and stage.

## Interpretation of Results

Shared seeds and documented conditions support traceability and comparison, but LLM nondeterminism, limited repeated runs, and platform differences, particularly Kiro's inaccessible underlying model, make this an exploratory study rather than an exact or fully reproducible experiment. See [`docs/reproducibility.md`](docs/reproducibility.md).
