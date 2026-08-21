# Specification Quality Checklist: Source Audio Retention

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**Decisions taken from the user, not inferred**

- **Retention is on by default with a flag to suppress** (FR-008), chosen over
  always-on and over opt-in. Opt-in was rejected for the same reason feature 013
  removed the reverse-wrap flag: a working folder that is only complete when
  someone remembers a flag is the failure mode we just designed out.
- **`.bac.wav`, not `.wav.bak`** (FR-011) — the user's own suggestion, and
  better than the two options offered. It keeps the `.wav` extension so the OS
  hands the file to the spectrogram tool, while the `.bac` infix still marks it
  as the superseded original.

**The inference is now resolved**

An earlier draft flagged a trade-off: `relink` naming the retained audio after
the **image's** stem (so the pairing holds by construction in both routes) at
the cost of discarding the wav's original filename.

Investigation closed it. Neither tree contains a single `.wav.bak` or
`Image <N>-…` candidate, and the user confirmed no evidence of `relink` ever
being called — the author delivers through `ingest`. So no file in existence
carries the name the choice would discard, and the trade-off costs nothing.
Adopted.

The same finding removed a user story: the `.wav.bak` migration is dropped
rather than built speculatively, since there is nothing to migrate. If one ever
surfaces, its gram is counted in FR-010's "without retained audio" figure rather
than failing silently.

**Deliberately left out of scope**

Whether to retire `relink_glc_to_image.py` altogether. It is superseded in
practice by `ingest`, and the constitution's pre-production posture favours
deleting superseded shapes — but that is a decision about the pipeline's
surface, not about audio retention, and it belongs in its own change. This
feature corrects `relink`'s behaviour so the route works if picked up again.

**Scope boundary worth confirming on review**

The feature covers **converted** Lofars only. A gram whose `.glc` still names a
`.wav` already has its audio copied into the topic folder today (referenced, as
the viewer link's companion), so nothing changes there — FR-005 exists to keep
it that way and to prevent a second copy under a different name.

**Open for implementation**

- The CSV column name (`source_wav_path` proposed) and the suppression flag's
  name (`--no-source-wav` proposed).
- Whether the `.wav.bak` migration lives on `relink_glc_to_image.py` (its
  originator, per Principle II) or alongside feature 013's sweep on the
  snapshot stage. `relink` looks right.
- Whether the mock corpus needs a converted-gram-with-audio fixture, or whether
  the existing `.wav` stubs plus a relink run in the test suite suffice.
