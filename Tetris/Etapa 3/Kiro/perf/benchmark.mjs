// Playwright-Chromium browser performance benchmark harness (Stage 3, Option A).
//
// EXECUTABLE harness, not pseudocode. Timing-sensitive; run MANUALLY on a real
// machine with a physical foreground display, never in ordinary unit CI
// (Req 15.5, 16.7). This revision applies the verified ROUND-07 corrections
// recorded in the Stage 3 requirements (Requirement 21) and design ("Benchmark
// harness corrected defects (Round 07, Req 21)"), on top of the earlier
// round-06 and round-04 corrections (all preserved). Round 07 replaces the weak
// "rising matching-count + any board change" completion with a GENUINE,
// AUDITABLE action-to-visible-update association: a PASSIVE Playwright
// request/response observer selects the single NEW /move request whose parsed
// direction matches the dispatched key and whose lifecycle starts after
// dispatch, reads that response's board + active_piece, computes the EXACT
// expected full 200-cell displayed signature exactly as the production React
// Board renders it, and completes the action only when the DOM shows that exact
// expected signature (never merely a changed board, so unrelated gravity can no
// longer complete an action). This round does NOT execute the timing-sensitive
// benchmark; real performance evidence exists only after the documented manual run.
//
// Separated measurement streams (Req 13.2, 14.5, 14.9, 20):
//   - Browser frame scheduling: raw requestAnimationFrame timestamps/intervals
//     on the PAGE performance clock.
//   - Actual game DOM updates: board MutationObserver batches with COMPLETE
//     200-cell signatures and transitions, on the same page clock. A DOM batch
//     is a CHANGED-SIGNATURE observer batch, never a count of cell mutations.
//   - API timing: two honestly separated streams --
//       (a) page-clock Resource Timing (PerformanceObserver "resource"), and
//       (b) a Node-side request->response stream on its OWN monotonic clock
//           (process.hrtime.bigint()), observed via Playwright network events.
//     Timestamps are NEVER subtracted across the page clock and the Node clock.
// requestAnimationFrame frequency alone is NEVER treated as proof of rendering
// throughput or of physical display presentation.
//
// Scenario (Req 13.4-13.6, 20): a VISIBLE FOREGROUND Chromium window at
// 1280x900, device scale factor 1, a recorded 60 Hz target, a 5-second warm-up
// (excluded from action latency), and exactly THREE independent measured runs
// of 30 seconds each, each in its own fresh sandboxed headed session
// (chromiumSandbox:true; no reused profile).
//
// Integrity / isolation (Req 15.1-15.4, 20): no gravity change, no inflating
// animation loop, no rotation, no Canvas/WebGL migration, real keyboard
// controls, no fake game responses, and inputs paced at most 4 actions/second.
// The harness does not touch application request bodies or queues.
//
// Honesty (Req 14.6, 14.10, 14.11, 20): numeric scheduling targets are reported
// SEPARATELY from a measurement-validity qualification gate (focus, full 200
// -cell geometry, adequate non-empty samples per stream, observed full window,
// screenshot-bearing trace, real final PNG). Unsupported environments and unmet
// targets are reported as-is; unobservable physical display presentation
// remains unknown.

import { chromium } from "playwright";
import os from "node:os";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// --- Scenario parameters (fixed experimental controls). ---
const TARGET_URL = process.env.PERF_TARGET_URL ?? "http://localhost:5183";
const VIEWPORT = { width: 1280, height: 900 };
const DEVICE_SCALE_FACTOR = 1;
const TARGET_HZ = 60;
const WARMUP_MS = 5000;
const MEASURE_MS = 30000;
const RUNS = 3;
const TARGET_MEAN_FPS = 55;
const TARGET_P95_INTERVAL_MS = 25;
const SLOW_FRAME_MS = 33.34;
// Input pacing: one action every 250 ms => at most 4 mutating requests/second.
const ACTION_INTERVAL_MS = 250;
// Full 10x20 board = 200 cells.
const BOARD_COLS = 10;
const BOARD_ROWS = 20;
const BOARD_CELLS = BOARD_COLS * BOARD_ROWS;
// Adequate-sample thresholds for qualification (per measured stream).
const MIN_FRAME_SAMPLES = 100;    // ~>=55 FPS over 30 s yields thousands; 100 is a floor.
const MIN_FOCUS_SAMPLES = 10;     // sampled ~1/s over 30 s.
const MIN_GEOMETRY_SAMPLES = 10;  // sampled ~1/s over 30 s.
// Documented optional stable-Chrome channel (e.g. PERF_BROWSER_CHANNEL=chrome).
const BROWSER_CHANNEL = process.env.PERF_BROWSER_CHANNEL ?? null;
// Max wait for a visible, complete board before warm-up.
const BOARD_READY_TIMEOUT_MS = 15000;
// Max wait for an authoritative visible transition after an action.
const ACTION_SETTLE_TIMEOUT_MS = 2000;
// Round-07: the fixed 30 s window must be observed to its END. captureEndAt
// must be >= windowEnd STRICTLY (no earlier-stop tolerance); any genuine late
// stop is retained separately for transparency.
const WINDOW_OBSERVED_TOLERANCE_MS = 0;

// --- Production React Board mirror (frontend/src/Board.tsx), used to compute
// the EXPECTED displayed board from an authoritative /move response so the
// harness can require that exact DOM signature (round-07 association). These
// MUST stay in sync with Board.tsx COLORS and TYPE_CODE. ---
const BOARD_COLORS = {
  0: "#111827",
  1: "#22d3ee", // I
  2: "#facc15", // O
  3: "#a855f7", // T
  4: "#22c55e", // S
  5: "#ef4444", // Z
  6: "#3b82f6", // J
  7: "#f97316", // L
};
const PIECE_TYPE_CODE = { I: 1, O: 2, T: 3, S: 4, Z: 5, J: 6, L: 7 };
// Directions a run's valid action samples must cover to qualify (round-07):
// left, right, and soft-drop.
const REQUIRED_DIRECTIONS = ["left", "right", "down"];

// Compute the EXPECTED per-cell hex-color grid (row-major, 200 entries) that
// the production Board renders for a given authoritative game state: copy the
// settled board, overlay the active piece cells with the piece type code, then
// map every code to its Board color. Mirrors Board.tsx exactly.
function expectedColorGridFromState(state) {
  if (!state || !Array.isArray(state.board)) return null;
  const grid = state.board.map((row) => row.slice());
  const active = state.active_piece;
  if (active && Array.isArray(active.cells) && PIECE_TYPE_CODE[active.type]) {
    const code = PIECE_TYPE_CODE[active.type];
    for (const pair of active.cells) {
      const r = pair[0], c = pair[1];
      if (r >= 0 && r < BOARD_ROWS && c >= 0 && c < BOARD_COLS) grid[r][c] = code;
    }
  }
  const colors = [];
  for (let r = 0; r < BOARD_ROWS; r += 1) {
    for (let c = 0; c < BOARD_COLS; c += 1) {
      const code = grid[r] && grid[r][c] != null ? grid[r][c] : 0;
      colors.push(BOARD_COLORS[code] != null ? BOARD_COLORS[code] : BOARD_COLORS[0]);
    }
  }
  return colors.length === BOARD_CELLS ? colors : null;
}

