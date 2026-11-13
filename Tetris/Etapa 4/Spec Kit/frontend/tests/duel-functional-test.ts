import { chromium, expect, Browser, BrowserContext, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const CANONICAL_COLORS = [
  [12, 12, 16],      // 0: Empty (Background #0c0c10)
  [0, 240, 240],     // 1: I (Cyan)
  [240, 240, 0],     // 2: O (Yellow)
  [160, 0, 240],     // 3: T (Purple)
  [0, 240, 0],       // 4: S (Green)
  [240, 0, 0],       // 5: Z (Red)
  [0, 0, 240],       // 6: J (Blue)
  [240, 160, 0]      // 7: L (Orange)
];

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

    function getCellIndex(r, g, b) {
      let minDistance = Infinity;
      let bestIndex = 0;
      for (let i = 0; i < canonicalColors.length; i++) {
        const [cr, cg, cb] = canonicalColors[i];
        const dist = Math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2);
        if (dist < minDistance) {
          minDistance = dist;
          bestIndex = i;
        }
      }
      return bestIndex;
    }
    
    const observed = Array.from({ length: 20 }, () => Array(10).fill(0));
    const mismatchList = [];
    
    for (let r = 0; r < 20; r++) {
      for (let c = 0; c < 10; c++) {
        const cx = Math.floor((c + 0.5) * cellWidth);
        const cy = Math.floor((r + 0.5) * cellHeight);
        const idx = (cy * W + cx) * 4;
        const pr = imgData.data[idx];
        const pg = imgData.data[idx+1];
        const pb = imgData.data[idx+2];
        
        const cellVal = getCellIndex(pr, pg, pb);
        observed[r][c] = cellVal;
        
        if (cellVal !== expected[r][c]) {
          mismatchList.push('Cell(' + r + ',' + c + ') expected ' + expected[r][c] + ', got ' + cellVal + ' (RGB: ' + pr + ',' + pg + ',' + pb + ')');
        }
      }
    }
    
    return {
      success: mismatchList.length === 0,
      board,
      activePiece,
      observed,
      mismatchDetails: mismatchList.length > 0 ? mismatchList : null
    };
  }
