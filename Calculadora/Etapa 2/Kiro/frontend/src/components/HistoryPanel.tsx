import type { CalculationHistory } from "../api/types";
import { isHistoryEmpty } from "../state/historyReducer";
import { CalcButton } from "./CalcButton";
import "./HistoryPanel.css";

/**
 * Props for {@link HistoryPanel}.
 *
 * Presentational component: the Calculator container (task 35.3) owns the
 * Calculation_History state (via `historyReducer`) and the selection logic. This
 * panel only renders the entries it is handed and routes activations to the
 * supplied callbacks; it holds no state and performs no arithmetic.
 */
export interface HistoryPanelProps {
  /**
   * The session Calculation_History, already ordered newest-first by the
   * reducer. The panel renders it in the given order (Requirement 21.2).
   */
  history: CalculationHistory;
  /**
   * Loads the selected entry's expression into the current expression
   * (Requirement 21.3). Called with the entry's `expression` string.
   */
  onSelectExpression: (expression: string) => void;
  /**
   * Loads the selected entry's result into the current expression
   * (Requirement 21.4). Called with the entry's `result` string.
   */
  onSelectResult: (result: string) => void;
  /** Clears the entire Calculation_History (Requirement 21.6). */
  onClear: () => void;
}

/**
 * A side panel listing the session's completed calculations.
 *
 * - Rendered as an `<aside role="complementary">` with an accessible name
 *   "calculation history" so assistive technologies can locate the region.
 * - Lists entries newest-first in the order supplied (Requirement 21.2).
 * - For each entry the expression and the result are two INDEPENDENTLY
 *   selectable controls: activating the expression calls
 *   {@link HistoryPanelProps.onSelectExpression}; activating the result calls
 *   {@link HistoryPanelProps.onSelectResult} (Requirements 21.3, 21.4). Both
 *   reuse {@link CalcButton}, inheriting its visible-label + matching-aria-label
 *   and focus/pressed states (Requirements 11.6, 12.1, 12.2).
 * - A Clear History control calls {@link HistoryPanelProps.onClear}
 *   (Requirement 21.6); it is disabled when the history is empty.
 * - When the history is empty an empty-state message is shown instead of the
 *   list (Requirement 21.8).
 *
 * List keys: history entries can duplicate (the same expression/result pair can
 * recur), so there is no stable natural key. The list is append-only and capped
 * (MAX_HISTORY), and entries are never reordered in place, so the array index is
 * an acceptable, stable-enough key here. Contrast/responsive drawer behavior is
 * finalized by the styling task (task 36).
 */
export function HistoryPanel({
  history,
  onSelectExpression,
  onSelectResult,
  onClear,
}: HistoryPanelProps) {
  const empty = isHistoryEmpty(history);

  return (
    <aside
      className="history-panel"
      role="complementary"
      aria-label="calculation history"
    >
      <div className="history-panel__header">
        <h2 className="history-panel__title">History</h2>
        {/*
         * Native <button> (not CalcButton) for Clear History because it must be
         * `disabled` when the history is empty (Requirement 21.8), and the Stage 1
         * CalcButton API does not forward a `disabled` prop. It mirrors
         * CalcButton's pattern (native button, visible label + matching
         * aria-label, shared `calc-button` classes so focus/pressed states are
         * inherited) per Requirements 11.6, 12.1, 12.2, 21.6.
         */}
        <button
          type="button"
          className="calc-button calc-button--action history-panel__clear"
          aria-label="clear history"
          onClick={onClear}
          disabled={empty}
        >
          Clear
        </button>
      </div>

      {empty ? (
        <p className="history-panel__empty">No calculations yet.</p>
      ) : (
        <ul className="history-panel__list">
          {history.map((entry, index) => (
            <li key={index} className="history-panel__item">
              <CalcButton
                label={entry.expression}
                ariaLabel={`Load expression ${entry.expression}`}
                variant="digit"
                className="history-panel__expression"
                onActivate={() => onSelectExpression(entry.expression)}
              />
              <CalcButton
                label={`= ${entry.result}`}
                ariaLabel={`Load result ${entry.result}`}
                variant="operator"
                className="history-panel__result"
                onActivate={() => onSelectResult(entry.result)}
              />
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

export default HistoryPanel;
