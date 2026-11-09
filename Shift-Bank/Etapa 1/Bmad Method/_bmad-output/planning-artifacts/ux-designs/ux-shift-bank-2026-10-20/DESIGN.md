---
name: Shift Bank
description: Visual design specification and token dictionary for Shift Bank Stage 1 retail banking web application.
sources:
  - _bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/prd.md
  - _bmad-output/planning-artifacts/prds/prd-shift-bank-2026-10-20/addendum.md
status: final
updated: 2026-10-20
colors:
  primary: '#0A2540'
  primary-foreground: '#FFFFFF'
  primary-hover: '#081D33'
  accent: '#00D4B2'
  accent-foreground: '#0A2540'
  accent-hover: '#00BA9C'
  background: '#F8FAFC'
  foreground: '#0F172A'
  surface: '#FFFFFF'
  surface-card: '#FFFFFF'
  surface-card-active: '#F1F5F9'
  border: '#E2E8F0'
  border-focus: '#0A2540'
  border-active-card: '#0A2540'
  muted: '#64748B'
  muted-foreground: '#64748B'
  muted-surface: '#F1F5F9'
  success: '#059669'
  success-surface: '#ECFDF5'
  success-foreground: '#065F46'
  warning: '#D97706'
  warning-surface: '#FFFBEB'
  warning-foreground: '#92400E'
  destructive: '#DC2626'
  destructive-surface: '#FEF2F2'
  destructive-foreground: '#991B1B'
  credit: '#059669'
  debit: '#0F172A'
typography:
  display:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    fontSize: '28px'
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: '-0.02em'
  heading-lg:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    fontSize: '20px'
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: '-0.01em'
  heading-md:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    fontSize: '16px'
    fontWeight: '600'
    lineHeight: '1.4'
  body:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    fontSize: '14px'
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    fontSize: '12px'
    fontWeight: '400'
    lineHeight: '1.4'
  mono-balance:
    fontFamily: 'ui-monospace, "SF Mono", Menlo, Consolas, monospace'
    fontSize: '24px'
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: '-0.01em'
  mono-amount:
    fontFamily: 'ui-monospace, "SF Mono", Menlo, Consolas, monospace'
    fontSize: '14px'
    fontWeight: '600'
    lineHeight: '1.4'
rounded:
  sm: '4px'
  md: '8px'
  lg: '12px'
  full: '9999px'
spacing:
  xs: '4px'
  sm: '8px'
  md: '16px'
  lg: '24px'
  xl: '32px'
  xxl: '48px'
components:
  account-card:
    background: '{colors.surface}'
    border: '1px solid {colors.border}'
    border-selected: '2px solid {colors.border-active-card}'
    radius: '{rounded.lg}'
    padding: '{spacing.lg}'
  balance-display:
    font: '{typography.mono-balance}'
    color: '{colors.foreground}'
  transfer-panel:
    background: '{colors.surface}'
    border: '1px solid {colors.border}'
    radius: '{rounded.lg}'
    padding: '{spacing.lg}'
  button-primary:
    background: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
    radius: '{rounded.md}'
    font: '{typography.body}'
    padding: '10px 18px'
  button-secondary:
    background: '{colors.surface}'
    foreground: '{colors.foreground}'
    border: '1px solid {colors.border}'
    radius: '{rounded.md}'
    padding: '10px 18px'
  input-field:
    background: '{colors.surface}'
    border: '1px solid {colors.border}'
    radius: '{rounded.md}'
    padding: '10px 14px'
    font: '{typography.body}'
  otp-input-box:
    width: '44px'
    height: '52px'
    font: '{typography.heading-lg}'
    radius: '{rounded.md}'
    border: '1px solid {colors.border}'
    border-focus: '2px solid {colors.primary}'
  modal-dialog:
    background: '{colors.surface}'
    radius: '{rounded.lg}'
    border: '1px solid {colors.border}'
    padding: '{spacing.xl}'
    shadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)'
  movement-row:
    border-bottom: '1px solid {colors.border}'
    padding: '{spacing.md} 0'
  empty-state:
    padding: '{spacing.xxl}'
    radius: '{rounded.lg}'
    background: '{colors.surface}'
    border: '1px dashed {colors.border}'
---

# Shift Bank — Visual Design Specification

## Brand & Style

Shift Bank is a modern digital banking portal engineered for financial precision and customer trust. The visual tone is institutional yet agile: clean lines, generous breathing room, high text contrast, and an absence of decorative gimmickry. The visual design conveys stability, transparency, and authoritative operational correctness.

Every balance, movement amount, and timestamp is presented with exact typographic hierarchy, ensuring numbers can be parsed at a glance with zero ambiguity. The user interface favors sober navy and slate tones with purposeful accents of cyan and emerald for positive financial states.

## Colors

The color palette is built for high-contrast legibility and financial semantics:

- **Primary Navy (`{colors.primary}`)**: `#0A2540`. The anchor color for headers, key callouts, primary buttons, and selected account states. Delivers authority and calm reliability.
- **Action Cyan (`{colors.accent}`)**: `#00D4B2`. Used selectively for high-visibility highlights, active indicators, and interactive cues.
- **Background & Surface (`{colors.background}`, `{colors.surface}`)**: Light neutral foundation (`#F8FAFC` canvas, pure `#FFFFFF` cards) ensuring clear visual container boundaries.
- **Semantic Financial States**:
  - **Credit Inflow (`{colors.credit}`)**: Emerald Green (`#059669`) with light green badge background (`#ECFDF5`). Communicates monetary addition.
  - **Debit Outflow (`{colors.debit}`)**: Deep Slate (`#0F172A`). Neutral, non-alarmist debit display that reserves red exclusively for destructive errors.
  - **Warning & Pending (`{colors.warning}`)**: Amber (`#D97706`) with warm tint (`#FFFBEB`). Used for MFA expiration countdowns and warning callouts.
  - **Destructive & Error (`{colors.destructive}`)**: Crimson (`#DC2626`). Used for transfer rejection banners, exhausted MFA attempts, and field validation errors.

