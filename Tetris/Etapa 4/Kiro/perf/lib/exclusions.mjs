// Sample qualification + exclusion rules (task 20.1; driver-correction 23).
//
// Every action-visible latency sample must be qualified or EXCLUDED WITH an
// explicit recorded reason (design.md "Clock domains and exclusions"; Req
// 27.3, 27.14, 27.15). This module is the single pure decision function the
// driver and the semantic self-checks both use, so the self-checks exercise the
// REAL logic (not a mirror of it). It never clamps a negative interval and
// never treats gravity-only, scalar-only, no-op, stale, rate-rejected,
// superseded, out-of-window, or unqualified-focus effects as action-visible.
//
// CORRECTION 23 (defect 6): the qualifier now requires POSITIVE proof. A field
// that is unknown (null) or merely not-false is NOT acceptance: accepted,
// focusOk, dispatchInWindow, and updateInWindow must each be exactly `true`,
// and a duel correlation must have roomOk/seatOk/revisionOk all exactly `true`.
// The prior rules rejected only on an explicit `=== false`, so a sample with
// {accepted:null, focusOk:null, dispatchInWindow:null, updateInWindow:null}
// slipped through and qualified. That hole is closed here: unknown proof is a
// documented exclusion, never a silent pass.

import { masksEqual } from "./palette.mjs";

// The canonical exclusion reason codes. Each is a stable string recorded on an
// excluded sample so a reader sees exactly why it was dropped.
export const REASON = Object.freeze({
  NO_OP_UNCHANGED_MASK: "no_op_unchanged_mask",
  O_ROTATION_UNCHANGED: "o_rotation_unchanged_mask",
  GRAVITY_ONLY: "gravity_only_change",
  SCALAR_ONLY: "scalar_only_change",
  STALE_REVISION: "stale_or_future_revision_reject",
  RATE_REJECTED: "rate_limited_reject",
  SUPERSEDED: "superseded_by_later_input",
  OUT_OF_WINDOW: "out_of_fixed_window",
  UNQUALIFIED_FOCUS: "unqualified_focus",
  NO_CORRELATED_REPLY: "no_correlated_ack_or_http_result",
  WRONG_CORRELATION: "wrong_room_seat_or_revision",
  NEGATIVE_INTERVAL: "negative_latency_not_clamped",
  EXPECTED_MASK_NEVER_RENDERED: "expected_changed_mask_never_rendered",
  // CORRECTION 23: a field that must be positively proven is unknown (null) or
  // otherwise not exactly true. Unknown proof is NOT acceptance.
  UNPROVEN_ACCEPTED: "action_not_positively_accepted",
  UNPROVEN_FOCUS: "focus_not_positively_qualified",
  UNPROVEN_WINDOW: "window_membership_not_positively_proven",
  UNPROVEN_CORRELATION: "correlation_not_positively_proven",
});

