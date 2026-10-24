import "./MemoryIndicator.css";

/**
 * Props for {@link MemoryIndicator}.
 *
 * This is a presentational ("dumb") component: it owns no state and performs no
 * arithmetic or zero-check. The Calculator container (task 35.3) derives the
 * `active` flag by calling `isMemoryActive(memoryState)` from
 * `state/memoryReducer.ts` (which performs the exact decimal-string, non-float
 * zero-check) and passes the boolean down. The indicator is shown iff the
 * Memory_Register is non-zero (Requirements 20.6, 20.7).
 */
export interface MemoryIndicatorProps {
  /**
   * Whether the Memory_Register currently holds a non-zero value. The container
   * computes this via `isMemoryActive(memoryState)` — do NOT derive it here with
   * `parseFloat`/`Number`, so no float ever enters the zero-check path.
   */
  active: boolean;
}

/**
 * A small "M" badge signalling that the Memory_Register holds a stored value.
 *
 * - Renders the badge only while `active` is `true` (Requirement 20.6); returns
 *   `null` to render nothing when the register is zero (Requirement 20.7).
 * - Accessibility: the badge is a status element. It carries `role="status"`
 *   with `aria-live="polite"` so assistive technologies announce when memory
 *   becomes active without interrupting, and an `aria-label` describing the
 *   state in words rather than relying on the bare letter "M".
 * - Contrast: styling lives in `MemoryIndicator.css`, hooked to the shared
 *   theme tokens; the badge boundary/graphic stays >= 3:1 (Requirement 11.3).
 */
export function MemoryIndicator({ active }: MemoryIndicatorProps) {
  // Show iff the register is non-zero (Requirements 20.6/20.7).
  if (!active) {
    return null;
  }

  return (
    <span
      className="memory-indicator"
      role="status"
      aria-live="polite"
      aria-label="Memory contains a stored value"
    >
      M
    </span>
  );
}

export default MemoryIndicator;
