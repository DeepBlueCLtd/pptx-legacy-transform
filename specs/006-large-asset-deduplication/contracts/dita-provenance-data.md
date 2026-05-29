# Contract: redirected lofar — `<data>` provenance + master href

Extends the DITA output schema
(`specs/001-pptx-dita-migration/contracts/dita-topic-schema.md` §1.2/§1.3) for
lofar `<section>`s whose asset has been redirected to a master copy.

## When a lofar is redirected

A lofar is redirected iff its CSV row carries a non-empty, resolvable
`master_png_path`. The export then differs from the normal case in exactly two
ways: (1) the asset is **not** copied into the gram folder; (2) the link points
to the master copy and a `<data>` element is appended.

## Image lofar (GramFrame `gram-config` table — §1.2)

Normal: `<image href="lofar-1-abc.png" …/>` referencing the local copy.

Redirected:

```xml
<section outputclass="lofar-stage">
  <title>…display text…</title>
  <table outputclass="gram-config">
    <tgroup cols="2">
      …
      <image href="../../gram-07/lofar-1-abc.png" placement="break" align="center"/>
      …
    </tgroup>
  </table>
  <data name="original-asset-path" value="supporting/gram-12/Lofar 1 ABC.png"/>
</section>
```

- `<image href>` is the **relative path** from this gram's folder to the master
  gram's copy (computed via `os.path.relpath`, POSIX-separated). The asset is
  written **once**, in the master gram's folder.
- `@value` of `<data>` is the original local path of the **link target** — for
  an image lofar that is this row's own `png_path` (where the image should sit
  locally if rehydrated), not the master's.

## Audio lofar (GLC-viewer link — §1.3)

Normal: `<xref href="lofar-1-i.glc" format="glc" scope="local">…</xref>` with the
`.glc` and `.wav` copied side by side into the gram folder.

Redirected:

```xml
<section outputclass="lofar-stage">
  <title>…display text…</title>
  <p>
    <xref href="../../gram-07/lofar-1-i.glc" format="glc" scope="local">…</xref>
  </p>
  <data name="original-asset-path" value="supporting/gram-12/Lofar 1 I.glc"/>
</section>
```

- The `<xref>` targets the **master `.glc`** (FR-009). Neither the `.glc` nor the
  `.wav` is copied into the redirected gram; the large `.wav` stays adjacent to
  the master `.glc` in the master gram's folder.
- `@value` records the original local path of the **link target — the `.glc`
  (this row's `glc_path`), not the `.wav`** — so the re-localised `<xref>` href
  is an exact inverse. The `.wav` is not named in the element; on rehydration it
  is restored by **adjacency** (copied from beside the master `.glc`). The master
  `.glc` link plus this value are sufficient to rehydrate the pair.

## `<data>` element rules

| Aspect | Value |
|---|---|
| Element | `<data>` — standard DITA metadata domain, valid in `<section>`, no specialisation |
| `@name` | exactly `original-asset-path` |
| `@value` | the original local path of the **link target** — the row's `png_path` for an image lofar, the row's `glc_path` for an audio lofar (never the `.wav`) |
| Placement | last child of the redirected lofar `<section>` |
| Cardinality | exactly one on a redirected lofar; **absent** otherwise |
| Flagging | presence alone marks the lofar as redirected — no `@outputclass` token (FR-007) |
| Rendering | suppressed from default trainee XHTML by DITA-OT (FR-006) |
| Determinism | identical bytes across runs (LF, UTF-8 no BOM, no timestamps) — FR-013 |

## Reversal (consumed by `rehydrate_dita.py`)

Given a redirected lofar, rehydration is a pure inverse transform using only the
element + href:
1. Resolve the master file from the `<image>`/`<xref>` href (relative to the
   topic folder).
2. Recompute the local slug for the link target from `basename(@value)` via
   `slugify_asset_name`, and copy the master link target into **this gram's
   folder** under that slug. For audio, `@value` is the `.glc`, so the master
   `.glc` is restored under its slug and its adjacent master `.wav` is copied
   too (restored by adjacency, under the `.wav`'s own slug).
3. Rewrite the href to the local copy and **remove** the `<data>` element.

The result is byte-/structure-identical to a never-deduplicated topic (SC-004).
A lofar without `<data name="original-asset-path">` is left untouched.
