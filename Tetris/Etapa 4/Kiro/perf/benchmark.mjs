// Stage 4 Playwright-Chromium benchmark harness (Option A).
//
// DRIVER CORRECTION 23. This EXTENDS this tool's own Stage 3 perf harness to
// Stage 4 and fixes seven functional defects (see
// docs/native-checks/23-stage4-benchmark-driver-correction/). The application
// (backend/, frontend/) is UNCHANGED; only perf/ is edited. Dependency versions
// (Playwright 1.56.0), the installed Chrome channel, and the Chromium sandbox
// are preserved. This file is an IMPLEMENTED, RUNNABLE harness; importing it
// launches nothing. A measured trial/probe runs ONLY on the authorized CLI path
// with an explicit mode.
//
// Key corrections:
//   1. OWNED PID via the PUBLIC chromium.launchServer().process().pid +
//      chromium.connect(wsEndpoint); Browser.process() is UNDEFINED on this
//      build (proven by the researcher qualification report), so it is NOT used.
//   2. Duel opens REAL A and B pages, both join the SAME room and reach
//      room_status "playing" before READY_FOR_FOREGROUND. Solo skips the (then
//      disabled) Solo-tab click when it is already selected.
//   3. Duel correlation ties the outgoing action -> ACK (by action_id) -> the
//      StateFrame at the ACK revision for THAT room/seat. Solo correlates by the
//      specific move/rotate POST request object, never a /tick or stale latest.
//   4. OS-foreground qualification uses read-only EnumWindows-by-PID plus DOM
//      focus/visibility/1280x900/DPR1; unknown/lost/wrong foreground invalidates
//      a trial.
//   5. Actor and peer browser clocks are distinct; peer latency is mapped
//      through calibrated Node common time with uncertainty, never raw.
//   6. Qualification requires POSITIVE proof (see lib/exclusions.mjs).
//   7. CLI adds single-trial and SHORT-probe modes; probes are not performance
//      results; nonzero exit on invalid/empty required data.

import os from "node:os";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  BOARD_COLS,
  BOARD_ROWS,
  BOARD_CELLS,
  COLORS,
  TYPE_CODE,
  expectedRgbMaskFromState,
  maskFromCenterRgba,
  masksEqual,
  nonBackgroundCellCount,
} from "./lib/palette.mjs";
import {
  DECLARED_PATTERN,
  INPUT_INTERVAL_MS,
  ACTION_TO_KEY,
  keyForAction,
  planInputs,
} from "./lib/input-pattern.mjs";
import {
  REASON,
  qualifyActionSample,
  summarizeLatencies,
  evaluateSchedulingTargets,
  trialIsInvalid,
} from "./lib/exclusions.mjs";
import {
  DOMAIN_NODE,
  DOMAIN_BROWSER,
  DOMAIN_PEER_BROWSER,
  calibrationPoint,
  summarizeCalibration,
  stamp,
  sameDomainDuration,
  peerLatencyThroughNode,
} from "./lib/clock.mjs";
import {
  readForegroundWindow,
  foregroundMatchesActor,
  readyForForegroundSignal,
  waitForForegroundTransition,
  enumerateWindowsForPid,
  qualifyActorWindow,
} from "./lib/foreground.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// --- Fixed experimental controls. ---
export const TARGET_URL = process.env.PERF_TARGET_URL ?? "http://127.0.0.1:5517";
export const VIEWPORT = { width: 1280, height: 900 };
export const DEVICE_SCALE_FACTOR = 1; // DPR 1
export const BROWSER_CHANNEL = process.env.PERF_BROWSER_CHANNEL ?? "chrome";
export const WARMUP_MS = 5000;
export const MEASURE_MS = 30000;
export const TRIAL_MS = 35000;
export const SOLO_TRIALS = 3;
export const DUEL_TRIALS = 3;
export const BOARD_READY_TIMEOUT_MS = 20000;
export const ACTION_SETTLE_TIMEOUT_MS = 1500;
export const DUEL_JOIN_TIMEOUT_MS = 20000;
export const FOREGROUND_WAIT_MS = Number(process.env.PERF_FOREGROUND_WAIT_MS ?? 30000);
export const WINDOW_OBSERVED_TOLERANCE_MS = 0;
// A SHORT probe is explicitly NOT a performance result: a brief measured window
// used only to confirm the instrument drives the real app end to end.
export const PROBE_MEASURE_MS = Number(process.env.PERF_PROBE_MS ?? 3000);

// Selectors from the FROZEN frontend (App.tsx / DuelView.tsx / CanvasBoard.tsx).
export const SELECTOR = Object.freeze({
  modeTabSolo: '[role="tab"][data-testid="mode-solo"]',
  modeTabDuel: '[role="tab"][data-testid="mode-duel"]',
  roomNameInput: '#duel-room-name',
  createOrJoinButton: 'button:has-text("Create or join")',
  soloCanvas: 'section[aria-label="Solo"] canvas[aria-label="Tetris board"]',
  actorCanvas: '[aria-label="Your Tetris board"] canvas',
  peerCanvas: '[aria-label="Opponent Tetris board (read-only)"] canvas',
});

function newOutDir(label) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const safe = typeof label === "string" && label.length ? label.replace(/[^a-zA-Z0-9_-]/g, "_") : "run";
  return path.join(__dirname, "results", `${stamp}-${safe}`);
}

function artifactStat(p) {
  try {
    const st = fs.statSync(p);
    return { exists: st.isFile(), size: st.size };
  } catch (_) {
    return { exists: false, size: 0 };
  }
}

