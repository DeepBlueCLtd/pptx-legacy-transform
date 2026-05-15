# Contract: Backlog File Schema

This contract pins the shape of `BACKLOG.md` that the hosted
backlog-navigator can parse. It is informative — the navigator's
parser is the authoritative implementation — but downstream tasks
(`/speckit-tasks`) and reviewers should treat any drift from this
contract as a defect.

## File location

- Path: `BACKLOG.md` (uppercase) at the repository root.
- Encoding: UTF-8, LF line endings, terminated by a single trailing
  newline.

## Document structure

The file is composed, in this order, of:

1. A top-level heading (`# Backlog`).
2. Prose describing the document's purpose.
3. A "Scoring Criteria" section containing scoring and complexity
   tables and a "Workflow" status table. These are read by humans
   only — the navigator does not enforce them, but they MUST remain
   consistent with the enum values used in the Items table.
4. An "Epics" heading followed immediately by the **Epics table**.
5. An "Items" heading followed immediately by the **Items table**.

Sections 1–3 are free-form for humans; sections 4–5 are
machine-relevant.

## Epics table

A markdown pipe table with this exact header row (column order matters):

```
| ID | Title | Description | Status |
```

Followed by a header-separator row of at least three dashes per cell.
Each subsequent row is one epic.

**Cell rules**:

- `ID`: matches `^E\d{2,}$`.
- `Title`: non-empty plain text or inline markdown.
- `Description`: one sentence, plain text or inline markdown.
- `Status`: one of the workflow statuses defined in `data-model.md`.

## Items table

A markdown pipe table with this exact 12-column header (column order
matters; trailing columns are reserved by the navigator and rendered
empty by this repository):

```
| ID | Title | Category | Epic | V | M | A | Total | Complexity | Status |
```

Followed by a header-separator row. Each subsequent row is one item.

**Cell rules**:

- `ID`: matches `^\d{3}$`, unique across the table, assigned
  monotonically.
- `Title`: plain text or inline markdown; may contain links. No
  pipe characters (`|`) — escape as `\|` if unavoidable.
- `Category`: one of the categories named in `data-model.md`.
- `Epic`: foreign key to an Epic `ID`, or empty.
- `V`, `M`, `A`: integers in `1..5`.
- `Total`: integer; MUST equal `V + M + A`. This is invariant — the
  PR-comment workflow does not check it, but reviewers and the
  navigator's totals column do.
- `Complexity`: one of `Low`, `Medium`, `High`.
- `Status`: one of the workflow statuses; see `data-model.md` for the
  permitted transitions.

## Round-trip invariant

When the navigator serialises this file after loading it, the
result MUST be byte-identical to the input (SC-003). Practically
this means:

- No trailing whitespace appears or disappears from rows.
- Column alignment (the spaces used to pad cells in the markdown
  source) is preserved exactly.
- Unrecognised markdown features outside the two machine-relevant
  tables (HTML comments, footnotes, fenced code blocks) are passed
  through untouched.
- The trailing newline at end of file is preserved.

## Completed items

Items in `complete` status are rendered with their `Title` cell
wrapped in `~~` (strikethrough) per the backlog header's convention.
The navigator MUST treat this as styling, not as part of the title's
semantic identity, so filters on title text continue to match.
