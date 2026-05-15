# Quickstart: Backlog Navigator Integration

This walkthrough is the executable acceptance check for the feature.
It is written for a maintainer with push access to the repository
and a phone or second device on which to open the navigator. The
whole thing should take under fifteen minutes once the changes are
merged.

## Prerequisites

- The feature has been merged to `main`.
- You have a GitHub Personal Access Token with the scope the
  navigator's own README documents (browse the link from this
  repo's README to find it).
- You have a phone or a private/incognito browser window where you
  are signed out of this repository.

## Step 1 — Browse the backlog without credentials

1. From a signed-out browser, open the URL printed in this
   repository's README under "Browse the backlog".
2. Confirm:
   - The page loads without prompting for a token.
   - The Epics table renders with at least one row.
   - The Items table renders with all expected columns visible.
   - The status filter dropdown lists every workflow state used in
     the table.
3. Apply a status filter (e.g. `proposed`) and a free-text search
   (e.g. `navigator`). Confirm only matching items remain visible.

If any of the above fails, the integration is broken — stop and
file a bug instead of continuing.

## Step 2 — Open a PR that touches the backlog

1. On a feature branch, edit one cell of `BACKLOG.md` (e.g. flip a
   `proposed` to `approved` for an item you actually intend to
   approve).
2. Push the branch and open a pull request.
3. Within a minute, confirm that a single comment from
   `github-actions[bot]` appears on the PR. The comment must:
   - Start with the hidden marker `<!-- backlog-navigator-link -->`
     (visible in "Edit" mode).
   - Contain a link to the navigator with `?pr=<this PR's number>`.
4. Click the link. Confirm the navigator opens loaded with the PR's
   branch, and that the cell you changed shows the new value.
5. Push a second commit to the same branch. Confirm the same
   workflow run updates the existing comment rather than spawning a
   second one.

## Step 3 — Submit an edit through the navigator

1. From the navigator (signed-out tab from Step 1 will not work —
   use a tab where you've configured your token per the navigator's
   own setup guide), make one inline cell edit to a different
   item.
2. Confirm the dirty-count badge increments to `1`.
3. Submit the pending change. Confirm a new pull request is opened
   on this repository whose diff is confined to `BACKLOG.md` and
   contains only the cell you edited — surrounding whitespace,
   alignment, and trailing newline are unchanged.

If the diff shows incidental whitespace or alignment changes, the
round-trip invariant in `contracts/backlog-file-schema.md` has been
violated — file a bug against the navigator project.

## Step 4 — Verify no existing references broke

Run, from a fresh clone of `main`:

```bash
grep -rni 'backlog\.md' --include='*.md' --include='*.py' --include='*.bat' --include='*.yml' .
```

Every match should be either (a) in this feature's own spec/plan
artifacts (where the historical name is mentioned for clarity) or
(b) updated to `BACKLOG.md`. There should be no live link, import,
or script reference that still expects the lowercase filename.

## Done

If all four steps pass, the feature satisfies SC-001 through SC-006
and the spec's three user stories can be considered accepted.