// Parse the move direction from a captured POST body, e.g. {"direction":"left"}.
function directionFromPostData(postData) {
  if (!postData) return null;
  try {
    const d = JSON.parse(postData).direction;
    return d === "left" || d === "right" || d === "down" ? d : null;
  } catch (_) {
    return null;
  }
}

// Map a dispatched ArrowKey to the move direction string used by the API body.
function directionForKey(key) {
  if (key === "ArrowLeft") return "left";
  if (key === "ArrowRight") return "right";
  if (key === "ArrowDown") return "down";
  return null;
}

const OUT_DIR = path.join(__dirname, "results", new Date().toISOString().replace(/[:.]/g, "-"));

function percentile(sorted, p) {
  if (sorted.length === 0) return null;
  const idx = Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length));
  return sorted[idx];
}

function summarizeIntervals(intervals) {
  const sorted = [...intervals].sort((a, b) => a - b);
  const sum = sorted.reduce((a, b) => a + b, 0);
  const meanInterval = sorted.length ? sum / sorted.length : null;
  return {
    count: intervals.length,
    meanInterval,
    median: percentile(sorted, 50),
    p95: percentile(sorted, 95),
    p99: percentile(sorted, 99),
    approxFps: meanInterval ? 1000 / meanInterval : null,
    slowFrames: intervals.filter((v) => v > SLOW_FRAME_MS).length,
  };
}

// Verify a file exists and is non-empty; returns { exists, size }.
function artifactStat(p) {
  try {
    const st = fs.statSync(p);
    return { exists: st.isFile(), size: st.size };
  } catch (_) {
    return { exists: false, size: 0 };
  }
}

