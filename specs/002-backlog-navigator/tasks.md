---

description: "Task list for Backlog Navigator Integration"
---

# Tasks: Backlog Navigator Integration

**Input**: Design documents from `/specs/002-backlog-navigator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: This feature ships docs and a single GitHub Actions workflow; there is no Python code to unit-test. The acceptance check is the quickstart walkthrough and the new `backlog-reference-check.yml` CI guard. No separate `tests/...` tasks are generated.

**Organization**: Tasks are grouped by user story (US1, US2, US3) plus a Foundational phase that performs the load-bearing rename, and a Polish phase that runs the quickstart.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Each task names exact file paths

## Path Conventions

This feature does not add a `src/` tree. All paths are repository-root relative; the only new directory is `.github/workflows/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: There is no source tree or build to initialise. The only setup is confirming the working state before the foundational rename.

- [ ] T001 Confirm no uncommitted edits to `backlog.md` exist on the feature branch (`git status --short backlog.md` shows clean) before starting Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Perform the case-only rename and add the new backlog rows in a single coordinated commit. The rest of the work — README edits, PR-comment workflow, reference-check workflow — depends on the new filename existing on the branch.

**⚠️ CRITICAL**: No user story task can begin until T002 lands.

- [ ] T002 Rename `backlog.md` → `BACKLOG.md` via `git mv -f backlog.md BACKLOG.md`, and in the same commit append three new rows to the Items table per `plan.md`'s "Project Structure" section: (a) item for this backlog-navigator integration itself (`Category: Tooling`, `Epic: E01`, `Status: specified`, link to `specs/002-backlog-navigator/`), (b) item for the reference-integrity CI check (`Category: Tooling`, `Status: planned`), (c) item for a future navigator-aware PR template (`Category: Tooling`, `Status: proposed`, note dependency on US3).
- [ ] T003 [P] Create `.github/workflows/backlog-reference-check.yml` — a workflow that runs on `pull_request` and on `push` to `main`, greps the repository for the lowercase literal `backlog.md` (regex `\bbacklog\.md\b`), and fails CI if any match falls outside `specs/002-backlog-navigator/`. Implements decision §6 in `research.md`. Permissions: `contents: read` only.
- [ ] T004 Sweep the repository for any remaining lowercase references to `backlog.md` outside `specs/002-backlog-navigator/` (run `grep -rn '\bbacklog\.md\b' --include='*.md' --include='*.py' --include='*.bat' --include='*.yml' --include='*.yaml' --include='*.txt' .`); update each match to `BACKLOG.md`. Confirm T003's workflow now passes locally with `act` if available, or by inspection.

**Checkpoint**: `BACKLOG.md` exists at repo root, the three new items are in its table, every internal reference uses the uppercase filename, and the CI guard is in place.

---

## Phase 3: User Story 1 — Browse the backlog from any device (Priority: P1) 🎯 MVP

**Goal**: A reviewer with the published URL can open the backlog on any device and use sort, filter, and search — without authenticating and without setup docs.

**Independent Test**: From a signed-out mobile browser, open the URL printed in the README; the Epics and Items tables render and the status-filter dropdown lists every workflow state. (Quickstart §1.)

### Implementation for User Story 1

- [ ] T005 [US1] Add a "Browse the backlog" section to `README.md`, placed after the existing "Folder structure" section. Section contains a single canonical link `https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&branch=main` (matching `contracts/navigator-url.md`) and a one-sentence note that it requires no setup or token to browse.
- [ ] T006 [US1] On a signed-out / private browsing tab, open the README's navigator URL on a phone and on a desktop. Confirm the items and epics tables render, the new T002 backlog rows are visible, and the status-filter dropdown lists every workflow state used in the table (per Quickstart §1).

**Checkpoint**: Story P1 is fully functional — reviewers without credentials can browse the live backlog from any device.

---

## Phase 4: User Story 2 — Propose backlog edits as a pull request (Priority: P2)

**Goal**: A token-holding maintainer can edit cells inline in the navigator and submit pending changes as a single pull request that preserves the rest of the file byte-for-byte.

**Independent Test**: With a token configured per the navigator's own setup guide, change one cell, confirm the dirty-count badge increments, submit; a PR appears on this repository whose diff is confined to `BACKLOG.md` and contains only the edited cell. (Quickstart §3.)

### Implementation for User Story 2

- [ ] T007 [US2] Extend the README's "Browse the backlog" section (file `README.md`) with a "To edit" sub-section that: (a) links to the backlog-navigator project's own README for token setup, (b) states tokens are stored in the user's browser `localStorage` only and never in this repo, (c) instructs the reader to revoke the token on GitHub if a device is lost. Do not duplicate the navigator's token-scope documentation locally — link out to it. Implements FR-007 + research.md §5.
- [ ] T008 [US2] Run Quickstart §3 end-to-end on a real edit: change one cell of `BACKLOG.md` via the navigator, submit the PR, then verify the resulting diff is confined to that cell and contains no incidental whitespace or alignment changes (round-trip invariant, SC-003). If the round-trip fails, file an upstream bug against backlog-navigator and stop — do not work around it locally.

**Checkpoint**: Story P2 is fully functional — contributors with a token can land backlog edits through the navigator without touching a local clone.

---

## Phase 5: User Story 3 — Discover the navigator link from a pull request (Priority: P3)

**Goal**: Every pull request that touches the backlog file gets a single, auto-updating comment containing a navigator link pre-loaded with the PR's head branch.

**Independent Test**: Open a PR that edits `BACKLOG.md`. Within one CI minute a comment from `github-actions[bot]` appears starting with the hidden marker `<!-- backlog-navigator-link -->` and containing a navigator URL with `?branch=<PR_HEAD_REF>`. Push a second commit; the same comment is updated in place rather than duplicated. (Quickstart §2.)

