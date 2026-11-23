// Non-timing validation of the ACTUAL injected Stage 4 instrumentation + the
// shared pure helpers (task 20.1). This does NOT run a browser or any measured
// benchmark. It:
//   1. Extracts the REAL `INSTRUMENT` String.raw template from benchmark.mjs,
//      cooks it exactly as the harness does, compiles the cooked script, and
//      executes it under a minimal inert window/document/Canvas stub.
//   2. Confirms the cooked script installs the SINGLE-buffer Canvas reader and
//      the rAF scheduling observer, and that a single getImageData read yields
//      800 bytes (200 cell centers x RGBA) from a stubbed backing store.
//   3. Confirms the palette oracle (lib/palette.mjs) maps the frozen Canvas
//      colors to the expected per-cell RGB and that an observed mask built from
//      the SAME colors matches exactly.
//
// This exercises the GENUINE cooked output and the GENUINE pure helpers; it is
// NOT a mirror that restates the function bodies. Run: node validate-instrument.mjs
// (from perf/). Exit 0 on success, 1 on any failure.
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  BOARD_CELLS,
  BOARD_COLS,
  BOARD_ROWS,
  COLORS,
  expectedRgbMaskFromState,
  maskFromCenterRgba,
  masksEqual,
  hexToRgb,
} from "./lib/palette.mjs";

const dir = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(dir, "benchmark.mjs"), "utf8");

const fail = (msg) => { console.error("VALIDATION FAIL:", msg); process.exit(1); };

// --- 1. Extract and cook the ACTUAL INSTRUMENT template. ---
const START = "export const INSTRUMENT = String.raw`";
const s = src.indexOf(START);
if (s < 0) fail("INSTRUMENT String.raw template not found in benchmark.mjs");
const bodyStart = s + START.length;
const bodyEnd = src.indexOf("`;", bodyStart);
if (bodyEnd < 0) fail("end of INSTRUMENT template not found");
const templateBody = src.slice(bodyStart, bodyEnd);

const cook = new Function(
  "BOARD_COLS", "BOARD_ROWS", "BOARD_CELLS", "MEASURE_MS",
  "return String.raw`" + templateBody + "`;",
);
const cooked = cook(BOARD_COLS, BOARD_ROWS, BOARD_CELLS, 30000);

if (!cooked.includes("getImageData")) fail("cooked instrument lacks the single-buffer getImageData read");
if (cooked.includes("monkeypatch") || /w\.fetch\s*=/.test(cooked)) fail("cooked instrument appears to patch fetch (must be passive)");
if (/WebSocket\s*=/.test(cooked)) fail("cooked instrument appears to patch WebSocket (must be passive)");

// --- Inert Canvas stub: a backing store whose pixels encode a known board. ---
// We paint the top-left cell the I-color and the rest the empty background, and
// confirm the single-buffer reader samples the 200 cell centers correctly.
const WIDTH = BOARD_COLS * 10; // 100 device px wide (10 px per cell)
const HEIGHT = BOARD_ROWS * 10; // 200 device px tall
const empty = hexToRgb(COLORS[0]);
const iColor = hexToRgb(COLORS[1]);
// Build a backing RGBA buffer painted per cell (flat pixel grid).
const pixels = new Uint8ClampedArray(WIDTH * HEIGHT * 4);
for (let y = 0; y < HEIGHT; y += 1) {
  for (let x = 0; x < WIDTH; x += 1) {
    const cellC = Math.floor(x / 10);
    const cellR = Math.floor(y / 10);
    const isTopLeft = cellR === 0 && cellC === 0;
    const col = isTopLeft ? iColor : empty;
    const idx = (y * WIDTH + x) * 4;
    pixels[idx] = col.r; pixels[idx + 1] = col.g; pixels[idx + 2] = col.b; pixels[idx + 3] = 255;
  }
}

const canvasStub = {
  width: WIDTH,
  height: HEIGHT,
  getContext() {
    return { getImageData: () => ({ data: pixels, width: WIDTH, height: HEIGHT }) };
  },
};
let perfNowValue = 0;
const keydownListeners = [];
const documentStub = {
  readyState: "complete",
  title: "",
  hasFocus() { return true; },
  querySelector() { return canvasStub; },
  addEventListener(type, cb, capture) { if (type === "keydown") keydownListeners.push({ cb, capture }); },
  visibilityState: "visible",
};
const windowStub = {
  document: documentStub,
  performance: { now: () => perfNowValue },
  requestAnimationFrame() { return 0; }, // inert
  innerWidth: 1280,
  innerHeight: 900,
  devicePixelRatio: 1,
};
windowStub.window = windowStub;

const ctx = vm.createContext({
  window: windowStub,
  document: documentStub,
  performance: windowStub.performance,
  requestAnimationFrame: windowStub.requestAnimationFrame,
  console,
});

try { new vm.Script(cooked).runInContext(ctx); }
catch (e) { fail("cooked instrumentation failed to compile/execute: " + (e && e.message ? e.message : e)); }

const w = windowStub;
if (typeof w.__perfReadCanvasCenters !== "function") fail("single-buffer Canvas reader not installed");
if (typeof w.__perfStartRaf !== "function") fail("rAF scheduling observer not installed");
if (typeof w.__perfMarkWindowStart !== "function") fail("window-start marker not installed");
// CORRECTION 23 (defect 5): the Canvas reader must expose its own read
// timestamp in the SAME call, and the DOM-qualification reader must exist.
if (typeof w.__perfDomQual !== "function") fail("DOM-qualification reader (__perfDomQual) not installed");
if (typeof w.__perfReadCanvasCenters !== "function") fail("Canvas reader not installed");