// Instrumentation injected BEFORE app scripts run. It installs passive
// observers and a TRANSPARENT fetch passthrough only; it never alters gravity,
// pieces, rendering, request rate, request bodies, or request order.
//
// ROUND-06 corrections encoded here:
//   - Actions are stored in a Map keyed by a RUN-WIDE UNIQUE id; a completed
//     sample is never overwritten (ids are never reused by the driver).
//   - An action completes only when BOTH a real successful matching API
//     response AND a board-signature DOM transition are observed after its
//     dispatch; ordinary gravity alone cannot complete an action.
//   - The frame sampler can be STOPPED at capture end; captureEndAt is
//     recorded on the page clock.
//   - boardSignature encodes the COMPLETE per-cell displayed state for all 200
//     cells; DOM batches record CHANGED-SIGNATURE transitions (not cell counts).
const INSTRUMENT = String.raw`
(() => {
  const w = window;
  const BOARD_CELLS = ${BOARD_CELLS};
  // Single U+0001 signature separator, computed in the browser so the cooked
  // injected script contains no bare control character and no literal escape.
  const SIG_SEP = String.fromCharCode(1);
  w.__perf = {
    frames: [],       // { t, prevT, interval, inWindow, boundary }
    domBatches: [],    // { t, inWindow, signatureBefore, signatureAfter } (changed-signature batches)
    api: [],           // { name, method, status, ok, startTime, duration, clock:"page-performance" }
    actions: {},       // id -> action record (object map; ids are run-wide unique)
    actionOrder: [],   // ids in dispatch order (for stable iteration)
    focus: [],         // { t, hasFocus, inWindow }
    geometry: [],      // { t, boardVisible, cellCount, complete, rect, inWindow }
    windowStart: null,
    windowEnd: null,
    captureEndAt: null,
    lastSig: null,
    observerInstalled: false,
    samplersStopped: false,
  };

  function boardEl() {
    return document.querySelector('[data-testid="board"]')
      || document.querySelector('[aria-label="Tetris board"]')
      || document.querySelector('.board')
      || document.querySelector('table, #board');
  }
  function cellEls() {
    const b = boardEl();
    if (!b) return [];
    let cells = b.querySelectorAll('[data-cell], [data-testid="cell"]');
    if (cells.length === 0) cells = b.querySelectorAll('td, .cell');
    if (cells.length === 0) cells = b.children; // production board renders 200 leaf cell divs
    return cells;
  }

  // COMPLETE per-cell state (no lossy truncation): capture the full occupancy/
  // color/state marker for every cell so distinct colors and active/settled
  // states produce distinct signatures.
  function cellCode(c) {
    const dataCell = c.getAttribute ? c.getAttribute('data-cell') : null;
    if (dataCell !== null && dataCell !== undefined) return 'd:' + dataCell;
    const st = (c.getAttribute && c.getAttribute('style')) || '';
    const bg = (st.match(/background[^;]*/i) || [''])[0];
    const cls = (c.className && String(c.className)) || '';
    return 'b:' + bg + '|c:' + cls;
  }
  function boardArray() {
    const cells = cellEls();
    const arr = new Array(cells.length);
    for (let i = 0; i < cells.length; i++) arr[i] = cellCode(cells[i]);
    return arr;
  }
  function boardSignature() {
    const arr = boardArray();
    if (arr.length === 0) return null;
    return arr.join(SIG_SEP); // complete, unambiguous; no truncation
  }
  function boardComplete() {
    return cellEls().length >= BOARD_CELLS;
  }
  function cellCount() { return cellEls().length; }
  w.__perfBoardComplete = boardComplete;
  w.__perfBoardSignature = boardSignature;
  w.__perfBoardArray = boardArray;
  w.__perfCellCount = cellCount;

  // ROUND-07 association support. To require the EXACT displayed board that an
  // authoritative /move response implies, both the OBSERVED DOM and the
  // EXPECTED (response-derived) board are reduced to the SAME normalized
  // per-cell color token, so CSSOM hex/rgb serialization differences never
  // cause spurious mismatches. The expected colors come from the Node side
  // (computed exactly as the production Board renders them) and are normalized
  // here with the identical function used on observed cells.
  function normColor(raw) {
    if (raw == null) return "";
    let v = String(raw).trim().toLowerCase();
    // Expand #rgb to #rrggbb.
    const short = v.match(/^#([0-9a-f])([0-9a-f])([0-9a-f])$/);
    if (short) return "#" + short[1] + short[1] + short[2] + short[2] + short[3] + short[3];
    const hex = v.match(/^#([0-9a-f]{6})$/);
    if (hex) return "#" + hex[1];
    // rgb()/rgba() -> #rrggbb (ignore any alpha; board colors are opaque).
    const rgb = v.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
    if (rgb) {
      const h = (n) => Number(n).toString(16).padStart(2, "0");
      return "#" + h(rgb[1]) + h(rgb[2]) + h(rgb[3]);
    }
    return v;
  }
  // Observed per-cell color read from the live DOM (computed style background).
  function observedCellColor(c) {
    try {
      const cs = w.getComputedStyle(c);
      const bg = cs && (cs.backgroundColor || cs.background);
      if (bg) return normColor(bg);
    } catch (_) {}
    const st = (c.getAttribute && c.getAttribute("style")) || "";
    const m = st.match(/background[^;]*/i);
    if (m) {
      const col = (m[0].match(/#[0-9a-fA-F]{3,6}|rgba?\([^)]*\)/) || [""])[0];
      return normColor(col);
    }
    return "";
  }
  // Normalized observed board signature (row-major), aligned with the expected
  // signature format below. Returns null until all 200 cells exist.
  w.__perfNormalizedObservedSignature = () => {
    const cells = cellEls();
    if (cells.length < BOARD_CELLS) return null;
    const arr = new Array(BOARD_CELLS);
    for (let i = 0; i < BOARD_CELLS; i++) arr[i] = observedCellColor(cells[i]);
    return arr.join(SIG_SEP);
  };
  // Expected signature from a response-derived 200-entry hex-color grid, using
  // the SAME normalization as observed cells.
  w.__perfExpectedSignatureFromColorGrid = (colorGrid) => {
    if (!Array.isArray(colorGrid) || colorGrid.length !== BOARD_CELLS) return null;
    const arr = new Array(BOARD_CELLS);
    for (let i = 0; i < BOARD_CELLS; i++) arr[i] = normColor(colorGrid[i]);
    return arr.join(SIG_SEP);
  };

  function inFixedWindow(t) {
    return w.__perf.windowStart !== null
      && w.__perf.windowEnd !== null
      && t >= w.__perf.windowStart
      && t <= w.__perf.windowEnd;
  }

  // TRANSPARENT fetch passthrough: records real method/route/status and page
  // -clock start/end for app requests WITHOUT changing the request, its body,
  // or its ordering. We do not read or clone the response body (so queues and
  // body streams are untouched); status/ok is enough to confirm a real success.
  const origFetch = w.fetch ? w.fetch.bind(w) : null;
  if (origFetch) {
    w.fetch = (input, init) => {
      const method = (init && init.method) || (typeof input === 'object' && input.method) || 'GET';
      const url = typeof input === 'string' ? input : (input && input.url) || String(input);
      const startTime = performance.now();
      const p = origFetch(input, init);
      p.then((resp) => {
        try {
          w.__perf.api.push({
            name: url, method: String(method).toUpperCase(),
            status: resp.status, ok: resp.ok,
            startTime, duration: performance.now() - startTime,
            clock: 'page-performance',
          });
        } catch (_) {}
      }).catch(() => {});
      return p;
    };
  }

  // Frame scheduling sampler (single re-armed rAF; no inflation). Retains the
  // timestamp AND the previous-frame timestamp; an interval counts only when
  // BOTH endpoints are inside the fixed page-clock window. Can be STOPPED.
  let prevT = null;
  function onFrame(t) {
    if (w.__perf.samplersStopped) return; // stop at capture end
    if (prevT !== null) {
      const bothIn = inFixedWindow(prevT) && inFixedWindow(t);
      const boundary = (inFixedWindow(prevT) !== inFixedWindow(t));
      w.__perf.frames.push({ t, prevT, interval: t - prevT, inWindow: bothIn, boundary });
    }
    prevT = t;
    w.requestAnimationFrame(onFrame);
  }
  w.requestAnimationFrame(onFrame);

  w.__perfStopSamplers = () => {
    w.__perf.samplersStopped = true;
    w.__perf.captureEndAt = performance.now();
    return w.__perf.captureEndAt;
  };

  // Install the board MutationObserver only once the full board exists.
  w.__perfInstallObserver = () => {
    if (w.__perf.observerInstalled) return true;
    const b = boardEl();
    if (!b || !boardComplete()) return false;
    w.__perf.lastSig = boardSignature();
    const mo = new MutationObserver(() => {
      if (w.__perf.samplersStopped) return;
      const before = w.__perf.lastSig;
      const after = boardSignature();
      if (after !== before) {
        const t = performance.now();
        // One CHANGED-SIGNATURE batch (not a per-cell mutation count).
        w.__perf.domBatches.push({ t, inWindow: inFixedWindow(t), signatureBefore: before, signatureAfter: after });
        w.__perf.lastSig = after;
      }
    });
    mo.observe(b, { subtree: true, childList: true, attributes: true, characterData: true });
    w.__perf.observerInstalled = true;
    return true;
  };

  // Page-clock Resource Timing (honestly a SEPARATE stream on the page clock).
  try {
    const po = new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.initiatorType === 'fetch' || (e.name && e.name.includes('/api/'))) {
          w.__perf.api.push({ name: e.name, method: null, status: null, ok: null, startTime: e.startTime, duration: e.duration, clock: 'page-performance-resource-timing' });
        }
      }
    });
    po.observe({ entryTypes: ['resource'] });
  } catch (_) {}

  w.__perfSampleFocusGeometry = () => {
    if (w.__perf.samplersStopped) return;
    const t = performance.now();
    const within = inFixedWindow(t);
    w.__perf.focus.push({ t, hasFocus: document.hasFocus(), inWindow: within });
    const b = boardEl();
    if (b) {
      const r = b.getBoundingClientRect();
      const visible = r.width > 0 && r.height > 0 && r.top >= 0 && r.left >= 0 && r.bottom <= w.innerHeight && r.right <= w.innerWidth;
      const cc = cellEls().length;
      w.__perf.geometry.push({ t, boardVisible: visible, cellCount: cc, complete: cc >= BOARD_CELLS, rect: { x: r.x, y: r.y, width: r.width, height: r.height }, inWindow: within });
    } else {
      w.__perf.geometry.push({ t, boardVisible: false, cellCount: 0, complete: false, rect: null, inWindow: within });
    }
  };

  w.__perfMarkWindowStart = () => {
    w.__perf.windowStart = performance.now();
    w.__perf.windowEnd = w.__perf.windowStart + ${MEASURE_MS}; // fixed page-clock window
    return { start: w.__perf.windowStart, end: w.__perf.windowEnd };
  };
  w.__perfWindowElapsed = () => (w.__perf.windowStart === null ? 0 : performance.now() - w.__perf.windowStart);

  // ROUND-07 action lifecycle. An action is recorded at dispatch with its
  // RUN-WIDE UNIQUE id, its dispatched direction, the page-clock dispatch time,
  // and the raw full before-signature. Association to a real /move response and
  // the EXACT expected DOM signature happens in two later steps driven from the
  // Node side (which owns the passive request/response observer). A bare board
  // change can NEVER complete an action; completion requires the DOM to show
  // the exact expected 200-cell signature implied by the matched response.
  w.__perfRecordAction = (id, kind, direction) => {
    if (w.__perf.actions[id]) return id; // never overwrite a recorded id
    const tDispatch = performance.now();
    w.__perf.actions[id] = {
      id, kind, direction,
      route: "/move",
      tDispatch, tUpdate: null,
      sigBefore: boardSignature(),
      normSigBefore: w.__perfNormalizedObservedSignature(),
      expectedSig: null, observedSig: null,
      changed: null,
      // Matched API association (round-07): a single NEW /move with the same
      // direction, started after dispatch. Filled by __perfSetExpected.
      reqId: null, reqMethod: null, reqUrl: null, apiStatus: null,
      responseStateId: null, apiMatched: false, isNoop: false,
      inWindowDispatch: inFixedWindow(tDispatch),
      inWindowUpdate: null,
      excluded: false, reason: null,
    };
    w.__perf.actionOrder.push(id);
    return id;
  };
  // Bind the single matched /move response to the action and compute the EXACT
  // expected normalized 200-cell signature from that response's board +
  // active_piece (passed as a response-derived hex-color grid). Does not
  // complete the action; completion still requires the DOM to actually show the
  // expected signature.
  w.__perfSetExpected = (id, info) => {
    const a = w.__perf.actions[id];
    if (!a || a.expectedSig !== null) return false;
    const sig = w.__perfExpectedSignatureFromColorGrid(info && info.colorGrid);
    if (sig === null) return false;
    a.expectedSig = sig;
    a.reqId = info.reqId != null ? info.reqId : null;
    a.reqMethod = info.method != null ? info.method : null;
    a.reqUrl = info.url != null ? info.url : null;
    a.apiStatus = info.status != null ? info.status : null;
    a.responseStateId = info.stateId != null ? info.stateId : null;
    a.apiMatched = true;
    // A move whose authoritative response leaves the displayed board identical
    // to the pre-dispatch board is a no-op (e.g. a blocked wall move); it is
    // excluded rather than completed, since no visible update occurs.
    if (a.normSigBefore !== null && sig === a.normSigBefore) a.isNoop = true;
    return true;
  };
  // Report whether a bound action's matched response is a no-op (no visible
  // change). Used by the driver to exclude it with a precise reason.
  w.__perfIsNoop = (id) => {
    const a = w.__perf.actions[id];
    return !!(a && a.isNoop);
  };
  // Complete the action ONLY when the live DOM normalized signature equals the
  // expected signature derived from the matched response. Never completes on a
  // mere difference from the before-signature, so unrelated gravity transitions
  // (which produce a DIFFERENT board than this move's response implies) cannot
  // complete the action. A coalesced state never actually rendered is simply
  // never matched (and is later excluded on timeout).
  w.__perfTryCompleteAction = (id) => {
    const a = w.__perf.actions[id];
    if (!a) return false;
    if (a.tUpdate !== null) return true;
    if (a.expectedSig === null) return false; // not yet associated to a response
    const observed = w.__perfNormalizedObservedSignature();
    if (observed !== null && observed === a.expectedSig) {
      a.observedSig = observed;
      a.sigAfter = boardSignature();
      a.changed = true;
      a.tUpdate = performance.now();
      a.inWindowUpdate = inFixedWindow(a.tUpdate);
      return true;
    }
    return false;
  };
  w.__perfMarkActionExcluded = (id, reason) => {
    const a = w.__perf.actions[id];
    if (a) { a.excluded = true; a.reason = reason; a.changed = a.changed === null ? false : a.changed; }
  };
})();
`;

