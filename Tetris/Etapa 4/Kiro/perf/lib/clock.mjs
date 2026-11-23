// Paired Node hrtime / browser performance clock calibration (task 20.1).
//
// The actor input/browser clock and the Node monotonic clock are DIFFERENT
// domains (design.md "Clock domains and exclusions"; Req 26.7, 27.10). This
// module records paired pre/post calibration samples and an explicit
// uncertainty bound, and provides a GUARD that refuses to subtract two
// timestamps from different clock domains. It never clamps a negative interval.
//
// Pure/side-effect free on import: it does not read `process` or any browser
// global at import time. The caller passes in the actual paired readings it
// collected (a Node `process.hrtime.bigint()` nanosecond value alongside a
// browser `performance.now()` millisecond value, taken as close together as
// possible, once before the measured window and once after).

// The clock-domain labels the harness recognizes. A sample carries its domain,
// and durations are only ever computed within ONE domain.
export const DOMAIN_NODE = "node-hrtime";
export const DOMAIN_BROWSER = "browser-performance";

// Convert a Node hrtime bigint (nanoseconds) to milliseconds as a Number. The
// bigint is divided in nanoseconds first so no precision is lost before the
// final Number conversion of a (bounded) millisecond value.
export function hrtimeNsToMs(ns) {
  if (typeof ns === "bigint") return Number(ns) / 1e6;
  if (typeof ns === "number") return ns / 1e6;
  return null;
}

// Build one calibration point from a paired reading. `nodeNs` is a
// process.hrtime.bigint() value; `browserMs` is a performance.now() value read
// as close as possible to the Node reading. `gapMs` is the real wall gap the
// caller measured between taking the two readings (its own Node-side
// before/after hrtime around the page.evaluate round-trip); it is the
// uncertainty contribution of THIS calibration point and is never invented.
export function calibrationPoint(nodeNs, browserMs, gapMs) {
  const nodeMs = hrtimeNsToMs(nodeNs);
  return {
    nodeMs: nodeMs,
    browserMs: typeof browserMs === "number" ? browserMs : null,
    // offset = nodeClock - browserClock at this instant (ms). Null if either
    // reading is unknown; never fabricated as 0.
    offsetMs: nodeMs != null && typeof browserMs === "number" ? nodeMs - browserMs : null,
    uncertaintyMs: typeof gapMs === "number" && gapMs >= 0 ? gapMs : null,
  };
}

// Summarize paired pre/post calibration into drift and an explicit uncertainty
// bound (Req 27.10). Drift is the change in the node-minus-browser offset
// across the measured window; uncertainty is the sum of the two round-trip
// gaps plus the absolute drift. Any unknown input yields null fields (never 0),
// so an uncalibrated run is reported as uncalibrated, not as zero-drift.
export function summarizeCalibration(pre, post) {
  const preOffset = pre ? pre.offsetMs : null;
  const postOffset = post ? post.offsetMs : null;
  const driftMs = preOffset != null && postOffset != null ? postOffset - preOffset : null;
  const preU = pre && pre.uncertaintyMs != null ? pre.uncertaintyMs : null;
  const postU = post && post.uncertaintyMs != null ? post.uncertaintyMs : null;
  let uncertaintyMs = null;
  if (preU != null && postU != null && driftMs != null) {
    uncertaintyMs = preU + postU + Math.abs(driftMs);
  }
  return {
    pre: pre ?? null,
    post: post ?? null,
    driftMs,
    uncertaintyMs,
    calibrated: preOffset != null && postOffset != null,
    note:
      "Paired Node hrtime / browser performance calibration. Offsets are node-minus-browser " +
      "at each instant; drift is their difference across the measured window; uncertainty is " +
      "the sum of the two round-trip gaps plus the absolute drift. Timestamps from different " +
      "clock domains are NEVER subtracted; see assertSameDomain. Unknown fields are null.",
  };
}

// A single timestamped sample tagged with its clock domain. Factory kept tiny
// so every produced sample always carries a domain label.
export function stamp(domain, valueMs) {
  return { domain, valueMs: typeof valueMs === "number" ? valueMs : null };
}

