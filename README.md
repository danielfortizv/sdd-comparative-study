# Comparative Study of Spec-Driven Development in AI-Assisted Software Engineering

Repository for an undergraduate thesis at Universidad de los Andes comparing five approaches to Spec-Driven Development (SDD) in AI-assisted software engineering:

- OpenSpec
- GitHub Spec Kit
- Tessl
- BMad Method
- Kiro + AI-DLC

## Purpose

This repository is the reproducible evidence base for the study. It will preserve the requirements, prompts, native tool artifacts, generated code, tests, execution records, observations, and other evidence needed to compare the approaches under equivalent conditions.

The Tetris case is organized under [`Tetris/`](Tetris/README.md), with separate [`Etapa 1`](Tetris/Etapa%201/README.md) and [`Etapa 2`](Tetris/Etapa%202/README.md) directories. Each stage contains independent OpenSpec, GitHub Spec Kit, Tessl, BMad Method, and Kiro implementations, native specifications, tests, measured metrics, and SonarQube evidence. The Stage 2 report includes an advisor script, the Tetris thesis extract, charts, screenshots, and records for 49 invocation attempts. Other cases retain their own case directories.

## Scenarios

- **Greenfield:** the tool starts from an approved case description without an existing application codebase.
- **Brownfield:** the tool works with an approved existing repository and must account for its current structure, behavior, and constraints.

The final cases are pending approval. The placeholders in [`cases/`](cases/) must be completed before the first experiment.

## Repository Structure

| Path | Purpose |
| --- | --- |
| [`docs/`](docs/) | Methodology, criteria, reproducibility guidance, and experiment metadata template. |
| [`cases/`](cases/) | Approved or pending greenfield and brownfield case definitions. |
| [`Tetris/`](Tetris/README.md) | Tetris case, organized by stage and then by the five tools, with shared protocol and reports. |
| [`prompts/`](prompts/) | Exact prompts and prompt-use records. |
| [`evidence/`](evidence/) | Screenshots, logs, and metrics captured during execution. |
| [`results/`](results/) | Evidence-based observations and comparison templates. |

## Reproducibility Goal

Each experiment should be repeatable from the same functional requirements, acceptance criteria, initial repository state, tool and model versions, environment, and evaluation procedure. Previous evidence must remain immutable and traceable to the commits and prompts that produced it. See [`docs/reproducibility.md`](docs/reproducibility.md).

## Status

**Work in progress.** Tetris has verified Stage 1 and Stage 2 snapshots. Stage 1 provenance remains in [`Tetris/Etapa 1/PROGRESS.md`](Tetris/Etapa%201/PROGRESS.md); Stage 2 results, limitations, and the publication scope are documented in [`Tetris/Etapa 2/README.md`](Tetris/Etapa%202/README.md). Final cross-case conclusions are not yet established.

> **Important:** Do not treat empty templates or pending placeholders as experimental evidence. Add evidence only after an experiment has actually been executed.