// ---------------------------------------------------------------------------
// Browser instrumentation (passive, read-only). Installs ONLY an rAF SCHEDULING
// observer and a SINGLE-buffer Canvas reader. It does NOT patch fetch/WebSocket,
// read React internals, or inject authority. String.raw preserves regex
// backslashes (the Stage 3 round-08 defect).
//
// CORRECTION 23 (defect 5): the Canvas reader returns the read timestamp in the
// SAME browser call as the single-buffer read, so the observed-mask time is the
// real read time (not a separate later call).
export const INSTRUMENT = String.raw`
(() => {
  const w = window;
  const BOARD_COLS = ${BOARD_COLS};
  const BOARD_ROWS = ${BOARD_ROWS};
  const BOARD_CELLS = ${BOARD_CELLS};
  const MEASURE_MS = ${MEASURE_MS};
  w.__perf = {
    frames: [],
    windowStart: null,
    windowEnd: null,
    captureEndAt: null,
    samplersStopped: false,
    rafInstalled: false,
    keydowns: [],
    keydownSeq: 0,
    keydownInstalled: false,
  };

  function inFixedWindow(t) {
    return w.__perf.windowStart !== null
      && w.__perf.windowEnd !== null
      && t >= w.__perf.windowStart
      && t <= w.__perf.windowEnd;
  }

  let prevT = null;
  function onFrame(t) {
    if (w.__perf.samplersStopped) return;
    if (prevT !== null) {
      const bothIn = inFixedWindow(prevT) && inFixedWindow(t);
      w.__perf.frames.push({ t, prevT, interval: t - prevT, inWindow: bothIn });
    }
    prevT = t;
    w.requestAnimationFrame(onFrame);
  }
  w.__perfStartRaf = () => {
    if (w.__perf.rafInstalled) return true;
    w.__perf.rafInstalled = true;
    w.requestAnimationFrame(onFrame);
    return true;
  };

  w.__perfStopSamplers = () => {
    w.__perf.samplersStopped = true;
    w.__perf.captureEndAt = performance.now();
    return w.__perf.captureEndAt;
  };
  w.__perfMarkWindowStart = (durationMs) => {
    // CORRECTION 24 (defect 1): the fixed-window length is the ACTUAL measured
    // duration passed by the driver (full trial 30000 ms; short probe
    // PROBE_MEASURE_MS), not the hardcoded MEASURE_MS. A non-finite/negative
    // argument falls back to MEASURE_MS so the marker is never silently zero.
    const ms = typeof durationMs === "number" && isFinite(durationMs) && durationMs > 0
      ? durationMs : MEASURE_MS;
    w.__perf.windowStart = performance.now();
    w.__perf.windowEnd = w.__perf.windowStart + ms;
    return { start: w.__perf.windowStart, end: w.__perf.windowEnd, durationMs: ms };
  };
  w.__perfWindowElapsed = () => (w.__perf.windowStart === null ? 0 : performance.now() - w.__perf.windowStart);
  w.__perfNow = () => performance.now();
  w.__perfInWindow = (t) => inFixedWindow(t);
  w.__perfFocusAt = () => ({ now: performance.now(), hasFocus: document.hasFocus(), inWindow: inFixedWindow(performance.now()) });

  // DOM-side qualification snapshot (defect 4): focus, visibility, viewport
  // size and DPR, read together so the driver never assumes them.
  w.__perfDomQual = () => ({
    now: performance.now(),
    hasFocus: document.hasFocus(),
    visible: document.visibilityState === "visible",
    innerWidth: w.innerWidth,
    innerHeight: w.innerHeight,
    devicePixelRatio: w.devicePixelRatio,
  });

  // SINGLE actual Canvas image-buffer read. Returns the 800 cell-center RGBA
  // bytes, the backing dimensions, AND the read timestamp (defect 5), or null.
  w.__perfReadCanvasCenters = (selector) => {
    const readNow = performance.now();
    const canvas = document.querySelector(selector);
    if (!canvas || !canvas.getContext) return null;
    const width = canvas.width;
    const height = canvas.height;
    if (!width || !height) return null;
    let ctx;
    try { ctx = canvas.getContext("2d"); } catch (_) { return null; }
    if (!ctx) return null;
    let img;
    try { img = ctx.getImageData(0, 0, width, height); } catch (_) { return null; }
    const data = img.data;
    const cellW = width / BOARD_COLS;
    const cellH = height / BOARD_ROWS;
    const out = new Array(BOARD_CELLS * 4);
    let k = 0;
    for (let r = 0; r < BOARD_ROWS; r++) {
      for (let c = 0; c < BOARD_COLS; c++) {
        let x = Math.round((c + 0.5) * cellW);
        let y = Math.round((r + 0.5) * cellH);
        if (x < 0) x = 0; if (x > width - 1) x = width - 1;
        if (y < 0) y = 0; if (y > height - 1) y = height - 1;
        const idx = (y * width + x) * 4;
        out[k++] = data[idx];
        out[k++] = data[idx + 1];
        out[k++] = data[idx + 2];
        out[k++] = data[idx + 3];
      }
    }
    return { rgba: out, width, height, readNow };
  };

  w.__perfCanvasPresent = (selector) => {
    const canvas = document.querySelector(selector);
    return !!(canvas && canvas.getContext && canvas.width > 0 && canvas.height > 0);
  };

  // CORRECTION 24 (defect 2): a strictly READ-ONLY capture-phase keydown
  // recorder. It records each REAL source keydown's monotonically increasing
  // sequence, key, performance.now() event time, isTrusted, document.hasFocus()
  // and fixed-window membership. It NEVER calls preventDefault/stopPropagation,
  // never dispatches, and never hooks or replaces the app's own handlers; it
  // only observes. The driver snapshots the sequence before ONE keyboard.press
  // and selects exactly one new matching trusted event afterward, using that
  // event's own timestamp as the latency start.
  w.__perfInstallKeydownRecorder = () => {
    if (w.__perf.keydownInstalled) return true;
    w.__perf.keydownInstalled = true;
    document.addEventListener("keydown", (ev) => {
      const now = performance.now();
      w.__perf.keydownSeq += 1;
      w.__perf.keydowns.push({
        seq: w.__perf.keydownSeq,
        key: ev.key,
        at: now,
        isTrusted: ev.isTrusted === true,
        hasFocus: document.hasFocus(),
        inWindow: inFixedWindow(now),
      });
    }, true); // capture-phase, passive observation only
    return true;
  };
  w.__perfKeydownSeq = () => w.__perf.keydownSeq;
  // Return keydown records recorded AFTER a snapshot sequence value. The driver
  // uses this to find the single new source event produced by its one press.
  w.__perfKeydownsSince = (sinceSeq) =>
    w.__perf.keydowns.filter((k) => k.seq > (typeof sinceSeq === "number" ? sinceSeq : 0));
  // CORRECTION 24 (defect 6): set an ORDINARY document.title (plain metadata
  // only) so a controller can identify the owned window. No window is activated
  // here; this only writes document.title.
  w.__perfSetWindowTitle = (title) => {
    if (typeof title === "string" && title.length) document.title = title;
    return document.title;
  };

  w.__perfHasFocus = () => document.hasFocus();
})();
`;

// Observed-mask read + read timestamp. Returns { mask, width, height, readNow }
// or null. The timestamp comes from the SAME browser call as the pixel read.
async function readObservedMask(page, selector) {
  const res = await page.evaluate((sel) => window.__perfReadCanvasCenters(sel), selector);
  if (!res || !Array.isArray(res.rgba)) return null;
  const mask = maskFromCenterRgba(res.rgba);
  if (!mask) return null;
  // CORRECTION 24 (defect 4): retain the RAW RGBA800 bytes and dimensions
  // alongside the derived mask and the same-call read time, so a retained
  // candidate can persist the raw actor/peer pixel reads and peer visible
  // latency is reconstructible from the raw records.
  return { mask, rgba: res.rgba, width: res.width, height: res.height, readNow: res.readNow };
}

async function waitForCanvasReady(page, selector, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    // eslint-disable-next-line no-await-in-loop
    const ready = await page.evaluate((sel) => {
      if (document.readyState !== "complete") return false;
      return window.__perfCanvasPresent(sel);
    }, selector);
    if (ready) {
      await page.evaluate(() => window.__perfStartRaf());
      return true;
    }
    // eslint-disable-next-line no-await-in-loop
    await page.waitForTimeout(100);
  }
  return false;
}

async function takeCalibration(page) {
  const startNs = process.hrtime.bigint();
  const browserMs = await page.evaluate(() => window.__perfNow());
  const endNs = process.hrtime.bigint();
  const gapMs = Number(endNs - startNs) / 1e6;
  const midNs = startNs + (endNs - startNs) / 2n;
  return calibrationPoint(midNs, browserMs, gapMs);
}

