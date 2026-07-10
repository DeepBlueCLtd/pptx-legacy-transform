# Implementation Plan: Import Author Gram Images

**Branch**: `claude/gram-image-matching-metadata-365z6d` (spec dir `011-import-gram-images`) | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/011-import-gram-images/spec.md`

## Summary

A new prep-time stage converts wav-only grams to pre-rendered-image grams using
the author's analysis-tool screenshots, delivered in a parallel *incoming* tree
(`incoming/<doc>/<gram>/` ↔ `source/<doc>/<container>/<gram>/`, the container
being the single subfolder of each source doc folder) with filenames of the form
`<duration> <wav-stem>.<jpg|jpeg|png>`. Phase 1 (**verify**, default,
read-only) matches folders and image stems against the wavs referenced by each
gram folder's `.glc` files and writes a mismatch report (nearest candidates,
unparseable-duration survey, trend grouping); the operator fixes the incoming
tree and re-runs. Phase 2 (**apply**, explicit flag) copies each matched image
beside its `.glc` renamed to the wav's stem, rewrites the `.glc`'s
`<filename>`, and inserts `<bitmap_crop_values><bottom_crop>N</bottom_crop>
</bitmap_crop_values>` (duration in integer seconds) so a fresh extract reads
it as `time_end`. The `.wav` is deliberately left in place (divergence from
`relink_glc_to_image.py`); idempotency rides on the "GLC already references an
image" skip. Delivered as one new canonical script + one new root wrapper,
alongside the existing relink flow.

## Technical Context

**Language/Version**: Python 3.9 (WinPython 3.9.4.0 floor); `from __future__ import annotations`
**Primary Dependencies**: None new — stdlib only (`pathlib`, `re`, `difflib`, `shutil`, `argparse`, `logging`); reuses `parse_glc` from `extract_to_csv.py` (sibling import, as `relink_glc_to_image.py` already does)
**Storage**: Files — incoming tree (read-only), source tree (`.glc` rewritten, image copied in), report file + log in cwd
**Testing**: stdlib `unittest` (`python -m unittest discover tests/`), synthetic trees built in `tempfile` dirs; no Jest impact (no HTML-facing change until a later extract/generate run)
**Target Platform**: Air-gapped Windows (WinPython REPL wrapper); dev hosts POSIX
**Project Type**: Single-project CLI pipeline (`scripts/` canonical + root REPL wrappers)
**Performance Goals**: N/A (batch; ~15 docs, ~1,000 grams; sub-minute)
**Constraints**: Determinism/idempotency; incoming tree strictly read-only; warn-and-skip never guess; dual logging; no network
**Scale/Scope**: 1 new canonical script, 1 new wrapper template, 1 new test module, README/CLAUDE.md docs; zero changes to existing stages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Air-Gapped, Self-Sufficient Operation** — PASS. Zero new dependencies;
  pure stdlib. `difflib` (nearest-candidate suggestions) is stdlib and
  deterministic. Python 3.9 syntax. Dual logging (`ingest.log` + stdout) plus a
  plain-text report file readable in Notepad — the operator's fix-up loop needs
  no tooling beyond a file manager.
- **II. Single-Purpose Scripts, Minimal Surface** — PASS with justification.
  This is a **new script**, not the smallest change to an existing stage, which
  II asks us to prefer. Justification: the pipeline's shape is one script per
  stage, and this *is* a new stage — a second, differently-shaped image-intake
  flow (parallel tree, duration metadata, wav retained) whose matching model
  shares almost nothing with `relink_glc_to_image.py`'s same-folder
  `Image <N>` model. Folding both into one script would couple two matching
  grammars and two wav-disposition policies behind mode flags — more surface,
  not less. The spec (FR-015) mandates the separate tool. GLC read/rewrite
  logic is reused, not duplicated (see research R6).
- **III. Test-First Discipline** — PASS. New `tests/test_ingest_gram_images.py`
  covers duration parsing, container resolution, folder/stem matching, report
  classes and grouping, apply mutations (copy/rewrite/insert), idempotent
  re-run, read-only verify, and every warn-and-skip class. Suite green before
  merge.
- **IV. Human-in-the-Loop Authority** — PASS. The whole feature is built
  around warn-and-defer: verify mode exists solely to put ambiguity in front
  of the operator; apply never guesses (ambiguous/unmatched/already-converted
  all skip with warnings and summary counts).
- **V. Deterministic, Idempotent Output** — PASS. Sorted iteration everywhere;
  report content is a pure function of the two trees (no timestamps in the
  report body); byte-preserving targeted GLC edits; `shutil.copyfile` (content
  only, no metadata) for the image copy; second apply run is a no-op.
- **VI. Honest Limitations** — PASS. The deliberate divergence from
  `relink_glc_to_image.py` (wav left in place) is documented in both scripts'
  docstrings and README; the `Nm`/`NmSSs`-only duration grammar and the
  "extend-on-evidence" posture for other formats are stated in the spec and
  README.
- **VII. Strict on Self-Authored Data** — PASS. Everything this tool consumes
  is Zone B/C (author-typed names, legacy GLCs): mismatches and malformed GLCs
  warn-and-skip, never crash the run. The tool *produces* GLC edits; it
  guards its own output by failing loud (per-file, with skip) if a targeted
  rewrite cannot find its anchor — never writing a half-edited file.

**Development-Phase Posture**: Pre-production — the new report format and CLI
are unbound by compatibility; the existing relink flow is untouched.

One justified II note above → Complexity Tracking table omitted (no violation;
the constitutionally preferred shape *is* one script per stage).

## Project Structure

### Documentation (this feature)

```text
specs/011-import-gram-images/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 — decisions (naming, grammar, matching, rewrite mechanics)
├── data-model.md        # Phase 1 — entities, outcome classes, report shape
├── quickstart.md        # Phase 1 — how to verify
├── contracts/
│   └── ingest-contract.md   # CLI, matching rules, report format, GLC rewrite delta
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
ingest.py                        # NEW root wrapper template (REPL: exec(open(r"ingest.py").read()))
scripts/
└── ingest_gram_images.py        # NEW canonical stage: verify/apply, matching, report, GLC rewrite

