# Feature Specification: Backlog Navigator Integration

**Feature Branch**: `claude/add-backlog-navigator-2MlO2`
**Created**: 2026-05-15
**Status**: Draft
**Input**: User description: "we should incorporate the backlog navigator into this repo https://github.com/DeepBlueCLtd/backlog-navigator"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and triage the backlog from a phone (Priority: P1)

A maintainer or stakeholder is away from their development machine and wants to look at the project's outstanding work, sort items by total score, filter to a particular epic, or check the status of a specific item. They open a shared link on their phone, see the backlog rendered as cards, scroll the list, apply filters, and read item details — all without cloning the repository or running any local tooling.

**Why this priority**: Read-only access is the foundational capability. Without it, no other navigator-enabled workflow is possible, and it delivers immediate value on its own (the existing `backlog.md` becomes browsable to non-developers).

**Independent Test**: Open the published navigator URL pointing at this repository's backlog file on a mobile device. Confirm the epic table and items table render, that all 12 columns are present, and that sort/filter/search controls work. No code changes need to be merged to anything else to validate this.

**Acceptance Scenarios**:

1. **Given** the repository's backlog file is on the default branch and the user has the shared navigator URL, **When** the user opens the URL on a mobile browser, **Then** they see the backlog rendered as a scrollable card list with status, category, epic, score, and complexity visible per item.
2. **Given** the user is viewing the backlog on desktop, **When** they apply a status filter and a free-text search, **Then** only items matching both filters remain visible and the dirty-count badge stays at zero.
3. **Given** an unauthenticated user opens the URL, **When** they browse and filter, **Then** they can read everything without being asked for credentials.

---

### User Story 2 - Propose backlog edits as a pull request (Priority: P2)

A maintainer wants to add a new item, change an item's status from `proposed` to `approved`, or correct a score, but doesn't want to open an editor and craft a commit by hand. They authenticate the navigator with a GitHub Personal Access Token, edit cells inline, accumulate several pending changes, then submit them as a single pull request that the team can review through the normal PR process.

**Why this priority**: Editing extends the navigator from a viewer into a triage tool, but it depends on Story 1 being in place and requires the contributor to hold a GitHub token, so it serves a narrower audience.

**Independent Test**: Open the navigator with a token that has write access to a fork, change one item's status field inline, verify the dirty-count badge increments, click submit, and confirm a pull request appears on GitHub containing only the changed cell and preserving the rest of the file byte-for-byte.

**Acceptance Scenarios**:

1. **Given** the user has supplied a valid GitHub token and made one inline edit, **When** they submit pending changes, **Then** a pull request is opened against the configured branch containing the edit and no incidental formatting changes elsewhere in the file.
2. **Given** the user has made several pending edits across multiple items, **When** they review the pending list, **Then** each edit shows the old and new value and can be reverted individually before submission.
3. **Given** the user discards pending edits, **When** they reload the page, **Then** no draft state persists and the navigator reflects the file as it exists on the remote branch.

---

### User Story 3 - Discover the navigator link from a pull request (Priority: P3)

When a contributor opens a pull request that touches the backlog file, reviewers get a comment on the PR with a one-click link that opens the navigator pre-loaded with the PR's branch and changes, so they can review the table-form diff in a readable layout rather than scanning raw markdown in the GitHub diff view.

**Why this priority**: A convenience that improves review quality but is not required for the navigator to be useful — reviewers can always paste the URL manually.

**Independent Test**: Open a pull request that modifies the backlog file. Verify that an automated comment appears on the PR within a short window, containing a navigator link whose URL parameters point at the PR's head branch. Clicking the link must load the navigator showing the PR's version of the file.

**Acceptance Scenarios**:

1. **Given** a pull request modifies the backlog file, **When** the workflow runs, **Then** a single comment is posted on the PR with a navigator link that opens the PR branch.
2. **Given** a pull request that does not touch the backlog file is opened, **When** the workflow runs, **Then** no comment is posted.
3. **Given** the same pull request is updated with additional commits to the backlog file, **When** the workflow re-runs, **Then** the existing comment is updated (or left as-is) rather than spawning duplicate comments.

---

### Edge Cases