// ---------------------------------------------------------------------------
// Passive HTTP observation (Playwright events only). Solo actions are POSTs to
// /api/games/{id}/{move|rotate|hold}; /tick is GRAVITY and must NOT prove an
// action. CORRECTION 23 (defect 3): each solo action is correlated by the
// SPECIFIC request object started after dispatch whose route+body match the
// pressed key, plus that request's own response. A /tick response or an older
// latest response is never that proof.
// Parse the solo game_id from a /api/games/{id}/... URL. Null if absent.
function gameIdFromUrl(url) {
  if (typeof url !== "string") return null;
  const m = url.match(/\/api\/games\/([^/]+)\//);
  return m ? m[1] : null;
}

function installPassiveHttpObserver(page, store) {
  // CORRECTION 24 (defect 3): a WeakMap binds each Playwright request OBJECT to
  // its start record so the response is associated with the SAME request, not a
  // route/time heuristic. The response record then retains that request's id,
  // its start time, and the game_id.
  const reqStartByObject = new WeakMap();
  page.on("request", (req) => {
    const url = req.url();
    if (!url.includes("/api/")) return;
    const startNs = process.hrtime.bigint().toString();
    const rec = {
      kind: "request",
      reqId: `${store.http.length}-${Date.now()}`,
      url,
      method: req.method(),
      postData: req.postData() ?? null,
      atNs: startNs,
      startNs,
      gameId: gameIdFromUrl(url),
      clock: DOMAIN_NODE,
      _req: req,
    };
    reqStartByObject.set(req, rec);
    store.http.push(rec);
  });
  page.on("requestfinished", async (req) => {
    const url = req.url();
    if (!url.includes("/api/")) return;
    let status = null;
    let state = null;
    let resp = null;
    try { resp = await req.response(); status = resp ? resp.status() : null; } catch (_) {}
    const isStateRoute =
      req.method() === "POST" &&
      (url.includes("/move") || url.includes("/rotate") || url.includes("/tick") || url.includes("/hold"));
    const isGravityTick = url.includes("/tick");
    if (resp && status != null && status >= 200 && status < 300 && isStateRoute) {
      try { state = await resp.json(); } catch (_) { state = null; }
    }
    // Same-request identity via the WeakMap (never a nearest-in-time guess).
    const startRec = reqStartByObject.get(req) ?? null;
    const record = {
      kind: "response",
      url,
      method: req.method(),
      status,
      state,
      postData: (() => { try { return req.postData() ?? null; } catch (_) { return null; } })(),
      isGravityTick,
      reqId: startRec ? startRec.reqId : null,
      startNs: startRec ? startRec.startNs : null,
      gameId: startRec ? startRec.gameId : gameIdFromUrl(url),
      atNs: process.hrtime.bigint().toString(),
      clock: DOMAIN_NODE,
    };
    store.http.push(record);
    // Only NON-tick successful action responses are candidate solo proofs.
    if (state && !isGravityTick) store.soloActionResponses.push(record);
  });
  page.on("requestfailed", (req) => {
    const url = req.url();
    if (!url.includes("/api/")) return;
    store.http.push({ kind: "failed", url, method: req.method(), atNs: process.hrtime.bigint().toString(), clock: DOMAIN_NODE });
  });
}

// The body direction a solo action POST carries ("left"/"right"/"down" for
// /move; "cw"/"ccw" for /rotate). Returns null if not parseable.
function soloActionIdentity(record) {
  if (!record || record.kind !== "response") return null;
  const url = record.url;
  let kind = null;
  let dir = null;
  try {
    const body = record.postData ? JSON.parse(record.postData) : null;
    dir = body && typeof body.direction === "string" ? body.direction : null;
  } catch (_) { dir = null; }
  if (url.includes("/move")) kind = "move";
  else if (url.includes("/rotate")) kind = "rotate";
  else if (url.includes("/hold")) kind = "hold";
  return { kind, dir };
}

// CORRECTION 23 (defect 3): duel passive WS observer records the OWNED room/seat
// (welcome), the OUTGOING action frames (framesent), the ACKs/rejects correlated
// by action_id, and the per-(room,seat,revision) StateFrames. An opponent-seat
// state frame is retained for rendering but NEVER as owned authoritative proof.
export function ingestDuelFrame(store, msg, atNs, direction) {
  if (!msg || typeof msg !== "object") return store;
  if (direction === "sent") {
    if (msg.type === "action" && typeof msg.action_id === "string") {
      store.outgoingActions.push({
        actionId: msg.action_id,
        room: msg.room_id ?? null,
        seat: msg.seat_id ?? null,
        kind: msg.kind ?? null,
        expectedRevision: typeof msg.expected_revision === "number" ? msg.expected_revision : null,
        atNs,
      });
      store.outgoingByActionId[msg.action_id] = store.outgoingActions[store.outgoingActions.length - 1];
    }
    return store;
  }
  // inbound
  if (msg.type === "welcome" && typeof msg.seat_id === "string") {
    store.ownedRoom = msg.room_id ?? null;
    store.ownedSeat = msg.seat_id;
    store.ownedRoomStatus = msg.room_status ?? null;
  }
  if (msg.type === "ack" && typeof msg.action_id === "string") {
    store.acksByActionId[msg.action_id] = {
      actionId: msg.action_id,
      room: msg.room_id ?? null,
      seat: msg.seat_id ?? null,
      revision: typeof msg.revision === "number" ? msg.revision : null,
      applied: msg.applied === true,
      noOp: msg.no_op === true,
      atNs,
    };
  }
  if (msg.type === "reject" && typeof msg.action_id === "string") {
    store.rejectsByActionId[msg.action_id] = {
      actionId: msg.action_id,
      room: msg.room_id ?? null,
      seat: msg.seat_id ?? null,
      reason: msg.reason ?? null,
      authoritativeRevision: typeof msg.authoritative_revision === "number" ? msg.authoritative_revision : null,
      atNs,
    };
  }
  if (msg.type === "state" && Array.isArray(msg.board)) {
    const key = `${msg.room_id}|${msg.seat_id}|${msg.revision}`;
    store.stateByRoomSeatRev[key] = { msg, atNs };
    if (typeof msg.room_status === "string" && msg.seat_id === store.ownedSeat) {
      store.ownedRoomStatus = msg.room_status;
    }
    if (store.ownedSeat != null && msg.seat_id === store.ownedSeat) {
      store.latestDuelState = { msg, atNs };
      if (typeof msg.revision === "number" && (store.ownedRevHigh == null || msg.revision > store.ownedRevHigh)) {
        store.ownedRevHigh = msg.revision;
      }
    }
    store.latestAnyState = { msg, atNs };
  }
  return store;
}

function installPassiveWsObserver(page, store) {
  page.on("websocket", (ws) => {
    const url = ws.url();
    if (!url.includes("/ws/")) return;
    store.ws.push({ kind: "open", url, atNs: process.hrtime.bigint().toString(), clock: DOMAIN_NODE });
    ws.on("framesent", (data) => {
      const payload = safeWsText(data);
      store.ws.push({ kind: "sent", url, payload, atNs: process.hrtime.bigint().toString(), clock: DOMAIN_NODE });
      if (typeof payload === "string") {
        try { ingestDuelFrame(store, JSON.parse(payload), process.hrtime.bigint().toString(), "sent"); } catch (_) {}
      }
    });
    ws.on("framereceived", (data) => {
      const payload = safeWsText(data);
      const record = { kind: "received", url, payload, atNs: process.hrtime.bigint().toString(), clock: DOMAIN_NODE };
      store.ws.push(record);
      if (typeof payload === "string") {
        try { ingestDuelFrame(store, JSON.parse(payload), record.atNs, "received"); } catch (_) {}
      }
    });
    ws.on("close", () => {
      store.ws.push({ kind: "close", url, atNs: process.hrtime.bigint().toString(), clock: DOMAIN_NODE });
    });
  });
}

function safeWsText(data) {
  try {
    const payload = data && data.payload !== undefined ? data.payload : data;
    if (typeof payload === "string") return payload.length > 4096 ? payload.slice(0, 4096) : payload;
    return null;
  } catch (_) {
    return null;
  }
}

// Build a fresh passive store with all correlation maps the readers need.
function newPassiveStore() {
  return {
    http: [],
    ws: [],
    soloActionResponses: [],
    outgoingActions: [],
    outgoingByActionId: {},
    acksByActionId: {},
    rejectsByActionId: {},
    stateByRoomSeatRev: {},
    ownedRoom: null,
    ownedSeat: null,
    ownedRoomStatus: null,
    ownedRevHigh: null,
    latestDuelState: null,
    latestAnyState: null,
  };
}

// ---------------------------------------------------------------------------
// CORRECTION 23 (defect 3): correlate ONE dispatched input to its authoritative
// effect. Solo: pick the specific /move|/rotate POST started after dispatch
// whose route+body direction match the pressed key; use ITS response state.
// A /tick (gravity) or an older response is never that proof. Solo action_id /
// revision may legitimately be null.
export function soloActionCorrelate(store, { expectedKind, expectedDir, dispatchAtNs }) {
  // expectedKind: "move" | "rotate" | "hold"; expectedDir: "left"/"right"/"down"/"cw"/"ccw"/null.
  // CORRECTION 24 (defect 3): the matching response's REQUEST must have STARTED
  // AFTER this input's dispatch (compare request startNs, not the finish time),
  // so an older same-direction request already in flight before dispatch can
  // NEVER qualify. When startNs is unknown the response cannot prove an
  // after-dispatch request and is skipped.
  const after = BigInt(dispatchAtNs);
  let chosen = null;
  for (const rec of store.soloActionResponses) {
    if (rec.startNs == null) continue;             // no proven request start -> cannot qualify
    if (BigInt(rec.startNs) < after) continue;     // request started before dispatch -> older in-flight
    const id = soloActionIdentity(rec);
    if (!id || id.kind !== expectedKind) continue;
    if (expectedDir != null && id.dir !== expectedDir) continue;
    // earliest request that started after dispatch (by request start time)
    if (!chosen || BigInt(rec.startNs) < BigInt(chosen.startNs)) chosen = rec;
  }
  if (!chosen || !chosen.state) {
    return { state: null, accepted: null, reason: "no_matching_solo_response" };
  }
  const state = chosen.state;
  return {
    state,
    actionId: null,            // solo has no protocol action_id
    revision: typeof state.revision === "number" ? state.revision : null,
    room: null,
    seat: null,
    accepted: true,            // a matched 2xx action response is an accepted state
    rejectReason: null,
    isNoOp: null,
    scalarOnly: null,
    gravityOnly: null,
    correlation: null,         // not applicable for solo
    // Persisted HTTP request identity (defect 3): same-request reqId / start /
    // game_id tie the sample to the exact request object that produced it.
    httpReqId: chosen.reqId ?? null,
    httpStartNs: chosen.startNs ?? null,
    gameId: chosen.gameId ?? null,
    matchedResponseAtNs: chosen.atNs,
  };
}

// Duel: correlate the outgoing action_id -> its ACK (accepted/no_op) -> the
// StateFrame at the ACK revision for THAT room/seat. The StateFrame has no
// action_id, so the ACK is the ONLY bridge. A reject sets accepted=false. An
// opponent or gravity state, or a wrong room/seat/revision, cannot qualify.
export function duelActionCorrelate(store, { actionId }) {
  if (!actionId) return { state: null, accepted: null, reason: "no_action_id" };
  const reject = store.rejectsByActionId[actionId];
  if (reject) {
    return {
      state: null,
      actionId,
      revision: reject.authoritativeRevision ?? null,
      room: reject.room,
      seat: reject.seat,
      accepted: false,
      rejectReason: reject.reason,
      isNoOp: null,
      scalarOnly: null,
      gravityOnly: null,
      correlation: { roomOk: false, seatOk: false, revisionOk: false },
      reason: "rejected",
    };
  }
  const ack = store.acksByActionId[actionId];
  if (!ack) return { state: null, accepted: null, actionId, reason: "no_ack_yet" };
  const key = `${ack.room}|${ack.seat}|${ack.revision}`;
  const stateRec = store.stateByRoomSeatRev[key];
  const ownedSeat = store.ownedSeat ?? null;
  const ownedRoom = store.ownedRoom ?? null;
  const correlation = {
    roomOk: ownedRoom != null && ack.room === ownedRoom,
    seatOk: ownedSeat != null && ack.seat === ownedSeat,
    revisionOk: typeof ack.revision === "number" && !!stateRec,
  };
  if (!stateRec || !stateRec.msg) {
    return {
      state: null,
      actionId,
      revision: ack.revision,
      room: ack.room,
      seat: ack.seat,
      accepted: true,
      rejectReason: null,
      isNoOp: ack.noOp,
      scalarOnly: null,
      gravityOnly: null,
      correlation,
      reason: "no_state_at_ack_revision_yet",
    };
  }
  const msg = stateRec.msg;
  const state = { board: msg.board, active_piece: msg.active_piece ?? null, revision: msg.revision };
  return {
    state,
    actionId,
    revision: msg.revision,
    room: msg.room_id ?? null,
    seat: msg.seat_id ?? null,
    accepted: true,
    rejectReason: null,
    isNoOp: ack.noOp,
    scalarOnly: null,
    gravityOnly: null,
    correlation,
    ackAtNs: ack.atNs,
    stateAtNs: stateRec.atNs,
  };
}

// Kept for backward compatibility with the self-check: a passive owned-seat
// authoritative snapshot with a DERIVED correlation (never hardcoded true).
export async function duelAuthoritativeState(page, passive) {
  const rec = passive.latestDuelState;
  if (!rec || !rec.msg) return null;
  const msg = rec.msg;
  const state = { board: msg.board, active_piece: msg.active_piece ?? null, revision: msg.revision };
  const ownedSeat = passive.ownedSeat ?? null;
  const ownedRoom = passive.ownedRoom ?? null;
  const revHigh = passive.ownedRevHigh ?? null;
  const correlation = {
    roomOk: ownedRoom != null ? msg.room_id === ownedRoom : false,
    seatOk: ownedSeat != null ? msg.seat_id === ownedSeat : false,
    revisionOk: typeof msg.revision === "number" && revHigh != null && msg.revision === revHigh,
  };
  return {
    state,
    actionId: null,
    revision: typeof msg.revision === "number" ? msg.revision : null,
    room: msg.room_id ?? null,
    seat: msg.seat_id ?? null,
    accepted: true,
    rejectReason: null,
    isNoOp: null,
    scalarOnly: null,
    gravityOnly: null,
    correlation,
  };
}

// Pure derivation of per-sample focus / window / superseded proof from ACTUAL
// telemetry. Unknown inputs yield false (never an assumed true).
export function deriveSampleProof({ dispatchFocus, updateFocus, matched, laterInputDispatched }) {
  const df = dispatchFocus || {};
  const uf = updateFocus || null;
  const focusOk = df.hasFocus === true && (uf ? uf.hasFocus === true : false);
  const dispatchInWindow = df.inWindow === true;
  const updateInWindow = uf ? uf.inWindow === true : false;
  const superseded = matched === false && laterInputDispatched === true;
  return { focusOk, dispatchInWindow, updateInWindow, superseded };
}

// ---------------------------------------------------------------------------
// Page setup helpers. Each page gets the passive observers and the read-only
// instrument installed BEFORE navigation.
async function setupPage(context, store) {
  const page = await context.newPage();
  installPassiveHttpObserver(page, store);
  installPassiveWsObserver(page, store);
  await page.addInitScript(INSTRUMENT);
  return page;
}

// CORRECTION 24 (defect 2/6): after a page is loaded, install the read-only
// keydown recorder and set an ordinary document.title so the source events are
// recorded and the owned window is identifiable. Title ending differs for actor
// (ends "INPUT") vs peer so the controller can target exactly the actor window.
async function activatePageRecorders(page, title) {
  await page.evaluate(() => window.__perfInstallKeydownRecorder());
  if (typeof title === "string") {
    await page.evaluate((t) => window.__perfSetWindowTitle(t), title);
  }
}

// Select the Solo tab only when it is NOT already selected (defect 2: the Solo
// tab is disabled while selected, so clicking it would hang).
async function ensureSoloSelected(page) {
  const selected = await page.getAttribute(SELECTOR.modeTabSolo, "aria-selected").catch(() => null);
  if (selected !== "true") {
    await page.click(SELECTOR.modeTabSolo);
  }
}

// Join a duel room on a page: select the Duel tab by role/name, type the room
// name, and click Create or join.
async function joinDuelRoom(page, roomName) {
  await page.click(SELECTOR.modeTabDuel);
  await page.fill(SELECTOR.roomNameInput, roomName);
  await page.click(SELECTOR.createOrJoinButton);
}

// Wait until the OWNED-seat room_status is "playing" for a page's passive
// store. Returns true if observed before the timeout.
async function waitForRoomPlaying(page, store, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (store.ownedRoomStatus === "playing") return true;
    // eslint-disable-next-line no-await-in-loop
    await page.waitForTimeout(100);
  }
  return store.ownedRoomStatus === "playing";
}

