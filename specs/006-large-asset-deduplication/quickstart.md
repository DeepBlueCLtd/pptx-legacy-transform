# Quickstart: Large Asset Deduplication

End-to-end walkthrough that verifies the success criteria (SC-001…SC-006). Run
from the repository root. Assumes a signed-off CSV and an `--image-root` asset
tree (the same inputs `generate_dita.py` already takes).

## 0. Baseline (inert by default — SC-005)

Export with an **unprocessed** CSV (no `master_png_path` column) and keep the
output as the reference:

```bash
python generate_dita.py --csv source.csv --out dita-baseline --image-root source/ --clean
```

Every asset is copied into its own gram folder, exactly as today.

## 1. Post-process the CSV to nominate masters (US3 — FR-002/003)

```bash
python deduplicate_csv.py \
    --csv source.csv \
    --image-root source/ \
    --out source.dedup.csv
```

Expect log lines naming each duplicate group, its master, the redirect count,
and total bytes reclaimed. Only assets **strictly over 10 MiB** that genuinely
duplicate another row are redirected; unique or small assets are untouched.

**Check**: open `source.dedup.csv` — the master row of each group has an empty
`master_png_path`; the duplicates carry the master's `png_path`.

## 2. Export the deduplicated set (US1 — FR-004/005/009)

```bash
python generate_dita.py --csv source.dedup.csv --out dita-dedup --image-root source/ --clean
```

**Verify SC-001 (one physical copy)**: for a `.wav` duplicated N times, the file
exists in exactly **one** gram folder under `dita-dedup/`:

```bash
find dita-dedup -name '*.wav' | sort        # the deduplicated asset appears once
du -sh dita-baseline dita-dedup             # dita-dedup is dramatically smaller
```

**Verify FR-004/009 (redirect + pairing)**: a redirected audio lofar's `<xref>`
points at the master `.glc` via a `../` path, and neither the `.glc` nor the
`.wav` was copied into the redirected gram:

```bash
grep -R 'href="\.\./' dita-dedup --include='*.dita' | grep '\.glc'
```

## 3. Confirm provenance is recorded (US2 — FR-006/007)

Every redirected lofar carries the flag-and-anchor `<data>` element, and nothing
else distinguishes it:

```bash
grep -R 'data name="original-asset-path"' dita-dedup --include='*.dita'
```

**Verify SC-003**: the count of these elements equals the number of redirected
rows in `source.dedup.csv`; a reviewer can list every deduplicated gram from
this grep alone, with no separate index.

## 4. Publish HTML and confirm a single shared reference (FR-011)

```bash
python publish_html.py …            # existing invocation
```

**Verify**: the deduplicated asset is referenced by every usage but emitted once
in the HTML output (asserted by the Jest test in `tests/web/`). The `<data>`
element does **not** appear in the rendered trainee HTML (FR-006).

## 5. Rehydrate a gram back to self-contained (US2 — FR-012, SC-004)

```bash
python rehydrate_dita.py --dita dita-dedup --gram gram-12
```

**Verify SC-004**: the restored `gram-12` topic and its assets now match the
baseline:

```bash
diff -r dita-baseline/main/.../gram-12 dita-dedup/main/.../gram-12    # identical
```

The master (and, for a pair, its adjacent `.wav`) is copied back under the local
slug, the href is re-localised, and the `<data>` element is gone — the topic is
indistinguishable from one that was never deduplicated. Running `rehydrate_dita.py`
again is a no-op.

## 6. Idempotency (SC-006 / FR-013)

```bash
python generate_dita.py --csv source.dedup.csv --out dita-dedup2 --image-root source/ --clean
diff -r dita-dedup dita-dedup2        # byte-identical
python deduplicate_csv.py --csv source.csv --image-root source/ --out source.dedup2.csv
diff source.dedup.csv source.dedup2.csv   # byte-identical
```

## Success-criteria coverage

| Step | Criteria verified |
|---|---|
| 0, 2 | SC-005 (inert baseline), SC-001 (one copy, smaller set) |
| 2 | FR-004, FR-005, FR-009 |
| 3 | SC-003, FR-006, FR-007 |
| 4 | FR-011, FR-006 (HTML suppression) |
| 5 | SC-004, FR-012, FR-008 |
| 6 | SC-006, FR-013 |
