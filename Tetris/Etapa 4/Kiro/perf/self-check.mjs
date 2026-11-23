// Harness OWN semantic self-checks (task 20.2; driver-correction 23).
//
// These DRIVE THE REAL exported harness logic (the pure helpers AND the ACTUAL
// correlation/driver functions in benchmark.mjs) and assert each DELIBERATELY
// REJECTS a distinct defective input. They are NOT mirror tests. This file runs
// NO measured production trial, probe, or window: it imports the pure helpers
// (which launch nothing) and spawns the CLI with NO trial mode (which launches
// nothing and exits nonzero). Run: node self-check.mjs (from perf/). Exit 0 iff
// every deliberate rejection was observed.

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  REASON,
  qualifyActionSample,
  trialIsInvalid,
} from "./lib/exclusions.mjs";
import {
  DOMAIN_NODE,
  DOMAIN_BROWSER,
  DOMAIN_PEER_BROWSER,
  assertSameDomain,
  sameDomainDuration,
  stamp,
  summarizeCalibration,
  calibrationPoint,
  peerLatencyThroughNode,
} from "./lib/clock.mjs";
import {
  BOARD_CELLS,
  COLORS,
  TYPE_CODE,
  expectedRgbMaskFromState,
  hexToRgb,
} from "./lib/palette.mjs";
import {
  deriveSampleProof,
  ingestDuelFrame,
  duelAuthoritativeState,
  duelActionCorrelate,
  soloActionCorrelate,
} from "./benchmark.mjs";
import { qualifyActorWindow } from "./lib/foreground.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const checks = [];
function record(name, passed, detail) { checks.push({ name, passed: !!passed, detail: detail ?? null }); }
function expect(name, condition, detail) { record(name, condition, detail); }

function uniformMask(hex) {
  const rgb = hexToRgb(hex);
  return new Array(BOARD_CELLS).fill(0).map(() => ({ ...rgb }));
}

function stateWithActivePiece(type) {
  const board = Array.from({ length: 20 }, () => new Array(10).fill(0));
  return {
    board,
    active_piece: { type, origin: [0, 3], cells: [[0, 3], [0, 4], [0, 5], [0, 6]] },
    revision: 1,
  };
}

function qualifyingCandidate() {
  const state = stateWithActivePiece("T");
  const expectedMask = expectedRgbMaskFromState(state);
  const beforeMask = uniformMask(COLORS[0]);
  return {
    action: "cw",
    pieceType: "T",
    beforeMask,
    expectedMask,
    observedMask: expectedMask.map((c) => ({ ...c })),
    accepted: true,
    rejectReason: null,
    isNoOp: false,
    scalarOnly: false,
    gravityOnly: false,
    superseded: false,
    correlation: { roomOk: true, seatOk: true, revisionOk: true },
    focusOk: true,
    dispatchInWindow: true,
    updateInWindow: true,
    latencyMs: 12.5,
  };
}

// SANITY: the un-perturbed base candidate QUALIFIES via the real qualifier.
{
  const v = qualifyActionSample(qualifyingCandidate());
  expect("sanity: un-perturbed candidate qualifies via the real qualifier",
    v.qualified === true && v.reason === null, `got qualified=${v.qualified} reason=${v.reason}`);
}

// CHECK 1 - wrong cell mask rejected.
{
  const c = qualifyingCandidate();
  c.observedMask = c.observedMask.map((cell) => ({ ...cell }));
  c.observedMask[42] = { r: 1, g: 2, b: 3 };
  const v = qualifyActionSample(c);
  expect("1. wrong cell mask -> rejected (expected_changed_mask_never_rendered)",
    v.qualified === false && v.reason === REASON.EXPECTED_MASK_NEVER_RENDERED, `got qualified=${v.qualified} reason=${v.reason}`);
}