// Drive ONE measured input and correlate its authoritative effect + observed
// pixels. Input is dispatched on the driver's own cadence, ONCE, never inside a
// poll predicate, and never repeated to force a success (Req 27.12, defect 3).
async function driveOneInput({
  mode, label, index, actorPage, peerPage, store, canvasSelector, peerSelector,
  actorCalibration, peerCalibration, samples, excluded,
}) {
  const action = DECLARED_PATTERN[index % DECLARED_PATTERN.length];
  const key = keyForAction(action);
  if (!key) return;

  const sourceInputId = `${label}-src-${index}`;
  const before = await readObservedMask(actorPage, canvasSelector);
  const dispatchFocus = await actorPage.evaluate(() => window.__perfFocusAt());
  const dispatchAtNs = process.hrtime.bigint().toString();
  const dispatchIndex = index;

  // Snapshot the outgoing-action count (duel) so we can identify THIS input's
  // action_id as the next sent frame after dispatch.
  const sentBefore = mode === "duel" ? store.outgoingActions.length : 0;

  // CORRECTION 24 (defect 2): snapshot the read-only keydown recorder sequence
  // BEFORE the single press so we can select exactly the ONE new event this
  // press produced.
  const keydownSeqBefore = await actorPage.evaluate(() => window.__perfKeydownSeq());

  // SINGLE real keydown (trusted browser input).
  await actorPage.keyboard.press(key);

  // CORRECTION 24 (defect 2): select EXACTLY ONE new matching trusted keydown
  // event recorded after the snapshot, and use ITS own timestamp as the latency
  // start (not the preceding __perfFocusAt read). Zero matches, more than one
  // match, or an untrusted event make the source event unknown/ambiguous, which
  // excludes the sample downstream (sourceEvent stays null).
  let sourceEvent = null;
  let sourceEventReason = null;
  {
    const evDeadline = Date.now() + 500;
    let candidates = [];
    // eslint-disable-next-line no-constant-condition
    while (true) {
      // eslint-disable-next-line no-await-in-loop
      const since = await actorPage.evaluate((seq) => window.__perfKeydownsSince(seq), keydownSeqBefore);
      candidates = Array.isArray(since) ? since.filter((e) => e && e.key === key && e.isTrusted === true) : [];
      if (candidates.length >= 1 || Date.now() > evDeadline) break;
      // eslint-disable-next-line no-await-in-loop
      await actorPage.waitForTimeout(8);
    }
    if (candidates.length === 1) {
      sourceEvent = candidates[0];
    } else if (candidates.length === 0) {
      sourceEventReason = "no_trusted_source_keydown";
    } else {
      sourceEventReason = "ambiguous_multiple_source_keydowns";
    }
  }
  // The ACTUAL source-event timestamp drives latency; unknown/ambiguous/
  // untrusted -> null (excluded), never the preceding evaluate read.
  const tDispatch = sourceEvent ? sourceEvent.at : null;

  // Duel: discover the action_id this keypress produced (the next sent frame).
  let actionId = null;
  if (mode === "duel") {
    const idDeadline = Date.now() + 1000;
    while (Date.now() < idDeadline) {
      if (store.outgoingActions.length > sentBefore) {
        actionId = store.outgoingActions[sentBefore].actionId;
        break;
      }
      // eslint-disable-next-line no-await-in-loop
      await actorPage.waitForTimeout(16);
    }
  }

  // Expected direction for solo body-identity correlation.
  const expectedKind = action === "cw" || action === "ccw" ? "rotate" : (action === "hold" ? "hold" : "move");
  const expectedDir = expectedKind === "rotate" ? action : (expectedKind === "move" ? action : null);

  const settleDeadline = Date.now() + ACTION_SETTLE_TIMEOUT_MS;
  let observedMatch = null;
  let expectedMask = null;
  let authoritative = null;
  let tUpdate = null;
  let updateFocus = null;
  let peerObservedMatch = null;
  let peerReadNow = null;

  while (Date.now() < settleDeadline) {
    // eslint-disable-next-line no-await-in-loop
    authoritative = mode === "duel"
      ? duelActionCorrelate(store, { actionId })
      : soloActionCorrelate(store, { expectedKind, expectedDir, dispatchAtNs });
    if (authoritative && authoritative.state) {
      expectedMask = expectedRgbMaskFromState(authoritative.state);
    }
    // eslint-disable-next-line no-await-in-loop
    const obs = await readObservedMask(actorPage, canvasSelector);
    if (expectedMask && obs && masksEqual(expectedMask, obs.mask).equal) {
      observedMatch = obs;
      // eslint-disable-next-line no-await-in-loop
      updateFocus = await actorPage.evaluate(() => window.__perfFocusAt());
      tUpdate = obs.readNow; // SAME-call read timestamp (defect 5)
      // Peer pixel match to the SAME authoritative actor effect (duel only).
      if (mode === "duel" && peerPage) {
        // eslint-disable-next-line no-await-in-loop
        const peerObs = await readObservedMask(peerPage, peerSelector);
        if (peerObs && masksEqual(expectedMask, peerObs.mask).equal) {
          peerObservedMatch = peerObs;
          peerReadNow = peerObs.readNow;
        }
      }
      break;
    }
    // eslint-disable-next-line no-await-in-loop
    await actorPage.waitForTimeout(16);
  }

  const observedMask = observedMatch ? observedMatch.mask : null;

  // CORRECTION 24 (defect 2): dispatch focus/window proof comes from the ACTUAL
  // source keydown event (its own hasFocus/inWindow). With no proven source
  // event, dispatch proof is UNKNOWN (null) so the sample cannot positively
  // qualify. The pre-press __perfFocusAt read is retained only as recorded
  // telemetry, never as the latency start.
  const dispatchProof = sourceEvent
    ? { hasFocus: sourceEvent.hasFocus, inWindow: sourceEvent.inWindow, now: sourceEvent.at }
    : { hasFocus: null, inWindow: null, now: null };

  const { focusOk, dispatchInWindow, updateInWindow, superseded } = deriveSampleProof({
    dispatchFocus: dispatchProof,
    updateFocus,
    matched: observedMatch !== null,
    laterInputDispatched: (samples.length + excluded.length) > dispatchIndex,
  });

  // Actor latency on the actor's OWN browser clock (never cross-clock), measured
  // from the ACTUAL source-event time to the same-call observed-read time.
  let latencyMs = null;
  if (typeof tDispatch === "number" && typeof tUpdate === "number") {
    latencyMs = sameDomainDuration(stamp(DOMAIN_BROWSER, tDispatch), stamp(DOMAIN_BROWSER, tUpdate));
  }

  // CORRECTION 24 (defect 4): peer latency is NOT computed here with a pre-only
  // calibration. The RAW peer read time and actor dispatch time are persisted so
  // finalizeTrial recomputes peer mapped latency with the FINAL pre+post
  // calibrations (drift uncertainty included). The in-flight actorCalibration/
  // peerCalibration args are intentionally unused for the persisted result.
  void actorCalibration; void peerCalibration;

  const candidate = {
    sourceInputId,
    action,
    key,
    // Raw source-event record (defect 2/4): the actual keydown this press made.
    sourceEvent: sourceEvent
      ? { seq: sourceEvent.seq, key: sourceEvent.key, at: sourceEvent.at, isTrusted: sourceEvent.isTrusted, hasFocus: sourceEvent.hasFocus, inWindow: sourceEvent.inWindow }
      : null,
    sourceEventReason: sourceEventReason ?? null,
    prePressFocus: dispatchFocus ?? null,
    pieceType: authoritative && authoritative.state && authoritative.state.active_piece ? authoritative.state.active_piece.type : null,
    actionId: authoritative ? authoritative.actionId ?? null : null,
    revision: authoritative ? authoritative.revision ?? null : null,
    room: authoritative ? authoritative.room ?? null : null,
    seat: authoritative ? authoritative.seat ?? null : null,
    accepted: authoritative ? authoritative.accepted ?? null : null,
    rejectReason: authoritative ? authoritative.rejectReason ?? null : null,
    isNoOp: authoritative ? authoritative.isNoOp ?? null : null,
    scalarOnly: authoritative ? authoritative.scalarOnly ?? null : null,
    gravityOnly: authoritative ? authoritative.gravityOnly ?? null : null,
    // Persisted HTTP request identity for solo (defect 3), null for duel.
    httpReqId: authoritative ? authoritative.httpReqId ?? null : null,
    httpStartNs: authoritative ? authoritative.httpStartNs ?? null : null,
    gameId: authoritative ? authoritative.gameId ?? null : null,
    superseded,
    correlation: mode === "duel" && authoritative ? authoritative.correlation ?? null : null,
    beforeMask: before ? before.mask : null,
    expectedMask: expectedMask ?? null,
    observedMask,
    // Raw actor pixel read (defect 4): RGBA800 / mask / time / dimensions.
    actorPixelRead: observedMatch
      ? { rgba: observedMatch.rgba, mask: observedMatch.mask, width: observedMatch.width, height: observedMatch.height, readNow: observedMatch.readNow }
      : null,
    // Raw peer pixel read (defect 4): RGBA800 / mask / time / dimensions, so the
    // peer visible latency is reconstructible from the raw records.
    peerPixelRead: peerObservedMatch
      ? { rgba: peerObservedMatch.rgba, mask: peerObservedMatch.mask, width: peerObservedMatch.width, height: peerObservedMatch.height, readNow: peerObservedMatch.readNow }
      : null,
    peerMatched: mode === "duel" ? peerObservedMatch !== null : null,
    peerReadNow: typeof peerReadNow === "number" ? peerReadNow : null,
    focusOk,
    dispatchInWindow,
    updateInWindow,
    latencyMs,
    // Peer latency is recomputed at summary time; left null here on purpose.
    peerLatencyMs: null,
    peerLatencyUncertaintyMs: null,
    peerLatencyReason: null,
    tDispatch,
    tUpdate,
    clock: DOMAIN_BROWSER,
  };

  const verdict = qualifyActionSample(candidate);
  candidate.qualified = verdict.qualified;
  candidate.reason = verdict.reason;
  if (verdict.qualified) {
    samples.push(candidate);
  } else {
    excluded.push({ ...candidate, reason: verdict.reason });
  }
}

