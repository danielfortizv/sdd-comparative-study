# Methodology

## Study Design

This empirical study compares five Spec-Driven Development (SDD) approaches: OpenSpec, GitHub Spec Kit, Tessl, BMad Method, and Kiro. The comparison uses four web application case studies with increasing architectural, technical, and security demands:

- **Calculator:** a basic client-server application that establishes a baseline for setup overhead and simple communication between a React interface and a FastAPI API.
- **Tetris:** an interactive application involving continuous state, asynchronous user events, and dynamic rendering, with increasingly complex game behavior.
- **E-commerce:** a data-oriented application involving relational persistence, multiple entities, CRUD operations, sessions, and an interactive shopping cart.
- **Banking system:** a security-critical application involving financial transaction integrity, concurrency, role-based access control, and vulnerability prevention.

The common application architecture is a Python backend built with FastAPI and a TypeScript frontend built with React. The cases evolve through a four-stage lifecycle. Shared Markdown seeds define the requirements for each case and stage and are organized under [`seeds/`](../seeds/) by stage and case; each tool receives the same applicable seed to standardize its input.

## Development Stages

1. **Initialization (greenfield):** Build the initial architecture and core functionality from scratch, without legacy code.
2. **Complexification (initial brownfield):** Add requirements to the existing implementation and assess whether the tool updates its specifications coherently while preserving baseline behavior.
3. **Operations and architecture:** Mature the project with operational and quality assurance concerns, including deployment infrastructure, container configuration, pipelines, and automated test suites.
4. **Migration and disruption:** Apply a substantial or unexpected change to the consolidated system to examine whether the tool can preserve consistency and integrity between specifications and code under structural stress.

A change-control matrix records the scope and instructions for the iterations. Each stage builds on the preceding project state, except that Stage 1 begins without a legacy codebase.

## Experimental Conditions

The study follows each tool's standard SDD workflow, without advanced optimizations, custom skills, or platform-specific enhancements. This evaluates the tools as encountered by developers using their basic workflows. The language model is standardized as Gemini 3.5 Flash for tools that allow model selection. Kiro is evaluated in its default Auto mode because its underlying model cannot be configured.

The resulting projects are assessed with SonarQube for static code analysis. Tool and model configuration, environment details, and the analysis setup are recorded with the corresponding experiment evidence so that results can be interpreted in context.

## Experimental Procedure

For each case, stage, and tool:

1. Start from the applicable shared seed and the prescribed project state for that stage.
2. Run the tool using its standard SDD workflow and preserve its native specifications and other workflow artifacts.
3. Record the generated or modified code, tests, interaction evidence, tool usage, elapsed time, and relevant human interventions.
4. Analyze the resulting implementation and artifacts using the evaluation dimensions in [`evaluation-criteria.md`](evaluation-criteria.md).
5. Preserve the evidence and document limitations or unavailable measurements alongside the observations.

The analysis combines quantitative measures from tool sessions, project artifacts, and static analysis with qualitative reviews of functional outcomes and researcher experience. Comparisons should be grounded in the preserved evidence and interpreted in light of differences in what each platform exposes or permits measuring.
