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
| `branch` | Branch name whose `BACKLOG.md` to load | yes (used in both emitted URLs) | README uses `main`; workflow uses `${{ github.event.pull_request.head.ref }}` |
| `pr` | Pull request number — **documented as legacy form, "resolves against bundled default"** | no | Not used by either emitted URL; see "Out of contract" |
| `dryRun` | Suppress write paths in the navigator UI | no | Omit |

Note: the navigator does not currently expose a `?path=` parameter,
so the backlog filename is fixed by the navigator at `BACKLOG.md`
(case-sensitive). This is why the rename described in `research.md`
is required.

## Canonical emitted URLs

**README (default branch view)**:

```
https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&branch=main
```

**PR-comment workflow (per-PR view)**:

```
https://deepbluecltd.github.io/backlog-navigator/?repo=DeepBlueCLtd/pptx-legacy-transform&branch=<PR_HEAD_REF>
```

`<PR_HEAD_REF>` is the PR's head branch name. In the workflow this
comes from `${{ github.event.pull_request.head.ref }}`. Branch names
containing characters that need URL-encoding (e.g. `/`) MUST be
URL-encoded before substitution.

## Encoding rules

- Parameter values are URL-encoded; `/` in `repo` is left as-is per
  the navigator's documented convention.
- Parameters are joined with `&`; no trailing `&`.
- No fragment (`#...`) component is used.

## Out of contract

- `?pr=<n>` is documented by the navigator project as a **legacy
  form** that "resolves against bundled default". It is not used
  in either of the emitted URLs above. Do not add it back without
  updating this contract first.
- Any URL shape other than the two canonical forms above requires
  updating this contract first.
