# Implementation Plan: Backlog Navigator Integration

**Branch**: `claude/add-backlog-navigator-2MlO2` | **Date**: 2026-05-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-backlog-navigator/spec.md`

## Summary

Wire the existing `DeepBlueCLtd/backlog-navigator` hosted PWA up to this
repository's backlog file so reviewers can browse it on mobile, and so
backlog edits arrive as pull requests rather than direct commits. The
work is almost entirely documentation, file naming, and one GitHub
Actions workflow — no application code is added, and the existing
PPTX → DITA pipeline is untouched. Three things ship together:

1. The backlog file is renamed/aliased to the casing the navigator
   expects, and every existing reference is updated in the same commit
   so no links break.
2. The README gains a "Browse the backlog" section with a single
   stable URL targeting the hosted navigator and a short note for
   contributors who want to edit (token scope, what to expect).
3. A `.github/workflows/backlog-navigator-pr-link.yml` workflow
   posts (or updates) a single comment on every PR that touches the
   backlog file, linking to the navigator pre-loaded with the PR
   branch.

The hosted instance at `deepbluecltd.github.io/backlog-navigator` is
the target — no self-hosted fork, no backend, no build pipeline of
our own. The integration adds zero runtime dependencies to the Python
pipeline.

## Technical Context

**Language/Version**: No new language. The integration is markdown
(backlog file, README), YAML (one GitHub Actions workflow), and a
small inline shell snippet inside that workflow.
**Primary Dependencies**: GitHub Actions only — `actions/checkout`
and either `actions/github-script` or `peter-evans/create-or-update-comment`
to manage the PR comment idempotently. The hosted navigator is
treated as an external service whose URL contract we depend on but
do not vendor.
**Storage**: None. The backlog file in the repository is the only
state.
**Testing**: Manual end-to-end walkthrough in `quickstart.md`
(load URL on phone, open a PR, observe comment, do an inline edit,
verify resulting PR). No unit tests are added — there is no
application code with branchable logic. The existing `unittest`
suite is unaffected and must continue to pass.
**Target Platform**: GitHub.com (Actions runner + PR UI), plus any
modern mobile or desktop browser opening the hosted navigator URL.
**Project Type**: Repository-tooling / documentation feature — no
code artifact is produced or installed.
**Performance Goals**: Navigator review-link comment must appear on a
PR within one CI minute of the PR being opened or updated against
the backlog file (SC-004 derived). No perceptible latency targets
otherwise — read performance is the hosted navigator's responsibility.
**Constraints**: Must preserve byte-level integrity of the backlog
file through navigator round-trips (SC-003); must not introduce
always-on infrastructure (SC-005, FR-009); must not break any
existing reference to the backlog file in this repo (FR-008, SC-006).
**Scale/Scope**: One backlog file, currently one epic and one item,
expected to grow to tens of items. PR comment workflow runs only on
PRs that change the backlog file (path filter).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution at `.specify/memory/constitution.md` is the unmodified
Spec Kit template — no concrete principles have been ratified, so
there are no formal gates to evaluate. The implicit principles that
the sibling feature (`001-pptx-dita-migration`) called out also
hold here:

- **Simplicity / YAGNI**: Reuse the hosted navigator, do not fork or
  self-host. One workflow file, one README section, one rename.
- **Test-first**: Limited applicability — the deliverable is config
  and docs, not code. The quickstart serves as the executable
  acceptance check.
- **Observability**: The GitHub Actions workflow's run logs are the
  observability surface; the workflow must fail loudly rather than
  silently skip when something goes wrong.
- **Versioning / breaking changes**: The integration is additive.
  The one breaking-shaped change (backlog filename casing) is
  contained to a single commit that updates every reference.

**Result**: PASS — no ratified gates, design adheres to the implicit
principles above. Re-evaluated after Phase 1: still PASS, no new
violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/002-backlog-navigator/
├── plan.md                  # This file (/speckit-plan output)
├── spec.md                  # Feature specification (/speckit-specify output)
├── research.md              # Phase 0 — decisions resolving open questions
├── data-model.md            # Phase 1 — backlog file shape the navigator depends on
├── quickstart.md            # Phase 1 — end-to-end walkthrough for a maintainer
├── contracts/
│   ├── backlog-file-schema.md   # Tables, columns, allowed status values
│   ├── navigator-url.md         # URL parameters the README and workflow use
│   └── pr-comment-workflow.md   # Event trigger, comment shape, idempotency rule
├── checklists/
│   └── requirements.md      # Spec quality checklist (already complete)
└── tasks.md                 # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
BACKLOG.md                   # Renamed from backlog.md (case-only rename — see research.md)
README.md                    # Adds "Browse the backlog" section
.github/
└── workflows/
    └── backlog-navigator-pr-link.yml   # New: PR comment workflow
```

No directories are added. The existing Python scripts
(`mock_pptx.py`, `introspect_pptx.py`, `extract_to_csv.py`,
`generate_dita.py`, `run_pipeline.bat`), `tests/`, `source/`,
`specs/001-pptx-dita-migration/`, and `high-level-spec.md` are
untouched.

**Structure Decision**: Single-repository, no new source tree. This
is a "repo plumbing" feature whose only artifacts are a rename, a
README edit, and one workflow file.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table omitted.
