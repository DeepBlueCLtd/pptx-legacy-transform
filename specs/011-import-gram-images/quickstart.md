# Quickstart: Import Author Gram Images

## Verify the stage end-to-end (dev host)

1. **Run the canonical suite** (the air-gapped contract):

   ```bash
   python -m unittest discover tests/
   ```

   Expect green, including the new `tests.test_ingest_gram_images` cases.

2. **Build a tiny synthetic delivery** against the in-repo `source/` corpus
   (pick any gram folder that has a wav-backed `.glc`, e.g. under
   `source/Instructor Week 4 Grams_Updated/`):

   ```bash
   mkdir -p "incoming/Instructor Week 4 Grams_Updated/Gram 8"
   # any small image will do; the name encodes duration + the wav's stem
   cp tests/fixtures/<some>.png \
      "incoming/Instructor Week 4 Grams_Updated/Gram 8/5m26s <wav-stem>.png"
   ```

3. **Verify pass** (default; nothing is modified):

   ```bash
   python scripts/ingest_gram_images.py --incoming-root incoming/ --source-root source/
   cat ingest_report.txt
   ```

   Expect the pair under `matched` in the summary (or a reported mismatch if
   the stem/folder was typed wrong — fix the *incoming* side and re-run).
   Confirm `git status` shows no change under `source/`.

4. **Apply pass**:

   ```bash
   python scripts/ingest_gram_images.py --incoming-root incoming/ --source-root source/ --apply
   git diff --stat source/
   ```

   Expect: `<wav-stem>.png` copied beside the `.glc`; the `.glc` diff shows
   only the `<filename>` change plus the inserted
   `<bitmap_crop_values><bottom_crop>326</bottom_crop></bitmap_crop_values>`;
   the `.wav` untouched and still present.

5. **Idempotency**: run the apply command again — the summary reports the gram
   as `already-converted` and `git status` shows nothing new.

6. **Downstream**: re-run extraction and generation; the converted gram's CSV
   row carries `time_end=326` and the generated topic embeds the image inline
   (no `.glc`/`.wav` link treatment):

   ```bash
   python scripts/extract_to_csv.py --input-root source/ --out extracted.csv
   python scripts/generate_dita.py --csv extracted.csv --out dita/ --image-root source/
   ```

## Targeted checks

```bash
python -m unittest tests.test_ingest_gram_images
```

## On the air-gapped target (operator shape)

```python
import os
os.chdir(r"C:\dev\aaac")
exec(open(r"ingest.py").read())      # verify: writes ingest_report.txt + ingest.log
# review/fix incoming names, re-run until clean, then set APPLY in ingest.py's
# Config block (or uncomment "--apply") and:
exec(open(r"ingest.py").read())      # apply
exec(open(r"extract.py").read())     # fresh extract picks up time_end
```
