# Implementation Plan: Large Asset Deduplication with Reversible Provenance

**Branch**: `claude/optimistic-hawking-HpMvd` (developed on the existing working branch; no separate feature branch) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-large-asset-deduplication/spec.md`

## Summary

Make the DITA/HTML export shrink dramatically by writing **one** physical
copy of each large (>10 MB) duplicated asset and linking every other usage
back to that single master copy — reversibly. The mechanism is a new,
**optional** CSV column `master_png_path` populated by a new post-processing
script (`deduplicate_csv.py`), consumed at export time by `generate_dita.py`.

A redirected row no longer copies its asset into its own gram folder; instead
its lofar links to the master copy that already lives in the *first
occurrence's* gram folder (a relative `../…` href), and the lofar's
`<section>` carries a `<data name="original-asset-path" value="…"/>` element
recording where the file was meant to sit locally. That element alone marks
the lofar as redirected and — together with the master href — contains
everything a new reverse script (`rehydrate_dita.py`) needs to copy the master
back into the gram folder, re-localise the link, and delete the `<data>`
element, with no reference to the original extraction inputs.

The feature is **inert by default**: a CSV with no `master_png_path` column (or
an all-empty one) produces byte-for-byte identical output to today (FR-010,
SC-005). For the `.glc`/`.wav` audio pair the dedup unit is the pair: the
redirected `<xref>` targets the master `.glc`, and the large `.wav` stays
adjacent to that master `.glc` (FR-009).

The MVP is User Story 1 (redirect duplicates, write the master once). User
Story 2 (understand/reverse via `rehydrate_dita.py`) and User Story 3 (opt-in
post-processing) fall out of the same column and code paths.

**Edited/added files**: new `deduplicate_csv.py`, new `rehydrate_dita.py`,
modified `generate_dita.py`; `publish_html.py` is verified (and only touched if
DITA-OT does not carry cross-folder hrefs cleanly). `extract_to_csv.py` and
`introspect_pptx.py` are **not** modified (extraction is out of scope).

## Technical Context

**Language/Version**: Python 3.9+ (`from __future__ import annotations`
throughout, string-evaluated modern type hints), consistent with the
air-gapped WinPython 3.9.4.0 target carried from feature 001. No new
third-party dependencies — duplicate detection uses `hashlib` (stdlib) and the
existing `file_size` column; the export changes use only what
`generate_dita.py` already imports (`csv`, `shutil`, `xml.etree.ElementTree`,
`pathlib`).

**Primary Dependencies**: `python-pptx` (extractor only — untouched here).
DITA-OT 4.x for the HTML publish, used unchanged. No DITA-OT plugin, no DTD
specialisation — `<data>` is part of the standard DITA metadata domain and
validates without specialisation.

**Storage**: Filesystem only. The signed-off CSV gains one **optional**
right-edge column `master_png_path`, written by `deduplicate_csv.py` (the
extractor does not emit it). The generated DITA tree gains `<data>` elements on
redirected lofar `<section>`s; redirected grams no longer receive their own
copy of the large asset (the master gram's folder holds the one physical copy).

**Testing**: `python -m unittest discover tests/` for the CSV/DITA layers and
Jest (`tests/web/`) for rendered HTML. New module `tests/test_deduplicate_csv.py`
(detection, threshold, master nomination, blank-master warning, CSV round-trip),
new `tests/test_rehydrate_dita.py` (inverse-transform restores a
never-deduplicated topic; `.glc`/`.wav` restored together; no-op on un-redirected
lofars), and extensions to `tests/test_generate_dita.py` (redirected href points
to master, `<data>` emission, master written once, inert when column absent,
idempotency). HTML assertion (`tests/web/`) that a deduplicated asset is
referenced once.

**Target Platform**: Windows analyst workstations (air-gapped after handover);
Linux/macOS for development except `run_pipeline.bat`. Output is static HTML and
a DITA source tree.

**Project Type**: CLI/script tool. Two new top-level scripts, one modified;
no library packaging.

**Performance Goals**: `deduplicate_csv.py` hashes only candidate rows whose
`file_size` exceeds the threshold (a small minority — the large `.wav`s), so it
reads at most each large file once. The export adds one in-memory index pass
over the already-loaded rows (O(rows)); no extra disk I/O versus today, and it
*reduces* bytes written (the headline win). Re-export stays idempotent.

**Constraints**: Idempotency parity with features 001/004 — two consecutive
exports over an unchanged post-processed CSV produce byte- **and** stat-identical
output (FR-013, SC-006), preserved by deterministic row ordering and `copy2`
mtime preservation already in `generate_dita.py`. Inert-by-default byte-identity
(FR-010, SC-005) is preserved by reading `master_png_path` as an *optional*
column (empty default), never adding it to the strict required-column set in
`read_csv`. `<data>` must validate against the DITA DTD and be suppressed from
default trainee HTML (FR-006).

**Scale/Scope**: The feature 001 corpus (`main` ~6 chapters/~480 grams plus
several `progress-test-N`). The redirection targets the ~18% of grams whose
`.glc` configures live-from-`.wav` rendering — the large `.wav`s duplicated up
to ~10× are the headline >10 GB problem; images are rarely over threshold.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` is the unmodified
Spec Kit template — no concrete principles are ratified, so there are no formal
gates. The implicit principles features 001–005 honour also hold here:

