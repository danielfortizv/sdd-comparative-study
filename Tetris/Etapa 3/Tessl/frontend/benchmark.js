import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const TARGET_URL = 'http://127.0.0.1:5183';
const WARMUP_MS = 5000;
const MEASURE_MS = 30000;
const OUTPUT_DIR = path.resolve('benchmark-results');

// Generate unique directory name with timestamp and nonce to refuse collisions
const timestampStr = new Date().toISOString().replace(/[:.]/g, '-');
const nonceStr = Math.random().toString(36).substring(2, 8);
const RUN_DIR_NAME = `run_${timestampStr}_${nonceStr}`;
const RUN_DIR_PATH = path.join(OUTPUT_DIR, RUN_DIR_NAME);

// Helper to run shell commands safely
function runCmd(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf-8', stdio: 'pipe' }).trim();
  } catch (err) {
    return null;
  }
}

// Explicit percentile calculation: Linear interpolation between closest ranks.
// For a sorted array 'arr' and percentile 'p' (0 to 1):
// Index is calculated as (arr.length - 1) * p.
// The value is the weighted average of the elements at floor(index) and ceil(index).
function getPercentile(arr, p) {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const index = (sorted.length - 1) * p;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

// Collect Host Specs
const osType = process.platform;
const nodeVersion = process.version;

let cpuName = 'Unknown (Error querying via PowerShell)';
let gpuName = 'Unknown (Error querying via PowerShell)';
let displayRefreshRate = 'Unknown (Error querying via PowerShell)';

try {
  const cpuResult = runCmd('powershell.exe -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"');
  if (cpuResult) cpuName = cpuResult;
} catch (err) {
  cpuName = `Unknown (Exception: ${err.message})`;
}

try {
  const gpuResult = runCmd('powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"');
  if (gpuResult) gpuName = gpuResult;
} catch (err) {
  gpuName = `Unknown (Exception: ${err.message})`;
}

try {
  const refreshResult = runCmd('powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty CurrentRefreshRate"');
  if (refreshResult) displayRefreshRate = refreshResult;
} catch (err) {
  displayRefreshRate = `Unknown (Exception: ${err.message})`;
}

const hostSpecs = {
  os: osType,
  node: nodeVersion,
  cpu: cpuName,
  gpu: gpuName,
  display_refresh_rate: displayRefreshRate
};

console.log('Host specs captured:', hostSpecs);

async function runTrial(browser, trialNum) {
  console.log(`\n=== Starting Trial ${trialNum} ===`);
  
  // Fresh browser context and page per trial
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 1
  });

  // Start Playwright context-level tracing with screenshots, snapshots, and sources
  await context.tracing.start({
    screenshots: true,
    snapshots: true,
    sources: true
  });

  const page = await context.newPage();

  // Capture network request/response timings
  const networkEvents = [];
  page.on('request', request => {
    networkEvents.push({
      time: Date.now(),
      type: 'request',
      url: request.url(),
      method: request.method()
    });
  });

  page.on('requestfinished', request => {
    const timing = request.timing();
    networkEvents.push({
      time: Date.now(),
      type: 'requestfinished',
      url: request.url(),
      method: request.method(),
      timing: timing
    });
  });

  page.on('requestfailed', request => {
    networkEvents.push({
      time: Date.now(),
      type: 'requestfailed',
      url: request.url(),
      method: request.method(),
      failure: request.failure()
    });
  });

  // Track manual/auto API response bodies
  const apiResponses = [];
  page.on('response', async response => {
    const url = response.url();
    const method = response.request().method();
    if (url.includes('/api/') && method === 'POST') {
      try {
        const status = response.status();
        const json = await response.json().catch(() => null);
        apiResponses.push({
          time: await page.evaluate(() => performance.now()),
          url: url,
          status: status,
          body: json
        });
      } catch (err) {
        // Ignored
      }
    }
  });

  // Navigate to production app
  await page.goto(TARGET_URL);
  await page.waitForTimeout(1000); // Wait for page to initialize

  // Bring to front to ensure true active visibility and focus state
  await page.bringToFront();
  
  // Verify initial visibility and focus snapshots
  const initialFocus = await page.evaluate(() => document.hasFocus());
  const initialVisibility = await page.evaluate(() => document.visibilityState);
  console.log(`[Trial ${trialNum}] Focus: ${initialFocus}, Visibility: ${initialVisibility}`);

  // Inject metric-tracking hooks before initiating warmup
  await page.evaluate(({ warmupMs, measureMs }) => {
    window.warmupStart = performance.now();
    window.warmupEnd = window.warmupStart + warmupMs;
    window.measureStart = window.warmupEnd;
    window.measureEnd = window.measureStart + measureMs;

    window.rafTimestamps = [];
    window.domMutations = [];
    window.actions = [];
    window.actionLatencies = [];
    window.focusSnapshots = [];
    window.visibilitySnapshots = [];
    window.focusEvents = [];
    window.visibilityEvents = [];
    
    window.recordSnapshot = (label) => {
      const now = performance.now();
      window.focusSnapshots.push({ event: label, time: now, hasFocus: document.hasFocus() });
      window.visibilitySnapshots.push({ event: label, time: now, state: document.visibilityState });
    };
    
    window.recordSnapshot('init');

    // Track rAF callback intervals continuously
    function rafCallback(timestamp) {
      window.rafTimestamps.push({
        callback_time: performance.now(),
        frame_time: timestamp
      });
      window.rafLoopId = requestAnimationFrame(rafCallback);
    }
    window.rafLoopId = requestAnimationFrame(rafCallback);

    // Track DOM mutations inside the main container
    window.domObserver = new MutationObserver((mutations) => {
      const now = performance.now();
      window.domMutations.push({
        time: now,
        mutationCount: mutations.length
      });
    });
    const root = document.getElementById('root');
    if (root) {
      window.domObserver.observe(root, {
        childList: true,
        subtree: true,
        attributes: true
      });
    }

    // Monitor action-to-render latencies on keypress
    window.addEventListener('keydown', (e) => {
      const start = performance.now();
      window.actions.push({
        time: start,
        key: e.key
      });
      
      const obs = new MutationObserver((mutations) => {
        const mutationTime = performance.now();
        window.actionLatencies.push({
          actionTime: start,
          mutationTime: mutationTime,
          latency: mutationTime - start,
          key: e.key,
          mutationCount: mutations.length
        });
        obs.disconnect();
      });
      const target = document.getElementById('root');
      if (target) {
        obs.observe(target, { childList: true, subtree: true, attributes: true });
      }
    });

    // Capture true focus/visibility transition events
    window.addEventListener('focus', () => {
      window.focusEvents.push({ time: performance.now(), event: 'focus', hasFocus: document.hasFocus() });
    });
    window.addEventListener('blur', () => {
      window.focusEvents.push({ time: performance.now(), event: 'blur', hasFocus: document.hasFocus() });
    });
    document.addEventListener('visibilitychange', () => {
      window.visibilityEvents.push({ time: performance.now(), event: 'visibilitychange', state: document.visibilityState });
    });
  }, { warmupMs: WARMUP_MS, measureMs: MEASURE_MS });

  // Restart game initially to guarantee a completely fresh game session at the start of trial
  const restartButton = page.locator('.btn-restart');
  if (await restartButton.isVisible()) {
    await restartButton.click();
    await page.waitForTimeout(500);
  }

  // Retrieve the fixed in-page bounds
  const startBounds = await page.evaluate(() => {
    window.warmupStart = performance.now();
    window.warmupEnd = window.warmupStart + 5000;
    window.measureStart = window.warmupEnd;
    window.measureEnd = window.measureStart + 30000;
    window.recordSnapshot('warmup_start');
    return {
      warmupStart: window.warmupStart,
      warmupEnd: window.warmupEnd,
      measureStart: window.measureStart,
      measureEnd: window.measureEnd
    };
  });

  // 1. Warmup Phase (exactly 5000ms inside the page clock domain)
  console.log(`[Trial ${trialNum}] Warmup starting (in-page bounds: [${startBounds.warmupStart.toFixed(1)}ms, ${startBounds.warmupEnd.toFixed(1)}ms])...`);
  let warmupActive = true;
  let lastInputTime = 0;
  while (warmupActive) {
    const elapsed = await page.evaluate(() => performance.now() - window.warmupStart);
    if (elapsed >= WARMUP_MS) {
      warmupActive = false;
      break;
    }
    // Simulate soft-drop periodically during warmup
    if (elapsed - lastInputTime > 200) {
      await page.keyboard.press('ArrowDown');
      lastInputTime = elapsed;
    }
    await page.waitForTimeout(30);
  }

  // Warmup Boundary Snapshot
  await page.evaluate(() => window.recordSnapshot('measure_start'));

  // 2. Monotonic Measurement Phase (exactly 30000ms inside the page clock domain)
  console.log(`[Trial ${trialNum}] Measurement starting (in-page bounds: [${startBounds.measureStart.toFixed(1)}ms, ${startBounds.measureEnd.toFixed(1)}ms])...`);
  let measureActive = true;
  let actionCount = 0;
  lastInputTime = 0;
  while (measureActive) {
    const elapsed = await page.evaluate(() => performance.now() - window.warmupStart);
    const measureElapsed = elapsed - WARMUP_MS;
    if (measureElapsed >= MEASURE_MS) {
      measureActive = false;
      break;
    }

    // Dispatch alternating Left, Right, and Soft-drop actions at a human rate (approx 6.7 Hz)
    if (measureElapsed - lastInputTime > 150) {
      const keys = ['ArrowLeft', 'ArrowRight', 'ArrowDown'];
      const key = keys[actionCount % keys.length];
      await page.keyboard.press(key);
      actionCount++;
      lastInputTime = measureElapsed;
    }

    // Automatically trigger restart/new-game if the game ends to maintain active gameplay
    const isGameOver = await page.evaluate(() => {
      const banner = document.querySelector('.game-over-banner');
      return !!banner;
    });
    if (isGameOver) {
      console.log(`[Trial ${trialNum}] Game over detected. Clicking restart button...`);
      const restartBtn = page.locator('.btn-restart');
      if (await restartBtn.isVisible()) {
        await restartBtn.click();
        await page.waitForTimeout(300);
      }
    }

    await page.waitForTimeout(30);
  }

  // End Snapshot
  await page.evaluate(() => window.recordSnapshot('end'));

  // Capture genuine finished screenshot
  const screenshotPath = path.join(RUN_DIR_PATH, `trial-${trialNum}-screenshot.png`);
  await page.screenshot({ path: screenshotPath });

  // Retrieve raw metrics from page context
  const pageData = await page.evaluate(() => {
    if (window.domObserver) window.domObserver.disconnect();
    cancelAnimationFrame(window.rafLoopId);

    return {
      rafTimestamps: window.rafTimestamps,
      domMutations: window.domMutations,
      actions: window.actions,
      actionLatencies: window.actionLatencies,
      focusSnapshots: window.focusSnapshots,
      visibilitySnapshots: window.visibilitySnapshots,
      focusEvents: window.focusEvents,
      visibilityEvents: window.visibilityEvents
    };
  });

  // Stop Playwright tracing and save trace file
  const tracePath = path.join(RUN_DIR_PATH, `trial-${trialNum}-trace.zip`);
  await context.tracing.stop({ path: tracePath });
  await context.close();

  // Post-process metrics
  const rafSamples = pageData.rafTimestamps;
  const intervals = [];
  for (let i = 1; i < rafSamples.length; i++) {
    const t_prev = rafSamples[i - 1].callback_time;
    const t_curr = rafSamples[i].callback_time;
    const diff = t_curr - t_prev;
    intervals.push({ t_prev, t_curr, diff });
  }

  // Mathematical classification of every interval
  const classifiedIntervals = intervals.map(item => {
    let classification = '';
    if (item.diff <= 0) {
      classification = 'nonpositive';
    } else if (item.t_curr <= startBounds.warmupStart) {
      classification = 'pre-window';
    } else if (item.t_prev < startBounds.warmupStart && item.t_curr > startBounds.warmupStart) {
      classification = 'cross-boundary-pre-to-warmup';
    } else if (item.t_curr <= startBounds.warmupEnd) {
      classification = 'warmup';
    } else if (item.t_prev >= startBounds.measureStart && item.t_curr <= startBounds.measureEnd) {
      classification = 'eligible';
    } else if (item.t_prev < startBounds.measureStart && item.t_curr >= startBounds.measureStart) {
      classification = 'cross-boundary-warmup-to-measure';
    } else if (item.t_prev <= startBounds.measureEnd && item.t_curr > startBounds.measureEnd) {
      classification = 'cross-boundary-measure-to-post';
    } else if (item.t_prev >= startBounds.measureEnd) {
      classification = 'post-window';
    } else {
      classification = 'other';
    }
    return { ...item, classification };
  });

  const classificationCounts = {};
  classifiedIntervals.forEach(x => {
    classificationCounts[x.classification] = (classificationCounts[x.classification] || 0) + 1;
  });

  // Retain eligible intervals inside the measured 30-second window
  const eligibleIntervals = classifiedIntervals.filter(x => x.classification === 'eligible').map(x => x.diff);
  const totalDurationSeconds = MEASURE_MS / 1000;
  const approxFPS = eligibleIntervals.length / totalDurationSeconds;

  // Frame drops / janky frames (> 33.34ms)
  const jankyFrames = eligibleIntervals.filter(x => x > 33.34).length;

  // Calculate percentiles from eligible intervals
  const medianInterval = getPercentile(eligibleIntervals, 0.5);
  const p95Interval = getPercentile(eligibleIntervals, 0.95);
  const p99Interval = getPercentile(eligibleIntervals, 0.99);

  // Scoped DOM mutations
  const eligibleMutations = pageData.domMutations.filter(m => m.time >= startBounds.measureStart && m.time <= startBounds.measureEnd);
  const totalDomMutations = eligibleMutations.reduce((sum, m) => sum + m.mutationCount, 0);

  // Scoped Actions
  const eligibleActions = pageData.actions.filter(a => a.time >= startBounds.measureStart && a.time <= startBounds.measureEnd);

  // Scoped Action Latencies (Heuristic)
  const eligibleLatencies = pageData.actionLatencies.filter(al => al.actionTime >= startBounds.measureStart && al.actionTime <= startBounds.measureEnd).map(al => al.latency);
  const medianLatency = getPercentile(eligibleLatencies, 0.5);

  const stats = {
    trial: trialNum,
    bounds: {
      warmup_start: startBounds.warmupStart,
      warmup_end: startBounds.warmupEnd,
      measure_start: startBounds.measureStart,
      measure_end: startBounds.measureEnd
    },
    focus_snapshots: pageData.focusSnapshots,
    visibility_snapshots: pageData.visibilitySnapshots,
    focus_events: pageData.focusEvents,
    visibility_events: pageData.visibilityEvents,
    network_events_count: networkEvents.length,
    api_responses_count: apiResponses.length,
    summary: {
      rAF_total_recorded: rafSamples.length,
      eligible_interval_count: eligibleIntervals.length,
      classification_counts: classificationCounts,
      approx_FPS: approxFPS,
      intervals_ms: {
        median: parseFloat(medianInterval.toFixed(2)),
        p95: parseFloat(p95Interval.toFixed(2)),
        p99: parseFloat(p99Interval.toFixed(2))
      },
      janky_frames_above_33_34ms: jankyFrames,
      measured_dom_mutations: totalDomMutations,
      measured_actions: eligibleActions.length,
      action_latency_ms: {
        median: parseFloat(medianLatency.toFixed(2)),
        samples: eligibleLatencies.length
      }
    },
    raw_data: {
      rAF_timestamps: rafSamples,
      rAF_intervals: classifiedIntervals,
      dom_mutations: pageData.domMutations,
      actions: pageData.actions,
      action_latencies: pageData.actionLatencies,
      network_events: networkEvents,
      api_responses: apiResponses
    }
  };

  console.log(`[Trial ${trialNum}] Done. FPS: ${approxFPS.toFixed(2)}, p95 Interval: ${p95Interval.toFixed(2)}ms, DOM Mutations: ${totalDomMutations}`);
  return stats;
}

