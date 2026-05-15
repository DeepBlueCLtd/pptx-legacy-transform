# Source-Corpus Reverse Spec

This document describes the shape of the real instructor PPTX corpus held
on the air-gapped network, distilled from an interview-driven exploration
of source material that cannot be copied into the repository. It exists
to drive `mock_pptx.py` — the synthetic mock generator — so the mock
corpus is structurally faithful to the originals without containing any
real operational data.

Companion artifact: [`readme.txt`](./readme.txt) holds the raw folder-tree
sketch this spec was distilled from.

## 1. Corpus scope

16 publications exist on the source disk. **The corpus to be migrated is
whatever PPTX files are present in the source folder at run time** — the
pipeline does not enforce a publication list. The SME prunes
unnecessary document sets manually before handoff.

The expected in-scope corpus, after pruning, is ~11–12 publications in
three families:

| Family | Count | Members |
|---|---|---|
| Week lessons | 4 | Week 1, Week 2, Week 3, Week 4 (`_Updated`) |
| Progress Tests | 5 | Test 1, Test 2 (`_Updated`), Test 3, Test 3 (`No FR`), Test 4 |
| Final Assessment | 1 | Final Assessment |
| Pub 10 reference | 1–2 | Pub10_Ed22B (`_Updated`); the plain "Pub 10" may be dropped — TBC |

`_Updated` variants reflect revision churn — same shape, substituted
content. `No FR` is a content variant of one Test (descriptors with the
`FR ` prefix are rewritten without it).

## 2. On-disk layout per publication

```text
<Publication Name>/
├── <Publication Name>.pptx
└── <Publication Name> Files/
    ├── Gram 1/
    │   ├── Analysis Sheet.docx        (or Analysis.png)
    │   ├── <Lofar 1 target>.glc
    │   ├── <Lofar 1 target>.png       (referenced from the GLC)
    │   └── ...
    ├── Gram 2/
    └── ...
```

**Pub10_Ed22B exception:** its `Files` folder is split into batches of 10
grams (`Pub 10_Ed 2_(1-10)`, `(11-20)`, …). Each slide in the PPTX still
holds ~15 grams, so slide batches and folder batches **are not aligned**
— hyperlinks span folders. This is filesystem hygiene only; the pipeline
follows hyperlinks and does not care about the batch boundaries.

## 3. PPTX slide structure

- 2–3 slides per publication for Weeks / Tests / Final; ~5 slides for the
  Pub 10 family.
- Each slide:
  - **Title bar** — title text + org logo. Title pattern is
    `"<Publication> — Page N of M"` (or similar slide-numbered form)
    across the slides of one deck.
  - **Grid of gram tiles** — typically 5×3, sometimes 5×2. Last slide
    often has a partial final row.
- The visual grid layout is **presentational only**. The DITA target
  page is a reflowable list of gram links, so the mock does not need to
  match the exact grid geometry — only the per-tile content and the
  hyperlinks.
- **No speaker notes.** Source decks have empty notes panes; the mock
  should leave them empty too.

## 4. Gram-tile structure

Each gram tile contains:

