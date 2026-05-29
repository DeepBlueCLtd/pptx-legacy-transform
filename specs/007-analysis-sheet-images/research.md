# Phase 0 Research: Analysis-Sheet Images

This file resolves the open questions raised by the spec's Assumptions and by
the Constitution Check, so Phase 1 design rests on settled decisions.

## R1 — How to turn a Word document (`.doc` and `.docx`) into a page image

**Decision**: Shell out to **LibreOffice headless** as the default renderer
(`soffice --headless --convert-to png --outdir <tmp> <doc>`), behind a
configurable `--renderer-cmd`. Treat it as an external, installed-by-the-user
tool, never a Python dependency.

**Rationale**:
- It handles **both** the legacy binary `.doc` (OLE2 compound format) and
  `.docx` (OOXML) with one invocation — the key requirement (FR-002). Legacy
  `.doc` is the format the older decks use and the one with no good pure-Python
  parser.
- It renders the laid-out page, preserving the eye-aligned text blocks the spec
  forbids us from parsing logically (FR-003).
- The project already accepts exactly this posture for DITA-OT (feature 001
  FR-021): an external toolchain, documented in the README, transferred across
  the air-gap by the maintainer, not bundled and not a runtime Python
  dependency — so it costs nothing against Principle I that the project hasn't
  already accepted.

**Alternatives considered**:
- *Parse the binary `.doc` in pure Python and re-emit a DITA `<table>`.*
  Rejected: legacy `.doc` table structure lives in the `WordDocument` binary
  stream as paragraph/row marks + `sprm` property runs; pure-Python parsers are
  fragile/unmaintained, and — decisively — the "tables" are visually aligned
  text blocks, so a logical parse would silently corrupt them (the spec's core
  finding). This is the option the user explicitly ruled out.
- *MS Word COM automation (`win32com`).* Rejected as the default: Windows/Word-
  only, not scriptable on the dev VM, and a heavier automation surface than a
  one-shot `subprocess` convert. It remains usable via `--renderer-cmd` for a
  site that prefers it.
- *`.doc → PDF → PNG` (LibreOffice + poppler/pdftoppm).* Rejected for the MVP:
  adds a second external tool for a marginal quality gain on a single landscape
  page. The configurable command leaves the door open if legibility proves
  insufficient.
- *A Python-wheel renderer (no external tool).* The maintainer has cleared
  pulling additional Python wheels across the air-gap **if justified**, so this
  was evaluated explicitly. Finding: **no free/open-source Python wheel renders
  legacy binary `.doc` to a faithful page image** — rendering a Word document
  needs a Word *layout* engine, and the open-source ones are external
  (LibreOffice) or browser-based, not wheels. `python-docx` reads `.docx` only
  and cannot render; `mammoth`/`pydocx` go to HTML and discard the eye-aligned
  positioning (defeating FR-003); `weasyprint` renders HTML (not `.doc`) and
  drags in non-wheel system libs on Windows. The **only** pure-wheel paths that
  handle `.doc` rendering are the **commercial** engines (`Aspose.Words`,
  `Spire.Doc`), which bundle their own layout engine. Those would make the
  air-gap transfer a single wheel rather than an installer, but were rejected for
  the MVP because (a) they carry a license cost / page-limited free tiers, and
  (b) a heavyweight closed-source rendering engine the receiving team cannot
  inspect, debug, or replace without the internet cuts against Principle I's
  "debuggable after handover" more than an external LibreOffice install does.
  **Decision (confirmed by the maintainer): stay on external LibreOffice.** A
  commercial wheel remains a documented fallback if a single-artifact wheel
  install is later judged worth the license. Free wheels such as `Pillow` (PNG
  crop/DPI) or `pypdf` (page-count detection) are not load-bearing for the MVP
  and are not pulled in.

## R2 — Determinism vs. a non-reproducible renderer (Principle V)

**Decision**: Produce the PNG **once** and treat it as a **committed source
asset**; the normaliser is **idempotent** (skips any sheet that already has its
sibling `.png`). Downstream determinism is the existing `generate_dita.py`
`copy2` byte-for-byte copy.

**Rationale**: LibreOffice PNG bytes are not guaranteed identical across
versions/machines, so reproducing them on every run would violate byte-identity.
Instead the renderer runs outside the re-runnable loop (FR-006): once a gram
folder has its PNG, every subsequent generate/publish run copies the *same
committed bytes*, so two consecutive runs over an unchanged tree are
byte-identical (SC-004). This mirrors how feature 001 treats any other binary
source asset — the determinism contract is on *copying*, not on *re-rendering*.

