# Contract delta: GLC schema — `bandcentre`

Amends `specs/001-pptx-dita-migration/contracts/glc-schema.md`.

## Element added

```xml
<settings>
  <lofar>
    <bandwidth>...</bandwidth>     <!-- band width  -->
    <bandcentre>...</bandcentre>   <!-- band centre frequency -->
  </lofar>
</settings>
```

## Mapping change

| GLC path                     | GlcDocument field | Type   | Missing behaviour                         |
|------------------------------|-------------------|--------|-------------------------------------------|
| `settings/lofar/bandwidth`   | `bandwidth`       | string | trim; empty + `"GLC missing bandwidth"`   |
| `settings/lofar/bandcentre`  | `bandcentre`      | string | trim; empty + `"GLC missing bandcentre"`  |

`freq_end` is no longer a `GlcDocument` field. The frequency band is derived by
the **consumer** (generator) from the `bandwidth`/`bandcentre` pair:
`[bandcentre - bandwidth/2, bandcentre + bandwidth/2]`.

## Warnings

- `"GLC missing bandwidth"` — `<bandwidth>` absent or empty (unchanged)
- `"GLC missing bandcentre"` — `<bandcentre>` absent or empty (new)

`parse_glc` still never raises.
