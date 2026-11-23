// Declared fixed ~5 Hz source-input pattern + key mapping (task 20.1).
//
// The harness drives REAL keyboard input via Playwright `keyboard.press`. This
// module declares the fixed pattern and the key mapping up front (design.md
// "Input pattern"; Req 26.3, 26.4, 27.12) so a trial is reproducible and every
// dispatched input's identity is known before any measured window. It performs
// NO input itself and launches nothing; it only declares data and maps names to
// keys. Input is never placed inside a polling predicate (Req 27.12) -- the
// driver reads this pattern and presses keys on its own cadence.

// The fixed declared action sequence, exactly as recorded in design.md and the
// task. Each entry is a canonical action name. The sequence exercises real
// left, right, soft-drop, clockwise, and counter-clockwise actions and keeps a
// fresh game alive without resetting.
export const DECLARED_PATTERN = Object.freeze([
  "right",
  "right",
  "right",
  "down",
  "cw",
  "left",
  "left",
  "left",
  "left",
  "left",
  "left",
  "down",
  "ccw",
  "right",
  "right",
  "right",
]);

// ~5 Hz: one source input every 200 ms. This is the SOURCE input cadence, not a
// claim about frame rate or display presentation.
export const INPUT_INTERVAL_MS = 200;

// Canonical action -> real browser key, matching the FROZEN production controls
// (frontend/src/SoloView keyboard and DuelView): left/right are
// ArrowLeft/ArrowRight, soft-drop is ArrowDown, clockwise is ArrowUp, and
// counter-clockwise is `z` (or `Z`). `hold` is included for completeness but is
// not part of the declared pattern.
export const ACTION_TO_KEY = Object.freeze({
  left: "ArrowLeft",
  right: "ArrowRight",
  down: "ArrowDown",
  cw: "ArrowUp",
  ccw: "z", // CCW accepts z or Z; the harness sends lowercase z
  hold: "c",
});

// Actions that cause a horizontal/vertical/rotation board change we treat as a
// candidate action-visible effect. `down` is soft-drop (a real move). Gravity
// is NOT an action and is never in this set.
export const MOVING_ACTIONS = Object.freeze(["left", "right", "down", "cw", "ccw"]);

// Resolve the key for a canonical action name. Returns null for an unknown
// action so the caller records it as unknown rather than pressing a wrong key.
export function keyForAction(action) {
  return Object.prototype.hasOwnProperty.call(ACTION_TO_KEY, action)
    ? ACTION_TO_KEY[action]
    : null;
}

// Produce the full ordered list of (index, action, key) inputs for a trial by
// repeating the declared pattern until `count` inputs are produced. The harness
// uses a count derived from the measured-window duration and INPUT_INTERVAL_MS;
// the sequence is deterministic and declared before the trial runs. Every entry
// carries a run-wide-unique source input id so the SOURCE input identity stays
// distinct from the protocol action_id and from any ack/HTTP/revision (Req
// 27.12). `idPrefix` scopes ids to a trial (e.g. "solo-1").
export function planInputs(count, idPrefix) {
  const plan = [];
  for (let i = 0; i < count; i += 1) {
    const action = DECLARED_PATTERN[i % DECLARED_PATTERN.length];
    plan.push({
      inputIndex: i,
      sourceInputId: `${idPrefix}-src-${i}`,
      action,
      key: keyForAction(action),
      intervalMs: INPUT_INTERVAL_MS,
    });
  }
  return plan;
}
