# Implementation Plan: PPTX to DITA Migration Pipeline

**Branch**: `claude/document-pptx-spec-xQZC8` | **Date**: 2026-05-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-pptx-dita-migration/spec.md`

## Summary

Migrate ~15 instructor PowerPoint presentations (~1,000 grams of acoustic
training content) into DITA XML publications that match the existing
pub-9/pub-10 structure, using a five-stage pipeline (introspect → extract →
human review → generate → QA). The automated stages are five small,
defensively written Python tools with one dependency (`python-pptx`), a
synthetic mock generator, a `unittest`-based test suite, a Windows batch
wrapper, and a README. The whole thing must remain debuggable on an
air-gapped network without AI assistance, so emphasis is on logging,
explicit error capture in the intermediate CSV, idempotent generation, and
documentation suited to a lone maintainer.

The shape-grouping function in the extractor is deliberately delivered as a
documented `NotImplementedError` stub: it depends on findings from running
the introspection script against real instructor presentations on the
development VM, which only happen after handover.

## Technical Context

**Language/Version**: Python 3.11+ (CPython, standard interpreter)
**Primary Dependencies**: `python-pptx` for PPTX reading and mock generation; standard library only for everything else (`xml.etree.ElementTree`, `csv`, `pathlib`, `logging`, `argparse`, `unittest`)
**External Toolchain (not a Python dependency, not bundled)**: DITA-OT plus a Java runtime, installed manually on the air-gapped target PC. Used ad-hoc by the maintainer to render generated DITA to HTML for inspection. The README ships acquisition/install/run instructions; the user handles transfer through the air-gap. Oxygen XML Author remains the production publishing path — DITA-OT is for development and sanity-check previews only, and is invoked outside the automated pipeline.
**Storage**: Filesystem only — PPTX/GLC/PNG/WAV inputs read from a configurable content root; intermediate CSV at the project root; DITA topics, copied assets (PNG/WAV/analysis sheets), and ditamaps written under the `dita/` tree (each asset is renamed to match its owning topic's stem); HTML preview (when `publish_html.py` is run) under `html/`
**Testing**: `unittest` discovery (`python -m unittest discover tests/`); fixtures shipped under `tests/fixtures/`; no third-party test framework
**Target Platform**: Windows workstations on an air-gapped analyst network (post-deployment) and an internet-connected Windows VM (development); both run the same Python and the same scripts
**Project Type**: CLI/script tool — five executable scripts plus a Windows batch orchestrator, no library packaging, no service runtime
**Performance Goals**: Process the full corpus (~15 PPTXs, ~1,000 grams, ~5 publications) in a single generator run with no manual intervention beyond Stage 3 sign-off; full test suite under one minute on a standard development workstation (SC-003)
**Constraints**: Air-gapped operation post-handover (no internet, no AI, no `pip install`); single third-party dependency (`python-pptx`); `pathlib` everywhere, explicit UTF-8 on every file, `logging` rather than `print`, no global mutable state, no silent exception swallowing; idempotent generator output; both DITA audience profiles (instructor and trainee) must build cleanly in Oxygen
**Scale/Scope**: ~15 instructor presentations, ~1,000 gram placeholders, ~1,000–4,000 GLC files, one main publication with chapters plus ~4–5 flat progress-test publications, an output tree of ~1,000+ DITA topic files plus per-publication ditamaps

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` is the
unmodified Spec Kit template — no concrete principles have been ratified.
There are therefore no constitution gates to evaluate. Should the
constitution be ratified later, the principles most likely to apply to
this project are already implicitly upheld:

- **Simplicity / YAGNI**: Standard-library testing, single third-party
  dependency, no premature abstraction. Five small scripts each with a
  single responsibility.
- **Test-first**: The test suite is part of the deliverable list; every
  script in section 8 of the spec has a paired test module. The
  `unittest` framework is mandated by the air-gapped constraint.
- **Observability**: Mandatory `logging` (FR-014) at INFO/WARNING/ERROR
  levels, dual stdout + per-stage log file, plus warning capture in the
  intermediate CSV.
- **Versioning / breaking changes**: Not relevant — this is a one-shot
  migration tool, not an evolving library.

**Result**: PASS (no ratified gates; design adheres to the implicit
principles above).

## Project Structure

### Documentation (this feature)

```text
specs/001-pptx-dita-migration/
├── plan.md                  # This file (/speckit-plan output)
├── spec.md                  # Feature specification (/speckit-specify output)
├── research.md              # Phase 0 — decisions resolving open questions
├── data-model.md            # Phase 1 — entity model for CSV and DITA
├── quickstart.md            # Phase 1 — end-to-end walkthrough
├── contracts/
│   ├── csv-schema.md        # Intermediate CSV column contract
│   ├── glc-schema.md        # Subset of GLC XML the parser depends on
│   ├── dita-topic-schema.md # Shape of generated DITA topics + ditamaps
│   └── cli-contracts.md     # Argument and exit-code contract per script
├── checklists/
│   └── requirements.md      # Spec quality checklist (already complete)
└── tasks.md                 # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
mock_pptx.py                 # Synthetic instructor PPTX generator (Story 4)
introspect_pptx.py           # Structural report producer (Story 3)
extract_to_csv.py            # PPTX + GLC → intermediate CSV (Story 2)
generate_dita.py             # Reviewed CSV → DITA topics + assets + ditamaps (Story 1)
publish_html.py              # DITA → HTML5 via DITA-OT (FR-021 preview helper)
run_pipeline.bat             # Windows batch orchestrator (Story 6)
README.md                    # Project documentation (FR-018)

tests/                       # unittest suite (Story 5)
├── __init__.py
├── test_mock_pptx.py
├── test_introspect.py
├── test_glc_parser.py
├── test_generate_dita.py
└── fixtures/
    ├── minimal.glc
    ├── minimal.csv
    └── malformed.glc
```

**Structure Decision**: Flat repository root for the five executable
scripts, the Windows batch orchestrator, and the README, mirroring the
delivery layout in section 11 of the source specification. No package or
`src/` layer — these are standalone CLI scripts that operate on filesystem
inputs and outputs, and a flat layout is the simplest thing that works for
both an air-gapped maintainer and the `unittest` discovery command. Tests
live under `tests/` with fixtures under `tests/fixtures/`. Per-feature
documentation (this plan, the research outputs, contracts, quickstart) is
isolated under `specs/001-pptx-dita-migration/` so the project root stays
operational rather than documentation-heavy.

Common helpers (e.g. logging setup, GLC parsing) will live alongside the
scripts as a small `pipeline_common.py` module if and only if duplication
across scripts becomes non-trivial; the default is to inline simple
helpers per script to keep each one self-contained and readable on the
air-gapped network. This decision is captured in research.md as a
principle rather than a hard rule, and revisited if duplication emerges.

## Complexity Tracking

> No constitution violations to justify (see Constitution Check above).
> No deviations from the simplest viable design.
