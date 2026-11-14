// Playwright-based Browser Performance Benchmark for Tetris Stage 3
// Measures rendering throughput, frame scheduling intervals, action latency, and DOM updates.
import { chromium } from 'playwright';
import os from 'os';
import fs from 'fs';
import path from 'path';

const APP_URL = process.env.BENCHMARK_APP_URL || 'http://127.0.0.1:5183';
const TRIALS = 3;
const WARMUP_MS = 5000;
const MEASURE_MS = 30000;
const OUTPUT_DIR_BASE = process.env.BENCHMARK_OUTPUT_DIR || path.resolve('benchmark-results');

// Quantile calculation using linear interpolation
function getPercentile(sortedArray, percentile) {
  if (sortedArray.length === 0) return 0;
  const index = (sortedArray.length - 1) * percentile;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;
  return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
}

async function runTrial(trialNum, runDir) {
  console.log(`\n--- Starting Trial ${trialNum} / ${TRIALS} ---`);
  console.log(`Target: ${APP_URL}`);

  let browser = null;
  let context = null;
  let page = null;
  
  // Trackers
  const apiRequests = new Map(); // request -> detail
  let requestSeq = 0;
  const actionSamples = [];
  const restartsList = [];
  let restartCount = 0;

  // Variables for exact timeline declarations
  let warmupStartPage = null;
  let warmupEndPage = null;
  let measureStartPage = null;
  let measureEndPage = null;
  let observedStopPage = null;

  let initSnapshot = null;
  let warmupStartSnapshot = null;
  let measureStartSnapshot = null;
  let stopSnapshot = null;

  try {
    // 1. Launch Chrome with specified criteria: channel 'chrome', headless: false, and sandbox enabled.
    // Explicitly set chromiumSandbox: true and do NOT include disabling args.
    browser = await chromium.launch({
      headless: false,
      channel: 'chrome',
      chromiumSandbox: true
    });

    context = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      deviceScaleFactor: 1,
    });

    // Start Playwright Tracing
    await context.tracing.start({ screenshots: true, snapshots: true });

    page = await context.newPage();

    // Monitor API requests using stable Playwright Request objects and stable IDs
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/')) {
        const id = `api-req-${++requestSeq}`;
        apiRequests.set(request, {
          id,
          url,
          method: request.method(),
          postData: request.postData() || null,
          nodeStartTime: performance.now(),
          nodeEndTime: null,
          status: null,
          responseBody: null,
          error: null
        });
      }
    });

    page.on('response', async response => {
      const request = response.request();
      const reqData = apiRequests.get(request);
      if (reqData) {
        reqData.nodeEndTime = performance.now();
        reqData.status = response.status();
        try {
          reqData.responseBody = await response.json();
        } catch (_) {
          try {
            reqData.responseBody = await response.text();
          } catch (_) {}
        }
      }
    });

    page.on('requestfailed', request => {
      const reqData = apiRequests.get(request);
      if (reqData) {
        reqData.nodeEndTime = performance.now();
        reqData.error = request.failure()?.errorText || 'Failed';
      }
    });

    await page.goto(APP_URL);
    await page.bringToFront();

    // Verify initial focus & visibility snapshots (at init)
    initSnapshot = await page.evaluate(() => {
      return {
        timestamp: performance.now(),
        focused: document.hasFocus(),
        visible: document.visibilityState === 'visible'
      };
    });
    console.log(`Initial status - Focused: ${initSnapshot.focused}, Visibility: ${initSnapshot.visible ? 'visible' : 'hidden'}`);

    // Wait for the Start Session button in the sidebar
    const startButton = page.getByRole('button', { name: 'Start Session', exact: true });
    await startButton.waitFor({ timeout: 10000 });

    // Initialize in-page performance tracking scripts
    await page.evaluate(() => {
      window.benchmark_active = false;
      window.benchmark_rAF_data = []; // Elements represent [prevTime, currTime, delta]
      window.benchmark_focus_visibility_log = [];
      window.benchmark_events = [];
      window.benchmark_raw_mutations = []; // Each element: { timestamp, mutationCount, fullsignature }
      window.benchmark_transitions = [];   // Board state transitions
      window.benchmark_board_geometry_samples = [];
      window.benchmark_board_left_viewport = false;

      // Board geometry sampler function
      window.sampleBoardGeometry = (contextLabel) => {
        const board = document.querySelector('.board');
        if (!board) return;
        const rect = board.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const now = performance.now();
        const bounds = {
          left: rect.left,
          top: rect.top,
          right: rect.right,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height
        };
        const scroll = {
          x: window.scrollX,
          y: window.scrollY
        };
        const hasFocus = document.hasFocus();
        const withinViewport = (
          rect.top >= 0 &&
          rect.left >= 0 &&
          rect.bottom <= viewportHeight &&
          rect.right <= viewportWidth
        );
        
        window.benchmark_board_geometry_samples.push({
          timestamp: now,
          context: contextLabel,
          bounds,
          viewport: { width: viewportWidth, height: viewportHeight },
          scroll,
          hasFocus,
          withinViewport
        });

        // If it leaves viewport during measured window, record and flag it
        if (window.benchmark_timeline &&
            now >= window.benchmark_timeline.measureStart &&
            now <= window.benchmark_timeline.measureEnd) {
          if (!withinViewport) {
            window.benchmark_board_left_viewport = true;
          }
        }
      };

      // Board signature builder - returns FULL 200 cells/400 characters board class signatures
      window.getBoardSignature = () => {
        const cells = Array.from(document.querySelectorAll('.board .cell'));
        if (cells.length === 0) return 'EMPTY';
        return cells.map(c => {
          const cls = c.className || '';
          const colorMatch = cls.match(/color-(\d+)/);
          const color = colorMatch ? colorMatch[1] : '0';
          const isActive = cls.includes('cell-active') ? 'A' : 'S';
          return color + isActive;
        }).join('');
      };

      // Mutation observer for DOM updates on .board-container
      const boardEl = document.querySelector('.board-container') || document.body;
      window.boardObserver = new MutationObserver((mutations) => {
        const sig = window.getBoardSignature();
        const now = performance.now();
        
        // Record details for every single mutation callback (defect 3)
        window.benchmark_raw_mutations.push({
          timestamp: now,
          mutationCount: mutations.length,
          fullsignature: sig
        });
        
        // Retain every true board transition separately
        if (window.benchmark_transitions.length === 0 || window.benchmark_transitions[window.benchmark_transitions.length - 1].signature !== sig) {
          window.benchmark_transitions.push({ timestamp: now, signature: sig });
        }

        if (typeof window.sampleBoardGeometry === 'function') {
          window.sampleBoardGeometry('mutation');
        }
      });
      window.boardObserver.observe(boardEl, { attributes: true, childList: true, subtree: true });

      // requestAnimationFrame interval tracker
      let lastTime = performance.now();
      window.rAF_running = true;
      function trackFrame(time) {
        if (!window.rAF_running) return;
        const delta = time - lastTime;
        window.benchmark_rAF_data.push([lastTime, time, delta]);
        lastTime = time;
        requestAnimationFrame(trackFrame);
      }
      requestAnimationFrame(trackFrame);

      // Listeners for real focus, blur, and visibility events
      window.addEventListener('focus', () => {
        window.benchmark_events.push({ type: 'focus', timestamp: performance.now() });
      });
      window.addEventListener('blur', () => {
        window.benchmark_events.push({ type: 'blur', timestamp: performance.now() });
      });
      document.addEventListener('visibilitychange', () => {
        window.benchmark_events.push({ type: 'visibilitychange', value: document.visibilityState, timestamp: performance.now() });
      });

      // Periodic focus/visibility/geometry sampler (every 500ms)
      window.focusSampler = setInterval(() => {
        const now = performance.now();
        window.benchmark_focus_visibility_log.push({
          time: now,
          focused: document.hasFocus(),
          visible: document.visibilityState === 'visible'
        });
        if (typeof window.sampleBoardGeometry === 'function') {
          window.sampleBoardGeometry('periodic');
        }
      }, 500);
    });

    // 2. Start actual game BEFORE warmup, await playing state selector (defect 2)
    console.log('Starting actual game session...');
    await startButton.click();
    
    // Await actual active playing class selector to confirm state before setup
    await page.waitForSelector('.status-playing', { timeout: 10000 });

    // Scroll actual .board into viewport if needed without CSS/layout/zoom/gravity changes
    const boardLocator = page.locator('.board');
    await boardLocator.scrollIntoViewIfNeeded();

    // Validate .board rect fully within 1280x900 viewport; record bounds/viewport/scroll/hasFocus with performance.now
    const boardGeometryInit = await page.evaluate(() => {
      const board = document.querySelector('.board');
      if (!board) {
        return {
          success: false,
          error: 'No .board element found',
          bounds: null,
          viewport: null,
          scroll: null,
          hasFocus: false,
          timestamp: performance.now()
        };
      }
      const rect = board.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const bounds = {
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height
      };
      const scroll = {
        x: window.scrollX,
        y: window.scrollY
      };
      const hasFocus = document.hasFocus();
      const withinViewport = (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= viewportHeight &&
        rect.right <= viewportWidth
      );
      return {
        success: withinViewport,
        bounds,
        viewport: { width: viewportWidth, height: viewportHeight },
        scroll,
        hasFocus,
        timestamp: performance.now()
      };
    });

    console.log(`Initial Board Geometry Qualification:`, JSON.stringify(boardGeometryInit, null, 2));
    if (!boardGeometryInit.success) {
      throw new Error(`Failure: The .board element bounding rect is not fully within the 1280x900 viewport! bounds: ${JSON.stringify(boardGeometryInit.bounds)}`);
    }

    // Also register the initial board geometry sample
    await page.evaluate(() => {
      if (typeof window.sampleBoardGeometry === 'function') {
        window.sampleBoardGeometry('init-qualification');
      }
    });

    // 3. Setup DECLARED pageclock timeline ONCE at setup (defect 1)
    warmupStartPage = await page.evaluate(() => {
      const now = performance.now();
      window.benchmark_timeline = {
        warmupStart: now,
        warmupEnd: now + 5000,
        measureStart: now + 5000,
        measureEnd: now + 35000,
        observedStop: null
      };
      window.benchmark_active = true;
      return now;
    });

    warmupEndPage = warmupStartPage + WARMUP_MS;
    measureStartPage = warmupEndPage;
    measureEndPage = measureStartPage + MEASURE_MS;

    // Capture focus/visibility snapshot at warmupStart (defect 5)
    warmupStartSnapshot = await page.evaluate(() => {
      return {
        timestamp: performance.now(),
        focused: document.hasFocus(),
        visible: document.visibilityState === 'visible'
      };
    });

    console.log(`Starting ${WARMUP_MS}ms warm-up WITH gameplay (loop check against declared pageclock)...`);
    const observedWarmupStartPage = await page.evaluate(() => performance.now());
    const observedWarmupStartNode = performance.now();
    
    // Gameplay actions during warmup - check loop end against declared page clock
    while (true) {
      const nowPage = await page.evaluate(() => performance.now());
      if (nowPage >= warmupEndPage) {
        break;
      }

      // Handle restarts during warmup (defect 2)
      const isGameOver = await page.evaluate(() => {
        const overlay = document.querySelector('.overlay');
        return !!(overlay && overlay.textContent && overlay.textContent.includes('GAME OVER'));
      });

      if (isGameOver) {
        console.log('Game Over detected during warmup. Triggering restart via Play Again button...');
        const playAgainBtn = page.getByRole('button', { name: 'Play Again', exact: true });
        const restartStartPage = await page.evaluate(() => performance.now());
        const restartStartNode = performance.now();
        await playAgainBtn.click();
        restartCount++;
        await page.waitForSelector('.status-playing', { timeout: 5000 });
        const restartEndPage = await page.evaluate(() => performance.now());
        const restartEndNode = performance.now();
        restartsList.push({
          phase: 'warmup',
          timestampPage: restartStartPage,
          durationPage: restartEndPage - restartStartPage,
          timestampNode: restartStartNode,
          durationNode: restartEndNode - restartStartNode
        });
        continue;
      }

      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(150);
    }
    const observedWarmupEndPage = await page.evaluate(() => performance.now());
    const observedWarmupEndNode = performance.now();

    // Capture focus/visibility snapshot at measureStart (defect 5)
    measureStartSnapshot = await page.evaluate(() => {
      return {
        timestamp: performance.now(),
        focused: document.hasFocus(),
        visible: document.visibilityState === 'visible'
      };
    });

    console.log('Warm-up complete. Starting 30-second measured window...');
    const observedMeasureStartPage = await page.evaluate(() => performance.now());
    const observedMeasureStartNode = performance.now();
    const actions = ['ArrowLeft', 'ArrowRight', 'ArrowDown'];
    let actionIdx = 0;

    // Measurement loop - check loop end against declared pageclock bounds so no extra actions (defect 1)
    while (true) {
      const nowPage = await page.evaluate(() => performance.now());
      if (nowPage >= measureEndPage) {
        break;
      }

      // Stop with honest failed raw if board leaves viewport during measured window
      const boardLeftViewport = await page.evaluate(() => window.benchmark_board_left_viewport);
      if (boardLeftViewport) {
        throw new Error(`Failure: The .board element left the fully visible 1280x900 viewport during the measured window.`);
      }

      // Check for Game Over and restart through Play Again button
      const isGameOver = await page.evaluate(() => {
        const overlay = document.querySelector('.overlay');
        return !!(overlay && overlay.textContent && overlay.textContent.includes('GAME OVER'));
      });

      if (isGameOver) {
        console.log('Game Over detected. Triggering restart via Play Again button...');
        const playAgainBtn = page.getByRole('button', { name: 'Play Again', exact: true });
        const restartStartPage = await page.evaluate(() => performance.now());
        const restartStartNode = performance.now();
        await playAgainBtn.click();
        restartCount++;
        await page.waitForSelector('.status-playing', { timeout: 5000 });
        const restartEndPage = await page.evaluate(() => performance.now());
        const restartEndNode = performance.now();
        restartsList.push({
          phase: 'measurement',
          timestampPage: restartStartPage,
          durationPage: restartEndPage - restartStartPage,
          timestampNode: restartStartNode,
          durationNode: restartEndNode - restartStartNode
        });
        continue;
      }

      // Select deterministic action
      const key = actions[actionIdx % actions.length];
      actionIdx++;

      // Capture state BEFORE keypress
      const beforeSig = await page.evaluate(() => window.getBoardSignature());
      const actionStartPage = await page.evaluate(() => performance.now());
      const actionStartNode = performance.now();

      // Press key in foreground
      await page.keyboard.press(key);

      // Record board geometry at action dispatch
      await page.evaluate(() => {
        if (typeof window.sampleBoardGeometry === 'function') {
          window.sampleBoardGeometry('action-dispatch');
        }
      });

      // Wait a short duration to let React register the DOM state change (up to 120ms)
      await page.waitForTimeout(120);

      const actionEndNode = performance.now();

      // Capture state AFTER keypress
      const afterSig = await page.evaluate(() => window.getBoardSignature());
      const pageTransitions = await page.evaluate(() => window.benchmark_transitions);

      // Stable requests association and clocks alignment (defect 4)
      const expectedDir = key === 'ArrowLeft' ? 'left' : (key === 'ArrowRight' ? 'right' : 'down');
      const associatedRequests = Array.from(apiRequests.values()).filter(req => {
        if (!req.url.includes('/move')) return false;
        const isTimeClose = req.nodeStartTime >= (actionStartNode - 15) && req.nodeStartTime <= (actionEndNode + 15);
        if (!isTimeClose) return false;
        try {
          const body = JSON.parse(req.postData || '{}');
          return body.direction === expectedDir;
        } catch (_) {
          return false;
        }
      });

      let sampleStatus = 'success';
      let apiDetail = null;
      let candidateIds = associatedRequests.map(r => r.id);
      let isAmbiguous = false;

      // Handle heuristic same-direction request overlap (defect 4)
      if (associatedRequests.length === 0) {
        sampleStatus = 'missing-api';
      } else if (associatedRequests.length > 1) {
        sampleStatus = 'ambiguous';
        isAmbiguous = true;
        const primaryReq = associatedRequests[0];
        apiDetail = {
          id: primaryReq.id,
          url: primaryReq.url,
          method: primaryReq.method,
          durationNode: primaryReq.nodeEndTime ? (primaryReq.nodeEndTime - primaryReq.nodeStartTime) : null,
          status: primaryReq.status
        };
      } else {
        const primaryReq = associatedRequests[0];
        apiDetail = {
          id: primaryReq.id,
          url: primaryReq.url,
          method: primaryReq.method,
          durationNode: primaryReq.nodeEndTime ? (primaryReq.nodeEndTime - primaryReq.nodeStartTime) : null,
          status: primaryReq.status
        };
        if (primaryReq.status !== 200) {
          sampleStatus = 'api-error';
        }
      }

      // Latency calculation on page clock (defect 4)
      // DOCUMENTATION ON FIRST DOM TRANSITION CAUSALITY LIMITS:
      // When an action key is pressed, we observe the next transition in the DOM. However,
      // there is inherent gravity ticks running in parallel on the board, which can also trigger
      // a DOM mutation transition. If gravity overlaps with a manual movement, the first observed
      // DOM transition might be caused by gravity rather than the user action itself. Thus, the
      // action-to-visible-update latency can be affected by heuristic overlap. When multiple same-direction
      // API requests are detected in the window, we mark them as ambiguous and exclude them from
      // successful summaries to ensure data causality integrity.
      const matchingTransition = pageTransitions.find(t => t.timestamp >= actionStartPage && t.signature !== beforeSig);
      let latency = null;
      let visibleTime = null;

      if (beforeSig === afterSig) {
        sampleStatus = 'no-op'; // Movement blocked
      } else if (matchingTransition) {
        visibleTime = matchingTransition.timestamp;
        latency = visibleTime - actionStartPage;
        if (latency < 0) {
          sampleStatus = 'invalid-latency';
        }
      } else {
        sampleStatus = 'timeout'; // State changed but mutation event not caught
      }

      // Enforce HTTP 200 requirement for success status
      if (sampleStatus === 'success') {
        if (associatedRequests.length === 0) {
          sampleStatus = 'missing-api';
        } else if (isAmbiguous) {
          sampleStatus = 'ambiguous';
        } else if (apiDetail && apiDetail.status !== 200) {
          sampleStatus = 'api-error';
        }
      }

      actionSamples.push({
        actionId: `action-${trialNum}-${actionIdx}`,
        key,
        direction: expectedDir,
        actionStartPage,
        actionStartNode,
        beforeSignature: beforeSig,
        afterSignature: afterSig,
        visibleTime,
        latency,
        status: sampleStatus,
        api: apiDetail,
        candidateIds,
        isAmbiguous
      });

      // Modest gameplay pacing delay
      await page.waitForTimeout(130);
    }
    const observedMeasureEndPage = await page.evaluate(() => performance.now());
    const observedMeasureEndNode = performance.now();

    // Stop observers (rAF, focusSampler, boardObserver) BEFORE visual screenshot (defect 1)
    observedStopPage = await page.evaluate(() => {
      const now = performance.now();
      window.benchmark_timeline.observedStop = now;
      window.rAF_running = false;
      if (window.focusSampler) clearInterval(window.focusSampler);
      if (window.boardObserver) window.boardObserver.disconnect();
      return now;
    });

    stopSnapshot = await page.evaluate(() => {
      return {
        timestamp: performance.now(),
        focused: document.hasFocus(),
        visible: document.visibilityState === 'visible'
      };
    });

    // Retrieve full in-page data BEFORE closing the browser to avoid losing raw telemetry (defect 6)
    const benchmarkData = await page.evaluate(() => {
      return {
        rAF_data: window.benchmark_rAF_data || [],
        raw_mutations: window.benchmark_raw_mutations || [],
        transitions: window.benchmark_transitions || [],
        focus_visibility_log: window.benchmark_focus_visibility_log || [],
        events: window.benchmark_events || [],
        board_geometry_samples: window.benchmark_board_geometry_samples || [],
        board_left_viewport: window.benchmark_board_left_viewport || false
      };
    });

    const browserVersion = await browser.version();

    // Capture visual snapshot at completion
    const screenshotPath = path.join(runDir, `trial-${trialNum}-screenshot.png`);
    await page.screenshot({ path: screenshotPath });

    // Stop Playwright Tracing
    const tracePath = path.join(runDir, `trial-${trialNum}-trace.zip`);
    await context.tracing.stop({ path: tracePath });

    // Close browser & context
    await context.close();
    await browser.close();
    browser = null;
    page = null;
    context = null;

    // --- CALCULATIONS & STATS ---

    // Final measured DOM count = sum raw callback counts within [measureStart, measureEnd] (defect 3)
    const measuredDOMcount = benchmarkData.raw_mutations
      .filter(m => m.timestamp >= measureStartPage && m.timestamp <= measureEndPage)
      .reduce((sum, m) => sum + m.mutationCount, 0);

    // Final measured transitions count similarly (defect 3)
    const measuredTransitionCount = benchmarkData.transitions
      .filter(t => t.timestamp >= measureStartPage && t.timestamp <= measureEndPage).length;

    // Period totals clearly named, not reported as "measured" (defect 3)
    const totalDOMcountAllPeriods = benchmarkData.raw_mutations.reduce((sum, m) => sum + m.mutationCount, 0);
    const totalTransitionCountAllPeriods = benchmarkData.transitions.length;

    // Filter ONLY positive frame pairs wholly inside [measureStartPage, measureEndPage] (defect 1)
    const eligibleFrames = benchmarkData.rAF_data.filter(([prev, curr, delta]) => {
      return prev >= measureStartPage && curr <= measureEndPage && delta > 0;
    });

    const frameIntervals = eligibleFrames.map(item => item[2]);
    // FPS calculated exactly with denominator 30000ms (defect 1)
    const approximateFPS = eligibleFrames.length * 1000 / 30000;

    const sortedIntervals = [...frameIntervals].sort((a, b) => a - b);
    const median = getPercentile(sortedIntervals, 0.50);
    const p95 = getPercentile(sortedIntervals, 0.95);
    const p99 = getPercentile(sortedIntervals, 0.99);
    const janksCount = frameIntervals.filter(delta => delta > 33.34).length;

    // Filter action latency to actions AND visible updates wholly inside [measureStart, measureEnd] (defect 4)
    const validLatencies = actionSamples.filter(s => {
      const insideBounds = s.actionStartPage >= measureStartPage && s.visibleTime !== null && s.visibleTime <= measureEndPage;
      return s.status === 'success' && insideBounds && s.latency !== null && s.latency >= 0;
    }).map(s => s.latency);

    const meanActionLatency = validLatencies.length > 0 ? (validLatencies.reduce((a, b) => a + b, 0) / validLatencies.length) : null;

    // 6. Save FULL raw payload BEFORE validation throw (defect 6)
    const rawFilename = `trial-${trialNum}-raw.json`;
    const rawPath = path.join(runDir, rawFilename);
    const rawPayload = {
      trial: trialNum,
      success: true,
      restarts: restartCount,
      restartsList,
      timelinePage: {
        warmupStart: warmupStartPage,
        warmupEnd: warmupEndPage,
        measureStart: measureStartPage,
        measureEnd: measureEndPage,
        observedStop: observedStopPage,
        observedWarmupStart: observedWarmupStartPage,
        observedWarmupEnd: observedWarmupEndPage,
        observedMeasureStart: observedMeasureStartPage,
        observedMeasureEnd: observedMeasureEndPage,
        overshootExplanation: "Due to scheduling jitter, event loop delays, and Playwright keyboard execution overhead, the actual action loop inevitably overshoots the declared 30000ms window. We preserve the separate observed stops and starts for audit but strictly filter eligible frames and actions to the declared bounds."
      },
      focus_snapshots: {
        init: initSnapshot,
        warmupStart: warmupStartSnapshot,
        measureStart: measureStartSnapshot,
        stop: stopSnapshot
      },
      raw_mutations: benchmarkData.raw_mutations,
      rAF_all_pairs: benchmarkData.rAF_data,
      rAF_eligible_pairs: eligibleFrames,
      dom_updates_measured: measuredDOMcount,
      transitions_measured: measuredTransitionCount,
      total_dom_updates_all_periods: totalDOMcountAllPeriods,
      total_transitions_all_periods: totalTransitionCountAllPeriods,
      focus_visibility_log: benchmarkData.focus_visibility_log,
      focus_events: benchmarkData.events,
      transitions: benchmarkData.transitions,
      action_samples: actionSamples,
      api_calls: Array.from(apiRequests.values()),
      board_geometry_samples: benchmarkData.board_geometry_samples,
      board_left_viewport: benchmarkData.board_left_viewport
    };
    fs.writeFileSync(rawPath, JSON.stringify(rawPayload, null, 2));

    // --- PRECONDITION VALIDATIONS (defect 6) ---

    // 1. Require visible / foreground during measurement
    if (!measureStartSnapshot.focused || !measureStartSnapshot.visible) {
      throw new Error('Precondition Failure: Page was not focused or visible at the start of measurement window.');
    }
    if (!stopSnapshot.focused || !stopSnapshot.visible) {
      throw new Error('Precondition Failure: Page was not focused or visible at the stop of measurement window.');
    }
    const lostFocusDuringMeasurement = benchmarkData.focus_visibility_log
      .filter(s => s.time >= measureStartPage && s.time <= measureEndPage)
      .some(s => !s.focused || !s.visible);

    const eventFailureDuringMeasurement = benchmarkData.events
      .filter(ev => ev.timestamp >= measureStartPage && ev.timestamp <= measureEndPage)
      .some(ev => ev.type === 'blur' || (ev.type === 'visibilitychange' && ev.value !== 'visible'));

    if (lostFocusDuringMeasurement || eventFailureDuringMeasurement) {
      throw new Error('Precondition Failure: Visual foreground focus or visibility was lost inside the 30-second measurement window.');
    }

    // 2. Non-empty eligible frame intervals
    if (frameIntervals.length === 0) {
      throw new Error('Precondition Failure: Eligible frame intervals dataset is empty.');
    }

    // 3. Measured DOM transitions count > 0
    if (measuredTransitionCount === 0) {
      throw new Error('Precondition Failure: Measured DOM board transitions count within interval is 0.');
    }

    // 4. Actual three-direction gameplay with successful API 200 latency samples
    const successfulDirections = new Set(actionSamples.filter(s => {
      const insideBounds = s.actionStartPage >= measureStartPage && s.visibleTime !== null && s.visibleTime <= measureEndPage;
      return s.status === 'success' && insideBounds;
    }).map(s => s.direction));

    if (!successfulDirections.has('left') || !successfulDirections.has('right') || !successfulDirections.has('down')) {
      throw new Error('Precondition Failure: Missing successful latency samples (status success, API response 200) wholly inside measurement window for all 3 directions (left, right, down).');
    }

    // 5. Board geometry & viewport validations
    const measuredGeometrySamples = benchmarkData.board_geometry_samples.filter(s => {
      return s.timestamp >= measureStartPage && s.timestamp <= measureEndPage;
    });

    const periodicSamples = measuredGeometrySamples.filter(s => s.context === 'periodic');
    const actionDOMSamples = measuredGeometrySamples.filter(s => s.context === 'mutation' || s.context === 'action-dispatch');

    if (benchmarkData.board_left_viewport) {
      throw new Error('Precondition Failure: The .board element left the fully visible 1280x900 viewport during the measured window.');
    }

    const failedGeometrySample = measuredGeometrySamples.find(s => !s.withinViewport || !s.hasFocus);
    if (failedGeometrySample) {
      throw new Error(`Precondition Failure: Board geometry sample failed viewport or focus check within measured window. Context: ${failedGeometrySample.context}, timestamp: ${failedGeometrySample.timestamp}, withinViewport: ${failedGeometrySample.withinViewport}, hasFocus: ${failedGeometrySample.hasFocus}`);
    }

    if (periodicSamples.length === 0) {
      throw new Error('Precondition Failure: Measured periodic geometry samples are empty inside the measurement window.');
    }

    if (actionDOMSamples.length === 0) {
      throw new Error('Precondition Failure: Measured action/DOM geometry samples are empty inside the measurement window.');
    }

    if (apiRequests.size === 0) {
      throw new Error('Precondition Failure: No API calls were recorded during the gameplay.');
    }

    console.log(`Trial ${trialNum} Complete:`);
    console.log(`  - approximateFPS: ${approximateFPS.toFixed(2)} FPS`);
    console.log(`  - median: ${median.toFixed(2)} ms`);
    console.log(`  - p95: ${p95.toFixed(2)} ms`);
    console.log(`  - janks (>33.34ms): ${janksCount}`);
    console.log(`  - restarts: ${restartCount}`);
    console.log(`  - measuredDOMcount: ${measuredDOMcount}`);
    console.log(`  - measuredTransitionCount: ${measuredTransitionCount}`);
    console.log(`  - meanActionLatency: ${meanActionLatency ? meanActionLatency.toFixed(2) + ' ms' : 'N/A'}`);
    console.log(`  - boardGeometryQualification: passed (total samples: ${measuredGeometrySamples.length}, periodic: ${periodicSamples.length}, action/DOM: ${actionDOMSamples.length})`);

    return {
      success: true,
      trial: trialNum,
      approximateFPS,
      median,
      p95,
      p99,
      janksCount,
      domUpdates: measuredDOMcount,
      transitionsMeasured: measuredTransitionCount,
      meanActionLatency,
      restarts: restartCount,
      rawPath,
      screenshotPath,
      tracePath,
      browserVersion,
      boardGeometrySamplesCount: measuredGeometrySamples.length,
      periodicSamplesCount: periodicSamples.length,
      actionDOMSamplesCount: actionDOMSamples.length,
      boardGeometryQualification: 'passed'
    };

  } catch (err) {
    console.error(`Error during Trial ${trialNum}:`, err);
    
    // On error, collect whatever page arrays are still available safely (defect 6)
    let partialTelemetry = {};
    if (page) {
      try {
        partialTelemetry = await page.evaluate(() => {
          return {
            rAF_data: window.benchmark_rAF_data || [],
            raw_mutations: window.benchmark_raw_mutations || [],
            transitions: window.benchmark_transitions || [],
            focus_visibility_log: window.benchmark_focus_visibility_log || [],
            events: window.benchmark_events || [],
            board_geometry_samples: window.benchmark_board_geometry_samples || [],
            board_left_viewport: window.benchmark_board_left_viewport || false
          };
        }).catch(() => ({}));
      } catch (_) {}
    }

    // Save FULL raw telemetry and error JSON on failure before closing context/browser (defect 6)
    try {
      const failedRawPath = path.join(runDir, `trial-${trialNum}-failed-raw.json`);
      fs.writeFileSync(failedRawPath, JSON.stringify({
        trial: trialNum,
        success: false,
        error: err.message,
        stack: err.stack,
        restarts: restartCount,
        restartsList,
        timelinePage: {
          warmupStart: typeof warmupStartPage !== 'undefined' ? warmupStartPage : null,
          warmupEnd: typeof warmupEndPage !== 'undefined' ? warmupEndPage : null,
          measureStart: typeof measureStartPage !== 'undefined' ? measureStartPage : null,
          measureEnd: typeof measureEndPage !== 'undefined' ? measureEndPage : null,
          observedStop: typeof observedStopPage !== 'undefined' ? observedStopPage : null
        },
        focus_snapshots: {
          init: typeof initSnapshot !== 'undefined' ? initSnapshot : null,
          warmupStart: typeof warmupStartSnapshot !== 'undefined' ? warmupStartSnapshot : null,
          measureStart: typeof measureStartSnapshot !== 'undefined' ? measureStartSnapshot : null,
          stop: typeof stopSnapshot !== 'undefined' ? stopSnapshot : null
        },
        raw_mutations: partialTelemetry.raw_mutations || [],
        partialTelemetry,
        api_calls: Array.from(apiRequests.values()),
        action_samples: actionSamples,
        board_geometry_samples: partialTelemetry.board_geometry_samples || [],
        board_left_viewport: partialTelemetry.board_left_viewport || false
      }, null, 2));
    } catch (writeErr) {
      console.error('Failed to write failed-raw telemetry file:', writeErr);
    }

    return {
      success: false,
      trial: trialNum,
      error: err.message
    };
  } finally {
    // Graceful closing
    if (context) {
      try {
        const tracePath = path.join(runDir, `trial-${trialNum}-failed-trace.zip`);
        await context.tracing.stop({ path: tracePath }).catch(() => {});
      } catch (_) {}
      try {
        await context.close().catch(() => {});
      } catch (_) {}
    }
    if (browser) {
      try {
        await browser.close().catch(() => {});
      } catch (_) {}
    }
  }
}

