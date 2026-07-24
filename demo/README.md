# Demo data

## `demon-incoming/` — demon-image demo (issue #151)

An **incoming** delivery tree of demon screenshots used to demonstrate the
demon-image flow in the PR preview. It mirrors the `source/` layout minus the
per-document container tier (exactly what `ingest_gram_images.py` expects):

```
demon-incoming/<document>/<gram>/<Demon ...>.png
   ↔ source/<document>/<container>/<gram>/
```

The demon `.glc` markers are **derived**, not committed. The PR-preview build
regenerates them from this fixture before extraction:

```bash
python scripts/ingest_gram_images.py \
  --incoming-root demo/demon-incoming --source-root source/ --apply
```

That copies each demon image into its `source/` gram folder and writes the
`demon.glc` / `demon-2.glc` marker (cloned from the gram's first hyperlinked
`.glc`, repointed at the image, band overwritten to the fixed 0 – 40 Hz). The
step is idempotent and only touches the ephemeral CI checkout — `source/` in the
repo stays free of derived demon artefacts.

Current fixture seeds two Week 1 grams:

- **Gram 5** — one demon (`Demon - 0-40Hz.png`)
- **Gram 2** — two demons (`Demon - 0-40Hz.png`, `4m10s_Demon - 0 - 40 Hz.png`),
  proving multiple-demon ordering and the duration-prefixed filename form

The images are copies of the repo-root `demon_stock.png` (978 × 232), so each
demon's time period renders as 232 (its pixel height, per issue #148).
