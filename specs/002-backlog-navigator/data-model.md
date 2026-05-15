# Data Model: Backlog Navigator Integration

This feature adds no new persisted state. The only "data" involved is
the existing backlog file, which already has an implicit schema that
the hosted navigator depends on. This document records that schema as
an entity model so downstream tasks and reviewers can check changes
against it without re-reading the navigator's source.

## Entity: Backlog File

**Identity**: The single markdown file `BACKLOG.md` at the repository
root.

**Validation rules**:

- File MUST exist at the repository root after this feature ships.
- File MUST be valid UTF-8 markdown.
- File MUST contain exactly one Epics table and exactly one Items
  table, in that order, each preceded by the section heading
  documented in the spec.
- The file MUST round-trip through the navigator's parser-serialiser
  byte-for-byte (SC-003). Concretely: any change made through the
  navigator UI must leave untouched cells, surrounding whitespace,
  trailing newline, and column alignment exactly as they were on
  disk.

**State**: None — the file is read each time the navigator loads it.

## Entity: Epic (row in the Epics table)

**Fields**:

| Field | Type | Notes |
|---|---|---|
| ID | string | Stable identifier, `E` followed by digits (e.g. `E01`). |
| Title | string | Short human-readable name. |
| Description | string | One-sentence summary. |
| Status | enum | One of the workflow states listed in the backlog header. |

**Relationships**: Referenced by `Epic` foreign key from rows in the
Items table.

**Validation rules**:

- `ID` MUST be unique within the Epics table.
- `Status` MUST be one of the documented workflow states; any
  unrecognised value blocks the navigator's status-filter dropdown.

## Entity: Item (row in the Items table)

**Fields** (10 columns, matching the shape of the existing
`backlog.md` and what the navigator's parser reads from this repo):

| # | Field | Type | Notes |
|---|---|---|---|
| 1 | ID | string | Three-digit zero-padded sequential id (e.g. `001`). |
| 2 | Title | string | Free-text; may contain inline markdown links. |
| 3 | Category | enum | `Tooling`, `Bug`, `Feature`, `Docs`, `Tech Debt` (extend in the backlog's own header table when needed). |
| 4 | Epic | string | Foreign key to an Epic ID, or empty. |
| 5 | V | int | Value score 1-5 per the backlog's scoring criteria. |
| 6 | M | int | Media score 1-5. |
| 7 | A | int | Autonomy score 1-5. |
| 8 | Total | int | Sum of V+M+A; must equal that sum. |
| 9 | Complexity | enum | `Low`, `Medium`, `High`. |
| 10 | Status | enum | One of the workflow states (`needs-interview`, `proposed`, `approved`, `specified`, `clarified`, `planned`, `tasked`, `implementing`, `complete`). |

The navigator README describes a "virtualized 12-column table for
desktop"; that refers to the desktop UI's rendering (data columns
plus UI-only columns such as selection and actions), not a markdown
schema requirement. The on-disk file is and remains a 10-column
table.

**Relationships**:

- `Epic` → Epics table by ID (many-to-one, optional).

**State transitions** (column 10, `Status`):

```
needs-interview ──┐
                  ├──▶ proposed ──▶ approved ──▶ specified ──▶ clarified ──▶ planned ──▶ tasked ──▶ implementing ──▶ complete
                  │
                  └──▶ (bug fast-track) approved ──▶ implementing ──▶ complete
```

Transitions are advisory — the navigator does not enforce them. The
backlog's own header documents the workflow.

## Entity: Navigator URL

Not persisted, but worth modelling because it appears in two artifacts
(README and PR-comment workflow) that must stay consistent.

**Fields**:

| Field | Source | Example |
|---|---|---|
| Base | constant | `https://deepbluecltd.github.io/backlog-navigator/` |
| `repo` | constant | `DeepBlueCLtd/pptx-legacy-transform` |
| `branch` | per-context | `main` (README) |
| `pr` | per-context | PR number (workflow) |

**Validation rule**: Exactly one of `branch` or `pr` should be set
in any emitted URL. The workflow uses `pr`; the README uses `branch`.

## Entity: PR Navigator-Link Comment

**Identity**: A single comment on a pull request, identified by the
hidden marker `<!-- backlog-navigator-link -->` as its first line.

**Fields**:

| Field | Notes |
|---|---|
| Marker | First-line HTML comment used for idempotent lookup. |
| Body | Short prose ("Review this PR's backlog changes in the navigator:") plus the navigator URL with `?pr=<NUMBER>`. |
| Author | The GitHub Actions bot user (`github-actions[bot]`). |

**State transitions**:

- *Absent* → *Present*: first time the workflow runs for a PR that
  touches the backlog file.
- *Present* → *Updated*: subsequent runs of the workflow on the same
  PR. The marker ensures the existing comment is edited rather than
  duplicated.
- *Present* → *Stale*: if a later commit removes the backlog change
  from the PR, the comment remains (acceptable — the link still
  resolves to a valid navigator view).
