# Contract: Navigator URL

The hosted navigator is reached at a single base URL with a small set
of query parameters. Two URL shapes are emitted from this repository
(one from the README, one from the PR-comment workflow); both MUST be
constructed exactly as described here so that any future change to
the URL contract is made in a single place.

## Base

```
https://deepbluecltd.github.io/backlog-navigator/
```

The trailing slash is preserved in every link.

## Query parameters

| Parameter | Purpose | Required | Source |
|---|---|---|---|
| `repo` | `owner/name` slug identifying the repository | yes | Constant: `DeepBlueCLtd/pptx-legacy-transform` |
| `branch` | Branch name whose `BACKLOG.md` to load | exactly one of `branch` or `pr` | README uses `main` |
| `pr` | Pull request number to load (head ref of the PR) | exactly one of `branch` or `pr` | Workflow uses `${{ github.event.pull_request.number }}` |
| `path` | Override the backlog file path | no | Omit — we rely on the navigator's default of `BACKLOG.md` |
| `dryRun` | Suppress write paths in the navigator UI | no | Omit |

## Canonical emitted URLs

**README (default branch view)**:

```
https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&branch=main
```

**PR-comment workflow (per-PR view)**:

```
https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&pr=<PR_NUMBER>
```

## Encoding rules

- Parameter values are URL-encoded; `/` in `repo` is left as-is per
  the navigator's documented convention.
- Parameters are joined with `&`; no trailing `&`.
- No fragment (`#...`) component is used.

## Fallback (documented, not currently used)

If the `?pr=` view is ever unavailable on the hosted instance, the
workflow MAY fall back to `?branch=${{ github.head_ref }}`. This is
the only sanctioned variation; any other URL shape requires updating
this contract first.
