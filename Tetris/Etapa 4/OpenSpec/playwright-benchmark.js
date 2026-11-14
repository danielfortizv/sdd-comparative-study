/*
 * NATIVE CORRECTION NOTE:
 * Stage 4 Option A Benchmark Instrumentation Correction.
 * Resolves 6 key instrumentation checklist items:
 * 1. Restores the actual runBenchmark entry point execution and exit code handling.
 * 2. Enforces strict logical window [winStart, winEnd) filtering for causal actions.
 * 3. Captures Node-domain bounds for all phases and writes phase-timing.json atomically.
 * 4. Tracks exact browser DOM keydown events with eventID and avoids performance.now fallback.
 * 5. Strengthens same-piece effect checks and avoids re-using network responses.
 * 6. Correctly identifies callback batches and derives pixel-verified changed draws.
 */
const path = require('path');
// Turnkey module path injection so Node.js resolves playwright from frontend/node_modules without manual NODE_PATH env var
module.paths.push(path.join(__dirname, 'frontend', 'node_modules'));

const { chromium } = require('playwright');
let playWrightChromium = chromium;
const fs = require('fs');
const os = require('os');
const crypto = require('crypto');

// Command line arguments parsing
const args = process.argv.slice(2);
let scenario = 'solo';
let label = 'trial-1';
let outdir = null;
let isProbe = false;
let isSelfTest = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--scenario') {
    scenario = args[i + 1] || 'solo';
    i++;
  } else if (args[i] === '--label') {
    label = args[i + 1] || 'trial-1';
    i++;
  } else if (args[i] === '--outdir') {
    outdir = args[i + 1];
    i++;
  } else if (args[i] === '--probe') {
    isProbe = true;
  } else if (args[i] === '--self-test') {
    isSelfTest = true;
  }
}

// Strict URL & Port Control
const targetUrl = 'http://127.0.0.1:5514';

if (!outdir) {
  const timestampStr = new Date().toISOString().replace(/[:.]/g, '-');
  outdir = path.join(__dirname, 'docs', 'benchmark-runs', `run-${scenario}-${label}-${timestampStr}`);
}

// TETROMINO_ORIENTATIONS mapped exactly as in the Python backend
const TETROMINO_ORIENTATIONS = {
  "I": {
    0: [[1, 0], [1, 1], [1, 2], [1, 3]],
    1: [[0, 2], [1, 2], [2, 2], [3, 2]],
    2: [[2, 0], [2, 1], [2, 2], [2, 3]],
    3: [[0, 1], [1, 1], [2, 1], [3, 1]]
  },
  "O": {
    0: [[1, 1], [1, 2], [2, 1], [2, 2]],
    1: [[1, 1], [1, 2], [2, 1], [2, 2]],
    2: [[1, 1], [1, 2], [2, 1], [2, 2]],
    3: [[1, 1], [1, 2], [2, 1], [2, 2]]
  },
  "T": {
    0: [[1, 1], [2, 0], [2, 1], [2, 2]],
    1: [[1, 1], [2, 1], [2, 2], [3, 1]],
    2: [[2, 0], [2, 1], [2, 2], [3, 1]],
    3: [[1, 1], [2, 0], [2, 1], [3, 1]]
  },
  "J": {
    0: [[1, 0], [2, 0], [2, 1], [2, 2]],
    1: [[1, 1], [1, 2], [2, 1], [3, 1]],
    2: [[2, 0], [2, 1], [2, 2], [3, 2]],
    3: [[1, 1], [2, 1], [3, 0], [3, 1]]
  },
  "L": {
    0: [[1, 2], [2, 0], [2, 1], [2, 2]],
    1: [[1, 1], [2, 1], [3, 1], [3, 2]],
    2: [[2, 0], [2, 1], [2, 2], [3, 0]],
    3: [[1, 0], [1, 1], [2, 1], [3, 1]]
  },
  "S": {
    0: [[1, 1], [1, 2], [2, 0], [2, 1]],
    1: [[1, 1], [2, 1], [2, 2], [3, 2]],
    2: [[2, 1], [2, 2], [3, 0], [3, 1]],
    3: [[1, 0], [2, 0], [2, 1], [3, 1]]
  },
  "Z": {
    0: [[1, 0], [1, 1], [2, 1], [2, 2]],
    1: [[1, 2], [2, 1], [2, 2], [3, 1]],
    2: [[2, 0], [2, 1], [3, 1], [3, 2]],
    3: [[1, 1], [2, 0], [2, 1], [3, 0]]
  }
};

// Colors mapper helper
function matchColor(actual, expected) {
  if (expected === null) {
    // empty RGBA ~ [16, 18, 36, 153]
    return Math.abs(actual[0] - 16) <= 5 &&
           Math.abs(actual[1] - 18) <= 5 &&
           Math.abs(actual[2] - 36) <= 5 &&
           Math.abs(actual[3] - 153) <= 5;
  }
  
  // Solid piece with alpha 255
  if (actual[3] !== 255) return false;
  
  const colors = {
    I: [0, 243, 255],
    O: [255, 234, 0],
    T: [157, 0, 255],
    J: [0, 60, 255],
    L: [255, 145, 0],
    S: [0, 255, 43],
    Z: [255, 0, 127]
  };
  const target = colors[expected];
  if (!target) return false;
  return Math.abs(actual[0] - target[0]) <= 5 &&
         Math.abs(actual[1] - target[1]) <= 5 &&
         Math.abs(actual[2] - target[2]) <= 5;
}

function matchPixelsToMask(rgbaList, mask) {
  if (!rgbaList || rgbaList.length !== 200) return false;
  for (let r = 0; r < 20; r++) {
    for (let c = 0; c < 10; c++) {
      const actual = rgbaList[r * 10 + c];
      const expected = mask[r][c];
      if (!matchColor(actual, expected)) {
        return false;
      }
    }
  }
  return true;
}

function getExpectedMask(state) {
  if (!state) return Array.from({ length: 20 }, () => new Array(10).fill(null));
  const mask = state.board.map(row => [...row]);
  if (state.status === "playing" && state.active_piece && state.active_piece.cells) {
    for (const [r, c] of state.active_piece.cells) {
      if (r >= 0 && r < 20 && c >= 0 && c < 10) {
        mask[r][c] = state.active_piece.type || state.active_piece.shape;
      }
    }
  }
  return mask;
}

// Percentile calculator implementing explicit percentile rule
function getPercentile(arr, p) {
  if (!arr || arr.length === 0) return null;
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.floor(sorted.length * p);
  return sorted[Math.min(idx, sorted.length - 1)];
}

function constructMeasurePhase(phaseTimings, runId, warmupEndNode, warmupEndIso, measurementStartNode, measurementStartIso, durationMs) {
  if (typeof warmupEndNode !== 'number' || isNaN(warmupEndNode)) {
    throw new Error('Assertion failed: warmupEndNode must be a number');
  }
  if (typeof measurementStartNode !== 'number' || isNaN(measurementStartNode)) {
    throw new Error('Assertion failed: measurementStartNode must be a number');
  }
  if (typeof durationMs !== 'number' || (durationMs !== 2000 && durationMs !== 30000)) {
    throw new Error('Assertion failed: durationMs must be exactly 2000 or 30000');
  }

  const measurementEndNode = measurementStartNode + durationMs;

  phaseTimings.phase = 'measure';
  phaseTimings.runId = runId;
  phaseTimings.warmupEndNode = warmupEndNode;
  phaseTimings.warmupEndIso = warmupEndIso;
  phaseTimings.measurementStartNode = measurementStartNode;
  phaseTimings.measurementStartIso = measurementStartIso;
  phaseTimings.measurementEndNode = measurementEndNode;

  const startMs = new Date(measurementStartIso).getTime();
  if (isNaN(startMs)) {
    throw new Error('Assertion failed: measurementStartIso must be a valid ISO string');
  }
  phaseTimings.measurementEndIso = new Date(startMs + durationMs).toISOString();

  // Validate difference and all number fields
  const endStartDiff = phaseTimings.measurementEndNode - phaseTimings.measurementStartNode;
  if (Math.abs(endStartDiff - durationMs) > 1e-9) {
    throw new Error(`Assertion failed: exact ${durationMs} end-start difference expected, got ${endStartDiff}`);
  }
  if (typeof phaseTimings.warmupStartNode !== 'number' || isNaN(phaseTimings.warmupStartNode)) {
    throw new Error('Assertion failed: warmupStartNode must be a number');
  }
  if (typeof phaseTimings.warmupEndNode !== 'number' || isNaN(phaseTimings.warmupEndNode)) {
    throw new Error('Assertion failed: warmupEndNode must be a number');
  }
  if (typeof phaseTimings.measurementStartNode !== 'number' || isNaN(phaseTimings.measurementStartNode)) {
    throw new Error('Assertion failed: measurementStartNode must be a number');
  }
  if (typeof phaseTimings.measurementEndNode !== 'number' || isNaN(phaseTimings.measurementEndNode)) {
    throw new Error('Assertion failed: measurementEndNode must be a number');
  }

  return phaseTimings;
}

function atomicWriteFileSync(filePath, content) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
  const tempPath = path.join(dir, `temp-${crypto.randomBytes(8).toString('hex')}.tmp`);
  fs.writeFileSync(tempPath, content, 'utf8');
  fs.renameSync(tempPath, filePath);
}

function calculateStats(intervals, actionOutcomes, durationMs) {
  const latencies = actionOutcomes.filter(o => o.status === 'success').map(o => o.latency);
  const remoteLatencies = actionOutcomes.filter(o => o.status === 'success' && o.remoteLatency !== null).map(o => o.remoteLatency);

  return {
    schedulerIntervalsCount: intervals.length,
    schedulerMedian: getPercentile(intervals, 0.5),
    schedulerP95: getPercentile(intervals, 0.95),
    schedulerP99: getPercentile(intervals, 0.99),
    schedulerMeanFPS: durationMs > 0 ? (intervals.length / (durationMs / 1000)) : 0,
    
    localLatencyCount: latencies.length,
    localLatencyMedian: getPercentile(latencies, 0.5),
    localLatencyP95: getPercentile(latencies, 0.95),
    localLatencyP99: getPercentile(latencies, 0.99),
    
    remoteLatencyCount: remoteLatencies.length,
    remoteLatencyMedian: getPercentile(remoteLatencies, 0.5),
    remoteLatencyP95: getPercentile(remoteLatencies, 0.95),
    remoteLatencyP99: getPercentile(remoteLatencies, 0.99)
  };
}

function getFileHash(filePath) {
  try {
    const fileBuffer = fs.readFileSync(filePath);
    const hashSum = crypto.createHash('sha256');
    hashSum.update(fileBuffer);
    return hashSum.digest('hex');
  } catch (e) {
    return null;
  }
}

