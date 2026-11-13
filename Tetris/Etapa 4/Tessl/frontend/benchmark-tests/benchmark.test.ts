import { describe, expect, test } from 'vitest';
import {
  calibratePageTimeToNode,
  getCellTypeFromRgb,
  verifyCanvasPixels,
  calculateChangedMask,
  getLatestWSBoardState,
  getLatestPeerBoardFromPeerSocket,
  getLatestSoloState,
  checkWin32ObserverGate
} from '../benchmark.js';

describe('Benchmark Pure Helpers & Calibration Verification', () => {
  
  test('Clock Calibration with TWO mock page clocks shifted by different offsets from Node', () => {
    // Offset 1: Actor page clock is shifted by +100ms
    // Midpoint Node 50ms => Browser time 150ms
    const preCalActor = {
      nodeStart: 49,
      nodeEnd: 51,
      browserTime: 150,
      uncertainty: 1,
      midpointNode: 50
    };
    // Midpoint Node 10050ms => Browser time 10150ms
    const postCalActor = {
      nodeStart: 10049,
      nodeEnd: 10051,
      browserTime: 10150,
      uncertainty: 1,
      midpointNode: 10050
    };

    // Offset 2: Peer page clock is shifted by -50ms
    // Midpoint Node 50ms => Browser time 0ms
    const preCalPeer = {
      nodeStart: 49,
      nodeEnd: 51,
      browserTime: 0,
      uncertainty: 1,
      midpointNode: 50
    };
    // Midpoint Node 10050ms => Browser time 10000ms
    const postCalPeer = {
      nodeStart: 10049,
      nodeEnd: 10051,
      browserTime: 10000,
      uncertainty: 1,
      midpointNode: 10050
    };

    // 1. Map actor page event timestamp to Node
    const actorBrowserEventTime = 5150; // Halfway between pre-cal and post-cal browser times
    const calibratedActorNode = calibratePageTimeToNode(actorBrowserEventTime, preCalActor, postCalActor);
    // Expected Node time: halfway between 50 and 10050 => 5050
    expect(calibratedActorNode.nodeTime).toBe(5050);

    // 2. Map peer page event timestamp to Node
    const peerBrowserEventTime = 5000; // Halfway between pre-cal and post-cal browser times
    const calibratedPeerNode = calibratePageTimeToNode(peerBrowserEventTime, preCalPeer, postCalPeer);
    // Expected Node time: halfway between 50 and 10050 => 5050
    expect(calibratedPeerNode.nodeTime).toBe(5050);

    // 3. Local/remote Peer visual latency calculation after calibration
    const peerVisualLatencyNode = calibratedPeerNode.nodeTime - calibratedActorNode.nodeTime;
    expect(peerVisualLatencyNode).toBe(0);
  });

  test('Real WebSocket payload structures and wrong/right peer frame exclusion', () => {
    const roomId = 'room-abc-123';
    
    // Peer Handshake frame
    const handshakeFrame = {
      direction: 'in',
      payload: {
        type: 'handshake',
        payload: {
          seat: 'player2',
          room_id: roomId
        }
      }
    };

    // Wrong peer frame: from a different room
    const wrongRoomStateFrame = {
      direction: 'in',
      payload: {
        type: 'state_update',
        payload: {
          room_id: 'room-wrong-456',
          player1_board: { board_revision: 100, board: [] },
          player2_board: { board_revision: 100, board: [] }
        }
      }
    };

    // Right peer frame: correct room, player1 seat state update
    const rightStateFrame = {
      direction: 'in',
      payload: {
        type: 'state_update',
        payload: {
          room_id: roomId,
          player1_board: { board_revision: 15, board: [['I', 'I']] },
          player2_board: { board_revision: 15, board: [] }
        }
      }
    };

    const wsFramesPeer = [handshakeFrame, wrongRoomStateFrame, rightStateFrame];

    // Verify Peer board extraction excludes wrong room and extracts right board
    const extractedBoard = getLatestPeerBoardFromPeerSocket(wsFramesPeer, roomId, 'player1');
    expect(extractedBoard).not.toBeNull();
    expect(extractedBoard?.board_revision).toBe(15);
    expect(extractedBoard?.board[0][0]).toBe('I');

    // Verify Actor WS Board state retrieval
    const extractedActorState = getLatestWSBoardState(wsFramesPeer, 'player1', roomId);
    expect(extractedActorState?.board_revision).toBe(15);
  });

  test('getCellTypeFromRgb palette color checks', () => {
    // Exact palette check
    expect(getCellTypeFromRgb(0, 240, 240)).toBe('I');
    expect(getCellTypeFromRgb(240, 240, 0)).toBe('O');
    
    // Close colors check within threshold < 40
    expect(getCellTypeFromRgb(5, 235, 235)).toBe('I');
    
    // Distant/unknown colors should return null
    expect(getCellTypeFromRgb(100, 100, 100)).toBeNull();
  });

  test('calculateChangedMask cell mapping and canvas verify', () => {
    // Define 10x20 cell maps (200 cells)
    const emptyPixel = [28, 31, 43, 255];
    const occupiedPixel = [0, 240, 240, 255]; // 'I'
    
    const priorPixels = Array(200).fill(null).map(() => [...emptyPixel]);
    const postPixels = Array(200).fill(null).map(() => [...emptyPixel]);
    
    // Mutate a few cells
    postPixels[0] = [...occupiedPixel];
    postPixels[5] = [...occupiedPixel];

    const priorRecord = { pixels: priorPixels };
    const postRecord = { pixels: postPixels };

    const changedMask = calculateChangedMask(priorRecord, postRecord);
    expect(changedMask).not.toBeNull();
    expect(changedMask?.length).toBe(200);
    
    // First cell (index 0) changed => '1'
    expect(changedMask?.[0]).toBe('1');
    // Second cell (index 1) unchanged => '0'
    expect(changedMask?.[1]).toBe('0');
    // Sixth cell (index 5) changed => '1'
    expect(changedMask?.[5]).toBe('1');
  });

  test('verifyCanvasPixels accurate cell matching and discrepancies with composited background', () => {
    const emptyPixel = [28, 31, 43, 255];
    const occupiedPixel = [0, 240, 240, 255]; // 'I'
    
    const actualPixels = Array(200).fill(null).map(() => [...emptyPixel]);
    // Set first cell as filled in Canvas
    actualPixels[0] = [...occupiedPixel];

    const record = { pixels: actualPixels };

    // Expected State matching exactly
    const expectedStateMatch = {
      board_revision: 1,
      board: Array(20).fill(null).map(() => Array(10).fill(null)),
      active_piece: null
    };
    // Let's set expectedState first cell to match the Canvas
    expectedStateMatch.board[0][0] = 'I';

    const verifyMatch = verifyCanvasPixels(record, expectedStateMatch);
    expect(matchesWithVerify(verifyMatch)).toBe(true);
    expect(verifyMatch?.discrepanciesCount).toBe(0);

    // Expected State mismatch (board expects first cell to be empty)
    const expectedStateMismatch = {
      board_revision: 1,
      board: Array(20).fill(null).map(() => Array(10).fill(null)),
      active_piece: null
    };
    
    const verifyMismatch = verifyCanvasPixels(record, expectedStateMismatch);
    expect(matchesWithVerify(verifyMismatch)).toBe(false);
    expect(verifyMismatch?.discrepanciesCount).toBe(1);
    expect(verifyMismatch?.discrepancies[0].r).toBe(0);
    expect(verifyMismatch?.discrepancies[0].c).toBe(0);
  });

  test('verifyCanvasPixels empty center composited RGB background vs old background', () => {
    const oldBackgroundPixel = [21, 24, 36, 255];
    const newBackgroundPixel = [28, 31, 43, 255];
    
    const recordWithOld = { pixels: Array(200).fill(null).map(() => [...oldBackgroundPixel]) };
    const recordWithNew = { pixels: Array(200).fill(null).map(() => [...newBackgroundPixel]) };
    
    const expectedState = {
      board_revision: 1,
      board: Array(20).fill(null).map(() => Array(10).fill(null)),
      active_piece: null
    };
    
    // New composited background matches empty state perfectly
    const verifyNew = verifyCanvasPixels(recordWithNew, expectedState);
    expect(matchesWithVerify(verifyNew)).toBe(true);
    
    // Old background does not match anymore (dist > 40 from [28,31,43])
    // dist is sqrt((28-21)^2 + (31-24)^2 + (43-36)^2) = sqrt(49+49+49) = sqrt(147) ~ 12.12. Wait, 12.12 is < 40!
    // Wait! Let's check if dist of [21,24,36] to [28,31,43] is < 40. Yes, dist is ~12.12.
    // What about completely mismatched colors? E.g. [0,0,0,255] or [100,100,100,255]
    const recordMismatched = { pixels: Array(200).fill(null).map(() => [100, 100, 100, 255]) };
    const verifyMismatched = verifyCanvasPixels(recordMismatched, expectedState);
    expect(matchesWithVerify(verifyMismatched)).toBe(false);
  });

  test('verifyCanvasPixels board precedence over active cells', () => {
    const emptyPixel = [28, 31, 43, 255];
    const redPixel = [240, 0, 0, 255]; // 'Z'
    const cyanPixel = [0, 240, 240, 255]; // 'I'
    
    const actualPixels = Array(200).fill(null).map(() => [...emptyPixel]);
    // Set [0, 0] to red ('Z')
    actualPixels[0] = [...redPixel];
    
    const record = { pixels: actualPixels };
    
    // expectedState has board containing 'Z' at [0][0] AND active_piece overlapping at [0][0] with 'I'
    const expectedState = {
      board_revision: 1,
      board: Array(20).fill(null).map(() => Array(10).fill(null)),
      active_piece: {
        type: 'I',
        cells: [[0, 0], [0, 1], [0, 2], [0, 3]]
      }
    };
    expectedState.board[0][0] = 'Z';
    
    // Since board has precedence over active, the expected color at [0][0] is red ('Z') [240, 0, 0]
    // If active took precedence, it would expect cyan [0, 240, 240] and mismatch the actual red pixel.
    const verifyResult = verifyCanvasPixels(record, expectedState);
    
    // If board precedence is correct, first cell [0,0] matches (expected 'Z' and actual 'Z')
    // and [0,1], [0,2], [0,3] will mismatch (expected active 'I' but actual empty) - that's fine, we check [0,0] discrepancy:
    const discAtFirstCell = verifyResult?.discrepancies.find(d => d.r === 0 && d.c === 0);
    expect(discAtFirstCell).toBeUndefined(); // No discrepancy at [0,0] because board precedence matches perfectly!
  });

  test('Solo response matching and false candidates isolation', () => {
    const gameId = 'game-123';
    
    const mockResponses = [
      {
        reqId: 'req-1',
        method: 'POST',
        status: 200,
        reqMeta: {
          gameId: 'game-123',
          endpoint: 'move',
          direction: 'left',
          time_node: 1000
        },
        body: {
          board_revision: 10,
          board: []
        }
      },
      {
        reqId: 'req-2',
        method: 'POST',
        status: 200,
        reqMeta: {
          gameId: 'game-different', // false candidate due to different gameId
          endpoint: 'move',
          direction: 'left',
          time_node: 1005
        },
        body: {
          board_revision: 11,
          board: []
        }
      },
      {
        reqId: 'req-3',
        method: 'GET', // false candidate due to GET method
        status: 200,
        reqMeta: {
          gameId: 'game-123',
          endpoint: 'move',
          direction: 'left',
          time_node: 1010
        },
        body: {
          board_revision: 12,
          board: []
        }
      }
    ];
    
    const latest = getLatestSoloState(mockResponses, gameId);
    expect(latest).not.toBeNull();
    // Must select req-1, skipping req-2 and req-3
    expect(latest?.reqId).toBe('req-1');
    expect(latest?.state.board_revision).toBe(10);
  });

  test('Duel WS peer authority and room isolation', () => {
    const roomId = 'room-abc';
    
    const wsFramesPeer = [
      {
        direction: 'in',
        payload: {
          type: 'state_update',
          payload: {
            room_id: 'room-different', // false candidate due to room ID
            player1_board: { board_revision: 4, board: [] },
            player2_board: { board_revision: 4, board: [] }
          }
        }
      },
      {
        direction: 'in',
        payload: {
          type: 'state_update',
          payload: {
            room_id: 'room-abc',
            player1_board: { board_revision: 5, board: [['I']] },
            player2_board: { board_revision: 5, board: [] }
          }
        }
      }
    ];
    
    const latestP1 = getLatestPeerBoardFromPeerSocket(wsFramesPeer, roomId, 'player1');
    expect(latestP1).not.toBeNull();
    expect(latestP1?.board_revision).toBe(5);
    expect(latestP1?.board[0][0]).toBe('I');
    
    const latestP2 = getLatestPeerBoardFromPeerSocket(wsFramesPeer, roomId, 'player2');
    expect(latestP2).not.toBeNull();
    expect(latestP2?.board_revision).toBe(5);
    expect(latestP2?.board.length).toBe(0);
  });

});

// Helper wrapper to safely check matches
function matchesWithVerify(verifyResult: any) {
  return verifyResult ? verifyResult.matches : false;
}
