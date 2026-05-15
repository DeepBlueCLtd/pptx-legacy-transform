# Contract: PR Navigator-Link Workflow

The single GitHub Actions workflow added by this feature. This
contract pins the trigger, the comment shape, and the idempotency
rule so a future edit cannot accidentally change behaviour without
also updating this document.

## File

`.github/workflows/backlog-navigator-pr-link.yml`

## Trigger

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - BACKLOG.md
```

- `opened`: first time the PR is opened with backlog changes.
- `synchronize`: subsequent commits pushed to the PR branch.
- `reopened`: previously closed PR brought back to life.
- The `paths:` filter means the job is not even queued for PRs
  that do not touch `BACKLOG.md` (FR-006, edge case "PR doesn't
  touch the backlog").

## Permissions

```yaml
permissions:
  pull-requests: write   # to create/update comments
  contents: read          # implicit, kept explicit for clarity
```

No other permissions are granted; the workflow does not push code,
create branches, or read other repositories.

## Job: post-or-update-comment

Runs on `ubuntu-latest`. Steps:

1. **Compose the comment body** (in-line shell or step output). The
   body MUST begin with the marker line and MUST embed the
   navigator URL produced according to `navigator-url.md`:

   ```
   <!-- backlog-navigator-link -->
   Review this PR's backlog changes in the navigator:
   https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&pr=${{ github.event.pull_request.number }}
   ```

2. **Find existing comment by marker** and either create a new
   comment or update the existing one in place. The reference
   implementation is `peter-evans/create-or-update-comment` pinned
   by commit SHA; `body-includes: '<!-- backlog-navigator-link -->'`
   is the lookup key.

## Idempotency rule

A given pull request MUST end up with **exactly one** navigator-link
comment from this workflow, regardless of how many times the
workflow runs. The marker comment on the first line is the sole
mechanism for ensuring this.

## Failure behaviour

If the GitHub API call to create or update the comment fails, the
workflow MUST exit non-zero (visible as a red check on the PR). It
must NOT swallow the failure and report success — that would
violate the implicit observability principle and hide a broken
review affordance.

## Out of contract

The following are deliberately not part of this workflow's
responsibilities; they are mentioned to keep future PRs from
accidentally adding them under this file's name:

- Linting or validating `BACKLOG.md` against the schema in
  `backlog-file-schema.md`. (See research.md §6.)
- Auto-merging the PR.
- Posting comments on issues.
- Reacting to comment edits or deletions.