// GUARD against a cross-clock subtraction (design.md "Clock domains and
// exclusions"; Req 27.10). Throws if two samples are from different domains.
// The harness computes an interval ONLY between two same-domain samples; a
// cross-domain duration is a programming error, not a silently-wrong number.
export function assertSameDomain(a, b) {
  if (!a || !b || !a.domain || !b.domain) {
    throw new Error("clock sample missing a domain label; refusing to subtract");
  }
  if (a.domain !== b.domain) {
    throw new Error(
      `cross-clock subtraction refused: ${a.domain} vs ${b.domain}. ` +
        "Node hrtime and browser performance timestamps are never subtracted across domains.",
    );
  }
  return true;
}

// Compute a duration between two SAME-domain samples. Returns null if either
// value is unknown. Does NOT clamp a negative interval (Req 27.14): a negative
// result is returned as-is so the caller can EXCLUDE it with a recorded reason
// rather than hide it as 0.
export function sameDomainDuration(start, end) {
  assertSameDomain(start, end);
  if (start.valueMs == null || end.valueMs == null) return null;
  return end.valueMs - start.valueMs;
}

// ---------------------------------------------------------------------------
// CORRECTION 23 (defect 5): cross-browser (actor vs peer) latency mapping.
//
// The actor browser clock and the peer browser clock are DISTINCT domains, and
// neither is the Node clock. A peer latency is therefore NEVER raw
// peerPerformance - actorPerformance. Instead each browser is paired to the
// Node hrtime clock via its own calibration (summarizeCalibration), and a peer
// timestamp is transformed into the actor's domain THROUGH the common Node
// time, carrying an explicit uncertainty. A missing calibration refuses the
// mapping (returns null) rather than inventing a zero offset.
//
// Domain label for a distinct peer browser clock.
export const DOMAIN_PEER_BROWSER = "peer-browser-performance";

// Map a browser timestamp (ms, in some browser domain) to the Node hrtime
// domain (ms) using that browser's calibration offset (node - browser). Returns
// { nodeMs, uncertaintyMs } or null if the calibration offset is unknown.
export function browserToNode(browserMs, calibration) {
  if (typeof browserMs !== "number" || !calibration) return null;
  // Prefer the pre calibration offset but fold in the drift as uncertainty.
  const pre = calibration.pre ? calibration.pre.offsetMs : null;
  const offset = pre != null ? pre : (calibration.post ? calibration.post.offsetMs : null);
  if (offset == null) return null;
  const nodeMs = browserMs + offset; // node = browser + (node - browser)
  const u = calibration.uncertaintyMs != null ? calibration.uncertaintyMs : null;
  return { nodeMs, uncertaintyMs: u };
}

// Compute a PEER action-visible latency: from the ACTOR's input/dispatch time
// (actor browser clock) to the PEER's observed-update time (peer browser
// clock), mapping BOTH through their own Node calibrations into the common Node
// domain and subtracting there. Returns { latencyMs, uncertaintyMs, domain } or
// a refusal { latencyMs: null, reason } when either calibration is missing or a
// timestamp is unknown. NEVER subtracts the two raw browser performance values
// directly, and NEVER clamps a negative result.
export function peerLatencyThroughNode({ actorDispatchBrowserMs, actorCalibration, peerUpdateBrowserMs, peerCalibration }) {
  const a = browserToNode(actorDispatchBrowserMs, actorCalibration);
  const p = browserToNode(peerUpdateBrowserMs, peerCalibration);
  if (!a || !p) {
    return { latencyMs: null, uncertaintyMs: null, domain: DOMAIN_NODE, reason: "uncalibrated_cross_browser_refused" };
  }
  const latencyMs = p.nodeMs - a.nodeMs; // common Node domain; not clamped
  const uncertaintyMs =
    (a.uncertaintyMs != null ? a.uncertaintyMs : 0) +
    (p.uncertaintyMs != null ? p.uncertaintyMs : 0);
  return {
    latencyMs,
    uncertaintyMs,
    domain: DOMAIN_NODE,
    reason: null,
    note:
      "Peer action-to-opponent-visible latency mapped through calibrated Node common time " +
      "(actor and peer browser clocks are distinct and are NEVER subtracted raw). The result " +
      "carries the summed calibration uncertainty and is not clamped.",
  };
}
