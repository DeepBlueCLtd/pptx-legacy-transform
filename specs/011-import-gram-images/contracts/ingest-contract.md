# Contract: ingest_gram_images.py (feature 011)

The operator-facing contract for the new prep-time stage. The GLC element it
writes (`data_source/bitmap_crop_values/bottom_crop`) is documented in the
canonical `specs/001-pptx-dita-migration/contracts/glc-schema.md`; this stage
produces values conforming to that schema.

> **Superseded (issue #148 + duration-parsing removal):** `extract_to_csv.py`
> measures the gram's time period (`time_end`) from the imported image's pixel
> height, not from any GLC value. As a consequence this stage **no longer parses
> a duration from the incoming filename and no longer writes `bottom_crop`** —
> the incoming screenshot is named for the wav's own stem (no duration prefix)
> and the apply-mode GLC edit is a bare `<filename>` repoint. The image this
> stage copies in is what the extractor measures, so the imported screenshot's
> own pixel height is what reaches GramFrame. Sections below marked *(superseded)*
> describe the retired duration/crop behaviour.

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
4. **Image stem**: the whole filename stem is the match stem — there is **no
   duration token to strip** (the author names the screenshot for the wav's own
   stem; `time_end` is image-derived, issue #148). Eligible extensions: `.jpg`
   `.jpeg` `.png`, case-insensitive; other files ignored (debug log only).
   *(superseded: the old contract split a leading `^(\d+)m(?:(\d{1,2})s)?$`
   duration token off the stem and reported `unparseable-duration` on a miss;
   both the split and that outcome class are gone.)*
5. **Image → asset**: fold every stem (incoming and referenced) through
   `match_key` = casefold + collapse-whitespace + strip-spaces-around-hyphens,
   then compare against stems of assets referenced by the gram folder's `.glc`
   files (via `parse_glc`), extension-blind:
   - the key hits exactly one wav-backed GLC's wav (uniquely among the folder's
     incoming images) → **match** (all GLCs sharing that wav are part of it);
   - two+ incoming images fold onto one key → `ambiguous`, none applied;
   - one image folds onto ≥2 *distinct* wav basenames → `ambiguous`, none
     applied;
   - the key hits an image-backed GLC's stem → `already-converted`;
   - otherwise → `unmatched-image` (folder's wav stems echoed).
   Unreadable GLCs → `glc-unreadable` and are excluded from matching.
6. `match_key` folds two systematic drifts so the operator need not hand-fix
   them: **case** (an incoming `WAV 2` ↔ source `Wav 2.wav`) and **hyphen
   spacing** (an incoming `0 - 1000 Hz` ↔ source `0-1000 Hz.wav`, either
   direction). Everything else — different tokens, a missing digit — stays
   exact, so real mistakes are reported, never silently absorbed. The fold
   applies at every folder level too (doc and gram names, case only).

## Apply semantics (normative)

Per verified match, in this order, per gram folder in sorted path order:

1. Copy the incoming image to `<gram-folder>/<wav-stem><ext>` (`shutil.copyfile`
   semantics: bytes only, no metadata; overwrite existing). The basename takes
   the **wav's own casing and spacing** (from the matched GLC's referenced wav),
   not the incoming screenshot's — so an incoming `WAV 1.jpg` lands as
   `Wav 1.jpg` beside a source `Wav 1.wav`, and an incoming `0 - 1000 Hz.jpg`
   lands as `0-1000 Hz.jpg` beside a source `0-1000 Hz.wav`, keeping the folder
   internally consistent.
2. For each matched GLC (sorted): a single-write targeted text edit that
   replaces the first `<filename>` inner text with the copied basename.
   **Nothing else in the GLC is touched** — no `<bitmap_crop_values>` /
   `<bottom_crop>` is inserted (the time period is image-derived, issue #148).
   A missing `<filename>` anchor is a per-file error: skip, count, write
   nothing. *(superseded: the old contract also inserted a
   `<bitmap_crop_values><bottom_crop>{seconds}</bottom_crop></bitmap_crop_values>`
   block and skipped an already-cropped wav GLC whole as `glc-already-cropped`;
   both behaviours, and that outcome class, are gone.)*
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

== UNMATCHED IMAGES (n) ==
<doc>/<gram>/<file>  ->  stem "<stem>"; folder wavs: <stem1>, <stem2>

== AMBIGUOUS (n) ==
<doc>/<gram>  ->  stem "<stem>" claimed by <file1>, <file2>; none applied

== TRENDS ==
token-drift 'WAVE' -> 'WAV' x 14
whitespace-only x 3

== SUMMARY ==
matched|applied N, already-converted N, unmatched-doc N, ... glcs_rewritten N, images_copied N
```

Sections with zero entries are omitted except SUMMARY. Entries sorted by
path; body contains no timestamps (byte-stable across identical re-runs).

## Test surface (stdlib unittest, synthetic tempfile trees)

- filename parsing: whole stem kept intact (`0 - 1322 Hz`, `WAV 2`), extension
  gate + case, `.wav`/`.txt` rejected
- match key: case fold, hyphen-spacing fold both directions, genuine token/digit
  drift stays distinct
- container resolution: 1 / 0 / 2 / ≥8 (flat) subdirectories
- matching: exact hit, case drift, hyphen-spacing drift both directions, token
  drift labelling, nearest-candidate content, wav-vs-image asset classification
- apply: copy bytes + overwrite; GLC filename rewrite only (no crop block); copy
  named in wav's casing *and* spacing; two GLCs sharing one wav; wav untouched
- demon: leading / numbered (`Demon2-`) / duration-prefixed tokens recognised,
  `Demonstrate` rejected; marker seeded, band baked, no crop
- guards: verify writes nothing in either tree; apply re-run is a no-op; two
  images folding onto one wav → ambiguous; one image folding onto two wavs →
  ambiguous; unreadable GLC isolated; report determinism (two runs, identical
  bytes)
