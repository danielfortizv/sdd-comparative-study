# Seeds

This directory stores the seed used for each case study at each development stage. Each seed defines the initial requirements provided to every tool implementation and serves as its starting prompt. The seed content is shared across implementations; it may be adapted to the workflow and command syntax of each SDD tool without changing the requirements being evaluated.

Seeds are organized first by development stage and then by case study:

```text
seeds/
├── Etapa 1/
│   ├── Calculadora/
│   ├── Tetris/
│   ├── E-commerce/
│   └── Shift-Bank/
├── Etapa 2/
├── Etapa 3/
└── Etapa 4/
```

Other prompts and the interaction flows used with each tool are preserved in [`evidence/`](../evidence/). That directory documents the prompts and tool interactions beyond the initial seed.
