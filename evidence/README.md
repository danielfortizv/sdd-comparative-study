# Evidence

This directory stores experiment evidence organized by case study, development stage, and SDD tool. Place each artifact in the folder for the implementation it documents.

```text
evidence/
└── <case study>/
    └── <development stage>/
        └── <tool>/
            ├── prompt_logs/
            ├── screenshots/
            └── metrics/
```

The directory names are `Calculadora`, `Tetris`, `E-commerce`, and `Shift-Bank`; `Etapa 1` through `Etapa 4`; and `OpenSpec`, `Spec Kit`, `Tessl`, `Bmad Method`, and `Kiro`.

## Evidence Categories

- **`prompt_logs/`** stores the `.jsonl` transcript of the session that generated the implementation.
- **`screenshots/`** stores screenshots of Gemini CLI session statistics and the final functioning frontend.
- **`metrics/`** stores supporting metric files, such as Excel workbooks or CSV files, when the metrics cannot be obtained from the prompt logs or screenshots.

Keep evidence with the case, stage, and tool it belongs to so each implementation can be inspected independently.

Copies of this evidence are also stored in the corresponding implementation's `docs/` directory. This directory provides a centralized, consistently organized copy across cases, stages, and tools.