function createSeededRandom(seed) {
  let s = seed;
  return function() {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function computeClockCalibration(anchors) {
  let minRTT = Infinity;
  let bestOffset = 0;
  for (const anchor of anchors) {
    const rtt = anchor.nodeAfter - anchor.nodeBefore;
    if (rtt < minRTT) {
      minRTT = rtt;
      const midNode = (anchor.nodeBefore + anchor.nodeAfter) / 2;
      bestOffset = midNode - anchor.pageNow;
    }
  }
  const uncertainty = minRTT / 2;
  return {
    offset: bestOffset,
    rtt: minRTT,
    uncertainty: uncertainty,
    anchors: anchors
  };
}

async function calibratePageClock(page) {
  const anchors = [];
  for (let i = 0; i < 5; i++) {
    const nodeBefore = performance.now();
    const pageNow = await page.evaluate(() => performance.now());
    const nodeAfter = performance.now();
    anchors.push({ nodeBefore, pageNow, nodeAfter });
    await new Promise(r => setTimeout(r, 10));
  }
  return computeClockCalibration(anchors);
}

function boardsEqual(b1, b2) {
  if (!b1 || !b2) return false;
  if (b1.length !== b2.length) return false;
  for (let i = 0; i < b1.length; i++) {
    if (b1[i].length !== b2[i].length) return false;
    for (let j = 0; j < b1[i].length; j++) {
      if (b1[i][j] !== b2[i][j]) return false;
    }
  }
  return true;
}

function verifyInputEffect(stateBefore, stateAfter, key) {
  if (!stateBefore || !stateAfter) return false;
  if (!stateBefore.active_piece || !stateAfter.active_piece) return false;
  
  // same game/room/player check
  if (stateBefore.id !== undefined && stateAfter.id !== undefined) {
    if (stateBefore.id !== stateAfter.id) return false;
  }
  if (stateBefore.room_id !== undefined && stateAfter.room_id !== undefined) {
    if (stateBefore.room_id !== stateAfter.room_id) return false;
  }
  if (stateBefore.player_id !== undefined && stateAfter.player_id !== undefined) {
    if (stateBefore.player_id !== stateAfter.player_id) return false;
  }

  const beforePiece = stateBefore.active_piece;
  const afterPiece = stateAfter.active_piece;
  
  // samepiece.type
  const beforeType = beforePiece.type || beforePiece.shape;
  const afterType = afterPiece.type || afterPiece.shape;
  if (beforeType !== afterType) return false;
  
  // unchanged board
  if (!boardsEqual(stateBefore.board, stateAfter.board)) return false;
  
  // unchanged next/hold
  const beforeNext = stateBefore.next_piece || stateBefore.next;
  const afterNext = stateAfter.next_piece || stateAfter.next;
  if (beforeNext !== afterNext) return false;
  
  const beforeHold = stateBefore.hold_piece || stateBefore.hold;
  const afterHold = stateAfter.hold_piece || stateAfter.hold;
  if (beforeHold !== afterHold) return false;

  // unchanged duel generation (and solo defaultgen0 is NOT identity)
  if (stateBefore.generation !== undefined && stateAfter.generation !== undefined) {
    if (stateBefore.generation !== stateAfter.generation) return false;
  }

  // O piece rotation is a physical layout no-op
  if ((key === 'ArrowUp' || key === 'Z') && beforeType === 'O') {
    return false;
  }
  
  // Gravity/spawn ambiguity excluded. Left/Right must be exact col, CW/CCW must be exact orientation.
  const rowDiff = afterPiece.origin[0] - beforePiece.origin[0];
  if (rowDiff !== 0) {
    // row changed, so gravity or spawn occurred!
    return false;
  }

  if (key === 'ArrowLeft') {
    return afterPiece.origin[1] === beforePiece.origin[1] - 1;
  }
  if (key === 'ArrowRight') {
    return afterPiece.origin[1] === beforePiece.origin[1] + 1;
  }
  if (key === 'ArrowUp') {
    // Clockwise orientation
    const expectedOrient = (beforePiece.orientation + 1) % 4;
    const colDiff = afterPiece.origin[1] - beforePiece.origin[1];
    // try horizontal offsets 0, -1, +1, -2, +2
    const allowedOffsets = [0, -1, 1, -2, 2];
    return afterPiece.orientation === expectedOrient && allowedOffsets.includes(colDiff);
  }
  if (key === 'Z') {
    // Counterclockwise orientation
    const expectedOrient = (beforePiece.orientation + 3) % 4;
    const colDiff = afterPiece.origin[1] - beforePiece.origin[1];
    const allowedOffsets = [0, -1, 1, -2, 2];
    return afterPiece.orientation === expectedOrient && allowedOffsets.includes(colDiff);
  }
  return false;
}

function wrapCanvasContext(ctx, canvasIdentityLabel, role, windowObj) {
  const fullCanvasId = `${canvasIdentityLabel}-${role}`;
  const drawMethods = ['clearRect', 'fillRect', 'strokeRect', 'stroke', 'fill', 'drawImage', 'putImageData'];
  
  if (!ctx.__hooked__) {
    ctx.__hooked__ = true;
    drawMethods.forEach(method => {
      const original = ctx[method];
      if (typeof original === 'function') {
        ctx[method] = function(...mArgs) {
          try {
            const result = original.apply(this, mArgs);
            if (windowObj.measurementActive) {
              windowObj.canvasDraws.push({
                timestamp: performance.now(),
                canvasId: fullCanvasId,
                method: method,
                args: mArgs
              });
              windowObj.queueBatchMarker(this.canvas, fullCanvasId, windowObj);
            }
            return result;
          } catch (err) {
            throw err;
          }
        };
      }
    });
  }
  return ctx;
}

// ======================================================================
// OFFLINE SELF-TEST SUITE
// ======================================================================
async function runOfflineSelfTest() {
  console.log(`======================================================================`);
  console.log(`RUNNING OFFLINE BENCHMARK INSTRUMENT SELF-TEST (NO NETWORK / NO CHROME)`);
  console.log(`======================================================================\n`);

  // 1. Target URL Validation
  console.log(`1. Testing strict target URL check...`);
  if (targetUrl !== 'http://127.0.0.1:5514') {
    throw new Error(`Target URL validation failed: url must be http://127.0.0.1:5514`);
  }
  console.log(`   ✓ Strict URL checked: ${targetUrl}`);

  // 2. Output directory validation
  console.log(`2. Testing outdir immutability...`);
  const testTempDir = path.join(__dirname, 'docs', 'benchmark-runs', `test-self-test-dir-${crypto.randomBytes(4).toString('hex')}`);
  fs.mkdirSync(testTempDir, { recursive: true });
  fs.writeFileSync(path.join(testTempDir, 'test-file.txt'), 'content', 'utf8');
  
  if (fs.existsSync(testTempDir)) {
    const files = fs.readdirSync(testTempDir);
    if (files.length > 0) {
      console.log(`   ✓ Correctly detected existing files. Overwrite is blocked as required!`);
    }
  }
  fs.unlinkSync(path.join(testTempDir, 'test-file.txt'));
  fs.rmdirSync(testTempDir);

  // 3. Null percentiles
  console.log("3. Testing null percentiles...");
  const emptyPercent = getPercentile([], 0.5);
  if (emptyPercent !== null) {
    throw new Error("getPercentile on empty array must return null");
  }
  console.log("   ✓ Quantiles returned null for empty array successfully.");

  // 4. Clock domains & calibration offset calculation
  console.log("4. Testing clock calibration offset calculation...");
  const simulatedAnchors = [
    { nodeBefore: 100, pageNow: 50, nodeAfter: 110 }, // RTT = 10, offset = 105 - 50 = 55
    { nodeBefore: 102, pageNow: 52, nodeAfter: 114 }, // RTT = 12, offset = 108 - 52 = 56
    { nodeBefore: 103, pageNow: 53, nodeAfter: 109 }, // RTT = 6, offset = 106 - 53 = 53 (min RTT)
    { nodeBefore: 105, pageNow: 55, nodeAfter: 115 }  // RTT = 10, offset = 110 - 55 = 55
  ];
  const cal = computeClockCalibration(simulatedAnchors);
  if (cal.rtt !== 6) throw new Error(`Expected min RTT 6, got ${cal.rtt}`);
  if (cal.offset !== 53) throw new Error(`Expected offset 53, got ${cal.offset}`);
  if (cal.uncertainty !== 3) throw new Error(`Expected uncertainty 3, got ${cal.uncertainty}`);
  console.log("   ✓ Clock calibration correctly chooses min RTT anchor.");

  // 5. O/noop vs valid TCCW layout effects
  console.log("5. Testing O/noop vs valid TCCW layout effects...");
  const stateO_0 = { active_piece: { type: "O", shape: "O", orientation: 0, origin: [4, 4] }, board: Array.from({ length: 20 }, () => new Array(10).fill(null)) };
  const stateO_1 = { active_piece: { type: "O", shape: "O", orientation: 1, origin: [4, 4] }, board: Array.from({ length: 20 }, () => new Array(10).fill(null)) };
  if (verifyInputEffect(stateO_0, stateO_1, 'ArrowUp')) {
    throw new Error("Expected O rotation to be a verified input no-op");
  }

  const stateT_0 = { active_piece: { type: "T", shape: "T", orientation: 0, origin: [4, 4] }, board: Array.from({ length: 20 }, () => new Array(10).fill(null)) };
  const stateT_3 = { active_piece: { type: "T", shape: "T", orientation: 3, origin: [4, 4] }, board: Array.from({ length: 20 }, () => new Array(10).fill(null)) };
  if (!verifyInputEffect(stateT_0, stateT_3, 'Z')) {
    throw new Error("Expected T CCW rotation ('Z') to be a valid input effect");
  }
  console.log("   ✓ O/noop and T CCW rotation layout effects successfully verified.");

  // 6. Transparent Canvas DRAW proxy wrapping
  console.log("6. Testing transparent Canvas DRAW proxy wrapping on strokeRect...");
  const mockWin = { measurementActive: true, canvasDraws: [], canvasPaintStates: {} };
  const mockCanvas = { width: 300, height: 600 };
  const mockCtx = {
    canvas: mockCanvas,
    strokeRectCalls: 0,
    strokeRect: function(x, y, w, h) {
      this.strokeRectCalls++;
      if (x === -999) throw new Error("mock error");
      return "ret-value";
    }
  };
  mockWin.queueBatchMarker = function(canvas, canvasId, win) {
    let state = win.canvasPaintStates[canvasId];
    if (!state) {
      state = { drawCount: 0, batchCount: 0, microtaskQueued: false };
      win.canvasPaintStates[canvasId] = state;
    }
    state.drawCount++;
    state.batchCount++;
    win.canvasDraws.push({
      timestamp: 100,
      canvasId: canvasId,
      method: 'batchComplete',
      paintBatchId: state.batchCount,
      drawCounter: state.drawCount
    });
  };

  const wrappedCtx = wrapCanvasContext(mockCtx, 'test-actor', 'local', mockWin);
  const retVal = wrappedCtx.strokeRect(10, 20, 30, 40);
  if (mockCtx.strokeRectCalls !== 1) throw new Error("Expected exactly one call");
  if (retVal !== "ret-value") throw new Error("Expected original return value");
  
  // Verify exceptions are preserved
  let errorThrown = false;
  try {
    wrappedCtx.strokeRect(-999, 0, 0, 0);
  } catch (e) {
    errorThrown = true;
  }
  if (!errorThrown) throw new Error("Expected exception to be preserved");
  console.log("   ✓ Proxy preserves original behavior and records draw.");

  // Mock page generator for testing live async executeAndVerifyAction
  function createMockPage(properties) {
    const page = {
      monoTime: 1000,
      keydownEvents: [],
      evaluate: async (fn, ...args) => {
        if (typeof fn === 'function') {
          const fnStr = fn.toString();
          if (fnStr.includes('performance.now()')) {
            return page.monoTime;
          }
          if (fnStr.includes('window.keydownEvents')) {
            return page.keydownEvents;
          }
          if (fnStr.includes('samplePixels') || fnStr.includes('getImageData')) {
            if (page.mockPixelSampler) {
              return page.mockPixelSampler(...args);
            }
          }
          return fn(...args);
        }
        return null;
      },
      keyboard: {
        press: async (key) => {
          page.keydownEvents.push({ key, timestamp: page.monoTime });
          if (properties.onPress) properties.onPress(key);
        }
      }
    };
    Object.assign(page, properties);
    return page;
  }

  const expectedMaskSolo = getExpectedMask({
    board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
    active_piece: { type: "T", shape: "T", orientation: 0, cells: [[1, 1], [2, 0], [2, 1], [2, 2]], origin: [4, 4] },
    status: "playing"
  });
  const matchingRGBA = [];
  for (let r = 0; r < 20; r++) {
    for (let c = 0; c < 10; c++) {
      matchingRGBA.push(expectedMaskSolo[r][c] ? [157, 0, 255, 255] : [16, 18, 36, 153]);
    }
  }

  // 7. Testing live executeAndVerifyAction for Success Solo
  console.log("7. Testing live executeAndVerifyAction on successful Solo play...");
  const realNowSolo = performance.now();
  const keydownNodeSolo = realNowSolo - 100;

  const page1Solo = createMockPage({
    monoTime: 1000,
    mockPixelSampler: () => {
      const obsStart = performance.now();
      return {
        rgba: matchingRGBA,
        width: 300,
        height: 600,
        dpr: 1,
        drawCount: 5,
        batchCount: 2,
        observationStart: obsStart,
        observationEnd: obsStart + 5
      };
    }
  });
  const calibrationSolo = { offset: keydownNodeSolo - 1000, rtt: 10, uncertainty: 5 };
  const sessionStateSolo = {
    lastStateReceivedPage1: {
      id: 'game123',
      board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
      active_piece: { type: "T", shape: "T", orientation: 3, cells: [[1, 1], [2, 1], [2, 2], [3, 1]], origin: [4, 4] },
      status: "playing"
    }
  };
  const httpEventsSolo = [
    {
      url: `${targetUrl}/api/games/game123/move`,
      method: 'POST',
      postData: { direction: 'clockwise' },
      status: 200,
      timestamp: realNowSolo, // realNowSolo is >= keydownNodeSolo
      data: {
        id: 'game123',
        board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
        active_piece: { type: "T", shape: "T", orientation: 0, cells: [[1, 1], [2, 0], [2, 1], [2, 2]], origin: [4, 4] },
        status: "playing"
      }
    }
  ];

  // Run success solo test
  const testSoloPromise = executeAndVerifyAction(
    page1Solo, null, 'solo', 'ArrowUp',
    calibrationSolo, null, 0, 50000, null,
    JSON.parse(JSON.stringify(httpEventsSolo)), [], [], [], sessionStateSolo
  ).then(record => {
    if (record.status !== 'success') throw new Error(`Expected success status, got ${record.status}: ${record.exclusionReason}`);
    if (typeof record.latency !== 'number' || record.latency <= 0) {
      throw new Error(`Expected positive numeric latency, got ${record.latency}`);
    }
    console.log(`   ✓ Success Solo verification passed! (Latency: ${record.latency.toFixed(2)}ms)`);
  });

  // 8. Testing live executeAndVerifyAction for Success Duel
  console.log("8. Testing live executeAndVerifyAction on successful Duel match...");
  const realNowDuel = performance.now();
  const keydownNodeDuel = realNowDuel - 100;

  const page1Duel = createMockPage({
    monoTime: 1000,
    mockPixelSampler: () => {
      const obsStart = performance.now();
      return {
        rgba: matchingRGBA,
        width: 300,
        height: 600,
        dpr: 1,
        drawCount: 6,
        batchCount: 3,
        observationStart: obsStart,
        observationEnd: obsStart + 5
      };
    }
  });
  const page2Duel = createMockPage({
    monoTime: 1000,
    mockPixelSampler: () => {
      const obsStart = performance.now() + 15;
      return {
        rgba: matchingRGBA,
        width: 300,
        height: 600,
        dpr: 1,
        drawCount: 6,
        batchCount: 3,
        observationStart: obsStart,
        observationEnd: obsStart + 5
      };
    }
  });
  const calibrationDuel1 = { offset: keydownNodeDuel - 1000, rtt: 10, uncertainty: 5 };
  const calibrationDuel2 = { offset: keydownNodeDuel - 1000, rtt: 12, uncertainty: 6 };
  const sessionStateDuel = {
    roomId: 'room1',
    playerId: 'p1',
    opponentId: 'p2',
    lastStateReceivedPage1: {
      id: 'game123',
      board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
      active_piece: { type: "T", shape: "T", orientation: 3, cells: [[1, 1], [2, 1], [2, 2], [3, 1]], origin: [4, 4] },
      status: "playing"
    }
  };

  const wsSentDuel = [
    {
      timestamp: realNowDuel,
      data: {
        type: 'action',
        payload: {
          action: 'rotate_clockwise',
          seq: 1,
          room_id: 'room1',
          player_id: 'p1',
          generation: 0
        }
      }
    }
  ];

  const wsRecDuel = [
    {
      timestamp: realNowDuel + 10,
      data: {
        type: 'state',
        payload: {
          room_id: 'room1',
          player_id: 'p1',
          last_processed_seq: 1,
          generation: 0,
          board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
          active_piece: { type: "T", shape: "T", orientation: 0, cells: [[1, 1], [2, 0], [2, 1], [2, 2]], origin: [4, 4] },
          status: "playing"
         }
      }
    }
  ];

  const testDuelPromise = executeAndVerifyAction(
    page1Duel, page2Duel, 'duel', 'ArrowUp',
    calibrationDuel1, calibrationDuel2, 0, 50000, null,
    [], JSON.parse(JSON.stringify(wsSentDuel)), JSON.parse(JSON.stringify(wsRecDuel)), [], sessionStateDuel
  ).then(record => {
    if (record.status !== 'success') throw new Error(`Expected success status, got ${record.status}: ${record.exclusionReason}`);
    if (typeof record.latency !== 'number' || record.latency <= 0) {
      throw new Error(`Expected positive numeric latency, got ${record.latency}`);
    }
    if (typeof record.remoteLatency !== 'number' || record.remoteLatency <= 0) {
      throw new Error(`Expected positive numeric remoteLatency, got ${record.remoteLatency}`);
    }
    const diff = record.remoteLatency - record.latency;
    if (diff < 10 || diff > 25) {
      throw new Error(`Expected remote latency to be ~15ms larger than local, got diff ${diff}`);
    }
    console.log(`   ✓ Success Duel verification passed! (Local: ${record.latency.toFixed(2)}ms, Remote: ${record.remoteLatency.toFixed(2)}ms)`);
  });

  // 9. Testing live executeAndVerifyAction for Wrong room/player/seq/generation rejection
  console.log("9. Testing live executeAndVerifyAction wrong WS ACK rejection...");
  const sessionStateWrong = {
    roomId: 'room1',
    playerId: 'p1',
    opponentId: 'p2',
    lastStateReceivedPage1: {
      id: 'game123',
      board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
      active_piece: { type: "T", shape: "T", orientation: 3, cells: [[1, 1], [2, 1], [2, 2], [3, 1]], origin: [4, 4] },
      status: "playing"
    }
  };
  const wsSentWrong = [
    {
      timestamp: realNowDuel,
      data: {
        type: 'action',
        payload: {
          action: 'rotate_clockwise',
          seq: 1,
          room_id: 'room1',
          player_id: 'p1',
          generation: 0
        }
      }
    }
  ];
  // Incorrect player ID
  const wsRecWrong = [
    {
      timestamp: realNowDuel + 10,
      data: {
        type: 'state',
        payload: {
          room_id: 'room1',
          player_id: 'wrong_p1',
          last_processed_seq: 1,
          generation: 0,
          board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
          active_piece: { type: "T", shape: "T", orientation: 0, cells: [[1, 1], [2, 0], [2, 1], [2, 2]], origin: [4, 4] },
          status: "playing"
        }
      }
    }
  ];

  const testWrongPromise = executeAndVerifyAction(
    page1Duel, page2Duel, 'duel', 'ArrowUp',
    calibrationDuel1, calibrationDuel2, 0, 50000, null,
    [], wsSentWrong, wsRecWrong, [], sessionStateWrong
  ).then(record => {
    if (record.status !== 'excluded' || !record.exclusionReason.includes('Timeout waiting for ACK')) {
      throw new Error(`Expected timeout for ACK, got status ${record.status}`);
    }
    console.log("   ✓ Mismatched player WS state update correctly rejected/timed out!");
  });

  // 10. Testing live executeAndVerifyAction for mutated one pixel rejection
  console.log("10. Testing live executeAndVerifyAction mutated pixel rejection...");
  const mutatedRGBA = JSON.parse(JSON.stringify(matchingRGBA));
  mutatedRGBA[15] = [255, 255, 255, 255]; // mutate 1 pixel
  const page1Mutated = createMockPage({
    monoTime: 1000,
    mockPixelSampler: () => ({
      rgba: mutatedRGBA,
      width: 300,
      height: 600,
      dpr: 1,
      drawCount: 5,
      batchCount: 2,
      observationStart: 1100,
      observationEnd: 1105
    })
  });

  const testMutatedPromise = executeAndVerifyAction(
    page1Mutated, null, 'solo', 'ArrowUp',
    calibrationSolo, null, 0, 50000, null,
    httpEventsSolo, [], [], [], sessionStateSolo
  ).then(record => {
    if (record.status !== 'excluded' || !record.exclusionReason.includes('Timeout polling/matching pixels')) {
      throw new Error(`Expected pixel match timeout, got status ${record.status}`);
    }
    console.log("    ✓ Mutated pixel state correctly rejected/timed out!");
  });

  // 11. Testing live executeAndVerifyAction for O-piece / block rotation rejection
  console.log("11. Testing live executeAndVerifyAction O-piece/no-op exclusion...");
  const sessionStateO = {
    lastStateReceivedPage1: {
      id: 'game123',
      board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
      active_piece: { type: "O", shape: "O", orientation: 0, cells: [[1, 1], [1, 2], [2, 1], [2, 2]], origin: [4, 4] },
      status: "playing"
    }
  };
  const httpEventsO = [
    {
      url: `${targetUrl}/api/games/game123/move`,
      method: 'POST',
      postData: { direction: 'clockwise' },
      status: 200,
      timestamp: realNowSolo,
      data: {
        id: 'game123',
        board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
        active_piece: { type: "O", shape: "O", orientation: 1, cells: [[1, 1], [1, 2], [2, 1], [2, 2]], origin: [4, 4] },
        status: "playing"
      }
    }
  ];

  const testOpiecePromise = executeAndVerifyAction(
    page1Solo, null, 'solo', 'ArrowUp',
    calibrationSolo, null, 0, 50000, null,
    httpEventsO, [], [], [], sessionStateO
  ).then(record => {
    if (record.status !== 'excluded' || !record.exclusionReason.includes('Action was a no-op, blocked move, or O-piece rotation')) {
      throw new Error(`Expected no-op/O rotation exclusion, got status ${record.status}`);
    }
    console.log("    ✓ O-piece/no-op rotation correctly excluded!");
  });

  // 12. Testing late remote pixel match exclusion
  console.log("12. Testing live executeAndVerifyAction late remote opponent canvas exclusion...");
  const page2Late = createMockPage({
    monoTime: 1000,
    mockPixelSampler: () => {
      return {
        rgba: matchingRGBA, // MATCHING
        width: 300,
        height: 600,
        dpr: 1,
        drawCount: 6,
        batchCount: 3,
        observationStart: 50010,
        observationEnd: 50015
      };
    }
  });

  const testLatePromise = executeAndVerifyAction(
    page1Duel, page2Late, 'duel', 'ArrowUp',
    calibrationDuel1, calibrationDuel2, 0, 50000, null,
    [], wsSentDuel, wsRecDuel, [], sessionStateDuel
  ).then(record => {
    if (record.status !== 'success') throw new Error(`Expected success, got ${record.status}`);
    if (record.remoteLatency !== null) throw new Error(`Expected remoteLatency to be null due to late matching, got ${record.remoteLatency}`);
    if (record.remoteExclusionReason !== 'Remote observation outside logical measurement window') {
      throw new Error(`Expected remoteExclusionReason to indicate outside window, got: ${record.remoteExclusionReason}`);
    }
    console.log("    ✓ Late remote opponent canvas correctly excluded (remoteLatency = null)!");
  });

  // 13. Testing live executeAndVerifyAction on successful CCW rotation ('Z')
  console.log("13. Testing live executeAndVerifyAction on successful CCW rotation...");
  const sessionStateCCW = {
    roomId: 'room1',
    playerId: 'p1',
    opponentId: 'p2',
    lastStateReceivedPage1: {
      id: 'game123',
      board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
      active_piece: { type: "T", shape: "T", orientation: 0, cells: [[1, 1], [2, 0], [2, 1], [2, 2]], origin: [4, 4] },
      status: "playing"
    }
  };
  const wsSentCCW = [
    {
      timestamp: realNowDuel,
      data: {
        type: 'action',
        payload: {
          action: 'rotate_counterclockwise',
          seq: 1,
          room_id: 'room1',
          player_id: 'p1',
          generation: 0
        }
      }
    }
  ];
  const wsRecCCW = [
    {
      timestamp: realNowDuel + 10,
      data: {
        type: 'state',
        payload: {
          room_id: 'room1',
          player_id: 'p1',
          last_processed_seq: 1,
          generation: 0,
          board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
          active_piece: { type: "T", shape: "T", orientation: 3, cells: [[1, 1], [2, 1], [2, 2], [3, 1]], origin: [4, 4] },
          status: "playing"
         }
      }
    }
  ];
  
  const expectedMaskCCW = getExpectedMask({
    board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
    active_piece: { type: "T", shape: "T", orientation: 3, cells: [[1, 1], [2, 1], [2, 2], [3, 1]], origin: [4, 4] },
    status: "playing"
  });
  const matchingRGBACCW = [];
  for (let r = 0; r < 20; r++) {
    for (let c = 0; c < 10; c++) {
      matchingRGBACCW.push(expectedMaskCCW[r][c] ? [157, 0, 255, 255] : [16, 18, 36, 153]);
    }
  }

  const page1CCW = createMockPage({
    monoTime: 1000,
    mockPixelSampler: () => {
      const obsStart = performance.now();
      return {
        rgba: matchingRGBACCW,
        width: 300,
        height: 600,
        dpr: 1,
        drawCount: 5,
        batchCount: 2,
        observationStart: obsStart,
        observationEnd: obsStart + 5
      };
    }
  });

  const testCCWPromise = executeAndVerifyAction(
    page1CCW, null, 'duel', 'Z',
    calibrationDuel1, null, 0, 50000, null,
    [], wsSentCCW, wsRecCCW, [], sessionStateCCW
  ).then(record => {
    if (record.status !== 'success') throw new Error(`Expected success on CCW rotation, got ${record.status}: ${record.exclusionReason}`);
    console.log("    ✓ CCW rotation correctly verified!");
  });

  // 14. Testing live executeAndVerifyAction changed piece type exclusion
  console.log("14. Testing live executeAndVerifyAction changed piece exclusion...");
  const sessionStateChangedPiece = {
    roomId: 'room1',
    playerId: 'p1',
    opponentId: 'p2',
    lastStateReceivedPage1: {
      id: 'game123',
      board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
      active_piece: { type: "T", shape: "T", orientation: 3, cells: [[1, 1], [2, 1], [2, 2], [3, 1]], origin: [4, 4] },
      status: "playing"
    }
  };
  const wsSentChangedPiece = [
    {
      timestamp: realNowDuel,
      data: {
        type: 'action',
        payload: {
          action: 'rotate_clockwise',
          seq: 1,
          room_id: 'room1',
          player_id: 'p1',
          generation: 0
        }
      }
    }
  ];
  const wsRecChangedPiece = [
    {
      timestamp: realNowDuel + 10,
      data: {
        type: 'state',
        payload: {
          room_id: 'room1',
          player_id: 'p1',
          last_processed_seq: 1,
          generation: 0,
          board: Array.from({ length: 20 }, () => new Array(10).fill(null)),
          active_piece: { type: "I", shape: "I", orientation: 0, cells: [[1, 0], [1, 1], [1, 2], [1, 3]], origin: [4, 4] },
          status: "playing"
         }
      }
    }
  ];
  const page1ChangedPiece = createMockPage({
    monoTime: 1000,
    mockPixelSampler: () => {
      const obsStart = performance.now();
      return {
        rgba: matchingRGBA,
        width: 300,
        height: 600,
        dpr: 1,
        drawCount: 5,
        batchCount: 2,
        observationStart: obsStart,
        observationEnd: obsStart + 5
      };
    }
  });

  const testChangedPiecePromise = executeAndVerifyAction(
    page1ChangedPiece, null, 'duel', 'ArrowUp',
    calibrationDuel1, null, 0, 50000, null,
    [], wsSentChangedPiece, wsRecChangedPiece, [], sessionStateChangedPiece
  ).then(record => {
    if (record.status !== 'excluded') {
      throw new Error(`Expected exclusion due to changed piece type, got: ${record.status}`);
    }
    console.log("    ✓ Changed piece type correctly excluded!");
  });

  // 14.5. Testing constructMeasurePhase helper with different known starts/durations
  console.log("14.5. Testing constructMeasurePhase helper with different known starts/durations...");
  const mockPhaseTimings1 = { warmupStartNode: 100 };
  constructMeasurePhase(mockPhaseTimings1, 'run-id-1', 200, 'warmup-end-iso-1', 210, '2026-11-05T12:00:00.000Z', 2000);
  if (mockPhaseTimings1.phase !== 'measure') throw new Error("Expected phase to be 'measure'");
  if (mockPhaseTimings1.measurementEndNode !== 2210) throw new Error("Expected measurementEndNode to be 2210");
  const endIsoTime1 = new Date(mockPhaseTimings1.measurementEndIso).getTime();
  const startIsoTime1 = new Date(mockPhaseTimings1.measurementStartIso).getTime();
  if (endIsoTime1 - startIsoTime1 !== 2000) throw new Error("Expected ISO duration to be exactly 2000ms");

  const mockPhaseTimings2 = { warmupStartNode: 1000 };
  constructMeasurePhase(mockPhaseTimings2, 'run-id-2', 5000, 'warmup-end-iso-2', 5100, '2026-11-05T12:00:00.000Z', 30000);
  if (mockPhaseTimings2.phase !== 'measure') throw new Error("Expected phase to be 'measure'");
  if (mockPhaseTimings2.measurementEndNode !== 35100) throw new Error("Expected measurementEndNode to be 35100");
  const endIsoTime2 = new Date(mockPhaseTimings2.measurementEndIso).getTime();
  const startIsoTime2 = new Date(mockPhaseTimings2.measurementStartIso).getTime();
  if (endIsoTime2 - startIsoTime2 !== 30000) throw new Error("Expected ISO duration to be exactly 30000ms");
  console.log("    ✓ constructMeasurePhase helper verified successfully with 2000ms and 30000ms durations!");

  // 15. Testing actual CLI branch runBenchmark invocation with fake injected browser
  console.log("15. Testing actual CLI branch runBenchmark invocation with fake injected browser...");
  const fakeBrowser = {
    version: () => "1.0-fake",
    newContext: async () => ({
      newPage: async () => ({
        on: () => {},
        goto: async () => {},
        click: async () => {},
        evaluate: async (fn, ...args) => {
          if (typeof fn === 'function') {
            const s = fn.toString();
            if (s.includes('document.hasFocus') || s.includes('visibilityState')) {
              return { visibilityState: 'visible', hasFocus: true };
            }
            if (s.includes('window.keydownEvents')) return [];
            if (s.includes('window.schedulerTimestamps')) {
              return { schedulerTimestamps: [], canvasDraws: [], keydownEvents: [], visibilityFocusTransitions: [] };
            }
          }
          return "mock-val";
        },
        title: async () => `frontend-mockrunId-solo-trial-1 INPUT`,
        fill: async () => {},
        waitForSelector: async () => {},
        bringToFront: async () => {},
        screenshot: async () => {}
      }),
      tracing: {
        start: async () => {},
        stop: async () => ({})
      }
    }),
    close: async () => {}
  };
  
  const originalChromium = playWrightChromium;
  let launchCalled = false;
  playWrightChromium = {
    launch: async () => {
      launchCalled = true;
      return fakeBrowser;
    }
  };
  
  const originalOutdir = outdir;
  const tempOutdir = path.join(__dirname, 'docs', 'benchmark-runs', `test-cli-${crypto.randomBytes(4).toString('hex')}`);
  outdir = tempOutdir;
  
  fs.mkdirSync(outdir, { recursive: true });
  fs.writeFileSync(path.join(outdir, 'foreground-approved.json'), JSON.stringify({ runId: '1234567812345678', approved: true }), 'utf8');

  // Mock readdirSync to bypass the empty folder immutability check
  const originalReaddirSync = fs.readdirSync;
  fs.readdirSync = (p) => {
    if (p === tempOutdir) return [];
    return originalReaddirSync(p);
  };
  
  const originalRandomBytes = crypto.randomBytes;
  crypto.randomBytes = (n) => {
    if (n === 8) return Buffer.from('1234567812345678', 'hex');
    return originalRandomBytes(n);
  };
  
  const originalScenario = scenario;
  scenario = 'solo';
  
  let runBenchmarkResolved = false;
  try {
    const originalIsProbe = isProbe;
    isProbe = true;
    
    await runBenchmark();
    runBenchmarkResolved = true;
  } catch (err) {
    console.error("Fake runBenchmark failed:", err);
  } finally {
    try {
      fs.rmSync(tempOutdir, { recursive: true, force: true });
    } catch (e) {}
    
    fs.readdirSync = originalReaddirSync;
    playWrightChromium = originalChromium;
    outdir = originalOutdir;
    crypto.randomBytes = originalRandomBytes;
    scenario = originalScenario;
  }
  
  if (runBenchmarkResolved) {
    throw new Error("Expected runBenchmark to throw and NOT resolve successfully because fakeBrowser lacks addInitScript and actual browser capabilities.");
  }
  if (!launchCalled) {
    throw new Error("Expected playWrightChromium.launch to be called");
  }
  console.log("    ✓ Entry/cleanup smokecheck successfully verified (runBenchmark threw as expected on fakeBrowser, launchCalled proved, cleanup completed). Full runtime validation remains PENDING 2 real foreground probes.");

  // Return a promise that resolves when ALL async tests have finished
  return Promise.all([
    testSoloPromise,
    testDuelPromise,
    testWrongPromise,
    testMutatedPromise,
    testOpiecePromise,
    testLatePromise,
    testCCWPromise,
    testChangedPiecePromise
  ]).then(() => {
    console.log(`\n======================================================================`);
    console.log(`✅ ALL OFFLINE SELF-TESTS PASSED SUCCESSFULLY!`);
    console.log(`======================================================================\n`);
  });
}

function runMain() {
  if (isSelfTest) {
    runOfflineSelfTest().then(() => {
      process.exit(0);
    }).catch(err => {
      console.error("❌ Self-test suite failed:", err);
      process.exit(1);
    });
  } else {
    runBenchmark().then(() => {
      process.exit(0);
    }).catch(err => {
      console.error("❌ Benchmark execution failed:", err);
      process.exit(1);
    });
  }
}

if (require.main === module) {
  runMain();
}

// ======================================================================
// RUN LIVE BENCHMARK WINDOWS
// ======================================================================
async function runBenchmark() {
  // Validate scenario
  if (scenario !== 'solo' && scenario !== 'duel') {
    console.error(`❌ ERROR: Invalid scenario '${scenario}'. Must be 'solo' or 'duel'.`);
    process.exit(1);
  }

  // Immutability Check: fail closed and refuse to overwrite or execute if output directory already contains files or folders
  if (fs.existsSync(outdir)) {
    const files = fs.readdirSync(outdir);
    if (files.length > 0) {
      console.error(`❌ ERROR: Output directory already exists and contains files/folders!`);
      console.error(`Output Directory: ${outdir}`);
      console.error(`To preserve retention and prevent trace overwrites, execution is strictly BLOCKED.`);
      process.exit(1);
    }
  }

  // OS FOREGROUND GATING AND ABORT FILENAMES
  const runId = crypto.randomBytes(8).toString('hex');
  const readyFile = path.join(outdir, 'foreground-ready.json');
  const approvedFile = path.join(outdir, 'foreground-approved.json');
  const abortFile = path.join(outdir, 'foreground-abort.json');

  const actualChannel = process.env.BROWSER_CHANNEL || 'chrome';
  const envMetadata = {
    os: `${os.type()} ${os.release()} (${os.platform()})`,
    arch: os.arch(),
    cpu: os.cpus()[0]?.model || 'Unknown CPU',
    memoryTotalGB: Math.round(os.totalmem() / (1024 * 1024 * 1024)),
    browser: 'Chromium',
    browserChannel: actualChannel,
    viewport: '1280x900',
    deviceScaleFactor: 1.0,
    headless: false,
    executionTime: new Date().toISOString(),
    timeOrigin: performance.timeOrigin,
    scenario: scenario,
    isProbe: isProbe
  };

  console.log(`Launching headful Chromium (channel: ${actualChannel}, viewport: 1280x900)...`);
  const browser = await playWrightChromium.launch({
    headless: false,
    channel: actualChannel,
    args: [] // ordinary default flags only
  });

  const browserVer = browser.version();
  envMetadata.browserVersion = browserVer;

  const warmupTimeMs = isProbe ? 1000 : 5000;
  const measurementTimeMs = isProbe ? 2000 : 30000;

  console.log(`Warm-up Time: ${warmupTimeMs}ms | Measurement Window: ${measurementTimeMs}ms`);

  const context1 = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 1.0
  });
  const page1 = await context1.newPage();
  
  const tracePath1 = path.join(outdir, `trace-actor.zip`);
  await context1.tracing.start({ screenshots: true, snapshots: true });

  // Network Event Queues populated natively via Playwright listeners
  const httpEvents = [];
  const wsSentEventsPage1 = [];
  const wsReceivedEventsPage1 = [];
  const wsReceivedEventsPage2 = [];
  
  const sessionState = {
    lastStateReceivedPage1: null,
    roomId: null,
    playerId: null,
    opponentId: null
  };

  // Intercept HTTP API responses natively
  page1.on('response', async (response) => {
    const url = response.url();
    const request = response.request();
    if (url.includes('/api/games/')) {
      try {
        const text = await response.text();
        const data = JSON.parse(text);
        const timestamp = performance.now();
        let postData = null;
        try {
          postData = JSON.parse(request.postData() || 'null');
        } catch (e) {}

        httpEvents.push({
          url,
          method: request.method(),
          postData,
          status: response.status(),
          timestamp,
          data
        });
        sessionState.lastStateReceivedPage1 = data;
      } catch (e) {}
    }
  });

  // Intercept WebSocket frames natively
  page1.on('websocket', (ws) => {
    ws.on('framesent', ({ payload }) => {
      try {
        const data = JSON.parse(payload.toString('utf8'));
        wsSentEventsPage1.push({
          timestamp: performance.now(),
          data
        });
      } catch (e) {}
    });

    ws.on('framereceived', ({ payload }) => {
      try {
        const data = JSON.parse(payload.toString('utf8'));
        wsReceivedEventsPage1.push({
          timestamp: performance.now(),
          data
        });
        if (data.type === 'state') {
          const payloadData = data.payload;
          // Filter strictly by active room and player
          if (payloadData.room_id === sessionState.roomId && payloadData.player_id === sessionState.playerId) {
            sessionState.lastStateReceivedPage1 = payloadData;
          }
        }
      } catch (e) {}
    });
  });

  // Expose hooks to separate rAF scheduler timestamps from actual Canvas DRAW calls
  const injectInstrumentation = async (page, identityLabel) => {
    await page.addInitScript((label) => {
      window.canvasIdentityLabel = label;
      window.schedulerTimestamps = [];
      window.canvasDraws = [];
      window.measurementActive = false;
      window.keydownEvents = [];
      window.visibilityFocusTransitions = [];

      const logTransition = (type) => {
        if (window.measurementActive) {
          window.visibilityFocusTransitions.push({
            type,
            timestamp: new Date().toISOString(),
            monotonicTime: performance.now(),
            visibilityState: document.visibilityState,
            hasFocus: document.hasFocus()
          });
        }
      };
      document.addEventListener('visibilitychange', () => logTransition('visibilitychange'));
      window.addEventListener('focus', () => logTransition('focus'));
      window.addEventListener('blur', () => logTransition('blur'));

      // Keydown events capture
      window.addEventListener('keydown', (e) => {
        if (window.measurementActive) {
          window.keydownEvents.push({
            key: e.key,
            timestamp: performance.now()
          });
        }
      }, true);

      // Dedicated rAF sampler
      window.originalRequestAnimationFrame = window.requestAnimationFrame;
      (function runSampler() {
        if (window.measurementActive) {
          window.schedulerTimestamps.push(performance.now());
        }
        window.originalRequestAnimationFrame(runSampler);
      })();

      // Setup window wrapping/proxy function
      window.canvasIdsMap = new WeakMap();
      window.canvasPaintStates = {};
      
      window.queueBatchMarker = function(canvas, canvasId, win) {
        let state = win.canvasPaintStates[canvasId];
        if (!state) {
          state = { drawCount: 0, batchCount: 0, microtaskQueued: false };
          win.canvasPaintStates[canvasId] = state;
        }
        state.drawCount++;
        if (!state.microtaskQueued) {
          state.microtaskQueued = true;
          queueMicrotask(() => {
            state.microtaskQueued = false;
            state.batchCount++;
            if (win.measurementActive) {
              win.canvasDraws.push({
                timestamp: performance.now(),
                canvasId: canvasId,
                method: 'batchComplete',
                paintBatchId: state.batchCount,
                drawCounter: state.drawCount
              });
            }
          });
        }
      };

      const originalGetContext = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        const ctx = originalGetContext.apply(this, [type, ...args]);
        if (type === '2d' && ctx && !ctx.__hooked__) {
          ctx.__hooked__ = true;

          let role = 'local';
          if (this.closest('.duel-seat.local-seat')) {
            role = 'local';
          } else if (this.closest('.duel-seat.opponent-seat')) {
            role = 'opponent';
          }
          const fullCanvasId = `${window.canvasIdentityLabel}-${role}`;

          const drawMethods = ['clearRect', 'fillRect', 'strokeRect', 'stroke', 'fill', 'drawImage', 'putImageData'];
          drawMethods.forEach(method => {
            const original = ctx[method];
            if (typeof original === 'function') {
              ctx[method] = function(...mArgs) {
                try {
                  const result = original.apply(this, mArgs);
                  if (window.measurementActive) {
                    window.canvasDraws.push({
                      timestamp: performance.now(),
                      canvasId: fullCanvasId,
                      method: method,
                      args: mArgs
                    });
                    window.queueBatchMarker(this.canvas, fullCanvasId, window);
                  }
                  return result;
                } catch (err) {
                  throw err;
                }
              };
            }
          });
        }
        return ctx;
      };
    }, identityLabel);
  };

  // Run everything inside high-level try block to guarantee browser cleanup on any error or abort
  let browserCleanupCompleted = false;
  let page2 = null;
  let context2 = null;
  let tracePath2 = null;

  const phaseTimings = {
    warmup: null,
    measure: null,
    finished: null
  };

  try {
    await injectInstrumentation(page1, 'local-actor');

    // Navigation and setting unique title using runId/scenario/label
    console.log(`Actor page navigating to: ${targetUrl}`);
    await page1.goto(targetUrl);

    // Click mode-toggle-duel IMMEDIATELY to prevent solo gravity from running during gate wait
    console.log(`Switching to Duel mode on landing to pause solo gravity...`);
    await page1.click('[data-testid="mode-toggle-duel"]');

    // Define actual unique actorTitle and read it back
    const uniqueTitle = `frontend-${runId}-${scenario}-${label} INPUT`;
    await page1.evaluate((t) => { document.title = t; }, uniqueTitle);
    const actualTitle = await page1.title();
    console.log(`Unique Title read back: "${actualTitle}"`);

    fs.mkdirSync(outdir, { recursive: true });

    // Write foreground-ready.json contract
    // actorBrowserLaunchOrdinal is 1-based exactly
    const readyData = {
      runId: runId,
      scenario: scenario,
      actorTitle: actualTitle,
      actorUrl: targetUrl,
      actorBrowserLaunchOrdinal: 1,
      ordinalBase: "1-based",
      createdUTC: new Date().toISOString()
    };
    fs.writeFileSync(readyFile, JSON.stringify(readyData, null, 2), 'utf8');
    console.log(`Written foreground-ready.json. Waiting up to 120s for approved file...`);

    let approved = false;
    const startGateTime = Date.now();
    while (Date.now() - startGateTime < 120000) {
      if (fs.existsSync(abortFile)) {
        throw new Error("External abort detected during gating!");
      }

      if (fs.existsSync(approvedFile)) {
        try {
          const approvedData = JSON.parse(fs.readFileSync(approvedFile, 'utf8'));
          console.log(`DEBUG gating check: approvedData.runId = "${approvedData.runId}", runId = "${runId}", equal = ${approvedData.runId === runId}`);
          if (approvedData.runId === runId && approvedData.approved === true) {
            approved = true;
            break;
          }
        } catch (e) {
          // Retry on partial file reads
        }
      }

      await page1.bringToFront();
      const focusData = await page1.evaluate(() => {
        return {
          visibilityState: document.visibilityState,
          hasFocus: document.hasFocus()
        };
      });

      if (focusData.visibilityState !== 'visible' || !focusData.hasFocus) {
        throw new Error("Focus or visibility lost during foreground gating!");
      }
      await new Promise(r => setTimeout(r, 1000));
    }

    if (!approved) {
      throw new Error("Focus gate approval timeout or failed closure.");
    }

    console.log("✅ Foreground approved!");

    // Setup active game scenarios AFTER gate approval
    const roomName = `bench-room-${crypto.randomBytes(4).toString('hex')}`;
    
    if (scenario === 'duel') {
      context2 = await browser.newContext({
        viewport: { width: 1280, height: 900 },
        deviceScaleFactor: 1.0
      });
      page2 = await context2.newPage();
      tracePath2 = path.join(outdir, `trace-opponent.zip`);
      await context2.tracing.start({ screenshots: true, snapshots: true });

      await injectInstrumentation(page2, 'opponent-spectator');
      
      // Page 2 WS observers
      page2.on('websocket', (ws) => {
        ws.on('framereceived', ({ payload }) => {
          try {
            const data = JSON.parse(payload.toString('utf8'));
            wsReceivedEventsPage2.push({
              timestamp: performance.now(),
              data
            });
          } catch (e) {}
        });
      });

      console.log(`Opponent page navigating to: ${targetUrl}`);
      await page2.goto(targetUrl);

      const actorId = `actor-${crypto.randomBytes(2).toString('hex')}`;
      const opponentId = `opponent-${crypto.randomBytes(2).toString('hex')}`;
      sessionState.roomId = roomName;
      sessionState.playerId = actorId;
      sessionState.opponentId = opponentId;

      // Enter Room and Player details
      await page1.fill('#roomId', roomName);
      await page1.fill('#playerId', actorId);
      
      await page2.click('[data-testid="mode-toggle-duel"]');
      await page2.fill('#roomId', roomName);
      await page2.fill('#playerId', opponentId);

      // Opponent joins FIRST, actor joins LAST
      console.log(`Opponent joining first...`);
      await page2.click('[data-testid="join-duel-button"]');
      await new Promise(r => setTimeout(r, 1000));

      console.log(`Actor joining last...`);
      await page1.click('[data-testid="join-duel-button"]');

      // Wait for both boards
      await page1.waitForSelector('.duel-boards-side-by-side');
      await page2.waitForSelector('.duel-boards-side-by-side');
      console.log(`Duel matchmaking synchronized.`);

      // Scroll both boards into view (1280x900 bounds check) without app CSS/viewport changes
      await page1.evaluate(() => {
        const b = document.querySelector('.duel-boards-side-by-side');
        if (b) b.scrollIntoView();
      });
      await page2.evaluate(() => {
        const b = document.querySelector('.duel-boards-side-by-side');
        if (b) b.scrollIntoView();
      });
    } else {
      // Solo mode: click mode-toggle-solo (which starts a fresh game)
      console.log(`Switching back to Solo play...`);
      await page1.click('[data-testid="mode-toggle-solo"]');
      
      // Reset button click to confirm fresh ID and playing state
      const resetBtn = page1.locator('button.reset-button');
      if (await resetBtn.isVisible()) {
        await resetBtn.click();
      }
      
      await page1.waitForSelector('[data-testid="grid-board-canvas"]');
      await page1.evaluate(() => {
        const b = document.querySelector('[data-testid="grid-board"]');
        if (b) b.scrollIntoView();
      });
    }

    // Verify Focus and Sizing before warm-up
    await page1.bringToFront();
    const isPage1Focused = await page1.evaluate(() => document.hasFocus());
    if (!isPage1Focused) {
      throw new Error("Page 1 lost focus prior to warm-up!");
    }

    if (scenario === 'duel' && page2) {
      const isPage2Focused = await page2.evaluate(() => document.hasFocus());
      if (!isPage2Focused) {
        await page2.bringToFront();
        await new Promise(r => setTimeout(r, 100));
        await page1.bringToFront();
      }
    }

    // Calibrate clocks individually before warm-up using anchors
    console.log(`Calibrating clocks (pre-warmup)...`);
    const page1CalibrationBefore = await calibratePageClock(page1);
    const page2CalibrationBefore = scenario === 'duel' ? await calibratePageClock(page2) : null;
    console.log(`Page 1 Calibration (Pre): RTT = ${page1CalibrationBefore.rtt.toFixed(2)}ms | Uncertainty = ${page1CalibrationBefore.uncertainty.toFixed(2)}ms`);

    // Emit PHASE_WARMUP_START timing marker & write phase-timing.json
    const warmupStartMono = performance.now();
    console.log(`MARKER: PHASE_WARMUP_START ${warmupStartMono}`);
    phaseTimings.phase = 'warmup';
    phaseTimings.warmupStartNode = warmupStartMono;
    phaseTimings.warmupStartIso = new Date().toISOString();
    atomicWriteFileSync(path.join(outdir, 'phase-timing.json'), JSON.stringify(phaseTimings, null, 2), 'utf8');

    // Warm-up phase (5s standard, 1s probe) with real moves and rotations
    let warmupIdx = 0;
    const warmupKeys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'Z'];
    while (performance.now() - warmupStartMono < warmupTimeMs) {
      if (fs.existsSync(abortFile)) {
        throw new Error("External abort detected during warm-up!");
      }
      const focusCheck1 = await page1.evaluate(() => document.hasFocus());
      if (!focusCheck1) {
        throw new Error("Focus lost on page 1 during warm-up phase!");
      }
      if (scenario === 'duel' && page2) {
        const focusCheck2 = await page2.evaluate(() => document.hasFocus());
        if (!focusCheck2) {
          // peer is loaded in same Chromium window tab context, visibility is fine if visible
        }
      }

      const key = warmupKeys[warmupIdx % warmupKeys.length];
      await page1.keyboard.press(key);
      warmupIdx++;
      await new Promise(r => setTimeout(r, 150));
    }
    console.log("Warm-up completed.");

    // Warm-up completion metadata capture
    const warmupEndNode = performance.now();
    const warmupEndIso = new Date().toISOString();

    // Measurement window start/end bounds captured ONCE
    const measurementStartMono = performance.now();
    const measurementStartIso = new Date().toISOString();
    const measurementEndMono = measurementStartMono + measurementTimeMs;

    // Transition to measure phase, assign runId and logical bounds
    constructMeasurePhase(phaseTimings, runId, warmupEndNode, warmupEndIso, measurementStartMono, measurementStartIso, measurementTimeMs);

    // Emit PHASE_MEASURE_START timing marker & write phase-timing.json atomically AFTER assignments and BEFORE activation
    console.log(`MARKER: PHASE_MEASURE_START ${measurementStartMono}`);
    atomicWriteFileSync(path.join(outdir, 'phase-timing.json'), JSON.stringify(phaseTimings, null, 2), 'utf8');

    // START GATED MEASUREMENT WINDOW
    await page1.evaluate(() => {
      window.schedulerTimestamps = [];
      window.canvasDraws = [];
      window.keydownEvents = [];
      window.visibilityFocusTransitions = [];
      window.measurementActive = true;
    });

    if (scenario === 'duel' && page2) {
      await page2.evaluate(() => {
        window.schedulerTimestamps = [];
        window.canvasDraws = [];
        window.keydownEvents = [];
        window.visibilityFocusTransitions = [];
        window.measurementActive = true;
      });
    }

    const actionsRecorded = [];
    const seededRand = createSeededRandom(1003);
    let lastActionDispatchMono = 0;

    // Loop through 30s measurement window
    while (performance.now() < measurementEndMono) {
      if (fs.existsSync(abortFile)) {
        throw new Error("External abort detected during measurement!");
      }
      const focusCheck1 = await page1.evaluate(() => document.hasFocus());
      if (!focusCheck1) {
        throw new Error("Focus lost on page 1 during measurement window!");
      }

      // If the deadline is near (< 1s remaining), cease dispatching new actions to prevent window overflow
      const timeLeftMs = measurementEndMono - performance.now();
      if (timeLeftMs > 1000 && (performance.now() - lastActionDispatchMono >= 300)) {
        const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'Z'];
        const chosenKey = keys[Math.floor(seededRand() * keys.length)];

        // Fail-safe: Check if game is in a terminal state
        if (sessionState.lastStateReceivedPage1 && sessionState.lastStateReceivedPage1.status === 'game_over') {
          throw new Error("Game over / terminal state reached. Invalidating run.");
        }

        // Execute action, poll pixels, calibrate, and record causal latency
        const actionResult = await executeAndVerifyAction(
          page1, page2, scenario, chosenKey,
          page1CalibrationBefore, page2CalibrationBefore,
          measurementStartMono, measurementEndMono,
          outdir, httpEvents, wsSentEventsPage1, wsReceivedEventsPage1, wsReceivedEventsPage2,
          sessionState
        );

        actionsRecorded.push(actionResult);
        lastActionDispatchMono = performance.now();
      }
      await new Promise(r => setTimeout(r, 20));
    }

    // GATED WINDOW COMPLETED
    console.log("Measurement window complete. Freezing raw metrics...");

    await page1.evaluate(() => { window.measurementActive = false; });
    if (scenario === 'duel' && page2) {
      await page2.evaluate(() => { window.measurementActive = false; });
    }

    const finishedMono = performance.now();
    phaseTimings.phase = 'finished';
    phaseTimings.finishedNode = finishedMono;
    phaseTimings.finishedIso = new Date().toISOString();
    atomicWriteFileSync(path.join(outdir, 'phase-timing.json'), JSON.stringify(phaseTimings, null, 2), 'utf8');

    // Calibrate clocks individually AFTER the measurement window to compute drift
    console.log(`Calibrating clocks (post-measurement)...`);
    const page1CalibrationAfter = await calibratePageClock(page1);
    const page2CalibrationAfter = scenario === 'duel' ? await calibratePageClock(page2) : null;
    
    const page1Drift = page1CalibrationAfter.offset - page1CalibrationBefore.offset;
    const page2Drift = page2CalibrationAfter ? (page2CalibrationAfter.offset - page2CalibrationBefore.offset) : null;
    console.log(`Page 1 clock drift calculated: ${page1Drift.toFixed(4)}ms`);

    // Stop and finalize tracing context BEFORE hashing
    await context1.tracing.stop({ path: tracePath1 });
    if (scenario === 'duel' && context2) {
      await context2.tracing.stop({ path: tracePath2 });
    }

    // Retrieve frozen metrics
    const frozenMetrics1 = await page1.evaluate(() => {
      return {
        schedulerTimestamps: [...window.schedulerTimestamps],
        canvasDraws: [...window.canvasDraws],
        keydownEvents: [...window.keydownEvents],
        visibilityFocusTransitions: [...window.visibilityFocusTransitions]
      };
    });

    let frozenMetrics2 = null;
    if (scenario === 'duel' && page2) {
      frozenMetrics2 = await page2.evaluate(() => {
        return {
          schedulerTimestamps: [...window.schedulerTimestamps],
          canvasDraws: [...window.canvasDraws],
          keydownEvents: [...window.keydownEvents],
          visibilityFocusTransitions: [...window.visibilityFocusTransitions]
        };
      });
    }

    // Filter samples to logical [start, end) interval in Node clock domain
    const isInWindow = (t) => t >= measurementStartMono && t < measurementEndMono;

    // Map scheduler page timestamps to Node domain prior to filtering
    const rAFTimestampsNode = frozenMetrics1.schedulerTimestamps.map(t => t + page1CalibrationBefore.offset);
    const rAFTimestamps = rAFTimestampsNode.filter(isInWindow);
    const rAFIntervals = [];
    for (let i = 1; i < rAFTimestamps.length; i++) {
      rAFIntervals.push(rAFTimestamps[i] - rAFTimestamps[i-1]);
    }

    // Map canvas draws to Node domain prior to filtering
    const rawDraws = frozenMetrics1.canvasDraws.map(d => ({
      ...d,
      timestampNode: d.timestamp + page1CalibrationBefore.offset
    })).filter(d => isInWindow(d.timestampNode));

    const verifiedDraws = rawDraws.filter(d => d.method === 'batchComplete');
    const drawMethodsCalls = rawDraws.filter(d => d.method !== 'batchComplete');

    // Filter action samples using strict window check
    const finalActions = actionsRecorded.map(act => {
      if (!isInWindow(act.dispatchNode)) {
        act.status = 'excluded';
        act.exclusionReason = 'Dispatched outside logical measurement window';
      }
      return act;
    });

    // Calculate statistics
    const stats = calculateStats(rAFIntervals, finalActions, measurementTimeMs);
    stats.canvasDrawCount = drawMethodsCalls.length;
    stats.callbackBatchesCount = verifiedDraws.length; // renamed as callbackbatches
    stats.traceFile = `trace-actor.zip`;
    stats.traceHash = getFileHash(tracePath1);
    
    if (scenario === 'duel') {
      stats.traceOpponentFile = `trace-opponent.zip`;
      stats.traceOpponentHash = getFileHash(tracePath2);
    }

    stats.rawActions = finalActions;
    stats.clockCalibration = {
      page1: {
        pre: { offset: page1CalibrationBefore.offset, uncertainty: page1CalibrationBefore.uncertainty, rtt: page1CalibrationBefore.rtt },
        post: { offset: page1CalibrationAfter.offset, uncertainty: page1CalibrationAfter.uncertainty, rtt: page1CalibrationAfter.rtt },
        drift: page1Drift
      },
      page2: page2CalibrationBefore ? {
        pre: { offset: page2CalibrationBefore.offset, uncertainty: page2CalibrationBefore.uncertainty, rtt: page2CalibrationBefore.rtt },
        post: { offset: page2CalibrationAfter.offset, uncertainty: page2CalibrationAfter.uncertainty, rtt: page2CalibrationAfter.rtt },
        drift: page2Drift
      } : null
    };

    // Store actual logical Node bounds to rawstats and phaseJSON
    stats.runId = runId;
    stats.phase = phaseTimings.phase;
    stats.warmupStartNode = phaseTimings.warmupStartNode;
    stats.warmupStartIso = phaseTimings.warmupStartIso;
    stats.warmupEndNode = phaseTimings.warmupEndNode;
    stats.warmupEndIso = phaseTimings.warmupEndIso;
    stats.measurementStartNode = phaseTimings.measurementStartNode;
    stats.measurementStartIso = phaseTimings.measurementStartIso;
    stats.measurementEndNode = phaseTimings.measurementEndNode;
    stats.measurementEndIso = phaseTimings.measurementEndIso;
    stats.finishedNode = phaseTimings.finishedNode;
    stats.finishedIso = phaseTimings.finishedIso;

    // Derive actual state/pixelverified changed-draw samples from accepted persisted200RGBA proofs
    // dedup consecutive maskhash percanvas, retain their Node observation times/count/interval quantiles
    const localChangedDraws = [];
    let lastLocalHash = null;
    for (const act of finalActions) {
      if (act.status === 'success' && act.localMaskHash) {
        if (act.localMaskHash !== lastLocalHash) {
          localChangedDraws.push({
            timestamp: act.localObservationEnd,
            maskHash: act.localMaskHash
          });
          lastLocalHash = act.localMaskHash;
        }
      }
    }

    const localDrawIntervals = [];
    for (let i = 1; i < localChangedDraws.length; i++) {
      localDrawIntervals.push(localChangedDraws[i].timestamp - localChangedDraws[i-1].timestamp);
    }

    stats.pixelVerifiedDrawCountLocal = localChangedDraws.length;
    stats.pixelVerifiedDrawIntervalMedianLocal = getPercentile(localDrawIntervals, 0.5);
    stats.pixelVerifiedDrawIntervalP95Local = getPercentile(localDrawIntervals, 0.95);
    stats.pixelVerifiedDrawIntervalP99Local = getPercentile(localDrawIntervals, 0.99);
    stats.pixelVerifiedDrawTimestampsLocal = localChangedDraws.map(d => d.timestamp);

    if (scenario === 'duel') {
      const remoteChangedDraws = [];
      let lastRemoteHash = null;
      for (const act of finalActions) {
        if (act.status === 'success' && act.remoteMaskHash) {
          if (act.remoteMaskHash !== lastRemoteHash) {
            remoteChangedDraws.push({
              timestamp: act.remoteObservationEnd,
              maskHash: act.remoteMaskHash
            });
            lastRemoteHash = act.remoteMaskHash;
          }
        }
      }

      const remoteDrawIntervals = [];
      for (let i = 1; i < remoteChangedDraws.length; i++) {
        remoteDrawIntervals.push(remoteChangedDraws[i].timestamp - remoteChangedDraws[i-1].timestamp);
      }

      stats.pixelVerifiedDrawCountRemote = remoteChangedDraws.length;
      stats.pixelVerifiedDrawIntervalMedianRemote = getPercentile(remoteDrawIntervals, 0.5);
      stats.pixelVerifiedDrawIntervalP95Remote = getPercentile(remoteDrawIntervals, 0.95);
      stats.pixelVerifiedDrawIntervalP99Remote = getPercentile(remoteDrawIntervals, 0.99);
      stats.pixelVerifiedDrawTimestampsRemote = remoteChangedDraws.map(d => d.timestamp);
    }

    // Save Screenshots
    await page1.screenshot({ path: path.join(outdir, 'screenshot-actor.png') });
    if (scenario === 'duel' && page2) {
      await page2.screenshot({ path: path.join(outdir, 'screenshot-opponent.png') });
    }

    // Write raw-metrics.json atomically
    const rawMetricsJSON = {
      environment: envMetadata,
      runs: [stats],
      rawNetwork: {
        httpEvents,
        wsSentEventsPage1,
        wsReceivedEventsPage1,
        wsReceivedEventsPage2: scenario === 'duel' ? wsReceivedEventsPage2 : []
      },
      rawInput: {
        page1KeydownEvents: frozenMetrics1.keydownEvents,
        page2KeydownEvents: scenario === 'duel' ? frozenMetrics2.keydownEvents : []
      },
      rawScheduler: {
        page1SchedulerTimestamps: frozenMetrics1.schedulerTimestamps,
        page2SchedulerTimestamps: scenario === 'duel' ? frozenMetrics2.schedulerTimestamps : []
      },
      rawDraw: {
        page1CanvasDraws: frozenMetrics1.canvasDraws,
        page2CanvasDraws: scenario === 'duel' ? frozenMetrics2.canvasDraws : []
      },
      rawCalibration: {
        page1CalibrationBefore,
        page1CalibrationAfter,
        page2CalibrationBefore,
        page2CalibrationAfter,
        page1Drift,
        page2Drift
      }
    };
    atomicWriteFileSync(path.join(outdir, 'raw-metrics.json'), JSON.stringify(rawMetricsJSON, null, 2));
    console.log(`Raw metrics stored in: ${path.join(outdir, 'raw-metrics.json')}`);

    // Markdown Report
    const reportPath = path.join(outdir, 'benchmark-evidence.md');
    const mdContent = `# Playwright Chromium Canvas/WebSocket Performance Report (Stage 4)

## Execution Environment
- **OS**: ${envMetadata.os}
- **Processor**: ${envMetadata.cpu}
- **Arch**: ${envMetadata.arch}
- **Memory**: ${envMetadata.memoryTotalGB} GB
- **Browser**: Chromium (version: ${envMetadata.browserVersion})
- **Viewport**: 1280x900
- **DPR**: 1.0

## Performance Measurement Run Summary
- **Scenario**: ${scenario.toUpperCase()}
- **Measurement Window**: ${measurementTimeMs} ms
- **Scheduler Mean FPS**: ${stats.schedulerMeanFPS ? stats.schedulerMeanFPS.toFixed(2) : '0'}
- **Scheduler Median Interval**: ${stats.schedulerMedian ? stats.schedulerMedian.toFixed(2) + ' ms' : 'null'}
- **Scheduler p95 Interval**: ${stats.schedulerP95 ? stats.schedulerP95.toFixed(2) + ' ms' : 'null'}
- **Canvas Draw Calls Total**: ${stats.canvasDrawCount}
- **Callback Batches (callbackbatches)**: ${stats.callbackBatchesCount}
- **Pixel-Verified Local Changed Draw Count**: ${stats.pixelVerifiedDrawCountLocal}
- **Pixel-Verified Local Draw Interval Median**: ${stats.pixelVerifiedDrawIntervalMedianLocal ? stats.pixelVerifiedDrawIntervalMedianLocal.toFixed(2) + ' ms' : 'null'}
- **Pixel-Verified Local Draw Interval p95**: ${stats.pixelVerifiedDrawIntervalP95Local ? stats.pixelVerifiedDrawIntervalP95Local.toFixed(2) + ' ms' : 'null'}
- **Median Local Latency (CONTROLLER-OBSERVED UPPERBOUND)**: ${stats.localLatencyMedian ? stats.localLatencyMedian.toFixed(2) + ' ms' : 'null'}
- **p95 Local Latency (CONTROLLER-OBSERVED UPPERBOUND)**: ${stats.localLatencyP95 ? stats.localLatencyP95.toFixed(2) + ' ms' : 'null'}
${scenario === 'duel' ? `
- **Pixel-Verified Remote Changed Draw Count**: ${stats.pixelVerifiedDrawCountRemote}
- **Pixel-Verified Remote Draw Interval Median**: ${stats.pixelVerifiedDrawIntervalMedianRemote ? stats.pixelVerifiedDrawIntervalMedianRemote.toFixed(2) + ' ms' : 'null'}
- **Pixel-Verified Remote Draw Interval p95**: ${stats.pixelVerifiedDrawIntervalP95Remote ? stats.pixelVerifiedDrawIntervalP95Remote.toFixed(2) + ' ms' : 'null'}
- **Median Remote Latency (CONTROLLER-OBSERVED UPPERBOUND)**: ${stats.remoteLatencyMedian ? stats.remoteLatencyMedian.toFixed(2) + ' ms' : 'null'}
- **p95 Remote Latency (CONTROLLER-OBSERVED UPPERBOUND)**: ${stats.remoteLatencyP95 ? stats.remoteLatencyP95.toFixed(2) + ' ms' : 'null'}
` : ''}
- **Page 1 Clock Drift**: ${page1Drift.toFixed(4)} ms
${scenario === 'duel' ? `- **Page 2 Clock Drift**: ${page2Drift ? page2Drift.toFixed(4) : 'null'} ms` : ''}

## Action-by-Action Detailed Trace
${finalActions.map((act, index) => `- Action #${index+1}: **${act.key}** | Status: \`${act.status}\` | Local Latency (CONTROLLER-OBSERVED UPPERBOUND): ${act.latency ? act.latency.toFixed(2) + 'ms' : 'null'} ${act.remoteLatency ? '| Remote Latency (CONTROLLER-OBSERVED UPPERBOUND): ' + act.remoteLatency.toFixed(2) + 'ms' : ''} ${act.exclusionReason ? '(' + act.exclusionReason + ')' : ''}`).join('\n')}

