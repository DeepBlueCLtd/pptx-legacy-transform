# Contract delta: GramFrame `gram-config` — derived frequency limits

Amends `specs/001-pptx-dita-migration/contracts/gramframe.md`.

## Frequency rows now derived (not hardcoded)

Previously: `freq-start` was hardcoded `0`, `freq-end` was the raw `freq_end`
(= `bandwidth`).

Now both are derived from the CSV row's `bandwidth`/`bandcentre`:

```text
freq-start = bandcentre - bandwidth/2
freq-end   = bandcentre + bandwidth/2
```

Emitted gram-config table rows:

```xml
<row><entry>time-start</entry><entry>0</entry></row>
<row><entry>time-end</entry><entry>{time_end}</entry></row>
<row><entry>freq-start</entry><entry>{freq_start}</entry></row>
<row><entry>freq-end</entry><entry>{freq_end}</entry></row>
```

## Formatting (deterministic)

- Integer-valued limits render with no decimal point (`0`, `400`).
- Non-integer limits (odd `bandwidth`) render trailing-zero-stripped (`200.5`).
- `freq-start` may be negative when `bandcentre < bandwidth/2` (emitted as-is,
  not clamped).

## Degradation

- If `bandcentre` is blank/non-numeric but `bandwidth` is numeric: fall back to
  legacy (`freq-start = 0`, `freq-end = bandwidth`).
- If `bandwidth` is also blank/non-numeric: emit blank values — never crash
  (missing-asset-dangles).

`time-start` remains `0`. The GramFrame bundle still validates
`freq-end > freq-start`.
