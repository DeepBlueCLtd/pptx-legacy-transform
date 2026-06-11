# Contract: `main` output layout (flattened)

## Path shape

| | Before (feature 008) | After (feature 009) |
|---|---|---|
| `main` topic | `main/<week-slug>/<doc-slug>/gram-NN/gram_NN.dita` | `main/<week-slug>/gram-NN/gram_NN.dita` |
| Non-`main` | `<pub>/[<doc-slug>/]gram-NN/…` | unchanged |

- `<week-slug>` is `week-N` (from the bare-integer effective chapter, feature 008).
- The `<doc-slug>` tier is **removed for `main` only**. Non-`main` publications
  keep any `doc-slug` tier.
- Assets are still copied beside the topic with stable bare-filename hrefs
  (`analysis.png`, `lofar-1.png`, …) — unchanged.

## Ditamap href

`emit_main_ditamap` topicref hrefs lose the `doc-slug` segment:

```
main/<week-slug>/gram-NN/gram_NN.dita      (no <doc-slug>/ segment)
```

The href is still built from non-empty segments only (feature 008's fix), so an
empty week slug never produces `main//…`. After the publish stager rewrites
`href="main/` → `href="`, the topic href is `<week-slug>/gram-NN/gram_NN.dita`.

## Uniqueness scope (generator fail-fast)

`generate_dita.py`'s collision check (`check_row_identity`) keys `main` on:

```
(publication, effective_chapter /* week */, effective_number)
```

— **dropping** `effective_doc` for `main` to match the flat folder. A residual
collision (two distinct `main` grams at the same `(week, number)`) fails fast with
the existing operator message pointing at the dedupe step. This holds under both
numbering schemes (continuous → publication-wide-unique numbers; per-week →
week-unique numbers, disambiguated by the `week-N` path segment).

## Out of scope

- Non-`main` publication layouts and their collision scope.
- Audience/edition behaviour, DITAVAL, HTML publish layout — all unchanged.
