# Phase 0 Research: Large Asset Deduplication

This document resolves the questions the spec deferred to planning. Each entry
records the **Decision**, the **Rationale**, and the **Alternatives considered**.

---

## R1 — How are duplicates detected, and what is the "size" threshold?

**Decision**: `deduplicate_csv.py` considers a row a *redirection candidate*
only when its `file_size` cell parses to an integer **strictly greater than**
`DEFAULT_THRESHOLD_BYTES = 10 * 1024 * 1024` (10 MiB = 10,485,760 bytes),
overridable with `--threshold-bytes`. Among the candidates, rows are grouped by
**content identity**: a cheap `(file_size)` pre-filter followed by a confirming
`sha256` of the file at `image_root / png_path`. Within each group of ≥2
byte-identical files, the **first occurrence in deterministic order** (sorted by
the row-identity tuple `(publication, chapter, gram_id, topic_type, sequence)`)
is the master; the others are redirected to it.

**Rationale**: `file_size` already exists in the CSV precisely to "surface
duplicate assets across publications during human review" (csv-schema §col
`file_size`), so it is the natural cheap pre-filter and avoids hashing the small
majority of files. `sha256` confirmation guarantees we never redirect two files
that merely share a size. Strict `>` matches FR-003 ("at or below the threshold
MUST never be redirected"). Deterministic ordering makes master nomination
stable across runs, which the export's idempotency contract (R9/FR-013) depends
on. 10 MiB is read as the binary mebibyte interpretation of the user's "10Mb"
cut-off; it is configurable so the operator can tune it.

**Alternatives considered**:
- *Path-equality detection* (group by identical `png_path`): rejected — the same
  audio is copied into many *per-gram* folders, so source paths can differ even
  when bytes are identical; content hashing is the robust signal the spec's
  "detecting duplicate assets across rows" implies.
- *Hash everything*: rejected — needless I/O over hundreds of small images; the
  `file_size` pre-filter plus threshold scopes hashing to the few large files.
- *Decimal megabytes (10,000,000)*: rejected as the default but supported via
  `--threshold-bytes`; the mebibyte reading is the conventional "10 MB" on disk.

---

## R2 — Where does the single physical master copy live, and how is it referenced?

**Decision**: The master copy lives in the **master gram's own output folder** —
i.e., the first-occurrence row is treated as a *normal, non-redirected* row and
copies its asset locally exactly as today. Redirected rows do **not** copy; their
lofar href is a relative path (with `../` segments) from the redirected gram's
`topic_dir` to the master copy, computed by the existing `resolve_image_href` /
`os.path.relpath` machinery in `generate_dita.py`. No new `shared/` directory is
introduced.

**Rationale**: The spec's US1 explicitly nominates "the first gram's copy as the
master" and requires the master be "written exactly once" — the master gram
already writes it once, so reusing that folder is the minimal change and keeps
the master gram fully self-contained (it is never itself redirected, so it stays
movable). `resolve_image_href` already returns `..`-bearing POSIX relative paths,
so cross-folder hrefs need no new code. Avoiding a `shared/` tree keeps the
output layout unchanged for every non-redirected gram (supports FR-010 byte
identity).

**Alternatives considered**:
- *A dedicated `shared/large-assets/` directory*: rejected — adds a new output
  location, changes layout, and complicates the "master gram stays a movable,
  self-contained pair" property the maintainers rely on.
- *Storing the master's output path directly in the CSV*: rejected — the
  post-process step would have to replicate the generator's folder/slug logic,
  duplicating (and risking drift from) the single source of truth in
  `generate_dita.py`. Instead the column stores a *source* path (see R4).

---

## R3 — Will DITA-OT carry cross-folder (`../`) image/xref hrefs and emit the master once? (FR-011)

**Decision**: Treat this as a **verification step** in `publish_html.py`'s test
layer rather than a code change. DITA-OT's HTML5 transform resolves `<image
href>` / `<xref href>` relative to the topic and copies referenced binaries into
the output relative to the map; a single master referenced by many topics via
`../` is the standard DITA "shared resource" pattern and is emitted once.
`publish_html.py` is edited **only** if the verification (a Jest assertion that
the deduplicated asset appears once and renders) fails — in which case the
fallback is to relativise/flatten the shared asset during the publish staging
step.

**Rationale**: Cross-topic shared images are idiomatic DITA; DITA-OT
de-duplicates copied resources by resolved target path. Verifying empirically
(an HTML test) is cheaper and safer than pre-emptively rewriting the publisher.
The `<data>` element is in the metadata domain and is suppressed from default
XHTML output, so it cannot leak into trainee HTML (FR-006).

**Alternatives considered**:
- *Pre-emptively rewrite `publish_html.py` to stage a shared asset folder*:
  rejected as premature — adds complexity before evidence it is needed.
- *Inline/base64 the asset*: rejected — defeats the size-reduction goal.

---

## R4 — What exactly does `master_png_path` store, and how does the generator resolve it?

**Decision**: `master_png_path` stores the **master row's `png_path`** (a
source-relative path, the same coordinate space as `png_path`). It is **empty**
for the master row itself and for every non-redirected row. The generator runs a
**two-pass** emit:

1. **Index pass** — iterate all rows in deterministic order, computing each
   gram's `topic_dir` and link href for its asset, and record a map
   `master_key (source png_path) → (master_topic_dir, link_href_basename)`. For
   image rows the link basename is the slugified image; for `.wav` rows it is the
   slugified **`.glc`** (the link target for the pair, FR-009).
2. **Emit pass** — for a row whose `master_png_path` is non-empty and present in
   the index, skip the local copy, compute the relative href from this gram's
   `topic_dir` to the master location, emit the lofar with that href, and append
   `<data name="original-asset-path" value="{this row's png_path}"/>`.

**Rationale**: Storing a *source* path (not an output path) keeps
`deduplicate_csv.py` ignorant of output folder/slug rules — the generator stays
the single source of truth for slugs and folders (avoids drift, R2). The master
row is guaranteed non-redirected and asset-owning, so its `png_path` is a stable
lookup key that the index pass can always resolve to a real output location. The
redirected row's *own* `png_path` is what goes into `<data>`, because that is
"where the file is meant to sit locally" — exactly what rehydration needs.

**Alternatives considered**:
- *Single-pass emit*: impossible — a redirected gram may reference a master gram
  that has not yet been emitted; the index pass removes the ordering dependency.
- *Storing the master's output href in the CSV*: rejected (see R2) — duplicates
  generator logic in the post-processor.

---

## R5 — How is the provenance recorded so it is DTD-valid, survives DITA-OT, and is reversible? (FR-006, FR-007, FR-008)

**Decision**: A single DITA `<data name="original-asset-path" value="{original
png_path}"/>` element, appended as a child of the redirected lofar's
`<section>` (the GramFrame `lofar-stage` section for images, or the GLC-viewer
`lofar-stage` section for audio), placed after the title and before/after the
table/`<p>` as the last metadata child. Its **presence alone** flags the lofar
as redirected — no separate `@outputclass` token (FR-007).

