# Contract: `main` output layout (flattened)

> **Superseded in part (2026-06, week sub-documents + in-folder ditamaps).**
> The topic *paths* below still hold, but the ditamap now lives **inside** the
> publication folder (`main/main.ditamap`) with folder-relative hrefs
> (`<week-slug>/gram-NN/gram_NN.dita` — no `main/` prefix and no publish-stage
> rewriting), and each week is referenced as a **chapter sub-document**
> (`<topicref href="week-N/week_N.dita">` wrapping the week's gram topicrefs)
> rather than a nav-only `<topichead>`. **Superseded again (2026-06, weeks at
> top level):** `main` no longer has a `Grams` folder — each week
> `<topicref>` now sits at the **top level** of the map, beside the static
> pages, so the top-level nav is **Welcome · Security · Week 1 · Week 2 · …**,
> and a `main` row with no week assigned is a fail-fast error
> (`check_main_chapter_assigned`). See `README.md` → *Common pages and the
> Grams nav folder* for the current shape.

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
