import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { createRequire } from 'module';
import { pathToFileURL } from 'url';

const require = createRequire(import.meta.url);
const TARGET_URL = 'http://127.0.0.1:5515'; // Production URL mapped by docker-compose

// Color palette used in the Canvas board
const SYSTEM_PALETTE = {
  I: [0, 240, 240],   // #00f0f0
  O: [240, 240, 0],   // #f0f000
  T: [160, 0, 240],   // #a000f0
  S: [0, 240, 0],     // #00f000
  Z: [240, 0, 0],     // #f00000
  J: [0, 0, 240],     // #0000f0
  L: [240, 160, 0]    // #f0a000
};

// Map actual RGB to closest tetromino type or null (empty/background)
function getCellTypeFromRgb(r, g, b) {
  let closestType = null;
  let minDistance = Infinity;
  
  for (const [type, rgb] of Object.entries(SYSTEM_PALETTE)) {
    const dist = Math.sqrt(
      Math.pow(r - rgb[0], 2) +
      Math.pow(g - rgb[1], 2) +
      Math.pow(b - rgb[2], 2)
    );
    if (dist < 40) { // Standard Euclidean color matching threshold
      if (dist < minDistance) {
        minDistance = dist;
        closestType = type;
      }
    }
  }
  return closestType;
}

// Percentile calculation helper
function getPercentile(arr, p) {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const index = (sorted.length - 1) * p;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

// Helper to run shell commands safely
function runCmd(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf-8', stdio: 'pipe' }).trim();
  } catch (err) {
    return null;
  }
}

// Collect Host Specifications
const osType = process.platform;
const nodeVersion = process.version;
let cpuName = 'Unknown';
let gpuName = 'Unknown';
let displayRefreshRate = 'Unknown';

if (osType === 'win32') {
  try {
    const cpuResult = runCmd('powershell.exe -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"');
    if (cpuResult) cpuName = cpuResult;
  } catch (err) {}
  try {
    const gpuResult = runCmd('powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"');
    if (gpuResult) gpuName = gpuResult;
  } catch (err) {}
  try {
    const refreshResult = runCmd('powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty CurrentRefreshRate"');
    if (refreshResult) displayRefreshRate = refreshResult;
  } catch (err) {}
}

const hostSpecs = {
  os: osType,
  node: nodeVersion,
  cpu: cpuName,
  gpu: gpuName,
  display_refresh_rate: displayRefreshRate,
  browser_version: null
};

// Node-to-browser clock calibration helper
async function calibrateClocks(page) {
  const t0_node = performance.now();
  const t0_browser = await page.evaluate(() => performance.now());
  const t1_node = performance.now();
  return {
    nodeStart: t0_node,
    nodeEnd: t1_node,
    browserTime: t0_browser,
    uncertainty: (t1_node - t0_node) / 2,
    midpointNode: (t0_node + t1_node) / 2
  };
}

// Map page timestamps with bracketed Node calibration
function calibratePageTimeToNode(pageTime, preCal, postCal) {
  const t0_b = preCal.browserTime;
  const t1_b = postCal ? postCal.browserTime : preCal.browserTime;
  const t0_n = preCal.midpointNode;
  const t1_n = postCal ? postCal.midpointNode : preCal.midpointNode;
  
  if (!postCal || t1_b === t0_b) {
    return {
      nodeTime: pageTime - t0_b + t0_n,
      uncertainty: preCal.uncertainty
    };
  }
  
  const fraction = (pageTime - t0_b) / (t1_b - t0_b);
  const nodeTime = t0_n + fraction * (t1_n - t0_n);
  const uncertainty = preCal.uncertainty + fraction * (postCal.uncertainty - preCal.uncertainty);
  return { nodeTime, uncertainty };
}

// Reconstruct 200 cell colors from Canvas back-buffer based on seat order
async function captureAndVerifyCanvas(page, canvasIndex, seatActor) {
  return await page.evaluate(({ index, seat }) => {
    const canvases = document.querySelectorAll('canvas.tetris-board');
    const canvas = canvases[index];
    if (!canvas) return null;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = canvas.width;
    const height = canvas.height;
    
    const cols = 10;
    const rows = 20;
    const cellStepX = width / cols;
    const cellStepY = height / rows;
    
    const pixels = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const centerX = Math.floor((c + 0.5) * cellStepX);
        const centerY = Math.floor((r + 0.5) * cellStepY);
        const imgData = ctx.getImageData(centerX, centerY, 1, 1).data;
        pixels.push([imgData[0], imgData[1], imgData[2], imgData[3]]);
      }
    }
    
    const boardHash = canvas.getAttribute('data-board-hash') || '';
    const activePieceType = canvas.getAttribute('data-active-piece-type') || 'none';
    const activePieceOrientation = canvas.getAttribute('data-active-piece-orientation') || 'none';
    
    const pixelMask = pixels.map(p => `${p[0]},${p[1]},${p[2]},${p[3]}`).join('|');
    
    return {
      timestamp: performance.now(),
      latestFrameIndex: window.rafTimestamps && window.rafTimestamps.length > 0 ? window.rafTimestamps.length - 1 : null,
      boardHash,
      activePieceType,
      activePieceOrientation,
      pixels,
      pixelMask,
      canvas_width: width,
      canvas_height: height,
      css_width: rect.width,
      css_height: rect.height,
      dpr,
      seat,
      index
    };
  }, { index: canvasIndex, seat: seatActor });
}

// Verify actual colors and alpha against expected logical board layout
function verifyCanvasPixels(record, expectedState) {
  if (!record || !record.pixels || record.pixels.length === 0 || !expectedState) return null;
  
  const expectedBoard = expectedState.board;
  const expectedActive = expectedState.active_piece;
  const actualPixels = record.pixels;
  
  let matches = true;
  const discrepancies = [];
  const pixelMask = [];
  const emptyColor = [28, 31, 43, 255]; // CSS background #151824 composited with 3% white alpha
  
  for (let r = 0; r < 20; r++) {
    for (let c = 0; c < 10; c++) {
      const idx = r * 10 + c;
      const rgba = actualPixels[idx];
      
      let expectedType = null;
      if (expectedBoard && expectedBoard[r] && expectedBoard[r][c]) {
        expectedType = expectedBoard[r][c];
      } else {
        const isActiveCell = expectedActive && expectedActive.cells
          ? expectedActive.cells.some(([pr, pc]) => pr === r && pc === c)
          : false;
        if (isActiveCell) {
          expectedType = expectedActive.type;
        }
      }
      
      let expectedColor = emptyColor;
      if (expectedType) {
        const rgb = SYSTEM_PALETTE[expectedType];
        if (rgb) {
          expectedColor = [rgb[0], rgb[1], rgb[2], 255];
        }
      }
      
      const dist = Math.sqrt(
        Math.pow(rgba[0] - expectedColor[0], 2) +
        Math.pow(rgba[1] - expectedColor[1], 2) +
        Math.pow(rgba[2] - expectedColor[2], 2)
      );
      
      const alphaMatches = rgba[3] === expectedColor[3];
      const cellMatches = dist < 40 && alphaMatches;
      
      const actualType = getCellTypeFromRgb(rgba[0], rgba[1], rgba[2]);
      pixelMask.push(actualType || '.');
      
      if (!cellMatches) {
        matches = false;
        discrepancies.push({
          r,
          c,
          expectedType,
          actualType,
          expectedColor,
          actualColor: rgba,
          dist,
          alphaMatches
        });
      }
    }
  }
  
  return {
    matches,
    pixelMaskString: pixelMask.join(''),
    discrepanciesCount: discrepancies.length,
    discrepancies
  };
}