**Rationale**: `<data>` is part of the standard DITA metadata domain, valid in
`<section>` without specialisation, round-trips through DITA-OT, and is
suppressed from default XHTML — satisfying every clause of FR-006. The
`name`/`value` attribute pair carries an arbitrary path safely (unlike
`@outputclass`, a space-tokenised class list a path would corrupt). The spec's
Assumptions section already pins this choice over custom attributes, overloaded
`@outputclass`, and conref/conkeyref; this research confirms it against the
actual section shapes in `generate_dita.py` (`_append_gramframe_table`,
`_append_glc_viewer_link`).

**Alternatives considered**: custom attribute (DTD-invalid), `@outputclass`
token (path-unsafe + redundant with `<data>`), conref/conkeyref (XML reuse, does
not reduce binary count) — all rejected per the spec's Assumptions.

---

## R6 — How does rehydration reverse the operation from the DITA alone? (FR-012)

**Decision**: `rehydrate_dita.py` walks the generated DITA tree, and for each
lofar `<section>` containing `<data name="original-asset-path" value="P">`:
1. Resolves the master file from the lofar's link href (the redirected
   `<image href>` / `<xref href>`), relative to the topic's folder.
2. Recomputes the **local slug** from `basename(P)` via the same
   `slugify_asset_name` rule, and copies the master file into **this gram's
   folder** under that slug. For an audio pair, the master `.glc`'s **adjacent
   `.wav`** is copied alongside (the `.glc` href's sibling `.wav`).
3. Rewrites the lofar href to the local copy and **removes** the `<data>`
   element.
A lofar without the `<data>` element is left untouched (it was never
deduplicated).

**Rationale**: The redirected href records *where to copy from*; the `<data>`
value records *where it should sit locally* — together a pure inverse transform
needing no extraction inputs (FR-008). Reusing `slugify_asset_name` guarantees
the restored local filename matches what a never-deduplicated export would have
produced, so SC-004's "restored topic matches a never-deduplicated one" holds.
The audio pair is restored as a unit so the on-PC GLC viewer's adjacent-`.wav`
lookup keeps working (FR-009).

**Alternatives considered**: storing a separate `dedup-master` record — rejected;
the href already encodes the master location, so one `<data>` element suffices
for both directions (spec Assumptions).

---

## R7 — How is inert-by-default byte identity guaranteed? (FR-010, SC-005)

**Decision**: `master_png_path` is read with `row.get("master_png_path", "")`
and is **not** added to the strict `CSV_COLUMNS` required-set that
`read_csv` validates. When the column is absent, or present-but-empty on every
row, the index/emit passes take exactly the existing code path (every asset
copied locally, no `<data>` emitted), producing byte-identical output.

**Rationale**: `read_csv` raises on *missing required* columns but tolerates
*extra* columns, so keeping `master_png_path` optional preserves both the current
16-column `source.csv` and any legacy CSV. This mirrors how the codebase reads
other optional cells with empty defaults.

**Alternatives considered**: adding the column to `CSV_COLUMNS` — rejected; it
would make legacy CSVs fail validation and break FR-010.

---

## R8 — Idempotency of the post-processor and the deduplicated export. (FR-013, SC-006)

**Decision**: `deduplicate_csv.py` is deterministic (stable sort by row-identity
tuple; stable hashing) so re-running it over the same inputs yields a
byte-identical CSV. The export's existing idempotency (deterministic iteration,
`copy2` mtime preservation, LF/UTF-8-no-BOM serialisation) is preserved because
the index pass uses the same deterministic ordering and emits the same `<data>`
value each run.

**Rationale**: Idempotency is an existing, tested contract (R9,
`test_idempotent_output`); the new code introduces no timestamps or
set-ordering. The new tests assert a second export run is byte- and
stat-identical, and that a second `deduplicate_csv.py` run produces an identical
CSV.

**Alternatives considered**: none — idempotency is non-negotiable parity.
