# Blog figures

Hand-drawn style diagrams and post covers, generated as PNGs into `assets/blog/`.

- `sketch.py` — the drawing helper (same one as the lab write-ups): boxes, arrows, blobs, tags,
  all jittered so they look pencil-drawn. Text is set in Patrick Hand, loaded from Google Fonts
  while Chrome renders the PNG, so the output matches the site's headings.
- One script per figure. Run `python3 figures/<name>.py` from the repo root; it writes the SVG and
  a wrapper HTML into `figures/build/` (ignored) and the 2x PNG into `assets/blog/`.
- Covers are 1200×630 so they double as the link-preview image (`og:image`).

Needs Google Chrome on the Mac and network access for the font.