// Decide whether a candidate action sample qualifies as an action-visible
// 200-cell changed-mask latency sample, or must be excluded with a reason.
//
// `sample` fields (all optional; unknowns are null, never 0):
//   action            canonical action name (e.g. "cw")
//   pieceType         the active piece type at dispatch ("O".."L") or null
//   beforeMask        observed 200-cell RGB mask before the action (or null)
//   expectedMask      expected 200-cell RGB mask implied by the correlated reply
//   observedMask      observed 200-cell RGB mask after the action (or null)
//   accepted          true if the authoritative reply ACCEPTED the action
//   rejectReason      "stale_revision"/"future_revision"/"rate_limited"/... or null
//   isNoOp            true if the reply was a legal no-op (applied, board unchanged)
//   scalarOnly        true if ONLY a scalar (score/level/revision) changed
//   gravityOnly       true if the observed change is attributable to gravity only
//   superseded        true if a later input overtook this one before it rendered
//   correlation       { roomOk, seatOk, revisionOk } booleans (duel) or null (solo ok)
//   focusOk           true if input focus was qualified at dispatch AND update
//   dispatchInWindow  true if the dispatch timestamp is inside the fixed window
//   updateInWindow    true if the observed-update timestamp is inside the window
//   latencyMs         same-domain dispatch->observed-mask duration (may be <0 or null)
//
// Returns { qualified, reason, latencyMs }. `reason` is null when qualified.
export function qualifyActionSample(sample) {
  const s = sample || {};

  // A rejected action (stale/future revision, rate limited) is never an
  // action-visible render; exclude with the precise reason.
  if (s.rejectReason === "stale_revision" || s.rejectReason === "future_revision") {
    return { qualified: false, reason: REASON.STALE_REVISION, latencyMs: s.latencyMs ?? null };
  }
  if (s.rejectReason === "rate_limited") {
    return { qualified: false, reason: REASON.RATE_REJECTED, latencyMs: s.latencyMs ?? null };
  }
  // CORRECTION 23: acceptance must be POSITIVELY proven. `accepted === true` is
  // required; null (unknown) or false both exclude. A non-null rejectReason of
  // any kind also means the action was not a clean acceptance.
  if (s.accepted !== true) {
    const reason = s.accepted === false ? REASON.NO_CORRELATED_REPLY : REASON.UNPROVEN_ACCEPTED;
    return { qualified: false, reason, latencyMs: s.latencyMs ?? null };
  }
  if (s.rejectReason != null) {
    return { qualified: false, reason: REASON.NO_CORRELATED_REPLY, latencyMs: s.latencyMs ?? null };
  }

  // A legal no-op (e.g. an O-piece rotation, or a blocked wall move) changes no
  // pixels; it is excluded, with the O-rotation case named explicitly.
  if (s.isNoOp) {
    const reason = s.action === "cw" || s.action === "ccw"
      ? (s.pieceType === "O" ? REASON.O_ROTATION_UNCHANGED : REASON.NO_OP_UNCHANGED_MASK)
      : REASON.NO_OP_UNCHANGED_MASK;
    return { qualified: false, reason, latencyMs: s.latencyMs ?? null };
  }

  // Scalar-only and gravity-only changes are never action-visible proof.
  if (s.scalarOnly) {
    return { qualified: false, reason: REASON.SCALAR_ONLY, latencyMs: s.latencyMs ?? null };
  }
  if (s.gravityOnly) {
    return { qualified: false, reason: REASON.GRAVITY_ONLY, latencyMs: s.latencyMs ?? null };
  }

  // A superseded input (overtaken before its own effect rendered) is excluded.
  if (s.superseded) {
    return { qualified: false, reason: REASON.SUPERSEDED, latencyMs: s.latencyMs ?? null };
  }

  // Correlation must POSITIVELY match the exact room/seat/revision (duel). A
  // null correlation means "not applicable" (solo) and passes; but a present
  // correlation object must have every one of roomOk/seatOk/revisionOk exactly
  // true. Any false OR unknown (non-true, e.g. null) correlation flag excludes.
  if (s.correlation) {
    const { roomOk, seatOk, revisionOk } = s.correlation;
    if (roomOk === false || seatOk === false || revisionOk === false) {
      return { qualified: false, reason: REASON.WRONG_CORRELATION, latencyMs: s.latencyMs ?? null };
    }
    if (roomOk !== true || seatOk !== true || revisionOk !== true) {
      return { qualified: false, reason: REASON.UNPROVEN_CORRELATION, latencyMs: s.latencyMs ?? null };
    }
  }

  // The expected changed mask must have ACTUALLY been observed on the Canvas.
  // An unchanged mask (observed === before) is not action-visible, and an
  // observed mask that differs from the expected one means the expected change
  // never rendered (e.g. coalesced / never drawn).
  if (!Array.isArray(s.expectedMask) || !Array.isArray(s.observedMask)) {
    return { qualified: false, reason: REASON.EXPECTED_MASK_NEVER_RENDERED, latencyMs: s.latencyMs ?? null };
  }
  if (Array.isArray(s.beforeMask) && masksEqual(s.beforeMask, s.observedMask).equal) {
    return { qualified: false, reason: REASON.NO_OP_UNCHANGED_MASK, latencyMs: s.latencyMs ?? null };
  }
  if (!masksEqual(s.expectedMask, s.observedMask).equal) {
    return { qualified: false, reason: REASON.EXPECTED_MASK_NEVER_RENDERED, latencyMs: s.latencyMs ?? null };
  }

  // CORRECTION 23: focus must be POSITIVELY qualified (exactly true). A false
  // focus is the historical unqualified-focus reason; an unknown (null) focus
  // is the new unproven-focus reason. Neither can qualify.
  if (s.focusOk === false) {
    return { qualified: false, reason: REASON.UNQUALIFIED_FOCUS, latencyMs: s.latencyMs ?? null };
  }
  if (s.focusOk !== true) {
    return { qualified: false, reason: REASON.UNPROVEN_FOCUS, latencyMs: s.latencyMs ?? null };
  }

  // CORRECTION 23: both window endpoints must be POSITIVELY inside the fixed
  // window (exactly true). A false endpoint is out-of-window; an unknown (null)
  // endpoint is unproven-window. Neither can qualify.
  if (s.dispatchInWindow === false || s.updateInWindow === false) {
    return { qualified: false, reason: REASON.OUT_OF_WINDOW, latencyMs: s.latencyMs ?? null };
  }
  if (s.dispatchInWindow !== true || s.updateInWindow !== true) {
    return { qualified: false, reason: REASON.UNPROVEN_WINDOW, latencyMs: s.latencyMs ?? null };
  }

  // Latency must be known and NOT negative. A negative interval is excluded
  // with its own reason and NEVER clamped to 0 (Req 27.14).
  if (typeof s.latencyMs !== "number") {
    return { qualified: false, reason: REASON.EXPECTED_MASK_NEVER_RENDERED, latencyMs: null };
  }
  if (s.latencyMs < 0) {
    return { qualified: false, reason: REASON.NEGATIVE_INTERVAL, latencyMs: s.latencyMs };
  }

  return { qualified: true, reason: null, latencyMs: s.latencyMs };
}