// ---------------------------------------------------------------------------
// Warm-up: drive the pattern but record nothing (window not yet open).
async function warmUp(actorPage, mode, store, canvasSelector, durationMs) {
  const deadline = Date.now() + durationMs;
  let i = 0;
  while (Date.now() < deadline) {
    const action = DECLARED_PATTERN[i % DECLARED_PATTERN.length];
    const key = keyForAction(action);
    i += 1;
    if (key) {
      // eslint-disable-next-line no-await-in-loop
      await actorPage.keyboard.press(key);
    }
    // eslint-disable-next-line no-await-in-loop
    await actorPage.waitForTimeout(INPUT_INTERVAL_MS);
  }
}

// Run ONE trial (solo or duel). `isProbe` shortens the measured window and
// marks the result as a NON-performance probe. For duel, `actorBrowser` and
// `peerBrowser` are connected clients; the actor page drives input and the peer
// page is observed read-only.
async function runTrial({
  mode, trialIndex, label, isProbe, outDir,
  actorBrowser, peerBrowser, actorPid, peerPid, actorHwnds,
}) {
  const trialDir = path.join(outDir, label);
  fs.mkdirSync(trialDir, { recursive: true });
  const startedAt = new Date().toISOString();
  const measureMs = isProbe ? PROBE_MEASURE_MS : MEASURE_MS;

  const store = newPassiveStore();
  const peerStore = mode === "duel" ? newPassiveStore() : null;

  const actorContext = await actorBrowser.newContext({ viewport: VIEWPORT, deviceScaleFactor: DEVICE_SCALE_FACTOR });
  await actorContext.tracing.start({ screenshots: true, snapshots: true });
  const actorPage = await setupPage(actorContext, store);

  let peerContext = null;
  let peerPage = null;
  if (mode === "duel") {
    peerContext = await peerBrowser.newContext({ viewport: VIEWPORT, deviceScaleFactor: DEVICE_SCALE_FACTOR });
    peerPage = await setupPage(peerContext, peerStore);
  }

  const samples = [];
  const excluded = [];
  const qualSamples = [];
  let calibrationPre = null;
  let calibrationPost = null;
  let peerCalibrationPre = null;
  let peerCalibrationPost = null;
  let captureEndAt = null;
  let failure = null;

  const canvasSelector = mode === "duel" ? SELECTOR.actorCanvas : SELECTOR.soloCanvas;
  const peerSelector = SELECTOR.peerCanvas;

  try {
    await actorPage.goto(TARGET_URL, { waitUntil: "load" });
    if (mode === "duel") {
      const room = `perf-${label}-${Date.now()}`;
      await peerPage.goto(TARGET_URL, { waitUntil: "load" });
      // Both A and B join the SAME fresh room (defect 2).
      await joinDuelRoom(actorPage, room);
      await joinDuelRoom(peerPage, room);
      const aPlaying = await waitForRoomPlaying(actorPage, store, DUEL_JOIN_TIMEOUT_MS);
      const bPlaying = await waitForRoomPlaying(peerPage, peerStore, DUEL_JOIN_TIMEOUT_MS);
      if (!aPlaying || !bPlaying) {
        failure = `duel did not reach room_status=playing on BOTH clients (A=${store.ownedRoomStatus}, B=${peerStore.ownedRoomStatus})`;
      }
    } else {
      await ensureSoloSelected(actorPage);
    }

    // CORRECTION 24 (defect 2/6): install the read-only keydown recorder on both
    // pages and give the ACTOR a unique title ending "INPUT" and the PEER a
    // distinct title, BEFORE the READY_FOR_FOREGROUND signal, so the controller
    // can identify and activate exactly the actor-owned window. Plain
    // document.title metadata only; no window is activated here.
    const actorTitle = `TETRIS-PERF ${mode} ${label} ACTOR INPUT`;
    const peerTitle = `TETRIS-PERF ${mode} ${label} PEER VIEW`;
    if (!failure) {
      await activatePageRecorders(actorPage, actorTitle);
      if (mode === "duel" && peerPage) await activatePageRecorders(peerPage, peerTitle);
    }

    const ready = !failure && await waitForCanvasReady(actorPage, canvasSelector, BOARD_READY_TIMEOUT_MS);
    const peerReady = mode === "duel" && !failure ? await waitForCanvasReady(peerPage, peerSelector, BOARD_READY_TIMEOUT_MS) : true;
    if (!failure && (!ready || !peerReady)) {
      failure = `target canvas not ready before warm-up (actor=${ready}, peer=${peerReady})`;
    }

    // Identify the owned actor window(s) READ-ONLY and emit READY_FOR_FOREGROUND
    // carrying the ACTUAL actor identity (defect 2, 4). Never force foreground.
    let actorWindowInfo = actorHwnds ?? null;
    if (!failure) {
      actorWindowInfo = await enumerateWindowsForPid(actorPid);
      const firstTitle = actorWindowInfo && Array.isArray(actorWindowInfo.windows) && actorWindowInfo.windows.length
        ? actorWindowInfo.windows[0].title : null;
      const firstHwnd = actorWindowInfo && Array.isArray(actorWindowInfo.windows) && actorWindowInfo.windows.length
        ? actorWindowInfo.windows[0].hwnd : null;
      // Pick the owned window whose title matches the DOM title we set (ends
      // "INPUT"); fall back to the first enumerated window only if none match.
      const windows = actorWindowInfo && Array.isArray(actorWindowInfo.windows) ? actorWindowInfo.windows : [];
      const owned = windows.find((wnd) => typeof wnd.title === "string" && wnd.title.includes("ACTOR INPUT")) ?? null;
      const chosenTitle = owned ? owned.title : firstTitle;
      const chosenHwnd = owned ? owned.hwnd : firstHwnd;
      const signal = readyForForegroundSignal({ actorPid, actorTitle: chosenTitle, actorHwnd: chosenHwnd });
      console.log(JSON.stringify(signal));
    }

    // Wait boundedly for a real OS foreground transition (controller/user acts).
    let fg = { observed: false, finalSample: null };
    if (!failure) {
      fg = await waitForForegroundTransition({ actorPid, deadlineMs: FOREGROUND_WAIT_MS });
    }

    if (!failure) {
      calibrationPre = await takeCalibration(actorPage);
      if (mode === "duel") peerCalibrationPre = await takeCalibration(peerPage);

      await warmUp(actorPage, mode, store, canvasSelector, WARMUP_MS);

      await actorPage.evaluate((ms) => window.__perfMarkWindowStart(ms), measureMs);
      if (mode === "duel") await peerPage.evaluate((ms) => window.__perfMarkWindowStart(ms), measureMs);

      const calibration = summarizeCalibration(calibrationPre, null);
      const peerCalibration = mode === "duel" ? summarizeCalibration(peerCalibrationPre, null) : null;

      const hardDeadline = Date.now() + measureMs + 5000;
      let index = 0;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        // eslint-disable-next-line no-await-in-loop
        const elapsed = await actorPage.evaluate(() => window.__perfWindowElapsed());
        if (elapsed >= measureMs || Date.now() > hardDeadline) break;
        // Per-input OS+DOM qualification sample (defect 4): record it, and
        // invalidate the trial if foreground/DOM qualification is lost.
        // eslint-disable-next-line no-await-in-loop
        const dom = await actorPage.evaluate(() => window.__perfDomQual());
        // eslint-disable-next-line no-await-in-loop
        const fgSample = await readForegroundWindow();
        const q = qualifyActorWindow({ foregroundSample: fgSample, actorPid, dom });
        qualSamples.push({ atMs: Date.now(), qualified: q.qualified, failing: q.failing, osForeground: q.osForeground });
        // eslint-disable-next-line no-await-in-loop
        await driveOneInput({
          mode, label, index, actorPage, peerPage, store, canvasSelector, peerSelector,
          actorCalibration: calibration, peerCalibration, samples, excluded,
        });
        index += 1;
        // eslint-disable-next-line no-await-in-loop
        await actorPage.waitForTimeout(INPUT_INTERVAL_MS);
      }
      try { captureEndAt = await actorPage.evaluate(() => window.__perfStopSamplers()); } catch (_) {}
      calibrationPost = await takeCalibration(actorPage);
      if (mode === "duel") peerCalibrationPost = await takeCalibration(peerPage);
    }

    const perf = await actorPage.evaluate(() => window.__perf).catch(() => null);
    await actorPage.screenshot({ path: path.join(trialDir, "final.png") }).catch(() => {});
    await actorContext.tracing.stop({ path: path.join(trialDir, "trace.zip") }).catch(() => {});

    return finalizeTrial({
      label, trialIndex, mode, isProbe, startedAt, perf, samples, excluded, qualSamples,
      calibrationPre, calibrationPost, peerCalibrationPre, peerCalibrationPost,
      captureEndAt, store, peerStore, trialDir, failure, measureMs,
      actorPid, peerPid, actorWindowInfo, foreground: fg,
    });
  } catch (err) {
    failure = (failure ? failure + "; " : "") + `exception: ${err && err.stack ? err.stack : String(err)}`;
    let perf = null;
    try { perf = await actorPage.evaluate(() => window.__perf); } catch (_) {}
    try { await actorContext.tracing.stop({ path: path.join(trialDir, "trace.zip") }); } catch (_) {}
    try { await actorPage.screenshot({ path: path.join(trialDir, "final.png") }); } catch (_) {}
    return finalizeTrial({
      label, trialIndex, mode, isProbe, startedAt, perf, samples, excluded, qualSamples,
      calibrationPre, calibrationPost, peerCalibrationPre, peerCalibrationPost,
      captureEndAt, store, peerStore, trialDir, failure, measureMs,
      actorPid, peerPid, actorWindowInfo: null, foreground: { observed: false, finalSample: null },
    });
  } finally {
    try { await actorContext.close(); } catch (_) {}
    if (peerContext) { try { await peerContext.close(); } catch (_) {} }
  }
}