async function run() {
  console.log('================================================================');
  console.log('TETRIS STAGE 3 BROWSER PERFORMANCE BENCHMARK (CORRECTED)');
  console.log('================================================================');
  
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const runDir = path.join(OUTPUT_DIR_BASE, `run-${timestamp}`);
  fs.mkdirSync(runDir, { recursive: true });

  console.log(`Saving immutable results to: ${runDir}\n`);

  // Read actual Playwright and Playwright Core versions from installed packages (defect 5)
  let playwrightVersion = '1.64.1';
  let playwrightCoreVersion = '1.64.1';
  try {
    const pkgPath = path.resolve('node_modules/playwright/package.json');
    if (fs.existsSync(pkgPath)) {
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      playwrightVersion = pkg.version;
    }
    const corePkgPath = path.resolve('node_modules/playwright-core/package.json');
    if (fs.existsSync(corePkgPath)) {
      const pkg = JSON.parse(fs.readFileSync(corePkgPath, 'utf8'));
      playwrightCoreVersion = pkg.version;
    }
  } catch (err) {
    console.warn('Could not dynamically read installed playwright versions, falling back to package.json defaults:', err.message);
  }

  // OS information & true versions + complete hardware metadata (defect 5)
  const metadata = {
    benchmark_time: new Date().toISOString(),
    os: {
      platform: os.platform(),
      release: os.release(),
      type: os.type(),
      arch: os.arch()
    },
    hardware: {
      cpu: os.cpus()[0]?.model || 'Unknown',
      ram_gb: (os.totalmem() / 1024 / 1024 / 1024).toFixed(2),
      gpu: 'Unsupported/Headed sandbox limit (Playwright Chromium standard environment)',
      display: 'Unsupported/Physical presentation limit (60 Hz target browser frame scheduling)'
    },
    versions: {
      node: process.version,
      playwright: playwrightVersion,
      playwright_core: playwrightCoreVersion
    },
    launch_configuration: {
      channel: 'chrome',
      headless: false,
      chromiumSandbox: true
    },
    config: {
      app_url: APP_URL,
      trials: TRIALS,
      warmup_ms: WARMUP_MS,
      measure_ms: MEASURE_MS,
      target_fps: 60,
      viewport: { width: 1280, height: 900, deviceScaleFactor: 1 },
      scenario: 'Standard 120ms action interval pacing with 130ms modest post-action delay',
      quantile_linear_interpolation: true
    }
  };

  const results = [];
  let executionFailed = false;

  for (let i = 1; i <= TRIALS; i++) {
    const res = await runTrial(i, runDir);
    results.push(res);
    if (!res.success) {
      executionFailed = true;
    }
  }

  // Generate final summary report
  const summary = {
    metadata,
    trials: results,
    overall_status: 'failed'
  };

  console.log('\n================================================================');
  console.log('BENCHMARK SUMMARY REPORT');
  console.log('================================================================');

  if (executionFailed) {
    console.log('⚠️  One or more benchmark trials failed to execute successfully.');
  } else {
    // Evaluate operational targets PER TRIAL
    // Targets: approximateFPS >= 55 AND p95 <= 25ms in EVERY TRIAL
    let targetsPassed = true;
    results.forEach(r => {
      const fpsPassed = r.approximateFPS >= 55;
      const p95Passed = r.p95 <= 25;
      const trialPassed = fpsPassed && p95Passed;

      console.log(`Trial ${r.trial}:`);
      console.log(`  - approximateFPS: ${r.approximateFPS.toFixed(2)} FPS ${fpsPassed ? '✅' : '❌ (Target >= 55 FPS)'}`);
      console.log(`  - p95 Frame Interval: ${r.p95.toFixed(2)} ms ${p95Passed ? '✅' : '❌ (Target <= 25 ms)'}`);
      console.log(`  - median: ${r.median.toFixed(2)} ms`);
      console.log(`  - janks (>33.34ms): ${r.janksCount}`);
      console.log(`  - DOM Updates count (measured): ${r.domUpdates}`);
      console.log(`  - Board Transitions count (measured): ${r.transitionsMeasured}`);
      console.log(`  - Mean Action Latency: ${r.meanActionLatency ? r.meanActionLatency.toFixed(2) + ' ms' : 'N/A'}`);
      console.log(`  - Restarts: ${r.restarts}`);
      console.log(`  - Board Geometry Qualification: ${r.boardGeometryQualification || 'passed'} (Samples: ${r.boardGeometrySamplesCount || 0}, Periodic: ${r.periodicSamplesCount || 0}, Action/DOM: ${r.actionDOMSamplesCount || 0})`);

      if (!trialPassed) {
        targetsPassed = false;
      }
    });

    summary.overall_status = targetsPassed ? 'passed' : 'failed';

    console.log('\n----------------------------------------------------------------');
    console.log('OPERATIONAL TARGET PERFORMANCE EVALUATION:');
    if (targetsPassed) {
      console.log('🎉 ALL TRIALS PASSED TARGETS (>=55 FPS AND p95 <= 25 ms)');
    } else {
      console.log('❌ ONE OR MORE TRIALS FAILED OPERATIONAL TARGETS.');
    }
    console.log('This target represents frame scheduling rates in browser loop context, not a physical monitor refresh guarantee.');
    console.log('----------------------------------------------------------------');
  }

  // Persist final JSON summary report
  const reportPath = path.join(runDir, 'benchmark-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(summary, null, 2));
  console.log(`Final report written to: ${reportPath}`);

  // Exit with non-zero code if any execution failed or any trial did not meet targets
  if (executionFailed || summary.overall_status === 'failed') {
    process.exit(1);
  } else {
    process.exit(0);
  }
}

run().catch(err => {
  console.error('Fatal benchmark execution failure:', err);
  process.exit(1);
});