// Retrieve the latest valid board state from captured WebSocket frames
function getLatestWSBoardState(wsFrames, seat, roomId) {
  let latestState = null;
  let latestRev = -1;
  
  for (const f of wsFrames) {
    if (f.direction === 'in' && f.payload) {
      const msg = f.payload;
      if (msg.type === 'state_update' && msg.payload) {
        if (msg.payload.room_id === roomId) {
          const b = seat === 'player1' ? msg.payload.player1_board : msg.payload.player2_board;
          if (b && b.board_revision > latestRev) {
            latestState = b;
            latestRev = b.board_revision;
          }
        }
      } else if (msg.type === 'ack' && msg.payload) {
        // Handshake validation ensures we correlate correct sockets
        const handshake = wsFrames.find(x => x.direction === 'in' && x.payload && x.payload.type === 'handshake');
        if (handshake && handshake.payload && handshake.payload.payload && handshake.payload.payload.seat === seat) {
          const ackPayload = msg.payload;
          const status = ackPayload.status;
          if ((status === 'applied' || status === 'accepted') && ackPayload.authoritative_board) {
            if (ackPayload.board_revision > latestRev) {
              latestState = ackPayload.authoritative_board;
              latestRev = ackPayload.board_revision;
            }
          }
        }
      }
    }
  }
  return latestState;
}

// Match peer board state strictly from the peer socket
function getLatestPeerBoardFromPeerSocket(wsFramesPeer, roomId, seatPeer) {
  // Try inbound ACKs first
  const peerAcks = wsFramesPeer.filter(f => 
    f.direction === 'in' && 
    f.payload && 
    f.payload.type === 'ack' && 
    f.payload.payload &&
    (f.payload.payload.status === 'accepted' || f.payload.payload.status === 'applied')
  );
  if (peerAcks.length > 0) {
    return peerAcks[peerAcks.length - 1].payload.payload.authoritative_board;
  }
  
  // Fall back to state updates
  const peerStateUpdates = wsFramesPeer.filter(f => 
    f.direction === 'in' && 
    f.payload && 
    f.payload.type === 'state_update' && 
    f.payload.payload &&
    f.payload.payload.room_id === roomId
  );
  if (peerStateUpdates.length > 0) {
    const latestStateUpdate = peerStateUpdates[peerStateUpdates.length - 1].payload.payload;
    return seatPeer === 'player1' ? latestStateUpdate.player1_board : latestStateUpdate.player2_board;
  }
  return null;
}

// Retrieve the latest valid board state from intercepted HTTP responses
function getLatestSoloState(responses, gameId) {
  for (let i = responses.length - 1; i >= 0; i--) {
    const res = responses[i];
    if (res.body && typeof res.body === 'object') {
      if (gameId && res.reqMeta && res.reqMeta.gameId && res.reqMeta.gameId !== gameId) {
        continue;
      }
      if (res.body.board && typeof res.body.board_revision === 'number') {
        return {
          state: res.body,
          reqId: res.reqId,
          endpoint: res.reqMeta.endpoint,
          method: res.reqMeta.method
        };
      }
    }
  }
  return null;
}

// Calculate the visual difference changed mask (length 200) between prior and post
function calculateChangedMask(priorRecord, postRecord) {
  if (!priorRecord || !postRecord || !priorRecord.pixels || !postRecord.pixels) return null;
  const mask = [];
  for (let i = 0; i < 200; i++) {
    const p1 = priorRecord.pixels[i];
    const p2 = postRecord.pixels[i];
    const changed = p1[0] !== p2[0] || p1[1] !== p2[1] || p1[2] !== p2[2] || p1[3] !== p2[3];
    mask.push(changed ? '1' : '0');
  }
  return mask.join('');
}