// CHECK 2a - scalar-only rejected.
{
  const c = qualifyingCandidate(); c.scalarOnly = true;
  const v = qualifyActionSample(c);
  expect("2a. scalar-only change -> rejected (scalar_only_change)",
    v.qualified === false && v.reason === REASON.SCALAR_ONLY, `got qualified=${v.qualified} reason=${v.reason}`);
}

// CHECK 2b-i / 2b-ii - no-op rejected.
{
  const c = qualifyingCandidate(); c.action = "cw"; c.pieceType = "O"; c.isNoOp = true;
  const v = qualifyActionSample(c);
  expect("2b-i. O-rotation no-op -> rejected (o_rotation_unchanged_mask)",
    v.qualified === false && v.reason === REASON.O_ROTATION_UNCHANGED, `got qualified=${v.qualified} reason=${v.reason}`);
}
{
  const c = qualifyingCandidate(); c.isNoOp = false; c.scalarOnly = false; c.gravityOnly = false;
  const bg = uniformMask(COLORS[0]);
  c.beforeMask = bg.map((x) => ({ ...x }));
  c.observedMask = bg.map((x) => ({ ...x }));
  c.expectedMask = bg.map((x) => ({ ...x }));
  const v = qualifyActionSample(c);
  expect("2b-ii. unchanged-mask no-op (observed==before) -> rejected (no_op_unchanged_mask)",
    v.qualified === false && v.reason === REASON.NO_OP_UNCHANGED_MASK, `got qualified=${v.qualified} reason=${v.reason}`);
}

// CHECK 3 - wrong correlation rejected.
for (const [which, corr] of [
  ["room", { roomOk: false, seatOk: true, revisionOk: true }],
  ["seat", { roomOk: true, seatOk: false, revisionOk: true }],
  ["revision", { roomOk: true, seatOk: true, revisionOk: false }],
]) {
  const c = qualifyingCandidate(); c.correlation = corr;
  const v = qualifyActionSample(c);
  expect(`3. wrong ${which} correlation -> rejected (wrong_room_seat_or_revision)`,
    v.qualified === false && v.reason === REASON.WRONG_CORRELATION, `got qualified=${v.qualified} reason=${v.reason}`);
}

// CHECK 4 - cross-clock refused; same-domain works; negative not clamped.
{
  const nodeSample = stamp(DOMAIN_NODE, 100);
  const browserSample = stamp(DOMAIN_BROWSER, 50);
  let threw = false; let message = null;
  try { assertSameDomain(nodeSample, browserSample); } catch (err) { threw = true; message = err && err.message ? err.message : String(err); }
  expect("4a. cross-clock subtraction -> assertSameDomain THROWS",
    threw === true && typeof message === "string" && message.includes("cross-clock"), `threw=${threw} message=${message}`);
  let durThrew = false;
  try { sameDomainDuration(nodeSample, browserSample); } catch (_) { durThrew = true; }
  expect("4b. sameDomainDuration cross-domain -> THROWS via the guard", durThrew === true, `durThrew=${durThrew}`);
  const d = sameDomainDuration(stamp(DOMAIN_BROWSER, 20), stamp(DOMAIN_BROWSER, 35));
  expect("4c. same-domain subtraction returns the real interval", d === 15, `got ${d}`);
  const neg = sameDomainDuration(stamp(DOMAIN_BROWSER, 40), stamp(DOMAIN_BROWSER, 25));
  expect("4d. same-domain negative interval is NOT clamped (returned as -15)", neg === -15, `got ${neg}`);
  const c = qualifyingCandidate(); c.latencyMs = neg;
  const v = qualifyActionSample(c);
  expect("4e. negative latency sample -> rejected (negative_latency_not_clamped)",
    v.qualified === false && v.reason === REASON.NEGATIVE_INTERVAL && v.latencyMs === -15,
    `got qualified=${v.qualified} reason=${v.reason} latencyMs=${v.latencyMs}`);
}

