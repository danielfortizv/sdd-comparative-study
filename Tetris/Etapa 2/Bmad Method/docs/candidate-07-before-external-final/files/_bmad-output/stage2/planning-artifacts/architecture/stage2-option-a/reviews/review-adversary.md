# Adversarial and Compatibility Review — Stage 2 Tetris Study (Option A)

**Review Date:** October 25, 2026
**Reviewer:** Adversarial Lens (Vulnerability & Consistency Check)
**Harness/Delegation Override:** HEADLESS_NO_DELEGATION_HARNESS_OVERRIDE (Sequential Fallback active due to headless subagent-free execution)

---

## 1. Objective and Attack Strategy
This review attacks the feature-altitude `ARCHITECTURE-SPINE.md` to identify structural holes, race conditions, or uncoordinated states where individual components, following the stated ADs to the letter, could still construct incompatible behaviors or corrupt game states.

## 2. Adversarial Scenarios Evaluated

### Scenario A: The Restart Preemption Conflict
- **Attack Vector:** A user enqueues several movements in the FIFO queue. While these requests are in-flight, they click "Restart" multiple times. One team implements the frontend to immediately restart local state and reset the generation token, but lets the server-side restart request join the end of the previous FIFO queue. Another team implements the backend to process restart immediately, bypassing the FIFO queue.
- **Vulnerability:** If the server-side restart request is enqueued behind older movement requests on the client but executed immediately on the server, older in-flight movement requests (which carry the older session generation token) might arrive at the backend after the backend has already reset the game. Alternatively, the client resets its token locally, but old responses from the previous session are processed on the client because of race conditions.
- **Hole Mitigation in Revised Spine:** AD-9 point 5 and 6 and AD-10 completely closed this hole. Clicking Restart on the client must immediately preempt and discard the old mutation queue and clear any automatic timer *without* waiting for prior pending fetch/JSON requests to finish. The client updates its monotonically unique generation token instantly, so any late-arriving responses from prior requests are guaranteed to fail the ownership check and be safely discarded.

### Scenario B: The Illegal Move vs. Blocked Movement Collision
- **Attack Vector:** A player attempts to move left into a wall or downward into a settled block. One developer implements the backend to return an HTTP 422 error for these "illegal moves," since the piece cannot move there. The frontend developer, seeing an HTTP 422, treats it as a fatal API error, displays a "Network Error" HUD banner, or breaks the FIFO queue loop.
- **Vulnerability:** Under basic gameplay, colliding with walls or blocks is completely legal and a standard part of the game. Returning HTTP 422 for a normal collision (which is a standard "no-op" or "lock" event) breaks the decoupled thin client-server flow.
- **Hole Mitigation in Revised Spine:** AD-12 point 1 and 2 clarify the exact boundary. HTTP 422 is strictly reserved for *invalid direction payloads* (such as malformed structures or invalid direction parameters). Standard left/right collisions are treated as legal, valid movements that result in a no-op, returning HTTP 200 OK with the unchanged state. Downward blocked movements trigger the normal piece lock, row clear, and spawn sequence, also returning HTTP 200 OK.

### Scenario C: Accidental GameState Field Reset
- **Attack Vector:** When a movement or tick occurs, the backend reconstructs the `GameState` object. The developer implementing the movement branch creates a new `GameState` but fails to copy the score, level, lines, next piece, or hold piece fields, accidentally resetting them to their default values (0, 1, 500, null, null).
- **Vulnerability:** Moving left or right would wipe out the player's score, level, lines, or held piece!
- **Hole Mitigation in Revised Spine:** AD-7 points 1, 2, and 3 explicitly require all 7 Stage 2 fields to persist correctly across all horizontal moves, soft drops, ticks, rejected moves, and holds. Reconstruction or copying of the game state on the backend must never reset or use default values for these variables. A dirty scored/leveled state must be explicitly preserved through non-locking moves.

## 3. Review Verdict
With the integration of the revised AD-7, AD-9, and AD-12 constraints, the adversarial loops have been thoroughly resolved. The system is structurally robust against desynchronizations, premature state resets, and API mismatches.
