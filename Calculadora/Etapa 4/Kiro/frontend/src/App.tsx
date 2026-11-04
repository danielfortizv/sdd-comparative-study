/**
 * Application shell — the root layout container (Task 12.5).
 *
 * `App` owns no calculator state of its own. It provides a simple, accessible
 * page layout — a top-level container, a page `<h1>` title, and a `<main>`
 * landmark — and mounts the {@link Calculator} container, which owns all state
 * and wiring (Requirement 8.4). Responsive layout and the contrast-compliant
 * theme are applied separately in Task 13.
 *
 * Requirements: 8.4
 */

import Calculator from './components/Calculator';

export default function App(): JSX.Element {
  return (
    <div className="app">
      <h1>Web Calculator</h1>
      <main>
        <Calculator />
      </main>
    </div>
  );
}