// CHECK 5 - invalid focus rejected.
{
  const c = qualifyingCandidate(); c.focusOk = false;
  const v = qualifyActionSample(c);
  expect("5. invalid focus -> rejected (unqualified_focus)",
    v.qualified === false && v.reason === REASON.UNQUALIFIED_FOCUS, `got qualified=${v.qualified} reason=${v.reason}`);
}

// CHECK 6 - out of window rejected.
{
  const c1 = qualifyingCandidate(); c1.dispatchInWindow = false;
  const v1 = qualifyActionSample(c1);
  expect("6a. dispatch out of fixed window -> rejected (out_of_fixed_window)",
    v1.qualified === false && v1.reason === REASON.OUT_OF_WINDOW, `got qualified=${v1.qualified} reason=${v1.reason}`);
  const c2 = qualifyingCandidate(); c2.updateInWindow = false;
  const v2 = qualifyActionSample(c2);
  expect("6b. update out of fixed window -> rejected (out_of_fixed_window)",
    v2.qualified === false && v2.reason === REASON.OUT_OF_WINDOW, `got qualified=${v2.qualified} reason=${v2.reason}`);
}

// CHECK P1 (defect 6) - NULL (unknown) proof is NOT acceptance. The exact
// counterexample that previously qualified now REJECTS via the real qualifier.
{
  const changed = new Array(BOARD_CELLS).fill(0).map(() => ({ r: 34, g: 211, b: 238 }));
  const bg = uniformMask(COLORS[0]);
  const s = { accepted: null, focusOk: null, dispatchInWindow: null, updateInWindow: null, latencyMs: 2, beforeMask: bg, expectedMask: changed, observedMask: changed };
  const v = qualifyActionSample(s);
  expect("P1. null-proof sample {accepted,focusOk,dispatchInWindow,updateInWindow all null} -> REJECTED",
    v.qualified === false && v.reason === REASON.UNPROVEN_ACCEPTED, `got qualified=${v.qualified} reason=${v.reason}`);
}
// P1b - each positive-proof field independently: null focus/window/correlation reject.
{
  const c = qualifyingCandidate(); c.focusOk = null;
  expect("P1b. unknown focus (null) -> REJECTED (focus_not_positively_qualified)",
    (() => { const v = qualifyActionSample(c); return v.qualified === false && v.reason === REASON.UNPROVEN_FOCUS; })(), "null focusOk");
  const c2 = qualifyingCandidate(); c2.dispatchInWindow = null;
  expect("P1c. unknown dispatch window (null) -> REJECTED (window_not_positively_proven)",
    (() => { const v = qualifyActionSample(c2); return v.qualified === false && v.reason === REASON.UNPROVEN_WINDOW; })(), "null dispatchInWindow");
  const c3 = qualifyingCandidate(); c3.correlation = { roomOk: true, seatOk: true, revisionOk: null };
  expect("P1d. unknown correlation (revisionOk null) -> REJECTED (correlation_not_positively_proven)",
    (() => { const v = qualifyActionSample(c3); return v.qualified === false && v.reason === REASON.UNPROVEN_CORRELATION; })(), "null revisionOk");
}

// CHECK 7 - no-op CLI exits nonzero and launches nothing.
async function runCliNoTrial() {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, ["benchmark.mjs"], { cwd: __dirname, windowsHide: true });
    let stdout = ""; let stderr = "";
    const timer = setTimeout(() => { try { child.kill(); } catch (_) {} resolve({ code: null, stdout, stderr, timedOut: true }); }, 20000);
    child.stdout.on("data", (d) => { stdout += d.toString(); });
    child.stderr.on("data", (d) => { stderr += d.toString(); });
    child.on("error", (err) => { clearTimeout(timer); resolve({ code: null, stdout, stderr, spawnError: String(err) }); });
    child.on("close", (code) => { clearTimeout(timer); resolve({ code, stdout, stderr, timedOut: false }); });
  });
}
const cli = await runCliNoTrial();
expect("7a. no-op CLI (no mode) exits NONZERO with code 3", cli.code === 3,
  `exit code=${cli.code} timedOut=${cli.timedOut ?? false} spawnError=${cli.spawnError ?? "none"}`);