// Build the per-trial result. Scheduling targets stay SEPARATE from
// qualification. Unknown fields are null, never 0. A trial is FAILED if there
// was a failure, the full window was not observed, OR any per-input OS/DOM
// qualification sample failed (defect 4: lost/wrong foreground invalidates).
function finalizeTrial({
  label, trialIndex, mode, isProbe, startedAt, perf, samples, excluded, qualSamples,
  calibrationPre, calibrationPost, peerCalibrationPre, peerCalibrationPost,
  captureEndAt, store, peerStore, trialDir, failure, measureMs,
  actorPid, peerPid, actorWindowInfo, foreground,
}) {
  const safePerf = perf ?? {};
  const windowIntervals = (safePerf.frames ?? []).filter((f) => f.inWindow).map((f) => f.interval);
  const sortedIntervals = windowIntervals.slice().sort((a, b) => a - b);
  const meanInterval = sortedIntervals.length
    ? sortedIntervals.reduce((a, b) => a + b, 0) / sortedIntervals.length
    : null;
  const meanFps = meanInterval ? 1000 / meanInterval : null;
  const p95Interval = sortedIntervals.length
    ? sortedIntervals[Math.min(sortedIntervals.length - 1, Math.floor(0.95 * sortedIntervals.length))]
    : null;
  const schedulingTargets = evaluateSchedulingTargets(meanFps, p95Interval);

  // Final calibrations FIRST (pre+post), so peer latency is mapped through the
  // complete calibration with drift uncertainty, not a pre-only offset.
  const calibration = summarizeCalibration(calibrationPre, calibrationPost);
  const peerCalibration = mode === "duel" ? summarizeCalibration(peerCalibrationPre, peerCalibrationPost) : null;

  // CORRECTION 24 (defect 4): recompute each qualified duel sample's peer mapped
  // latency from its RAW persisted records (actor source-event dispatch time +
  // raw peer read time) using the FINAL pre+post calibrations. Unknown /
  // uncalibrated -> null with a reason; a negative result is kept (not clamped)
  // and excluded by its own reason, never silently zeroed.
  if (mode === "duel") {
    for (const s of samples) {
      if (typeof s.tDispatch === "number" && typeof s.peerReadNow === "number") {
        const pl = peerLatencyThroughNode({
          actorDispatchBrowserMs: s.tDispatch,
          actorCalibration: calibration,
          peerUpdateBrowserMs: s.peerReadNow,
          peerCalibration,
        });
        s.peerLatencyMs = pl.latencyMs;
        s.peerLatencyUncertaintyMs = pl.uncertaintyMs;
        s.peerLatencyReason = pl.reason;
      } else {
        s.peerLatencyMs = null;
        s.peerLatencyUncertaintyMs = null;
        s.peerLatencyReason = "missing_raw_peer_or_dispatch_record";
      }
    }
  }

  const latencies = samples.map((s) => s.latencyMs).filter((x) => typeof x === "number");
  const latencyStats = summarizeLatencies(latencies);
  // Only NON-negative peer latencies are summarized; a negative mapped latency
  // is reported as an exclusion reason and not clamped into the stats.
  const peerLatencies = samples
    .map((s) => s.peerLatencyMs)
    .filter((x) => typeof x === "number" && x >= 0);
  const peerLatencyStats = summarizeLatencies(peerLatencies);
  const duelPeerMatchCount = mode === "duel" ? samples.filter((s) => s.peerMatched === true).length : null;
  const duelPeerLatencyCount = mode === "duel" ? peerLatencies.length : null;

  const fullWindowObserved =
    safePerf.windowStart != null &&
    safePerf.windowEnd != null &&
    captureEndAt != null &&
    captureEndAt >= safePerf.windowEnd - WINDOW_OBSERVED_TOLERANCE_MS;

  const qualAll = qualSamples.length > 0 && qualSamples.every((q) => q.qualified === true);
  const foregroundObserved = foreground && foreground.observed === true;

  const pngStat = artifactStat(path.join(trialDir, "final.png"));
  const traceStat = artifactStat(path.join(trialDir, "trace.zip"));

  const writeJson = (name, value) => {
    try { fs.writeFileSync(path.join(trialDir, name), JSON.stringify(value ?? null, null, 2)); } catch (_) {}
  };
  writeJson("frames.json", safePerf.frames ?? []);
  writeJson("samples.json", samples);
  writeJson("excluded.json", excluded);
  writeJson("qualification.json", qualSamples);
  writeJson("http.json", store ? store.http : []);
  writeJson("ws.json", store ? store.ws : []);
  writeJson("outgoing-actions.json", store ? store.outgoingActions : []);
  writeJson("acks.json", store ? store.acksByActionId : {});
  writeJson("rejects.json", store ? store.rejectsByActionId : {});
  writeJson("peer-ws.json", peerStore ? peerStore.ws : null);
  writeJson("calibration.json", calibration);
  writeJson("peer-calibration.json", peerCalibration);
  writeJson("foreground.json", foreground ?? null);
  writeJson("actor-window.json", actorWindowInfo ?? null);

  // CORRECTION 24 (defect 5): the SINGLE centralized validity predicate decides
  // failure. Empty frame/action data, invalid calibration, lost OS/DOM
  // qualification, an unobserved full window, or (duel) missing peer matches /
  // peer latency all invalidate the trial. Probes are NOT exempt from the OS
  // foreground + DOM qualification requirement.
  const validity = trialIsInvalid({
    mode,
    isProbe: !!isProbe,
    hasFailure: !!failure,
    fullWindowObserved,
    frameSampleCount: windowIntervals.length,
    qualifiedSampleCount: samples.length,
    calibrationValid: calibration ? calibration.calibrated === true : false,
    qualificationAllPassed: qualAll,
    foregroundObserved,
    duelPeerMatchCount,
    duelPeerLatencyCount,
  });
  const failed = validity.invalid;

  const result = {
    trial: label,
    trialIndex: trialIndex + 1,
    mode,
    isProbe: !!isProbe,
    resultKind: isProbe ? "short_probe_NOT_a_performance_result" : "full_trial",
    startedAt,
    finishedAt: new Date().toISOString(),
    failed,
    failure: failure ?? null,
    invalidReasons: validity.reasons,
    ownedChromePid: actorPid ?? null,
    peerChromePid: peerPid ?? null,
    foregroundTransitionObserved: foregroundObserved,
    qualificationAllPassed: qualAll,
    qualificationSampleCount: qualSamples.length,
    scenario: {
      targetUrl: TARGET_URL,
      viewport: VIEWPORT,
      deviceScaleFactor: DEVICE_SCALE_FACTOR,
      channel: BROWSER_CHANNEL,
      headful: true,
      sandbox: true,
      warmupMs: WARMUP_MS,
      measureMs,
      inputPattern: DECLARED_PATTERN,
      inputIntervalMs: INPUT_INTERVAL_MS,
    },
    window: {
      start: safePerf.windowStart ?? null,
      end: safePerf.windowEnd ?? null,
      captureEndAt: captureEndAt ?? safePerf.captureEndAt ?? null,
      fullWindowObserved,
    },
    scheduling: {
      ...schedulingTargets,
      frameSamples: windowIntervals.length,
      meanIntervalMs: meanInterval,
    },
    actionLatency: {
      qualifiedCount: latencyStats.count,
      excludedCount: excluded.length,
      median: latencyStats.median,
      p95: latencyStats.p95,
      p99: latencyStats.p99,
      excludedReasons: excluded.map((e) => ({ sourceInputId: e.sourceInputId, action: e.action, reason: e.reason })),
      note:
        "Actor dispatch-to-observed-CHANGED-200-cell-Canvas-mask latency on the actor browser " +
        "performance clock ONLY. Gravity/scalar-only, no-op/O-rotation, stale/rate-rejected, " +
        "superseded, out-of-window, unproven-focus/window/correlation samples are EXCLUDED with " +
        "reasons. NOT input-to-photon or physical display presentation latency.",
    },
    peerActionLatency: mode === "duel" ? {
      qualifiedCount: peerLatencyStats.count,
      median: peerLatencyStats.median,
      p95: peerLatencyStats.p95,
      p99: peerLatencyStats.p99,
      excludedReasons: samples
        .filter((s) => s.peerLatencyReason != null || !(typeof s.peerLatencyMs === "number" && s.peerLatencyMs >= 0))
        .map((s) => ({ sourceInputId: s.sourceInputId, reason: s.peerLatencyReason ?? (typeof s.peerLatencyMs === "number" && s.peerLatencyMs < 0 ? "negative_peer_latency_not_clamped" : "no_peer_latency") })),
      note:
        "Peer action-to-opponent-visible latency RECOMPUTED at summary time from the raw " +
        "persisted actor source-event dispatch time and raw peer pixel-read time, mapped through " +
        "calibrated Node common time using the FINAL pre+post calibrations (drift uncertainty " +
        "included). Actor and peer browser clocks are distinct and NEVER subtracted raw; the " +
        "summed calibration uncertainty is reported and negative results are excluded, not clamped.",
    } : null,
    calibration,
    peerCalibration,
    evidence: {
      finalPng: pngStat.exists ? "final.png" : null,
      finalPngBytes: pngStat.size,
      trace: traceStat.exists ? "trace.zip" : null,
      traceBytes: traceStat.size,
    },
  };
  writeJson("summary.json", result);
  return result;
}

