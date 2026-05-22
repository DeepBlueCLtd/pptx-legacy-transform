# Quickstart: Per-Gram Audience Tags via CSV `audience` Column

This walkthrough takes a fresh checkout (or a re-run after edits) and
produces all three HTML editions from the existing DITA source, end
to end. It is the same path a maintainer follows to verify the
feature after any change — it exercises every Success Criterion in
the spec.

## 0. Prerequisites

- Python 3.9 or later — no new third-party packages added by this
  feature.
- DITA-OT 4.x installed locally with a Java runtime on `PATH`.
  Acquisition/install path is documented in the project README
  (carried over from feature 001).
- The DITA source tree at `dita/` is up to date with the latest
  generator run. If unsure: re-run the generator (§3).

## 1. Verify the environment

```bash
python --version                   # expect 3.9+
python -m unittest discover tests/ # all green before any edits
```

The test suite includes the new assertions from this feature. All
tests should pass before you start making changes, and again after
each change.

## 2. Regenerate the mock PPTX corpus (optional)

If you want to start from the mock-corpus baseline rather than the
committed real corpus:

```bash
python mock_pptx.py --out mock_pptx_data --seed 0
```

After this feature ships, the mock corpus:

- Does NOT contain a `Instructor Progress Test 3 Grams No FR/`
  publication. The `mock_pptx_data/` directory should have one fewer
  top-level entry than before (10 publications instead of 11).
- Includes a Week 3 PPTX whose second grams slide has the last two
  items tagged `[-own]` and `[-other]` respectively in their
  descriptor text.

## 3. Re-extract the CSV

```bash
python extract_to_csv.py --source mock_pptx_data --out source.csv
```

Verify the new `audience` column landed on every row:

```bash
head -1 source.csv | tr ',' '\n' | nl
# Expect line 16: audience
```

Verify the Week 3 tagged grams carry the values:

```bash
awk -F',' '$1 == "main" && $2 ~ /Week 3/ { print $3, $4, $NF }' source.csv \
  | tail -5
# Expect the last two grams on slide 2 to show -own and -other in
# the final column (vessel_name no longer carries the bracket suffix).
```

## 4. Regenerate the DITA source tree

```bash
python generate_dita.py --csv source.csv --out dita
```

Verify the topicref attribute landed:

```bash
grep -E 'topicref href=.*progress-test-3.*audience' dita/progress-test-3.ditamap
# Expect at least one topicref with audience="-own" and one with
# audience="-other".
```

Verify the new DITAVAL profiles exist:

```bash
ls -1 dita/*.ditaval
# Expect: dita/student-other.ditaval
#         dita/student-own.ditaval
#         dita/trainee.ditaval
```

Verify the generator logged the per-publication tag counts:

```bash
python generate_dita.py --csv source.csv --out dita 2>&1 \
  | grep -E 'audience .* applied'
# Expect at least one INFO line naming the publication(s) where
# audience attributes were emitted, and the count.
```

## 5. Publish to HTML

```bash
python publish_html.py --dita dita --html html
```

Verify the three-edition layout:

```bash
ls -1 html/
# Expect: index.html
#         instructor/
#         student-other/
#         student-own/
# (and NOT: student/)
```

Verify the shared landing page lists three editions:

```bash
grep -E 'href="(instructor|student-own|student-other)' html/index.html
# Expect three matching <a href="…/index.html"> lines.
```

## 6. Verify Week 3 substitution (SC-001)

Count the grams in each student edition's Week 3 test index page:

```bash
grep -cE '<a [^>]*href="gram-' html/student-own/progress-test-3/index.html
grep -cE '<a [^>]*href="gram-' html/student-other/progress-test-3/index.html
# Expect both counts equal.

grep -cE '<a [^>]*href="gram-' html/instructor/progress-test-3/index.html
# Expect this count = each student-* count + 1.
# (instructor sees both tagged grams; each student-* sees one of them.)
```

Identify which gram each student edition omits:

```bash
diff <(grep -oE 'href="gram-[0-9]+' html/student-own/progress-test-3/index.html | sort -u) \
     <(grep -oE 'href="gram-[0-9]+' html/student-other/progress-test-3/index.html | sort -u)
# Expect exactly two diff lines: one gram present in student-own
# only (it's tagged -other in CSV), one gram present in student-other
# only (it's tagged -own in CSV).
```

## 7. Verify the No-FR publication is gone (SC-003)

```bash
grep -ric 'no.fr' html/ dita/ source.csv mock_pptx.py 2>&1 \
  | grep -v ':0$' | head
# Expect no matching lines (every searched location returns 0).

grep -ric 'no fr' html/ dita/ source.csv mock_pptx.py 2>&1 \
  | grep -v ':0$' | head
# Expect no matching lines.
```

## 8. Verify idempotency (SC-004)

```bash
# Stash the first publish output.
mv html html-run1

# Run the publish step a second time from the same DITA source.
python publish_html.py --dita dita --html html

# Compare the two trees.
diff -r html-run1/ html/
# Expect no output (byte-identical trees in all three editions).

# Cleanup.
rm -rf html-run1
```

## 9. Verify the per-gram consistency check (SC-007)

Manually break the CSV by setting two rows of one gram to different
`audience` values, then re-run the generator:

```bash
cp source.csv source.csv.bak

# Pick a gram with two rows (analysis + at least one glc) and
# perturb just one of them. Example: progress-test-3 gram 10.
python - <<'PY'
import csv
rows = list(csv.DictReader(open("source.csv", encoding="utf-8-sig")))
# Set the analysis row's audience differently from the glc rows.
for r in rows:
    if r["publication"] == "progress-test-3" and r["gram_id"] == "10":
        if r["topic_type"] == "analysis":
            r["audience"] = "-own"
        else:
            r["audience"] = "-other"
import sys
w = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys())
w.writeheader(); w.writerows(rows)
PY > source.csv.broken
mv source.csv.broken source.csv

# Re-run and confirm the named exception fires.
python generate_dita.py --csv source.csv --out dita 2>&1 | head
# Expect an error message naming "progress-test-3", "gram_id=10",
# and listing the two conflicting audience values.

# Restore.
mv source.csv.bak source.csv
```

## 10. Author hand-edit walkthrough (User Story 2)

Pick an arbitrary gram with an empty `audience` cell. Edit the
cell to `-other` for *every* row of that gram. Re-run §4 and §5,
then verify:

- The gram appears in `html/instructor/<publication>/index.html`.
- The gram appears in `html/student-own/<publication>/index.html`.
- The gram does NOT appear in
  `html/student-other/<publication>/index.html`.

Restore the CSV when finished.

---

## Success Criterion → step mapping

| SC | Verified by step |
|---|---|
| SC-001 | §6 |
| SC-002 | §10 |
| SC-003 | §7 |
| SC-004 | §8 |
| SC-005 | §1 (full test run) |
| SC-006 | §5 + manual click-through of `html/index.html` |
| SC-007 | §9 |