**Alternatives considered**:
- *Re-render every run and pin LibreOffice + fonts for reproducibility.*
  Rejected: brittle (font availability, version drift) and pointless work; the
  committed-asset approach is simpler and strictly more robust on the air-gapped
  target.

## R3 — Page scope: single landscape page, and multi-page behaviour

**Decision**: Render the **first page** only and document the
single-landscape-page expectation as a known limitation (Principle VI). Do not
build automatic multi-page detection in the MVP.

**Rationale**: The user states the analysis sheets are, without exception, a
single landscape page with one table. `soffice --convert-to png` already yields
the first page. Reliable page-count detection would need either PDF
intermediate parsing or a document-model dependency — disproportionate to a
"without exception single page" corpus and against YAGNI (Principle II). Being
honest about the boundary (README + this note) is the constitution-aligned
response rather than silent best-effort.

**Open refinement (flagged for `/speckit-clarify`)**: the spec's edge case asks
for a *warning* on multi-page documents. Detecting that without a new dependency
is not free; the MVP downgrades it to a documented limitation. If the corpus
turns out to contain multi-page sheets, revisit (e.g. render via PDF and count
pages) — captured here rather than silently dropped.

## R4 — Naming and how the rendered PNG reaches the topic

**Decision**: Render to a **same-stem sibling** in the gram folder
(`analysis table.doc` → `analysis table.png`). The extractor redirects a `.doc`/
`.docx` analysis hyperlink to that sibling `.png`; the unchanged generator then
embeds it inline.

**Rationale**:
- The extractor already resolves the analysis sheet from the slide's hyperlink
  to a specifically-named file. A same-stem sibling is a deterministic,
  zero-configuration mapping from that target — no canonical filename to agree
  on, no new CSV column.
- It keeps the change to the smallest possible diff: `generate_dita.py` and the
  DITA topic shape are untouched because the analysis row simply now carries a
  `.png` `png_path` (which the generator already embeds inline,
  `_append_analysis_section` line 646).

**Alternatives considered**:
- *Feature 001's sketched FR-023 shape (canonical `Analysis.png` + a new
  `analysis_docx_path` CSV column).* Rejected: the canonical name requires the
  extractor to map an arbitrarily-named hyperlink target onto it, and the new
  column changes the CSV contract for no benefit this feature needs. The
  same-stem sibling is the smaller surface. (We note this divergence explicitly
  in the plan and update the 001 contracts to record that `analysis_docx_path`
  was never implemented and is not introduced.)

## R5 — Failure posture (Principle IV)

**Decision**: Renderer-unavailable, render-failure, corrupt/locked document, and
missing-sheet are all **WARNINGs that defer**: the normaliser logs per-sheet,
continues, and exits 0; the affected gram is surfaced in `normalise.log`, the
end-of-run summary, and — because the rendered `.png` is then absent — the
extractor records a warning in that analysis row's `warnings` column. The
generator still emits the topic with the intended `.png` href (dangling), so
dropping the image in later and re-running resolves it with no XML churn (FR-010).

**Rationale**: Direct application of the human-in-the-loop and missing-asset-
dangles invariants; an aborting batch or a silent drop is the failure mode the
air-gapped operator cannot afford. Exit 1 is reserved for genuinely unhandled
errors so `run_pipeline.bat`'s `errorlevel` check still catches real breakage.

## R6 — Keeping tests stdlib-only and LibreOffice-free (Principle I/III)

**Decision**: Tests drive the normaliser with `--renderer-cmd` pointing at a tiny
in-repo stub script that writes the project's **existing PNG byte template** (the
one `mock_pptx.py` already uses). The `.doc`/`.docx` inputs in tests are
placeholder files — the normaliser does not parse them, it only passes them to
the renderer — so no valid binary `.doc` and no LibreOffice install are needed.

**Rationale**: Preserves the air-gapped stdlib-only test contract while fully
exercising classify → render-or-skip → summarise and the failure paths
(stub exits 1). The full-pipeline tests get a deterministic `.doc`-sourced gram
via the `mock_pptx.py` "doc" variant, which ships the rendered sibling alongside.