// ---------------------------------------------------------------------------
// OWNED-Chrome PID via the PUBLIC chromium.launchServer().process().pid, plus a
// chromium.connect(wsEndpoint) client (defect 1). Browser.process() is
// UNDEFINED on this build, so it is NOT used. BOTH the server and the connected
// browser are returned so the caller can clean up: close the connected browser,
// then close/kill the server.
async function launchServerAndConnect(chromium, launchOptions) {
  const server = await chromium.launchServer(launchOptions);
  const proc = server.process();
  const pid = proc && typeof proc.pid === "number" ? proc.pid : null;
  const browser = await chromium.connect(server.wsEndpoint());
  return { server, browser, pid };
}

async function closeServerAndBrowser(handle) {
  if (!handle) return;
  try { if (handle.browser) await handle.browser.close(); } catch (_) {}
  try { if (handle.server) await handle.server.close(); } catch (_) {}
}

// ---------------------------------------------------------------------------
// CLI. Modes (defect 7):
//   solo | duel | all                       -> full performance trials
//   solo-probe | duel-probe                 -> SHORT probes (NOT performance)
//   trial <solo|duel> [--label X]           -> ONE labelled full trial
// Exits NONZERO if no trial executed OR required data is invalid/empty.
export async function main(argv = process.argv.slice(2)) {
  const mode = argv[0] ?? null;
  const VALID = ["solo", "duel", "all", "solo-probe", "duel-probe", "trial"];
  if (!mode || !VALID.includes(mode)) {
    console.error(
      "No trial executed: a mode is required (" + VALID.join("|") + "). " +
        "Implementation and self-checks do NOT run a measured trial.",
    );
    process.exitCode = 3;
    return { trialsExecuted: 0, reason: "no_trial_mode" };
  }

  // Parse `trial <kind> [--label X]`.
  let singleKind = null;
  let singleLabel = null;
  if (mode === "trial") {
    singleKind = argv[1] ?? null;
    if (!["solo", "duel"].includes(singleKind)) {
      console.error("trial requires a kind: trial solo | trial duel");
      process.exitCode = 3;
      return { trialsExecuted: 0, reason: "bad_trial_kind" };
    }
    const li = argv.indexOf("--label");
    singleLabel = li >= 0 && argv[li + 1] ? argv[li + 1] : `${singleKind}-trial`;
  }

  const isProbe = mode === "solo-probe" || mode === "duel-probe";
  const probeKind = mode === "solo-probe" ? "solo" : mode === "duel-probe" ? "duel" : null;

  const { chromium } = await import("playwright");

  const outDir = newOutDir(mode === "trial" ? singleLabel : mode);
  fs.mkdirSync(outDir, { recursive: true });
  const batchStartedAt = new Date().toISOString();
  const launchOptions = { headless: false, channel: BROWSER_CHANNEL, chromiumSandbox: true };

  // Decide the trial plan.
  const plan = [];
  if (mode === "all") {
    for (let i = 0; i < SOLO_TRIALS; i += 1) plan.push({ kind: "solo", index: i, isProbe: false, label: `solo-${i + 1}` });
    for (let i = 0; i < DUEL_TRIALS; i += 1) plan.push({ kind: "duel", index: i, isProbe: false, label: `duel-${i + 1}` });
  } else if (mode === "solo") {
    for (let i = 0; i < SOLO_TRIALS; i += 1) plan.push({ kind: "solo", index: i, isProbe: false, label: `solo-${i + 1}` });
  } else if (mode === "duel") {
    for (let i = 0; i < DUEL_TRIALS; i += 1) plan.push({ kind: "duel", index: i, isProbe: false, label: `duel-${i + 1}` });
  } else if (isProbe) {
    plan.push({ kind: probeKind, index: 0, isProbe: true, label: `${probeKind}-probe` });
  } else if (mode === "trial") {
    plan.push({ kind: singleKind, index: 0, isProbe: false, label: singleLabel });
  }

  const trials = [];
  let trialsExecuted = 0;

  for (const item of plan) {
    let actorHandle = null;
    let peerHandle = null;
    try {
      // eslint-disable-next-line no-await-in-loop
      actorHandle = await launchServerAndConnect(chromium, launchOptions);
      if (item.kind === "duel") {
        // eslint-disable-next-line no-await-in-loop
        peerHandle = await launchServerAndConnect(chromium, launchOptions);
      }
      // eslint-disable-next-line no-await-in-loop
      const r = await runTrial({
        mode: item.kind, trialIndex: item.index, label: item.label, isProbe: item.isProbe, outDir,
        actorBrowser: actorHandle.browser, peerBrowser: peerHandle ? peerHandle.browser : null,
        actorPid: actorHandle.pid, peerPid: peerHandle ? peerHandle.pid : null, actorHwnds: null,
      });
      trials.push(r);
      trialsExecuted += 1;
    } finally {
      // eslint-disable-next-line no-await-in-loop
      await closeServerAndBrowser(peerHandle);
      // eslint-disable-next-line no-await-in-loop
      await closeServerAndBrowser(actorHandle);
    }
  }

  let playwrightVersion = null;
  try { playwrightVersion = (await import("playwright/package.json", { with: { type: "json" } })).default.version; } catch (_) {}

  const report = {
    batchStartedAt,
    batchFinishedAt: new Date().toISOString(),
    mode,
    isProbe,
    resultKind: isProbe ? "short_probe_NOT_a_performance_result" : "performance_trials",
    trialsExecuted,
    trials,
    versions: { node: process.version, playwright: playwrightVersion, channel: BROWSER_CHANNEL },
    runtime: {
      platform: os.platform(),
      release: os.release(),
      arch: os.arch(),
      cpu: os.cpus().map((c) => c.model)[0] ?? null,
      cpuCount: os.cpus().length,
      totalMemBytes: os.totalmem(),
      gpu: null,
      display: "unknown; physical foreground display presentation is NOT observable and is reported as unknown",
    },
    honestyNote:
      "Samples are not pooled across trials; no statistical-significance, scalability, or " +
      "physical-presentation claim is made. rAF scheduling (>=55 FPS mean, <=25 ms p95) is a " +
      "SCHEDULING TARGET only. Probes are NOT performance results. Unknown fields are null, never zero.",
  };
  try { fs.writeFileSync(path.join(outDir, "report.json"), JSON.stringify(report, null, 2)); } catch (_) {}

  console.log(`Benchmark complete. Results: ${outDir}`);
  console.log(`Trials executed: ${trialsExecuted}`);

  // Required-data validity (defect 7): a non-probe run must have at least one
  // trial, and no executed trial may have failed, else exit nonzero. An empty
  // run is never a success.
  const anyFailed = trials.some((t) => t.failed === true);
  if (trialsExecuted === 0) {
    process.exitCode = 4;
  } else if (anyFailed) {
    process.exitCode = 5;
  } else {
    process.exitCode = 0;
  }
  return { trialsExecuted, outDir, anyFailed };
}

const INVOKED_DIRECTLY = (() => {
  try {
    return path.resolve(process.argv[1] ?? "") === path.resolve(fileURLToPath(import.meta.url));
  } catch (_) {
    return false;
  }
})();

if (INVOKED_DIRECTLY) {
  main().catch((err) => {
    console.error("Benchmark failed:", err && err.stack ? err.stack : err);
    process.exitCode = 2;
  });
}