- **Simplicity / YAGNI**: One new optional CSV column (the affordance), reusing
  the master gram's existing folder as the single physical home (no new
  `shared/` directory, no asset store). Detection reuses the existing
  `file_size` column plus stdlib `hashlib`. No new dependencies, no DTD
  specialisation, no DITA-OT plugin.
- **Backwards compatibility / inert-by-default**: Reading `master_png_path` with
  an empty default keeps legacy and current CSVs valid and byte-identical
  (FR-010), exactly how prior columns were introduced additively.
- **Reversibility as a first-class goal**: A single `<data>` element plus the
  master href is a complete inverse transform — no separate index, no lookup
  against extraction inputs (FR-008, FR-012).
- **Test-first**: Each new/changed code path gets focused assertions in the
  paired test module before the source change; the quickstart is the executable
  acceptance check for SC-001…SC-006.
- **Observability**: `deduplicate_csv.py` logs per-group redirect counts and
  reclaimed bytes; the generator logs how many lofars were redirected; blank or
  missing master targets are WARNINGs, not aborts (FR-014).

**Result**: PASS — no ratified gates; design adheres to the implicit principles.
Re-evaluated after Phase 1 (contracts, data-model, quickstart written): still
PASS, no new violations. The Phase 1 surface area is one optional CSV column,
one new `<data>` element on redirected lofar sections, two new top-level
scripts, and one modified generator with paired test extensions.

## Project Structure

### Documentation (this feature)

```text
specs/006-large-asset-deduplication/
├── plan.md                         # This file (/speckit-plan output)
├── spec.md                         # Feature specification (/speckit-specify output)
├── research.md                     # Phase 0 — decisions resolving open questions
├── data-model.md                   # Phase 1 — column, <data> element, master index, dedup unit
├── quickstart.md                   # Phase 1 — end-to-end walkthrough (verifies SC-001…SC-006)
├── contracts/
│   ├── csv-master-png-path.md      # The optional master_png_path column: shape, semantics, detection rules
│   ├── dita-provenance-data.md     # The <data name="original-asset-path"> element + redirected href shape
│   └── dedup-cli.md                # deduplicate_csv.py and rehydrate_dita.py CLI contracts
├── checklists/
│   └── requirements.md             # Spec quality checklist (complete)
└── tasks.md                        # Phase 2 output (created by /speckit-tasks — NOT here)
```

### Source Code (repository root)

