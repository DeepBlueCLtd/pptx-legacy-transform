# Implementation Plan: Instructor / Student Versions via DITA Audience Filtering

**Branch**: `claude/instructor-student-versions-6haQg` | **Date**: 2026-05-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-instructor-student-versions/spec.md`

## Summary

Produce two HTML editions — *instructor* (full content) and *student*
(answers redacted) — from one DITA source tree by running DITA-OT
twice: once with no audience filter, once with a DITAVAL profile that
excludes `audience="-trainee"`. The DITA generator already tags the
two largest carriers of instructor-only content (vessel-name decoration
inside the gram title, Analysis Sheet section) with `audience="-trainee"`;
this feature finishes the tagging story for two more cases — chapter
navtitles whose source names lead with "Instructor", and an
"Instructor Version" decoration on each publication's map title — and
then teaches `publish_html.py` to emit both editions into a tidy
`html/instructor/` + `html/student/` layout under a single shared
landing page at `html/index.html`.

No new Python dependencies. The intermediate CSV contract
(`source.csv`) and every script upstream of `generate_dita.py`
(`mock_pptx.py`, `introspect_pptx.py`, `extract_to_csv.py`) are
untouched. The only edited Python files are `generate_dita.py` and
`publish_html.py`; one new tiny artefact (`dita/trainee.ditaval`) is
committed alongside the source tree as the DITAVAL profile.

The MVP shape is User Story 1 (the student edition). Stories 2 and 3
fall out of the same code path: Story 2 is the unfiltered DITA-OT run
that this pipeline already does today, and Story 3 is the new shared
landing page plus per-edition index pages.

## Technical Context

**Language/Version**: Python 3.9+, no new third-party dependencies.
The codebase uses `from __future__ import annotations` throughout, so
modern type-hint syntax (`list[X]`, `X | None`) is evaluated as strings
and runs on 3.9. The air-gapped target ships WinPython 3.9.4.0, which
is the floor this feature is verified against.
The DITA generator and publisher use standard-library XML/text APIs
only, consistent with the air-gapped operating constraint from feature
001.

**Primary Dependencies**: The existing `python-pptx` dep is upstream of
this work and unaffected. DITA-OT (with bundled Java runtime) remains
the publish engine; this feature uses its built-in DITAVAL filtering
mechanism (the `--filter=` CLI flag), no DITA-OT plugin or extension.

**Storage**: Filesystem only. The single DITA source tree at `dita/`
gains one new sibling file (`dita/trainee.ditaval`). The output tree
at `html/` is restructured with two new top-level subdirectories
(`html/instructor/`, `html/student/`) replacing today's flat layout.

**Testing**: `unittest` discovery via `python -m unittest discover tests/`.
This feature extends `tests/test_generate_dita.py` (audience tags on
map titles and chapter navtitles, normalized chapter slugs) and
`tests/test_publish_html.py` (dual-edition layout, trainee-leakage
grep). No new test framework.

**Target Platform**: Windows workstations (air-gapped analyst PCs after
handover; internet-connected Windows VM during development). Linux/macOS
work for everything except `run_pipeline.bat`. Both editions are
delivered as static HTML readable in any modern browser; no runtime
backend.

**Project Type**: CLI/script tool. Two existing scripts are modified;
no library packaging.

**Performance Goals**: Two DITA-OT invocations per publication, run
sequentially. Whole-corpus publish target stays well under five minutes
on a developer workstation (no goal regression vs the existing
single-edition publish).

**Constraints**: Idempotency parity with feature 001 (FR-008 / SC-006)
— two consecutive publish runs over an unchanged DITA source produce
byte-identical HTML in both editions. The DITAVAL filter must be the
only mechanism that distinguishes the student edition from the
instructor edition; no per-edition source forking, copying, or
post-publish rewriting (FR-013). The student-edition output must
contain zero occurrences of the substring "instructor" (case-insensitive)
in any rendered text, page title, link label, or URL path below
`student/` (FR-015 / SC-002).

**Scale/Scope**: The same corpus feature 001 ships — one `main`
publication (~6 chapters, ~480 grams) plus five `progress-test-N`
publications (~30 grams each). Each publication is rendered twice per
publish run.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` is the
unmodified Spec Kit template — no concrete principles have been
ratified, so there are no formal gates to evaluate. The implicit
principles that features 001 and 002 honour also hold here:

