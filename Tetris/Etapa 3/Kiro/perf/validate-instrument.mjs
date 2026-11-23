// Non-timing validation of the ACTUAL injected instrumentation (Stage 3,
// Requirement 22, task 23.2). This does NOT run a browser or any measured
// benchmark. It extracts the REAL `INSTRUMENT` String.raw template from
// benchmark.mjs, cooks it exactly as the harness does, compiles the cooked
// script, executes it under a minimal inert window/document/requestAnimationFrame
// stub, and then calls the instrumentation's OWN color/signature functions to
// confirm that the empty-cell color rgb(17,24,39) and #111827 normalize to the
// identical token across all 200 cells. It asserts the cooked regexes survived
// (the round-07 defect was an escape-stripped, uncompilable cooked regex).
//
// Run: node validate-instrument.mjs   (from perf/). Exit 0 on success.
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dir = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(dir, "benchmark.mjs"), "utf8");

// --- Extract the ACTUAL template text (not a copy of the function bodies). ---
const START = "const INSTRUMENT = String.raw`";
const s = src.indexOf(START);
if (s < 0) throw new Error("INSTRUMENT String.raw template not found in benchmark.mjs");
const bodyStart = s + START.length;
const bodyEnd = src.indexOf("`;", bodyStart);
if (bodyEnd < 0) throw new Error("end of INSTRUMENT template not found");
const templateBody = src.slice(bodyStart, bodyEnd);

// The harness interpolates ${BOARD_CELLS} and ${MEASURE_MS}; use the same values.
const BOARD_CELLS = 200;
const MEASURE_MS = 30000;
const cook = new Function("BOARD_CELLS", "MEASURE_MS",
  "return String.raw`" + templateBody + "`;");
const cooked = cook(BOARD_CELLS, MEASURE_MS);

const fail = (msg) => { console.error("VALIDATION FAIL:", msg); process.exit(1); };

// --- Static cooked-script assertions. ---
if (cooked.includes("rgba?(s*(d+)")) fail("cooked script still contains escape-stripped rgba regex");
if (!cooked.includes("rgba?\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)")) fail("cooked rgba matcher missing/altered");
if (cooked.includes("\\u0001")) fail("cooked script contains literal \\u0001 escape (would break joins)");

// --- Inert environment. 200 cells; observed background is rgb(17,24,39). ---
const EMPTY_RGB = "rgb(17, 24, 39)";       // computed-style form Chromium returns
const EMPTY_HEX = "#111827";               // Board COLORS[0]
function makeCell() {
  return {
    getAttribute() { return null; },       // no data-cell / no inline style
    className: "",
  };
}
const cells = Array.from({ length: BOARD_CELLS }, makeCell);
const board = {
  querySelectorAll() { return []; },        // force fallback to children
  get children() { return cells; },
  getBoundingClientRect() { return { x: 0, y: 0, width: 300, height: 600, top: 0, left: 0, bottom: 600, right: 300 }; },
};
const document = {
  readyState: "complete",
  hasFocus() { return true; },
  querySelector(sel) {
    if (sel.includes("board") || sel.includes("table") || sel === "#board") return board;
    return null;
  },
};
const windowStub = {
  document,
  innerWidth: 1280,
  innerHeight: 900,
  performance: { now: () => 0 },
  requestAnimationFrame() { return 0; }, // inert: never actually schedules
  getComputedStyle() { return { backgroundColor: EMPTY_RGB, background: EMPTY_RGB }; },
  MutationObserver: class { observe() {} disconnect() {} },
  PerformanceObserver: class { observe() {} disconnect() {} },
  fetch: null,
};
windowStub.window = windowStub;

const ctx = vm.createContext({ window: windowStub, document, performance: windowStub.performance,
  requestAnimationFrame: windowStub.requestAnimationFrame, console });

// --- Compile + execute the ACTUAL cooked instrumentation. ---
try { new vm.Script(cooked).runInContext(ctx); }
catch (e) { fail("cooked instrumentation failed to compile/execute: " + (e && e.message ? e.message : e)); }

const w = windowStub;
if (typeof w.__perfExpectedSignatureFromColorGrid !== "function") fail("expected-signature function not installed");
if (typeof w.__perfNormalizedObservedSignature !== "function") fail("observed-signature function not installed");

// Expected signature: 200-entry grid, every cell the empty-cell HEX color.
const grid = Array.from({ length: BOARD_CELLS }, () => EMPTY_HEX);
const expectedSig = w.__perfExpectedSignatureFromColorGrid(grid);
// Observed signature: 200 DOM cells whose computed background is the RGB form.
const observedSig = w.__perfNormalizedObservedSignature();

if (expectedSig === null) fail("expected signature was null");
if (observedSig === null) fail("observed signature was null");
const tokens = expectedSig.split(String.fromCharCode(1));
if (tokens.length !== BOARD_CELLS) fail("expected signature did not contain 200 tokens (got " + tokens.length + ")");
if (!tokens.every((t) => t === "#111827")) fail("not every normalized token was #111827");
if (expectedSig !== observedSig) fail("rgb(17,24,39) and #111827 did NOT normalize identically across 200 cells");

console.log(JSON.stringify({
  cookedCompiles: true,
  functionsInstalled: true,
  cells: BOARD_CELLS,
  normalizedToken: tokens[0],
  rgbAndHexNormalizeIdentically: expectedSig === observedSig,
  separatorCharCode: 1,
}, null, 2));
console.log("VALIDATION PASS: rgb(17,24,39) and #111827 normalize identically across all 200 cells.");
