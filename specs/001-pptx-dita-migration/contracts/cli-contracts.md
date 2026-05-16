# CLI Contracts

This file is the authoritative reference for every script's command-line
interface, exit codes, and on-disk side effects.

## Conventions (R15)

- Long-form GNU flags only.
- Paths are accepted as strings, converted immediately to `pathlib.Path`.
- Required flags use `argparse`'s `required=True`.
- Exit codes:
  - `0` — success
  - `1` — any unhandled error or stage failure
  - `2` — `argparse` usage error (default)

---

## `mock_pptx.py`

**Purpose** (Story 4): Generate a synthetic instructor PPTX.

```text
python mock_pptx.py --out PATH
```

| Flag | Required | Type | Description |
|---|---|---|---|
| `--out` | yes | path | Output file path; will be overwritten if it exists |

**Side effects**: Writes one `.pptx` file at `--out`.

**Exit codes**: `0` on success; `1` if writing fails.

---

## `introspect_pptx.py`

**Purpose** (Story 3): Produce a structural report for a PPTX.

```text
python introspect_pptx.py --input PATH [--out PATH] [--slides N[,M[,...]]]
```

| Flag | Required | Type | Description |
|---|---|---|---|
| `--input` | yes | path | Input PPTX file |
| `--out` | no | path | Report output (UTF-8). If omitted, report goes to stdout |
| `--slides` | no | comma list | Restrict per-slide section to these slide numbers |

**Side effects**: Writes the report to `--out` (or stdout). Always
writes a small log file `introspect.log` (UTF-8) in the current
working directory.

**Exit codes**: `0` on success; `1` if the PPTX cannot be opened or
parsed.

**Report shape** (FR-007/FR-008):

1. *Section 1 — Summary*: filename, total slide count, hyperlink target
   extensions with counts, shape-level vs text-run hyperlink counts,
   slides flagged as deviating from expected layout.
2. *Section 2 — Per-slide*: per-slide title, total shape count; per-shape
   index, name, type, position in inches (2dp), text (truncated to 80
   chars), shape hyperlink (if any), per-run text + hyperlink.
3. *Section 3 — Hyperlink targets*: deduplicated, grouped by file
   extension; each entry shows target path, hyperlink type, slide
   number, shape name.

---

## `extract_to_csv.py`

**Purpose** (Story 2): Walk an input root, parse PPTXs and GLC files,
write the intermediate CSV.

```text
python extract_to_csv.py --input-root PATH --out PATH
                         [--test-pattern STR]
```

| Flag | Required | Type | Description |
|---|---|---|---|
| `--input-root` | yes | path | Root directory containing PPTX folders |
| `--out` | yes | path | Output CSV path; overwritten |
| `--test-pattern` | no | string | Substring (case-insensitive) identifying progress-test PPTXs (default: `progress_test`) |

**Side effects**:

- Writes a CSV at `--out` with the column structure in
  `data-model.md` §2.
- Writes `extract.log` next to the CSV (mode `"w"`, UTF-8).
- Stage 2's shape-grouping logic is currently a stub; the script will
  raise `NotImplementedError` from `extract_grams_from_slide()` if it
  reaches a content slide. All other infrastructure runs to completion.

**Exit codes**: `0` on success; `1` on unrecoverable failure (e.g.
input root missing). Per-PPTX or per-GLC failures are recorded as
warnings on the affected CSV rows and do not change the exit code.

**Logging contract** (FR-014):

- INFO: each PPTX processed, each GLC resolved, each ditamap (n/a here),
  end-of-run summary.
- WARNING: missing GLC, malformed GLC, unexpected shape count, missing
  vessel name.
- ERROR: PPTX cannot be opened or parsed (after which the script aborts
  with exit 1).

End-of-run summary (stdout + log): total PPTXs, total rows written,
total warnings, distinct warning types with counts.

---

## `generate_dita.py`

**Purpose** (Story 1): Consume the signed-off CSV and write DITA
topics + ditamaps + manifest.

```text
python generate_dita.py --csv PATH --out PATH --image-root PATH
                        [--clean]
```

| Flag | Required | Type | Description |
|---|---|---|---|
| `--csv` | yes | path | Reviewed CSV file |
| `--out` | yes | path | Output directory; created if missing |
| `--image-root` | yes | path | Root used to resolve `png_path` columns |
| `--clean` | no | flag | If set, deletes the existing output directory tree before writing |

**Side effects**:

- Writes one DITA topic per non-skipped row under
  `--out/<publication>/[<chapter-slug>/]<topic_filename>`.
- Writes one ditamap per publication at the `--out/` root
  (e.g. `--out/main.ditamap`, `--out/progress-test-1.ditamap`), each
  alongside its similarly-named content folder.
- Writes `--out/manifest.txt` listing every file produced.
- Writes `--out/skipped.txt` listing every row skipped (only if there
  is at least one).
- Writes `generate.log` (mode `"w"`, UTF-8) in the current working
  directory.

**Exit codes**: `0` on success (even if some rows are skipped); `1` on
any unhandled error (e.g. CSV missing, malformed CSV, write failure).

**Idempotency contract** (FR-013, R9, SC-004): With `--clean` *not*
set, running twice with the same CSV produces byte-identical output
files for every file the second run also produces. With `--clean` set,
the output tree is deleted before writing on each run.

**Logging contract** (FR-014):

- INFO: each topic written, each ditamap written, manifest written,
  skipped count, end-of-run summary (total topics, total ditamaps,
  total skipped, total errors).
- WARNING: image not found at the resolved `png_path`; row uses the
  empty time/freq values.
- ERROR: row skipped (GLC inner asset missing or unrecognised
  extension); CSV missing or malformed.

---

## `run_pipeline.bat`

**Purpose** (Story 6): Windows orchestrator for Stages 2 + 4 with a
manual review pause.

```text
run_pipeline.bat <input-root>
```

| Position | Required | Type | Description |
|---|---|---|---|
| `%1` | yes | path | Content root (forwarded to `extract_to_csv.py --input-root` and `generate_dita.py --image-root`) |

**Side effects**: Runs `extract_to_csv.py`, pauses for the technical
author to inspect `extracted.csv`, then runs `generate_dita.py`.

**Exit codes**: `0` on success; `1` if either Python stage exits
non-zero. `errorlevel 1` is the contract that downstream automation
relies on.

**Operator UX**: Stage banners between runs (`=== PPTX to DITA
Migration Pipeline ===`, `[Stage 2] ...`, `[Stage 4] ...`); a `pause >
nul` between extraction and generation so the operator can `start
extracted.csv` in another window before continuing.

---

## Test runner (informational)

```text
python -m unittest discover tests/
```

Standard `unittest` discovery, no flags. Exit `0` on green, `1` on
any test failure or error.
