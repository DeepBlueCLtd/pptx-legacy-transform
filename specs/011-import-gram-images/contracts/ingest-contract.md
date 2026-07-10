# Contract: ingest_gram_images.py (feature 011)

The operator-facing contract for the new prep-time stage. The GLC element it
writes (`data_source/bitmap_crop_values/bottom_crop`) is *already specified* in
the canonical `specs/001-pptx-dita-migration/contracts/glc-schema.md` (parsed
as `time_end`); this stage produces values conforming to that schema, so the
canonical contract needs no change.

## CLI

```text
python scripts/ingest_gram_images.py --incoming-root <dir> --source-root <dir> [--apply]
```

| Flag | Required | Meaning |
|---|---|---|
| `--incoming-root` | yes | root of the author's delivery tree; read-only in every mode |
| `--source-root` | yes | root of the source corpus (`source\` on target); mutated only with `--apply` |
| `--apply` | no | perform the conversion for verified matches; without it the run is verify/report-only |

Exit code: `0` on any completed run (mismatches are report content, not
errors); `1` only for unusable invocations (missing/non-directory roots).
Non-interactive; safe to re-run at any time in either mode.

Wrapper: root-level `ingest.py` template (Config block holds the two roots and
the commented-out `--apply` toggle), REPL-driven via
`exec(open(r"ingest.py").read())` after the session chdir, exactly like the
other wrappers.

## Outputs

| Artefact | Location | Mode | Notes |
|---|---|---|---|
| `ingest_report.txt` | cwd | both | deterministic body (no timestamps); sections per outcome class; sorted entries; trend aggregation; tally footer |
| `ingest.log` | cwd | both | DEBUG dual-log per pipeline convention |
| image copies | source gram folders | apply | `<wav-stem><incoming ext>`, content-only copy, unconditional overwrite |
| GLC edits | source gram folders | apply | see "GLC rewrite delta" |

## Matching rules (normative)

1. **Doc**: incoming `<doc>` dir name must equal a `--source-root` child dir
   name **case-insensitively**. Miss → `unmatched-doc` (+ ≤3 nearest
   candidates, drift label).
2. **Container**: resolve the tier that holds the gram folders. If the matched
   source doc dir has exactly one subdirectory (any name), that is the
   container. If it has **≥ 8** subdirectories, it is a *flat* publication
   (one exists) whose gram folders sit directly under the doc dir — the doc dir
   itself is the container. Any other count (0, or 2–7) →
   `structurally-ambiguous-doc`; doc skipped.
3. **Gram**: incoming `<gram>` dir name must equal a container child dir name
   **case-insensitively**. Miss → `unmatched-gram` (+ candidates, drift label).
4. **Image filename split**: leading token = chars before the first separator,
   which is a space **or** an underscore (`10m_0 - 600 Hz`,
   `7m20s_0 - 441 Hz`, `11m Wav 1`); token must match
   `^(\d+)m(?:(\d{1,2})s)?$` (case-insensitive); `seconds = m*60 + s(0)`.
   Stem = rest after that separator, stripped, non-empty. Violation →
   `unparseable-duration` (raw token echoed). Eligible extensions: `.jpg`
   `.jpeg` `.png`, case-insensitive; other files ignored (debug log only).
5. **Image → asset**: compare the stem against stems of assets referenced by
   the gram folder's `.glc` files (via `parse_glc`), extension-blind and
   **case-insensitive**:
   - equals a wav-backed GLC's wav stem, uniquely among the folder's incoming
     images → **match** (all GLCs sharing that wav stem are part of it);
   - two+ incoming images resolve to one wav stem (case-folded) → `ambiguous`,
     none applied;
   - equals an image-backed GLC's stem → `already-converted`;
   - otherwise → `unmatched-image` (folder's wav stems echoed).
   Unreadable GLCs → `glc-unreadable` and are excluded from matching.
6. Matching folds **case** (folders and stems) so the hand-typed incoming
   names need not match `source\`'s casing; **whitespace and token content are
   still exact**, so missing spaces and changed words are reported, never
   silently absorbed.

## Apply semantics (normative)

Per verified match, in this order, per gram folder in sorted path order:

1. Copy the incoming image to `<gram-folder>/<wav-stem><ext>` (`shutil.copyfile`
   semantics: bytes only, no metadata; overwrite existing). The basename takes
   the **wav's own casing** (from the matched GLC's referenced wav), not the
   incoming screenshot's — so an incoming `7m_WAV 1.jpg` lands as `Wav 1.jpg`
   beside a source `Wav 1.wav`, keeping the folder internally consistent.
2. For each matched GLC (sorted): a single-write targeted text edit that
   (a) replaces the first `<filename>` inner text with the copied basename,
   and (b) inserts, immediately after `</filename>`, indented to match the
   file:

   ```xml
   <bitmap_crop_values>
     <bottom_crop>{seconds}</bottom_crop>
   </bitmap_crop_values>
   ```

   A wav-backed GLC that already contains `<bitmap_crop_values>` is skipped
   whole (`glc-already-cropped`) — never overwritten, never double-inserted.
   A missing edit anchor is a per-file error: skip, count, write nothing.
3. The referenced `.wav` is left in place, byte-untouched — **deliberate
   divergence** from `relink_glc_to_image.py`'s `.wav.bak` rename, documented
   in both scripts.

Idempotency: a rewritten GLC references an image, so a re-run classifies the
gram `already-converted` and changes nothing.

## Report format

```text
INGEST REPORT
incoming: <incoming-root>
source:   <source-root>
mode:     verify | apply

== UNMATCHED DOCUMENTS (n) ==
<incoming doc>  ->  no exact match; nearest: "<cand>" [case-only], "<cand2>" ...

== STRUCTURALLY AMBIGUOUS DOCUMENTS (n) ==
<source doc>  ->  0|k subdirectories (expected exactly 1); skipped

== UNMATCHED GRAM FOLDERS (n) ==
<doc>/<gram>  ->  nearest: "<cand>" [token-drift('WAVE' -> 'WAV')]

== UNPARSEABLE DURATIONS (n) ==
<doc>/<gram>/<file>  ->  token "<raw>"

== UNMATCHED IMAGES (n) ==
<doc>/<gram>/<file>  ->  stem "<stem>"; folder wavs: <stem1>, <stem2>

== AMBIGUOUS (n) ==
<doc>/<gram>: wav "<stem>" claimed by <file1>, <file2>; none applied

== TRENDS ==
token-drift 'WAVE' -> 'WAV' x 14
whitespace-only x 3

== SUMMARY ==
matched|applied N, already-converted N, unmatched-doc N, ... glcs_rewritten N, images_copied N
```

Sections with zero entries are omitted except SUMMARY. Entries sorted by
path; body contains no timestamps (byte-stable across identical re-runs).

## Test surface (stdlib unittest, synthetic tempfile trees)

- duration parsing: `21m`, `5m26s`, `0m`, `10M`, rejects `326`, `5:26`,
  `5m26s.jpg` (empty stem), `5m261s`
- container resolution: 1 / 0 / 2 subdirectories
- matching: exact hit, case drift, whitespace drift, token drift labelling,
  nearest-candidate content, wav-vs-image referenced asset classification
- apply: copy bytes + overwrite; GLC filename rewrite; crop insertion position,
  indentation and value; two GLCs sharing one wav; wav untouched
- guards: verify writes nothing in either tree; apply re-run is a no-op;
  ambiguous applies nothing; already-cropped GLC untouched; unreadable GLC
  isolated; report determinism (two runs, identical bytes)