expect("7b. no-op CLI reports no trial executed", typeof cli.stderr === "string" && /No trial executed/i.test(cli.stderr),
  `stderr=${JSON.stringify((cli.stderr || "").slice(0, 300))}`);
expect("7c. no-op CLI printed NO 'Benchmark complete'", typeof cli.stdout === "string" && !/Benchmark complete/i.test(cli.stdout),
  `stdout=${JSON.stringify((cli.stdout || "").slice(0, 300))}`);

// ---------------------------------------------------------------------------
// DRIVER-LEVEL counterfactuals using the ACTUAL driver/correlation functions.
const dummyPage = { evaluate() { throw new Error("self-check must not call page.evaluate"); } };

// Build a passive store the way benchmark.mjs does (via ingestDuelFrame), with
// all the maps the correlators read.
function freshDuelStore() {
  return {
    http: [], ws: [], soloActionResponses: [], outgoingActions: [], outgoingByActionId: {},
    acksByActionId: {}, rejectsByActionId: {}, stateByRoomSeatRev: {},
    ownedRoom: null, ownedSeat: null, ownedRoomStatus: null, ownedRevHigh: null,
    latestDuelState: null, latestAnyState: null,
  };
}
function duelStateFrame(seat, rev, room = "perf-room", roomStatus = "playing") {
  return { type: "state", room_id: room, seat_id: seat, revision: rev, room_status: roomStatus,
    board: Array.from({ length: 20 }, () => new Array(10).fill(0)), active_piece: null };
}

// D1 - deriveSampleProof refuses to produce true from defective telemetry.
{
  const unfocused = deriveSampleProof({ dispatchFocus: { hasFocus: false, inWindow: true }, updateFocus: { hasFocus: true, inWindow: true }, matched: true, laterInputDispatched: false });
  expect("D1a. unfocused dispatch -> focusOk=false", unfocused.focusOk === false, JSON.stringify(unfocused));
  const noUpdate = deriveSampleProof({ dispatchFocus: { hasFocus: true, inWindow: true }, updateFocus: null, matched: false, laterInputDispatched: false });
  expect("D1b. no matched update -> focusOk=false AND updateInWindow=false", noUpdate.focusOk === false && noUpdate.updateInWindow === false, JSON.stringify(noUpdate));
  const overtaken = deriveSampleProof({ dispatchFocus: { hasFocus: true, inWindow: true }, updateFocus: null, matched: false, laterInputDispatched: true });
  expect("D1c. unrendered + overtaken -> superseded=true", overtaken.superseded === true, JSON.stringify(overtaken));
  const good = deriveSampleProof({ dispatchFocus: { hasFocus: true, inWindow: true }, updateFocus: { hasFocus: true, inWindow: true }, matched: true, laterInputDispatched: true });
  expect("D1d. fully-valid telemetry -> all proof true (non-vacuous)", good.focusOk === true && good.dispatchInWindow === true && good.updateInWindow === true && good.superseded === false, JSON.stringify(good));
}

// D2 - duelActionCorrelate ties action_id -> ACK -> StateFrame at ACK revision.
{
  const store = freshDuelStore();
  ingestDuelFrame(store, { type: "welcome", room_id: "perf-room", seat_id: "A", room_status: "waiting" }, "1", "received");
  // outgoing action
  ingestDuelFrame(store, { type: "action", room_id: "perf-room", seat_id: "A", action_id: "A-1", expected_revision: 4, kind: "cw" }, "2", "sent");
  // No ACK yet -> not accepted (unknown).
  const pending = duelActionCorrelate(store, { actionId: "A-1" });
  expect("D2a. action with NO ack yet -> accepted=null (unproven), not qualified", pending.accepted === null && !pending.state, JSON.stringify({ accepted: pending.accepted, reason: pending.reason }));
  // ACK arrives at revision 5, then the state frame at revision 5.
  ingestDuelFrame(store, { type: "ack", room_id: "perf-room", seat_id: "A", action_id: "A-1", revision: 5, applied: true, no_op: false }, "3", "received");
  ingestDuelFrame(store, duelStateFrame("A", 5), "4", "received");
  const done = duelActionCorrelate(store, { actionId: "A-1" });
  expect("D2b. action -> ack -> state@rev correlated true", done.state && done.accepted === true && done.correlation.roomOk === true && done.correlation.seatOk === true && done.correlation.revisionOk === true, JSON.stringify(done.correlation));
}

