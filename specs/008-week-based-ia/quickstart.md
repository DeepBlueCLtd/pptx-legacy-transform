# Quickstart — Week-Based IA (verifies SC-001…SC-006)

End-to-end walkthrough on the synthetic corpus. Run from the repo root.

## 1. Extract — weeks become bare integers (SC-001)

```bash
python extract_to_csv.py --input-root source --out extracted.csv
```

Open `extracted.csv` in Excel:

- Every row whose source `chapter` is `Instructor Week N Grams` carries
  `target_chapter = N`.
- Pub10 rows (`Instructor Pub10_Ed22B_Updated`) carry an **empty**
  `target_chapter` — the analyst fills in the week per the analyst's table.
- `target_doc` is empty for all `main` rows (no per-document sub-folder).

## 2. Author review — assign Pub10 weeks

In `target_chapter`, enter `1`…`4` for each Pub10 gram per the agreed table.
Leave the `chapter` and other identity columns untouched.

## 3. Renumber — resolve within-week collisions (SC-002, SC-003)

```bash
python deduplicate_csv.py --csv extracted.csv --image-root source --out signed-off.csv
```

`dedup.log` shows lines like:

```
gram renumbered: chapter=2 gram_id=5 → 11
Renumber summary: grams_renumbered=1
```

The native Week 2 / Gram 5 keeps `5`; the Pub10 gram reassigned to Week 2 that
also claimed `5` gets `target_gram_id = 11` (one past the week's maximum). The
deck whose source `chapter` sorts first keeps its number (SC-003).

## 4. Generate — neat, unique week folders (SC-002, SC-006)

```bash
python generate_dita.py --csv signed-off.csv --out dita --image-root source
```

- `main` contains only `week-1/` … `week-4/` (SC-001).
- Each gram is a `gram-NN/` folder with a unique number; **no** `gram-05a/`
  letter-suffixed folders (SC-002).
- `main.ditamap` has one `<topichead><navtitle>Week N</navtitle>` per week.

### Fail-fast check (SC-006)

Remove the `target_gram_id` value from the renumbered Pub10 gram (re-introducing
the collision) and re-run `generate_dita.py`: it aborts before writing any topic
with an error per colliding slot that names the grams and says to renumber.

## 5. Inert-by-default check (SC-004)

A CSV with no `target_gram_id` column (e.g. a feature-006-era CSV) generates
exactly as before — numbering straight from `gram_id`.

## 6. Idempotency check (SC-005)

```bash
python deduplicate_csv.py --csv signed-off.csv --image-root source --out signed-off-2.csv
diff signed-off.csv signed-off-2.csv   # no differences
```
