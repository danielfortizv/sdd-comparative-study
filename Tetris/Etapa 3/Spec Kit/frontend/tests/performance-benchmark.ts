import { chromium, Page, Browser, BrowserContext } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TARGET_URL = process.env.BENCHMARK_TARGET_URL || 'http://127.0.0.1:5183';
const EVIDENCE_DIR = path.resolve(__dirname, 'evidence');

interface RafEntry {
  intervalStart: number;
  intervalEnd: number;
  delta: number;
  timestamp: number;
  classification: string;
  reason: string;
}

interface ActionLatency {
  id: number;
  action: string;
  dispatchTime: number;
  visibleUpdateTime: number | null;
  latency: number | null;
  status: string;
  causality: string;
  classification: string;
  reason: string;
}

interface ApiTiming {
  url: string;
  method: string;
  duration: number;
  success: boolean;
  timestamp: number;
  status: number | string;
  classification: string;
  reason: string;
}

function ensureDirExists(dirPath: string) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function calculatePercentile(values: number[], percentile: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.ceil((percentile / 100) * sorted.length) - 1;
  return sorted[Math.max(0, index)];
}

async function runBenchmark() {
  console.log('==================================================');
  console.log('TETRIS STAGE 3 OPTION A: PERFORMANCE BENCHMARK (MONOTONIC WINDOW)');
  console.log('==================================================');

  // 1. Setup a unique attempt directory with UTC timestamp and random ID
  const nowWall = new Date();
  const runTimestamp = nowWall.toISOString().replace(/[:.]/g, '-').replace('T', '_').slice(0, 19);
  const randomId = Math.random().toString(36).substring(2, 10);
  const attemptDirName = `run_${runTimestamp}_${randomId}`;
  const ATTEMPT_DIR = path.resolve(EVIDENCE_DIR, attemptDirName);

  if (fs.existsSync(ATTEMPT_DIR)) {
    console.error(`Error: Destination directory already exists: ${ATTEMPT_DIR}`);
    process.exit(1);
  }
  ensureDirExists(ATTEMPT_DIR);
  console.log(`Created immutable attempt directory: ${ATTEMPT_DIR}`);

  // Record system environment details
  const envDetails = {
    os: `${os.platform()} ${os.release()} (${os.arch()})`,
    cpu: os.cpus()[0]?.model || 'Unknown CPU',
    memory: `${(os.totalmem() / (1024 ** 3)).toFixed(2)} GB`,
    runtime: `Node.js ${process.version}`,
    timestamp: nowWall.toISOString(),
    displayHzTarget: 60,
    launchContextConfig: {} as any,
  };

  console.log('System Environment:');
  console.log(`- OS: ${envDetails.os}`);
  console.log(`- CPU: ${envDetails.cpu}`);
  console.log(`- Memory: ${envDetails.memory}`);
  console.log(`- Runtime: ${envDetails.runtime}`);

  const results: any[] = [];
  let allRunsPassed = true;
  let browserVersion = 'Unknown';
  let selectedChannel = 'chrome';

  // Measurement Runs: 3 independent 30-second trials, each with its OWN 5-second warmup
  for (let runIndex = 1; runIndex <= 3; runIndex++) {
    console.log(`\n--- Run ${runIndex}: Starting independent trial ---`);

    let browser: Browser | null = null;
    let isHeadless = false;
    selectedChannel = 'chrome';

    try {
      console.log('Launching Chromium browser in headed foreground mode with sandbox...');
      browser = await chromium.launch({
        headless: false,
        channel: 'chrome',
        chromiumSandbox: true,
        args: [
          '--disable-renderer-backgrounding',
          '--disable-background-timer-throttling',
          '--disable-backgrounding-occluded-windows',
          '--force-device-scale-factor=1',
        ]
      });
    } catch (err: any) {
      console.warn(`Warning: Failed to launch official Chrome via channel 'chrome' (err: ${err.message}).`);
      console.log('Attempting to launch default bundled Chromium browser instead with sandbox...');
      try {
        selectedChannel = 'bundled-chromium';
        browser = await chromium.launch({
          headless: false,
          chromiumSandbox: true,
          args: [
            '--disable-renderer-backgrounding',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--force-device-scale-factor=1',
          ]
        });
      } catch (e2: any) {
        console.warn(`Warning: Failed to launch headed browser (err: ${e2.message}).`);
        console.log('Falling back to headless browser as permitted for unsupported environment logging with sandbox...');
        isHeadless = true;
        selectedChannel = 'headless-bundled';
        try {
          browser = await chromium.launch({
            headless: true,
            chromiumSandbox: true,
            args: [
              '--disable-renderer-backgrounding',
              '--disable-background-timer-throttling',
              '--disable-backgrounding-occluded-windows',
              '--force-device-scale-factor=1',
            ]
          });
        } catch (e3: any) {
          console.error('Fatal Error: Could not launch any browser instance.', e3.message);
          process.exit(1);
        }
      }
    }

    browserVersion = browser.version();
    console.log(`- Browser: Chromium/${browserVersion} (Channel: ${selectedChannel})`);
    console.log(`- Mode: ${isHeadless ? 'Headless' : 'Headed/Foreground (1280x900, deviceScaleFactor 1)'}`);

    const launchContextConfig = {
      headless: isHeadless,
      channel: selectedChannel,
      version: browserVersion,
      sandbox: true,
      viewport: { width: 1280, height: 900 },
      deviceScaleFactor: 1,
    };
    envDetails.launchContextConfig = launchContextConfig;

    const context = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      deviceScaleFactor: 1,
    });

    // Ensure trace collection is active for this run
    await context.tracing.start({ screenshots: true, snapshots: true });

    // Inject in-page performance monitoring scripts before load
    await context.addInitScript(() => {
      // Safeguard for esbuild/bundler global __name references
      (window as any).__name = (target: any, value: string) => {
        try {
          Object.defineProperty(target, 'name', { value, configurable: true });
        } catch (e) {}
        return target;
      };

      (window as any).__timeOrigin = performance.timeOrigin;
      (window as any).__timeOriginUnit = 'ms';
      (window as any).__pageClockUnit = 'ms';

      (window as any).__warmupStart = null;
      (window as any).__warmupEnd = null;
      (window as any).__warmupDeadline = null;
      (window as any).__measurementStart = null;
      (window as any).__declaredEnd = null;
      (window as any).__observedWarmupStop = null;
      (window as any).__observedStop = null;
      (window as any).__windowEnded = false;

      (window as any).__rafRecords = [];
      (window as any).__domMutations = [];
      (window as any).__actionDispatches = [];
      (window as any).__apiTimings = [];
      (window as any).__visibilityFocusEvents = [];
      (window as any).__pendingAction = null;
      (window as any).__benchmarkPhase = 'idle'; // 'idle', 'warmup', 'measurement', 'ended'

      // Independent measurement rAF loop (Owned by harness context, not app code)
      let lastTime = performance.now();
      function runRafMeasurement() {
        const now = performance.now();
        const delta = now - lastTime;
        const intervalStart = lastTime;
        const intervalEnd = now;
        lastTime = now;

        if ((window as any).__windowEnded) {
          return; // Buffers frozen!
        }

        // Automatically transition phase based on the pre-declared monotonic page clock
        const warmupStart = (window as any).__warmupStart;
        const warmupEnd = (window as any).__warmupEnd;
        const declaredEnd = (window as any).__declaredEnd;

        if (warmupStart !== null && warmupEnd !== null && declaredEnd !== null) {
          if (now < warmupStart) {
            (window as any).__benchmarkPhase = 'idle';
          } else if (now >= warmupStart && now < warmupEnd) {
            (window as any).__benchmarkPhase = 'warmup';
          } else if (now >= warmupEnd && now < declaredEnd) {
            if ((window as any).__benchmarkPhase === 'warmup') {
              (window as any).__observedWarmupStop = now;
              // Record measurement start snapshot
              (window as any).__visibilityFocusEvents.push({
                type: 'measurement_start_snapshot',
                state: {
                  visibility: document.visibilityState,
                  focus: document.hasFocus()
                },
                timestamp: now,
                wallTime: new Date().toISOString(),
                classification: 'within',
                reason: 'measurement_start_snapshot'
              });
            }
            (window as any).__benchmarkPhase = 'measurement';
          } else if (now >= declaredEnd) {
            if ((window as any).__benchmarkPhase === 'measurement') {
              (window as any).__observedStop = now;
              // Record measurement end snapshot
              (window as any).__visibilityFocusEvents.push({
                type: 'measurement_end_snapshot',
                state: {
                  visibility: document.visibilityState,
                  focus: document.hasFocus()
                },
                timestamp: now,
                wallTime: new Date().toISOString(),
                classification: 'after',
                reason: 'measurement_end_snapshot'
              });
            }
            (window as any).__benchmarkPhase = 'ended';
            (window as any).__windowEnded = true;
          }
        }

        const record: any = {
          intervalStart,
          intervalEnd,
          delta,
          timestamp: now,
          classification: 'idle',
          reason: 'before_warmup'
        };

        if (delta <= 0) {
          record.classification = 'zero_or_negative';
          record.reason = 'ineligible_non_positive_interval';
        } else if (warmupStart !== null && warmupEnd !== null && declaredEnd !== null) {
          if (intervalEnd <= warmupEnd) {
            record.classification = 'before';
            record.reason = 'warmup_or_before_window';
          } else if (intervalStart < warmupEnd && intervalEnd > warmupEnd) {
            record.classification = 'crossing_start';
            record.reason = 'crossing_start_boundary';
          } else if (intervalStart >= warmupEnd && intervalEnd <= declaredEnd) {
            record.classification = 'within';
            record.reason = 'within_measurement_window';
          } else if (intervalStart < declaredEnd && intervalEnd > declaredEnd) {
            record.classification = 'crossing_end';
            record.reason = 'crossing_end_boundary';
          } else if (intervalStart >= declaredEnd) {
            record.classification = 'after';
            record.reason = 'after_measurement_window';
          }
        }

        if (!(window as any).__windowEnded || record.classification === 'crossing_end' || record.classification === 'within') {
          (window as any).__rafRecords.push(record);
        }

        if (!(window as any).__windowEnded) {
          requestAnimationFrame(runRafMeasurement);
        }
      }
      requestAnimationFrame(runRafMeasurement);

      // MutationObserver hook with causality matching
      window.addEventListener('DOMContentLoaded', () => {
        const observer = new MutationObserver((mutations) => {
          if ((window as any).__windowEnded) return;
          const phase = (window as any).__benchmarkPhase;
          const now = performance.now();

          mutations.forEach(m => {
            const pending = (window as any).__pendingAction;
            const causality = pending ? `action_${pending.action}` : 'unknown';

            const mRecord: any = {
              time: now,
              target: m.target ? ((m.target as HTMLElement).className || m.target.nodeName) : 'unknown',
              type: m.type,
              causality: causality,
              classification: 'idle',
              reason: 'before_warmup'
            };

            if (phase === 'warmup') {
              mRecord.classification = 'warmup';
              mRecord.reason = 'warmup_phase';
            } else {
              const start = (window as any).__measurementStart;
              const declaredEnd = (window as any).__declaredEnd;
              if (start !== null && declaredEnd !== null) {
                if (now < start) {
                  mRecord.classification = 'before';
                  mRecord.reason = 'before_measurement_start';
                } else if (now >= start && now <= declaredEnd) {
                  mRecord.classification = 'within';
                  mRecord.reason = 'within_measurement_window';
                } else {
                  mRecord.classification = 'after';
                  mRecord.reason = 'after_measurement_window';
                }
              }
            }

            (window as any).__domMutations.push(mRecord);

            if (pending && pending.status === 'pending') {
              pending.visibleUpdateTime = now;
              pending.latency = now - pending.dispatchTime;
              pending.status = 'completed';
              (window as any).__pendingAction = null;
            }
          });
        });
        observer.observe(document.body, { attributes: true, childList: true, subtree: true });
      });

      // Fetch API timing interceptor hook
      const originalFetch = window.fetch;
      window.fetch = async function(...args) {
        if ((window as any).__windowEnded) {
          return originalFetch(...args);
        }
        const start = performance.now();
        const url = String(args[0]);
        const method = args[1]?.method || 'GET';
        const phase = (window as any).__benchmarkPhase;

        try {
          const res = await originalFetch(...args);
          const duration = performance.now() - start;

          const apiEntry: any = {
            url,
            method,
            duration,
            success: res.ok,
            timestamp: start,
            status: res.status,
            classification: 'idle',
            reason: 'before_warmup'
          };

          if (phase === 'warmup') {
            apiEntry.classification = 'warmup';
            apiEntry.reason = 'warmup_phase';
          } else {
            const mStart = (window as any).__measurementStart;
            const declaredEnd = (window as any).__declaredEnd;
            if (mStart !== null && declaredEnd !== null) {
              if (start < mStart) {
                apiEntry.classification = 'before';
                apiEntry.reason = 'before_measurement_start';
              } else if (start >= mStart && start <= declaredEnd) {
                apiEntry.classification = 'within';
                apiEntry.reason = 'within_measurement_window';
              } else {
                apiEntry.classification = 'after';
                apiEntry.reason = 'after_measurement_window';
              }
            }
          }

          (window as any).__apiTimings.push(apiEntry);
          return res;
        } catch (err) {
          const duration = performance.now() - start;

          const apiEntry: any = {
            url,
            method,
            duration,
            success: false,
            timestamp: start,
            status: 'error',
            classification: 'idle',
            reason: 'before_warmup'
          };

          if (phase === 'warmup') {
            apiEntry.classification = 'warmup';
            apiEntry.reason = 'warmup_phase';
          } else {
            const mStart = (window as any).__measurementStart;
            const declaredEnd = (window as any).__declaredEnd;
            if (mStart !== null && declaredEnd !== null) {
              if (start < mStart) {
                apiEntry.classification = 'before';
                apiEntry.reason = 'before_measurement_start';
              } else if (start >= mStart && start <= declaredEnd) {
                apiEntry.classification = 'within';
                apiEntry.reason = 'within_measurement_window';
              } else {
                apiEntry.classification = 'after';
                apiEntry.reason = 'after_measurement_window';
              }
            }
          }

          (window as any).__apiTimings.push(apiEntry);
          throw err;
        }
      };

      // Page visibility & focus trackers
      const recordEvent = (type: string, state: any) => {
        if ((window as any).__windowEnded) return;
        const now = performance.now();
        const phase = (window as any).__benchmarkPhase;

        const vRecord: any = {
          type,
          state,
          timestamp: now,
          wallTime: new Date().toISOString(),
          classification: 'idle',
          reason: 'before_warmup'
        };

        if (phase === 'warmup') {
          vRecord.classification = 'warmup';
          vRecord.reason = 'warmup_phase';
        } else {
          const start = (window as any).__measurementStart;
          const declaredEnd = (window as any).__declaredEnd;
          if (start !== null && declaredEnd !== null) {
            if (now < start) {
              vRecord.classification = 'before';
              vRecord.reason = 'before_measurement_start';
            } else if (now >= start && now <= declaredEnd) {
              vRecord.classification = 'within';
              vRecord.reason = 'within_measurement_window';
            } else {
              vRecord.classification = 'after';
              vRecord.reason = 'after_measurement_window';
            }
          }
        }

        (window as any).__visibilityFocusEvents.push(vRecord);
      };

      document.addEventListener('visibilitychange', () => {
        recordEvent('visibilitychange', document.visibilityState);
      });
      window.addEventListener('focus', () => {
        recordEvent('focus', 'focused');
      });
      window.addEventListener('blur', () => {
        recordEvent('blur', 'blurred');
      });

      // Record initial visibility & focus state and save to window variable so it survives reset
      const initialSnapshotObj = {
        type: 'initial',
        state: {
          visibility: document.visibilityState,
          focus: document.hasFocus()
        },
        timestamp: performance.now(),
        wallTime: new Date().toISOString(),
        classification: 'initial',
        reason: 'before_warmup'
      };
      (window as any).__initialVisibilityFocus = initialSnapshotObj;
      (window as any).__visibilityFocusEvents.push(initialSnapshotObj);
    });

    const page = await context.newPage();

    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('Failed') || text.includes('Error') || text.includes('exception')) {
        console.log('PAGE LOG (error/warn):', text);
      }
    });
    page.on('pageerror', err => console.error('PAGE ERROR:', err.message));

    console.log(`Navigating to Tetris production frontend: ${TARGET_URL}...`);
    try {
      await page.goto(TARGET_URL);
      await page.waitForSelector('.restart-btn', { timeout: 10000 });
      console.log('App loaded successfully.');
    } catch (err: any) {
      console.error(`Fatal Error: Could not connect to the Tetris app at ${TARGET_URL}. Ensure it is running!`);
      console.error(err.message);
      await browser.close();
      process.exit(1);
    }

    // Helper to trigger action dispatches cleanly with causal mapping
    async function pressWithActionTracking(key: string, actionName: string) {
      await page.evaluate(({ actName }) => {
        const now = performance.now();
        const phase = (window as any).__benchmarkPhase;

        const actionEntry: any = {
          action: actName,
          dispatchTime: now,
          visibleUpdateTime: null,
          latency: null,
          status: 'pending',
          causality: 'heuristic/causality unknown',
          classification: 'idle',
          reason: 'before_warmup'
        };

        if (phase === 'warmup') {
          actionEntry.classification = 'warmup';
          actionEntry.reason = 'warmup_phase';
        } else {
          const start = (window as any).__measurementStart;
          const declaredEnd = (window as any).__declaredEnd;
          if (start !== null && declaredEnd !== null) {
            if (now < start) {
              actionEntry.classification = 'before';
              actionEntry.reason = 'before_measurement_start';
            } else if (now >= start && now <= declaredEnd) {
              actionEntry.classification = 'within';
              actionEntry.reason = 'within_measurement_window';
            } else {
              actionEntry.classification = 'after';
              actionEntry.reason = 'after_measurement_window';
            }
          }
        }

        (window as any).__actionDispatches.push(actionEntry);
        (window as any).__pendingAction = actionEntry;
      }, { actName: actionName });

      await page.keyboard.press(key);
    }

    // Ensure focus and visibility are forced
    await page.bringToFront();
    await page.focus('body');
    await page.click('body', { force: true });

    // Ensure game is in active start state (click Play Again or Start Game if modal/overlay visible)
    const startOrRestartBtn = await page.$('.restart-btn');
    if (startOrRestartBtn) {
      await startOrRestartBtn.click();
      await page.waitForTimeout(500);
    }

    // --- RESET COLLECTORS AFTER NAV + RESET GAME ---
    await page.evaluate(() => {
      const initial = (window as any).__initialVisibilityFocus;
      (window as any).__rafRecords = [];
      (window as any).__domMutations = [];
      (window as any).__actionDispatches = [];
      (window as any).__apiTimings = [];
      // Re-populate visibilityFocusEvents with initial snapshot if it exists
      (window as any).__visibilityFocusEvents = initial ? [initial] : [];
      (window as any).__pendingAction = null;
      (window as any).__observedWarmupStop = null;
      (window as any).__observedStop = null;
      (window as any).__windowEnded = false;

      // Immediately after reset, record current actual visibility & focus state
      (window as any).__visibilityFocusEvents.push({
        type: 'reset_snapshot',
        state: {
          visibility: document.visibilityState,
          focus: document.hasFocus()
        },
        timestamp: performance.now(),
        wallTime: new Date().toISOString(),
        classification: 'reset',
        reason: 'immediate_after_reset'
      });
    });

    // --- PRE-DECLARE THE MONOTONIC TIMELINE IN-PAGE ---
    await page.evaluate(() => {
      const now = performance.now();
      (window as any).__benchmarkPhase = 'warmup';
      (window as any).__warmupStart = now;
      (window as any).__warmupEnd = now + 5000;
      (window as any).__measurementStart = (window as any).__warmupEnd;
      (window as any).__declaredEnd = (window as any).__measurementStart + 30000;
    });

    // --- A. WARM-UP PHASE (5 seconds) ---
    console.log(`Run ${runIndex}: Entering 5-second warmup phase...`);
    const warmupStartTime = Date.now();
    while (Date.now() - warmupStartTime < 5000) {
      // Warm up interactions
      await pressWithActionTracking('ArrowLeft', 'warmup_left');
      await page.waitForTimeout(600);
      await pressWithActionTracking('ArrowRight', 'warmup_right');
      await page.waitForTimeout(600);
    }
    console.log(`Run ${runIndex}: Warmup phase complete.`);

    // --- B. MEASUREMENT PHASE START ---
    console.log(`Run ${runIndex}: Transitioning to 30-second measurement window...`);

    // Run simulated user inputs every 800ms
    const actionInterval = setInterval(async () => {
      // Check for Game Over modal during gameplay and click restart so gameplay is sustained
      const gameOverModal = await page.$('.modal-content');
      if (gameOverModal) {
        const restartBtn = await gameOverModal.$('.restart-btn');
        if (restartBtn) {
          console.log(`Run ${runIndex}: Detected Game Over! Clicking restart button to maintain gameplay...`);
          await restartBtn.click();
          return;
        }
      }

      const actions = [
        { key: 'ArrowLeft', name: 'move_left' },
        { key: 'ArrowRight', name: 'move_right' },
        { key: 'ArrowDown', name: 'move_down' }
      ];
      const randomAction = actions[Math.floor(Math.random() * actions.length)];
      await pressWithActionTracking(randomAction.key, randomAction.name);
    }, 800);

    // Wait for the in-page clock to reach declaredEnd
    console.log(`Run ${runIndex}: Awaiting in-page monotonic clock boundary...`);
    await page.evaluate(async () => {
      return new Promise((resolve) => {
        const declaredEnd = (window as any).__declaredEnd;
        function check() {
          if (performance.now() >= declaredEnd) {
            resolve(true);
          } else {
            setTimeout(check, 30);
          }
        }
        check();
      });
    });

    clearInterval(actionInterval);
    console.log(`Run ${runIndex}: Measurement window ended at declaredEnd. Buffers frozen.`);

    // Retrieve frozen page-side metrics
    const frozenMetrics = await page.evaluate(() => {
      return {
        timeOrigin: (window as any).__timeOrigin,
        timeOriginUnit: (window as any).__timeOriginUnit,
        pageClockUnit: (window as any).__pageClockUnit,
        warmupStart: (window as any).__warmupStart,
        warmupEnd: (window as any).__warmupEnd,
        warmupDeadline: (window as any).__warmupDeadline,
        measurementStart: (window as any).__measurementStart,
        declaredEnd: (window as any).__declaredEnd,
        observedWarmupStop: (window as any).__observedWarmupStop,
        observedStop: (window as any).__observedStop,
        windowEnded: (window as any).__windowEnded,
        raf: [...(window as any).__rafRecords],
        mutations: [...(window as any).__domMutations],
        actions: [...(window as any).__actionDispatches],
        api: [...(window as any).__apiTimings],
        visibilityFocus: [...(window as any).__visibilityFocusEvents],
      };
    });

    // Capture traces & screenshots inside the unique attempt directory
    const tracePath = path.resolve(ATTEMPT_DIR, `run_${runIndex}_trace.zip`);
    await context.tracing.stop({ path: tracePath });

    const screenshotPath = path.resolve(ATTEMPT_DIR, `run_${runIndex}_screenshot.png`);
    await page.screenshot({ path: screenshotPath });

    // Close browser cleanly at the end of each run to release handles and focus
    await browser.close();

    // Process and analyze metrics - Filter strictly to 'within' window
    const withinFrames = frozenMetrics.raf.filter((r: any) => r.classification === 'within');
    const crossingStartFrames = frozenMetrics.raf.filter((r: any) => r.classification === 'crossing_start');
    const crossingEndFrames = frozenMetrics.raf.filter((r: any) => r.classification === 'crossing_end');
    const beforeFrames = frozenMetrics.raf.filter((r: any) => r.classification === 'before');
    const afterFrames = frozenMetrics.raf.filter((r: any) => r.classification === 'after');

    const deltas = withinFrames.map((r: any) => r.delta).filter(d => d > 0);
    const totalFrames = deltas.length;

    // --- C. PROOF OF VISIBILITY AND FOCUS OVER THE MEASURED WINDOW ---
    const visibilityEvents = frozenMetrics.visibilityFocus || [];
    const startSnap = visibilityEvents.find((v: any) => v.type === 'measurement_start_snapshot');
    const endSnap = visibilityEvents.find((v: any) => v.type === 'measurement_end_snapshot');

    const visibleAtStart = !!(startSnap && startSnap.state && startSnap.state.visibility === 'visible');
    const focusedAtStart = !!(startSnap && startSnap.state && startSnap.state.focus === true);
    const visibleAtEnd = !!(endSnap && endSnap.state && endSnap.state.visibility === 'visible');
    const focusedAtEnd = !!(endSnap && endSnap.state && endSnap.state.focus === true);

    let focusLostDuringWindow = false;
    let visibilityLostDuringWindow = false;
    const mStart = frozenMetrics.measurementStart;
    const dEnd = frozenMetrics.declaredEnd;

    for (const ev of visibilityEvents) {
      if (ev.timestamp >= mStart && ev.timestamp <= dEnd) {
        if (ev.type === 'blur') {
          focusLostDuringWindow = true;
        }
        if (ev.type === 'visibilitychange' && ev.state === 'hidden') {
          visibilityLostDuringWindow = true;
        }
      }
    }

    const provenVisibleAndFocused = !!(
      visibleAtStart &&
      focusedAtStart &&
      visibleAtEnd &&
      focusedAtEnd &&
      !focusLostDuringWindow &&
      !visibilityLostDuringWindow
    );

    console.log(`Run ${runIndex} Focus Proof:`);
    console.log(`- Start Snapshot: Visible=${visibleAtStart}, Focused=${focusedAtStart}`);
    console.log(`- End Snapshot: Visible=${visibleAtEnd}, Focused=${focusedAtEnd}`);
    console.log(`- Focus Lost during window: ${focusLostDuringWindow}`);
    console.log(`- Visibility Lost during window: ${visibilityLostDuringWindow}`);
    console.log(`- Proven Visible and Focused Over Entire Window: ${provenVisibleAndFocused ? 'YES' : 'NO'}`);

    let approximateFps: number | null = null;
    let medianInterval: number | null = null;
    let p95Interval: number | null = null;
    let p99Interval: number | null = null;
    let slowFrames: number | null = null;
    let runPassed = false;

    // Strict 30-second window duration
    const durationSec = 30.0;

    if (totalFrames === 0) {
      console.warn(`Run ${runIndex} Warning: Captured within-window rAF array is empty!`);
    } else {
      approximateFps = totalFrames / durationSec;
      medianInterval = calculatePercentile(deltas, 50);
      p95Interval = calculatePercentile(deltas, 95);
      p99Interval = calculatePercentile(deltas, 99);
      slowFrames = deltas.filter(d => d > 33.34).length;

      const targetFpsMet = approximateFps >= 55;
      const targetP95Met = p95Interval <= 25;
      runPassed = targetFpsMet && targetP95Met && provenVisibleAndFocused;
    }

    if (!runPassed) {
      allRunsPassed = false;
    }

    const withinActions = frozenMetrics.actions.filter((a: any) => a.classification === 'within');
    const completedActions = withinActions.filter((a: any) => a.status === 'completed');
    const latencies = completedActions.map((a: any) => a.latency).filter((l: any) => l !== null) as number[];
    const avgLatency = latencies.length > 0 ? (latencies.reduce((sum, val) => sum + val, 0) / latencies.length) : 0;
    const maxLatency = latencies.length > 0 ? Math.max(...latencies) : 0;

    const runReport = {
      runIndex,
      durationSec,
      totalFrames,
      approximateFps: approximateFps !== null ? approximateFps : null,
      medianIntervalMs: medianInterval !== null ? medianInterval : null,
      p95IntervalMs: p95Interval !== null ? p95Interval : null,
      p99IntervalMs: p99Interval !== null ? p99Interval : null,
      slowFramesCount: slowFrames !== null ? slowFrames : null,
      domMutationsCount: frozenMetrics.mutations.filter((m: any) => m.classification === 'within').length,
      avgActionLatencyMs: avgLatency,
      maxActionLatencyMs: maxLatency,
      apiCount: frozenMetrics.api.filter((a: any) => a.classification === 'within').length,
      passed: runPassed,
      provenVisibleAndFocused,
      targets: {
        targetFps: '>= 55',
        targetP95: '<= 25 ms',
        fpsPassed: approximateFps !== null ? approximateFps >= 55 : false,
        p95Passed: p95Interval !== null ? p95Interval <= 25 : false,
        focusPassed: provenVisibleAndFocused
      },
      visibilityFocusEventCount: frozenMetrics.visibilityFocus.filter((v: any) => v.classification === 'within').length,
      clockBoundaries: {
        timeOrigin: frozenMetrics.timeOrigin,
        timeOriginUnit: frozenMetrics.timeOriginUnit,
        pageClockUnit: frozenMetrics.pageClockUnit,
        warmupStart: frozenMetrics.warmupStart,
        warmupEnd: frozenMetrics.warmupEnd,
        measurementStart: frozenMetrics.measurementStart,
        declaredEnd: frozenMetrics.declaredEnd,
        observedWarmupStop: frozenMetrics.observedWarmupStop,
        observedStop: frozenMetrics.observedStop,
        windowEnded: frozenMetrics.windowEnded
      },
      outOfWindowClassificationCounts: {
        beforeFrames: beforeFrames.length,
        crossingStartFrames: crossingStartFrames.length,
        crossingEndFrames: crossingEndFrames.length,
        afterFrames: afterFrames.length
      }
    };

    results.push({
      runReport,
      rawMetrics: frozenMetrics
    });

    console.log(`Run ${runIndex} Results:`);
    console.log(`- FPS: ${approximateFps !== null ? approximateFps.toFixed(2) : 'N/D'} (Target: >= 55) - ${runReport.targets.fpsPassed ? 'PASS' : 'FAIL'}`);
    console.log(`- Median Frame Interval: ${medianInterval !== null ? medianInterval.toFixed(2) + ' ms' : 'N/D'}`);
    console.log(`- p95 Frame Interval: ${p95Interval !== null ? p95Interval.toFixed(2) + ' ms' : 'N/D'} (Target: <= 25) - ${runReport.targets.p95Passed ? 'PASS' : 'FAIL'}`);
    console.log(`- p99 Frame Interval: ${p99Interval !== null ? p99Interval.toFixed(2) + ' ms' : 'N/D'}`);
    console.log(`- Slow Frames (>33.34 ms): ${slowFrames !== null ? slowFrames : 'N/D'} / ${totalFrames}`);
    console.log(`- Board DOM Mutations: ${runReport.domMutationsCount}`);
    console.log(`- Mean Action-to-Visible Latency: ${avgLatency.toFixed(2)} ms (heuristic/causality unknown)`);
    console.log(`- API Calls Intercepted: ${runReport.apiCount}`);
    console.log(`- Out of Window Frames Classifications: Before/Warmup=${beforeFrames.length}, CrossingStart=${crossingStartFrames.length}, CrossingEnd=${crossingEndFrames.length}, After=${afterFrames.length}`);
    console.log(`- Screenshot Saved: ${screenshotPath}`);
    console.log(`- Trace Saved: ${tracePath}`);

    // Save individual raw JSON inside the unique attempt directory
    const rawMetricsPath = path.resolve(ATTEMPT_DIR, `run_${runIndex}_raw.json`);
    fs.writeFileSync(rawMetricsPath, JSON.stringify({
      envDetails,
      runReport,
      rawMetrics: frozenMetrics
    }, null, 2));
  }

  // 2. Final aggregate summary
  const finalSummary = {
    systemEnvironment: envDetails,
    browser: `Chromium/${browserVersion} (Channel: ${selectedChannel})`,
    targetUrl: TARGET_URL,
    runs: results.map(r => r.runReport),
    allRunsPassed
  };

  const summaryPath = path.resolve(ATTEMPT_DIR, 'benchmark_summary.json');
  fs.writeFileSync(summaryPath, JSON.stringify({
    summary: finalSummary,
    detailedRuns: results
  }, null, 2));

  console.log('\n==================================================');
  console.log('BENCHMARK COMPLETE');
  console.log(`All runs passed operational targets: ${allRunsPassed ? 'YES' : 'NO'}`);
  console.log(`Full immutable summary written to: ${summaryPath}`);
  console.log('==================================================');

  if (!allRunsPassed) {
    console.warn('\nWarning: One or more operational targets (mean FPS >= 55 or p95 interval <= 25 ms) were not met.');
    console.warn('Explanation: This target represents browser frame scheduling tolerance around a 60 Hz display refresh target, not physical presentation.');
  }
}

runBenchmark().catch((err) => {
  console.error('Fatal Exception running benchmark:', err);
  process.exit(1);
});