// D3 - an OPPONENT-seat state frame cannot become our authoritative proof, and
// the ack->state bridge cannot resolve to an opponent/wrong state.
{
  const store = freshDuelStore();
  ingestDuelFrame(store, { type: "welcome", room_id: "perf-room", seat_id: "A", room_status: "playing" }, "1", "received");
  // Opponent (B) ACK + state must NOT satisfy our owned-seat correlation.
  ingestDuelFrame(store, { type: "action", room_id: "perf-room", seat_id: "A", action_id: "A-2", expected_revision: 1, kind: "cw" }, "2", "sent");
  ingestDuelFrame(store, { type: "ack", room_id: "perf-room", seat_id: "B", action_id: "A-2", revision: 9, applied: true, no_op: false }, "3", "received");
  ingestDuelFrame(store, duelStateFrame("B", 9), "4", "received");
  const wrong = duelActionCorrelate(store, { actionId: "A-2" });
  expect("D3a. opponent-seat ack/state -> seatOk=false (cannot qualify)", wrong.correlation && wrong.correlation.seatOk === false, JSON.stringify(wrong.correlation));
  const sample = { ...qualifyingCandidate(), correlation: wrong.correlation, accepted: wrong.accepted };
  const v = qualifyActionSample(sample);
  expect("D3b. opponent-correlated sample -> qualifier REJECTS (wrong_room_seat_or_revision)", v.qualified === false && v.reason === REASON.WRONG_CORRELATION, `got qualified=${v.qualified} reason=${v.reason}`);
}

// D4 - a REJECTED duel action cannot qualify (accepted=false).
{
  const store = freshDuelStore();
  ingestDuelFrame(store, { type: "welcome", room_id: "perf-room", seat_id: "A", room_status: "playing" }, "1", "received");
  ingestDuelFrame(store, { type: "action", room_id: "perf-room", seat_id: "A", action_id: "A-3", expected_revision: 2, kind: "cw" }, "2", "sent");
  ingestDuelFrame(store, { type: "reject", room_id: "perf-room", seat_id: "A", action_id: "A-3", reason: "stale_revision", authoritative_revision: 7 }, "3", "received");
  const rej = duelActionCorrelate(store, { actionId: "A-3" });
  expect("D4a. rejected action -> accepted=false with rejectReason", rej.accepted === false && rej.rejectReason === "stale_revision", JSON.stringify({ accepted: rej.accepted, rejectReason: rej.rejectReason }));
  const sample = { ...qualifyingCandidate(), accepted: false, rejectReason: "stale_revision" };
  const v = qualifyActionSample(sample);
  expect("D4b. rejected sample -> qualifier REJECTS (stale)", v.qualified === false && v.reason === REASON.STALE_REVISION, `got reason=${v.reason}`);
}

