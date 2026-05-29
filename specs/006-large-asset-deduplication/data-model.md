# Phase 1 Data Model: Large Asset Deduplication

The feature introduces one CSV field, one DITA element, and two transient
in-memory structures. No database; all state is the CSV and the DITA tree.

---

## Entity 1 — `master_png_path` (new, optional CSV column)

| Aspect | Value |
|---|---|
| Position | Appended at the **right edge** of the CSV (after the current last column) |
| Required? | **No** — optional/additive; read with empty default, never in the strict required-set |
| Type | string (a source-relative asset path, same space as `png_path`); or empty |
| Empty means | Row is **not** redirected (master row, non-duplicate, or unprocessed CSV) |
| Non-empty means | Row is redirected; the value is the **master row's `png_path`** to link to |
| Written by | `deduplicate_csv.py` (the extractor does not emit it) |
| Read by | `generate_dita.py` via `row.get("master_png_path", "")` |

**Validation / rules**:
- Only rows whose `file_size` parses to an integer **strictly > threshold**
  (default 10 MiB) are eligible to be redirected (FR-003).
- A non-empty `master_png_path` MUST equal the `png_path` of an existing,
  non-redirected row in the same CSV (the master). If it is blank-but-present in
  a way the generator cannot resolve, the row is treated as non-redirected and a
  WARNING is logged (FR-014).
- The master row itself carries an **empty** `master_png_path`.
- Relationship to existing fields: orthogonal to `target_doc`/`target_chapter`
  (refactor columns) and `png_path` (unchanged meaning). For a `.wav` row the
  redirection links to the master `.glc` even though `master_png_path` names the
  master's `.wav` `png_path` — the generator maps `.wav` master keys to the
  master's `.glc` link target (see Entity 3).

---

## Entity 2 — `<data name="original-asset-path">` (new, in generated DITA)

The provenance record. Emitted **only** on a redirected lofar.

```xml
<section outputclass="lofar-stage">
  <title>…display text…</title>
  <!-- image case: GramFrame gram-config table, OR audio case: <p><xref …/></p> -->
  …
  <data name="original-asset-path" value="supporting/gram-07/Lofar 1 I.wav"/>
</section>
```

| Aspect | Value |
|---|---|
| Element | `<data>` (standard DITA metadata domain; no specialisation) |
| `@name` | exactly `original-asset-path` |
| `@value` | the **redirected row's own `png_path`** (where the file should sit locally) |
| Placement | child of the redirected lofar `<section>`, emitted last (after title + table/`<p>`) |
| Cardinality | exactly one per redirected lofar; **absent** on non-redirected lofars |
| Role | (a) sole flag that the lofar was redirected (FR-007); (b) the anchor for reversal (FR-008) |
| HTML | suppressed from default trainee XHTML (FR-006) |

**State transitions**:
- *Non-redirected → redirected* (export of a post-processed CSV): asset not
  copied locally; href points to master; `<data>` added.
- *Redirected → rehydrated* (`rehydrate_dita.py`): master (and adjacent `.wav`
  for a pair) copied back under the local slug; href re-localised; `<data>`
  removed. Result is indistinguishable from a never-deduplicated topic (SC-004).

---

## Entity 3 — Master Index (transient, in `generate_dita.py`)

Built in the **index pass**, consumed in the **emit pass**. Not persisted.

```
master_index: dict[str, MasterTarget]
  key   = master row's png_path (source-relative)            # the master_png_path value redirectors carry
  value = MasterTarget(
            topic_dir,        # the master gram's output folder (Path)
            link_basename,    # slug of the file a redirector links to:
                              #   image rows → slugify_asset_name(png basename)
                              #   .wav rows  → slugify_asset_name(glc basename)   (FR-009: link targets .glc)
          )
```

**Population rule**: during the index pass, for every **non-redirected**
asset-owning glc/image/analysis row, record `png_path → MasterTarget`. Only keys
that are actually referenced by some `master_png_path` need survive, but
recording all is simplest and harmless.

**Resolution rule** (emit pass): a redirected row's href =
`relpath(master.topic_dir / master.link_basename, this_gram.topic_dir)` as POSIX
(via the existing `resolve_image_href`/`os.path.relpath` path). If the key is
absent (master missing/blank), the row falls back to the normal local-copy path
and a WARNING is logged (FR-014).

---

## Entity 4 — Deduplication Unit (conceptual)

| Lofar kind | Unit | Master link target | Files at master folder |
|---|---|---|---|
| Image (`.png`/`.jpg`/`.jpeg`) | the single image file | the master image | the image |
| Audio (`.wav` via `.glc`) | the `.glc`/`.wav` **pair** | the master `.glc` | the `.glc` **and** its adjacent `.wav` |

The audio pair is detected, redirected, and rehydrated **as a unit**: the
redirected gram receives neither file; the master gram holds both side by side so
the on-PC GLC viewer's adjacent-`.wav` lookup always resolves (FR-009).

---

## Relationships summary

```
CSV row ──(file_size > threshold & content-dup)──► redirected
   │ master_png_path = master row.png_path
   ▼
generate_dita.py index pass:  master row.png_path ──► MasterTarget(topic_dir, link_basename)
   │
   ▼ emit pass (redirected row)
DITA lofar <section>:  href → ../master/<link_basename>
                       + <data name="original-asset-path" value="row.png_path"/>
   │
   ▼ rehydrate_dita.py (inverse)
DITA lofar <section>:  href → ./<local slug from data value>   (+ master copied back; <data> removed)
```
