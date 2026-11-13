import { chromium, expect, Browser, BrowserContext, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// Precise monotonic clock using Node's performance.now
const driverNow = () => performance.now();

// Euclidean distance classifier for Canvas2D color sampling
const CANONICAL_COLORS = [
  [19, 19, 23],      // 0: Empty (Background #0c0c10 with 3% white overlay)
  [0, 240, 240],     // 1: I (Cyan)
  [240, 240, 0],     // 2: O (Yellow)
  [160, 0, 240],     // 3: T (Purple)
  [0, 240, 0],       // 4: S (Green)
  [240, 0, 0],       // 5: Z (Red)
  [0, 0, 240],       // 6: J (Blue)
  [240, 160, 0]      // 7: L (Orange)
];

// JS string injected in the page to monitor Canvas pixels & attributes
const CANVAS_INSPECTOR_FN = `
  (selector, expectedBoard, expectedActivePiece) => {
    const canvas = document.querySelector(selector);
    if (!canvas) return { success: false, reason: 'Canvas not found' };

    const board = expectedBoard;
    const activePiece = expectedActivePiece;
    
    if (!board) return { success: false, reason: 'No expected board state provided' };
    
    // Construct expected grid
    const expected = board.map(row => [...row]);
    if (activePiece) {
      const { type, cells } = activePiece;
      const colorMap = { I: 1, O: 2, T: 3, S: 4, Z: 5, J: 6, L: 7 };
      const val = colorMap[type] || 0;
      cells.forEach(([r, c]) => {
        if (r >= 0 && r < 20 && c >= 0 && c < 10) {
          expected[r][c] = val;
        }
      });
    }
    
    const W = canvas.width;
    const H = canvas.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return { success: false, reason: 'No 2d context' };
    
    const imgData = ctx.getImageData(0, 0, W, H);
    const cellWidth = W / 10;
    const cellHeight = H / 20;
    
    const canonicalColors = ${JSON.stringify(CANONICAL_COLORS)};
    const MAX_TOLERANCE = 35.0; // Bounded distance tolerance to classify canvas colors

    function getCellIndex(r, g, b) {
      let minDistance = Infinity;
      let bestIndex = -1;
      for (let i = 0; i < canonicalColors.length; i++) {
        const [cr, cg, cb] = canonicalColors[i];
        const dist = Math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2);
        if (dist < minDistance) {
          minDistance = dist;
          bestIndex = i;
        }
      }
      if (minDistance > MAX_TOLERANCE) {
        return { value: -1, distance: minDistance, reason: 'Color too far from canonical: RGB(' + r + ',' + g + ',' + b + '), min distance: ' + minDistance.toFixed(1) };
      }
      return { value: bestIndex, distance: minDistance };
    }
    
    const observed = Array.from({ length: 20 }, () => Array(10).fill(0));
    const rawRGB = Array.from({ length: 20 }, () => Array(10).fill(null));
    const mismatchList = [];
    
    for (let r = 0; r < 20; r++) {
      for (let c = 0; c < 10; c++) {
        const cx = Math.floor((c + 0.5) * cellWidth);
        const cy = Math.floor((r + 0.5) * cellHeight);
        const idx = (cy * W + cx) * 4;
        const pr = imgData.data[idx];
        const pg = imgData.data[idx+1];
        const pb = imgData.data[idx+2];
        
        rawRGB[r][c] = [pr, pg, pb];
        const cellRes = getCellIndex(pr, pg, pb);
        observed[r][c] = cellRes.value;
        
        if (cellRes.value !== expected[r][c]) {
          if (cellRes.value === -1) {
            mismatchList.push('Cell(' + r + ',' + c + ') expected ' + expected[r][c] + ', got color mismatch: ' + cellRes.reason);
          } else {
            mismatchList.push('Cell(' + r + ',' + c + ') expected ' + expected[r][c] + ', got ' + cellRes.value + ' (RGB: ' + pr + ',' + pg + ',' + pb + ', dist: ' + cellRes.distance.toFixed(1) + ')');
          }
        }
      }
    }
    
    return {
      success: mismatchList.length === 0,
      readTimestamp: performance.now(),
      board,
      activePiece,
      observed,
      rawRGB,
      mismatchDetails: mismatchList.length > 0 ? mismatchList : null
    };
  }
`;

// Helper to inject instrument trackers into the page using explicitly invoked IIFE
async function injectInstrumentTrackers(page: Page) {
  await page.evaluate(`(() => {
    // 1. requestAnimationFrame Scheduling Tracker (storing [prev, curr, delta] samples)
    window.__rafSamples = [];
    window.__rafActive = true;
    let lastRafTime = performance.now();
    function loop() {
      const now = performance.now();
      if (window.__rafActive) {
        window.__rafSamples.push([lastRafTime, now, now - lastRafTime]);
      }
      lastRafTime = now;
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);

    // 2. Canvas2D Candidate Draw Tracker (storing timestamp & args)
    window.__drawEvents = [];
    const originalFillRect = CanvasRenderingContext2D.prototype.fillRect;
    CanvasRenderingContext2D.prototype.fillRect = function(...args) {
      const now = performance.now();
      window.__drawEvents.push({
        timestamp: now,
        method: 'fillRect',
        args: args
      });
      return originalFillRect.apply(this, args);
    };

    // 3. Visibility and Focus Tracker
    window.__visibilityEvents = [];
    window.addEventListener('focus', () => {
      window.__visibilityEvents.push({ type: 'focus', timestamp: performance.now() });
    });
    window.addEventListener('blur', () => {
      window.__visibilityEvents.push({ type: 'blur', timestamp: performance.now() });
    });
    document.addEventListener('visibilitychange', () => {
      window.__visibilityEvents.push({ type: 'visibility', state: document.visibilityState, timestamp: performance.now() });
    });
  })()`);

  // Assert trackers exist and rAF/draw samples are produced before claiming readiness
  let ready = false;
  for (let i = 0; i < 20; i++) {
    ready = await page.evaluate(() => {
      return Array.isArray(window.__rafSamples) && window.__rafSamples.length > 0;
    }).catch(() => false);
    if (ready) break;
    await page.waitForTimeout(100);
  }
  if (!ready) {
    throw new Error('Instrument tracker assertion failed: rAF samples were not produced.');
  }
}

interface ClockCalibration {
  offset: number; // t_page - t_driver
  uncertainty: number; // RTT / 2
  probes: any[];
}

// Clock calibration to bridge page local monotonic clock to driver time
async function calibrateClock(page: Page): Promise<ClockCalibration> {
  let bestRtt = Infinity;
  let bestOffset = 0;
  let bestUncertainty = 0;
  const probes: any[] = [];
  
  for (let i = 0; i < 5; i++) {
    const t_before = driverNow();
    const t_page = await page.evaluate(() => performance.now());
    const t_after = driverNow();
    const rtt = t_after - t_before;
    const offset = t_page - (t_before + t_after) / 2;
    const uncertainty = rtt / 2;
    
    probes.push({ t_before, t_page, t_after, rtt, offset, uncertainty });
    
    if (rtt < bestRtt) {
      bestRtt = rtt;
      bestOffset = offset;
      bestUncertainty = uncertainty;
    }
  }
  
  return {
    offset: bestOffset,
    uncertainty: bestUncertainty,
    probes
  };
}

// Parse args
function parseArgs() {
  const args = process.argv;
  let baseUrl = 'http://127.0.0.1:5513';
  let outputDir = 'benchmark-output';
  let runs = 3;
  let warmupSeconds = 5;
  let measureSeconds = 30;
  let isSmoke = false;
  let isHeadless = false;
  let channel = 'chrome';
  let foregroundGate = false;
  let foregroundGateTimeoutSeconds = 120;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--base-url' && i + 1 < args.length) baseUrl = args[i + 1];
    if (args[i] === '--output' && i + 1 < args.length) outputDir = args[i + 1];
    if (args[i] === '--runs' && i + 1 < args.length) runs = parseInt(args[i + 1], 10);
    if (args[i] === '--warmup-seconds' && i + 1 < args.length) warmupSeconds = parseInt(args[i + 1], 10);
    if (args[i] === '--measure-seconds' && i + 1 < args.length) measureSeconds = parseInt(args[i + 1], 10);
    if (args[i] === '--smoke') isSmoke = true;
    if (args[i] === '--headless') isHeadless = true;
    if (args[i] === '--channel' && i + 1 < args.length) channel = args[i + 1];
    if (args[i] === '--foreground-gate') foregroundGate = true;
    if (args[i] === '--foreground-gate-timeout-seconds' && i + 1 < args.length) {
      foregroundGateTimeoutSeconds = parseInt(args[i + 1], 10);
    }
  }

  if (isSmoke) {
    console.log('--- SMOKE RUN SPECIFIED ---');
    runs = 1;
    warmupSeconds = 2;
    measureSeconds = 3;
    isHeadless = true;
  }

  return { baseUrl, outputDir, runs, warmupSeconds, measureSeconds, isSmoke, isHeadless, channel, foregroundGate, foregroundGateTimeoutSeconds };
}

