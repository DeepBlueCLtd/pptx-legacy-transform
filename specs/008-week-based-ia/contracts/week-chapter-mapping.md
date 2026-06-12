# Contract — Week-token extraction and chapter expansion

## Extraction: deck title → `target_chapter` (`main` only)

For a `main` publication deck, extraction sets `target_chapter` from the source
chapter title (the deck's parent folder name):

```
WEEK_TOKEN = /\bweek\s*0*(\d+)\b/i        # "Week 1", "Week 01", "Week1" → "1"
target_chapter = WEEK_TOKEN.search(chapter_title).group(1)  if matched
               = ""                                          otherwise
```

- A match writes the bare integer (leading zeros stripped) — e.g.
  `Instructor Week 3 Grams` → `target_chapter = "3"`.
- No match (e.g. `Instructor Pub10_Ed22B_Updated`) leaves `target_chapter`
  empty for an analyst to fill in.
- The immutable `chapter` column always keeps the full source title.
- `target_doc` is set to `""` for `main` (no per-document folder segment).

Non-`main` publications (progress tests, final assessment) are unchanged.

## Generation: effective chapter → navtitle + slug

`_normalise_chapter(raw)` returns `(audience_prefix, display, slug)`:

| Input (effective chapter) | audience_prefix | display | slug |
|---|---|---|---|
| `"1"` (bare integer) | `None` | `Week 1` | `week-1` |
| `"4"` | `None` | `Week 4` | `week-4` |
| `"Instructor Week 1 Grams"` | `"Instructor "` | `Week 1 Grams` | `week-1-grams` |
| `"Nordic Fishing Vessels"` | `None` | `Nordic Fishing Vessels` | `nordic-fishing-vessels` |
| `""` | `None` | `` | `` |

- A purely-numeric effective chapter `N` (matched as `^\d+$`) expands to display
  `Week N` and slug `week-N`. The rule is general for any positive integer.
- The on-disk topic path (`main/{slug}/gram-NN/`) and the ditamap navtitle both
  derive from this single function, so the map and the tree agree.

## Resulting `main` layout

```
out/main/week-1/gram-01/gram_01.dita
out/main/week-1/gram-02/gram_02.dita
out/main/week-2/gram-01/gram_01.dita
...
```

The main ditamap groups one entry per effective (week) chapter, and one
`<topicref>` per gram at its effective-numbered path.

> **Update (2026-06, week sub-documents):** the chapter entry is no longer a
> `<topichead>` with a `<navtitle>`. Each week is now a **chapter topic**
> (`main/week-N/week_N.dita`, title `Week N` via the same
> `_normalise_chapter` decomposition, Instructor prefix audience-tagged) and
> the map nests the week's gram topicrefs under a `<topicref>` to it. The map
> itself lives at `main/main.ditamap` with folder-relative hrefs.
