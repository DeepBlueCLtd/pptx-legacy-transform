# Research: Backlog Navigator Integration

Phase 0 of the implementation plan. Each section resolves one open
question raised by the spec or the Technical Context, and records the
chosen approach plus the alternatives that were considered.

## 1. Backlog filename casing

**Decision**: Rename `backlog.md` → `BACKLOG.md` in the repository
root, as a case-only `git mv` plus a sweep of every reference
(README, CLAUDE.md, plan files, skill prompts, this spec's
contracts) inside the same commit.

**Rationale**: The hosted backlog-navigator documents `BACKLOG.md`
(uppercase) as its expected filename. Most existing tooling that
discovers backlog files (GitHub's repository templates, "Awesome"
lists, Dependabot's documentation conventions) also assumes the
uppercase form. Aligning with the convention removes a configuration
surface that we would otherwise have to maintain in two places (the
navigator URL parameters and our PR-comment workflow). The
repository is small, the rename is mechanical, and a single
coordinated commit means no broken link survives. Git's
case-insensitive default on macOS is mitigated by performing the
rename via `git mv -f` and committing on a Linux runner.

**Alternatives considered**:

- *Keep `backlog.md` lowercase and configure the navigator to read
  it.* The navigator supports a `?path=` URL parameter, so this is
  technically possible. Rejected because (a) it leaves the repo
  out of step with the navigator's documented convention, (b)
  every navigator URL we publish gets longer and more fragile,
  and (c) future tooling that auto-discovers `BACKLOG.md` will
  silently miss this repo.
- *Add a `BACKLOG.md` that symlinks or includes `backlog.md`.*
  Rejected: symlinks behave inconsistently across Windows
  developer machines and GitHub's web preview; includes are not
  a standard markdown feature.

## 2. Hosted vs. self-hosted navigator instance

**Decision**: Use the hosted instance at
`https://deepbluecltd.github.io/backlog-navigator/`.

**Rationale**: It is operated by the same organisation, requires
zero infrastructure on our side (satisfies FR-009 and SC-005), and
matches the navigator project's documented "zero infrastructure"
adoption path. No branding or feature customisation is wanted at
this stage.

**Alternatives considered**:

- *Fork and self-host on this repository's own GitHub Pages.*
  Rejected — adds a build pipeline and a release cadence we would
  have to maintain, with no offsetting benefit at current scale.
- *Vendor the navigator as a submodule.* Rejected — same maintenance
  burden plus a confusing repo-shape signal (this is a PPTX → DITA
  migration tool, not a navigator host).

## 3. PR comment workflow: implementation choice

**Decision**: A single workflow file at
`.github/workflows/backlog-navigator-pr-link.yml`, triggered on
`pull_request` events of types `opened` and `synchronize`, with a
`paths:` filter limiting it to changes touching the backlog file.
The job uses `peter-evans/create-or-update-comment` (pinned by SHA)
keyed on a hidden marker comment (e.g. an HTML comment containing
`<!-- backlog-navigator-link -->`) so re-runs update the existing
comment rather than spawning duplicates.

**Rationale**: The action is widely used, has a small API surface,
supports the "find existing comment by marker" pattern out of the
box, and avoids the boilerplate of writing the same lookup in
`actions/github-script`. Pinning by SHA satisfies the standard
supply-chain hygiene expectation for third-party actions.

**Alternatives considered**:

- *Inline `actions/github-script` with `@octokit/rest` calls.*
  Rejected — more code to maintain for no functional gain. Kept as
  a fallback option in `contracts/pr-comment-workflow.md` in case
  we later want to drop the third-party action dependency.
- *A separate workflow per event type.* Rejected — needless
  duplication; `opened` and `synchronize` share the same body.
- *Comment on every push to the branch (not just PR events).*
  Rejected — the comment only makes sense in a PR context.

## 4. Navigator URL shape

**Decision**: Canonical URL pattern used in the README and emitted
by the PR workflow:

- README (default branch):
  `https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&branch=main`
- PR comment (per-PR branch):
  `https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&pr=<PR_NUMBER>`

**Rationale**: These are the parameters documented by the
navigator project. Using `?pr=` rather than `?branch=` in the PR
comment lets the navigator render the PR-diff view directly
(loading the head branch's version of the file) without us needing
to derive a branch name.

**Alternatives considered**:

- *Hard-code `?branch=` derived from `github.head_ref`.* Workable
  but loses the "PR-diff" affordance the navigator provides when
  given a PR number. Kept documented as a fallback in
  `contracts/navigator-url.md`.

## 5. Token guidance for editors

**Decision**: Do not invent our own token-scope guidance. The
README's "Browse the backlog" section will say "to edit, follow the
navigator's own setup guide" and link to the navigator repository's
README. The local guidance is limited to: (a) tokens are stored in
the navigator's `localStorage` on the user's device only, never in
this repo; (b) revoke the token on GitHub if a device is lost.

**Rationale**: Token-scope requirements are owned by the navigator
project and will change when the navigator changes. Mirroring them
here invites drift. A short pointer plus the safety-net guidance is
enough to satisfy FR-007 without taking on documentation debt.

**Alternatives considered**:

- *Reproduce the navigator's full token-setup walkthrough in our
  README.* Rejected — duplication, will go stale.

## 6. Reference-integrity guard for the rename

**Decision**: Add a second workflow file,
`.github/workflows/backlog-reference-check.yml`, that runs on
`pull_request` and on `push` to `main`, greps the repository for
the lowercase literal `backlog.md` (word-bounded, regex
`\bbacklog\.md\b`), and fails if any match falls outside
`specs/002-backlog-navigator/` (where historical mentions are
preserved deliberately).

**Rationale**: SC-006 ("no existing link, command, or skill returns
'file not found'") is the spec's load-bearing invariant. The
manual `grep` in `quickstart.md §4` is one-shot; an automated check
keeps the invariant true forever and costs ~ten lines of YAML. The
review identified this as a critical gap because the rename is
invasive and the failure mode (a stale link to a missing file) is
silent.

**Alternatives considered**:

- *Manual grep in `quickstart.md` only.* Rejected — does not survive
  the project's lifetime; SC-006 silently regresses the first time
  someone adds a new file with the old reference.
- *A `pre-commit` hook instead of CI.* Rejected — relies on every
  contributor's local environment being correctly configured, which
  is fragile in a multi-machine team.

## 7. URL parameter choice for the PR-comment workflow

**Decision**: The PR-comment workflow uses
`?repo=...&branch=${{ github.event.pull_request.head.ref }}`. The
`?pr=<n>` parameter is **not** used.

**Rationale**: Verification against the navigator project's README
during review showed that `?pr=` is documented as a "legacy form —
resolves against bundled default", while `?branch=` is the modern
canonical parameter. Initial planning had reversed these roles; the
review corrected them. Using the modern parameter keeps us aligned
with the navigator's supported surface and avoids a future
deprecation break.

**Alternatives considered**:

- *Use `?pr=<n>` as originally planned.* Rejected — relies on a
  legacy code path in the navigator that may be removed without
  notice.
- *Emit both `?branch=` and `?pr=` for robustness.* Rejected — the
  navigator's URL contract is "exactly one of"; duplicating both
  is undefined behaviour.

## 8. Out of scope

The following were deliberately excluded from this feature; calling
them out here so they are not re-raised during `/speckit-tasks`:

- **A "BACKLOG schema" linter / pre-commit hook.** The navigator's
  parser is the source of truth for whether the file is valid;
  adding our own validator would either lag or contradict it.
- **Migrating backlog history.** The existing `backlog.md` is short
  and recent. A normal `git mv` preserves the history we have.
- **Wiring the navigator into CI gates (e.g. block merge if
  backlog malformed).** Premature — revisit if we ever see a
  malformed-backlog PR slip through.
- **Bot-driven backlog edits from agents.** Out of scope for this
  spec; a future backlog item can address it.
