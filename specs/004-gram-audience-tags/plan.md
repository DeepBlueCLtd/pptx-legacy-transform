# Implementation Plan: Per-Gram Audience Tags via CSV `audience` Column

**Branch**: `claude/zealous-tesla-lqGEa` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-gram-audience-tags/spec.md`

## Summary

Carry per-gram exclude-audience tags (`-own`, `-other`, …) from the
PPTX through a new 17th CSV column `audience` and out to an
`audience="…"` attribute on the gram's topicref inside each ditamap.
Replace feature 003's single student edition with two nation-specific
student editions (`student-own` excluding `-trainee -own`,
`student-other` excluding `-trainee -other`) and update the shared
landing page to list three editions. Delete the
`Instructor Progress Test 3 Grams No FR` duplicate publication from
the mock corpus generator — the per-gram tag is what makes the
duplication unnecessary.

No new Python dependencies. The CSV contract gains exactly one new
column appended at the right edge (17th column, position after
`warnings`). The DITA tree gains two new DITAVAL profiles; the
feature-003 `trainee.ditaval` stays in place and is composed with the
new ones, not replaced. The only edited Python files are
`extract_to_csv.py`, `generate_dita.py`, `publish_html.py`, and
`mock_pptx.py`.

The MVP shape is User Story 1 (Week 3 produces equal-size
`student-own` and `student-other` editions). User Story 2 (broaden
tagging by editing one CSV cell) and User Story 3 (drop the No-FR
duplicate publication) fall out of the same code paths.

## Technical Context

**Language/Version**: Python 3.9+, no new third-party dependencies.
Consistent with the floor established by feature 003 (`from __future__
import annotations` throughout, modern type-hint syntax evaluates as
strings, runs on 3.9). Verified against the air-gapped WinPython
3.9.4.0 target carried over from feature 001.

**Primary Dependencies**: `python-pptx` for the extractor (upstream,
unchanged shape — this feature only adds one regex pass to the
existing descriptor parser). DITA-OT 4.x for the publisher, used via
its built-in DITAVAL filtering mechanism (the `--filter=` CLI flag,
same mechanism feature 003 introduced). No DITA-OT plugin or
extension.

**Storage**: Filesystem only. `source.csv` gains one column (17th).
The `dita/` tree gains two new DITAVAL profiles next to the existing
`trainee.ditaval`. The `html/` output tree's three top-level
subdirectories change from `instructor/`+`student/` (feature 003) to
`instructor/`+`student-own/`+`student-other/`.

**Testing**: `unittest` discovery via `python -m unittest discover
tests/`. This feature extends `tests/test_extract_to_csv.py`
(audience-suffix stripping into the new column),
`tests/test_generate_dita.py` (topicref `audience=` attribute
emission, gram-row consistency check), `tests/test_publish_html.py`
(three-edition layout, Week 3 substitution semantics, idempotency).
No new test modules.

**Target Platform**: Windows workstations (air-gapped analyst PCs
after handover; internet-connected Windows VM during development).
Linux/macOS work for everything except `run_pipeline.bat`. All three
editions are delivered as static HTML readable in any modern browser.

**Project Type**: CLI/script tool. Four existing scripts modified;
no library packaging.

**Performance Goals**: Three DITA-OT invocations per publication
(instructor, student-own, student-other), run sequentially. Whole-
corpus publish target stays well under five minutes on a developer
workstation. The third edition adds roughly 30–50% to feature 003's
publish time (the bottleneck is DITA-OT startup per ditamap, which
scales linearly with edition count).

**Constraints**: Idempotency parity with features 001 / 003
(FR-014 / SC-004) — two consecutive publish runs over an unchanged
`source.csv` produce byte-identical HTML in all three editions.
Per-gram audience consistency across the rows of one gram is enforced
fail-fast at the DITA generation stage (FR-004 / SC-007); the
generator names the offending gram in its error message. The audience
attribute MUST land on the topicref, never on the topic file's root
element (FR-006).

**Scale/Scope**: The same corpus as features 001 / 003 minus one
publication. After this feature: `main` (~6 chapters, ~480 grams)
plus five `progress-test-N` publications (~30 grams each). Each
publication renders three times per publish run. The number of grams
that carry an `audience` value in the initial commit is exactly two
(both in Week 3 of `main`); the column is the affordance, not a
broad-stroke change to existing tagging.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` is the
unmodified Spec Kit template — no concrete principles have been
ratified, so there are no formal gates to evaluate. The implicit
principles that features 001, 002, and 003 honour also hold here:

- **Simplicity / YAGNI**: Reuse DITA-OT's built-in DITAVAL mechanism
  (already in place from feature 003). One new CSV column (the
  affordance), two new tiny DITAVAL profiles, one new regex pass in
  the extractor. No new Python dependencies, no new top-level scripts,
  no schema migration tooling — the CSV column is appended at the
  right edge so older CSVs read forward-compatibly.
- **Test-first**: Each existing test module gains a small focused
  block of assertions before its corresponding source file is changed.
  The quickstart serves as the executable acceptance check for the
  Week 3 substitution scenario.
