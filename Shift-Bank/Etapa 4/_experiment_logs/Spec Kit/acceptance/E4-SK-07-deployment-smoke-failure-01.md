# E4-SK-07 deployment smoke failure 01

- Command: isolated Stage 4 smoke script through Nginx at `https://localhost:18443` and `http://localhost:18080`, project `e4sk07`.
- Outcome: deployment health, routing, currency accounts, and the first encrypted versioned USD transfer reached the projection checkpoint assertion; the run stopped there.
- Observed response from `GET /api/projections/status`: `latest_event_sequence=9`, `checkpoint_sequence=8`.
- The smoke test asserted these values were equal before replay. No production or inherited database was used; the deployment used a fresh project-scoped volume.
- This is preserved as a real verification failure pending diagnosis. No expected result was weakened to obtain a pass.
