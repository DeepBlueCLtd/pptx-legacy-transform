# Data Model: Import Author Gram Images

## Trees

### Incoming tree (read-only input)

```text
<incoming-root>/
└── <doc>/                 # matches a source doc folder name, case-insensitively
    └── <gram>/            # matches a gram folder name under the source container, case-insensitively
        └── <duration>[ _]<stem>.<jpg|jpeg|png>   # candidate image; duration + stem split on space OR underscore
```

Partial coverage at every level is normal. Non-image files and empty folders
are debug-logged and ignored. The tool never creates, modifies, renames, or
deletes anything under `<incoming-root>`.

### Source tree (mutation target, apply mode only)

```text
source/
└── <doc>/
    ├── <doc-title>.pptx           # ignored by this tool
    └── <container>/               # the single subdirectory (normal), OR the doc
        └── <gram>/                # folder itself when it holds a large flat set
            ├── Lofar N.glc        # 0+ GLCs; the unit of conversion
            ├── <stem>.wav         # referenced by a GLC; never touched
            └── <stem>.<ext>       # written by apply (copy of incoming image)
```

## Entities

### CandidateImage

| Field | Type | Source | Notes |
|---|---|---|---|
| `path` | Path | incoming tree | absolute path of the delivered screenshot |
| `raw_token` | str | filename | leading run up to first space |
| `seconds` | Optional[int] | parsed from `raw_token` | `None` ⇒ outcome `unparseable-duration` |
| `stem` | str | filename after token | must be non-empty to be parseable |
| `extension` | str | filename | `.jpg`/`.jpeg`/`.png`, case-insensitive test, case preserved |

Parse rule: token matches `^(\d+)m(?:(\d{1,2})s)?$` case-insensitively →
`seconds = m*60 + s`; stem = remainder after the first space run, stripped.

### GramFolderView

The per-gram matching context, built once per matched gram folder by parsing
every `*.glc` in it (sorted order):

| Field | Type | Notes |
|---|---|---|
| `folder` | Path | source gram folder |
| `wav_refs` | dict[stem → list[GlcRef]] | GLCs whose inner asset is a `.wav`; keyed by wav stem |
| `image_refs` | dict[stem → list[GlcRef]] | GLCs whose inner asset is an image (drives `already-converted`) |
| `unreadable` | list[Path] | GLCs `parse_glc` returned no filename for (`glc-unreadable`) |

`GlcRef` = `(glc_path, referenced_basename, has_crop: bool)` — `has_crop` is
true when the raw text already contains `<bitmap_crop_values>` (drives
`glc-already-cropped`).

### Match

A verified pairing, the unit of apply:

| Field | Type | Notes |
|---|---|---|
| `image` | CandidateImage | |
| `gram_folder` | Path | |
| `glc_refs` | list[GlcRef] | every wav-backed GLC whose wav stem equals `image.stem` — all rewritten; one copy |
| `target_name` | str | `image.stem + image.extension` (extension case preserved) |

### Outcome (per finding; the report and tally are aggregations of these)

| Class | Level | Meaning / report payload |
|---|---|---|
| `matched` / `applied` | info | verify: would apply; apply: did apply |
| `unmatched-doc` | report | incoming doc folder with no exact source counterpart + up to 3 nearest candidates + drift label |
| `structurally-ambiguous-doc` | report | source doc folder with 0 or 2+ subdirectories; doc skipped |
| `unmatched-gram` | report | incoming gram folder with no exact counterpart under the container + candidates + drift label |
| `unparseable-duration` | report | image whose leading token fails the grammar (or empty stem); raw token echoed — the format survey |
| `unmatched-image` | report | parsed image whose stem matches no GLC-referenced asset stem; folder's available wav stems echoed |
| `ambiguous` | report | 2+ incoming images resolving to the same wav stem in one gram folder; all listed; none applied |
| `already-converted` | info | stem matches a GLC-referenced *image* — idempotency class, clean post-apply verify |
| `glc-unreadable` | warn | GLC skipped (malformed / no inner filename); others in the folder still process |
| `glc-already-cropped` | warn | wav-backed GLC already carrying `bitmap_crop_values`; skipped, never overwritten |

**Drift labels** (attached to `unmatched-*` when a nearest candidate exists):
`case-only`, `whitespace-only`, `case+whitespace`, `token-drift('X' → 'Y')`,
`other`. `token-drift` pairs are aggregated with counts in the report's trend
section.

### Tally

Run summary — one integer per outcome class, emitted to console, log, and the
report footer. Apply additionally reports `glcs_rewritten` and `images_copied`
(they differ when two GLCs share one wav).

## State transitions (apply, per Match)

```text
verified Match
  → copy image  : incoming path → gram_folder/target_name   (copyfile, overwrite)
  → per GlcRef  : in-memory text edit =
                    rewrite first <filename> inner text → target_name
                  + insert <bitmap_crop_values><bottom_crop>{seconds}</bottom_crop></bitmap_crop_values>
                    immediately after </filename>, matching file indentation
  → single write of the edited text (anchor missing ⇒ error, skip file, no write)
  → wav: untouched, by design
```

Re-run: the GLC now references an image → the gram lands in
`already-converted` → no further change (idempotency).

## Validation rules

- Duration grammar per CandidateImage above; violations are data to report,
  never fatal (Zone B/C — author-typed input).
- Container resolution: exactly one subdirectory of the source doc folder, or
  the doc folder itself when it holds ≥ `FLAT_DOC_MIN_GRAMS` subdirectories (a
  container-less publication); an in-between count skips and reports the doc.
- Matching folds case (folders and stems); whitespace/token drift is reported
  with suggestions, never absorbed.
- Verify mode writes nothing except `ingest_report.txt` and `ingest.log`
  (both in cwd, outside both trees).
- Apply refuses per-file (skip + count) rather than per-run: one bad GLC never
  aborts the corpus (Principle IV), and a GLC is never half-written
  (Principle VII on our own output).