async function waitForBoardReady(page, timeoutMs) {
  // Wait for document readiness AND the full 200-cell board, then install the
  // observer. Returns true if the board is complete and observed.
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const ok = await page.evaluate(() => {
      if (document.readyState !== "complete") return false;
      if (!window.__perfBoardComplete || !window.__perfBoardComplete()) return false;
      return window.__perfInstallObserver();
    });
    if (ok) return true;
    // eslint-disable-next-line no-await-in-loop
    await page.waitForTimeout(100);
  }
  return false;
}

// Select the single NEW /move observation that matches a dispatched direction
// and whose lifecycle started AFTER the action was dispatched. Candidates are
// the move observations appended at or after the pre-dispatch snapshot index.
// Returns { status, obs, reason }:
//   status "one"      -> exactly one finished successful matching candidate
//   status "none"     -> no finished matching candidate yet
//   status "multiple" -> more than one matching candidate (ambiguous/overlap)
//   status "failed"   -> a matching candidate failed / was a no-op
function selectMoveCandidate(moveObservations, fromIndex, direction) {
  const matching = moveObservations
    .slice(fromIndex)
    .filter((o) => o.direction === direction);
  if (matching.length === 0) return { status: "none" };
  if (matching.some((o) => o.failed)) {
    return { status: "failed", reason: "matched /move request failed (no-op/network error)" };
  }
  // Wait on the explicit body-ready flag, NOT endNs: endNs is set at body-end
  // before the async JSON parse fills colorGrid, so keying off endNs could
  // falsely reject a still-parsing successful 200. A candidate is only
  // considered finished once its body has been fully resolved (parsed or
  // terminally failed).
  const finished = matching.filter((o) => o.bodyReady);
  if (finished.length === 0) return { status: "none" };
  if (matching.length > 1) {
    return { status: "multiple", reason: "more than one matching /move candidate after dispatch (ambiguous/overlapping)" };
  }
  const obs = finished[0];
  if (!obs.ok || !obs.colorGrid) {
    return { status: "failed", reason: "matched /move response not a usable success (bad status or unreadable state)" };
  }
  return { status: "one", obs };
}

async function driveGameplay(page, deadline, ctx) {
  // ctx: { measured, counter, moveObservations }. counter is a RUN-WIDE shared
  // { n } object so action ids are monotonically unique across every sub-call
  // (round-06 defect 1). moveObservations is the PASSIVE Node-side /move
  // request/response store used for round-07 association.
  const { measured, counter, moveObservations } = ctx;
  const keys = ["ArrowLeft", "ArrowRight", "ArrowDown"];
  while (Date.now() < deadline) {
    const key = keys[counter.n % keys.length];
    const direction = directionForKey(key);
    const actionId = `${measured ? "m" : "w"}-${counter.n}`; // run-wide unique
    counter.n += 1;

    // Snapshot the observation index BEFORE dispatch so only /move requests
    // whose lifecycle starts after this dispatch are considered candidates.
    const fromIndex = moveObservations.length;

    if (measured) {
      await page.evaluate(({ id, k, d }) => window.__perfRecordAction(id, k, d), { id: actionId, k: key, d: direction });
    }
    await page.keyboard.press(key);

    if (measured) {
      // ROUND-07 association: wait for the single NEW matching-direction /move
      // response, bind it (computing the EXACT expected displayed signature),
      // then require the DOM to actually show that exact expected signature.
      // Unrelated gravity transitions never match the expected signature, and a
      // coalesced state that is never rendered is excluded on timeout. The
      // eligible-action subset may be explicitly limited; every exclusion is
      // reported with a reason.
      const settleDeadline = Date.now() + ACTION_SETTLE_TIMEOUT_MS;
      let expectedBound = false;
      let excludeReason = null;
      let completed = false;

      while (Date.now() < settleDeadline) {
        if (!expectedBound) {
          const sel = selectMoveCandidate(moveObservations, fromIndex, direction);
          if (sel.status === "failed" || sel.status === "multiple") { excludeReason = sel.reason; break; }
          if (sel.status === "one") {
            sel.obs.consumedByActionId = actionId;
            // eslint-disable-next-line no-await-in-loop
            await page.evaluate(
              ({ id, info }) => window.__perfSetExpected(id, info),
              { id: actionId, info: { colorGrid: sel.obs.colorGrid, reqId: sel.obs.reqId, method: sel.obs.method, url: sel.obs.url, status: sel.obs.status, stateId: sel.obs.stateId } },
            );
            expectedBound = true;
            // eslint-disable-next-line no-await-in-loop
            const noop = await page.evaluate((id) => window.__perfIsNoop(id), actionId);
            if (noop) { excludeReason = "matched /move response is a no-op (board unchanged; e.g. blocked move)"; break; }
          }
        }
        if (expectedBound) {
          // eslint-disable-next-line no-await-in-loop
          completed = await page.evaluate((id) => window.__perfTryCompleteAction(id), actionId);
          if (completed) break;
        }
        // eslint-disable-next-line no-await-in-loop
        await page.waitForTimeout(16);
      }

      if (!completed) {
        if (!excludeReason) {
          excludeReason = expectedBound
            ? "expected displayed signature never observed in the DOM within settle timeout (coalesced/never-rendered/timed-out)"
            : "no single matching-direction /move response associated within settle timeout (no candidate/timed-out)";
        }
        await page.evaluate(({ id, reason }) => window.__perfMarkActionExcluded(id, reason), { id: actionId, reason: excludeReason });
      }
      await page.evaluate(() => window.__perfSampleFocusGeometry());
    }

    // Restart to keep gameplay active if the game ended (Req 13.6). Uses the
    // real restart control; no fake responses.
    const ended = await page.evaluate(() => (document.body.innerText || "").includes("Game Over"));
    if (ended) {
      const restart = await page.$('button:has-text("Restart")');
      if (restart) await restart.click();
    }
    await page.waitForTimeout(ACTION_INTERVAL_MS);
  }
}