// D5 - solo correlation uses the SPECIFIC move/rotate response after dispatch;
// a /tick (gravity) response is NOT that proof.
{
  const store = { soloActionResponses: [] };
  // CORRECTION 24 (defect 3): a response carries its request START time; the
  // correlator requires startNs > dispatchAtNs. Here the request started at 60
  // (after dispatch 50) and finished at 100.
  const mkResp = (url, dir, startNs, atNs, rev) => ({ kind: "response", url, postData: dir ? JSON.stringify({ direction: dir }) : null, state: { board: Array.from({ length: 20 }, () => new Array(10).fill(0)), active_piece: null, revision: rev }, reqId: `r-${rev}`, startNs, gameId: "1", atNs });
  // A matching rotate response whose request STARTED after dispatch.
  store.soloActionResponses.push(mkResp("http://x/api/games/1/rotate", "cw", "60", "100", 10));
  const r = soloActionCorrelate(store, { expectedKind: "rotate", expectedDir: "cw", dispatchAtNs: "50" });
  expect("D5a. solo rotate correlated by body identity after dispatch", r.state && r.revision === 10 && r.accepted === true, JSON.stringify({ rev: r.revision, accepted: r.accepted }));
  const none = soloActionCorrelate(store, { expectedKind: "move", expectedDir: "left", dispatchAtNs: "50" });
  expect("D5b. no matching solo response -> accepted=null (not qualified)", none.state === null && none.accepted === null, JSON.stringify({ reason: none.reason }));
}

// D6 - distinct actor/peer clocks are transformed through Node, or refused.
{
  const cal = (off, u) => ({ pre: { offsetMs: off }, post: { offsetMs: off }, uncertaintyMs: u });
  const r = peerLatencyThroughNode({ actorDispatchBrowserMs: 100, actorCalibration: cal(1000, 2), peerUpdateBrowserMs: 150, peerCalibration: cal(1050, 3) });
  expect("D6a. peer latency mapped through Node common time (not raw subtraction)", r.latencyMs === 100 && r.uncertaintyMs === 5 && r.domain === DOMAIN_NODE, JSON.stringify(r));
  const refused = peerLatencyThroughNode({ actorDispatchBrowserMs: 100, actorCalibration: null, peerUpdateBrowserMs: 150, peerCalibration: cal(1050, 3) });
  expect("D6b. uncalibrated cross-browser latency REFUSED (null, with reason)", refused.latencyMs === null && refused.reason === "uncalibrated_cross_browser_refused", JSON.stringify(refused));
}

// D7 - qualifyActorWindow requires POSITIVE OS foreground + DOM qualification.
{
  const ok = qualifyActorWindow({ foregroundSample: { pid: 7184 }, actorPid: 7184, dom: { hasFocus: true, visible: true, innerWidth: 1280, innerHeight: 900, devicePixelRatio: 1 } });
  expect("D7a. actor foreground + exact DOM qualification -> qualified", ok.qualified === true && ok.failing.length === 0, JSON.stringify(ok.failing));
  const lost = qualifyActorWindow({ foregroundSample: { pid: 2 }, actorPid: 7184, dom: { hasFocus: true, visible: true, innerWidth: 1280, innerHeight: 900, devicePixelRatio: 1 } });
  expect("D7b. wrong foreground PID -> NOT qualified (os_foreground failing)", lost.qualified === false && lost.failing.includes("os_foreground"), JSON.stringify(lost.failing));
  const unknown = qualifyActorWindow({ foregroundSample: { pid: 7184 }, actorPid: 7184, dom: { hasFocus: null } });
  expect("D7c. unknown DOM focus/size/dpr -> NOT qualified (never silently ignored)", unknown.qualified === false && unknown.failing.length > 0, JSON.stringify(unknown.failing));
}

