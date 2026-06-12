# Contract: `deduplicate_csv.py` and `rehydrate_dita.py` CLIs

Two new top-level scripts following the repo's `verb_noun.py` convention and the
existing `main(argv) -> int` / `argparse` pattern (`generate_dita.py`,
`extract_to_csv.py`).

---

## `deduplicate_csv.py` — post-process the signed-off CSV (US3, FR-001/002/003/014)

Reads a signed-off CSV, detects large duplicated assets, and writes a copy with
the optional `master_png_path` column populated. Inert-safe: assets at/below the
threshold or used only once are never redirected.

```
python deduplicate_csv.py \
    --csv source.csv \
    --image-root source/ \
    --out source.dedup.csv \
    [--threshold-bytes 10485760]
```

| Argument | Required | Default | Meaning |
|---|---|---|---|
| `--csv` | yes | — | input signed-off CSV |
| `--image-root` | yes | — | root the `png_path` cells resolve against (for hashing) |
| `--out` | yes | — | output CSV path (may equal `--csv` to rewrite in place) |
| `--threshold-bytes` | no | `10485760` (10 MiB) | candidacy cut-off; only rows with `file_size` **strictly greater** are eligible (FR-003) |

**Behaviour**
- Candidate = `int(file_size) > threshold`. Group candidates by `file_size` then
  confirm with `sha256` of `image_root / png_path`. First occurrence (sorted by
  the row-identity tuple) is master; the rest get `master_png_path = master.png_path`.
- `.wav` rows additionally require an exact `(time_end, freq_end)` match
  (issue #78): an audio pair's link target is its `.glc`, and two `.glc` files
  can window the same recording differently. Byte-identical `.wav` rows whose
  views differ are left non-redirected; a `.wav` row with a blank `time_end` or
  `freq_end` is never merged (its view cannot be confirmed) and logs a WARNING.
- Appends the `master_png_path` column if absent; otherwise repopulates it.
- Preserves the CSV file-level contract (utf-8-sig, QUOTE_MINIMAL, `\r\n`) and is
  idempotent (re-running over the same inputs → byte-identical CSV).

**Logging / exit**
- Logs per duplicate group: master path, redirect count, bytes reclaimed; logs a
  total reclaimed-bytes summary.
- A row whose asset file is missing/unhashable is left non-redirected with a
  WARNING (it is not a confirmed duplicate).
- Exit `0` on success (including "no duplicates found" — output is then
  equivalent to input plus an empty column).

---

## `rehydrate_dita.py` — reverse the deduplication (US2, FR-008/012)

Walks a generated DITA tree and restores any redirected lofar to a
self-contained, never-deduplicated form using only the DITA content.

```
python rehydrate_dita.py --dita dita/ [--gram gram-12] [--dry-run]
```

| Argument | Required | Default | Meaning |
|---|---|---|---|
| `--dita` | yes | — | root of the generated DITA tree to rehydrate |
| `--gram` | no | all | restrict to a single gram folder (e.g. `gram-12`) |
| `--dry-run` | no | off | report what would change without writing |

**Behaviour** — for each lofar `<section>` with
`<data name="original-asset-path" value="P">` (P is the original local path of
the **link target**: the image for an image lofar, the `.glc` for an audio
lofar — never the `.wav`):
1. Resolve the master file from the lofar's `<image>`/`<xref>` href (relative to
   the topic folder).
2. Recompute the local slug from `basename(P)` (`slugify_asset_name`) and copy
   the master link target into this gram's folder under that slug. For an audio
   pair (P is the `.glc`), also copy the master `.glc`'s adjacent `.wav` back
   under the `.wav`'s own slug (restored by adjacency).
3. Rewrite the href to the local copy and remove the `<data>` element.

A lofar without the `<data>` element is left untouched (idempotent; no-op on an
already-local lofar). Output (topic XML + restored assets) matches a
never-deduplicated export (SC-004). Serialisation matches the generator's
contract (LF, UTF-8 no BOM, deterministic).

**Logging / exit**
- Logs per rehydrated lofar: gram, restored local filename, source master.
- WARNING (not error) if a master file is missing on disk — the href is still
  re-localised so dropping the file in and re-running resolves it.
- Exit `0` on success; `--dry-run` writes nothing and exits `0`.
