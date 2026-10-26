# Read-only Google Docs layout review — pre-final snapshot

Reviewed the native Google Doc `1JRZvjK8-fdFitwbiKLe2NhOsk1FZNCa_TclgnFwdjao`, title “Tetris — Etapa 2: bitácora, métricas y evidencias de las cinco herramientas”. Drive metadata reported `application/vnd.google-apps.document`, modified `2026-10-21T01:28:56.275Z`. Exported through the authenticated Drive connector to PDF and materialized locally without changing the native document.

- Export: `drive-current.pdf`, 508,731 bytes, 15 pages.
- SHA-256: `26A379095CAC8BF62E34A831421907B25B97173B177904D2348130C719244CA6`.
- Page metadata and image boxes: `layout-inventory.json`; text extraction retained as `page-01.txt` through `page-15.txt`.
- Rendered at 144 dpi using bundled Poppler: `page-01.png`, `page-04.png`, `page-05.png`, `page-07.png`, `page-08.png`. All five were visually inspected at original PNG resolution.

## Findings

### Image margins overflow, but content is not clipped by the paper edge

The requested native A4 width is 595.2756 PT with 72-PT left/right margins, giving 451.2756 PT usable width and an intended right content edge at 523.2756 PT. This PDF rounds the media box to 596 by 842 PT.

| Page | Historical image | Actual PDF box (PT) | Result |
| --- | --- | --- | --- |
| 4 | Tetris UI, source 1440x1000 | x 73.5–503.25; width 429.75; top 117.14–415.64 | Fits content width and paper. Main board/panels are recognizable; small source UI labels require zoom. |
| 7 | Sessions/artifact metrics panel, source 1600x1300 | x 73.5–541.50; width 468.00; top 73.5–453.75 | Extends 18.2244 PT beyond the intended right content edge, while remaining entirely inside the paper. No clipped last column or image edge observed. |
| 8 | SonarQube/pruebas panel, source 1600x1450 | x 73.5–541.50; width 468.00; top 73.5–497.25 | Same 18.2244-PT content-margin overrun, with no actual paper-edge clipping. |

Do not describe these historical images as cropped or missing columns. They overflow the intended text margin. A source width at or below the available paragraph width is appropriate for future images; a conservative 449-PT width would fit even the observed 1.5-PT inset from the nominal left margin. Resizing alone will not improve dense-table readability.

### Dense screenshot tables are too small for comfortable normal-size reading

The metrics and Sonar source panels use 15-pixel table text, 14-pixel notes, and 13-pixel terminal text in 1600-pixel-wide screenshots. At the observed 468-PT document width this corresponds to approximately 4.39-PT table text, 4.10-PT notes, and 3.80-PT terminal text. The exported raster is sharp when zoomed, but those details are very small at ordinary printed/page scale. Summary cards are more readable.

The page-5 prose repeats the session and aggregate metrics at body-text size and remains readable. If final evidence must be readable directly in the document, split dense panels into narrower detail images or use native tables with explicit values, while retaining original screenshots and raw logs as evidence. Reducing the existing full panels to fit margins will make their small text slightly smaller still.

### Two captions are separated from their corresponding images

- `Captura 2` appears at the bottom of page 6; its metrics image starts on page 7.
- `Captura 3` appears below the metrics image on page 7; its Sonar image starts on page 8. This can initially look like a caption for the preceding image.
- `Captura 1` and its UI image remain together on page 4.

Keep each caption with the following image when preparing the final document, or adopt an unambiguous figure/caption convention. The historical source images themselves need not be altered for this pagination fix.

### Prose fits; no native tables exist in this snapshot

The Google Docs tables API returned an empty table list. The tables visible on pages 7 and 8 are raster content inside the two images, not editable Google Docs tables. The session records on page 5 are paragraphs with pipe separators.

Representative title/protocol content on page 1 and dense prose metrics on page 5 are readable, with no visible overlap or clipped lines. The PDF text-box check found no nonblank text characters outside the approximate 72-PT horizontal margins on any of the 15 pages. That geometry check supplements the inspected representative pages; it is not a claim that every page received visual review.

## Scope and limitations

This is the current pre-final native export, not a new report or a replacement document. No Google Drive/Docs write action was performed. No application, test, specification, or shared measurement code was edited. Only the local PDF copy, selected page PNGs, extraction inventory/text, and this review note were created.

PDF export and local rendering succeeded, so there is no export blocker. Two attempted partial Google Docs field masks returned an API 400 for mixing legacy fields with tab content; a full read succeeded, and the separate tables read succeeded. The layout findings are based on the actual exported PDF/PNGs, so that partial-read limitation does not prevent the stated conclusions.