function evaluateRun(perf, runIndex, nodeApi) {
  // Window-scoped frame intervals only (both endpoints inside the fixed window).
  const windowIntervals = perf.frames.filter((f) => f.inWindow).map((f) => f.interval);
  const frameSummary = summarizeIntervals(windowIntervals);

  // Action latency (round-07): eligible only when the action was associated to
  // a single NEW matching-direction /move response AND the DOM actually showed
  // the EXACT expected 200-cell signature that response implies, with BOTH the
  // dispatch and the observed-update timestamps inside the fixed window.
  // Excluded samples are retained with reasons; the eligible subset may be
  // explicitly limited. Directional coverage (left/right/soft-drop) across the
  // VALID samples is tracked for qualification.
  const latencies = [];
  const validSamples = [];
  const excludedActions = [];
  const coveredDirections = new Set();
  const ids = perf.actionOrder || Object.keys(perf.actions || {});
  for (const id of ids) {
    const a = perf.actions[id];
    if (!a) continue;
    if (a.excluded) { excludedActions.push({ id, direction: a.direction ?? null, reason: a.reason ?? "excluded" }); continue; }
    if (!a.apiMatched || a.expectedSig === null) {
      excludedActions.push({ id, direction: a.direction ?? null, reason: "no single matching-direction /move response associated" });
      continue;
    }
    if (!a.changed || a.tUpdate === null || a.observedSig === null || a.observedSig !== a.expectedSig) {
      excludedActions.push({ id, direction: a.direction ?? null, reason: "expected displayed signature never observed exactly in the DOM" });
      continue;
    }
    if (!a.inWindowDispatch || !a.inWindowUpdate) {
      excludedActions.push({ id, direction: a.direction ?? null, reason: "dispatch and/or observed update outside fixed window" });
      continue;
    }
    const latency = a.tUpdate - a.tDispatch;
    latencies.push(latency);
    if (a.direction) coveredDirections.add(a.direction);
    validSamples.push({
      id,
      direction: a.direction,
      reqId: a.reqId,
      apiStatus: a.apiStatus,
      responseStateId: a.responseStateId,
      tDispatch: a.tDispatch,
      tObservedUpdate: a.tUpdate,
      dispatchToObservedDomMs: latency, // page clock only; never mixed with Node RTT
      expectedSignatureMatched: true,
    });
  }
  const latencySorted = latencies.slice().sort((x, y) => x - y);
  const eligibleActionTotal = latencies.length + excludedActions.length;
  const hasValidSamples = latencies.length > 0;
  const directionalCoverageComplete = REQUIRED_DIRECTIONS.every((d) => coveredDirections.has(d));

  // Measurement-validity qualification, SEPARATE from numeric targets.
  const windowFocus = perf.focus.filter((f) => f.inWindow);
  const windowGeom = perf.geometry.filter((g) => g.inWindow);
  const focusAlways = windowFocus.length >= MIN_FOCUS_SAMPLES && windowFocus.every((f) => f.hasFocus);
  // Require EXACTLY 200 visible cells throughout the window (round-06 defect 4).
  const geometryComplete =
    windowGeom.length >= MIN_GEOMETRY_SAMPLES &&
    windowGeom.every((g) => g.boardVisible && g.cellCount === BOARD_CELLS);
  const domBatchCountInWindow = perf.domBatches.filter((b) => b.inWindow).length;
  const adequateFrames = windowIntervals.length >= MIN_FRAME_SAMPLES;
  const nonEmptySamples = adequateFrames && domBatchCountInWindow > 0;
  // Full fixed window actually observed (round-07): captureEndAt must be at or
  // past windowEnd STRICTLY (no earlier-stop tolerance). Any genuine late stop
  // is retained separately for transparency.
  const fullWindowObserved =
    perf.windowStart !== null &&
    perf.windowEnd !== null &&
    perf.captureEndAt !== null &&
    perf.captureEndAt >= perf.windowEnd - WINDOW_OBSERVED_TOLERANCE_MS;
  const lateStopMs =
    perf.captureEndAt !== null && perf.windowEnd !== null && perf.captureEndAt > perf.windowEnd
      ? perf.captureEndAt - perf.windowEnd
      : 0;

  const numericTargetsMet =
    frameSummary.approxFps !== null &&
    frameSummary.approxFps >= TARGET_MEAN_FPS &&
    frameSummary.p95 !== null &&
    frameSummary.p95 <= TARGET_P95_INTERVAL_MS;

  return {
    runIndex: runIndex + 1,
    windowStart: perf.windowStart,
    windowEnd: perf.windowEnd,
    captureEndAt: perf.captureEndAt,
    fullWindowObserved,
    frame: frameSummary,
    actionLatency: {
      eligibleTotal: eligibleActionTotal,
      count: latencies.length,
      excludedCount: excludedActions.length,
      excluded: excludedActions,
      median: percentile(latencySorted, 50),
      p95: percentile(latencySorted, 95),
      coveredDirections: Array.from(coveredDirections),
      directionalCoverageComplete,
      samples: validSamples,
      note:
        "Dispatch-to-observed-DOM latency on the PAGE clock only. Eligible only when the " +
        "action was associated to a single NEW matching-direction /move response AND the DOM " +
        "actually showed the EXACT expected 200-cell signature implied by that response, with " +
        "dispatch and observed update both inside the fixed window. A mere board change (e.g. " +
        "ordinary gravity) never completes an action, and a coalesced state never rendered is " +
        "excluded rather than attributed to a later gravity update. This is NOT input-to-photon " +
        "or physical display presentation latency; observer and 16 ms polling overhead is " +
        "included in the dispatch-to-observed-DOM span. The eligible-action subset may be " +
        "explicitly limited; excluded samples are reported above with reasons. API round-trip " +
        "time lives only on the Node monotonic clock (nodeApi) and is never subtracted against " +
        "this page-clock latency.",
    },
    domBatchCountInWindow, // CHANGED-SIGNATURE batches, not cell-mutation count.
    apiPageClock: { count: (perf.api || []).length },
    nodeApi: nodeApi ?? { count: 0, note: "Node request->response stream on its own monotonic clock; never subtracted against the page clock.", samples: [] },
    focus: { samples: windowFocus.length, always: focusAlways },
    geometry: { samples: windowGeom.length, complete: geometryComplete },
    lateStopMs,
    numericTargetsMet,
    qualified:
      focusAlways && geometryComplete && nonEmptySamples && fullWindowObserved &&
      hasValidSamples && directionalCoverageComplete,
    qualificationDetail: {
      focusAlways, geometryComplete, adequateFrames,
      domBatchesPresent: domBatchCountInWindow > 0, fullWindowObserved,
      exactly200CellsThroughout: geometryComplete,
      // Round-07: a qualified run must have a nonempty set of VALID action
      // samples covering actual left/right/soft-drop, and the full fixed window
      // must have been observed to its end (captureEndAt >= windowEnd strictly).
      hasValidActionSamples: hasValidSamples,
      validActionSampleCount: latencies.length,
      directionalCoverageComplete,
      coveredDirections: Array.from(coveredDirections),
    },
  };
}