async function main() {
  console.log('=== Launching Tetris Stage 3 Performance Benchmark (Headed & Sandboxed) ===');
  console.log(`Working Directory: ${process.cwd()}`);
  console.log(`Writing results to: ${RUN_DIR_PATH}`);

  // Ensure parent output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  // Create the new timestamp+nonce batch directory exclusively/non-recursively (fail on collision)
  if (fs.existsSync(RUN_DIR_PATH)) {
    throw new Error(`Collision detected: Batch directory ${RUN_DIR_PATH} already exists!`);
  }
  fs.mkdirSync(RUN_DIR_PATH, { recursive: false });

  // Launch Playwright Chrome in foreground mode with sandbox enabled (NO --no-sandbox args)
  console.log('Launching installed Chrome via Playwright (channel: chrome, headless: false, chromiumSandbox: true)...');
  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome',
    chromiumSandbox: true
  });

  // Capture the actual SAME measured browser.version() before closing
  const browser_version = await browser.version();

  const results = [];
  try {
    for (let t = 1; t <= 3; t++) {
      const res = await runTrial(browser, t);
      results.push(res);
    }
  } catch (err) {
    console.error('Error during benchmark trials execution:', err);
  } finally {
    await browser.close();
    console.log('Playwright browser session closed. Note: production Docker container stack is kept running on port 5183.');
  }

  // Write final report containing precise raw JSON details
  const report = {
    timestamp: new Date().toISOString(),
    browser_version: browser_version,
    host: {
      ...hostSpecs,
      display_refresh_rate_label: `${hostSpecs.display_refresh_rate}Hz (OS-reported configuration, not proof of physical presentation)`
    },
    target: TARGET_URL,
    launch_configuration: {
      headless: false,
      channel: 'chrome',
      chromiumSandbox: true
    },
    trials: results
  };

  const reportPath = path.join(RUN_DIR_PATH, 'performance-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8');
  console.log(`\n=== Complete Raw & Summary JSON Saved to ${reportPath} ===`);

  // Log final summaries to console
  results.forEach(trial => {
    console.log(`\nTrial ${trial.trial} Summary:`);
    console.log(`  - Target display reference: 60Hz (Reference target for timing tolerance, not a guarantee of physical display presentation)`);
    console.log(`  - OS-reported configuration: ${hostSpecs.display_refresh_rate}Hz (OS-reported configuration, not proof of physical presentation)`);
    console.log(`  - Approx FPS: ${trial.summary.approx_FPS.toFixed(2)} (Operational target >= 55 FPS)`);
    console.log(`  - Median Interval: ${trial.summary.intervals_ms.median}ms`);
    console.log(`  - p95 Interval: ${trial.summary.intervals_ms.p95}ms (Operational target <= 25ms)`);
    console.log(`  - p99 Interval: ${trial.summary.intervals_ms.p99}ms`);
    console.log(`  - Drops > 33.34ms: ${trial.summary.janky_frames_above_33_34ms}`);
    console.log(`  - DOM mutations: ${trial.summary.measured_dom_mutations}`);
    console.log(`  - Simulated keys dispatched: ${trial.summary.measured_actions}`);
    console.log(`  - Action latency (median): ${trial.summary.action_latency_ms.median}ms (samples: ${trial.summary.action_latency_ms.samples})`);
  });
}

main().catch(err => {
  console.error('Fatal error in benchmark runner script:', err);
});
