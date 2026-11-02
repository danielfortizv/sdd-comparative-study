# Scoped historical-image repair — Google research Doc

Only historical Captura 2/3 images were reinserted from the same original local PNG files at 448 PT width, preserving aspect ratio. Caption wording and all paragraph text/index positions are unchanged. The three-image count is preserved; Captura 1 and its object remain unchanged. Native caption2/3 paragraphs now use keepWithNext=true and each image paragraph uses false.

Native readback verified both repaired objects 448 PT wide. The authenticated PDF export is 17 pages and was rendered at 144 dpi with bundled Poppler. Pages 7/8 were visually inspected: each caption and its image share the same page, both images fit the content margin, and no clipping or overlap is visible. PDF boxes are x 73.5–521.25PT, 447.75 PT wide, within the intended right edge 523.2756 PT. Captura 1 stays 429.75 PT wide on page 4.

This is a layout repair, not final research acceptance. Historical raster-table type remains small; the final appendix must provide readable native tables. No old wording, metric history, screenshot pixels or final numbers were changed by this repair.

Artifacts: drive-repaired.pdf; layout-inventory.json; page-07.png; page-08.png. The first sandbox download attempt failed DNS resolution; the same authenticated exported file was then downloaded successfully through the approved command. No native document content was rebuilt.

PDF SHA-256: 8B6DCDD5D422E6D0AFA1AFD690F5490C0224BA7391CED8B1DA7F2A775B622C43.