async function runOnce(runIndex, launchMeta) {
  const runDir = path.join(OUT_DIR, `run-${runIndex + 1}`);
  fs.mkdirSync(runDir, { recursive: true });
  // Real per-run boundary timestamps (round-06 defect 6): started captured NOW.
  const runStartedAt = new Date().toISOString();

  let browser = null;
  let context = null;
  let page = null;
  let perf = null;
  let boardReady = false;
  let failure = null;
  let screenshotTaken = false;
  let traceTaken = false;
  let captureEndAt = null;

  // Node-side request->response stream on its OWN monotonic clock
  // (process.hrtime.bigint, nanoseconds). NEVER subtracted against the page
  // clock. Observed via Playwright network events; app bodies/queues untouched.
  const nodeApiSamples = [];
  const nodeReqStart = new Map();
  // ROUND-07: PASSIVE per-/move observation store. Each observed POST .../move
  // request gets a unique per-run request id and records its method, URL,
  // direction (parsed from the POST body), response status, the successful
  // response JSON state identity, and Node monotonic request-to-body-end
  // timestamps. The response JSON is read from the Playwright Response object on
  // the NODE side; the page's fetch body stream is never consumed or cloned,
  // and request bodies/queues are never altered.
  const moveObservations = [];
  let moveReqSeq = 0;

  try {
    const launchOptions = { headless: false, chromiumSandbox: true };
    if (BROWSER_CHANNEL) launchOptions.channel = BROWSER_CHANNEL;
    browser = await chromium.launch(launchOptions);
    launchMeta.browserVersion = browser.version();

    context = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: DEVICE_SCALE_FACTOR });
    await context.tracing.start({ screenshots: true, snapshots: true });
    page = await context.newPage();

    // Node monotonic-clock API observation (separate stream; no cross-clock math).
    page.on("request", (req) => {
      if (!req.url().includes("/api/")) return;
      const startNs = process.hrtime.bigint();
      nodeReqStart.set(req, startNs);
      if (req.method() === "POST" && req.url().includes("/move")) {
        moveReqSeq += 1;
        const obs = {
          reqId: `move-${runIndex + 1}-${moveReqSeq}`,
          url: req.url(),
          method: req.method(),
          direction: directionFromPostData(req.postData()),
          startNs: startNs.toString(),
          endNs: null,
          durationMs: null,
          status: null,
          ok: null,
          failed: false,
          // Explicit body-readiness: bodyReady flips true only AFTER the
          // response body is fully read/parsed (or terminally failed), set in a
          // finally. selectMoveCandidate waits on bodyReady, never on endNs, so
          // a still-parsing successful 200 is never mistaken for an unusable
          // result. bodyError distinguishes a genuine failure from still-parsing.
          bodyReady: false,
          bodyError: false,
          gameId: null,         // response game id (identity only)
          colorGrid: null,      // expected 200-cell hex color grid (Board-rendered)
          stateId: null,        // compact identity of the response state
          consumedByActionId: null,
          clock: "node-monotonic-hrtime",
        };
        req.__perfMoveObs = obs;
        moveObservations.push(obs);
      }
    });
    page.on("requestfailed", (req) => {
      const obs = req.__perfMoveObs;
      if (obs) {
        obs.failed = true;
        obs.bodyError = true;
        obs.endNs = process.hrtime.bigint().toString();
        obs.bodyReady = true; // terminally resolved (as a failure)
      }
    });
    page.on("requestfinished", async (req) => {
      if (!req.url().includes("/api/")) return;
      const start = nodeReqStart.get(req);
      if (start === undefined) return;
      const end = process.hrtime.bigint();
      let status = null;
      let resp = null;
      try { resp = await req.response(); status = resp ? resp.status() : null; } catch (_) {}
      nodeApiSamples.push({
        url: req.url(), method: req.method(), status,
        startNs: start.toString(), endNs: end.toString(),
        durationMs: Number(end - start) / 1e6,
        clock: "node-monotonic-hrtime",
      });
      nodeReqStart.delete(req);

      // ROUND-07: finalize the /move observation. request-to-body-end is the
      // Node monotonic span; the response JSON (read on the Node side) yields
      // the authoritative state used to compute the EXPECTED displayed board.
      const obs = req.__perfMoveObs;
      if (obs) {
        // endNs/durationMs are the REAL Node monotonic request-to-body-end span
        // (RTT stays on the Node clock). bodyReady flips true ONLY in the finally
        // below, after the body is fully read/parsed, so a still-parsing 200 is
        // never selected as usable nor falsely rejected.
        obs.endNs = end.toString();
        obs.durationMs = Number(end - start) / 1e6;
        obs.status = status;
        obs.ok = status !== null && status >= 200 && status < 300;
        try {
          if (obs.ok && resp) {
            const state = await resp.json();
            obs.gameId = state.id != null ? state.id : null;
            obs.colorGrid = expectedColorGridFromState(state);
            obs.stateId = JSON.stringify({ id: state.id, b: state.board, a: state.active_piece });
          }
        } catch (_) {
          obs.ok = false;       // successful status but unreadable body is unusable
          obs.bodyError = true; // a genuine failure, distinct from still-parsing
        } finally {
          // Body fully resolved (parsed or terminally failed): only now is the
          // observation eligible for selection. selectMoveCandidate waits on this
          // flag instead of endNs, closing the body-readiness race.
          obs.bodyReady = true;
        }
      }
    });

    await page.addInitScript(INSTRUMENT);

    await page.goto(TARGET_URL, { waitUntil: "load" });
    await page.bringToFront();
    await page.mouse.click(VIEWPORT.width / 2, VIEWPORT.height / 2); // ensure focus

    // Wait for the full board BEFORE warm-up and before any window marking.
    boardReady = await waitForBoardReady(page, BOARD_READY_TIMEOUT_MS);
    if (!boardReady) {
      failure = "board did not become visible/complete before warm-up";
    } else {
      // RUN-WIDE unique action counter shared across all driving sub-calls.
      const counter = { n: 0 };
      // Warm-up (NOT counted; window not yet started so samples are excluded).
      await driveGameplay(page, Date.now() + WARMUP_MS, { measured: false, counter, moveObservations });

      // Open the FIXED page-clock window end = start + MEASURE_MS.
      await page.evaluate(() => window.__perfMarkWindowStart());
      const geomTimer = setInterval(() => {
        page.evaluate(() => window.__perfSampleFocusGeometry()).catch(() => {});
      }, 1000);
      try {
        const hardDeadline = Date.now() + MEASURE_MS + 5000;
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const elapsed = await page.evaluate(() => window.__perfWindowElapsed());
          if (elapsed >= MEASURE_MS || Date.now() > hardDeadline) break;
          await driveGameplay(page, Date.now() + ACTION_INTERVAL_MS, { measured: true, counter, moveObservations });
        }
      } finally {
        clearInterval(geomTimer);
        // STOP passive samplers and record the real capture end (round-06 d.4).
        try { captureEndAt = await page.evaluate(() => window.__perfStopSamplers()); } catch (_) {}
      }
    }

    perf = await page.evaluate(() => window.__perf);
    await page.screenshot({ path: path.join(runDir, "final.png") });
    const pngStat0 = artifactStat(path.join(runDir, "final.png"));
    screenshotTaken = pngStat0.exists && pngStat0.size > 0; // honest flag
    await context.tracing.stop({ path: path.join(runDir, "trace.zip") });
    const traceStat0 = artifactStat(path.join(runDir, "trace.zip"));
    traceTaken = traceStat0.exists && traceStat0.size > 0; // honest flag
  } catch (err) {
    failure = (failure ? failure + "; " : "") + `exception: ${err && err.stack ? err.stack : String(err)}`;
    // Round-06 defect 5: fetch best-effort partial telemetry from the surviving
    // page BEFORE closing anything.
    if (page && !perf) {
      try { perf = await page.evaluate(() => window.__perf); } catch (_) {}
    }
    if (page && captureEndAt === null) {
      try { captureEndAt = await page.evaluate(() => (window.__perf ? window.__perf.captureEndAt : null)); } catch (_) {}
    }
    // Try to stop the trace; set traceTaken ONLY if the artifact really exists.
    try {
      if (context) {
        await context.tracing.stop({ path: path.join(runDir, "trace.zip") });
        const ts = artifactStat(path.join(runDir, "trace.zip"));
        traceTaken = ts.exists && ts.size > 0; // never true on a swallowed failure
      }
    } catch (_) {
      // swallowed stop failure: do NOT mark traceTaken true.
      const ts = artifactStat(path.join(runDir, "trace.zip"));
      traceTaken = ts.exists && ts.size > 0;
    }
    // Best-effort final PNG from the surviving page before close.
    if (page && !screenshotTaken) {
      try {
        await page.screenshot({ path: path.join(runDir, "final.png") });
        const ps = artifactStat(path.join(runDir, "final.png"));
        screenshotTaken = ps.exists && ps.size > 0;
      } catch (_) {}
    }
  } finally {
    // Persist partial raw datasets, failure metadata, exception details, and
    // the REAL success flags even if the run failed. Close only owned handles.
    const safe = perf ?? {};
    const writeJson = (name, value) => {
      try { fs.writeFileSync(path.join(runDir, name), JSON.stringify(value ?? null)); } catch (_) {}
    };
    writeJson("frames.json", safe.frames ?? []);
    writeJson("dom-batches.json", safe.domBatches ?? []);
    writeJson("api-page-clock.json", safe.api ?? []);
    writeJson("api-node-clock.json", nodeApiSamples);
    // Round-07: passive per-/move observation stream (ids, direction, status,
    // Node request-to-body-end timestamps, response-state identity, and the
    // Board-derived expected color grid) used for action association.
    writeJson("move-observations.json", moveObservations);
    // Actions saved as an ordered array with full association evidence.
    const actionsArr = (safe.actionOrder ?? []).map((id) => safe.actions[id]).filter(Boolean);
    writeJson("actions.json", actionsArr.length ? actionsArr : Object.values(safe.actions ?? {}));
    writeJson("focus.json", safe.focus ?? []);
    writeJson("geometry.json", safe.geometry ?? []);

    if (context) { try { await context.close(); } catch (_) {} }
    if (browser) { try { await browser.close(); } catch (_) {} }

    // Verify artifact existence/size before CLAIMING evidence.
    const pngStat = artifactStat(path.join(runDir, "final.png"));
    const traceStat = artifactStat(path.join(runDir, "trace.zip"));

    if (!perf || !boardReady || failure) {
      const result = {
        runIndex: runIndex + 1,
        failed: true,
        boardReady,
        failure: failure ?? "no samples captured",
        startedAt: runStartedAt,
        finishedAt: new Date().toISOString(),
        captureEndAt: captureEndAt ?? (safe.captureEndAt ?? null),
        evidence: {
          finalPng: pngStat.exists ? "final.png" : null, finalPngBytes: pngStat.size, screenshotTaken,
          trace: traceStat.exists ? "trace.zip" : null, traceBytes: traceStat.size, traceTaken,
        },
        samplesPersisted: {
          frames: (safe.frames ?? []).length,
          domBatches: (safe.domBatches ?? []).length,
          apiPageClock: (safe.api ?? []).length,
          apiNodeClock: nodeApiSamples.length,
          moveObservations: moveObservations.length,
          actions: actionsArr.length,
        },
        numericTargetsMet: false,
        qualified: false,
      };
      try { fs.writeFileSync(path.join(runDir, "summary.json"), JSON.stringify(result, null, 2)); } catch (_) {}
      // eslint-disable-next-line no-unsafe-finally
      return result;
    }

    const result = evaluateRun(perf, runIndex, {
      count: nodeApiSamples.length,
      note: "Node request->response stream on its own monotonic clock (hrtime); never subtracted against the page clock.",
      samples: nodeApiSamples,
    });
    result.startedAt = runStartedAt;
    result.finishedAt = new Date().toISOString();
    result.evidence = {
      finalPng: pngStat.exists ? "final.png" : null, finalPngBytes: pngStat.size, screenshotTaken,
      trace: traceStat.exists ? "trace.zip" : null, traceBytes: traceStat.size, traceTaken,
    };
    // The qualification gate ALSO requires a verified screenshot-bearing trace
    // and a real non-empty final PNG to actually exist on disk.
    const evidencePresent = screenshotTaken && traceTaken && pngStat.size > 0 && traceStat.size > 0;
    result.qualified = result.qualified && evidencePresent;
    result.qualificationDetail.screenshotTraceVerified = evidencePresent;
    try { fs.writeFileSync(path.join(runDir, "summary.json"), JSON.stringify(result, null, 2)); } catch (_) {}
    // eslint-disable-next-line no-unsafe-finally
    return result;
  }
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const batchStartedAt = new Date().toISOString(); // REAL batch start (round-06 d.6)
  const launchMeta = { channel: BROWSER_CHANNEL ?? "bundled-chromium", browserVersion: null };

  // Playwright version (actual, not a constant).
  let playwrightVersion = null;
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, "node_modules/playwright/package.json"), "utf8"));
    playwrightVersion = pkg.version;
  } catch (_) {
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, "package.json"), "utf8"));
      playwrightVersion = (pkg.dependencies && pkg.dependencies.playwright) ?? null;
    } catch (_) {}
  }

  const runResults = [];
  let runError = null;
  try {
    for (let i = 0; i < RUNS; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      const r = await runOnce(i, launchMeta);
      runResults.push(r);
    }
  } catch (err) {
    runError = err && err.stack ? err.stack : String(err);
  } finally {
    const batchFinishedAt = new Date().toISOString(); // REAL batch finish
    const allQualified = runResults.length === RUNS && runResults.every((r) => r.qualified);
    const allNumericMet = runResults.length === RUNS && runResults.every((r) => r.numericTargetsMet);
    const report = {
      scenario: {
        targetUrl: TARGET_URL,
        viewport: VIEWPORT,
        deviceScaleFactor: DEVICE_SCALE_FACTOR,
        targetHz: TARGET_HZ,
        warmupMs: WARMUP_MS,
        measureMs: MEASURE_MS,
        runs: RUNS,
        actionIntervalMs: ACTION_INTERVAL_MS,
        maxActionsPerSecond: Math.round(1000 / ACTION_INTERVAL_MS),
        headless: false,
        foreground: true,
        chromiumSandbox: true,
      },
      targets: {
        meanFps: TARGET_MEAN_FPS,
        p95IntervalMs: TARGET_P95_INTERVAL_MS,
        slowFrameMs: SLOW_FRAME_MS,
        note:
          "The >=55 FPS mean and <=25 ms p95 targets are a tolerance around a 60 Hz " +
          "SCHEDULING target. They are NOT a guarantee of physical display presentation. " +
          "Frame scheduling, game DOM throughput, and physical display presentation are " +
          "reported separately.",
      },
      browser: {
        name: "chromium",
        channel: launchMeta.channel,
        version: launchMeta.browserVersion,
        playwrightVersion,
      },
      runtime: {
        node: process.version,
        platform: os.platform(),
        release: os.release(),
        arch: os.arch(),
        cpus: os.cpus().map((c) => c.model)[0],
        cpuCount: os.cpus().length,
        totalMemBytes: os.totalmem(),
        gpu: "unknown (not probed by this harness)",
        display: "unknown; physical foreground display presentation is NOT observable from the page and is reported as unknown",
      },
      startedAt: batchStartedAt,
      finishedAt: batchFinishedAt,
      runs: runResults,
      overallQualified: allQualified,
      overallNumericTargetsMet: allNumericMet,
      runError,
      clockNote:
        "API timing is recorded as TWO honestly separated streams: a page-clock Resource " +
        "Timing / fetch-passthrough stream and a Node-side request->response stream on its " +
        "own monotonic clock (process.hrtime). Node API round-trip time stays entirely on the " +
        "Node clock; action dispatch-to-observed-DOM latency stays entirely on the page clock. " +
        "Timestamps are never subtracted across the two clock domains.",
      associationNote:
        "Action-to-visible-update latency uses a GENUINE association: a passive Playwright " +
        "request/response observer selects the single NEW matching-direction /move request " +
        "started after dispatch, reads that response's board + active_piece, computes the EXACT " +
        "expected 200-cell displayed signature the production React Board would render, and the " +
        "action completes only when the DOM actually shows that exact signature. A bare board " +
        "change (e.g. ordinary gravity) can never complete an action; zero/multiple/overlapping/" +
        "failed/no-op/timed-out candidates and never-rendered coalesced states are excluded and " +
        "reported with reasons. The reported dispatch-to-observed-DOM latency includes observer " +
        "and ~16 ms polling overhead and is NOT input-to-photon or physical display presentation " +
        "latency.",
      honestyNote:
        "requestAnimationFrame frequency alone is not proof of rendering throughput or of " +
        "physical display presentation. Numeric scheduling targets are reported SEPARATELY " +
        "from measurement-validity qualification (input focus throughout, exactly 200-cell " +
        "unclipped board geometry throughout, adequate non-empty frame/DOM samples, a nonempty " +
        "set of VALID action-latency samples covering actual left/right/soft-drop, the full " +
        "fixed window actually observed to its end (captureEndAt >= windowEnd strictly), and a " +
        "verified screenshot-bearing trace plus a real final PNG). A run that is not qualified " +
        "fails regardless of its numeric values. A hosted/CI runner does not establish a real " +
        "physical foreground display. Unmet targets or unsupported environments are reported " +
        "as-is; this file being present is NOT evidence that a measured run was executed.",
    };
    try { fs.writeFileSync(path.join(OUT_DIR, "report.json"), JSON.stringify(report, null, 2)); } catch (_) {}

    console.log(`Benchmark complete. Results: ${OUT_DIR}`);
    for (const r of runResults) {
      if (r.failed) {
        console.log(`Run ${r.runIndex}: FAILED/UNQUALIFIED - ${r.failure}`);
      } else {
        console.log(
          `Run ${r.runIndex}: approxFps=${r.frame.approxFps?.toFixed(1)} ` +
            `p95=${r.frame.p95?.toFixed(2)}ms median=${r.frame.median?.toFixed(2)}ms ` +
            `slow(>${SLOW_FRAME_MS}ms)=${r.frame.slowFrames} ` +
            `latencyEligible=${r.actionLatency.count}/${r.actionLatency.eligibleTotal} ` +
            `dirs=${(r.actionLatency.coveredDirections || []).join("+") || "none"} ` +
            `domBatches=${r.domBatchCountInWindow} ` +
            `numericTargetsMet=${r.numericTargetsMet} qualified=${r.qualified}`,
        );
      }
    }
    console.log(`Overall qualified in every run: ${allQualified}`);
    console.log(`Overall numeric targets met in every run: ${allNumericMet}`);
    // Exit success only when BOTH qualification and numeric targets hold in all
    // runs; a valid-but-slow or invalid capture never reports success.
    process.exitCode = allQualified && allNumericMet ? 0 : 1;
  }
}

main().catch((err) => {
  console.error("Benchmark failed:", err && err.stack ? err.stack : err);
  process.exitCode = 2;
});