### Implementation for User Story 3

- [ ] T009 [US3] Create `.github/workflows/backlog-navigator-pr-link.yml` per `contracts/pr-comment-workflow.md`: trigger on `pull_request` events `[opened, synchronize, reopened]` with `paths:` filter for `BACKLOG.md` and the workflow file itself; `permissions: pull-requests: write, contents: read`; one job on `ubuntu-latest` that composes the marker-led body with the navigator URL using `?repo=DeepBlueCLtd/pptx-legacy-transform&branch=${{ github.event.pull_request.head.ref }}` (URL-encoded if `head.ref` contains `/`); use `peter-evans/create-or-update-comment` pinned by commit SHA with `body-includes: '<!-- backlog-navigator-link -->'` for idempotency.
- [ ] T010 [US3] Smoke-test the workflow on a draft PR before merging it to `main`: open a draft PR that edits `BACKLOG.md`, confirm exactly one navigator-link comment appears, push a second commit that further edits `BACKLOG.md`, and confirm the existing comment is updated (not duplicated). Open a separate draft PR that does not touch `BACKLOG.md` and confirm no comment is posted (FR-006 path filter).
- [ ] T011 [US3] If T010 reveals any failure mode that the contract did not anticipate (e.g. `head.ref` URL-encoding gaps, comment-find races), update `specs/002-backlog-navigator/contracts/pr-comment-workflow.md` to record the corrected behaviour before merging the workflow. Contract and implementation must stay in sync.

**Checkpoint**: All three user stories are independently functional. SC-004 is observable (PR comment appears within one CI minute).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and a final audit that no existing reference broke.

- [ ] T012 Run the full Quickstart (`specs/002-backlog-navigator/quickstart.md`) end-to-end on the merged `main` branch: §1 (phone read), §2 (PR comment behaviour), §3 (round-trip edit), §4 (reference-integrity sweep). Record any deviation as a fresh backlog item rather than fixing in this feature.
- [ ] T013 [P] Verify SC-006 by running `grep -rni '\bbacklog\.md\b' --include='*.md' --include='*.py' --include='*.bat' --include='*.yml' --include='*.yaml' --include='*.txt' .` from a fresh clone of `main`. The only acceptable matches are inside `specs/002-backlog-navigator/`. If T003's CI workflow is green, this check is redundant — record that and move on.
- [ ] T014 Move the three backlog items added in T002 forward in status if appropriate: item (a) `specified` → `implementing` → `complete` once this feature merges; item (b) likewise once T003 is merged; item (c) remains `proposed` (its dependency, US3, will be complete but the PR template itself is a future feature).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: T002 blocks every later task. T003 is parallelisable with T002 only in the sense that its file lives elsewhere — but in practice T003 is most safely written after T002 has landed so its expected post-rename state is real, not speculative. T004 depends on T002.
- **User Story 1 (Phase 3)**: Depends on T002 (the README URL targets the renamed file).
- **User Story 2 (Phase 4)**: Depends on T005 (extends the same README section).
- **User Story 3 (Phase 5)**: Depends on T002 only — independent of US1/US2 README work.
- **Polish (Phase 6)**: Depends on US1, US2, US3 all complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational T002 only.
- **US2 (P2)**: Builds on US1's README section (T007 extends T005's section). Technically the navigator's edit flow works the moment T002 lands — the README guidance is a documentation-only deliverable that does not gate functionality.
- **US3 (P3)**: Depends on Foundational T002 only. Completely independent of US1 and US2 — different file, different deliverable.

### Within Each User Story

- README-modifying tasks within the same story are sequential (single file).
- Workflow files are independent of README files and can be authored in parallel.

### Parallel Opportunities

- T003 (reference-check workflow, `.github/workflows/backlog-reference-check.yml`) can be authored in parallel with T004 (reference sweep) since they touch different files — but T003 needs T002 to have landed so its grep is meaningful.
- US3 (T009) is fully parallel with US1 (T005) and US2 (T007) once T002 lands.
- T013 in Polish is parallelisable with T012 and T014.

---

## Parallel Example: After Foundational lands

```bash
# Once T002 (rename + new backlog rows) is merged or staged on the branch,
# the following can run concurrently in different working files:

Task: "T005 [US1] Add 'Browse the backlog' section to README.md"
Task: "T009 [US3] Create .github/workflows/backlog-navigator-pr-link.yml"
Task: "T003 (foundational) Create .github/workflows/backlog-reference-check.yml"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1: confirm clean working tree (T001).
2. Phase 2: rename + new backlog rows + reference-check CI (T002, T003, T004).
3. Phase 3: README "Browse the backlog" section (T005, T006).
4. **STOP and validate**: Quickstart §1 on a phone. This alone delivers the navigator's core read value.
5. Merge if ready — US2 and US3 can ship later without rework.

### Incremental Delivery

1. Foundational + US1 → first deliverable.
2. Add US2 (T007, T008) → contributors can land backlog edits via the navigator.
3. Add US3 (T009, T010, T011) → PR reviewers get the auto-comment affordance.
4. Polish (T012–T014) → end-to-end audit.

### Single-developer note

This feature is small enough that one person can land all three stories in one PR. The phase split exists to keep the rename and the reference-check on a tight loop; the per-story README/workflow tasks can be batched if preferred.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to user story for traceability.
- Each user story should be independently completable and testable per its Independent Test criterion.
- Commit after each task or logical group; the rename + new backlog rows (T002) MUST land as a single coordinated commit.
- Avoid: emitting the legacy `?pr=` URL parameter anywhere (see `contracts/navigator-url.md` "Out of contract"); manually duplicating the navigator's token-scope docs in our README (link out instead).