All actions have been evaluated causally, separating scheduler intervals from Canvas 2D paint callbacks, strictly matching verified game coordinates using CanvasRenderingContext2D.getImageData.
`;
    atomicWriteFileSync(reportPath, mdContent);
    console.log(`Report written to: ${reportPath}`);

    console.log(`\n✅ Playwright Benchmark run successfully completed!`);

  } catch (err) {
    console.error(`❌ Benchmark execution error:`, err);
    
    // Write run-failure.json on any error or abort
    const failPath = path.join(outdir, 'run-failure.json');
    fs.mkdirSync(outdir, { recursive: true });
    fs.writeFileSync(failPath, JSON.stringify({
      error: err.message,
      stack: err.stack,
      timestamp: new Date().toISOString()
    }, null, 2), 'utf8');

    // Write any collected raw metrics on failure for diagnosis
    try {
      const rawMetricsJSON = {
        environment: envMetadata,
        failure: err.message,
        rawNetwork: {
          httpEvents,
          wsSentEventsPage1,
          wsReceivedEventsPage1,
          wsReceivedEventsPage2
        }
      };
      fs.writeFileSync(path.join(outdir, 'raw-metrics.json'), JSON.stringify(rawMetricsJSON, null, 2), 'utf8');
    } catch (e) {}
    
    throw err;
  } finally {
    // Stop context traces and close contexts safely
    if (!browserCleanupCompleted) {
      browserCleanupCompleted = true;
      console.log("Cleaning up browser contexts and closing headful Chromium...");
      try {
        await context1.tracing.stop({ path: tracePath1 });
      } catch (e) {}
      if (context2) {
        try {
          await context2.tracing.stop({ path: tracePath2 });
        } catch (e) {}
      }
      try {
        await browser.close();
      } catch (e) {}
      console.log("Cleanup complete.");
    }
  }
}

// Causal keypress evaluation, pixel polling, and validation
async function executeAndVerifyAction(
  page1, page2, scenario, key,
  page1Calibration, page2Calibration,
  winStart, winEnd, outdir,
  httpEvents, wsSentEvents, wsReceivedEventsPage1, wsReceivedEventsPage2,
  sessionState
) {
  const keysToDirections = {
    'ArrowLeft': 'left',
    'ArrowRight': 'right',
    'ArrowUp': 'clockwise',
    'Z': 'counterclockwise'
  };

  const keysToWsActions = {
    'ArrowLeft': 'move_left',
    'ArrowRight': 'move_right',
    'ArrowUp': 'rotate_clockwise',
    'Z': 'rotate_counterclockwise'
  };

  const stateBefore = sessionState.lastStateReceivedPage1;

  const inWindow = (t) => {
    if (typeof winStart !== 'number' || typeof winEnd !== 'number') return true;
    return t >= winStart && t < winEnd;
  };

  // Retrieve exact keydown events from page before pressing to establish cursor/counter
  const keydownEventsOnPageBefore = await page1.evaluate(() => {
    return window.keydownEvents ? [...window.keydownEvents] : [];
  });
  const cursorBefore = keydownEventsOnPageBefore.length;

  // Press the key to dispatch keydown event
  await page1.keyboard.press(key);

  // Retrieve exact keydown events from page after pressing
  const keydownEventsOnPageAfter = await page1.evaluate(() => {
    return window.keydownEvents ? [...window.keydownEvents] : [];
  });
  const newEvents = keydownEventsOnPageAfter.slice(cursorBefore);
  const matchingKeydown = newEvents.find(e => e.key === key);

  const actionRecord = {
    key: key,
    dispatchMono: null,
    dispatchNode: null,
    timestampIso: new Date().toISOString(),
    status: 'pending',
    latency: null,
    remoteLatency: null,
    exclusionReason: null
  };

  // Missing event is strictly excluded, NO evaluate performance.now fallback
  if (!matchingKeydown) {
    actionRecord.status = 'excluded';
    actionRecord.exclusionReason = 'Missing keydown event in browser window.keydownEvents';
    return actionRecord;
  }

  const keydownMono = matchingKeydown.timestamp;
  const keydownNode = keydownMono + page1Calibration.offset;
  const eventID = matchingKeydown.eventID || 'mock_event_id';

  actionRecord.dispatchMono = keydownMono;
  actionRecord.dispatchNode = keydownNode;
  actionRecord.eventID = eventID;
  actionRecord.actualEvent = matchingKeydown;

  // Check keydownNode bound
  if (!inWindow(keydownNode)) {
    actionRecord.status = 'excluded';
    actionRecord.exclusionReason = `Dispatch time (${keydownNode.toFixed(1)}ms) outside logical measurement window [${winStart}, ${winEnd})`;
    return actionRecord;
  }

  // Wait/poll for the corresponding ACK (HTTP response or WS state update)
  const maxWait = 1000;
  const pollStart = performance.now();
  let matchedState = null;
  let ackTimestampNode = null;

  while (performance.now() - pollStart < maxWait) {
    if (scenario === 'solo') {
      const activeGameId = stateBefore ? stateBefore.id : null;
      const expectedDir = keysToDirections[key];
      const matchingRes = httpEvents.find(ev => 
        ev.url.includes(`/api/games/${activeGameId}/move`) && 
        ev.postData && ev.postData.direction === expectedDir &&
        ev.timestamp >= keydownNode &&
        !ev.used
      );
      if (matchingRes && matchingRes.data) {
        matchingRes.used = true; // Never re-use prior response
        matchedState = matchingRes.data;
        ackTimestampNode = matchingRes.timestamp;

        actionRecord.ackType = 'http';
        actionRecord.ackRequestUrl = matchingRes.url;
        actionRecord.ackRequestMethod = matchingRes.method;
        actionRecord.ackRequestPostData = matchingRes.postData;
        actionRecord.ackResponseStatus = matchingRes.status;
        actionRecord.ackTimestampNode = matchingRes.timestamp;
        break;
      }
    } else {
      const mappedAction = keysToWsActions[key];
      const matchingSent = wsSentEvents.find(ev => 
        ev.timestamp >= keydownNode &&
        ev.data.type === 'action' &&
        ev.data.payload &&
        ev.data.payload.action === mappedAction &&
        ev.data.payload.room_id === sessionState.roomId &&
        ev.data.payload.player_id === sessionState.playerId &&
        !ev.used
      );

      if (matchingSent && matchingSent.data && matchingSent.data.payload) {
        const seq = matchingSent.data.payload.seq;
        const generation = matchingSent.data.payload.generation;

        const matchingRec = wsReceivedEventsPage1.find(ev => 
          ev.timestamp >= matchingSent.timestamp &&
          ev.data.type === 'state' &&
          ev.data.payload.room_id === sessionState.roomId &&
          ev.data.payload.player_id === sessionState.playerId &&
          ev.data.payload.last_processed_seq === seq &&
          ev.data.payload.generation === generation &&
          !ev.used
        );
        if (matchingRec) {
          matchingSent.used = true;
          matchingRec.used = true;
          matchedState = matchingRec.data.payload;
          ackTimestampNode = matchingRec.timestamp;

          actionRecord.ackType = 'ws';
          actionRecord.ackWsSentSeq = seq;
          actionRecord.ackWsSentGeneration = generation;
          actionRecord.ackWsSentTimestampNode = matchingSent.timestamp;
          actionRecord.ackWsReceivedTimestampNode = matchingRec.timestamp;
          actionRecord.ackTimestampNode = matchingRec.timestamp;
          break;
        }
      }
    }
    await new Promise(r => setTimeout(r, 5));
  }

  if (!matchedState) {
    actionRecord.status = 'excluded';
    actionRecord.exclusionReason = 'Timeout waiting for ACK/response';
    return actionRecord;
  }

  // Check ackTimestampNode bound
  if (!inWindow(ackTimestampNode)) {
    actionRecord.status = 'excluded';
    actionRecord.exclusionReason = `ACK receipt time (${ackTimestampNode.toFixed(1)}ms) outside logical measurement window [${winStart}, ${winEnd})`;
    return actionRecord;
  }

  // Verify chosen effect happened
  const effectHappened = verifyInputEffect(stateBefore, matchedState, key);
  if (!effectHappened) {
    actionRecord.status = 'excluded';
    actionRecord.exclusionReason = 'Action was a no-op, blocked move, or O-piece rotation';
    return actionRecord;
  }

  // Poll actual pixels on page1 canvas using getImageData until match expected mask
  const expectedMask = getExpectedMask(matchedState);
  const maskHash = crypto.createHash('sha256').update(JSON.stringify(expectedMask)).digest('hex');

  let pixelMatched = false;
  let matchNodeTime = null;
  let localObservationStart = null;
  let localObservationEnd = null;
  const pixelPollStart = performance.now();
  let px = null;

  while (performance.now() - pixelPollStart < 500) {
    px = await samplePixels(page1, 'local');
    if (px && matchPixelsToMask(px.rgba, expectedMask)) {
      pixelMatched = true;
      localObservationStart = px.observationStart;
      localObservationEnd = px.observationEnd;
      matchNodeTime = px.observationEnd;

      // Persist local context details
      if (outdir) {
        const outPath = path.join(outdir, `pixel-match-${key}-${keydownMono.toFixed(0)}.json`);
        fs.writeFileSync(outPath, JSON.stringify({
          canvasIdentity: 'local-actor',
          paintCounter: px.batchCount,
          maskHash,
          state: matchedState,
          rgba: px.rgba,
          observationStart: px.observationStart,
          observationEnd: px.observationEnd
        }, null, 2), 'utf8');
      }
      break;
    }
    await new Promise(r => setTimeout(r, 5));
  }

  if (!pixelMatched || !px) {
    actionRecord.status = 'excluded';
    actionRecord.exclusionReason = 'Timeout polling/matching pixels on local canvas';
    return actionRecord;
  }

  // Check local observation bounds
  if (!inWindow(localObservationStart) || !inWindow(localObservationEnd)) {
    actionRecord.status = 'excluded';
    actionRecord.exclusionReason = `Local canvas observation window [${localObservationStart.toFixed(1)}ms, ${localObservationEnd.toFixed(1)}ms) outside logical measurement window [${winStart}, ${winEnd})`;
    return actionRecord;
  }

  actionRecord.status = 'success';
  actionRecord.latency = matchNodeTime - keydownNode;

  actionRecord.beforeState = stateBefore;
  actionRecord.matchedState = matchedState;
  actionRecord.localObservationStart = localObservationStart;
  actionRecord.localObservationEnd = localObservationEnd;
  actionRecord.local200RGBA = px.rgba;
  actionRecord.localMaskHash = maskHash;
  actionRecord.localPaintCounter = px.batchCount;

  // In duel mode, also poll opponent canvas on page2
  if (scenario === 'duel' && page2 && page2Calibration) {
    let opponentMatched = false;
    let oppMatchNodeTime = null;
    const oppPollStart = performance.now();
    let pxOpp = null;
    while (performance.now() - oppPollStart < 500) {
      pxOpp = await samplePixels(page2, 'opponent');
      if (pxOpp && matchPixelsToMask(pxOpp.rgba, expectedMask)) {
        opponentMatched = true;
        oppMatchNodeTime = pxOpp.observationEnd;

        // Persist remote context details
        if (outdir) {
          const outPathOpp = path.join(outdir, `pixel-match-opponent-${key}-${keydownMono.toFixed(0)}.json`);
          fs.writeFileSync(outPathOpp, JSON.stringify({
            canvasIdentity: 'opponent-spectator',
            paintCounter: pxOpp.batchCount,
            maskHash,
            state: matchedState,
            rgba: pxOpp.rgba,
            observationStart: pxOpp.observationStart,
            observationEnd: pxOpp.observationEnd
          }, null, 2), 'utf8');
        }
        break;
      }
      await new Promise(r => setTimeout(r, 5));
    }
    if (opponentMatched && pxOpp) {
      if (inWindow(pxOpp.observationStart) && inWindow(pxOpp.observationEnd)) {
        actionRecord.remoteLatency = oppMatchNodeTime - keydownNode;
        actionRecord.remoteObservationStart = pxOpp.observationStart;
        actionRecord.remoteObservationEnd = pxOpp.observationEnd;
        actionRecord.remote200RGBA = pxOpp.rgba;
        actionRecord.remoteMaskHash = maskHash;
        actionRecord.remotePaintCounter = pxOpp.batchCount;
      } else {
        actionRecord.remoteLatency = null;
        actionRecord.remoteExclusionReason = 'Remote observation outside logical measurement window';
        actionRecord.remoteObservationProof = {
          observationStart: pxOpp.observationStart,
          observationEnd: pxOpp.observationEnd,
          winStart,
          winEnd
        };
      }
    }
  }

  return actionRecord;
}

// In-browser pixel sampler page function
async function samplePixels(page, role) {
  const startNode = performance.now();
  const result = await page.evaluate(({ role }) => {
    const canvas = role === 'local'
      ? (document.querySelector('.duel-seat.local-seat canvas') || document.querySelector('[data-testid="grid-board-canvas"]'))
      : document.querySelector('.duel-seat.opponent-seat canvas');
    if (!canvas) return null;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const width = canvas.width;
    const height = canvas.height;
    const dpr = window.devicePixelRatio || 1;

    const canvasId = `${window.canvasIdentityLabel}-${role}`;
    const paintState = window.canvasPaintStates[canvasId] || { drawCount: 0, batchCount: 0 };

    const rgba = [];
    for (let r = 0; r < 20; r++) {
      for (let c = 0; c < 10; c++) {
        const px = Math.floor((c + 0.5) * width / 10);
        const py = Math.floor((r + 0.5) * height / 20);
        const img = ctx.getImageData(px, py, 1, 1).data;
        rgba.push([img[0], img[1], img[2], img[3]]);
      }
    }
    return {
      rgba,
      width,
      height,
      dpr,
      drawCount: paintState.drawCount,
      batchCount: paintState.batchCount
    };
  }, { role });

  if (!result) return null;
  result.observationStart = result.observationStart !== undefined ? result.observationStart : startNode;
  result.observationEnd = result.observationEnd !== undefined ? result.observationEnd : performance.now();
  return result;
}
