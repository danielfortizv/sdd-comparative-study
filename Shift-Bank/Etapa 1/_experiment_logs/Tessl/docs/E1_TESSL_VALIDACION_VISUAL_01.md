# Tessl — Stage 1 — Visual and Manual Functional Evaluation

## 1. Evaluation Identification

- Case study: Shift Bank.
- Stage: 1.
- SDD tool: Tessl.
- Evaluation date: November 3, 2026.
- Evaluation method: Browser screenshot inspection and user-reported interaction results.
- Application: React/TypeScript frontend with FastAPI backend.
- Frontend URL: `http://localhost:5173/`.
- Backend URL: `http://127.0.0.1:8000/`.

## 2. Application Startup

The original backend startup command failed because the Python module `backend` could not be imported when executing `python backend/run.py`.

The application was subsequently launched using:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The React frontend was launched using:

```powershell
npm --prefix frontend run dev
```

The application successfully rendered in the browser.

This adjustment changed the startup procedure only; no source-code correction was required.

## 3. Visual Inspection

The screenshot confirms the following elements:

| Component | Observed result |
|---|---|
| Application branding | Shift Bank, Stage 1 Mock |
| Mock user | Alex Morgan |
| User status indicator | Verified |
| Active accounts | 2 |
| Primary Checking | USD 2,500.00 |
| Standard Savings | USD 10,000.00 |
| Total net balance | USD 12,500.00 |
| Transaction history | 3 transactions visible |
| Transfer button | Present |
| Transaction filters | All Accounts, Primary Checking, Standard Savings |

The displayed account balances are consistent with the total net balance.

### Visual Quality

The interface presents:

- Clear navigation and banking account hierarchy.
- Consistent spacing and alignment.
- Distinct account cards.
- Legible balances and transaction descriptions.
- Color differentiation between positive and negative monetary transactions.
- Visually coherent banking dashboard design.

No obvious clipping, overlapping elements, or rendering failures were observed in the supplied desktop screenshot.

These observations apply to the supplied viewport only. Mobile responsiveness and accessibility were not independently evaluated.

## 4. User-Reported Functional Behavior

The user confirmed that all visible buttons function.

This constitutes positive manual interaction feedback, but no individual interaction log or screenshots of each resulting state were provided.

Therefore, this checkpoint records button functionality as user-reported rather than independently verified.

## 5. Evaluation Limitations

The screenshot alone does not establish:

- Successful persistence of a transfer.
- Exact MFA threshold handling.
- PIN validation and account lockout behavior.
- Updated account balances following a transfer.
- Transaction-history synchronization after a transfer.
- Responsive behavior on mobile devices.
- Automated accessibility compliance.

These behaviors have supporting implementation and automated-test evidence from previous checkpoints, but were not independently demonstrated by this visual inspection.

## 6. Conclusion

The Stage 1 Tessl application successfully rendered its primary dashboard, displayed the expected mock banking data, and received positive user feedback on visible button interactions.

The desktop interface is visually coherent and does not exhibit obvious layout defects.

This checkpoint supports a positive initial visual evaluation. Full end-to-end manual validation remains a distinct activity and should not be inferred solely from the dashboard screenshot.