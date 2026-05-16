Operator Console v2 — dark theme.

Source: mockups/index-dark/theme.css (a strict superset of the gram-topic
theme at mockups/theme-console-v2/theme.css — same first 351 lines plus
193 lines of body.ditamap-index rules). Vendored as a single stylesheet
so every published HTML page (gram topic, DITA-OT map index, per-edition
index, shared landing) can link the same file.

Per-edition variation is selected at runtime via the data-edition
attribute on <body> (instructor / student); per-page-type variation via
class="ditamap-index" / "landing".