tests/
└── test_ingest_gram_images.py   # NEW: stdlib unittest over synthetic tempfile trees

README.md                        # wrapper table, target layout, "Running on the air-gapped target"
CLAUDE.md                        # cold-start wrapper list + plan pointer (SPECKIT block)
```

**Structure Decision**: Single-project pipeline; one new canonical script
fronted by one new wrapper, mirroring the `relink.py` ↔
`relink_glc_to_image.py` pair (`ingest.py` ↔ `ingest_gram_images.py`). No
change to any existing stage: `extract_to_csv.py` already reads `bottom_crop`
as `time_end`, and `generate_dita.py` already dispatches on the GLC's inner
extension, so the conversion is complete once the GLC is rewritten. The
release packager discovers wrappers and `scripts/*.py` by glob, so the new
files ship without packager changes (verified in research R8).

## Phase 0 — Research

See [research.md](./research.md). Resolves: script/wrapper naming (R1),
duration grammar and regex (R2), matching pipeline and already-converted
classification (R3), nearest-candidate + trend grouping mechanics (R4), report
file format and location (R5), GLC reuse and rewrite/insert mechanics (R6),
copy semantics (R7), packaging/docs impact (R8).

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — trees, matches, outcome taxonomy, report
  sections, tally.
- [contracts/ingest-contract.md](./contracts/ingest-contract.md) — CLI
  surface, matching rules, duration grammar, report format, GLC rewrite delta
  (the canonical `glc-schema.md` needs no change: `bottom_crop` is already a
  documented, parsed element).
- [quickstart.md](./quickstart.md) — verification steps.
- Agent context (`CLAUDE.md`) plan pointer updated to this plan.