- A **rounded rectangle** with a descriptor in the form
  `"Gram N: <free-form instructor text>"`.
  - The descriptor is **split at the first colon**: left side
    (`"Gram N"`) is the student-visible label, right side is the
    instructor-visible detail.
  - Internal structure of the right side (commas, fields, ordering) is
    **not parsed** — it is passed through verbatim.
  - The rectangle is **hyperlinked (relative path)** to an Analysis
    Sheet in `Gram N\` — either `Analysis Sheet.docx` or `Analysis.png`.
- Beneath the rectangle, **1–4 text labels**, labelled `"Lofar 1"`
  through `"Lofar N"`. Each is **hyperlinked (relative path)** to a
  distinct `.glc` file in `Gram N\`.

Hyperlinks are encoded as standard PowerPoint hyperlinks
(`a:hlinkClick` relationships) with relative paths — `python-pptx`
handles them natively for both reading and writing.

Tile visual styling (fill colour, border, font) is **purely cosmetic**;
the pipeline carries no signal off it.

## 5. Linked-asset semantics

| Asset | Role | Mock fidelity |
|---|---|---|
| `.glc` | `GAPS_Lite_configuration` XML config; references a sibling `.png` or `.wav` | Must follow [contracts/glc-schema.md](../../specs/001-pptx-dita-migration/contracts/glc-schema.md) — the parser depends on it |
| `.png` / `.jpg` | Spectrogram image referenced from the GLC | Any small valid image; opaque to the pipeline |
| `.wav` | Audio recording referenced from the GLC (for audio-grams) | Any short valid WAV; opaque |
| `.docx` Analysis Sheet | Word table with structured rows (Bearing, Frequency, Identification, Notes, etc.) — used by instructors in teaching | Minimal valid `.docx`; opaque to the pipeline |
| `.png` Analysis Sheet | Image alternative to the `.docx` form | Any small valid image |

The pipeline **transforms** GLC content (into DITA topics) but treats
every other asset as an opaque artifact referenced by path.

**Orphan files** — files present in a `Gram N\` folder but not
hyperlinked from any slide — are silently dropped during extraction. The
mock therefore does not need to deliberately include orphans; the
spreadsheet is built top-down from PPTX hyperlinks.

## 6. Vocabulary and anonymization

Real corpus tokens (vessel types, codenames, frequency signatures) are
sensitive. The mock substitutes:

- **Vessel types & named vessels:** Star Trek and Star Wars classes and
  ship names (e.g. *Constitution-class*, *Galaxy-class*, *X-wing*,
  *Star Destroyer*, *Enterprise*, *Millennium Falcon*).
- **Codenames:** invented short tokens drawn from the same fictional
  universes (e.g. *Tantive*, *Defiant*, *Tatooine*).
- **Repetition:** the same vessel/codename should reappear in **2–6
  different publications** — mirrors how real training material reuses
  content week-on-week.
- **Categories & numeric tokens:** keep `Category N` (1–4) and any
  numeric metadata — generic enough to retain.
- **`FR` / `No FR`:** retained as opaque descriptor prefixes; the `No FR`
  Test variant has descriptors with the `FR ` prefix rewritten out, but
  otherwise matches the parent Test.
- **Org logo:** a generic placeholder (e.g. text-in-a-coloured-box) —
  obviously not a real organisation.

## 7. Per-family parameters for mock generation

| Family | Grams per publication | Slides | Files folder layout |
|---|---|---|---|
| Week lessons | ~35 | 3 (5×3 grid; last row partial) | Flat |
| Progress Tests | ~30 | 2–3 | Flat |
| Final Assessment | ~40 | 3 | Flat |
| Pub10_Ed22B | ~75 | ~5 (15 grams/slide) | Batched in folders of 10 |

Cross-cutting parameters:

- **Lofar count per gram:** uniform random 1–4.
- **Analysis Sheet type:** ~50/50 mix of `.docx` and `.png` per gram.
- **Lofar target media:** mostly PNG-referencing GLCs; a small minority
  WAV-referencing.
- **Gram numbering:** mostly sequential, with **occasional gaps** from
  simulated edits (e.g. Gram 1, 2, 4, 5 — Gram 3 removed during
  revision; surviving grams retain their original numbers).
- **Within Pub10_Ed22B**, the same gram number can recur as distinct
  folders disambiguated by zero-padding or codename suffix (e.g.
  `Gram_1`, `Gram_01`, `Gram_1 Gandalf`) — these are distinct grams that
  happen to share `1` in their names.
- **Filename style:** include suffix tokens (`_a`, `_b`, ` I`, ` ABC`,
  ` Loop 1/2/3`, codenames as suffixes) for realism. Strict per-gram
  folder containment is required to prevent filename collisions.
- **Cosmetic mess:** spaces vs underscores, mixed case, commas — fine to
  vary. Real typos like `.pnc` for `.png` are **not** required because
  the pipeline follows hyperlinks rather than discovering files by
  pattern.

## 8. Open questions / deferred decisions

- Whether the plain "Instructor Pub 10" stays in scope or is dropped in
  favour of Pub10_Ed22B alone — the SME will confirm against the live
  corpus.
- Exact slide-count rule for the Pub 10 family (assumed ~5 at 15 grams
  per slide; revisit if the real corpus differs).
- Whether `_Updated` publications differ from their unupdated siblings
  by content substitution only, or by gram-count change as well.
- Semantic meaning of `FR` (left opaque in the mock; treated as a
  free-text descriptor prefix only).
