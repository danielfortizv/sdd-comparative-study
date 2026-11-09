---
title: 'Story 1.3: Responsive Account Portfolio Grid & Selection UI'
type: 'feature'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '_bmad-output/planning-artifacts/architecture/architecture-shift-bank-2026-10-20/ARCHITECTURE-SPINE.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-shift-bank-2026-10-20/DESIGN.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-shift-bank-2026-10-20/EXPERIENCE.md'
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Retail customer Alex Morgan needs an intuitive, high-contrast dashboard overview to view their 3 accounts with exact tabular balances and select an active account for subsequent banking actions.

**Approach:** Implement `Navbar`, `AccountCard`, and `AccountGrid` components in React 18 with TypeScript, integrate with the existing `GET /api/accounts` endpoint via a dedicated API client injecting `X-Customer-Id: cust_mock_001`, manage active selection in `useAccounts`, enforce WCAG 2.1 AA keyboard accessibility, and verify with Vitest and React Testing Library.

## Boundaries & Constraints

**Always:**
- Format balances with tabular figures (`.tabular-nums`) to prevent layout jitter (`UX-DR-1`, `AD-1`).
- Display all 3 pre-seeded accounts: Primary Checking, High-Yield Savings, Emergency Reserve (`FR-1`, `AD-8`).
- Highlight active account with `{colors.border-active-card}` (2px solid Navy ring) and indicator dot (`UX-DR-3`).
- Support keyboard navigation (`Tab`, `Enter`, `Space`) with visible high-contrast focus rings (`NFR-4`).
- Integrate directly with `GET /api/accounts` with `X-Customer-Id: cust_mock_001` (`AD-4`).

**Never:**
- Never hardcode account balances in the frontend; fetch from backend API.
- Never use optimistic balance guessing (`AD-9`).
- Never modify unrelated Kiro files or experiment logs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Initial Load | App mount | Skeleton shimmer while fetching; renders 3 cards on resolution; defaults selected account to Primary Checking (`CHK-1001`) | Renders error alert if API fails |
| Card Click | Click on Savings | Updates selected account to `SAV-2001`, applies 2px solid Navy ring and accent dot | N/A |
| Keyboard Selection | Focus + `Enter` or `Space` | Selects focused account card | Prevents default page scroll on Space |
| Responsive Layout | Desktop / Tablet | Responsive CSS Grid (`repeat(auto-fit, minmax(280px, 1fr))`) | Stacks cleanly on narrow viewports |

</frozen-after-approval>

## Code Map

- `frontend/src/types/account.ts` -- TypeScript interfaces for Account and AccountType
- `frontend/src/api/client.ts` -- API client injecting `X-Customer-Id` header
- `frontend/src/hooks/useAccounts.ts` -- Hook managing accounts, loading, error, and active selection
- `frontend/src/components/AccountCard.tsx` -- Account card with masking, tabular numerals, and keyboard access
- `frontend/src/components/AccountGrid.tsx` -- Responsive 3-card grid with loading/error states
- `frontend/src/components/Navbar.tsx` -- Top navigation bar with Alex Morgan identity
- `frontend/src/App.tsx` -- Top-level assembly wiring Navbar, AccountGrid, and useAccounts
- `frontend/src/test/AccountComponents.test.tsx` -- Automated Vitest component tests

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/types/account.ts` -- Define Account model
- [x] `frontend/src/api/client.ts` -- Implement fetchAccounts with X-Customer-Id header
- [x] `frontend/src/hooks/useAccounts.ts` -- Implement state management for accounts and active selection
- [x] `frontend/src/components/AccountCard.tsx` -- Implement card with masked ID, type badge, and tabular balance
- [x] `frontend/src/components/AccountGrid.tsx` -- Implement responsive grid with loading skeletons
- [x] `frontend/src/components/Navbar.tsx` -- Implement brand header and customer profile badge
- [x] `frontend/src/App.tsx` -- Wire components to live hook state
- [x] `frontend/src/test/AccountComponents.test.tsx` -- Automated test suite verifying rendering, masking, selection, and keyboard navigation

**Acceptance Criteria:**
- Given the frontend application loads, when the dashboard initializes, then the top navigation bar displays the Shift Bank brand, the "Stage 1 Sandbox" tag, and customer badge "Alex Morgan (cust_mock_001)".
- And the account portfolio grid displays 3 cards (Primary Checking, High-Yield Savings, Emergency Reserve) formatted with account card styling and tabular numeral balances.
- And clicking an account card activates that card, applying 2px solid Navy ring and updating active account state.
- And keyboard navigation (Tab, Enter, Space) permits traversing and selecting account cards with visible focus rings complying with WCAG 2.1 AA.

## Implementation Notes

- **Components & Layout**:
  - Implemented `Navbar` displaying brand logo, Stage 1 Sandbox tag, and Alex Morgan customer badge (`UX-DR-2`).
  - Implemented `AccountCard` displaying nickname, masked number (`•••• 1001`), type badge (`CHECKING`), and tabular numeral balance (`tabular-nums`) (`UX-DR-1`).
  - Implemented `AccountGrid` providing responsive CSS grid layout (`repeat(auto-fit, minmax(280px, 1fr))`) and pulse shimmer skeleton loading states (`UX-DR-2`).
- **State & API Integration**:
  - Implemented `useAccounts` hook querying `GET /api/accounts` with `X-Customer-Id: cust_mock_001`, managing active selection and defaulting to Primary Checking on load (`AD-4`, `UX-DR-3`).
- **Accessibility & Interaction**:
  - `AccountCard` includes `role="button"`, `tabIndex={0}`, `aria-pressed`, and full keyboard navigation (`Enter`, `Space`) with high-contrast `:focus-visible` styling (`NFR-4`).
- **Automated Verification**:
  - 8 frontend unit and component tests passing via `vitest`.
  - 8 backend tests passing via `pytest`.
  - TypeScript compilation and Vite production build verified (`tsc && vite build`) with 0 errors.