async function runTrial(scenario, mode, trialNum, label, finalOutputDir, warmupMs, measureMs) {
  console.log(`\n=== Starting Trial ${trialNum} [${scenario.toUpperCase()} - ${mode.toUpperCase()}] ===`);
  
  let browserActor = null;
  let contextActor = null;
  let pageActor = null;
  let browserPeer = null;
  let contextPeer = null;
  let pagePeer = null;

  let gateMode = 'browser-only';
  let foregroundEvidence = null;

  const httpRequests = [];
  const httpResponses = [];
  const requestWeakMap = new WeakMap();

  const wsFramesActor = [];
  const wsFramesPeer = [];

  const dispatchedInputs = [];

  const actorTitle = `TESSL ${label} ACTOR INPUT`;
  const peerTitle = `TESSL ${label} PEER INPUT`;

  try {
    // Launch fresh client browsers with headed installed Chrome
    browserActor = await chromium.launch({
      headless: false,
      channel: 'chrome',
      chromiumSandbox: true,
      ignoreDefaultArgs: [
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding'
      ]
    });
    contextActor = await browserActor.newContext({
      viewport: { width: 1280, height: 900 },
      deviceScaleFactor: 1
    });
    pageActor = await contextActor.newPage();
    await contextActor.tracing.start({ screenshots: true, snapshots: true, sources: true });

    // Set host specs browser version
    if (!hostSpecs.browser_version) {
      hostSpecs.browser_version = browserActor.version();
    }

    if (scenario === 'duel') {
      browserPeer = await chromium.launch({
        headless: false,
        channel: 'chrome',
        chromiumSandbox: true,
        ignoreDefaultArgs: [
          '--disable-background-timer-throttling',
          '--disable-backgrounding-occluded-windows',
          '--disable-renderer-backgrounding'
        ]
      });
      contextPeer = await browserPeer.newContext({
        viewport: { width: 1280, height: 900 },
        deviceScaleFactor: 1
      });
      pagePeer = await contextPeer.newPage();
      await contextPeer.tracing.start({ screenshots: true, snapshots: true, sources: true });
    }

    // REGISTER WEBSOCKET OBSERVATION ON BOTH PAGES BEFORE ENTERING DUEL / NAVIGATION
    pageActor.on('websocket', ws => {
      ws.on('framesent', event => {
        try {
          const data = JSON.parse(event.payload);
          wsFramesActor.push({
            direction: 'out',
            time_node: performance.now(),
            payload: data
          });
        } catch (e) {}
      });
      ws.on('framereceived', event => {
        try {
          const data = JSON.parse(event.payload);
          wsFramesActor.push({
            direction: 'in',
            time_node: performance.now(),
            payload: data
          });
        } catch (e) {}
      });
    });

    if (pagePeer) {
      pagePeer.on('websocket', ws => {
        ws.on('framesent', event => {
          try {
            const data = JSON.parse(event.payload);
            wsFramesPeer.push({
              direction: 'out',
              time_node: performance.now(),
              payload: data
            });
          } catch (e) {}
        });
        ws.on('framereceived', event => {
          try {
            const data = JSON.parse(event.payload);
            wsFramesPeer.push({
              direction: 'in',
              time_node: performance.now(),
              payload: data
            });
          } catch (e) {}
        });
      });
    }

    // Solo Mode HTTP Request & Response Interceptors via WeakMap
    pageActor.on('request', req => {
      const url = req.url();
      const method = req.method();
      
      let endpoint = null;
      let gameId = null;
      let direction = null;
      
      if (url.endsWith('/api/games') && method === 'POST') {
        endpoint = 'create';
      } else {
        const matchAction = url.match(/\/api\/games\/([a-zA-Z0-9_-]+)\/(tick|move|rotate|hold)$/);
        if (matchAction) {
          gameId = matchAction[1];
          endpoint = matchAction[2];
        } else {
          const matchGet = url.match(/\/api\/games\/([a-zA-Z0-9_-]+)$/);
          if (matchGet && method === 'GET') {
            gameId = matchGet[1];
            endpoint = 'get';
          }
        }
      }
      
      if (endpoint) {
        if (endpoint === 'move' || endpoint === 'rotate') {
          const postDataStr = req.postData();
          if (postDataStr) {
            try {
              const parsed = JSON.parse(postDataStr);
              direction = parsed.direction;
            } catch (e) {}
          }
        }
        
        const reqId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
        const meta = {
          reqId,
          url,
          method,
          gameId,
          endpoint,
          direction,
          time_node: performance.now()
        };
        
        requestWeakMap.set(req, meta);
        httpRequests.push(meta);
      }
    });

    pageActor.on('response', async res => {
      const req = res.request();
      const reqMeta = requestWeakMap.get(req);
      if (reqMeta) {
        let body = null;
        try {
          body = await res.json();
        } catch (e) {
          try {
            body = await res.text();
          } catch (err) {}
        }
        
        httpResponses.push({
          reqId: reqMeta.reqId,
          url: res.url(),
          method: reqMeta.method,
          status: res.status(),
          body,
          time_node: performance.now(),
          reqMeta
        });
      }
    });

    // Navigate to production URL and apply labels
    await pageActor.goto(TARGET_URL);
    await pageActor.evaluate((title) => {
      document.title = title;
    }, actorTitle);

    if (pagePeer) {
      await pagePeer.goto(TARGET_URL);
      await pagePeer.evaluate((title) => {
        document.title = title;
      }, peerTitle);
    }

    // Switch modes and setup
    let roomId = null;
    let seatActor = null;
    let seatPeer = null;
    let gameId = null;

    if (scenario === 'solo') {
      const btnSolo = pageActor.locator('.btn-mode').first();
      if (await btnSolo.isVisible()) {
        await btnSolo.click();
      }
      // Rely on Solo automatic game creation without racing reset
      const soloCanvas = pageActor.locator('canvas.tetris-board').first();
      await soloCanvas.waitFor({ state: 'visible', timeout: 5000 });
      await pageActor.waitForTimeout(500);

      // Poll for Solo Game ID from create HTTP response
      const gameIdStart = Date.now();
      while (Date.now() - gameIdStart < 10000) {
        const res = httpResponses.find(r => r.reqMeta && r.reqMeta.endpoint === 'create' && r.body && r.body.id);
        if (res) {
          gameId = res.body.id;
          break;
        }
        await pageActor.waitForTimeout(100);
      }
      if (!gameId) {
        console.warn('Warning: Could not identify Solo Game ID from HTTP interceptions.');
      } else {
        console.log(`[Trial ${trialNum}] Identified Solo Game ID: ${gameId}`);
      }
    } else {
      // Duel Setup via UI Interaction
      const btnDuelActor = pageActor.locator('[data-testid="btn-mode-duel"]');
      await btnDuelActor.click();
      await pageActor.waitForTimeout(500);

      const btnCreate = pageActor.locator('button.btn-create');
      await btnCreate.click();
      await pageActor.waitForTimeout(1000);

      const roomIdDisplay = pageActor.locator('.room-id-display');
      await roomIdDisplay.waitFor({ state: 'visible', timeout: 5000 });
      roomId = (await roomIdDisplay.textContent()).trim();

      const btnDuelPeer = pagePeer.locator('[data-testid="btn-mode-duel"]');
      await btnDuelPeer.click();
      await pagePeer.waitForTimeout(500);

      const roomIdInput = pagePeer.locator('#room-id-input');
      await roomIdInput.fill(roomId);
      await pagePeer.waitForTimeout(200);

      const btnJoin = pagePeer.locator('button.btn-join');
      await btnJoin.click();
      await pagePeer.waitForTimeout(1000);

      // Gate Duel with actual playing wire messages on BOTH sockets
      console.log(`[Trial ${trialNum}] Waiting for Duel initialization wire messages...`);
      const duelGateStart = Date.now();
      let duelGated = false;
      while (Date.now() - duelGateStart < 15000) {
        const actorHandshake = wsFramesActor.find(f => f.direction === 'in' && f.payload && f.payload.type === 'handshake');
        const peerHandshake = wsFramesPeer.find(f => f.direction === 'in' && f.payload && f.payload.type === 'handshake');
        
        const actorStateUpdates = wsFramesActor.filter(f => f.direction === 'in' && f.payload && f.payload.type === 'state_update');
        const peerStateUpdates = wsFramesPeer.filter(f => f.direction === 'in' && f.payload && f.payload.type === 'state_update');
        
        const actorPlaying = actorStateUpdates.some(f => f.payload.payload && f.payload.payload.status === 'playing' && f.payload.payload.player1_board && f.payload.payload.player2_board);
        const peerPlaying = peerStateUpdates.some(f => f.payload.payload && f.payload.payload.status === 'playing' && f.payload.payload.player1_board && f.payload.payload.player2_board);
        
        if (actorHandshake && peerHandshake && actorPlaying && peerPlaying) {
          seatActor = actorHandshake.payload.payload.seat;
          seatPeer = peerHandshake.payload.payload.seat;
          duelGated = true;
          break;
        }
        await new Promise(r => setTimeout(r, 100));
      }
      if (!duelGated) {
        throw new Error("Duel Gating Timeout: WebSocket handshakes or playing wire messages failed to activate.");
      }
      console.log(`[Trial ${trialNum}] Duel Gated. Room: ${roomId}, Actor Seat: ${seatActor}, Peer Seat: ${seatPeer}`);

      // Ensure both boards/canvases are visible
      await pageActor.locator('canvas.tetris-board').first().waitFor({ state: 'visible', timeout: 5000 });
      await pagePeer.locator('canvas.tetris-board').first().waitFor({ state: 'visible', timeout: 5000 });
    }

    // Ensure document titles are absolutely correct after setup transitions
    await pageActor.evaluate((title) => {
      document.title = title;
    }, actorTitle);
    if (pagePeer) {
      await pagePeer.evaluate((title) => {
        document.title = title;
      }, peerTitle);
    }

    // Emit structured readiness
    console.log(JSON.stringify({
      event: 'readiness',
      trial: trialNum,
      actor_pid: null,
      actor_title: actorTitle,
      peer_pid: null,
      peer_title: pagePeer ? peerTitle : null
    }));

    // GATING FOCUS: Unified 90-second focus wait with optional Win32 observer gating. Fail trial on timeout or subsequent focus loss
    const observationPath = process.env.TESSL_FOREGROUND_OBSERVATION;
    if (observationPath) {
      gateMode = 'win32-observer';
      console.log(`[Trial ${trialNum}] Win32 foreground observation enabled. Path: ${observationPath}`);
    } else {
      gateMode = 'browser-only';
      console.log(`[Trial ${trialNum}] standalone browser-only focus gating (TESSL_FOREGROUND_OBSERVATION not set).`);
    }

    console.log(`[Trial ${trialNum}] Gating Foreground Focus (90s limit)...`);
    const startFocusTime = Date.now();
    let focusReady = false;

    if (pageActor) {
      try {
        await pageActor.bringToFront();
      } catch (e) {}
      try {
        await pageActor.focus('canvas.tetris-board');
      } catch (e) {}
    }

    let peerFocusStateAtGating = null;

    while (Date.now() - startFocusTime < 90000) {
      const focusState = await pageActor.evaluate(() => {
        return {
          focus: document.hasFocus(),
          visible: document.visibilityState === 'visible'
        };
      });

      const localReady = focusState.focus && focusState.visible;
      let observerReady = false;
      let observerResult = null;

      if (observationPath) {
        observerResult = checkWin32ObserverGate(observationPath);
        observerReady = observerResult.ready;
      } else {
        observerReady = true;
      }

      if (localReady && observerReady) {
        if (pagePeer) {
          try {
            peerFocusStateAtGating = await pagePeer.evaluate(() => {
              return {
                focus: document.hasFocus(),
                visible: document.visibilityState === 'visible'
              };
            });
          } catch (e) {
            peerFocusStateAtGating = { focus: false, visible: false, error: e.message };
          }
        }

        if (observationPath && observerResult) {
          foregroundEvidence = {
            timestamps: observerResult.timestamps,
            hwnd: observerResult.hwnd,
            pid: observerResult.pid
          };
        }

        focusReady = true;
        break;
      }

      const pollDelay = observationPath ? 100 : 200;
      await new Promise(r => setTimeout(r, pollDelay));
    }

    if (!focusReady) {
      if (observationPath) {
        throw new Error(`Gating Timeout: Actor page focus or Win32 foreground observer failed to acquire foreground focus within 90 seconds.`);
      } else {
        throw new Error(`Gating Timeout: Actor failed to acquire foreground focus within 90 seconds.`);
      }
    }

    // Inject metrics-tracking hooks
    await pageActor.evaluate(() => {
      window.rafTimestamps = [];
      window.focusLost = false;
      window.focusEvents = [];
      window.keydownRecords = [];
      window.stagedDispatchId = null;

      let frameCount = 0;
      function rafLoop(timestamp) {
        window.rafTimestamps.push({
          time_browser: performance.now(),
          frame_time: timestamp,
          frame_index: frameCount++
        });
        window.rafLoopId = requestAnimationFrame(rafLoop);
      }
      window.rafLoopId = requestAnimationFrame(rafLoop);

      window.addEventListener('blur', () => {
        window.focusLost = true;
        window.focusEvents.push({ time: performance.now(), event: 'blur' });
      });
      window.addEventListener('focus', () => {
        window.focusEvents.push({ time: performance.now(), event: 'focus' });
      });

      // KEYDOWN LISTENER with timestamp, key, isTrusted, focus, visibility, staged ID
      document.addEventListener('keydown', (event) => {
        window.keydownRecords.push({
          dispatchId: window.stagedDispatchId,
          key: event.key,
          isTrusted: event.isTrusted,
          timestamp: performance.now(),
          focus: document.hasFocus(),
          visibility: document.visibilityState,
          time_utc: Date.now()
        });
      });
    });

    if (pagePeer) {
      await pagePeer.evaluate(() => {
        window.focusLost = false;
        window.focusEvents = [];
        window.addEventListener('blur', () => {
          window.focusLost = true;
          window.focusEvents.push({ time: performance.now(), event: 'blur' });
        });
        window.addEventListener('focus', () => {
          window.focusEvents.push({ time: performance.now(), event: 'focus' });
        });
      });
    }

    // Pre-trial clock calibrations
    const preCalActor = await calibrateClocks(pageActor);
    let preCalPeer = null;
    if (pagePeer) {
      preCalPeer = await calibrateClocks(pagePeer);
    }

    // Define timing anchors and strict bounds in NODE
    const wallAnchorDate = Date.now();
    const wallAnchorPerformance = performance.now();

    const nodeWarmupStart = wallAnchorPerformance;
    const nodeMeasureStart = nodeWarmupStart + warmupMs;
    const nodeMeasureEnd = nodeMeasureStart + measureMs;

    const bounds = {
      nodeWarmupStart,
      nodeMeasureStart,
      nodeMeasureEnd,
      wallAnchorDate,
      wallAnchorPerformance,
      nominal_warmup_ms: warmupMs,
      nominal_measure_ms: measureMs
    };

    // Warm-up Phase
    console.log(`[Trial ${trialNum}] Warmup started...`);
    let lastInputTime = 0;
    let warmupInputsCount = 0;
    
    while (performance.now() < nodeMeasureStart) {
      const elapsed = performance.now() - nodeWarmupStart;
      
      const actorFocusState = await pageActor.evaluate(() => {
        return { focusLost: window.focusLost, hasFocus: document.hasFocus(), visible: document.visibilityState === 'visible' };
      });
      if (actorFocusState.focusLost || !actorFocusState.hasFocus || !actorFocusState.visible) {
        throw new Error("Trial Failed: Actor lost foreground focus during warm-up phase.");
      }

      if (elapsed - lastInputTime > 250) {
        const keys = ['ArrowLeft', 'ArrowRight'];
        const key = keys[warmupInputsCount % keys.length];
        await pageActor.keyboard.press(key);
        warmupInputsCount++;
        lastInputTime = elapsed;
      }
      await pageActor.waitForTimeout(10);
    }

    const actualNodeMeasureStart = performance.now();
    console.log(`[Trial ${trialNum}] Measurement window active...`);
    let nextActionAllowedTime = performance.now();
    let actionCount = 0;

    // Measurement loop
    while (performance.now() < nodeMeasureEnd) {
      const now = performance.now();
      if (now < nextActionAllowedTime) {
        await pageActor.waitForTimeout(5);
        continue;
      }
      
      const actorFocusState = await pageActor.evaluate(() => {
        return { focusLost: window.focusLost, hasFocus: document.hasFocus(), visible: document.visibilityState === 'visible' };
      });
      if (actorFocusState.focusLost || !actorFocusState.hasFocus || !actorFocusState.visible) {
        throw new Error("Trial Failed: Actor lost foreground focus during active measurement.");
      }

      if (nodeMeasureEnd - now < 300) {
        break;
      }

      // Keys generated: clockwise rotation uses 'z' (lowercase) or 'ArrowUp' as instructed
      const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'z'];
      const key = keys[actionCount % keys.length];
      actionCount++;
      
      const actorCanvasIndex = seatActor === 'player2' ? 1 : 0;
      const peerCanvasIndex = seatActor === 'player2' ? 0 : 1;
      
      let priorStateAndEvidence = null;
      let priorState = null;
      if (scenario === 'solo') {
        priorStateAndEvidence = getLatestSoloState(httpResponses, gameId);
        priorState = priorStateAndEvidence ? priorStateAndEvidence.state : null;
      } else {
        priorState = getLatestWSBoardState(wsFramesActor, seatActor, roomId);
      }
      
      // Capture canvases prior to action
      const priorCanvasRecord = await captureAndVerifyCanvas(pageActor, actorCanvasIndex, seatActor);
      const priorCanvasVerify = verifyCanvasPixels(priorCanvasRecord, priorState);

      let peerPriorCanvasRecord = null;
      if (scenario === 'duel' && pagePeer) {
        peerPriorCanvasRecord = await captureAndVerifyCanvas(pagePeer, actorCanvasIndex, seatActor);
      }
      
      // Stage per-dispatch ID before keyboard press
      const dispatchId = `dispatch_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
      await pageActor.evaluate((id) => {
        window.stagedDispatchId = id;
      }, dispatchId);
      
      const inputNodeTimestamp = performance.now();
      const inputDomTimestamp = await pageActor.evaluate(() => performance.now());
      await pageActor.keyboard.press(key);
      
      // Retrieve keydown event
      let keydownRecord = null;
      const keydownWaitStart = performance.now();
      while (performance.now() - keydownWaitStart < 200) {
        keydownRecord = await pageActor.evaluate((id) => {
          return window.keydownRecords.find(r => r.dispatchId === id);
        }, dispatchId);
        if (keydownRecord) break;
        await pageActor.waitForTimeout(5);
      }
      
      // Wait for corresponding API response or WebSocket ACK
      let expectedPostState = null;
      let matchedResponse = null;
      let matchedAck = null;
      let correlatedPeerStateUpdate = null;
      
      const expectedActionType = (key === 'ArrowUp' || key === 'Z' || key === 'z') ? 'rotate' : 'move';
      const expectedDirection = key === 'ArrowLeft' ? 'left' : (key === 'ArrowRight' ? 'right' : (key === 'ArrowUp' ? 'cw' : 'ccw'));
      
      const networkWaitStart = performance.now();
      let networkTimedOut = false;
      while (performance.now() - networkWaitStart < 800) {
        if (performance.now() >= nodeMeasureEnd) break;
        
        if (scenario === 'solo') {
          const candidates = httpResponses.filter(res => 
            res.reqMeta &&
            res.reqMeta.endpoint === expectedActionType &&
            res.method === 'POST' &&
            res.reqMeta.gameId === gameId &&
            res.reqMeta.direction === expectedDirection &&
            res.status === 200 &&
            res.reqId === res.reqMeta.reqId &&
            res.reqMeta.time_node >= inputNodeTimestamp &&
            res.reqMeta.time_node <= inputNodeTimestamp + 800
          );
          if (candidates.length === 1) {
            matchedResponse = candidates[0];
            expectedPostState = matchedResponse.body;
            break;
          } else if (candidates.length > 1) {
            break; // Ambiguous
          }
        } else {
          // Duel matching matching EXACTLY one outgoing action and corresponding peer state update
          const outbounds = wsFramesActor.filter(f => 
            f.direction === 'out' && 
            f.payload && 
            f.payload.type === 'action' && 
            f.payload.payload && 
            f.payload.payload.action_type === expectedActionType &&
            f.payload.payload.direction === expectedDirection &&
            f.time_node >= inputNodeTimestamp &&
            f.time_node <= inputNodeTimestamp + 800
          );
          if (outbounds.length === 1) {
            const outbound = outbounds[0];
            const ack = wsFramesActor.find(f => 
              f.direction === 'in' && 
              f.payload && 
              f.payload.type === 'ack' && 
              f.payload.payload && 
              f.payload.payload.action_id === outbound.payload.payload.action_id
            );
            if (ack) {
              const status = ack.payload.payload.status;
              if (status === 'applied' || status === 'accepted') {
                const tempPostState = ack.payload.payload.authoritative_board;
                
                // Find corresponding peer socket inbound state_update
                const peerStateUpdate = wsFramesPeer.find(f => {
                  if (f.direction !== 'in' || !f.payload || f.payload.type !== 'state_update') return false;
                  const payload = f.payload.payload;
                  if (!payload || payload.room_id !== roomId) return false;
                  
                  const boardData = seatActor === 'player1' ? payload.player1_board : payload.player2_board;
                  if (!boardData) return false;
                  
                  // Same board revision
                  if (boardData.board_revision !== tempPostState.board_revision) return false;
                  
                  // Same contents (board layout)
                  const contentsMatch = JSON.stringify(boardData.board) === JSON.stringify(tempPostState.board);
                  return contentsMatch;
                });
                
                if (peerStateUpdate) {
                  matchedAck = ack;
                  expectedPostState = tempPostState;
                  correlatedPeerStateUpdate = peerStateUpdate;
                  break;
                }
              }
            }
          } else if (outbounds.length > 1) {
            break; // Ambiguous
          }
        }
        await pageActor.waitForTimeout(5);
      }
      
      if (!expectedPostState) {
        networkTimedOut = true;
      }
      
      // Poll Canvas pixels on PageActor and PagePeer contemporaneously
      let postCanvasRecord = null;
      let postCanvasVerify = null;
      let matchedCanvasTimestamp = null;
      let canvasTimedOut = false;
      
      let peerPostCanvasRecord = null;
      let peerPostCanvasVerify = null;
      let peerMatchedCanvasTimestamp = null;
      let peerCanvasTimedOut = false;
      let expectedPeerPostState = null;
      
      if (expectedPostState) {
        const pollingStart = performance.now();
        while (performance.now() - pollingStart < 800) {
          if (performance.now() >= nodeMeasureEnd) break;
          
          // Poll Actor Canvas
          if (!postCanvasRecord) {
            const nodeCapTime = performance.now();
            const tempRecord = await captureAndVerifyCanvas(pageActor, actorCanvasIndex, seatActor);
            const tempVerify = verifyCanvasPixels(tempRecord, expectedPostState);
            if (tempVerify && tempVerify.matches) {
              postCanvasRecord = tempRecord;
              postCanvasRecord.node_capture_time = nodeCapTime;
              postCanvasVerify = tempVerify;
              matchedCanvasTimestamp = tempRecord.timestamp;
            }
          }
          
          // Poll Peer Canvas
          if (scenario === 'duel' && pagePeer && !peerPostCanvasRecord) {
            const nodeCapTime = performance.now();
            const tempRecord = await captureAndVerifyCanvas(pagePeer, actorCanvasIndex, seatActor);
            const tempVerify = verifyCanvasPixels(tempRecord, expectedPostState);
            if (tempVerify && tempVerify.matches) {
              peerPostCanvasRecord = tempRecord;
              peerPostCanvasRecord.node_capture_time = nodeCapTime;
              peerPostCanvasVerify = tempVerify;
              peerMatchedCanvasTimestamp = tempRecord.timestamp;
            }
          }
          
          // Break early if both are found
          if (postCanvasRecord && (scenario !== 'duel' || !pagePeer || peerPostCanvasRecord)) {
            break;
          }
          
          await pageActor.waitForTimeout(5);
        }
      }
      
      if (!postCanvasRecord) {
        canvasTimedOut = true;
        const nodeCapTime = performance.now();
        postCanvasRecord = await captureAndVerifyCanvas(pageActor, actorCanvasIndex, seatActor);
        postCanvasRecord.node_capture_time = nodeCapTime;
        postCanvasVerify = verifyCanvasPixels(postCanvasRecord, expectedPostState);
      }
      
      if (scenario === 'duel' && pagePeer && !peerPostCanvasRecord) {
        peerCanvasTimedOut = true;
        const nodeCapTime = performance.now();
        peerPostCanvasRecord = await captureAndVerifyCanvas(pagePeer, actorCanvasIndex, seatActor);
        peerPostCanvasRecord.node_capture_time = nodeCapTime;
        peerPostCanvasVerify = verifyCanvasPixels(peerPostCanvasRecord, expectedPostState);
      }
      
      // Capture peer's own board from peer socket
      if (scenario === 'duel' && pagePeer && expectedPostState) {
        expectedPeerPostState = getLatestPeerBoardFromPeerSocket(wsFramesPeer, roomId, seatPeer);
        if (expectedPeerPostState) {
          const peerOwnRecord = await captureAndVerifyCanvas(pagePeer, peerCanvasIndex, seatPeer);
          const peerOwnVerify = verifyCanvasPixels(peerOwnRecord, expectedPeerPostState);
          if (peerOwnVerify) {
            peerPostCanvasRecord.peer_own_board_verification = {
              expected: expectedPeerPostState,
              actual_record: peerOwnRecord,
              verify: peerOwnVerify
            };
          }
        }
      }
      
      // Qualify visual change, changed masks, and exclusions
      const hasVisualChange = postCanvasRecord && priorCanvasRecord && (postCanvasRecord.pixelMask !== priorCanvasRecord.pixelMask);
      
      let exclusionReason = null;
      
      // Key/code verification
      if (keydownRecord) {
        if (!keydownRecord.isTrusted) {
          exclusionReason = 'untrusted_event';
        } else if (!keydownRecord.focus || keydownRecord.visibility !== 'visible') {
          exclusionReason = 'lost_focus_during_event';
        }
      }

      if (key === 'ArrowUp' || key === 'Z' || key === 'z') {
        if (priorState && priorState.active_piece && priorState.active_piece.type === 'O') {
          exclusionReason = 'O_rotation';
        }
      }
      
      if (scenario === 'solo') {
        if (matchedResponse && matchedResponse.body) {
          if (matchedResponse.body.status === 'game_over') {
            exclusionReason = 'game_over';
          }
          if (priorState && matchedResponse.body.board_revision === priorState.board_revision) {
            exclusionReason = 'noop';
          }
        } else if (networkTimedOut) {
          exclusionReason = 'timeout';
        }
        
        // Reject intervening changes
        let hasInterveningSoloChange = false;
        if (priorState && expectedPostState) {
          for (const res of httpResponses) {
            if (res.reqMeta && res.reqMeta.gameId === gameId && res.body && typeof res.body.board_revision === 'number') {
              const rev = res.body.board_revision;
              if (res.reqId !== priorStateAndEvidence?.reqId && res.reqId !== matchedResponse?.reqId) {
                if (rev >= priorState.board_revision && rev < expectedPostState.board_revision) {
                  hasInterveningSoloChange = true;
                }
              }
            }
          }
        }
        if (hasInterveningSoloChange) {
          exclusionReason = 'intervening_change';
        }
      } else {
        if (matchedAck) {
          const status = matchedAck.payload.payload.status;
          if (status === 'noop' || status === 'rejected') {
            exclusionReason = status;
          }
        } else if (networkTimedOut) {
          exclusionReason = 'timeout';
        }
      }

      if (!hasVisualChange && !exclusionReason) {
        exclusionReason = 'blocked';
      }
      if (canvasTimedOut && !exclusionReason) {
        exclusionReason = 'stale';
      }
      if (expectedPostState && priorState && !exclusionReason) {
        const revDiff = expectedPostState.board_revision - priorState.board_revision;
        if (revDiff > 1) {
          exclusionReason = 'ambiguous';
        }
      }

      // Calculate separate qualified changed masks
      const actorChangedMask = calculateChangedMask(priorCanvasRecord, postCanvasRecord);
      const peerChangedMask = calculateChangedMask(peerPriorCanvasRecord, peerPostCanvasRecord);
      
      const sample = {
        inputId: dispatchId,
        key,
        actionType: expectedActionType,
        direction: expectedDirection,
        inputNodeTimestamp,
        inputDomTimestamp,
        keydownRecord,
        networkTimedOut,
        canvasTimedOut,
        peerCanvasTimedOut,
        hasVisualChange,
        exclusionReason,
        
        // Raw page-level timestamps saved for post-loop deferred calculations
        rawPageActorKeydownTimestamp: keydownRecord ? keydownRecord.timestamp : null,
        rawPageActorCanvasTimestamp: matchedCanvasTimestamp,
        rawPagePeerCanvasTimestamp: peerMatchedCanvasTimestamp,
        rawNodeActorCanvasTimestamp: postCanvasRecord ? postCanvasRecord.node_capture_time : null,
        rawNodePeerCanvasTimestamp: peerPostCanvasRecord ? peerPostCanvasRecord.node_capture_time : null,
        rawActorFrameIndex: postCanvasRecord ? postCanvasRecord.latestFrameIndex : null,
        rawPeerFrameIndex: peerPostCanvasRecord ? peerPostCanvasRecord.latestFrameIndex : null,
        correlatedPeerStateUpdate,
        
        actorChangedMask,
        peerChangedMask,
        
        priorCanvasRecord,
        postCanvasRecord,
        peerPriorCanvasRecord,
        peerPostCanvasRecord,
        priorState,
        expectedPostState,
        
        // Save request/response identity and chosen authority evidence
        authorityEvidence: {
          scenario,
          solo_game_id: gameId,
          duel_room_id: roomId,
          seat_actor: seatActor,
          prior_evidence_req_id: priorStateAndEvidence?.reqId,
          prior_evidence_endpoint: priorStateAndEvidence?.endpoint,
          post_evidence_req_id: matchedResponse?.reqId,
          post_evidence_ack_action_id: matchedAck?.payload?.payload?.action_id
        }
      };
      
      dispatchedInputs.push(sample);
      nextActionAllowedTime = performance.now() + 200; // 5Hz pace
    }

    // Ensure final wait covers complete fixed measurement window even when dispatching stops 300ms early
    const finalWaitMs = nodeMeasureEnd - performance.now();
    if (finalWaitMs > 0) {
      await pageActor.waitForTimeout(finalWaitMs);
    }
    const actualNodeMeasureEnd = performance.now();

    // Post-trial clock calibrations
    const postCalActor = await calibrateClocks(pageActor);
    let postCalPeer = null;
    if (pagePeer) {
      postCalPeer = await calibrateClocks(pagePeer);
    }

    // Now calculate estimates and uncertainty securely AFTER post-calibration
    for (const sample of dispatchedInputs) {
      let localVisualLatency = null;
      let peerVisualLatency = null;
      let reasonOmit = null;

      const rawKeydownTime = sample.rawPageActorKeydownTimestamp;
      const rawActorCanvasTime = sample.rawPageActorCanvasTimestamp;
      const rawPeerCanvasTime = sample.rawPagePeerCanvasTimestamp;

      if (rawKeydownTime !== null && rawActorCanvasTime !== null) {
        const calKeydown = calibratePageTimeToNode(rawKeydownTime, preCalActor, postCalActor);
        const calCanvas = calibratePageTimeToNode(rawActorCanvasTime, preCalActor, postCalActor);
        
        const keydownNode = calKeydown.nodeTime;
        const canvasNode = calCanvas.nodeTime;
        
        localVisualLatency = canvasNode - keydownNode;
        
        // Validate / omit checks
        if (localVisualLatency < 0) {
          reasonOmit = 'negative_latency';
          localVisualLatency = null;
        } else if (keydownNode < nodeMeasureStart || canvasNode > nodeMeasureEnd) {
          reasonOmit = 'out_of_window';
          localVisualLatency = null;
        }
      } else {
        reasonOmit = 'missing_timestamps';
      }

      if (scenario === 'duel' && rawKeydownTime !== null && rawPeerCanvasTime !== null && preCalPeer && postCalPeer) {
        if (sample.peerCanvasTimedOut) {
          peerVisualLatency = null;
          reasonOmit = reasonOmit ? `${reasonOmit},peer_canvas_timeout` : 'peer_canvas_timeout';
        } else {
          const calKeydown = calibratePageTimeToNode(rawKeydownTime, preCalActor, postCalActor);
          const calPeerCanvas = calibratePageTimeToNode(rawPeerCanvasTime, preCalPeer, postCalPeer);
          
          const keydownNode = calKeydown.nodeTime;
          const peerCanvasNode = calPeerCanvas.nodeTime;
          
          peerVisualLatency = peerCanvasNode - keydownNode;
          
          if (peerVisualLatency < 0) {
            reasonOmit = reasonOmit ? `${reasonOmit},negative_peer_latency` : 'negative_peer_latency';
            peerVisualLatency = null;
          } else if (keydownNode < nodeMeasureStart || peerCanvasNode > nodeMeasureEnd) {
            reasonOmit = reasonOmit ? `${reasonOmit},peer_out_of_window` : 'peer_out_of_window';
            peerVisualLatency = null;
          }
        }
      }

      sample.localVisualLatency = localVisualLatency;
      sample.peerVisualLatency = peerVisualLatency;
      if (reasonOmit && !sample.exclusionReason) {
        sample.exclusionReason = reasonOmit;
      }
    }

    // Capture metric data (rAF continues running until cancel here)
    const pageData = await pageActor.evaluate(() => {
      cancelAnimationFrame(window.rafLoopId);
      return {
        rafTimestamps: window.rafTimestamps,
        focusLost: window.focusLost,
        focusEvents: window.focusEvents
      };
    });

    let pagePeerData = null;
    if (pagePeer) {
      try {
        pagePeerData = await pagePeer.evaluate(() => {
          return {
            focusLost: window.focusLost,
            focusEvents: window.focusEvents
          };
        });
      } catch (e) {
        pagePeerData = { focusLost: false, focusEvents: [], error: e.message };
      }
    }

    // Capture screenshot PNGs
    const screenshotPathActor = path.join(finalOutputDir, `trial-${trialNum}-actor.png`);
    await pageActor.screenshot({ path: screenshotPathActor });

    if (pagePeer) {
      const screenshotPathPeer = path.join(finalOutputDir, `trial-${trialNum}-peer.png`);
      await pagePeer.screenshot({ path: screenshotPathPeer });
    }

    // Process rAF
    const rafSamples = pageData.rafTimestamps;
    const intervals = [];
    for (let i = 1; i < rafSamples.length; i++) {
      const t_prev = rafSamples[i - 1].time_browser;
      const t_curr = rafSamples[i].time_browser;
      intervals.push({ t_prev, t_curr, diff: t_curr - t_prev });
    }

    // Classify rAF intervals using Node calibrated offsets securely
    const classifiedIntervals = intervals.map(item => {
      const nodePrev = calibratePageTimeToNode(item.t_prev, preCalActor, postCalActor).nodeTime;
      const nodeCurr = calibratePageTimeToNode(item.t_curr, preCalActor, postCalActor).nodeTime;
      
      let classification = '';
      if (item.diff <= 0) {
        classification = 'nonpositive';
      } else if (nodeCurr <= nodeWarmupStart) {
        classification = 'pre-window';
      } else if (nodePrev < nodeWarmupStart && nodeCurr > nodeWarmupStart) {
        classification = 'cross-boundary-pre-to-warmup';
      } else if (nodeCurr <= nodeMeasureStart) {
        classification = 'warmup';
      } else if (nodePrev >= nodeMeasureStart && nodeCurr <= nodeMeasureEnd) {
        classification = 'eligible';
      } else if (nodePrev < nodeMeasureStart && nodeCurr >= nodeMeasureStart) {
        classification = 'cross-boundary-warmup-to-measure';
      } else if (nodePrev <= nodeMeasureEnd && nodeCurr > nodeMeasureEnd) {
        classification = 'cross-boundary-measure-to-post';
      } else if (nodePrev >= nodeMeasureEnd) {
        classification = 'post-window';
      } else {
        classification = 'other';
      }
      return { ...item, nodePrev, nodeCurr, classification };
    });

    const eligibleIntervals = classifiedIntervals.filter(x => x.classification === 'eligible').map(x => x.diff);
    const meanRafCallbacksPerSec = eligibleIntervals.length / (measureMs / 1000);
    
    const medianRaf = getPercentile(eligibleIntervals, 0.5);
    const p95Raf = getPercentile(eligibleIntervals, 0.95);
    const p99Raf = getPercentile(eligibleIntervals, 0.99);

    const eligibleVisualLatencies = dispatchedInputs.filter(x => !x.exclusionReason && x.localVisualLatency !== null).map(x => x.localVisualLatency);
    const peerVisualLatencies = dispatchedInputs.filter(x => !x.exclusionReason && x.peerVisualLatency !== null).map(x => x.peerVisualLatency);

    const actualBounds = {
      actualNodeWarmupStart: nodeWarmupStart,
      actualNodeWarmupEnd: actualNodeMeasureStart,
      actualNodeMeasureStart: actualNodeMeasureStart,
      actualNodeMeasureEnd: actualNodeMeasureEnd,
      actualUtcWarmupStart: wallAnchorDate + (nodeWarmupStart - wallAnchorPerformance),
      actualUtcWarmupEnd: wallAnchorDate + (actualNodeMeasureStart - wallAnchorPerformance),
      actualUtcMeasureStart: wallAnchorDate + (actualNodeMeasureStart - wallAnchorPerformance),
      actualUtcMeasureEnd: wallAnchorDate + (actualNodeMeasureEnd - wallAnchorPerformance)
    };

    const result = {
      trial: trialNum,
      gate_mode: gateMode,
      foreground_evidence: foregroundEvidence,
      nominalBounds: bounds,
      actualBounds,
      focus_lost: pageData.focusLost,
      focus_events: pageData.focusEvents,
      peer_focus_state_at_gating: peerFocusStateAtGating,
      peer_focus_lost: pagePeerData ? pagePeerData.focusLost : null,
      peer_focus_events: pagePeerData ? pagePeerData.focusEvents : null,
      pre_cal: preCalActor,
      post_cal: postCalActor,
      pre_cal_peer: preCalPeer,
      post_cal_peer: postCalPeer,
      browser_version: hostSpecs.browser_version,
      raf: {
        total_recorded: rafSamples.length,
        raw_samples: rafSamples,
        eligible_count: eligibleIntervals.length,
        mean_rate_callbacks_per_sec: meanRafCallbacksPerSec,
        intervals_ms: {
          median: medianRaf,
          p95: p95Raf,
          p99: p99Raf
        },
        classified_intervals: classifiedIntervals
      },
      actions: {
        total_dispatched: dispatchedInputs.length,
        local_sample_count: dispatchedInputs.filter(x => x.rawPageActorKeydownTimestamp !== null).length,
        peer_sample_count: dispatchedInputs.filter(x => x.rawPagePeerCanvasTimestamp !== null).length,
        linked_count: dispatchedInputs.filter(x => x.keydownRecord).length,
        eligible_latencies_count: eligibleVisualLatencies.length,
        latency_ms: {
          median: eligibleVisualLatencies.length ? getPercentile(eligibleVisualLatencies, 0.5) : null,
          p95: eligibleVisualLatencies.length ? getPercentile(eligibleVisualLatencies, 0.95) : null,
          p99: eligibleVisualLatencies.length ? getPercentile(eligibleVisualLatencies, 0.99) : null
        },
        peer_latency_ms: {
          median: peerVisualLatencies.length ? getPercentile(peerVisualLatencies, 0.5) : null,
          p95: peerVisualLatencies.length ? getPercentile(peerVisualLatencies, 0.95) : null,
          p99: peerVisualLatencies.length ? getPercentile(peerVisualLatencies, 0.99) : null
        },
        raw_samples: dispatchedInputs
      },
      network: {
        http_requests: httpRequests,
        http_responses: httpResponses,
        ws_frames_actor: wsFramesActor,
        ws_frames_peer: wsFramesPeer
      }
    };

    // Save individual trial named JSON file to ensure partial outcome survival
    fs.writeFileSync(path.join(finalOutputDir, `trial-${trialNum}-results.json`), JSON.stringify(result, null, 2), 'utf-8');
    return result;

  } finally {
    // DEFENSIVE RESOURCE CLEANUP IN FINALLY
    if (browserActor) {
      try {
        await contextActor.tracing.stop({ path: path.join(finalOutputDir, `trial-${trialNum}-actor-trace.zip`) });
      } catch (e) {}
      try {
        await browserActor.close();
      } catch (e) {}
    }
    if (browserPeer) {
      try {
        await contextPeer.tracing.stop({ path: path.join(finalOutputDir, `trial-${trialNum}-peer-trace.zip`) });
      } catch (e) {}
      try {
        await browserPeer.close();
      } catch (e) {}
    }
  }
}

async function main() {
  console.log('=== Launching Corrected Tetris Stage 4 Benchmark Instrument ===');
  
  const args = {};
  for (let i = 2; i < process.argv.length; i++) {
    const arg = process.argv[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const val = process.argv[i + 1];
      if (val && !val.startsWith('--')) {
        args[key] = val;
        i++;
      } else {
        args[key] = true;
      }
    }
  }

  const scenario = args.scenario;
  const mode = args.mode;
  const label = args.label;
  const outputDirArg = args.output;

  if (!scenario || !['solo', 'duel'].includes(scenario)) {
    console.error('Error: --scenario must be "solo" or "duel"');
    process.exit(1);
  }
  if (!mode || !['probe', 'final'].includes(mode)) {
    console.error('Error: --mode must be "probe" or "final"');
    process.exit(1);
  }
  if (!label) {
    console.error('Error: --label is required');
    process.exit(1);
  }
  if (!outputDirArg) {
    console.error('Error: --output is required');
    process.exit(1);
  }

  const finalOutputDir = path.resolve(outputDirArg);
  if (fs.existsSync(finalOutputDir)) {
    console.error(`Collision detected: Output directory "${finalOutputDir}" already exists!`);
    process.exit(1);
  }
  fs.mkdirSync(finalOutputDir, { recursive: true });

  const warmupMs = mode === 'final' ? 5000 : 2000;
  const measureMs = mode === 'final' ? 30000 : 8000;

  console.log(`Scenario: ${scenario.toUpperCase()}`);
  console.log(`Mode: ${mode.toUpperCase()} (Warmup: ${warmupMs}ms, Measurement: ${measureMs}ms)`);
  console.log(`Label: ${label}`);
  console.log(`Output Directory: ${finalOutputDir}`);

  const results = [];
  try {
    const res = await runTrial(scenario, mode, 1, label, finalOutputDir, warmupMs, measureMs);
    results.push(res);
  } catch (err) {
    console.error('Fatal error during benchmark execution:', err);
    // Persist partial failure receipt
    const failureReceipt = {
      timestamp: new Date().toISOString(),
      status: 'failed',
      error: err.message,
      stack: err.stack,
      partial_results: results
    };
    fs.writeFileSync(path.join(finalOutputDir, 'partial-failure-receipt.json'), JSON.stringify(failureReceipt, null, 2), 'utf-8');
    console.log(`Partial failure receipt saved to ${finalOutputDir}`);
    process.exit(1);
  }

  // Save complete consolidated performance report
  const report = {
    timestamp: new Date().toISOString(),
    label,
    scenario,
    mode,
    host: hostSpecs,
    target_url: TARGET_URL,
    playwright_environment: {
      playwright_version: require('playwright/package.json').version,
      platform: process.platform,
      arch: process.arch,
      node_version: process.version
    },
    trials: results
  };

  const reportPath = path.join(finalOutputDir, 'performance-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8');
  console.log(`\n=== Complete Performance Report Saved to ${reportPath} ===`);

  // Print high-level metrics summary
  results.forEach(t => {
    console.log(`\nTrial ${t.trial} Summary:`);
    console.log(`  - Mean rAF scheduling rate: ${t.raf.mean_rate_callbacks_per_sec.toFixed(2)} callbacks/s (Target: >= 55 callbacks/s)`);
    console.log(`  - p95 rAF scheduling interval: ${t.raf.intervals_ms.p95.toFixed(2)}ms (Target: <= 25ms)`);
    console.log(`  - Visual Latency (median): ${t.actions.latency_ms.median ? t.actions.latency_ms.median.toFixed(2) + 'ms' : 'null'}`);
    if (scenario === 'duel') {
      console.log(`  - Peer Visual Latency (median): ${t.actions.peer_latency_ms.median ? t.actions.peer_latency_ms.median.toFixed(2) + 'ms' : 'null'}`);
    }
  });

  const readmeContent = `### Stage 4 Benchmark Results [${label}]

- **Invocation:** \`node benchmark.js --scenario ${scenario} --mode ${mode} --label ${label} --output ${finalOutputDir}\`
- **Timestamp:** ${new Date().toISOString()}
- **Scenario:** ${scenario}
- **Mode:** ${mode}
- **Hardware Specs:**
  - OS: ${hostSpecs.os}
  - CPU: ${hostSpecs.cpu}
  - GPU: ${hostSpecs.gpu}
  - Refresh Rate: ${hostSpecs.display_refresh_rate}Hz
`;
  fs.writeFileSync(path.join(finalOutputDir, 'README.md'), readmeContent, 'utf-8');
}

// Check Win32 Foreground Observer logs
function checkWin32ObserverGate(filePath) {
  if (!fs.existsSync(filePath)) {
    return { ready: false, reason: `Observer file does not exist: ${filePath}` };
  }
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    return { ready: false, reason: `Failed to read observer file: ${err.message}` };
  }

  // Parse only complete newline-terminated lines safely
  const lines = content.split('\n');
  const completeLines = lines.slice(0, -1);

  const foregroundSamples = [];
  for (const line of completeLines) {
    if (!line.trim()) continue;
    try {
      const row = JSON.parse(line);
      // Do not count observer start/end records as foreground
      if (row && row.event === 'foreground') {
        foregroundSamples.push(row);
      }
    } catch (e) {
      // Safe ignore of malformed lines
    }
  }

  if (foregroundSamples.length < 3) {
    return { ready: false, reason: `Insufficient foreground samples (found ${foregroundSamples.length}, need at least 3)` };
  }

  // Require latest consecutive samples (at least three)
  const s1 = foregroundSamples[foregroundSamples.length - 3];
  const s2 = foregroundSamples[foregroundSamples.length - 2];
  const s3 = foregroundSamples[foregroundSamples.length - 1];

  // actor_title_match true, visible true
  if (!s1.actor_title_match || !s2.actor_title_match || !s3.actor_title_match) {
    return { ready: false, reason: "Latest foreground samples missing actor_title_match" };
  }
  if (s1.visible !== true || s2.visible !== true || s3.visible !== true) {
    return { ready: false, reason: "Latest foreground samples visible state is not true" };
  }

  // same hwnd and PID
  if (s1.hwnd === undefined || s1.hwnd !== s2.hwnd || s2.hwnd !== s3.hwnd) {
    return { ready: false, reason: "Latest foreground samples have different HWNDs" };
  }
  if (s1.pid === undefined || s1.pid !== s2.pid || s2.pid !== s3.pid) {
    return { ready: false, reason: "Latest foreground samples have different PIDs" };
  }

  // UTC newest no older than 400 ms (using Date.parse)
  const newestUtcTime = Date.parse(s3.utc);
  if (isNaN(newestUtcTime)) {
    return { ready: false, reason: `Invalid UTC format in newest sample: ${s3.utc}` };
  }

  const now = Date.now();
  const age = now - newestUtcTime;
  if (age > 400) {
    return { ready: false, reason: `Newest sample is stale: age is ${age}ms (> 400ms limit)` };
  }
  if (age < -1000) {
    return { ready: false, reason: `Newest sample is in the future: age is ${age}ms` };
  }

  return {
    ready: true,
    hwnd: s3.hwnd,
    pid: s3.pid,
    timestamps: [s1.utc, s2.utc, s3.utc]
  };
}

// Export helpers cleanly for vitest synthetic tests
export {
  calibratePageTimeToNode,
  getCellTypeFromRgb,
  verifyCanvasPixels,
  calculateChangedMask,
  getLatestWSBoardState,
  getLatestPeerBoardFromPeerSocket,
  getLatestSoloState,
  checkWin32ObserverGate
};

// Check if run directly
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(err => {
    console.error('Fatal unhandled error in main:', err);
    process.exit(1);
  });
}