// D8 (defect 3) - solo correlation requires the REQUEST to have STARTED AFTER
// dispatch: an older in-flight same-direction response (request started before
// dispatch) must NOT qualify, and the response identity is persisted.
{
  const mkResp = (dir, startNs, atNs, rev) => ({
    kind: "response", url: "http://x/api/games/42/rotate",
    postData: JSON.stringify({ direction: dir }),
    state: { board: Array.from({ length: 20 }, () => new Array(10).fill(0)), active_piece: null, revision: rev },
    reqId: `r-${rev}`, startNs, gameId: "42", atNs,
  });
  // Older request started at 10 (before dispatch 50) though it finished at 60.
  const older = mkResp("cw", "10", "60", 7);
  // Newer request started at 55 (after dispatch 50), finished at 70.
  const newer = mkResp("cw", "55", "70", 9);
  const store = { soloActionResponses: [older, newer] };
  const r = soloActionCorrelate(store, { expectedKind: "rotate", expectedDir: "cw", dispatchAtNs: "50" });
  expect("D8a. solo picks the request that STARTED AFTER dispatch (not the older in-flight one)",
    r.state && r.revision === 9 && r.httpStartNs === "55" && r.gameId === "42", JSON.stringify({ rev: r.revision, start: r.httpStartNs, game: r.gameId }));
  const onlyOld = { soloActionResponses: [older] };
  const none = soloActionCorrelate(onlyOld, { expectedKind: "rotate", expectedDir: "cw", dispatchAtNs: "50" });
  expect("D8b. an older in-flight-only response -> NOT correlated (accepted=null)",
    none.state === null && none.accepted === null, JSON.stringify({ reason: none.reason }));
  const noStart = { soloActionResponses: [{ ...newer, startNs: null }] };
  const nn = soloActionCorrelate(noStart, { expectedKind: "rotate", expectedDir: "cw", dispatchAtNs: "50" });
  expect("D8c. a response with unknown request start -> cannot prove after-dispatch (not correlated)",
    nn.state === null && nn.accepted === null, JSON.stringify({ reason: nn.reason }));
}

// D9 (defect 4) - peer latency through FINAL pre+post calibration folds drift
// into the uncertainty; pre-only would understate it.
{
  // actor: node = browser + 1000 (pre), +1004 (post) -> drift 4.
  const actorPre = calibrationPoint(2000n * 1000000n, 1000, 1);   // offset 1000, u 1
  const actorPost = calibrationPoint(3004n * 1000000n, 2000, 1);  // offset 1004, u 1
  const actorCal = summarizeCalibration(actorPre, actorPost);
  // peer: offset 1050 pre / 1052 post -> drift 2.
  const peerPre = calibrationPoint(1050n * 1000000n, 0, 1);
  const peerPost = calibrationPoint(2052n * 1000000n, 1000, 1);
  const peerCal = summarizeCalibration(peerPre, peerPost);
  expect("D9a. final calibration is calibrated with non-null drift+uncertainty (post included)",
    actorCal.calibrated === true && actorCal.driftMs === 4 && actorCal.uncertaintyMs === (1 + 1 + 4),
    JSON.stringify({ drift: actorCal.driftMs, u: actorCal.uncertaintyMs }));
  const mapped = peerLatencyThroughNode({ actorDispatchBrowserMs: 100, actorCalibration: actorCal, peerUpdateBrowserMs: 150, peerCalibration: peerCal });
  // uncertainty = actor.u (6) + peer.u (1+1+2=4) = 10, i.e. strictly > pre-only.
  expect("D9b. peer latency carries SUMMED pre+post uncertainty (not pre-only)",
    mapped.latencyMs !== null && mapped.uncertaintyMs === 10 && mapped.domain === DOMAIN_NODE,
    JSON.stringify({ lat: mapped.latencyMs, u: mapped.uncertaintyMs }));
}

