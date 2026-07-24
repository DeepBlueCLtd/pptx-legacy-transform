# GLC XML Schema (parser-relevant subset)

The pipeline depends only on the elements listed below. Anything else
in the GLC file is ignored. The parser is forgiving (R6): missing
elements produce empty strings plus warnings, malformed XML produces
an empty result plus a single `"GLC malformed: <reason>"` warning, and
the parser never raises.

## Document shape

```xml
<GAPS_Lite_configuration>
  <data_source>
    <filename>...</filename>            <!-- Windows path; only basename retained -->
    <bitmap_crop_values>
      <top_crop>...</top_crop>          <!-- ignored -->
      <bottom_crop>...</bottom_crop>    <!-- ignored since issue #148 (see below) -->
    </bitmap_crop_values>
  </data_source>
  <playback>
    <time_offset>...</time_offset>      <!-- ignored -->
  </playback>
  <settings>
    <lofar>
      <bandwidth>...</bandwidth>        <!-- band width  -->
      <bandcentre>...</bandcentre>      <!-- band centre frequency -->
    </lofar>
  </settings>
</GAPS_Lite_configuration>
```

## Field contract

| Path | Maps to | Type | Notes |
|---|---|---|---|
| `data_source/filename` | `image_filename` | string | strip path with `pathlib.PureWindowsPath(raw).name`; if `raw` is empty, return empty |
| `settings/lofar/bandwidth` | `bandwidth` | string | trim whitespace; empty if missing |
| `settings/lofar/bandcentre` | `bandcentre` | string | trim whitespace; empty if missing |

**`bottom_crop` is no longer read (issue #148).** The gram's time period
(`time_end`) is the referenced image's **pixel height** — the number of
horizontal scan lines — measured from the image file on disk by
`extract_to_csv.py`, not parsed from the GLC (the legacy viewer multiplies the
scan-line count by an update period that is always `1` s, so seconds == rows).
`parse_glc` therefore exposes only `image_filename`, `bandwidth` and
`bandcentre`; it neither reads `bottom_crop` nor emits a
`"GLC missing bottom_crop"` warning (many valid image GLCs omit the element).

The frequency band is **bandwidth + bandcentre** (issue #87): the band spans
`bandwidth/2` either side of `bandcentre`, so `freq_start = bandcentre -
bandwidth/2` and `freq_end = bandcentre + bandwidth/2`. The generator derives
these for the DITA gram-config table; the GLC carries the two raw settings, not
the derived limits. `time-start` is always literally `"0"` in DITA output and is
not read from GLC.

## Asset extension contract

The `data_source/filename` element may name an asset of three kinds.
The parser does not interpret the extension — it simply returns the
basename — but downstream stages (`extract_to_csv.py`,
`generate_dita.py`, see `dita-topic-schema.md` §1.2/§1.3) dispatch
on it:

| Extension | Semantics | Downstream rendering |
|---|---|---|
| `.png` / `.jpg` / `.gif` | Pre-rendered spectrogram screenshot living next to the `.glc` | Embedded inline as `<image>` in a gram-config table (§1.2) |
| `.wav` | Raw audio; the on-PC GLC viewer renders the spectrogram live from it | The `.glc` is copied alongside its `.wav` and linked from the gram topic via `<xref href="*.glc">` (§1.3) so the viewer can open both |
| anything else | Anomalous; not observed in the audited corpus | Row skipped, recorded in `skipped.txt` |

Corpus distribution today (1,004 audited `.glc` files): ~82% `.png`,
~18% `.wav`, no `.jpg` observed. The `.jpg` branch is supported
defensively because the GLC viewer accepts it; no migration in
flight has produced one yet.

## Tolerated deviations

| Deviation | Behaviour |
|---|---|
| Root element name differs | Treated as malformed; empty result + warning |
| Element present but empty (e.g. `<bandwidth/>`) | Treated as missing; empty value + warning |
| Element present with non-numeric content | Returned as-is; generator passes it through to DITA — author's review catches it |
| Extra unknown elements/attributes | Ignored without warning |
| Multiple `<filename>` elements | First occurrence wins; warning recorded |
| `<filename>` containing forward-slash POSIX path | Still passed through `PureWindowsPath`; on POSIX systems the basename is computed correctly |
| BOM at file start | Tolerated by `xml.etree.ElementTree` |

## Warning vocabulary (verbatim strings)

The parser emits these exact warning strings into the row's
`warnings` column so downstream filtering is reliable:

- `"GLC malformed: <reason>"` — XML parse failed (`<reason>` is the
  exception's first line, no newlines)
- `"GLC missing filename"` — `<filename>` element absent or empty
- `"GLC missing bandwidth"` — `<bandwidth>` element absent or empty
- `"GLC missing bandcentre"` — `<bandcentre>` element absent or empty
- `"GLC duplicate filename"` — `<filename>` appears more than once

## Worked example

Input:

```xml
<GAPS_Lite_configuration>
  <data_source>
    <filename>W:\AAAC\Nordik\gram12.PNG</filename>
    <bitmap_crop_values>
      <top_crop>1</top_crop>
      <bottom_crop>271</bottom_crop>
    </bitmap_crop_values>
  </data_source>
  <playback>
    <time_offset>1234567890</time_offset>
  </playback>
  <settings>
    <lofar>
      <bandwidth>400</bandwidth>
      <bandcentre>200</bandcentre>
    </lofar>
  </settings>
</GAPS_Lite_configuration>
```

Output:

```python
GlcDocument(
    image_filename="gram12.PNG",
    bandwidth="400",
    bandcentre="200",
    warnings=[],
)
```

(`bottom_crop` of `271` above is ignored — `time_end` is later set by
`extract_to_csv.py` from `gram12.PNG`'s pixel height, issue #148.)

Malformed input (truncated mid-tag):

```xml
<GAPS_Lite_configuration>
  <data_source>
    <filename>W:\AAAC\file.png<
```

Output:

```python
GlcDocument(
    image_filename="",
    bandwidth="",
    bandcentre="",
    warnings=["GLC malformed: not well-formed (invalid token): line 3, column ..."],
)
```
