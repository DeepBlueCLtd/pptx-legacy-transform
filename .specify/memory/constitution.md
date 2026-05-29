<!--
SYNC IMPACT REPORT
==================
Version change: (unratified template) → 1.0.0
Rationale: First concrete ratification. The prior file was the unmodified
Spec Kit placeholder template (no principles defined), so this is an initial
adoption, not an amendment — versioned 1.0.0.

Principles defined (6):
  I.   Air-Gapped, Self-Sufficient Operation
  II.  Single-Purpose Scripts, Minimal Surface
  III. Test-First Discipline
  IV.  Human-in-the-Loop Authority
  V.   Deterministic, Idempotent Output (quality goal)
  VI.  Honest Limitations

Added sections:
  - Development-Phase Posture (pre-production, no backward-compatibility binding)
  - Governance (amendment procedure, versioning policy, compliance review)

Removed sections: none (template placeholders replaced wholesale).

Templates reviewed for consistency:
  ✅ .specify/templates/plan-template.md — generic "Constitution Check" gate,
     no principle-specific edits required; gates derive from this file at runtime.
  ✅ .specify/templates/spec-template.md — no mandatory sections added/removed by
     these principles; no change required.
  ✅ .specify/templates/tasks-template.md — task categories already accommodate
     testing/observability tasks; no change required.
  ✅ CLAUDE.md / README.md — runtime guidance consistent with these principles.

Deferred TODOs: none. Ratification date set to first concrete adoption (today).
-->

# PPTX Legacy Transform Constitution

This project migrates legacy AAAC PowerPoint instructor decks into DITA XML
publications for an air-gapped Windows network. It is defensive migration
tooling: the value is in correct, auditable output that the receiving team can
operate and debug without the authors, the internet, or AI assistance.

## Core Principles

### I. Air-Gapped, Self-Sufficient Operation

The delivered pipeline MUST run and be debuggable on an air-gapped Windows PC
with **no internet access and no AI assistance**. This is the constraint from
which the others follow.

- Exactly **one** third-party runtime dependency (`python-pptx`), pinned with
  `~=` for predictable wheelhouse rebuilds. Adding any runtime dependency is
  rejected by default and requires explicit justification in the introducing PR.
- The test suite uses the **standard library only** — no third-party test
  framework on the air-gapped runtime path. (The developer-time Jest layer is
  explicitly outside this contract and never required to validate the pipeline.)
- **No network access at runtime.** No fetching of fonts, scripts, assets,
  telemetry, or remote schemas during execution; everything needed is local.
- Target floor is **Python 3.9** (WinPython 3.9.4.0). Use
  `from __future__ import annotations`; do not use 3.10+ syntax or stdlib APIs.
- Each stage writes a DEBUG log file at the repo root alongside console output,
  so a failure can be diagnosed from artifacts on the target machine alone.

Rationale: the receiving operators inherit the tool with none of the modern
conveniences the authors enjoy. Anything that needs the internet or a large
dependency tree is, in practice, undebuggable after handover.

### II. Single-Purpose Scripts, Minimal Surface