All text and interactive color pairings achieve WCAG 2.1 AA minimum contrast (4.5:1 for body copy, 3:1 for large display headers and icons).

## Typography

Typography is set in **Inter** for UI labels, interactive controls, and editorial text, paired with **system monospace** for monetary quantities:

- **Display (`{typography.display}`)**: 28px bold Inter for dashboard page titles and modal headlines.
- **Heading Large (`{typography.heading-lg}`)**: 20px semi-bold for section headers (Account Portfolio, Transfer Money, Transaction History).
- **Heading Medium (`{typography.heading-md}`)**: 16px semi-bold for account nicknames and modal subheads.
- **Body & Small (`{typography.body}`, `{typography.body-sm}`)**: 14px / 12px for form labels, descriptions, and metadata.
- **Tabular Figures (`{typography.mono-balance}`, `{typography.mono-amount}`)**: Uses monospace / tabular numerals (`font-variant-numeric: tabular-nums`). This prevents layout jitter during balance updates and guarantees columnar alignment across the movement ledger.

## Layout & Spacing

Shift Bank employs an 8pt grid with 4pt micro-increments:
- `{spacing.xs}` (4px), `{spacing.sm}` (8px), `{spacing.md}` (16px), `{spacing.lg}` (24px), `{spacing.xl}` (32px), `{spacing.xxl}` (48px).

### Grid Structure
- **Max Container Width**: 1280px, horizontally centered with 24px gutter padding.
- **Top Bar**: Fixed 64px height containing Shift Bank logo, environment indicator ("Stage 1 Sandbox"), and customer avatar/name badge ("Alex Morgan").
- **Account Summary Grid**: 3-column responsive card grid (`repeat(auto-fit, minmax(280px, 1fr))`) positioned at the top of the viewport.
- **Core Workspace (2 Columns)**:
  - **Left Pane (40% width, min 380px)**: Transfer Initiation Form.
  - **Right Pane (60% width)**: Account Movement Ledger and Transaction History.

## Elevation & Depth

Depth is handled with restraint to maintain a clean editorial feel:
- **Level 0 (Flat)**: Background canvas (`{colors.background}`).
- **Level 1 (Cards)**: Default card surfaces use a 1px solid border (`{colors.border}`) with subtle flat shadow (`0 1px 3px 0 rgba(0, 0, 0, 0.05)`).
- **Level 2 (Hover/Active)**: Account cards on hover elevate with `0 4px 6px -1px rgba(0, 0, 0, 0.08)`. Selected card gains a 2px active border (`{colors.border-active-card}`).
- **Level 3 (Modals & Overlays)**: MFA Verification Modal uses an elevated shadow (`{components.modal-dialog.shadow}`) over an opaque blurred backdrop (`backdrop-filter: blur(4px); background: rgba(10, 37, 64, 0.4)`).

## Shapes

Corners are calibrated for an institutional, crisp feel:
- `{rounded.sm}` (4px): Badges, tooltips, tags.
- `{rounded.md}` (8px): Form input fields, buttons, table rows, OTP input cells.
- `{rounded.lg}` (12px): Account cards, transfer panel, modal dialog container.
- `{rounded.full}` (9999px): Status indicator dots, avatar badges.

## Components

Visual specifications for core user-facing components:

- **Account Card (`{components.account-card}`)**: Card with `{colors.surface}` background, `{rounded.lg}` corners, and 1px border. Displays account type badge, account number, large balance (`{typography.mono-balance}`), and selectable indicator ring.
- **Transfer Panel (`{components.transfer-panel}`)**: Solid white card containing source selector, destination selector, currency-formatted amount input, and primary submit button.
- **Primary Button (`{components.button-primary}`)**: Navy fill (`{colors.primary}`), white text, 8px radius. Active state darkens to `{colors.primary-hover}`. Disabled state renders at 50% opacity with `cursor: not-allowed`.
- **Secondary / Cancel Button (`{components.button-secondary}`)**: White fill, 1px slate border, dark text.
- **OTP Input Box (`{components.otp-input-box}`)**: 6 discrete monospace input cells (44px wide by 52px tall). Active cell highlights with `{colors.border-focus}` ring.
- **MFA Modal Dialog (`{components.modal-dialog}`)**: Centered dialog (max width 460px) with `{rounded.lg}` corners, security shield icon, transaction summary pill, countdown timer, OTP inputs, and action buttons.
- **Movement Table Row (`{components.movement-row}`)**: Clean table row with light border bottom. Formats date in muted text, description in medium weight, green credit tag (`+$X.XX`) or neutral debit tag (`-$X.XX`), and right-aligned running balance.
- **Empty State Container (`{components.empty-state}`)**: Centered dashed container with bank vault icon, muted headline, and explanatory copy.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Use tabular figures (`tabular-nums`) on all monetary values. | Never use proportional numbers that wobble or shift column alignment. |
| Use emerald green exclusively for credit/inflow movements and success states. | Never use random decorative green on buttons or neutral text. |
| Display negative sign (`-$150.00`) and positive sign (`+$150.00`) explicitly in ledger movements. | Never display raw unsigned numbers in movement histories. |
| Provide explicit "Cancel Transfer" affordance in the MFA modal. | Never trap the user without a clear exit route. |
| Disable the submit button immediately upon submission to prevent double clicks. | Never allow multiple un-debounced transfer submissions. |
