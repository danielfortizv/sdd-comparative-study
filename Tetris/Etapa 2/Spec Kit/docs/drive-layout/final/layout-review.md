# Final native Google Docs PDF layout review

Exported and reviewed the completed native Google Doc `1JRZvjK8-fdFitwbiKLe2NhOsk1FZNCa_TclgnFwdjao` after the final appendix was inserted. Readback revision matches the researcher's final revision:

`AHj4eMT1T-F27DXRu7SwEzAqGa7vmytdr01nXhCaCh2QxX3xb3l70FrET6kNLIASMUvgsL9xpVFRCQAndFMLcDIrjKSkWaTKtcHPDNvd8w`

Metadata reports last modification `2026-10-21T13:53:58.325Z`. No Drive write action or application/test/specification change was performed during this review.

## Result

No clipping, overlapping content, missing image edge, unreadable native table text, split table row, or orphaned image caption was found in the reviewed final pages. The earlier image-width/caption problems on historical pages 7-8 are repaired. No further layout repair is required for the final appendix's content to be readable and reviewable.

The actual exported native table font is **11.0 PT**, not the requested 10.5 PT. It is consistently readable; this is an observed rendering difference, not a legibility failure. Captions for the seven new images export at 9 PT, body text at 11 PT, and appendix headings at 16/18 PT.

## Saved evidence

- `drive-final.pdf`: 38 pages, 1,682,578 bytes.
- PDF SHA-256: `6B821EFEA26E45628B6DF43A405CE5C7B2CCC1EB71F1E0721323EB6766F119DC`.
- `export-provenance.json`: native ID/URL, metadata timestamp, matching revision, and PDF hash; no temporary authenticated download URL is retained.
- `layout-inventory.json`: geometry, image/table boxes, fonts and text for the complete PDF.
- `font-margin-check.json`: fonts measured inside actual native table boxes and aggregate margin results.
- `page-07.png`, `page-08.png`, and `page-16.png` through `page-38.png`: 25 pages rendered at 144 dpi and individually visually inspected. The remaining historical pages were not re-rendered; all-page geometry checks still include them.
- `page-01.txt` through `page-38.txt`: searchable text extracted for review. PNGs and the PDF determine visual layout; text extraction alone was not treated as visual proof.

## Measured margins and table text

The PDF media box is rounded to 596 by 842 PT. The native A4 content-width target was 451.2756 PT with nominal 72-PT margins. All 10 images remain inside the content margins in this export. The widest reviewed images occupy x=73.5 to 521.25 PT, width 447.75 PT, leaving space before the intended right content edge at 523.2756 PT. No image is outside the paper boundary.

The all-page check found **zero nonblank text characters outside the approximate horizontal 72-PT content margins**, zero image margin overruns, and zero image page-boundary overruns. Fourteen PDF table fragments correspond to the 12 native tables reported by document readback; two tables continue on subsequent pages. Character sizes inside all detected native table fragments are 11.0 PT.

## Captures and captions

| PDF pages | Visual review |
| --- | --- |
| 7-8 | Historical captures 2/3 now measure 447.75 PT wide, fit margins, and share the page with their respective preceding captions. No clipped last column or image edge. |
| 16-17 | Historical progress continuation is readable, with deliberate separation from the verified final appendix on page 18. |
| 18-30 | Final control/provenance, token/API/correction, artifact, quality, acceptance, and evidence-alias text/tables are readable. All 20 acceptance IDs remain visible with mechanisms and sources; domain-only labels remain legible. |
| 31-33 | Three actual local app screenshots are intact, with adjacent same-page captions. Initial HUD/board, occupied Hold/disabled control, and game-over modal are recognizable. The dark overlay in the game-over screenshot is intentional source UI; the modal remains readable. |
| 34-37 | Four derived panels are intact and clearly labeled as derived rather than native console/Sonar screenshots. Each caption remains on its image's page. Dense raster log/table detail benefits from zoom; the preceding native tables provide readable values at normal page scale. |
| 38 | Corpus/methodology limits are readable and not clipped. |

The first word of page 33's caption was additionally checked after an inline preview appeared to omit its beginning. The PDF contains the complete `Captura 6.` glyph sequence at x=72.0-114.0249 PT, top=73.349 PT, size 9 PT. A separate 216-dpi render, `page-33-caption-detail.png`, visually confirms the complete phrase. The apparent omission was a preview display artifact; the PDF/PNG does not require repair.

## Pagination observations

The auxiliary-model table starts on page 21 and continues with one whole row at the top of page 22. The Sonar comparison starts on page 25 and continues with two whole rows on page 26. Headers are not repeated on those short continuation fragments, but no row or value is cut or lost. The acceptance tables on pages 28-29 wrap the narrow `Estado` header across two lines; the text remains readable. These are nonblocking pagination/word-wrap observations, not missing content.

The source panels retain small embedded text as evidence images. Native tables and the original local evidence paths make their figures reviewable without relying on tiny raster text. This review does not re-run application tests or re-audit metric arithmetic; it verifies the final export's actual layout and legibility.
