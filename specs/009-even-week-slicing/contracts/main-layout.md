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

## Ditamap shape (feature 010 update)

Feature 010 changes the *depth* of these topicrefs, not their hrefs. Every
generated ditamap (this `main` map included) is reshaped so grams no longer sit
at the map root:

- The common static pages are prepended as the first top-level topicrefs —
  `main/welcome.dita`, `main/security.dita` (the same `main/` prefix the stager
  strips).
- The per-week chapter `<topichead>`s are nested inside a single root-level
  `<topichead><topicmeta><navtitle>Grams</navtitle></topicmeta>…</topichead>`.

Per-gram topicref hrefs are byte-for-byte unchanged; only their position in the
tree moves. Top-level nav becomes **Welcome · Security · Grams**. Full detail in
`README.md` → *Common pages and the Grams nav folder (feature 010)*.

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
