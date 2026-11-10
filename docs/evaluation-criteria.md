# Evaluation Criteria

The study evaluates each tool's outputs across five dimensions. Quantitative measures are reported with their evidence sources; functional and human-feedback criteria are documented qualitatively. Metrics that a platform does not expose should be marked as unavailable rather than inferred.

## 1. Effort and Consumption

This dimension measures the computational, financial, and time resources used to transform specifications into working software.

| Measure | Definition |
| --- | --- |
| Input tokens | Tokens processed from the initial prompt and session context. |
| Cached input tokens | Input tokens served from model context cache. |
| Output tokens | Tokens generated, including code, explanations, and artifacts. |
| Session interactions | User requests, approvals, or reviews during a session. |
| Tool calls | Agent invocations of external capabilities, such as reading or writing files and running commands. |
| Agent processing time | Recorded time taken by the agent to complete assigned tasks. |
| Kiro credits | Platform-specific credits consumed by Kiro; applicable to Kiro only. |
| Estimated total cost | Derived estimate based on the available token or credit consumption data. |

For Gemini 3.5 Flash sessions, the source study estimates cost using rates of USD 1.50 per million new input tokens, USD 0.15 per million cached input tokens, and USD 9.00 per million output tokens. Since recorded input may include cached tokens, new input is calculated as total input minus cached input:

```text
Token cost = ((input tokens - cached input tokens) / 1,000,000 * 1.50)
           + (cached input tokens / 1,000,000 * 0.15)
           + (output tokens / 1,000,000 * 9.00)
```

For Kiro, the source study estimates cost at USD 0.03 per credit:

```text
Kiro cost = credits consumed * 0.03
```

These are estimates derived from the study's stated pricing assumptions. Report the underlying usage figures and assumptions with the estimate; do not present an estimate as an invoice or treat unavailable usage data as zero.

## 2. Generated Code Quality

SonarQube static analysis is used to assess the robustness, security, and maintainability of generated code. The analysis includes:

| Measure | Definition |
| --- | --- |
| Lines of code (LOC) | Number of executable source-code lines in the generated project. |
| Issues | Total SonarQube findings, also broken down into bugs, vulnerabilities, and code smells. |
| Issue density (issues/KLOC) | Issues per 1,000 lines of code. |
| Bugs | Findings that indicate a demonstrable defect or unexpected behavior. |
| Vulnerabilities | Findings that identify weaknesses that could be exploited. |
| Code smells | Maintainability problems that may increase future error risk. |
| Technical debt | SonarQube's estimated effort to remediate detected issues. |
| Duplication | Percentage of source-code lines duplicated in the project. |
| Cognitive complexity | Measure of the difficulty of understanding the code's control flow. |
| Ratings | SonarQube ratings, generally from A to E, for security, reliability, and maintainability. |
| Code coverage | Percentage of source code executed by automated test suites. |
| Added and deleted LOC | New and removed lines used to describe code evolution from Stage 2 onward. |

Coverage is reported as a quality measure, with its project scope identified. Comparisons should use consistent analysis scopes and distinguish inherited findings from newly introduced findings where that information is available.

## 3. Specifications and Documentation

This dimension examines Markdown documentation intended to provide context to the AI agent, including how much specification is produced and how it relates to the implementation.

| Measure | Definition |
| --- | --- |
| Markdown file count | Number of specification `.md` files generated or maintained by the tool. |
| Specification lines | Total lines across the specification Markdown files. |
| Average document density | Total specification lines divided by the number of specification files, in lines per file. |
| Code-to-specification ratio | Source-code LOC relative to specification lines. |
| Requirement count | Total explicitly specified functional and non-functional requirements. |
| Requirements per 100 documentation lines (Req/CLOD) | Requirement count normalized to each 100 lines of Markdown documentation. |
| Per-file volume distribution | The line volume of each document, used to examine how documentation is distributed across files. |

The document set should be scoped to agent-facing Markdown specifications. Other project documentation should not be included unless it serves that role in the tool's workflow. These measures describe document volume and structure; they do not, by themselves, establish specification quality.

## 4. Functional Expectations

This qualitative dimension compares each implementation and its specifications with the intentions in the applicable seed. It covers both requested functionality and unrequested additions.

For each implementation, record:

- **Minimum expected aspects:** the essential features implied by the seed.
- **Fulfillment status:** whether each expected aspect was implemented (`fulfilled` or `not fulfilled`).
- **Fulfillment rationale:** evidence-based explanation of why the aspect was or was not achieved.
- **Additional aspects:** functionality, configuration, or logic not explicitly requested in the seed.
- **Additional-aspect classification:** whether each addition provides **support** to the system or is **redundant** and potentially harmful.
- **Classification rationale:** explanation of the addition's actual impact on project behavior or architecture.

The same case- and stage-specific expectations should be applied across tools. A feature's presence alone is not sufficient to classify an unrequested addition as beneficial; the rationale should explain its impact.

## 5. Human Feedback

This qualitative dimension records researcher-observed problems specifically related to creating, structuring, or modifying project specifications with a tool.

For each issue, record:

- **Issue:** the specific error, misunderstanding, or anomalous behavior.
- **Relevance:** severity classified as **minor**, **medium**, or **high**, based on the obstacle's impact and whether it compromised design integrity.
- **Explanation:** the context, possible cause, effect on the workflow, and impact on confidence in the tool.

Separate observed behavior from hypotheses about why it occurred. Preserve enough session or artifact evidence to make each observation traceable.
