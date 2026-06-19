<!--
SYNC IMPACT REPORT
==================
Version change: 1.2.0 → 1.3.0 (amendment; see "Amendment 1.3.0" below).
1.0.0 was the first concrete ratification, replacing the unmodified Spec Kit
placeholder template (initial adoption, not an amendment).

Principles defined (7):
  I.   Air-Gapped, Self-Sufficient Operation
  II.  Single-Purpose Scripts, Minimal Surface
  III. Test-First Discipline
  IV.  Human-in-the-Loop Authority
  V.   Deterministic, Idempotent Output (quality goal)
  VI.  Honest Limitations
  VII. Strict on Self-Authored Data (fail-fast at the trust boundary)

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

Amendment 1.1.0 (2026-05-30):
  - Principle I — replaced the "exactly one runtime dependency" bullet with a
    "minimal and individually justified" dependency policy (transfer cost +
    fragility weighed per dependency; prefer offline-clean pure-Python wheels;
    prefer prep-time/non-runtime confinement and graceful degradation). The
    stdlib-only test contract is retained verbatim.
  - Bump rationale: MINOR. The dependency rule is relaxed, not removed — no
    principle is removed and no previously compliant artifact becomes
    non-compliant (Principle I and the stdlib-only test contract stand), so
    this is a material expansion of guidance, not a backward-incompatible
    redefinition.
  - Consistency: CLAUDE.md "One runtime dependency" invariant and README's
    "only third-party runtime dependency" line updated to match.

Amendment 1.2.0 (2026-06-11):
  - Principle II — the "flat set … at the repo root" location guidance now
    reads: canonical single-purpose scripts live under `scripts/` (one per
    stage, data strictly forward, YAGNI unchanged), fronted by thin REPL
    wrapper scripts at the repo root. The repository thereby mirrors the
    delivered target layout already ratified by README ("Project layout on
    the target") and built by the release packager; the wrappers become
    version-controlled templates and are the only artifact carrying
    target-specific paths.
  - Bump rationale: MINOR. The principle's obligations — tiny
    single-responsibility scripts, minimal surface, YAGNI — are unchanged;
    only the descriptive file-location guidance is materially expanded to
    name the wrapper tier. No previously compliant artifact becomes
    non-compliant.
  - Consistency: CLAUDE.md (Commands, Architecture, target layout), README
    (folder structure, quickstart, target/release sections), HANDOVER.md
    paths, and the packaging workflow updated to match.

Amendment 1.3.0 (2026-06-19):
  - Added Principle VII — "Strict on Self-Authored Data (fail-fast at the
    trust boundary)". Be ruthless with values this pipeline produces and
    forbids editing (the CSV identity columns), and with any value whose
    emptiness would silently corrupt one of our own invariants (the .wav
    dedup view fields): a blank one is a defect we fail loud on at the point
    of use (`require_field` → `PipelineDataError`), not a value we coerce to
    "". This is the complement of Principle IV, not a loosening of it: VII
    governs *our* data, IV governs *uncertain source* data, and the
    dangling-asset rule still governs *external assets*.
  - Bump rationale: MINOR. A new principle is added; no principle is removed
    or redefined. One documented behaviour changed direction (a blank .wav
    view in deduplicate_csv.py was tolerated, now hard-fails) — legitimate
    under the pre-production posture (no backward-compatibility binding) and
    covered by an updated regression test.
  - Consistency: generate_dita.py + deduplicate_csv.py grow `require_field`/
    `PipelineDataError`; CLAUDE.md "Invariants to preserve" and README's CSV
    identity-column note gain the trust-boundary rule; the test suite asserts
    the hard-fail.

Deferred TODOs: none. Ratification date set to first concrete adoption
(2026-05-29).
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

- Third-party runtime dependencies are kept **minimal and individually
  justified** — there is **no fixed cap**, but each dependency is a real cost:
  effort for the maintainer to transfer it across the air-gap, and a potential
  source of fragility on a machine no one can patch from the internet. A
  dependency is therefore added only when its value clearly outweighs that cost.
  The runtime baseline today is a single dependency (`python-pptx`, pinned with
  `~=` for predictable wheelhouse rebuilds). Any addition MUST, in the
  introducing PR, weigh its value against the transfer-and-fragility cost;
  prefer a pure-Python wheel that installs cleanly offline; and, where possible,
  confine it to a **prep-time / non-runtime path** and **degrade gracefully**
  when it is absent (e.g. a defensively-imported library with a working
  fallback), so the air-gapped runtime path stays as small and robust as
  possible.
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

The pipeline is a flat set of tiny, single-responsibility canonical scripts
under `scripts/` — one per stage — with data flowing strictly forward, fronted
by thin REPL wrapper scripts at the repo root that mirror the delivered target
layout. The wrappers are the only per-target surface: each sets `sys.argv`
(target paths and toggles live in its Config block alone) and `runpy`s its
canonical script; canonical scripts never carry target-specific paths and are
never edited per-target. New capability is preferred as the smallest change to
an existing stage over new scripts, directories, frameworks, or abstraction
layers. Apply YAGNI: build the simplest thing that satisfies the current spec,
and reuse mechanisms already in the toolchain (e.g. DITA-OT's built-in DITAVAL
filtering) before inventing new ones.

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

### VII. Strict on Self-Authored Data (fail-fast at the trust boundary)

There is a trust boundary between data this pipeline produces (and forbids
editing) and input it does not control. The pipeline MUST be **ruthless** on
its own side of that boundary and **forgiving** only on the far side:

- **Zone A — our data and our invariants (hard-fail).** The CSV identity
  columns the schema marks *Empty allowed? = no* (`publication`, `gram_id`,
  `topic_type`, `sequence`, `topic_filename`) and any value whose emptiness
  would silently corrupt one of our own invariants. A blank or missing Zone-A
  value is a defect in *our* pipeline: it MUST fail loud at the point of use
  (`require_field` raising `PipelineDataError`), never be coerced to `""` and
  carried forward into a malformed topic.
- **Zone B — uncertain author judgement (warn and defer).** Governed by
  Principle IV: human-editable cells and ambiguous source values are
  warned-and-deferred or skipped-and-reported, not crashed.
- **Zone C — external legacy artifacts (warn and dangle).** The `.pptx`
  corpus, the `.glc` files, and on-disk assets: a missing or malformed one is
  logged and the topic still emits with its intended local href (the
  dangling-asset rule), so dropping the asset in and re-running resolves it.

This principle is the **complement** of Principle IV, not a loosening of it:
IV protects the author from confident wrong guesses about *messy source*;
VII protects the output from silent defects in *data we authored*. Where an
externally-sourced value (Zone C) is consumed as the key to one of our own
invariants — e.g. a `.wav` row's `(time_end, bandwidth, bandcentre)` view,
which is the audio-dedup key — it is **promoted to Zone A** and hard-fails on
blank, because being forgiving at the boundary must never extend to corrupting
our own logic.

Rationale: the highest-risk failure for this tooling is a *silent* miscoercion
on the real, unit-test-thin corpus — a wrong but plausible publication shipped
without anyone noticing. A loud abort on our own malformed data is always
preferable to a quiet, plausible-looking wrong answer.

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

**Version**: 1.3.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-06-19
