# Comparative Study of Spec-Driven Development in AI-Assisted Software Engineering

Repository for an undergraduate thesis at Universidad de los Andes comparing five approaches to Spec-Driven Development (SDD) in AI-assisted software engineering:

- OpenSpec
- GitHub Spec Kit
- Tessl
- BMad Method
- Kiro + AI-DLC

## Purpose

This repository preserves the case implementations, shared seeds, tool artifacts, generated code, tests, execution evidence, and research documents for an exploratory comparison of SDD approaches. It records specific experimental runs; it does not claim that LLM-generated outputs can be reproduced exactly.

The four case studies have overviews and run instructions in their case directories: [`Calculator`](Calculadora/README.md), [`Tetris`](Tetris/README.md), [`E-commerce`](E-commerce/README.md), and [`Banking System`](Shift-Bank/README.md). Implementations are grouped by development stage and SDD tool, with shared artifacts kept alongside the relevant case where applicable.

## Scenarios

- **Greenfield:** the tool starts from an approved case description without an existing application codebase.
- **Brownfield:** the tool works with an approved existing repository and must account for its current structure, behavior, and constraints.

Stage 1 represents greenfield initialization; later stages evolve an existing implementation and therefore introduce brownfield changes.

## Repository Structure

| Path | Purpose |
| --- | --- |
| [`docs/`](docs/) | Academic-document descriptions, methodology, evaluation criteria, and study scope. |
| [`Tetris/`](Tetris/README.md) | Tetris case, organized by stage and then by the five tools, with shared protocol and reports. |
| [`seeds/`](seeds/) | Shared seed inputs organized by development stage and case study. |
| [`evidence/`](evidence/) | Session transcripts, screenshots, and supporting metric files organized by case, stage, and tool. |

## Interpretation of Results

Shared seeds and documented conditions support traceability and comparison, but LLM nondeterminism, limited repeated runs, and platform differences—particularly Kiro's inaccessible underlying model—make this an exploratory study rather than an exact or fully reproducible experiment. See [`docs/reproducibility.md`](docs/reproducibility.md).