// D10 (defect 5) - the centralized trial-validity predicate rejects empty
// frame/action data, invalid calibration, missing duel peer data, and a probe
// lacking foreground; and accepts a fully-valid trial.
{
  const base = {
    mode: "solo", isProbe: false, hasFailure: false, fullWindowObserved: true,
    frameSampleCount: 100, qualifiedSampleCount: 5, calibrationValid: true,
    qualificationAllPassed: true, foregroundObserved: true,
    duelPeerMatchCount: null, duelPeerLatencyCount: null,
  };
  expect("D10a. fully-valid solo trial -> NOT invalid", trialIsInvalid(base).invalid === false, JSON.stringify(trialIsInvalid(base).reasons));
  expect("D10b. empty frame data -> invalid (empty_frame_data)",
    trialIsInvalid({ ...base, frameSampleCount: 0 }).reasons.includes("empty_frame_data"), "frames=0");
  expect("D10c. empty action data -> invalid (empty_action_data)",
    trialIsInvalid({ ...base, qualifiedSampleCount: 0 }).reasons.includes("empty_action_data"), "samples=0");
  expect("D10d. invalid calibration -> invalid (invalid_calibration)",
    trialIsInvalid({ ...base, calibrationValid: false }).reasons.includes("invalid_calibration"), "calib invalid");
  expect("D10e. PROBE without foreground -> invalid (foreground_not_observed); probe is NOT exempt",
    trialIsInvalid({ ...base, isProbe: true, foregroundObserved: false }).reasons.includes("foreground_not_observed"), "probe no fg");
  const duelOk = { ...base, mode: "duel", duelPeerMatchCount: 3, duelPeerLatencyCount: 3 };
  expect("D10f. valid duel with peer matches+latency -> NOT invalid", trialIsInvalid(duelOk).invalid === false, JSON.stringify(trialIsInvalid(duelOk).reasons));
  expect("D10g. duel missing peer matches -> invalid (no_duel_peer_matches)",
    trialIsInvalid({ ...duelOk, duelPeerMatchCount: 0 }).reasons.includes("no_duel_peer_matches"), "no peer match");
  expect("D10h. duel missing peer latency -> invalid (no_duel_peer_latency)",
    trialIsInvalid({ ...duelOk, duelPeerLatencyCount: 0 }).reasons.includes("no_duel_peer_latency"), "no peer latency");
}

// D11 (defect 2) - deriveSampleProof with an UNKNOWN source event (null dispatch
// focus/window) cannot positively prove dispatch, so the qualifier rejects it.
{
  const noSource = deriveSampleProof({ dispatchFocus: { hasFocus: null, inWindow: null, now: null }, updateFocus: { hasFocus: true, inWindow: true }, matched: true, laterInputDispatched: false });
  expect("D11a. missing source event -> focusOk=false AND dispatchInWindow=false (unproven)",
    noSource.focusOk === false && noSource.dispatchInWindow === false, JSON.stringify(noSource));
  const c = { ...qualifyingCandidate(), focusOk: noSource.focusOk, dispatchInWindow: noSource.dispatchInWindow, updateInWindow: true };
  const v = qualifyActionSample(c);
  expect("D11b. sample from a missing source event -> qualifier REJECTS (unproven focus/window)",
    v.qualified === false && (v.reason === REASON.UNPROVEN_FOCUS || v.reason === REASON.UNQUALIFIED_FOCUS), `got reason=${v.reason}`);
}

// Report. Exit 0 iff every deliberate rejection was observed.
const failed = checks.filter((c) => !c.passed);
const summary = {
  task: "20.2/23/24 harness semantic + driver-integration self-checks",
  totalChecks: checks.length,
  passed: checks.length - failed.length,
  failed: failed.length,
  nonTiming: true,
  launchedBrowserOrWindow: false,
  measuredTrialOrProbe: false,
  cli: { exitCode: cli.code, timedOut: cli.timedOut ?? false },
  checks,
};
console.log(JSON.stringify(summary, null, 2));
if (failed.length > 0) {
  console.error(`SELF-CHECK FAIL: ${failed.length} of ${checks.length} deliberate rejections did not occur:`);
  for (const f of failed) console.error(`  - ${f.name} :: ${f.detail}`);
  process.exit(1);
}
console.log(`SELF-CHECK PASS: ${checks.length} non-timing checks, every deliberate rejection observed; the real qualifier/clock guard/correlators/foreground qualifier and the real CLI each refused defective/functionless work. No browser/window launched, no measured trial/probe/window run.`);
process.exit(0);