interface Distribution {
  median: number | null;
  p95: number | null;
  p99: number | null;
  mean: number | null;
}

function computePercentiles(arr: number[]): Distribution {
  if (arr.length === 0) return { median: null, p95: null, p99: null, mean: null };
  const sorted = [...arr].sort((a, b) => a - b);
  const sum = sorted.reduce((acc, v) => acc + v, 0);
  const mean = sum / sorted.length;

  const getP = (p: number) => {
    const idx = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[Math.max(0, idx)];
  };

  return {
    median: getP(50),
    p95: getP(95),
    p99: getP(99),
    mean
  };
}

async function safeLaunch(
  options: any,
  runId: string,
  type: 'solo' | 'duel',
  requestedSettings: { warmupSeconds: number; measureSeconds: number; channel: string; isHeadless: boolean },
  outputDir: string,
  runsReport: any[]
): Promise<Browser> {
  try {
    return await chromium.launch(options);
  } catch (err: any) {
    const runDir = path.join(outputDir, runId);
    fs.mkdirSync(runDir, { recursive: true });

    const errorMsg = err.message || err.toString();
    const runReport: any = {
      runId,
      type,
      success: false,
      error: errorMsg,
      errorStage: 'browser-launch',
      requestedWarmupSeconds: requestedSettings.warmupSeconds,
      requestedMeasureSeconds: requestedSettings.measureSeconds,
      channel: requestedSettings.channel,
      isHeadless: requestedSettings.isHeadless,
      browserName: 'chromium',
      browserVersion: 'unknown',
      launchArgs: options.args || [],
      viewport: '1280x900',
      dpr: 1,
      actions: []
    };

    if (type === 'solo') {
      runReport.successfulActions = 0;
      runReport.oRotationNoops = 0;
      runReport.blockedNoops = 0;
      runReport.unresolvedActions = 0;
      runReport.actionLatencyMs = { median: null, p95: null, p99: null, mean: null };
      runReport.frameSchedulingIntervalMs = { median: null, p95: null, p99: null, mean: null };
      runReport.drawCandidateIntervalMs = { median: null, p95: null, p99: null, mean: null };
      runReport.observedMeanFPS = null;
      runReport.rAFCount = 0;
      runReport.drawCount = 0;
      runReport.calibrationLimits = null;
      runReport.visibilityEventHistory = [];
      runReport.rawTelemetry = {
        rafSamples: [],
        drawEvents: [],
        visibilityEvents: [],
        httpLogs: []
      };
      runReport.excludedRaf = [];
      runReport.excludedNonpositiveRafCount = 0;
      runReport.excludedNonpositiveRafInWindowCount = 0;
      runReport.excludedDrawEvents = [];
      runReport.excludedActions = [];
    } else {
      runReport.successfulLocalActions = 0;
      runReport.successfulRemoteActions = 0;
      runReport.localActionLatencyMs = { median: null, p95: null, p99: null, mean: null };
      runReport.remoteActionLatencyMs = { median: null, p95: null, p99: null, mean: null };
      runReport.frameSchedulingIntervalMs_ClientA = { median: null, p95: null, p99: null, mean: null };
      runReport.frameSchedulingIntervalMs_ClientB = { median: null, p95: null, p99: null, mean: null };
      runReport.drawCandidateIntervalMs_ClientA = { median: null, p95: null, p99: null, mean: null };
      runReport.drawCandidateIntervalMs_ClientB = { median: null, p95: null, p99: null, mean: null };
      runReport.observedMeanFPS_ClientA = null;
      runReport.observedMeanFPS_ClientB = null;
      runReport.rAFCount_ClientA = 0;
      runReport.rAFCount_ClientB = 0;
      runReport.drawCount_ClientA = 0;
      runReport.drawCount_ClientB = 0;
      runReport.calibrationLimitsA = null;
      runReport.calibrationLimitsB = null;
      runReport.visibilityEventsA = [];
      runReport.visibilityEventsB = [];
      runReport.rawTelemetry = {
        rafSamplesA: [],
        rafSamplesB: [],
        drawEventsA: [],
        drawEventsB: [],
        visibilityEventsA: [],
        visibilityEventsB: [],
        wsLogsA: [],
        wsLogsB: []
      };
      runReport.excludedRafA = [];
      runReport.excludedRafB = [];
      runReport.excludedNonpositiveRafCount_ClientA = 0;
      runReport.excludedNonpositiveRafInWindowCount_ClientA = 0;
      runReport.excludedNonpositiveRafCount_ClientB = 0;
      runReport.excludedNonpositiveRafInWindowCount_ClientB = 0;
      runReport.excludedDrawEventsA = [];
      runReport.excludedDrawEventsB = [];
      runReport.excludedActions = [];
    }

    fs.writeFileSync(path.join(runDir, `${runId}_partial.json`), JSON.stringify(runReport, null, 2));
    runsReport.push(runReport);

    throw err;
  }
}

