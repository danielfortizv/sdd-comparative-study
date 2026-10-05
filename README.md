# Comparative Study of Spec-Driven Development in AI-Assisted Software Engineering

Repository for an undergraduate thesis at Universidad de los Andes comparing five approaches to Spec-Driven Development (SDD) in AI-assisted software engineering:

- OpenSpec
- GitHub Spec Kit
- Tessl
- BMad Method
- Kiro + AI-DLC

## Purpose

This repository is the reproducible evidence base for the study. It will preserve the requirements, prompts, native tool artifacts, generated code, tests, execution records, observations, and other evidence needed to compare the approaches under equivalent conditions.

The repository now includes the completed Tetris Stage 1, option A snapshot under [`Tetris/Etapa 1`](Tetris/Etapa%201/). It contains separate OpenSpec, GitHub Spec Kit, Tessl, BMad Method, and Kiro implementations, their native specifications, tests, and recorded SonarQube evidence. Other cases and later stages remain in progress.

## Scenarios

- **Greenfield:** the tool starts from an approved case description without an existing application codebase.
- **Brownfield:** the tool works with an approved existing repository and must account for its current structure, behavior, and constraints.

The final cases are pending approval. The placeholders in [`cases/`](cases/) must be completed before the first experiment.

## Repository Structure

| Path | Purpose |
| --- | --- |
| [`docs/`](docs/) | Methodology, criteria, reproducibility guidance, and experiment metadata template. |
| [`cases/`](cases/) | Approved or pending greenfield and brownfield case definitions. |
| [`openspec/`](openspec/), [`speckit/`](speckit/), [`tessl/`](tessl/), [`bmad/`](bmad/), [`kiro/`](kiro/) | Native artifacts produced by each approach, organized by scenario. |
| [`prompts/`](prompts/) | Exact prompts and prompt-use records. |
| [`evidence/`](evidence/) | Screenshots, logs, and metrics captured during execution. |
| [`results/`](results/) | Evidence-based observations and comparison templates. |

## Reproducibility Goal

Each experiment should be repeatable from the same functional requirements, acceptance criteria, initial repository state, tool and model versions, environment, and evaluation procedure. Previous evidence must remain immutable and traceable to the commits and prompts that produced it. See [`docs/reproducibility.md`](docs/reproducibility.md).

## Status

**Work in progress.** Tetris Stage 1 has an initial verified snapshot. Its measurements, assumptions, gaps, and supporting evidence are documented in [`Tetris/Etapa 1/PROGRESS.md`](Tetris/Etapa%201/PROGRESS.md) and the case report. Other cases, later stages, and any cross-case conclusions are not yet finalized.

> **Important:** Do not treat empty templates or pending placeholders as experimental evidence. Add evidence only after an experiment has actually been executed.