- The backlog file's filename casing differs from what the navigator expects (the repo currently has `backlog.md` lowercase; the navigator documents `BACKLOG.md` uppercase). The integration must either rename the file or configure the navigator to point at the existing filename, without breaking links elsewhere in the repo.
- The backlog contains markdown features the navigator's parser does not recognise (footnotes, HTML, comment blocks). The viewer should still render the recognised tables and the file should round-trip without losing the unrecognised content.
- A reviewer opens a navigator link for a deleted or force-pushed branch. The navigator should show a clear "not found" state rather than a blank screen.
- The user's GitHub token expires or lacks the required scope to open pull requests. Submission should fail with a message that names the missing capability rather than silently dropping edits.
- Two reviewers submit overlapping edits via the navigator at the same time. The second submission should produce a PR that either merges cleanly or surfaces a conflict the user can resolve, not silently overwrite the first PR's changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST contain a backlog file at a path that the backlog-navigator can load, and the file MUST conform to the navigator's expected structure (Epics table, Items table, fixed 12-column shape, recognised status values).
- **FR-002**: The repository MUST publish, in its README or equivalent entry-point documentation, a working navigator URL that opens the current backlog without further configuration.
- **FR-003**: The navigator integration MUST allow read-only browsing without requiring the user to supply a GitHub credential.
- **FR-004**: Authenticated users MUST be able to submit backlog edits as a pull request rather than as a direct commit to the default branch.
- **FR-005**: Edits submitted through the navigator MUST preserve the rest of the backlog file byte-for-byte, changing only the cells the user edited.
- **FR-006**: A pull request that modifies the backlog file MUST cause a navigator review link, scoped to that PR's branch, to be made visible to reviewers (either as an automated PR comment or in PR template guidance).
- **FR-007**: The repository's documentation MUST explain to a new contributor how to use the navigator, including how to obtain a token and what scope it needs, and what to do if a token is lost or compromised.
- **FR-008**: Existing internal references to the backlog file (in README, CLAUDE.md, plan.md, skill prompts, and any tooling) MUST continue to resolve after the integration is in place.
- **FR-009**: The integration MUST NOT require running a backend service, a database, or any always-on infrastructure beyond what GitHub already provides.
- **FR-010**: If the backlog file's name or location changes as part of this integration, the change MUST be made in a single coordinated update that leaves no broken references in the repository.

### Key Entities *(include if feature involves data)*

- **Backlog file**: The single markdown source of truth for items, epics, statuses, scores, and complexity. Located in the repository root; consumed by both humans and the navigator.
- **Backlog item**: A row in the Items table representing one piece of work, with ID, title, category, epic, value/media/autonomy scores, total, complexity, and status.
- **Epic**: A row in the Epics table grouping related items; referenced by ID from individual items.
- **Navigator link**: A URL pointing at the hosted navigator with parameters that identify the repository, branch, and (optionally) pull request to load.
- **Pull request from navigator**: A standard GitHub pull request whose diff is confined to the backlog file and which is authored on behalf of a navigator user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new reviewer can open the published navigator link and locate any specific backlog item (by ID, title, status, or epic) in under 30 seconds, without reading any setup documentation.
- **SC-002**: 100% of edits submitted through the navigator arrive as pull requests; zero edits land as direct commits to the default branch.
- **SC-003**: A round-trip through the navigator (load file, make no edits, refresh) produces a backlog file that is byte-identical to the version on the remote branch.
- **SC-004**: For pull requests that touch the backlog file, reviewers reach the navigator view in a single click from the PR page.
- **SC-005**: The integration adds no new always-on hosting cost — the only recurring obligation is whatever the navigator's hosting model already imposes.
- **SC-006**: After the integration ships, no existing link, command, or skill in this repository that references the backlog returns "file not found".

## Assumptions

- The team is willing to adopt the navigator's prescribed table shape (12 columns, fixed status vocabulary) for the existing backlog. The current `backlog.md` already follows a compatible structure with one exception: filename casing.
- Contributors who want to edit through the navigator are willing and able to create a GitHub Personal Access Token with the scope the navigator requires; the navigator's existing documentation is treated as the canonical guide for this.
- The hosted instance at `deepbluecltd.github.io/backlog-navigator` is the intended deployment target; this repository will not self-host its own fork unless a later decision says otherwise.
- The pull-request comment workflow is desirable; if it proves noisy, it can be disabled per-repository without affecting the read and edit flows.
- The existing `backlog.md` file is the canonical backlog and any rename to `BACKLOG.md` (or alternative) is acceptable to the maintainers if needed for compatibility.
- This integration is purely additive — it does not replace any existing tooling (e.g. the speckit-navigator item already in the backlog as item 001 is a separate, complementary tool).