The pipeline is a flat set of tiny, single-responsibility scripts at the repo
root — one per stage — with data flowing strictly forward. New capability is
preferred as the smallest change to an existing stage over new scripts,
directories, frameworks, or abstraction layers. Apply YAGNI: build the simplest
thing that satisfies the current spec, and reuse mechanisms already in the
toolchain (e.g. DITA-OT's built-in DITAVAL filtering) before inventing new ones.

Rationale: small scripts that one person can read end-to-end are the most
debuggable artifact on an air-gapped network. Complexity that cannot be justified
against a spec requirement is removed.

### III. Test-First Discipline

New features MUST be accompanied by tests; bug fixes MUST add a regression test
that fails before the fix and passes after. Tests MUST NOT be skipped or deleted
to ship a change. The full `unittest` suite (`python -m unittest discover
tests/`) MUST be green before merge. Strict red-green-refactor ordering is
encouraged but not mandated; what is mandated is that the canonical suite covers
the change and stays green.

Rationale: this is migration tooling whose output is hard to eyeball at scale;
the test suite is the safety net that makes refactoring and handover safe.

### IV. Human-in-the-Loop Authority

The technical author is the sole authority for ambiguous decisions. The pipeline
MUST NOT silently infer or guess. Where a value is uncertain (e.g. a missing
vessel name, an unresolved asset, a malformed source file), the pipeline
**warns and defers** — recording the issue rather than fabricating a value or
aborting the whole run. Unusable rows are **skipped and reported**
(`skipped.txt`), not silently dropped and not treated as fatal. The intermediate
CSV is the deliberate review boundary between automation and human judgement.

Rationale: source data is messy and the cost of a wrong silent inference in a
training publication is high. A reviewable warning is always preferable to a
confident guess.

### V. Deterministic, Idempotent Output (quality goal)

Re-running a stage over unchanged input SHOULD produce byte-identical output,
including copied binary assets; two consecutive publish runs over an unchanged
source SHOULD yield byte-identical HTML in every edition. Avoid timestamps,
nondeterministic iteration order, and hash-seeded ordering in generated output.
Idempotency tests are maintained as the check on this property.

This is a strong quality goal rather than a hard merge gate: an intentional,
reviewed change to output is legitimate, but incidental nondeterminism is a
defect to fix.

Rationale: deterministic output makes diffs meaningful, makes regeneration safe,
and lets the receiving team trust that re-running the tool changes nothing they
did not intend to change.

### VI. Honest Limitations

Known stubs, sharp edges, deprecated fields, and constraints MUST be enumerated
openly in the README, specs, and code (e.g. the documented `NotImplementedError`
stub in `extract_grams_from_slide`, the deprecated `wav_treatment` column, the
Excel "Save As" encoding pitfalls). Limitations are surfaced, not hidden behind
optimistic defaults.

Rationale: an honest, written record of where the tool stops is what lets the
next person — without the authors — pick it up safely.

## Development-Phase Posture

The project is **pre-production**: it owns all of its artifacts and has no
external consumers bound to its current shapes. Accordingly there are **no
backward-compatibility obligations** on the CSV contract, DITA topic shape,
output-tree layout, DITAVAL profiles, source layout, or script CLIs.

- Migrations for in-tree data (e.g. `source.csv`) are written only as needed to
  keep the test suite green; superseded shapes are deleted rather than preserved.
- Deep-link and layout changes between features are acceptable and documented as
  edge cases in the relevant spec (as features 003 and 004 did).
- A future deliberate decision — a production cut at handover, a tagged release,
  or an amendment to this section — will introduce compatibility binding. Until
  then, prefer the cleanest shape over preserving legacy ones.

## Governance

This constitution supersedes ad-hoc practice. Where another document conflicts
with it, this file wins until amended.

**Spec-driven workflow.** Non-trivial features use the Spec Kit flow
(`/speckit-specify`, `/speckit-plan`, and the Constitution Check gate in the plan
template) before implementation. Each feature lives under `specs/NNN-name/` with
its spec, plan, contracts, and tasks.

**Amendment procedure.** A PR that edits this file MUST state the version bump
(MAJOR / MINOR / PATCH) and its rationale, and update the Sync Impact Report at
the top of the file.

**Versioning policy** (semantic versioning of this constitution):
- **MAJOR** — backward-incompatible removal or redefinition of a principle or
  governance rule.
- **MINOR** — a new principle or section, or a material expansion of guidance.
- **PATCH** — clarifications, wording, and non-semantic refinements.

The project's own code is not under SemVer during the pre-production posture
above; that binding begins at the production cut.

**Compliance review.** Reviewers gate merges on these principles. A PR that adds
a dependency, touches the air-gapped runtime path, changes generated output, or
introduces a network call MUST explicitly note compliance or a justified
deviation. Unjustified complexity is grounds for rejection.

**Runtime guidance.** `CLAUDE.md` (for AI assistants) and `README.md` (for
humans) provide day-to-day guidance and MUST remain consistent with this
constitution.

**Version**: 1.0.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-05-29
