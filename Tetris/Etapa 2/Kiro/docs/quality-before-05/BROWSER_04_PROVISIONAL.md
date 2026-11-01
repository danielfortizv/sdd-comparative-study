# Provisional real-browser observations — invocation04 candidate

Researcher observations on October21,2026 America/Bogota. Backend served the Kiro Stage2 app at127.0.0.1:8000; Vite5.4.21 served its generated frontend at127.0.0.1:5173, one of the preserved CORS origins. Both processes were started by the researcher, separate from Kiro generation. No browser state injection or API calls from page evaluation were used.

- Initial rendered HUD: Score0, Lines0, Level1; NextO, Hold empty; Hold enabled.
- Clicking Hold changed the accessible state to NextI, HoldJ and disabled Hold. The screenshot captured in that same UI call retained an earlier painted frame, so **04-provisional-hold-button.jpg is not taken as visual proof of the updated Hold result**. The accessible state did update. Preserve this artifact as a capture timing limitation.
- Clicking Restart reset the rendered HUD to0/0/1, NextO, Hold empty and enabled Hold.
- Pressing the actual keyboard C shortcut changed the accessible state to NextI, HoldJ and disabled Hold. A subsequent separate screenshot visibly confirms the heldJ and previewI. Evidence: screenshots/04-provisional-c-key-hold.jpg.
- The HTML document title still says Stage1 although the page heading says Stage2; included in the next native Kiro correction.

These observations cover part of S2-17 and restart behavior, not the full20-ID catalog. They do not establish dynamic gravity timing, race safety or game-over cleanup. External deferred-transport tests independently found three concurrency failures, retained under docs/acceptance. The candidate remains provisional while invocation04 and correction/quality work continue.

The Google Doc received these provisional findings, caveats and the real C-key screenshot; readback verified the appended paragraphs at revisionAHj4eMT0u3APzZUd3AQWZf_pDID0JrC9T5diaBA2g8v32waeZ9I80D__MmEIOIrfFj99ZdLrOwPneAtTzM2YMQQrOSXcL4HCpd4EpYL_mA. New inline image IDkix.eqokf2imtycz. PDF page-fit verification remains pending.