// Percentile over an already-sorted ascending array using sorted[floor(p*n)].
// Returns null for an empty array (never a fabricated 0).
export function percentile(sortedAsc, p) {
  if (!Array.isArray(sortedAsc) || sortedAsc.length === 0) return null;
  const idx = Math.min(sortedAsc.length - 1, Math.floor((p / 100) * sortedAsc.length));
  return sortedAsc[idx];
}

// Summarize a set of qualified latencies (ms) into count/median/p95/p99.
// Unknown (empty) summaries report null statistics, never 0.
export function summarizeLatencies(latencies) {
  const valid = (latencies || []).filter((x) => typeof x === "number" && x >= 0);
  const sorted = valid.slice().sort((a, b) => a - b);
  return {
    count: sorted.length,
    median: percentile(sorted, 50),
    p95: percentile(sorted, 95),
    p99: percentile(sorted, 99),
  };
}

// rAF SCHEDULING targets, kept SEPARATE from measurement qualification (Req
// 27.6, 27.11). Mean >= 55 FPS and p95 interval <= 25 ms are SCHEDULING targets
// only, never a display or throughput guarantee.
export const SCHEDULING_TARGET_MEAN_FPS = 55;
export const SCHEDULING_TARGET_P95_INTERVAL_MS = 25;

// Evaluate the rAF scheduling targets against measured interval stats. Returns
// a report that explicitly labels these as scheduling targets, not a
// presentation guarantee.
export function evaluateSchedulingTargets(meanFps, p95IntervalMs) {
  return {
    meanFps: typeof meanFps === "number" ? meanFps : null,
    p95IntervalMs: typeof p95IntervalMs === "number" ? p95IntervalMs : null,
    meanFpsTargetMet: typeof meanFps === "number" ? meanFps >= SCHEDULING_TARGET_MEAN_FPS : null,
    p95TargetMet: typeof p95IntervalMs === "number" ? p95IntervalMs <= SCHEDULING_TARGET_P95_INTERVAL_MS : null,
    note:
      "Scheduler mean >= 55 FPS and p95 rAF interval <= 25 ms are SCHEDULING TARGETS ONLY, " +
      "kept separate from measurement qualification. They are NOT a display, throughput, or " +
      "physical-presentation guarantee; physical presentation latency remains UNKNOWN.",
  };
}

// ---------------------------------------------------------------------------
// CORRECTION 24 (defect 5): the SINGLE centralized trial-validity predicate.
//
// A trial cannot succeed with empty frame data OR empty qualified-action data,
// an invalid/uncalibrated calibration, lost OS/DOM qualification, an unobserved
// full window, OR (for a duel) missing peer pixel matches or missing peer
// latency. Probes must ALSO satisfy real OS foreground + DOM qualification
// (this closes the prior hole where a probe skipped the foreground
// requirement). The driver and the self-checks both call THIS function, so the
// self-checks exercise the real rule. Returns { invalid, reasons: [...] }.
//
// Inputs (all plain, already-derived facts; unknown -> treated as failing):
//   mode                 "solo" | "duel"
//   isProbe              true if this is a short probe
//   hasFailure           true if a failure string was already recorded
//   fullWindowObserved   true iff the capture covered the whole fixed window
//   frameSampleCount     number of in-window rAF interval samples
//   qualifiedSampleCount number of QUALIFIED action-visible samples
//   calibrationValid     true iff the actor pre+post calibration is calibrated
//   qualificationAllPassed true iff every per-input OS+DOM sample qualified
//   foregroundObserved   true iff a real OS foreground transition was observed
//   duelPeerMatchCount   (duel) number of qualified samples with a peer match
//   duelPeerLatencyCount (duel) number of qualified samples with a peer latency
export function trialIsInvalid({
  mode,
  isProbe,
  hasFailure,
  fullWindowObserved,
  frameSampleCount,
  qualifiedSampleCount,
  calibrationValid,
  qualificationAllPassed,
  foregroundObserved,
  duelPeerMatchCount,
  duelPeerLatencyCount,
}) {
  const reasons = [];
  if (hasFailure === true) reasons.push("recorded_failure");
  if (fullWindowObserved !== true) reasons.push("full_window_not_observed");
  if (!(typeof frameSampleCount === "number" && frameSampleCount > 0)) reasons.push("empty_frame_data");
  if (!(typeof qualifiedSampleCount === "number" && qualifiedSampleCount > 0)) reasons.push("empty_action_data");
  if (calibrationValid !== true) reasons.push("invalid_calibration");
  if (qualificationAllPassed !== true) reasons.push("os_dom_qualification_failed");
  // Probes must also pass the real OS foreground + DOM qualification.
  if (foregroundObserved !== true) reasons.push("foreground_not_observed");
  if (mode === "duel") {
    if (!(typeof duelPeerMatchCount === "number" && duelPeerMatchCount > 0)) reasons.push("no_duel_peer_matches");
    if (!(typeof duelPeerLatencyCount === "number" && duelPeerLatencyCount > 0)) reasons.push("no_duel_peer_latency");
  }
  return { invalid: reasons.length > 0, reasons, isProbe: isProbe === true };
}