async function runForegroundGate(
  actorPage: Page,
  receiverPage: Page | null,
  runId: string,
  scenario: string,
  runDir: string,
  options: {
    foregroundGate: boolean;
    foregroundGateTimeoutSeconds: number;
    runsPerScenario: number;
    channel: string;
    isHeadless: boolean;
  },
  runReport: any
): Promise<void> {
  runReport.foregroundGateEnabled = options.foregroundGate;
  runReport.foregroundGateTimeoutSeconds = options.foregroundGateTimeoutSeconds;
  runReport.foregroundGateApproved = false;
  runReport.foregroundGateWaitStart = null;
  runReport.foregroundGateWaitEnd = null;

  if (!options.foregroundGate) {
    runReport.foregroundOSVerified = false;
    console.log(`[${runId}] Foreground gate disabled. OS-foreground-unverified.`);
    return;
  }

  const outputDirBasename = path.basename(path.dirname(runDir));
  const actorTitle = `SDD S4 ${outputDirBasename} ${runId} INPUT`;
  const receiverTitle = receiverPage ? `SDD S4 ${outputDirBasename} ${runId} RECEIVER` : null;

  // Set the document title on the pages using self-contained evaluation
  await actorPage.evaluate((title) => { document.title = title; }, actorTitle);
  if (receiverPage && receiverTitle) {
    await receiverPage.evaluate((title) => { document.title = title; }, receiverTitle);
  }

  // Define file paths
  const readyPath = path.join(runDir, 'foreground-ready.json');
  const approvedPath = path.join(runDir, 'foreground-approved.json');

  const readyData = {
    runId,
    scenario,
    actorTitle,
    receiverTitle,
    runsPerScenario: options.runsPerScenario,
    createdUTC: new Date().toISOString(),
    requestedChannel: options.channel,
    requestedMode: options.isHeadless ? 'headless' : 'headed',
    phase: 'before-game-setup'
  };

  fs.writeFileSync(readyPath, JSON.stringify(readyData, null, 2));
  console.log(`[${runId}] Wrote foreground-ready.json to ${readyPath}. Temporary titles set.`);
  console.log(`[${runId}] Waiting for approved file at ${approvedPath}...`);

  const startTime = Date.now();
  runReport.foregroundGateWaitStart = new Date().toISOString();
  
  const timeoutMs = options.foregroundGateTimeoutSeconds * 1000;
  let approved = false;
  let approvalRecord: any = null;

  while (Date.now() - startTime < timeoutMs) {
    if (fs.existsSync(approvedPath)) {
      try {
        const fileContent = fs.readFileSync(approvedPath, 'utf8');
        const data = JSON.parse(fileContent);
        if (data.approved === true && data.runId === runId && data.actorTitle === actorTitle) {
          approved = true;
          approvalRecord = data;
          break;
        }
      } catch (e) {
        // Parse error or invalid schema, continue polling
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  runReport.foregroundGateWaitEnd = new Date().toISOString();

  if (!approved) {
    runReport.errorStage = 'foreground-gate';
    const errorMsg = `Foreground gate timeout or invalid approval after ${options.foregroundGateTimeoutSeconds}s.`;
    runReport.error = errorMsg;
    console.error(`[${runId}] ERROR: ${errorMsg}`);
    throw new Error(errorMsg);
  }

  runReport.foregroundGateApproved = true;
  runReport.foregroundOSVerified = true;
  runReport.foregroundGateApprovalRecord = approvalRecord;
  console.log(`[${runId}] Foreground gate approved! Matching runId and actorTitle verified.`);
}

async function main() {
  const { baseUrl, outputDir, runs, warmupSeconds, measureSeconds, isSmoke, isHeadless, channel, foregroundGate, foregroundGateTimeoutSeconds } = parseArgs();

  console.log(`Verifying target output directory '${outputDir}'...`);
  if (fs.existsSync(outputDir)) {
    console.error(`Error: Output directory '${outputDir}' already exists. Failing to prevent overwrite.`);
    process.exit(1);
  }

  fs.mkdirSync(outputDir, { recursive: true });

  const envDetails = {
    os: `${os.platform()} ${os.release()} (${os.arch()})`,
    cpu: os.cpus()[0]?.model || 'Unknown CPU',
    memory: `${(os.totalmem() / (1024 ** 3)).toFixed(2)} GB`,
    runtime: `Node.js ${process.version}`,
    timestamp: new Date().toISOString(),
    viewport: '1280x900',
    dpr: 1
  };

  console.log('================================================================');
  console.log('TETRIS STAGE 4 OPTION A: MONOTONIC INSTRUMENT BENCHMARK');
  console.log('================================================================');
  console.log(`Base URL: ${baseUrl}`);
  console.log(`Output: ${outputDir}`);
  console.log(`Runs: ${runs}, Warmup: ${warmupSeconds}s, Active: ${measureSeconds}s`);
  console.log(`Platform: ${envDetails.os}`);
  console.log(`Mode: ${isHeadless ? 'HEADLESS' : 'HEADED'}`);
  console.log('================================================================\n');

  const runsReport: any[] = [];
  let executionFailed = false;

  try {
    // ==========================================================================
    // SCENARIO 1: SOLO PLAY
    // ==========================================================================
    for (let run = 1; run <= runs; run++) {
      const runId = `solo_run_${run}`;
      const runDir = path.join(outputDir, runId);
      fs.mkdirSync(runDir, { recursive: true });

      console.log(`\n>>> Starting ${runId}...`);

      const browser = await safeLaunch(
        {
          headless: isHeadless,
          channel: channel,
          args: isHeadless ? [] : ['--window-size=1280,900', '--window-position=0,0']
        },
        runId,
        'solo',
        { warmupSeconds, measureSeconds, channel, isHeadless },
        outputDir,
        runsReport
      );
      const context = await browser.newContext({
        viewport: { width: 1280, height: 900 },
        deviceScaleFactor: 1
      });

      await context.tracing.start({ screenshots: true, snapshots: true });
      const page = await context.newPage();

      // Declare scoping outside the main try block
      let measureStartNode = 0;
      let measureEndNode = 0;
      const actionsTaken: any[] = [];
      let calibBefore: ClockCalibration | null = null;
      let calibAfter: ClockCalibration | null = null;
      let drift = 0;

      // Initialize persistent runReport outside the main action loop to prevent loss on failures
      const runReport: any = {
        runId,
        type: 'solo',
        success: false,
        error: null,
        errorStage: 'setup',
        requestedWarmupSeconds: warmupSeconds,
        requestedMeasureSeconds: measureSeconds,
        measureStartNode: null,
        measureEndNode: null,
        totalActions: 0,
        successfulActions: 0,
        oRotationNoops: 0,
        blockedNoops: 0,
        unresolvedActions: 0,
        actionLatencyMs: { median: null, p95: null, p99: null, mean: null },
        frameSchedulingIntervalMs: { median: null, p95: null, p99: null, mean: null },
        drawCandidateIntervalMs: { median: null, p95: null, p99: null, mean: null },
        observedMeanFPS: null,
        rAFCount: 0,
        drawCount: 0,
        calibrationLimits: null,
        visibilityEventHistory: [],
        browserName: browser.browserType().name(),
        browserVersion: browser.version(),
        channel: channel,
        browserMode: isHeadless ? 'headless' : 'headed',
        launchOptions: {
          headless: isHeadless,
          channel: channel,
          args: isHeadless ? [] : ['--window-size=1280,900', '--window-position=0,0']
        },
        launchArgs: isHeadless ? [] : ['--window-size=1280,900', '--window-position=0,0'],
        viewport: envDetails.viewport,
        dpr: envDetails.dpr,
        actions: [],
        rawTelemetry: {
          rafSamples: [],
          drawEvents: [],
          visibilityEvents: [],
          httpLogs: []
        },
        excludedRaf: [],
        excludedNonpositiveRafCount: 0,
        excludedNonpositiveRafInWindowCount: 0,
        excludedDrawEvents: [],
        excludedActions: []
      };

      const httpLogs: any[] = [];

      try {
        // Set up driver-side HTTP log observer
        page.on('response', async res => {
          const req = res.request();
          const url = req.url();
          const method = req.method();
          if (url.includes('/api/games/')) {
            let reqBody = null;
            if (req.postData()) {
              try { reqBody = JSON.parse(req.postData()); } catch(e) {}
            }
            let resBody = null;
            try {
              resBody = await res.json();
            } catch(e) {}
            httpLogs.push({
              url,
              method,
              reqBody,
              resBody,
              responseTime: driverNow()
            });
          }
        });

        await page.goto(baseUrl);
        await page.waitForLoadState('networkidle');

        // Inject trackers & assert readiness
        runReport.errorStage = 'tracker_injection';
        await injectInstrumentTrackers(page);

        // Run Foreground activation gate
        await runForegroundGate(page, null, runId, 'solo', runDir, {
          foregroundGate,
          foregroundGateTimeoutSeconds,
          runsPerScenario: runs,
          channel,
          isHeadless
        }, runReport);

        // Start New Game
        await page.click('text="Start New Game"');
        await page.waitForTimeout(500);

        // Warmup period
        runReport.errorStage = 'warmup';
        console.log(`[${runId}] Warming up...`);
        const warmupEnd = Date.now() + warmupSeconds * 1000;
        while (Date.now() < warmupEnd) {
          await page.keyboard.press('ArrowLeft');
          await page.waitForTimeout(200);
        }

        // Clean trackers after warmup
        await page.evaluate(() => {
          window.__rafSamples = [];
          window.__drawEvents = [];
          window.__visibilityEvents = [];
        });

        // Perform initial clock calibration
        calibBefore = await calibrateClock(page);
        console.log(`[${runId}] Calibrated offset: ${calibBefore.offset.toFixed(2)} ms, Uncertainty: ${calibBefore.uncertainty.toFixed(2)} ms`);
        runReport.calibrationLimits = { before: calibBefore, after: null, driftMs: 0 };

        const actionPattern = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'Z', 'ArrowDown'];
        let actionIdx = 0;

        console.log(`[${runId}] Measuring...`);
        runReport.errorStage = 'measurement';
        measureStartNode = driverNow();
        measureEndNode = measureStartNode + measureSeconds * 1000;

        runReport.measureStartNode = measureStartNode;
        runReport.measureEndNode = measureEndNode;

        // Keep track of the last known state
        let lastKnownState = await page.evaluate(() => {
          const canvas = document.querySelector('canvas.board-canvas');
          if (!canvas) return null;
          const boardStr = canvas.getAttribute('data-board-state');
          const activeStr = canvas.getAttribute('data-active-piece');
          return {
            board: boardStr ? JSON.parse(boardStr) : null,
            activePiece: activeStr ? JSON.parse(activeStr) : null
          };
        });

        while (driverNow() < measureEndNode) {
          const key = actionPattern[actionIdx % actionPattern.length];
          actionIdx++;

          // Capture focus & actual layout details before action
          const focusMode = await page.evaluate(() => ({
            focused: document.hasFocus(),
            visibility: document.visibilityState,
            screenX: window.screenX,
            screenY: window.screenY,
            outerWidth: window.outerWidth,
            outerHeight: window.outerHeight,
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio
          }));

          const dispatchTimeNode = driverNow();

          // Refresh/bind before state to the preceding actual mutation response for the same game
          const precedingLogs = httpLogs.filter(log => log.responseTime < dispatchTimeNode && log.resBody);
          if (precedingLogs.length > 0) {
            const lastLog = precedingLogs[precedingLogs.length - 1];
            if (lastLog.resBody.board) {
              lastKnownState = {
                board: lastLog.resBody.board,
                activePiece: lastLog.resBody.activePiece
              };
            }
          }

          await page.keyboard.press(key);

          // Map key to expected API action type direction
          let targetDirection = 'left';
          if (key === 'ArrowRight') targetDirection = 'right';
          if (key === 'ArrowDown') targetDirection = 'down';
          if (key === 'ArrowUp') targetDirection = 'cw';
          if (key === 'Z' || key === 'z') targetDirection = 'ccw';

          // Polling loop for matching HTTP response & canvas pixels
          let resolved = false;
          let observedTimeNode: number | null = null;
          let pixelAckTimeNode: number | null = null;
          let pageReadTimestamp: number | null = null;
          let finalState: any = null;
          let reason = 'unresolved';
          let matchedResponse: any = null;

          const pollStartNode = driverNow();
          while (driverNow() - pollStartNode < 250) {
            // Find the matching HTTP response in captured logs
            const found = httpLogs.find(log => 
              log.url.includes('/move') && 
              log.reqBody?.direction === targetDirection && 
              log.responseTime >= dispatchTimeNode
            );

            if (found && found.resBody) {
              matchedResponse = found;
              const authBoard = found.resBody.board;
              const authPiece = found.resBody.activePiece; // Correct shape alias 'activePiece'

              // Check if state changed from last known state
              const isStateChanged = JSON.stringify(authBoard) !== JSON.stringify(lastKnownState?.board) ||
                                     JSON.stringify(authPiece) !== JSON.stringify(lastKnownState?.activePiece);

              if (isStateChanged) {
                // Verify canvas has rendered the new expected state
                const curState = await page.evaluate(`(${CANVAS_INSPECTOR_FN})('canvas.board-canvas', ${JSON.stringify(authBoard)}, ${JSON.stringify(authPiece)})`);
                if (curState && curState.success) {
                  observedTimeNode = driverNow();
                  pixelAckTimeNode = driverNow();
                  pageReadTimestamp = curState.readTimestamp;
                  finalState = curState;
                  resolved = true;
                  lastKnownState = { board: authBoard, activePiece: authPiece };
                  break;
                }
              } else {
                // No change in authoritative state (no-op/blocked)
                resolved = false;
                break;
              }
            }
            await page.waitForTimeout(2);
          }

          const driverAckTimeNode = driverNow();

          // Classify the outcome
          let latency: number | null = null;
          let category = 'changed';

          if (resolved && observedTimeNode !== null) {
            latency = observedTimeNode - dispatchTimeNode;
          } else {
            if (matchedResponse) {
              const authBoard = matchedResponse.resBody.board;
              const authPiece = matchedResponse.resBody.activePiece;
              const isStateChanged = JSON.stringify(authBoard) !== JSON.stringify(lastKnownState?.board) ||
                                     JSON.stringify(authPiece) !== JSON.stringify(lastKnownState?.activePiece);

              if (isStateChanged) {
                category = 'unresolved';
                reason = 'Matched response changed state, but pixel verification failed (instrument mismatch/unresolved observation)';
              } else {
                const pieceType = lastKnownState?.activePiece?.type;
                if (pieceType === 'O' && (key === 'ArrowUp' || key === 'Z')) {
                  category = 'o_rotation_noop';
                  reason = 'O rotation is a strict state-invariant no-op';
                } else {
                  category = 'blocked_noop';
                  reason = 'Movement is blocked by boundary or locked cells';
                }
              }
            } else {
              category = 'unresolved';
              reason = 'Timeout or unmatched response';
            }
          }

          actionsTaken.push({
            action: key,
            category,
            success: resolved,
            latencyMs: latency,
            timestamps: {
              driverDispatch: dispatchTimeNode,
              driverResponseReceipt: matchedResponse ? matchedResponse.responseTime : null,
              driverPixelAck: pixelAckTimeNode,
              pageLocalRead: pageReadTimestamp,
              driverAck: driverAckTimeNode
            },
            focusMode,
            pieceType: lastKnownState?.activePiece?.type || null,
            expectedCells: finalState?.board || null,
            expectedActivePiece: finalState?.activePiece || null,
            observedBoard: finalState?.observed || null,
            observedRGB: finalState?.rawRGB || null,
            reason,
            linkedRequest: matchedResponse ? {
              url: matchedResponse.url,
              method: matchedResponse.method,
              reqBody: matchedResponse.reqBody,
              resBody: matchedResponse.resBody,
              responseTime: matchedResponse.responseTime
            } : null
          });

          await page.waitForTimeout(1000); // 1s causal spacing
        }

        // Post-run Clock Calibration to check drift
        calibAfter = await calibrateClock(page);
        drift = calibAfter.offset - (calibBefore ? calibBefore.offset : 0);
        console.log(`[${runId}] Clock drift during 30s run: ${drift.toFixed(2)} ms`);

        runReport.calibrationLimits.after = calibAfter;
        runReport.calibrationLimits.driftMs = drift;

        runReport.success = true;
        runReport.errorStage = 'complete';

      } catch (err: any) {
        console.error(`[${runId}] Failed:`, err);
        executionFailed = true;
        runReport.success = false;
        runReport.error = err.message || err.toString();
      } finally {
        runReport.rawTelemetry.httpLogs = httpLogs;

        try {
          const finalScreenshotPath = path.join(runDir, 'final_frame.png');
          await page.screenshot({ path: finalScreenshotPath }).catch(() => {});
          await context.tracing.stop({ path: path.join(runDir, 'solo_trace.zip') }).catch(() => {});
        } catch (e) {}

        try {
          const telemetry = await page.evaluate(() => ({
            rafSamples: window.__rafSamples || [],
            drawEvents: window.__drawEvents || [],
            visibilityEvents: window.__visibilityEvents || []
          })).catch(() => null);

          if (telemetry) {
            runReport.rawTelemetry.rafSamples = telemetry.rafSamples;
            runReport.rawTelemetry.drawEvents = telemetry.drawEvents;
            runReport.rawTelemetry.visibilityEvents = telemetry.visibilityEvents;
            runReport.visibilityEventHistory = telemetry.visibilityEvents;

            const calOffset = runReport.calibrationLimits?.before?.offset || 0;

            // Filter requestAnimationFrame samples checking BOTH prev and curr calibrated endpoints lie inside the window and delta is finite & strictly positive
            let excludedNonpositiveRafCount = 0;
            let excludedNonpositiveRafInWindowCount = 0;
            const filteredRaf = [];
            const excludedRaf = [];
            for (const s of telemetry.rafSamples) {
              const t_prev_driver = s[0] - calOffset;
              const t_curr_driver = s[1] - calOffset;
              const inWindow = t_prev_driver >= measureStartNode && t_curr_driver <= measureEndNode;

              const delta = s[2];
              const isPositive = typeof delta === 'number' && isFinite(delta) && delta > 0;

              if (inWindow && isPositive) {
                filteredRaf.push(s);
              } else {
                let rsn = '';
                if (!isPositive) {
                  excludedNonpositiveRafCount++;
                  if (inWindow) {
                    excludedNonpositiveRafInWindowCount++;
                    rsn = 'Nonpositive delta in window';
                  } else {
                    rsn = 'Nonpositive delta out of window';
                  }
                } else {
                  if (t_prev_driver < measureStartNode) rsn = 'Before start window';
                  if (t_curr_driver > measureEndNode) rsn = 'After end window';
                }
                excludedRaf.push({ sample: s, reason: rsn });
              }
            }

            runReport.excludedNonpositiveRafCount = excludedNonpositiveRafCount;
            runReport.excludedNonpositiveRafInWindowCount = excludedNonpositiveRafInWindowCount;
            runReport.excludedRaf = excludedRaf;
            const rafDeltas = filteredRaf.map((s: any) => s[2]);

            // Filter Draw events
            const filteredDrawEvents = [];
            const excludedDrawEvents = [];
            for (const e of telemetry.drawEvents) {
              const t_driver = e.timestamp - calOffset;
              if (t_driver >= measureStartNode && t_driver <= measureEndNode) {
                filteredDrawEvents.push(e);
              } else {
                let rsn = '';
                if (t_driver < measureStartNode) rsn = 'Before start window';
                if (t_driver > measureEndNode) rsn = 'After end window';
                excludedDrawEvents.push({ event: e, reason: rsn });
              }
            }

            runReport.excludedDrawEvents = excludedDrawEvents;

            const drawIntervals: number[] = [];
            for (let i = 1; i < filteredDrawEvents.length; i++) {
              const delta = filteredDrawEvents[i].timestamp - filteredDrawEvents[i-1].timestamp;
              drawIntervals.push(delta);
            }

            // Only use action latency where both dispatch and pixel ACK lie inside the measurement window
            const validLatencies = actionsTaken
              .filter(a => a.category === 'changed' && a.success && a.latencyMs !== null &&
                           a.timestamps.driverDispatch >= measureStartNode &&
                           a.timestamps.driverPixelAck <= measureEndNode)
              .map(a => a.latencyMs as number);

            const excludedActions = actionsTaken.filter(a => !(a.category === 'changed' && a.success && a.latencyMs !== null &&
                           a.timestamps.driverDispatch >= measureStartNode &&
                           a.timestamps.driverPixelAck <= measureEndNode));

            runReport.excludedActions = excludedActions;

            const latencyStats = computePercentiles(validLatencies);
            const frameStats = computePercentiles(rafDeltas);
            const drawStats = computePercentiles(drawIntervals);

            const elapsedSeconds = measureSeconds; // No teardown-based denominators
            const meanFPS = filteredRaf.length / elapsedSeconds;

            runReport.elapsedSeconds = elapsedSeconds;
            runReport.totalActions = actionsTaken.length;
            runReport.successfulActions = actionsTaken.filter(a => a.category === 'changed' && a.success).length;
            runReport.oRotationNoops = actionsTaken.filter(a => a.category === 'o_rotation_noop').length;
            runReport.blockedNoops = actionsTaken.filter(a => a.category === 'blocked_noop').length;
            runReport.unresolvedActions = actionsTaken.filter(a => a.category === 'unresolved').length;
            runReport.actionLatencyMs = latencyStats;
            runReport.frameSchedulingIntervalMs = frameStats;
            runReport.drawCandidateIntervalMs = drawStats;
            runReport.observedMeanFPS = meanFPS;
            runReport.rAFCount = filteredRaf.length;
            runReport.drawCount = filteredDrawEvents.length;
            runReport.actions = actionsTaken;

            console.log(`[${runId}] Telemetry complete.`);
            console.log(`  - Mean Scheduling Rate: ${meanFPS.toFixed(2)} FPS`);
            console.log(`  - rAF Interval p95: ${frameStats.p95 !== null ? frameStats.p95.toFixed(2) : 'N/A'} ms`);
            console.log(`  - Median Action Latency: ${latencyStats.median !== null ? latencyStats.median.toFixed(2) : 'N/A'} ms`);
          }
        } catch (e) {
          console.error('Error extracting telemetry in finally block:', e);
        }

        fs.writeFileSync(path.join(runDir, `${runId}_partial.json`), JSON.stringify(runReport, null, 2));
        runsReport.push(runReport);

        await context.close().catch(() => {});
        await browser.close().catch(() => {});
      }
    }

    // ==========================================================================
    // SCENARIO 2: TWO-PLAYER DUEL
    // ==========================================================================
    for (let run = 1; run <= runs; run++) {
      const runId = `duel_run_${run}`;
      const runDir = path.join(outputDir, runId);
      fs.mkdirSync(runDir, { recursive: true });

      console.log(`\n>>> Starting ${runId}...`);

      const browserA = await safeLaunch(
        {
          headless: isHeadless,
          channel: channel,
          args: isHeadless ? [] : ['--window-size=1280,900', '--window-position=0,0']
        },
        runId,
        'duel',
        { warmupSeconds, measureSeconds, channel, isHeadless },
        outputDir,
        runsReport
      );

      let browserB: Browser;
      try {
        browserB = await safeLaunch(
          {
            headless: isHeadless,
            channel: channel,
            args: isHeadless ? [] : ['--window-size=1280,900', '--window-position=620,0']
          },
          runId,
          'duel',
          { warmupSeconds, measureSeconds, channel, isHeadless },
          outputDir,
          runsReport
        );
      } catch (err) {
        if (browserA) {
          await browserA.close().catch(() => {});
        }
        throw err;
      }

      const contextA = await browserA.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
      const contextB = await browserB.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });

      await contextA.tracing.start({ screenshots: true, snapshots: true });
      await contextB.tracing.start({ screenshots: true, snapshots: true });

      const pageA = await contextA.newPage();
      const pageB = await contextB.newPage();

      // Scoping declarations outside try block
      let measureStartNode = 0;
      let measureEndNode = 0;
      const actionsTaken: any[] = [];
      let calibBeforeA: ClockCalibration | null = null;
      let calibBeforeB: ClockCalibration | null = null;
      let calibAfterA: ClockCalibration | null = null;
      let calibAfterB: ClockCalibration | null = null;

      const runReport: any = {
        runId,
        type: 'duel',
        success: false,
        error: null,
        errorStage: 'setup',
        requestedWarmupSeconds: warmupSeconds,
        requestedMeasureSeconds: measureSeconds,
        measureStartNode: null,
        measureEndNode: null,
        totalActions: 0,
        successfulLocalActions: 0,
        successfulRemoteActions: 0,
        localActionLatencyMs: { median: null, p95: null, p99: null, mean: null },
        remoteActionLatencyMs: { median: null, p95: null, p99: null, mean: null },
        frameSchedulingIntervalMs_ClientA: { median: null, p95: null, p99: null, mean: null },
        frameSchedulingIntervalMs_ClientB: { median: null, p95: null, p99: null, mean: null },
        drawCandidateIntervalMs_ClientA: { median: null, p95: null, p99: null, mean: null },
        drawCandidateIntervalMs_ClientB: { median: null, p95: null, p99: null, mean: null },
        observedMeanFPS_ClientA: null,
        observedMeanFPS_ClientB: null,
        rAFCount_ClientA: 0,
        rAFCount_ClientB: 0,
        drawCount_ClientA: 0,
        drawCount_ClientB: 0,
        calibrationLimitsA: null,
        calibrationLimitsB: null,
        visibilityEventsA: [],
        visibilityEventsB: [],
        browserName: browserA.browserType().name(),
        browserVersion: browserA.version(),
        channel: channel,
        browserMode: isHeadless ? 'headless' : 'headed',
        launchOptionsA: {
          headless: isHeadless,
          channel: channel,
          args: isHeadless ? [] : ['--window-size=1280,900', '--window-position=0,0']
        },
        launchOptionsB: {
          headless: isHeadless,
          channel: channel,
          args: isHeadless ? [] : ['--window-size=1280,900', '--window-position=620,0']
        },
        launchArgs: isHeadless ? [] : ['--window-size=1280,900', '--window-position=0,0'],
        viewport: envDetails.viewport,
        dpr: envDetails.dpr,
        actions: [],
        rawTelemetry: {
          rafSamplesA: [],
          rafSamplesB: [],
          drawEventsA: [],
          drawEventsB: [],
          visibilityEventsA: [],
          visibilityEventsB: [],
          wsLogsA: [],
          wsLogsB: []
        },
        excludedRafA: [],
        excludedRafB: [],
        excludedNonpositiveRafCount_ClientA: 0,
        excludedNonpositiveRafInWindowCount_ClientA: 0,
        excludedNonpositiveRafCount_ClientB: 0,
        excludedNonpositiveRafInWindowCount_ClientB: 0,
        excludedDrawEventsA: [],
        excludedDrawEventsB: [],
        excludedActions: []
      };

      const wsLogsA: any[] = [];
      const wsLogsB: any[] = [];

      try {
        // Set up WS Frame observers on Client A and Client B
        pageA.on('websocket', ws => {
          ws.on('framesent', ({ payload }) => {
            let parsed = null;
            try { parsed = JSON.parse(payload.toString()); } catch(e) {}
            wsLogsA.push({ type: 'send', payload: payload.toString(), parsed, timestamp: driverNow() });
          });
          ws.on('framereceived', ({ payload }) => {
            let parsed = null;
            try { parsed = JSON.parse(payload.toString()); } catch(e) {}
            wsLogsA.push({ type: 'receive', payload: payload.toString(), parsed, timestamp: driverNow() });
          });
        });

        pageB.on('websocket', ws => {
          ws.on('framesent', ({ payload }) => {
            let parsed = null;
            try { parsed = JSON.parse(payload.toString()); } catch(e) {}
            wsLogsB.push({ type: 'send', payload: payload.toString(), parsed, timestamp: driverNow() });
          });
          ws.on('framereceived', ({ payload }) => {
            let parsed = null;
            try { parsed = JSON.parse(payload.toString()); } catch(e) {}
            wsLogsB.push({ type: 'receive', payload: payload.toString(), parsed, timestamp: driverNow() });
          });
        });

        await pageA.goto(baseUrl);
        await pageB.goto(baseUrl);
        await pageA.waitForLoadState('networkidle');
        await pageB.waitForLoadState('networkidle');

        runReport.errorStage = 'tracker_injection';
        await injectInstrumentTrackers(pageA);
        await injectInstrumentTrackers(pageB);

        // Run Foreground activation gate
        await runForegroundGate(pageA, pageB, runId, 'duel', runDir, {
          foregroundGate,
          foregroundGateTimeoutSeconds,
          runsPerScenario: runs,
          channel,
          isHeadless
        }, runReport);

        // Switch to Real-Time Duel
        await pageA.click('text="Real-Time Duel"');
        await pageB.click('text="Real-Time Duel"');

        // Client A creates room
        await pageA.click('text="Create New Duel Room"');
        await pageA.waitForSelector('text="Room ID:"', { timeout: 5000 });
        const roomId = (await pageA.innerText('code')).trim();
        console.log(`[${runId}] Room ID: ${roomId}`);

        // Client B joins
        await pageB.fill('input[placeholder="Enter Room ID"]', roomId);
        await pageB.click('text="Join"');

        // Start Gating transition to ACTIVE status
        await pageA.waitForSelector('text="ACTIVE"', { timeout: 5000 });
        await pageB.waitForSelector('text="ACTIVE"', { timeout: 5000 });

        // Warmup period
        runReport.errorStage = 'warmup';
        console.log(`[${runId}] Warming up...`);
        const warmupEnd = Date.now() + warmupSeconds * 1000;
        while (Date.now() < warmupEnd) {
          await pageA.bringToFront();
          await pageA.keyboard.press('ArrowLeft');
          await pageA.waitForTimeout(200);
        }

        // Clean trackers after warmup
        await pageA.evaluate(() => {
          window.__rafSamples = [];
          window.__drawEvents = [];
          window.__visibilityEvents = [];
        });
        await pageB.evaluate(() => {
          window.__rafSamples = [];
          window.__drawEvents = [];
          window.__visibilityEvents = [];
        });

        // Perform clock calibration
        calibBeforeA = await calibrateClock(pageA);
        calibBeforeB = await calibrateClock(pageB);

        runReport.calibrationLimitsA = { before: calibBeforeA, after: null, driftMs: 0 };
        runReport.calibrationLimitsB = { before: calibBeforeB, after: null, driftMs: 0 };

        const actionPattern = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'Z', 'ArrowDown'];
        let actionIdx = 0;

        console.log(`[${runId}] Measuring...`);
        runReport.errorStage = 'measurement';
        measureStartNode = driverNow();
        measureEndNode = measureStartNode + measureSeconds * 1000;

        runReport.measureStartNode = measureStartNode;
        runReport.measureEndNode = measureEndNode;

        // Maintain current known states for both boards
        let lastAState = await pageA.evaluate(() => {
          const canvas = document.querySelector('.own-board canvas.board-canvas');
          if (!canvas) return null;
          const boardStr = canvas.getAttribute('data-board-state');
          const activeStr = canvas.getAttribute('data-active-piece');
          return { board: boardStr ? JSON.parse(boardStr) : null, activePiece: activeStr ? JSON.parse(activeStr) : null };
        });

        let lastBState = await pageB.evaluate(() => {
          const canvas = document.querySelector('.own-board canvas.board-canvas');
          if (!canvas) return null;
          const boardStr = canvas.getAttribute('data-board-state');
          const activeStr = canvas.getAttribute('data-active-piece');
          return { board: boardStr ? JSON.parse(boardStr) : null, activePiece: activeStr ? JSON.parse(activeStr) : null };
        });

        while (driverNow() < measureEndNode) {
          const key = actionPattern[actionIdx % actionPattern.length];
          actionIdx++;

          // Bring Page A to front before typing
          await pageA.bringToFront();

          // Refresh/bind before-state to the last state update received before dispatch
          const precedingStateA = wsLogsA.filter(log => log.type === 'receive' && log.parsed?.event === 'state_update' && log.timestamp < driverNow());
          if (precedingStateA.length > 0) {
            const lastState = precedingStateA[precedingStateA.length - 1];
            if (lastState.parsed?.payload?.seat_1) {
              lastAState = {
                board: lastState.parsed.payload.seat_1.board,
                activePiece: lastState.parsed.payload.seat_1.active_piece
              };
            }
          }

          const precedingStateB = wsLogsB.filter(log => log.type === 'receive' && log.parsed?.event === 'state_update' && log.timestamp < driverNow());
          if (precedingStateB.length > 0) {
            const lastState = precedingStateB[precedingStateB.length - 1];
            if (lastState.parsed?.payload?.seat_1) {
              lastBState = {
                board: lastState.parsed.payload.seat_1.board,
                activePiece: lastState.parsed.payload.seat_1.active_piece
              };
            }
          }

          const focusA = await pageA.evaluate(() => ({
            focused: document.hasFocus(),
            visibility: document.visibilityState,
            screenX: window.screenX,
            screenY: window.screenY,
            outerWidth: window.outerWidth,
            outerHeight: window.outerHeight,
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio
          }));
          const focusB = await pageB.evaluate(() => ({
            focused: document.hasFocus(),
            visibility: document.visibilityState,
            screenX: window.screenX,
            screenY: window.screenY,
            outerWidth: window.outerWidth,
            outerHeight: window.outerHeight,
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio
          }));

          const dispatchTimeNode = driverNow();
          await pageA.keyboard.press(key);

          // Map key to expected WS action type
          let targetActionType = 'left';
          if (key === 'ArrowRight') targetActionType = 'right';
          if (key === 'ArrowDown') targetActionType = 'down';
          if (key === 'ArrowUp') targetActionType = 'cw';
          if (key === 'Z' || key === 'z') targetActionType = 'ccw';

          // Poll for matching WS action message sent and corresponding state update frame received
          let resolvedLocal = false;
          let resolvedRemote = false;
          
          let localObservedNode: number | null = null;
          let remoteObservedNode: number | null = null;
          let localPixelAckNode: number | null = null;
          let remotePixelAckNode: number | null = null;

          let localReadTimestamp: number | null = null;
          let remoteReadTimestamp: number | null = null;

          let finalA: any = null;
          let finalB: any = null;
          let reason = 'unresolved';
          let category = 'changed';

          let actionSent: any = null;
          let stateUpdateA: any = null;
          let stateUpdateB: any = null;

          const pollStartNode = driverNow();
          while (driverNow() - pollStartNode < 250) {
            // Find action sent on Page A's WS connection
            actionSent = wsLogsA.find(log => 
              log.type === 'send' && 
              log.parsed?.event === 'action' && 
              log.parsed?.payload?.action_type === targetActionType &&
              log.timestamp >= dispatchTimeNode
            );

            if (actionSent) {
              const targetSeq = actionSent.parsed.payload.seq_num;

              // Find state update frame received on Page A (local seat_1)
              stateUpdateA = wsLogsA.find(log => 
                log.type === 'receive' && 
                log.parsed?.event === 'state_update' && 
                log.parsed?.payload?.last_action_seat === 'seat_1' && 
                log.parsed?.payload?.last_action_seq === targetSeq
              );

              // Find state update frame received on Page B (opponent seat_1)
              stateUpdateB = wsLogsB.find(log => 
                log.type === 'receive' && 
                log.parsed?.event === 'state_update' && 
                log.parsed?.payload?.last_action_seat === 'seat_1' && 
                log.parsed?.payload?.last_action_seq === targetSeq
              );

              // Process local seat state change
              if (stateUpdateA && !resolvedLocal) {
                const isObservable = stateUpdateA.parsed.payload.last_action_observable_change;
                const authA_Board = stateUpdateA.parsed.payload.seat_1.board;
                const authA_Piece = stateUpdateA.parsed.payload.seat_1.active_piece;

                if (isObservable) {
                  // Verify canvas pixels actually render the expected state
                  const curA = await pageA.evaluate(`(${CANVAS_INSPECTOR_FN})('.own-board canvas.board-canvas', ${JSON.stringify(authA_Board)}, ${JSON.stringify(authA_Piece)})`);
                  if (curA && curA.success) {
                    localObservedNode = driverNow();
                    localPixelAckNode = driverNow();
                    localReadTimestamp = curA.readTimestamp;
                    finalA = curA;
                    resolvedLocal = true;
                    lastAState = { board: authA_Board, activePiece: authA_Piece };
                  }
                } else {
                  // Authorized no-op!
                  resolvedLocal = false;
                  if (authA_Piece?.type === 'O' && (targetActionType === 'cw' || targetActionType === 'ccw')) {
                    category = 'o_rotation_noop';
                    reason = 'O rotation is a strict state-invariant no-op';
                  } else {
                    category = 'blocked_noop';
                    reason = 'Movement is blocked';
                  }
                  break;
                }
              }

              // Process remote seat state change
              if (stateUpdateB && !resolvedRemote) {
                const authB_Board = stateUpdateB.parsed.payload.seat_1.board;
                const authB_Piece = stateUpdateB.parsed.payload.seat_1.active_piece;

                const curB = await pageB.evaluate(`(${CANVAS_INSPECTOR_FN})('.opponent-board canvas.board-canvas', ${JSON.stringify(authB_Board)}, ${JSON.stringify(authB_Piece)})`);
                if (curB && curB.success) {
                  remoteObservedNode = driverNow();
                  remotePixelAckNode = driverNow();
                  remoteReadTimestamp = curB.readTimestamp;
                  finalB = curB;
                  resolvedRemote = true;
                  lastBState = { board: authB_Board, activePiece: authB_Piece };
                }
              }
            }

            if (resolvedLocal && resolvedRemote) {
              break;
            }
            await pageA.waitForTimeout(2);
          }

          const driverAckTimeNode = driverNow();

          // Action latency calculations
          const localLatency = resolvedLocal && localObservedNode ? (localObservedNode - dispatchTimeNode) : null;
          const remoteLatency = resolvedRemote && remoteObservedNode ? (remoteObservedNode - dispatchTimeNode) : null;

          if (!resolvedLocal) {
            if (stateUpdateA) {
              const isObservable = stateUpdateA.parsed.payload.last_action_observable_change;
              if (isObservable) {
                category = 'unresolved';
                reason = 'State update received with observable change, but pixel verification failed';
              } else {
                const authA_Piece = stateUpdateA.parsed.payload.seat_1.active_piece;
                if (authA_Piece?.type === 'O' && (targetActionType === 'cw' || targetActionType === 'ccw')) {
                  category = 'o_rotation_noop';
                  reason = 'O rotation is a strict state-invariant no-op';
                } else {
                  category = 'blocked_noop';
                  reason = 'Movement is blocked';
                }
              }
            } else {
              category = 'unresolved';
              reason = 'Timeout or unmatched WS state update';
            }
          }

          actionsTaken.push({
            action: key,
            category,
            successLocal: resolvedLocal,
            successRemote: resolvedRemote,
            localLatencyMs: localLatency,
            remoteLatencyMs: remoteLatency,
            driverTimestamps: {
              dispatch: dispatchTimeNode,
              localObserved: localObservedNode,
              remoteObserved: remoteObservedNode,
              pixelAckLocal: localPixelAckNode,
              pixelAckRemote: remotePixelAckNode,
              driverAck: driverAckTimeNode
            },
            localReadTimestamp,
            remoteReadTimestamp,
            focusState: { A: focusA, B: focusB },
            pieceType: lastAState?.activePiece?.type || null,
            expectedCellsA: finalA?.board || null,
            expectedActivePieceA: finalA?.activePiece || null,
            observedBoardA: finalA?.observed || null,
            observedRGBA: finalA?.rawRGB || null,
            expectedCellsB: finalB?.board || null,
            expectedActivePieceB: finalB?.activePiece || null,
            observedBoardB: finalB?.observed || null,
            observedRGBB: finalB?.rawRGB || null,
            reason,
            linkedWSMessages: {
              actionSent: actionSent ? {
                type: actionSent.type,
                payload: actionSent.payload,
                parsed: actionSent.parsed,
                timestamp: actionSent.timestamp
              } : null,
              stateUpdateA: stateUpdateA ? {
                type: stateUpdateA.type,
                payload: stateUpdateA.payload,
                parsed: stateUpdateA.parsed,
                timestamp: stateUpdateA.timestamp
              } : null,
              stateUpdateB: stateUpdateB ? {
                type: stateUpdateB.type,
                payload: stateUpdateB.payload,
                parsed: stateUpdateB.parsed,
                timestamp: stateUpdateB.timestamp
              } : null
            }
          });

          await pageA.waitForTimeout(1000);
        }

        // Post-run Clock Calibration to check drift
        calibAfterA = await calibrateClock(pageA);
        calibAfterB = await calibrateClock(pageB);

        runReport.calibrationLimitsA.after = calibAfterA;
        runReport.calibrationLimitsA.driftMs = calibAfterA.offset - (calibBeforeA ? calibBeforeA.offset : 0);
        runReport.calibrationLimitsB.after = calibAfterB;
        runReport.calibrationLimitsB.driftMs = calibAfterB.offset - (calibBeforeB ? calibBeforeB.offset : 0);

        runReport.success = true;
        runReport.errorStage = 'complete';

      } catch (err: any) {
        console.error(`[${runId}] Failed:`, err);
        executionFailed = true;
        runReport.success = false;
        runReport.error = err.message || err.toString();
      } finally {
        runReport.rawTelemetry.wsLogsA = wsLogsA;
        runReport.rawTelemetry.wsLogsB = wsLogsB;

        try {
          await pageA.screenshot({ path: path.join(runDir, 'client_a_final.png') }).catch(() => {});
          await pageB.screenshot({ path: path.join(runDir, 'client_b_final.png') }).catch(() => {});
          await contextA.tracing.stop({ path: path.join(runDir, 'client_a_trace.zip') }).catch(() => {});
          await contextB.tracing.stop({ path: path.join(runDir, 'client_b_trace.zip') }).catch(() => {});
        } catch (e) {}

        try {
          const telemetryA = await pageA.evaluate(() => ({
            rafSamples: window.__rafSamples || [],
            drawEvents: window.__drawEvents || [],
            visibilityEvents: window.__visibilityEvents || []
          })).catch(() => null);

          const telemetryB = await pageB.evaluate(() => ({
            rafSamples: window.__rafSamples || [],
            drawEvents: window.__drawEvents || [],
            visibilityEvents: window.__visibilityEvents || []
          })).catch(() => null);

          if (telemetryA && telemetryB) {
            runReport.rawTelemetry.rafSamplesA = telemetryA.rafSamples;
            runReport.rawTelemetry.drawEventsA = telemetryA.drawEvents;
            runReport.rawTelemetry.visibilityEventsA = telemetryA.visibilityEvents;
            runReport.visibilityEventsA = telemetryA.visibilityEvents;

            runReport.rawTelemetry.rafSamplesB = telemetryB.rafSamples;
            runReport.rawTelemetry.drawEventsB = telemetryB.drawEvents;
            runReport.rawTelemetry.visibilityEventsB = telemetryB.visibilityEvents;
            runReport.visibilityEventsB = telemetryB.visibilityEvents;

            const calOffsetA = runReport.calibrationLimitsA?.before?.offset || 0;
            const calOffsetB = runReport.calibrationLimitsB?.before?.offset || 0;

            // Filter Client A rAF samples checking BOTH endpoints lie inside the window and delta is finite & strictly positive
            let excludedNonpositiveRafCountA = 0;
            let excludedNonpositiveRafInWindowCountA = 0;
            const filteredRafA = [];
            const excludedRafA = [];
            for (const s of telemetryA.rafSamples) {
              const t_prev_driver = s[0] - calOffsetA;
              const t_curr_driver = s[1] - calOffsetA;
              const inWindow = t_prev_driver >= measureStartNode && t_curr_driver <= measureEndNode;

              const delta = s[2];
              const isPositive = typeof delta === 'number' && isFinite(delta) && delta > 0;

              if (inWindow && isPositive) {
                filteredRafA.push(s);
              } else {
                let rsn = '';
                if (!isPositive) {
                  excludedNonpositiveRafCountA++;
                  if (inWindow) {
                    excludedNonpositiveRafInWindowCountA++;
                    rsn = 'Nonpositive delta in window';
                  } else {
                    rsn = 'Nonpositive delta out of window';
                  }
                } else {
                  if (t_prev_driver < measureStartNode) rsn = 'Before start window';
                  if (t_curr_driver > measureEndNode) rsn = 'After end window';
                }
                excludedRafA.push({ sample: s, reason: rsn });
              }
            }

            // Filter Client B rAF samples checking BOTH endpoints lie inside the window and delta is finite & strictly positive
            let excludedNonpositiveRafCountB = 0;
            let excludedNonpositiveRafInWindowCountB = 0;
            const filteredRafB = [];
            const excludedRafB = [];
            for (const s of telemetryB.rafSamples) {
              const t_prev_driver = s[0] - calOffsetB;
              const t_curr_driver = s[1] - calOffsetB;
              const inWindow = t_prev_driver >= measureStartNode && t_curr_driver <= measureEndNode;

              const delta = s[2];
              const isPositive = typeof delta === 'number' && isFinite(delta) && delta > 0;

              if (inWindow && isPositive) {
                filteredRafB.push(s);
              } else {
                let rsn = '';
                if (!isPositive) {
                  excludedNonpositiveRafCountB++;
                  if (inWindow) {
                    excludedNonpositiveRafInWindowCountB++;
                    rsn = 'Nonpositive delta in window';
                  } else {
                    rsn = 'Nonpositive delta out of window';
                  }
                } else {
                  if (t_prev_driver < measureStartNode) rsn = 'Before start window';
                  if (t_curr_driver > measureEndNode) rsn = 'After end window';
                }
                excludedRafB.push({ sample: s, reason: rsn });
              }
            }

            runReport.excludedNonpositiveRafCount_ClientA = excludedNonpositiveRafCountA;
            runReport.excludedNonpositiveRafInWindowCount_ClientA = excludedNonpositiveRafInWindowCountA;
            runReport.excludedNonpositiveRafCount_ClientB = excludedNonpositiveRafCountB;
            runReport.excludedNonpositiveRafInWindowCount_ClientB = excludedNonpositiveRafInWindowCountB;
            runReport.excludedRafA = excludedRafA;
            runReport.excludedRafB = excludedRafB;

            const rafDeltasA = filteredRafA.map((s: any) => s[2]);
            const rafDeltasB = filteredRafB.map((s: any) => s[2]);

            // Filter Client A Draw events
            const filteredDrawEventsA = [];
            const excludedDrawEventsA = [];
            for (const e of telemetryA.drawEvents) {
              const t_driver = e.timestamp - calOffsetA;
              if (t_driver >= measureStartNode && t_driver <= measureEndNode) {
                filteredDrawEventsA.push(e);
              } else {
                let rsn = '';
                if (t_driver < measureStartNode) rsn = 'Before start window';
                if (t_driver > measureEndNode) rsn = 'After end window';
                excludedDrawEventsA.push({ event: e, reason: rsn });
              }
            }

            // Filter Client B Draw events
            const filteredDrawEventsB = [];
            const excludedDrawEventsB = [];
            for (const e of telemetryB.drawEvents) {
              const t_driver = e.timestamp - calOffsetB;
              if (t_driver >= measureStartNode && t_driver <= measureEndNode) {
                filteredDrawEventsB.push(e);
              } else {
                let rsn = '';
                if (t_driver < measureStartNode) rsn = 'Before start window';
                if (t_driver > measureEndNode) rsn = 'After end window';
                excludedDrawEventsB.push({ event: e, reason: rsn });
              }
            }

            runReport.excludedDrawEventsA = excludedDrawEventsA;
            runReport.excludedDrawEventsB = excludedDrawEventsB;

            const drawIntervalsA: number[] = [];
            for (let i = 1; i < filteredDrawEventsA.length; i++) {
              const delta = filteredDrawEventsA[i].timestamp - filteredDrawEventsA[i-1].timestamp;
              drawIntervalsA.push(delta);
            }

            const drawIntervalsB: number[] = [];
            for (let i = 1; i < filteredDrawEventsB.length; i++) {
              const delta = filteredDrawEventsB[i].timestamp - filteredDrawEventsB[i-1].timestamp;
              drawIntervalsB.push(delta);
            }

            // Only use action latency where both dispatch and pixel ACK lie inside the measurement window
            const localLatencies = actionsTaken
              .filter(a => a.category === 'changed' && a.successLocal && a.localLatencyMs !== null &&
                           a.driverTimestamps.dispatch >= measureStartNode &&
                           a.driverTimestamps.pixelAckLocal <= measureEndNode)
              .map(a => a.localLatencyMs as number);

            const remoteLatencies = actionsTaken
              .filter(a => a.category === 'changed' && a.successRemote && a.remoteLatencyMs !== null &&
                           a.driverTimestamps.dispatch >= measureStartNode &&
                           a.driverTimestamps.pixelAckRemote <= measureEndNode)
              .map(a => a.remoteLatencyMs as number);

            const excludedActions = actionsTaken.filter(a => !(a.category === 'changed' && a.successLocal && a.localLatencyMs !== null &&
                           a.driverTimestamps.dispatch >= measureStartNode &&
                           a.driverTimestamps.pixelAckLocal <= measureEndNode));

            runReport.excludedActions = excludedActions;

            const localStats = computePercentiles(localLatencies);
            const remoteStats = computePercentiles(remoteLatencies);
            const frameStatsA = computePercentiles(rafDeltasA);
            const frameStatsB = computePercentiles(rafDeltasB);
            const drawStatsA = computePercentiles(drawIntervalsA);
            const drawStatsB = computePercentiles(drawIntervalsB);

            const elapsedSeconds = measureSeconds; // No teardown-based denominators
            const meanFPS_A = filteredRafA.length / elapsedSeconds;
            const meanFPS_B = filteredRafB.length / elapsedSeconds;

            runReport.elapsedSeconds = elapsedSeconds;
            runReport.totalActions = actionsTaken.length;
            runReport.successfulLocalActions = actionsTaken.filter(a => a.category === 'changed' && a.successLocal).length;
            runReport.successfulRemoteActions = actionsTaken.filter(a => a.category === 'changed' && a.successRemote).length;
            runReport.localActionLatencyMs = localStats;
            runReport.remoteActionLatencyMs = remoteStats;
            runReport.frameSchedulingIntervalMs_ClientA = frameStatsA;
            runReport.frameSchedulingIntervalMs_ClientB = frameStatsB;
            runReport.drawCandidateIntervalMs_ClientA = drawStatsA;
            runReport.drawCandidateIntervalMs_ClientB = drawStatsB;
            runReport.observedMeanFPS_ClientA = meanFPS_A;
            runReport.observedMeanFPS_ClientB = meanFPS_B;
            runReport.rAFCount_ClientA = filteredRafA.length;
            runReport.rAFCount_ClientB = filteredRafB.length;
            runReport.drawCount_ClientA = filteredDrawEventsA.length;
            runReport.drawCount_ClientB = filteredDrawEventsB.length;
            runReport.actions = actionsTaken;

            console.log(`[${runId}] Telemetry complete.`);
            console.log(`  - Client A Mean Frame Rate: ${meanFPS_A.toFixed(2)} FPS`);
            console.log(`  - Client A rAF Interval p95: ${frameStatsA.p95 !== null ? frameStatsA.p95.toFixed(2) : 'N/A'} ms`);
            console.log(`  - Median Local Latency: ${localStats.median !== null ? localStats.median.toFixed(2) : 'N/A'} ms`);
            console.log(`  - Median Opponent-Visible Latency: ${remoteStats.median !== null ? remoteStats.median.toFixed(2) : 'N/A'} ms`);
          }
        } catch (e) {
          console.error('Error extracting duel telemetry in finally block:', e);
        }

        fs.writeFileSync(path.join(runDir, `${runId}_partial.json`), JSON.stringify(runReport, null, 2));
        runsReport.push(runReport);

        await contextA.close().catch(() => {});
        await contextB.close().catch(() => {});
        await browserA.close().catch(() => {});
        await browserB.close().catch(() => {});
      }
    }

  } catch (err: any) {
    console.error('Benchmark execution error:', err);
    executionFailed = true;
  }

  // ==========================================================================
  // SMOKE RUN VERIFICATION & ERROR FORCING
  // ==========================================================================
  let smokeValidationFailed = false;
  if (isSmoke) {
    console.log('\n--- VERIFYING SMOKE RUN ACCEPTANCE CRITERIA ---');
    for (const r of runsReport) {
      if (r.type === 'solo') {
        if (r.rAFCount === 0) {
          console.error(`Smoke validation failed for ${r.runId}: rAFCount is 0!`);
          smokeValidationFailed = true;
          r.success = false;
          r.error = 'Smoke validation failed: rAFCount is 0';
        }
        const successful = r.actions.filter((a: any) => a.category === 'changed' && a.success).length;
        if (successful === 0) {
          console.error(`Smoke validation failed for ${r.runId}: Zero successful (causally matched and pixel-verified) actions!`);
          smokeValidationFailed = true;
          r.success = false;
          r.error = 'Smoke validation failed: Zero successful actions';
        }
      } else if (r.type === 'duel') {
        if (r.rAFCount_ClientA === 0 || r.rAFCount_ClientB === 0) {
          console.error(`Smoke validation failed for ${r.runId}: Client A or Client B rAFCount is 0!`);
          smokeValidationFailed = true;
          r.success = false;
          r.error = 'Smoke validation failed: Client A or Client B rAFCount is 0';
        }
        const successfulLocal = r.actions.filter((a: any) => a.category === 'changed' && a.successLocal).length;
        const successfulRemote = r.actions.filter((a: any) => a.category === 'changed' && a.successRemote).length;
        if (successfulLocal === 0 || successfulRemote === 0) {
          console.error(`Smoke validation failed for ${r.runId}: Zero successful local or remote actions (local: ${successfulLocal}, remote: ${successfulRemote})!`);
          smokeValidationFailed = true;
          r.success = false;
          r.error = 'Smoke validation failed: Zero successful local or remote actions';
        }
      }
    }
  }

  // ==========================================================================
  // GENERATE COMBINED REPORT JSON
  // ==========================================================================
  const reportPath = path.join(outputDir, 'performance-report.json');
  const finalReport = {
    metadata: {
      generator: 'Monotonic Instrument Performance Benchmark Suite',
      version: '2.0.0',
      timestamp: envDetails.timestamp,
      environment: envDetails,
      isSmokeSuite: isSmoke
    },
    runs: runsReport
  };

  fs.writeFileSync(reportPath, JSON.stringify(finalReport, null, 2), 'utf-8');
  console.log('\n================================================================');
  console.log('PERFORMANCE REPORT GENERATED SUCCESSFULLY!');
  console.log(`Report JSON saved at: ${reportPath}`);
  console.log('================================================================');

  if (executionFailed || smokeValidationFailed) {
    console.error('Fatal: One or more benchmark runs encountered failures.');
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Fatal benchmark crash:', err);
  process.exit(1);
});