- **Simplicity / YAGNI**: Reuse DITA-OT's built-in DITAVAL mechanism
  rather than custom filtering. One new file (`dita/trainee.ditaval`),
  no new Python dependency, no new top-level scripts.
- **Test-first**: New behaviour is covered by extensions to the two
  existing test modules. The quickstart serves as the executable
  acceptance check.
- **Observability**: The publisher logs which audience filter (if any)
  is applied for each edition (FR-011) so the air-gapped maintainer
  can confirm the right output from the build log alone.
- **Versioning / breaking changes**: The output layout under `html/`
  changes (existing top-level publication folders move into
  `instructor/` and `student/` parents). This is documented as an edge
  case in the spec — pre-existing deep links may need to be re-derived
  by the consumer; the new shared landing page (FR-006) is the
  authoritative entry point going forward.

**Result**: PASS — no ratified gates, design adheres to the implicit
principles above. Re-evaluated after Phase 1 (contracts, data model,
quickstart written): still PASS, no new violations introduced. The
Phase 1 surface area is one new 4-line DITAVAL file, two modified
existing scripts, and test extensions in their already-paired modules.

## Project Structure

### Documentation (this feature)

```text
specs/003-instructor-student-versions/
├── plan.md                  # This file (/speckit-plan output)
├── spec.md                  # Feature specification (/speckit-specify output)
├── research.md              # Phase 0 — decisions resolving open questions
├── data-model.md            # Phase 1 — editions, audience-tagged elements
├── quickstart.md            # Phase 1 — end-to-end walkthrough (verifies SC-001…SC-008)
├── contracts/
│   ├── audience-filter.md       # DITAVAL profile + DITA-side audience tags + rendered behaviour
│   └── html-edition-layout.md   # Dual-edition output tree, landing pages, URL parity
├── checklists/
│   └── requirements.md      # Spec quality checklist (already complete)
└── tasks.md                 # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
dita/
└── trainee.ditaval           # NEW — DITAVAL profile excluding audience='trainee'

generate_dita.py              # MODIFIED — chapter slug normalisation, audience-tagged
                              #   "Instructor " prefix on chapter navtitles,
                              #   audience-tagged "Instructor Version" suffix on map titles,
                              #   map titles emitted as <title> child element (not attribute)

publish_html.py               # MODIFIED — dual-edition publish (two DITA-OT runs per
                              #   ditamap), html/instructor/ + html/student/ layout,
                              #   new shared html/index.html, per-edition index pages

tests/
├── test_generate_dita.py     # EXTENDED — assert chapter-navtitle decomposition,
                              #   slug normalisation, map-title <title> shape with
                              #   audience-tagged "Instructor Version" suffix
└── test_publish_html.py      # EXTENDED — assert dual-edition folder layout, grep
                              #   for "instructor" leakage under html/student/,
                              #   verify URL parity at the gram-path level
```

`mock_pptx.py`, `introspect_pptx.py`, `extract_to_csv.py`, `source.csv`,
`run_pipeline.bat`, and `README.md` are unchanged by this feature
(FR-012). The `dita/` tree as currently committed will be regenerated
with normalised chapter slugs by re-running `generate_dita.py` against
`source.csv`; the regen happens as part of the implementation tasks
and the resulting source-tree changes are committed together with the
generator change.

**Structure Decision**: Same flat repository root as features 001 and
002 — two existing scripts are edited, one new artefact is added to the
DITA source tree, no new directories at the project root. The dual-edition
shape lives entirely inside `publish_html.py`'s logic plus the output
tree layout; the DITA source tree stays single-rooted (FR-013).

## Complexity Tracking

> No constitution violations to justify. No deviations from the simplest
> viable design — the dual-edition output is built on DITA-OT's
> standard audience-filtering mechanism with one new tiny config file.