```text
deduplicate_csv.py                  # NEW — post-process the signed-off CSV: detect >threshold
                                    #   duplicate assets by (file_size pre-filter + sha256 confirm),
                                    #   nominate the first occurrence (deterministic order) as master,
                                    #   append the optional `master_png_path` column and point the
                                    #   remaining occurrences at the master's png_path. Preserves the
                                    #   CSV's utf-8-sig / QUOTE_MINIMAL / CRLF contract. (FR-001, FR-002,
                                    #   FR-003, FR-014, US3)

rehydrate_dita.py                   # NEW — reverse a deduplicated DITA tree: find lofar <section>s
                                    #   carrying <data name="original-asset-path">, copy the master
                                    #   asset (and, for a pair, its adjacent .wav) back into the gram
                                    #   folder under the local slug recomputed from the original path,
                                    #   rewrite the lofar href to the local copy, and remove the <data>
                                    #   element. No-op on lofars without the record. (FR-008, FR-012, US2)

generate_dita.py                    # MODIFIED — read `master_png_path` via row.get(..., "") (optional;
                                    #   never added to the strict required-column set). Two-pass emit:
                                    #   (1) build a master index mapping a master row's png_path → its
                                    #   output location + link href; (2) for redirected rows, skip the
                                    #   local copy, compute the relative href to the master copy, and
                                    #   append <data name="original-asset-path" value="{row png_path}"/>
                                    #   to the lofar <section>. For .wav rows the link targets the master
                                    #   .glc. Blank/invalid master → treat as non-redirected + WARN.
                                    #   (FR-004, FR-005, FR-006, FR-007, FR-009, FR-010, FR-013, FR-014)

publish_html.py                     # VERIFIED — DITA-OT derives <img>/links from the DITA hrefs, which
                                    #   now point at the single master via ../ paths; confirm cross-folder
                                    #   hrefs carry through and the master file is emitted once (FR-011).
                                    #   Only edited if DITA-OT mishandles cross-folder hrefs (see research R3).

tests/
├── test_deduplicate_csv.py         # NEW — threshold (strictly > , at/below never redirected),
│                                   #   duplicate grouping by content, first-occurrence master,
│                                   #   blank-master WARN, unique-large untouched, CSV round-trip fidelity
├── test_rehydrate_dita.py          # NEW — restored topic equals a never-deduplicated one; .glc/.wav
│                                   #   restored together; no-op on un-redirected lofars; idempotent
├── test_generate_dita.py           # EXTENDED — redirected href points to master (not a local copy),
│                                   #   master binary written exactly once, <data> emitted on redirected
│                                   #   lofar only, inert/byte-identical when column absent, idempotency
└── web/
    └── (existing edition tests)    # EXTENDED — assert a deduplicated asset is referenced once in HTML

specs/001-pptx-dita-migration/contracts/csv-schema.md
                                    # MODIFIED — add a row documenting the optional, right-edge
                                    #   `master_png_path` column with the backward-compat note
specs/001-pptx-dita-migration/contracts/dita-topic-schema.md
                                    # MODIFIED — document the <data name="original-asset-path"> element
                                    #   on a redirected lofar <section> and the redirected href shape
```

`introspect_pptx.py`, `extract_to_csv.py`, `mock_pptx.py`, `run_pipeline.bat`,
and `README.md` are unchanged. The committed `dita/` tree is **not**
pre-deduplicated; deduplication is applied by running `deduplicate_csv.py` then
`generate_dita.py` against the post-processed CSV.

**Structure Decision**: Same flat repository root as features 001–005 — two new
top-level scripts (`deduplicate_csv.py`, `rehydrate_dita.py`) mirroring the
existing `verb_noun.py` convention, one modified generator, and test extensions
in paired modules. The single physical master copy lives in the **master gram's
existing output folder** (no new top-level output directory); redirected grams
reference it with relative `../` hrefs, which `resolve_image_href` already
supports.

## Complexity Tracking

> No constitution violations to justify. The one non-trivial choice — a
> two-pass export (build a master index, then emit) — is required because a
> redirected gram must reference a *different* gram's output location, which is
> only known after that gram's folder/slug is computed. The index pass is a
> cheap O(rows) walk over already-loaded CSV rows and introduces no new disk I/O.
> Everything else (column, `<data>` element, master-in-place) is the simplest
> shape that satisfies the spec.