// The single-buffer read must return 800 RGBA bytes for 200 cell centers.
const read = w.__perfReadCanvasCenters("ignored-selector");
if (!read || !Array.isArray(read.rgba)) fail("single-buffer read returned no rgba");
if (read.rgba.length !== BOARD_CELLS * 4) fail(`single-buffer read returned ${read.rgba.length} bytes, expected ${BOARD_CELLS * 4}`);
if (typeof read.readNow !== "number") fail("single-buffer read did not return its own readNow timestamp (defect 5)");

// --- CORRECTION 24 defect 1: __perfMarkWindowStart honors the ACTUAL duration. ---
perfNowValue = 1000;
const win3s = w.__perfMarkWindowStart(3000);
if (!win3s || win3s.durationMs !== 3000 || win3s.end - win3s.start !== 3000) {
  fail("defect 1: __perfMarkWindowStart(3000) did not use the 3000 ms probe duration");
}
const win30s = w.__perfMarkWindowStart(30000);
if (!win30s || win30s.durationMs !== 30000 || win30s.end - win30s.start !== 30000) {
  fail("defect 1: __perfMarkWindowStart(30000) did not use the 30000 ms full-trial duration");
}
// A non-finite argument falls back to the cooked MEASURE_MS (30000), never 0.
const winBad = w.__perfMarkWindowStart(undefined);
if (!winBad || winBad.durationMs !== 30000) fail("defect 1: bad duration did not fall back to MEASURE_MS");

// --- CORRECTION 24 defect 2: read-only keydown recorder records real events. ---
if (typeof w.__perfInstallKeydownRecorder !== "function") fail("defect 2: keydown recorder installer missing");
if (typeof w.__perfKeydownSeq !== "function" || typeof w.__perfKeydownsSince !== "function") fail("defect 2: keydown query API missing");
w.__perfInstallKeydownRecorder();
if (keydownListeners.length !== 1 || keydownListeners[0].capture !== true) fail("defect 2: recorder did not register a capture-phase keydown listener");
const seq0 = w.__perfKeydownSeq();
perfNowValue = 1234.5;
// Simulate a trusted source keydown and a separate untrusted one.
keydownListeners[0].cb({ key: "ArrowUp", isTrusted: true });
perfNowValue = 1240;
keydownListeners[0].cb({ key: "ArrowUp", isTrusted: false });
const since = w.__perfKeydownsSince(seq0);
if (!Array.isArray(since) || since.length !== 2) fail("defect 2: recorder did not record both keydowns");
const trusted = since.filter((e) => e.isTrusted === true && e.key === "ArrowUp");
if (trusted.length !== 1 || trusted[0].at !== 1234.5) fail("defect 2: recorder did not record the trusted event time");
if (since.some((e) => e.seq <= seq0)) fail("defect 2: keydown sequence is not monotonic past the snapshot");

// --- CORRECTION 24 defect 6: ordinary document.title setter (metadata only). ---
if (typeof w.__perfSetWindowTitle !== "function") fail("defect 6: title setter missing");
w.__perfSetWindowTitle("TETRIS-PERF solo solo-1 ACTOR INPUT");
if (documentStub.title !== "TETRIS-PERF solo solo-1 ACTOR INPUT" || !documentStub.title.includes("INPUT")) {
  fail("defect 6: title setter did not set the ordinary document.title ending INPUT");
}

// --- 2. Build observed mask from the real reader and confirm cell 0 is I. ---
const observedMask = maskFromCenterRgba(read.rgba);
if (!observedMask) fail("maskFromCenterRgba returned null");
if (observedMask[0].r !== iColor.r || observedMask[0].g !== iColor.g || observedMask[0].b !== iColor.b) {
  fail("cell 0 center was not the I-piece color (single-buffer sampling is wrong)");
}
for (let i = 1; i < BOARD_CELLS; i += 1) {
  if (observedMask[i].r !== empty.r || observedMask[i].g !== empty.g || observedMask[i].b !== empty.b) {
    fail(`cell ${i} center was not the empty background color`);
  }
}

// --- 3. Expected mask from a matching authoritative state must equal observed. ---
// A state whose settled board has an I-code (1) in the top-left and nothing
// else; no active piece. The palette oracle should produce the SAME mask the
// single-buffer reader observed.
const board = Array.from({ length: BOARD_ROWS }, () => new Array(BOARD_COLS).fill(0));
board[0][0] = 1;
const expectedMask = expectedRgbMaskFromState({ board, active_piece: null });
if (!expectedMask) fail("expectedRgbMaskFromState returned null");
const eq = masksEqual(expectedMask, observedMask);
if (!eq.equal) fail(`expected and observed 200-cell masks differ at cell ${eq.firstDiffIndex}`);

console.log(JSON.stringify({
  cookedCompiles: true,
  singleBufferReaderInstalled: true,
  rafObserverInstalled: true,
  cells: BOARD_CELLS,
  rgbaBytes: read.rgba.length,
  cell0IsIColor: true,
  expectedEqualsObserved: eq.equal,
  canvasReadHasOwnTimestamp: typeof read.readNow === "number",
  domQualificationReaderInstalled: typeof w.__perfDomQual === "function",
  markWindowStartHonorsDuration: true,
  keydownRecorderReadOnlyCapturePhase: true,
  keydownRecordsTrustedEventTimes: true,
  ordinaryTitleSetterEndsInput: true,
}, null, 2));
console.log("VALIDATION PASS: single-buffer Canvas read of 200 cell centers matches the palette-derived expected mask.");
