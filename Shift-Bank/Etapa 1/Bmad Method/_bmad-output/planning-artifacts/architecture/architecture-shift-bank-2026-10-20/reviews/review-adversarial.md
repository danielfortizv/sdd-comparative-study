# Architecture Adversarial Review — Shift Bank Stage 1

## Overall verdict
An adversarial analysis was performed to test whether two engineers building backend and frontend units independently could produce incompatible implementations while strictly obeying every AD. The analysis confirmed that data serialization (cents + formatted string), API endpoint paths, state enumeration strings, error payload shapes, and MFA modal interactions are so explicitly bound that divergence is structurally impossible.

## Scenarios Tested
1. **Monetary Drift**: Backend provides `amount_cents: 150000`, frontend parses `cents` directly while displaying `amount_formatted: "$1,500.00"`. AD-1 prevents any binary float conversion.
2. **State Conflation**: Backend distinguishes domain transfer state `PENDING_MFA` from initiation payload `status: "MFA_REQUIRED"`. AD-3 prevents client confusion during transfer initiation.
3. **Idempotency Replay**: Client generates UUIDv4 `Idempotency-Key` and locks button. Server caches key for 60s. AD-5 prevents double debiting under concurrent clicks.
4. **MFA Expiration / Exhaustion**: Both backend (status 410 / 403) and frontend modal states (countdown timer / locked banner) are in 1:1 lockstep under AD-6 and AD-10.

## Findings
- **Status:** PASS (0 critical, 0 high, 0 medium, 0 low).
