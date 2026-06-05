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
asset**; the snapshotter is **idempotent** (skips any sheet that already has its
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

**Decision (revised after `/speckit.review`)**: Render the **first page** as the
analysis image **and actively detect multi-page documents**, logging a WARNING
and flagging the affected CSV row when a sheet has more than one page. Do **not**
silently truncate.

**Why revised**: the original plan downgraded this to a documented-only
limitation, but the review identified it as the one **silent-partial-output**
risk — a stray multi-page sheet would lose pages 2+ with no signal, which the
constitution's no-silent-failures posture (Principle IV) forbids. The maintainer
chose detect-and-warn.

**Approach (no new Python dependency, no new external tool)**: reuse the same
LibreOffice renderer for a companion `--convert-to pdf` of the sheet and read the
page count from the produced PDF with a tolerant **stdlib** scan (e.g. the
`/Count` in the page-tree root, which LibreOffice writes in cleartext). Render
the page-1 PNG as before. If the count is `> 1`, log a WARNING and mark the
sheet's `SnapshotResult` so the extractor surfaces it in the row `warnings`. If
the count genuinely cannot be determined, emit a softer "page count
undetermined" WARNING rather than staying silent (Principle VI honesty).

**Rationale**: the corpus is single-page "without exception", so the warning
should almost never fire — its value is catching the exception that breaks the
assumption, cheaply, with tools already required. Full multi-page → multi-image
rendering is **out of scope** for this feature (the warning is the safety net);
if a real multi-page sheet ever appears, the warning makes it visible and the
behaviour can be extended then.

**Alternatives considered**: *PNG-count detection* (rejected — `soffice
--convert-to png` emits only page 1 for Writer docs, so the count is always 1);
*a PDF-parsing wheel like `pypdf`* (rejected — the cleartext `/Count` scan is
enough for a warning and avoids a dependency, consistent with R1).

## R4 — Naming and how the rendered PNG reaches the topic

**Decision**: Render to a **same-stem sibling** beside the source document
(`aaa_analysis.doc` → `aaa_analysis.png`). The extractor redirects a `.doc`/
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
missing-sheet are all **WARNINGs that defer**: the snapshotter logs per-sheet,
continues, and exits 0; the affected gram is surfaced in `snapshot.log`, the
end-of-run summary, and — because the rendered `.png` is then absent — the
extractor records a warning in that analysis row's `warnings` column. The
generator still emits the topic with the intended `.png` href (dangling), so
dropping the image in later and re-running resolves it with no XML churn (FR-010).

**Rationale**: Direct application of the human-in-the-loop and missing-asset-
dangles invariants; an aborting batch or a silent drop is the failure mode the
air-gapped operator cannot afford. Exit 1 is reserved for genuinely unhandled
errors so `run_pipeline.bat`'s `errorlevel` check still catches real breakage.

## R6 — Keeping tests stdlib-only and LibreOffice-free (Principle I/III)

**Decision**: Tests drive the snapshotter with `--renderer-cmd` pointing at a tiny
in-repo stub script that writes the project's **existing PNG byte template** (the
one `mock_pptx.py` already uses). The `.doc`/`.docx` inputs in tests are
placeholder files — the snapshotter does not parse them, it only passes them to
the renderer — so no valid binary `.doc` and no LibreOffice install are needed.

**Rationale**: Preserves the air-gapped stdlib-only test contract while fully
exercising classify → render-or-skip → summarise and the failure paths
(stub exits 1). The full-pipeline tests get a deterministic `.doc`-sourced gram
via the `mock_pptx.py` "doc" variant, which ships the rendered sibling alongside.

## R7 — On-disk layout and how the snapshotter selects analysis sheets

**Decision (added after `/speckit.review`, from maintainer input on the real
corpus)**: The snapshotter selects analysis documents by **filename pattern**
(`*analysis*`, case-insensitive) **plus** the `.doc`/`.docx` extension, scanning
the content tree. It does **not** render every Word document it finds.

**Why**: the real corpus does **not** put each analysis sheet in its own gram
folder. Analysis documents live in the **chapter folder alongside other files**,
including **PPT source data and other Word documents**. Two consequences:

1. A "render every `.doc`/`.docx` under the root" rule (a tempting simplification
   when the script can't see slide hyperlinks) is **wrong** — it would convert
   unrelated source documents. Selection therefore keys on the analysis naming
   convention the corpus already follows (`aaa_analysis.doc`), matching by
   `*analysis*` substring. This is Principle IV (never act on the wrong file)
   and Principle II (smallest correct rule).
2. The earlier per-gram-folder framing in `data-model.md`/`plan.md` was
   inaccurate; the snapshotter scans for `*analysis*.{doc,docx}` files anywhere
   under the content root and renders a sibling `.png` for each.

**Missing-sheet detection stays with the extractor**: because the snapshotter
selects only files that exist, it cannot meaningfully report a gram with *no*
analysis sheet. That gap is already detected and warned by the extractor
("missing analysis PNG hyperlink"), so the snapshotter drops the `"missing"`
outcome to avoid duplicating that responsibility (DRY).

**Alternatives considered**: *Drive selection from PPTX hyperlinks* (open each
deck, follow shape-level links) — rejected: it would pull `python-pptx` and
extraction logic into the prep stage, coupling two stages and enlarging the
surface for no benefit, since the name convention is sufficient. *A configurable
`--name-glob`* — deferred; the fixed `*analysis*` rule is adequate for the known
corpus and can be parameterised later if a deck deviates.

## R8 — Tidy inline image: margin-trim + DPI (FR-017)

**Decision (added after `/speckit.review`, maintainer chose to fold in)**: After
rendering, trim the page margins (whitespace) and normalise resolution so the
inline image is tight and crisp, using **Pillow** — but import it **defensively**
and fall back to the untrimmed full-page render (with an INFO line) when it is
absent. Never fail because of it.

**Why a dependency is acceptable here**: `soffice --convert-to png` renders the
whole landscape page, leaving margin whitespace at LibreOffice's default DPI, so
the raw inline image is loose and soft. The maintainer has cleared a *prep-time*
wheel where justified (see R1). The constitution's hard limits are the **one
runtime dependency** and **stdlib-only tests** — both preserved because Pillow is
imported only inside the prep-time snapshotter, behind `try/except ImportError`,
and the crop test runs under `unittest.skipUnless(PIL importable)` while the
fallback path is asserted unconditionally.

**Approach**: `tidy_image(png)` — open the PNG, compute the bounding box of
non-white content (`ImageChops.difference` against a white background →
`getbbox()`), crop to it with a small fixed margin, set the DPI on save. In place,
deterministic for a given input. On any `ImportError`/processing error: log once,
leave the full-page PNG untouched (FR-017 graceful degradation).

**Alternatives considered**: *ImageMagick `convert -trim` (external tool)* —
rejected: a third external binary to install/transfer for the air-gap when a
single wheel does it in-process. *No crop (page-as-is)* — rejected by the
maintainer; the loose margins/soft DPI were the specific complaint. *Stdlib-only
PNG cropping* — rejected: parsing/recompressing PNG pixels by hand is far more
code and risk than a guarded Pillow import.

## R9 — Reverse wrap: guarantee a `.docx` form too (FR-018)

**Decision (added after `/speckit.review`, maintainer chose to fold in)**: For an
analysis sheet that exists only as a `.png` (no Word source), emit a minimal
full-page `.docx` embedding that image, so every sheet has **both** an image and
a Word form. This is the bidirectional half of feature 001's FR-023, now in
scope.

**Why no new dependency**: the repo already authors a valid `.docx` with the
standard library — `mock_pptx.emit_docx` (line 313) builds the OOXML zip via
`zipfile` + `xml.etree`. `wrap_png_in_docx` reuses that exact pattern (including
the **fixed `date_time`** on each `ZipInfo`), so the output is byte-stable and
idempotent (Principle V) with zero dependency cost.

**Idempotency**: skip when a same-stem `.docx` already exists (mirrors the
PNG-skip rule). The `.docx` is a committed source asset like the `.png`.

**Scope note**: the `.docx` wrapper is for downstream consumers that need a Word
form; it is **not** what the DITA topic embeds (the topic still embeds the inline
`.png`). So this adds no generator/DITA-shape change — purely an extra committed
file beside the sheet.

**Alternatives considered**: *Leave it out (forward-only)* — was the original
plan; the maintainer reversed it to guarantee both forms. *python-docx* —
rejected: a dependency for something the stdlib `emit_docx` pattern already does.
