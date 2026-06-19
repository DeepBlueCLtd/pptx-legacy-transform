# Quickstart: Frequency Bands

## Verify the corrected band end-to-end

1. **Run the canonical suite** (the air-gapped contract):

   ```bash
   python -m unittest discover tests/
   ```

   Expect green, including new cases for `bandcentre` parsing, the CSV column
   swap, the derived gram-config table, and the dedup view-key.

2. **Synthetic pipeline** (no real corpus needed):

   ```bash
   python scripts/mock_pptx.py --out-root mock_corpus/
   python scripts/extract_to_csv.py --input-root mock_corpus/ --out extracted.csv
   # confirm the CSV header has `bandwidth,bandcentre` (no `freq_end`)
   python scripts/generate_dita.py --csv extracted.csv --out dita/ --image-root mock_corpus/
   ```

3. **Inspect a gram-config table** in the generated DITA: for a gram whose
   `bandcentre != bandwidth/2`, confirm `freq-start` ≠ `0` and
   `freq-end = bandcentre + bandwidth/2`.

## Targeted checks

```bash
# GLC parser reads bandcentre
python -m unittest tests.test_glc_parser

# CSV column swap
python -m unittest tests.test_extract_to_csv

# gram-config freq derivation + dedup view-key
python -m unittest tests.test_generate_dita
python -m unittest tests.test_deduplicate_csv
```

## Acceptance spot-checks (from spec)

| bandwidth | bandcentre | freq-start | freq-end |
|-----------|------------|------------|----------|
| 400       | 200        | 0          | 400      |
| 400       | 600        | 400        | 800      |
| 100       | 250        | 200        | 300      |
| 401       | 200.5      | 0          | 401      |