`;

function parseArgs() {
  const args = process.argv;
  let baseUrl = 'http://127.0.0.1:5513';
  let outputDir = 'tests-output';
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--base-url' && i + 1 < args.length) {
      baseUrl = args[i + 1];
    }
    if (args[i] === '--output' && i + 1 < args.length) {
      outputDir = args[i + 1];
    }
  }
  return { baseUrl, outputDir };
}

async function runDuelFunctionalTest() {
  const { baseUrl, outputDir } = parseArgs();
  console.log('=== STARTING PLAYWRIGHT DUEL FUNCTIONAL TEST ===');
  console.log(`Base URL: ${baseUrl}`);
  console.log(`Output Directory: ${outputDir}`);
  
  // Ensure output directory exists
  fs.mkdirSync(outputDir, { recursive: true });
  
  const isHeaded = process.argv.includes('--headed');
  console.log(`Browser Mode: ${isHeaded ? 'HEADED' : 'HEADLESS'}`);
  
  let browser: Browser | null = null;
  let contextA: BrowserContext | null = null;
  let contextB: BrowserContext | null = null;
  let contextC: BrowserContext | null = null;
  
  const observations: any = {
    test: 'duel-functional-test',
    timestamp: new Date().toISOString(),
    browserMode: isHeaded ? 'headed' : 'headless',
    steps: []
  };

  let testFailed = false;
  let failureError: any = null;
  
  try {
    // Launch Chromium browser
    browser = await chromium.launch({ headless: !isHeaded });
    
    // Create isolated browser contexts (simulating independent clients)
    const viewport = { width: 1280, height: 900 };
    contextA = await browser.newContext({ viewport, deviceScaleFactor: 1 });
    contextB = await browser.newContext({ viewport, deviceScaleFactor: 1 });
    contextC = await browser.newContext({ viewport, deviceScaleFactor: 1 });
    
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();
    const pageC = await contextC.newPage();
    
    console.log(`Navigating Client A to ${baseUrl}...`);
    await pageA.goto(baseUrl);
    await pageA.waitForLoadState('networkidle');
    await pageA.screenshot({ path: path.join(outputDir, '01-client-a-landing.png') });
    
    console.log(`Navigating Client B to ${baseUrl}...`);
    await pageB.goto(baseUrl);
    await pageB.waitForLoadState('networkidle');
    await pageB.screenshot({ path: path.join(outputDir, '01-client-b-landing.png') });

    console.log(`Navigating Client C (Isolation Client) to ${baseUrl}...`);
    await pageC.goto(baseUrl);
    await pageC.waitForLoadState('networkidle');
    await pageC.screenshot({ path: path.join(outputDir, '01-client-c-landing.png') });
    
    // 1. Enter Duel Mode on all clients
    console.log('Switching all clients to Real-Time Duel mode...');
    await pageA.click('text="Real-Time Duel"');
    await pageB.click('text="Real-Time Duel"');
    await pageC.click('text="Real-Time Duel"');
    
    // Verify lobby buttons are visible
    await pageA.waitForSelector('text="Create New Duel Room"', { timeout: 5000 });
    await pageB.waitForSelector('text="Create New Duel Room"', { timeout: 5000 });
    await pageC.waitForSelector('text="Create New Duel Room"', { timeout: 5000 });
    
    await pageA.screenshot({ path: path.join(outputDir, '02-client-a-duel-lobby.png') });
    await pageB.screenshot({ path: path.join(outputDir, '02-client-b-duel-lobby.png') });
    
    // 2. Client A creates Room A
    console.log('Client A creating a fresh duel room (Room A)...');
    await pageA.click('text="Create New Duel Room"');
    await pageA.waitForSelector('text="Room ID:"', { timeout: 5000 });
    
    const roomIdText = await pageA.innerText('code');
    const roomIdA = roomIdText.trim();
    console.log(`Room A created successfully! ID: ${roomIdA}`);
    
    await pageA.waitForSelector('text="WAITING"', { timeout: 5000 });
    await pageA.screenshot({ path: path.join(outputDir, '03-client-a-waiting.png') });
    
    // 3. Client C creates Room B (to verify room isolation)
    console.log('Client C creating a separate duel room (Room B)...');
    await pageC.click('text="Create New Duel Room"');
    await pageC.waitForSelector('text="Room ID:"', { timeout: 5000 });
    const roomIdTextC = await pageC.innerText('code');
    const roomIdB = roomIdTextC.trim();
    console.log(`Room B created successfully! ID: ${roomIdB}`);
    
    // 4. Client B joins Room A
    console.log(`Client B typing Room ID: ${roomIdA} and joining Room A...`);
    await pageB.fill('input[placeholder="Enter Room ID"]', roomIdA);
    await pageB.click('text="Join"');
    
    // Wait for match to start (ACTIVE status) on Room A players
    console.log('Waiting for Client A and Client B to transition to ACTIVE status...');
    await pageA.waitForSelector('text="ACTIVE"', { timeout: 5000 });
    await pageB.waitForSelector('text="ACTIVE"', { timeout: 5000 });
    
    await pageA.screenshot({ path: path.join(outputDir, '04-client-a-active.png') });
    await pageB.screenshot({ path: path.join(outputDir, '04-client-b-active.png') });
    
    // Check Client C is still WAITING in Room B (isolated)
    const clientCStatus = await pageC.innerText('.duel-header strong');
    console.log(`Client C (Room B) status is: ${clientCStatus}`);
    observations.steps.push({
      step: 'room-isolation-setup',
      roomIdA,
      roomIdB,
      clientCStatus
    });

    // 5. Retrieve initial state on Client A before moves
    const beforeActivePieceStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-active-piece');
    const beforeActivePiece = beforeActivePieceStr ? JSON.parse(beforeActivePieceStr) : null;
    const beforeBoardStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-board-state');
    const beforeBoard = beforeBoardStr ? JSON.parse(beforeBoardStr) : null;
    const beforeSeq = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-seq');
    const beforeGen = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-gen');
    
    console.log(`Initial Active Piece Type: ${beforeActivePiece?.type}`);
    console.log(`Initial Sequence: ${beforeSeq}, Generation: ${beforeGen}`);

    // Verify Canvas 2D pixels match authoritative state before moves
    console.log('Verifying Canvas 2D pixels before movement...');
    const beforePixelCheck = await pageA.evaluate(`(${CANVAS_INSPECTOR_FN})('.own-board canvas.board-canvas', ${beforeBoardStr}, ${beforeActivePieceStr})`);
    expect(beforePixelCheck.success).toBe(true);
    
    // 6. Perform Left Movement
    console.log('Client A executing ArrowLeft...');
    await pageA.keyboard.press('ArrowLeft');
    await pageA.waitForTimeout(300);
    
    const afterLeftSeq = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-seq');
    const afterLeftBoardStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-board-state');
    const afterLeftPieceStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-active-piece');
    const opponentSeqOnB = await pageB.getAttribute('.opponent-board canvas.board-canvas', 'data-seq');
    
    console.log(`Client A sequence after Left: ${afterLeftSeq}`);
    console.log(`Client B opponent sequence after Client A Left: ${opponentSeqOnB}`);
    
    expect(Number(afterLeftSeq)).toBeGreaterThan(Number(beforeSeq));
    expect(Number(opponentSeqOnB)).toBe(Number(afterLeftSeq));

    // Verify Canvas 2D pixels match authoritative state after left movement
    console.log('Verifying Canvas 2D pixels after left movement...');
    const leftPixelCheck = await pageA.evaluate(`(${CANVAS_INSPECTOR_FN})('.own-board canvas.board-canvas', ${afterLeftBoardStr}, ${afterLeftPieceStr})`);
    if (!leftPixelCheck.success) {
      console.log('leftPixelCheck failed mismatch details:', JSON.stringify(leftPixelCheck.mismatchDetails, null, 2));
      console.log('leftPixelCheck expected active piece:', afterLeftPieceStr);
      console.log('leftPixelCheck expected board:', afterLeftBoardStr);
    }
    expect(leftPixelCheck.success).toBe(true);
    
    observations.steps.push({
      step: 'left-movement',
      beforeSeq,
      afterLeftSeq,
      opponentSeqOnB
    });

    // 7. Perform Clockwise (CW) Rotation (ArrowUp)
    console.log('Client A executing ArrowUp (Clockwise)...');
    const pieceBeforeRotStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-active-piece');
    const pieceBeforeRot = pieceBeforeRotStr ? JSON.parse(pieceBeforeRotStr) : null;
    
    await pageA.keyboard.press('ArrowUp');
    await pageA.waitForTimeout(300);
    
    const afterCwSeq = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-seq');
    const afterCwBoardStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-board-state');
    const pieceAfterCwStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-active-piece');
    const pieceAfterCw = pieceAfterCwStr ? JSON.parse(pieceAfterCwStr) : null;
    
    console.log(`Client A sequence after CW: ${afterCwSeq}`);
    console.log(`Piece cells before CW: ${JSON.stringify(pieceBeforeRot?.cells)}`);
    console.log(`Piece cells after CW: ${JSON.stringify(pieceAfterCw?.cells)}`);

    // Verify Canvas 2D pixels match authoritative state after CW rotation
    console.log('Verifying Canvas 2D pixels after CW rotation...');
    const cwPixelCheck = await pageA.evaluate(`(${CANVAS_INSPECTOR_FN})('.own-board canvas.board-canvas', ${afterCwBoardStr}, ${pieceAfterCwStr})`);
    expect(cwPixelCheck.success).toBe(true);
    
    let isRotationNoOp = false;
    if (pieceBeforeRot?.type === 'O') {
      console.log('Active piece is "O". Verifying that CW rotation is a strict no-op (accounting for potential concurrent gravity shifts)...');
      const beforeCols = pieceBeforeRot.cells.map(([r, c]) => c).sort();
      const afterCwCols = pieceAfterCw?.cells.map(([r, c]) => c).sort();
      expect(beforeCols).toEqual(afterCwCols);
      
      const beforeRows = pieceBeforeRot.cells.map(([r, c]) => r).sort();
      const afterCwRows = pieceAfterCw?.cells.map(([r, c]) => r).sort();
      const beforeRowSpan = Math.max(...beforeRows) - Math.min(...beforeRows);
      const afterRowSpan = Math.max(...afterCwRows) - Math.min(...afterCwRows);
      expect(beforeRowSpan).toBe(afterRowSpan);
      isRotationNoOp = true;
    } else {
      console.log(`Active piece is "${pieceBeforeRot?.type}". Verifying cell coordinates changed...`);
      expect(pieceBeforeRot?.cells).not.toEqual(pieceAfterCw?.cells);
    }
    
    observations.steps.push({
      step: 'cw-rotation',
      pieceType: pieceBeforeRot?.type,
      isRotationNoOp,
      beforeCells: pieceBeforeRot?.cells,
      afterCwCells: pieceAfterCw?.cells,
      afterCwSeq
    });

    // 8. Perform Counterclockwise (CCW) Rotation (Z)
    console.log('Client A executing Z (Counterclockwise)...');
    await pageA.keyboard.press('Z');
    await pageA.waitForTimeout(300);
    
    const afterCcwSeq = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-seq');
    const afterCcwBoardStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-board-state');
    const pieceAfterCcwStr = await pageA.getAttribute('.own-board canvas.board-canvas', 'data-active-piece');
    const pieceAfterCcw = pieceAfterCcwStr ? JSON.parse(pieceAfterCcwStr) : null;
    
    console.log(`Client A sequence after CCW: ${afterCcwSeq}`);
    console.log(`Piece cells after CCW: ${JSON.stringify(pieceAfterCcw?.cells)}`);

    // Verify Canvas 2D pixels match authoritative state after CCW rotation
    console.log('Verifying Canvas 2D pixels after CCW rotation...');
    const ccwPixelCheck = await pageA.evaluate(`(${CANVAS_INSPECTOR_FN})('.own-board canvas.board-canvas', ${afterCcwBoardStr}, ${pieceAfterCcwStr})`);
    expect(ccwPixelCheck.success).toBe(true);
    
    if (pieceBeforeRot?.type === 'O') {
      console.log('Active piece is "O". Verifying CCW is also a no-op (accounting for potential concurrent gravity shifts)...');
      const cwCols = pieceAfterCw?.cells.map(([r, c]) => c).sort();
      const ccwCols = pieceAfterCcw?.cells.map(([r, c]) => c).sort();
      expect(cwCols).toEqual(ccwCols);
      
      const cwRows = pieceAfterCw?.cells.map(([r, c]) => r).sort();
      const ccwRows = pieceAfterCcw?.cells.map(([r, c]) => r).sort();
      const cwRowSpan = Math.max(...cwRows) - Math.min(...cwRows);
      const ccwRowSpan = Math.max(...ccwRows) - Math.min(...ccwRows);
      expect(cwRowSpan).toBe(ccwRowSpan);
    } else {
      console.log('Active piece is not "O". Verifying cells rotated again (usually back to Orientation 0 if unobstructed)...');
      expect(pieceAfterCw?.cells).not.toEqual(pieceAfterCcw?.cells);
    }
    
    observations.steps.push({
      step: 'ccw-rotation',
      pieceType: pieceBeforeRot?.type,
      afterCcwCells: pieceAfterCcw?.cells,
      afterCcwSeq
    });

    // 9. Verify Room Isolation: check if Client C in Room B received any actions from Room A
    console.log('Verifying Room Isolation: Checking Client C board state...');
    const clientCSeq = await pageC.getAttribute('.own-board canvas.board-canvas', 'data-seq');
    console.log(`Client C (Room B) sequence number: ${clientCSeq}`);
    // Room B is completely isolated, so Client C sequence must still be 0 (or unchanged)
    expect(clientCSeq === '0' || clientCSeq === null).toBe(true);
    
    observations.steps.push({
      step: 'room-isolation-verification',
      clientCSeq
    });
    
    // 10. Client A disconnects (simulating forfeit)
    console.log('Simulating forfeit: Closing Client A page...');
    await pageA.close();
    
    // Client B should instantly receive forfeit/victory event
    console.log('Verifying victory notification on Client B...');
    await pageB.waitForSelector('text="VICTORY!"', { timeout: 5000 });
    await pageB.screenshot({ path: path.join(outputDir, '06-client-b-victory.png') });
    
    const reasonText = await pageB.innerText('.game-over-panel p');
    console.log(`Victory reason reported to Client B: "${reasonText}"`);
    expect(reasonText).toContain('disconnected/forfeited');
    
    observations.steps.push({
      step: 'victory-forfeit',
      reasonText
    });
    
    console.log('=== ALL FUNCTIONAL DUEL CHECKS PASSED PERFECTLY ===');
    
  } catch (error: any) {
    console.error('FAIL: Duel functional test encountered an error:', error);
    testFailed = true;
    failureError = error.message || error;
  } finally {
    console.log('Cleaning up resources inside finally...');
    if (contextA) await contextA.close().catch(() => {});
    if (contextB) await contextB.close().catch(() => {});
    if (contextC) await contextC.close().catch(() => {});
    if (browser) await browser.close().catch(() => {});
    
    // Save the raw observations report
    observations.result = testFailed ? 'FAILED' : 'PASSED';
    if (testFailed) {
      observations.error = failureError;
    }
    
    const reportPath = path.join(outputDir, 'observations-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(observations, null, 2), 'utf-8');
    console.log(`Raw observations report saved to: ${reportPath}`);
    
    if (testFailed) {
      process.exit(1);
    }
  }
}

runDuelFunctionalTest();