- **Observability**: The DITA generator logs per-publication audience
  application counts (FR-015) and warns (without erroring) on unknown
  audience tokens (FR-016). The publisher continues to log which
  DITAVAL profile was applied per edition (carried over from feature
  003's FR-011).
- **Versioning / breaking changes**: The CSV column appendage is
  forward-compatible (a 16-column legacy CSV reads as if the 17th
  cell were empty on every row). The output tree's student
  subdirectory name changes — `html/student/` → `html/student-own/` +
  `html/student-other/`. This is documented as an edge case in the
  spec; the shared `html/index.html` is the authoritative entry point
  going forward (carried over from feature 003).

**Result**: PASS — no ratified gates, design adheres to the implicit
principles above. Re-evaluated after Phase 1 (contracts, data model,
quickstart written): still PASS, no new violations introduced. The
Phase 1 surface area is two new tiny DITAVAL files, one new CSV
column, four modified existing scripts, and test extensions in their
already-paired modules.

## Project Structure

### Documentation (this feature)

```text
specs/004-gram-audience-tags/
├── plan.md                    # This file (/speckit-plan output)
├── spec.md                    # Feature specification (/speckit-specify output)
├── research.md                # Phase 0 — decisions resolving open questions
├── data-model.md              # Phase 1 — audience column, topicref attr, editions trio
├── quickstart.md              # Phase 1 — end-to-end walkthrough (verifies SC-001…SC-007)
├── contracts/
│   ├── audience-csv-column.md      # CSV column shape, extractor parsing rules
│   ├── audience-dita-topicref.md   # DITA topicref `audience=` attribute, ditaval profiles
│   └── html-edition-trio.md        # Three-edition output tree, landing page layout
├── checklists/
│   └── requirements.md        # Spec quality checklist (complete)
└── tasks.md                   # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
dita/
├── trainee.ditaval              # unchanged (feature 003)
├── student-own.ditaval          # NEW — excludes audience='trainee' AND audience='own'
└── student-other.ditaval        # NEW — excludes audience='trainee' AND audience='other'

extract_to_csv.py                # MODIFIED — strip trailing [xxx] groups from the
                                 #   gram-descriptor right-hand side, write into the
                                 #   new `audience` column; write the 17th column
                                 #   header into every emitted CSV
generate_dita.py                 # MODIFIED — read `audience` column with empty default,
                                 #   assert consistency across same-gram rows, emit
                                 #   `audience="…"` attribute on the topicref in
                                 #   `emit_main_ditamap` and `emit_test_ditamap`, log
                                 #   per-publication tag counts
publish_html.py                  # MODIFIED — replace single student edition with
                                 #   student-own + student-other, three DITA-OT runs
                                 #   per ditamap, html/instructor/ +
                                 #   html/student-own/ + html/student-other/ layout,
                                 #   new three-link shared html/index.html
mock_pptx.py                     # MODIFIED — remove the No-FR publication entry,
                                 #   plant `[-own]` and `[-other]` markers on the last
                                 #   two grams of Week 3's second slide for a fixed seed

source.csv                       # REGENERATED — adds 17th `audience` column;
                                 #   No-FR rows removed; Week 3 rows for the two
                                 #   tagged grams carry `-own` / `-other` cells

tests/
├── test_extract_to_csv.py       # EXTENDED — assert trailing-[xxx] stripping into
                                 #   the audience column, multi-bracket concatenation,
                                 #   17th-column header emission
├── test_generate_dita.py        # EXTENDED — assert topicref `audience=` emission,
                                 #   per-gram consistency error, audience-tagged
                                 #   topicrefs in both main and progress-test ditamaps
└── test_publish_html.py         # EXTENDED — assert three-edition folder layout,
                                 #   Week 3 substitution count parity, idempotency
                                 #   across all three editions, "no fr" absence

specs/001-pptx-dita-migration/contracts/csv-schema.md
                                 # MODIFIED — add row for column 17 (`audience`),
                                 #   note backward-compat behaviour for 16-column CSVs
```

`introspect_pptx.py`, `publish_html.py`'s upstream contract for
DITA-OT, `run_pipeline.bat`, and `README.md` are unchanged by this
feature. The `dita/` tree as currently committed will be regenerated
with the new topicref attribute when an `audience`-bearing CSV row
exists; the regen happens as part of the implementation tasks and the
resulting source-tree changes are committed together with the
generator change.

**Structure Decision**: Same flat repository root as features 001 /
002 / 003 — four existing scripts edited, two new DITAVAL files added
to the DITA source tree, no new directories at the project root. The
three-edition shape lives entirely inside `publish_html.py`'s logic
plus the output tree layout; the DITA source tree stays single-rooted
(carried over from feature 003's FR-013).

## Complexity Tracking

> No constitution violations to justify. No deviations from the
> simplest viable design — the per-gram audience tag is a single new
> CSV column carried through to a single new DITA attribute, and the
> three editions are produced by three DITA-OT runs against the same
> source with three DITAVAL profiles. Nothing more elaborate.
