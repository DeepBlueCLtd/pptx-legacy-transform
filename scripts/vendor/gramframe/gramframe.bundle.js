(function() {
  // Inject CSS styles
  const style = document.createElement('style');
  style.textContent = "/**\n * GramFrame Component Styles - Military/Industrial Theme\n */\n\n/* ---------------------------------------------------------------------------\n * Pre-conversion placeholder\n *\n * A `table.gram-config` is ordinary HTML until GramFrame replaces it, so on a\n * cold load (large spectrogram, slow network, unbundled dev modules) the raw\n * table is painted first: a stretched image followed by the time/freq parameter\n * rows in whatever table styling the host page uses. These rules dress that\n * intermediate state as a loading placeholder in the component's own dark\n * styling - the parameter rows are hidden, the image is dimmed back, and a\n * \"Loading spectrogram\" caption sits over the top. They stop applying the\n * moment the table is swapped for .gram-frame-container.\n *\n * Selectors are deliberately more specific than a bare `table.gram-config td`\n * so host-page table styling (borders, padding, stretched images) does not show\n * through the placeholder.\n * ------------------------------------------------------------------------- */\ntable.gram-config {\n  border-collapse: collapse;\n  background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 50%, #0f0f0f 100%);\n  border: 3px solid #444;\n  border-radius: 8px;\n  box-shadow:\n    inset 0 2px 4px rgba(255,255,255,0.1),\n    inset 0 -2px 4px rgba(0,0,0,0.3),\n    0 4px 8px rgba(0,0,0,0.5);\n}\n\n/* Per the config format, the first row holds the image and every later row is a\n   parameter definition - configuration, not content, so hide those rows */\ntable.gram-config tr:not(:first-child) {\n  display: none;\n}\n\ntable.gram-config tr:first-child td {\n  position: relative;\n  padding: 15px;\n  border: 0;\n  background: none;\n}\n\ntable.gram-config tr:first-child img {\n  display: block;\n  width: auto;\n  max-width: 100%;\n  height: auto;\n  opacity: 0.25;\n}\n\ntable.gram-config tr:first-child td::after {\n  content: 'Loading spectrogram';\n  position: absolute;\n  left: 50%;\n  top: 50%;\n  transform: translate(-50%, -50%);\n  font-family: 'Courier New', monospace;\n  font-size: 14px;\n  letter-spacing: 2px;\n  text-transform: uppercase;\n  color: #00ff00;\n  text-shadow: 0 0 6px rgba(0, 255, 0, 0.6);\n  white-space: nowrap;\n  pointer-events: none;\n}\n\n/* Initialisation failed: the table is kept in place beside the error message,\n   so drop the placeholder styling and show the config as plain content again */\ntable.gram-config.gram-frame-config-error {\n  background: none;\n  border: 0;\n  box-shadow: none;\n}\n\ntable.gram-config.gram-frame-config-error tr:not(:first-child) {\n  display: table-row;\n}\n\ntable.gram-config.gram-frame-config-error tr:first-child img {\n  opacity: 1;\n}\n\ntable.gram-config.gram-frame-config-error tr:first-child td::after {\n  content: none;\n}\n\n/* Container that replaces the config table */\n.gram-frame-container {\n  position: relative;\n  width: 100%;\n  max-width: 100%;\n  margin: 0;\n  padding: 0;\n  box-sizing: border-box;\n  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;\n  background: transparent;\n  transition: box-shadow 0.2s ease, border-color 0.2s ease;\n  margin-bottom: 20px;\n}\n\n/* Focus indicator for multiple instances */\n.gram-frame-container.gram-frame-focused {\n  box-shadow: 0 0 0 3px rgba(66, 139, 202, 0.5);\n  border-radius: 8px;\n}\n\n/* The outer frame (not the diffing <table> — see `gram-frame-layout` in\n   table.js).\n *\n * A hairline and a radius, on the panel's own surface. It used to be a 3px\n * bevelled border over a three-stop gradient — an instrument-case look that\n * competed with the readouts inside it for the eye, which is the problem the\n * control-row redesign exists to fix. The frame's job is to say where the\n * component ends. */\n.gram-frame-layout {\n  display: table;\n  /* Fixed, so the cells take the frame's width rather than the width their\n     contents would like. Without it the control row's min-content width — five\n     columns of nowrap labels — sets the component's width, and a host narrower\n     than that gets a clipped third table instead of a squeezed one. */\n  table-layout: fixed;\n  width: 100%;\n  height: 100%;\n  background: var(--gf-surface);\n  border: 1px solid var(--gf-divider);\n  border-radius: 8px;\n  overflow: hidden;\n}\n\n.gram-frame-row {\n  display: table-row;\n}\n\n.gram-frame-row:nth-child(2) {\n  height: 100%; /* Main panel row should stretch */\n}\n\n.gram-frame-cell {\n  display: table-cell;\n  vertical-align: middle;\n  padding: 0;\n}\n\n\n/* The plot area. Unchanged in what it draws — the gram, the axes and every\n * overlay are out of the redesign's scope — but its casing is now the same\n * ground as the panel above it, so the two read as one instrument rather than\n * as two bevelled boxes stacked. */\n.gram-frame-main-panel {\n  padding: 12px;\n  background: #0c0d16;\n  border: 0;\n  border-top: 1px solid var(--gf-divider);\n  position: relative;\n}\n\n/* The SVG has no size until the spectrogram's natural dimensions are known, so\n   the panel is an empty black rectangle between the table being replaced and\n   the image arriving. Caption that gap, and say so plainly if the image never\n   arrives, rather than leaving the analyst looking at a silent black box. */\n.gram-frame-container.gram-frame-loading .gram-frame-main-panel,\n.gram-frame-container.gram-frame-image-error .gram-frame-main-panel {\n  min-height: 120px;\n}\n\n.gram-frame-container.gram-frame-loading .gram-frame-main-panel::after,\n.gram-frame-container.gram-frame-image-error .gram-frame-main-panel::after {\n  content: 'Loading spectrogram';\n  position: absolute;\n  left: 50%;\n  top: 50%;\n  transform: translate(-50%, -50%);\n  font-family: 'Courier New', monospace;\n  font-size: 14px;\n  letter-spacing: 2px;\n  text-transform: uppercase;\n  color: #00ff00;\n  text-shadow: 0 0 6px rgba(0, 255, 0, 0.6);\n  white-space: nowrap;\n  pointer-events: none;\n}\n\n.gram-frame-container.gram-frame-image-error .gram-frame-main-panel::after {\n  content: 'Spectrogram image could not be loaded';\n  color: #ff6b6b;\n  text-shadow: none;\n}\n\n/* An audio-sourced gram (spec 168) is analysed after the table is replaced:\n   the loading caption stays up, but reads the stage and percentage the setup\n   step writes into data-gram-progress on the main panel (FR-006). */\n.gram-frame-container.gram-frame-analysing .gram-frame-main-panel::after {\n  content: attr(data-gram-progress);\n}\n\n/* While the recording plays, annotation tools are inert (spec 168 FR-013, as\n   narrowed by spec 171 FR-004a) but the gram can be dragged to seek through it\n   (spec 171, FR-015) — so the open hand, not the crosshair and not the arrow.\n   !important because the modes set the cursor inline on the SVG root. */\n.gram-frame-container.gram-frame-playing .gram-frame-svg {\n  cursor: grab !important;\n}\n\n/* The drag itself. Playback is paused for its duration, so the playing class\n   is gone and this rule stands on its own. */\n.gram-frame-container.gram-frame-drag-seek .gram-frame-svg {\n  cursor: grabbing !important;\n}\n\n/* The contrast controls, on the same bar as the transport (spec 171, US2). */\n/* The contrast controls (spec 171, US2). They ride the transport bar, and wrap\n   onto a line of their own when the bar has nothing left to give: the row above\n   is a fixed set of controls, so this pair is the one that yields. */\n.gram-frame-display-range {\n  display: flex;\n  align-items: center;\n  gap: 10px;\n  flex: 1 1 300px;\n  min-width: 0;\n}\n\n.gram-frame-display-control {\n  display: flex;\n  align-items: center;\n  gap: 6px;\n  flex: 1 1 0;\n  min-width: 0;\n}\n\n.gram-frame-display-label {\n  flex: none;\n  font: 400 9px/1 var(--gf-mono);\n  letter-spacing: 0.14em;\n  color: var(--gf-muted);\n  text-transform: uppercase;\n}\n\n.gram-frame-display-slider {\n  flex: 1;\n  min-width: 0;\n  height: 4px;\n  appearance: none;\n  -webkit-appearance: none;\n  background: rgba(247, 247, 250, 0.13);\n  border-radius: 2px;\n  cursor: pointer;\n}\n\n.gram-frame-display-slider::-webkit-slider-thumb {\n  appearance: none;\n  -webkit-appearance: none;\n  width: 9px;\n  height: 9px;\n  border: 0;\n  border-radius: 5px;\n  background: var(--gf-secondary);\n}\n\n.gram-frame-display-slider::-moz-range-thumb {\n  width: 9px;\n  height: 9px;\n  border: 0;\n  border-radius: 5px;\n  background: var(--gf-secondary);\n}\n\n.gram-frame-display-reset {\n  width: auto;\n  padding: 0 8px;\n  font-size: 10.5px;\n}\n\n/* The colour-map choice, on the same bar: a radio row so every map under\n   trial is visible at once and switching between two is one click each way. */\n.gram-frame-colour-map {\n  display: flex;\n  align-items: center;\n  flex-wrap: wrap;\n  gap: 2px 10px;\n  flex: 1 1 100%;\n  font-size: 11px;\n  letter-spacing: 0.03em;\n  text-transform: uppercase;\n  opacity: 0.9;\n}\n\n.gram-frame-colour-map-option {\n  display: inline-flex;\n  align-items: center;\n  gap: 3px;\n  cursor: pointer;\n}\n\n.gram-frame-colour-map-option input {\n  margin: 0;\n}\n\n/* The caption naming what the render caps changed (spec 171, FR-024). */\n.gram-frame-degraded-note {\n  margin-top: 8px;\n  padding: 4px 6px;\n  border: 1px solid rgba(230, 200, 120, 0.6);\n  border-radius: 4px;\n  background: rgba(60, 50, 20, 0.75);\n  color: #ffe6a0;\n  font-size: 12px;\n}\n\n/* The transport's live region is for screen readers only (spec 171, FR-026):\n   it carries no visible text of its own, and everything it says is already on\n   the bar for a sighted reader. */\n.gram-frame-transport-status {\n  position: absolute;\n  width: 1px;\n  height: 1px;\n  padding: 0;\n  margin: -1px;\n  overflow: hidden;\n  clip: rect(0, 0, 0, 0);\n  white-space: nowrap;\n  border: 0;\n}\n\n.gram-frame-transport-span {\n  flex: none;\n  font: 400 10px/1 var(--gf-mono);\n  color: var(--gf-muted);\n  white-space: nowrap;\n}\n\n/* The transport bar under an audio-sourced gram (spec 168, D13).\n *\n * Below the gram, so the scrub track and its bookmark flags line up with the\n * time axis they refer to and the control panel above never changes height.\n * One row, on the panel's own surface: it is chrome for the recording, not a\n * second instrument. */\n.gram-frame-transport {\n  display: flex;\n  flex-wrap: wrap;\n  align-items: center;\n  gap: 10px 12px;\n  min-height: 44px;\n  padding: 7px 12px;\n  box-sizing: border-box;\n  background: var(--gf-surface);\n  border-top: 1px solid rgba(247, 247, 250, 0.08);\n  color: var(--gf-text);\n  font-family: var(--gf-ui);\n}\n\n.gram-frame-transport-group {\n  display: flex;\n  align-items: center;\n  gap: 4px;\n  position: relative;\n}\n\n.gram-frame-transport-btn {\n  width: 26px;\n  height: 26px;\n  display: grid;\n  place-items: center;\n  padding: 0;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 5px;\n  color: var(--gf-secondary);\n  font: 400 12px/1 var(--gf-ui);\n  cursor: pointer;\n}\n\n.gram-frame-transport-btn .gram-frame-icon {\n  width: 13px;\n  height: 13px;\n}\n\n.gram-frame-transport-btn:hover {\n  border-color: rgba(247, 247, 250, 0.4);\n  color: var(--gf-text);\n}\n\n.gram-frame-transport-btn[aria-pressed=\"true\"] {\n  border-color: var(--gf-accent);\n  color: var(--gf-accent-200);\n  background: var(--gf-accent-900);\n}\n\n/* Play/pause is the one filled control on the bar: it is the thing an analyst\n   reaches for without looking. */\n.gram-frame-transport-primary {\n  width: 30px;\n  height: 30px;\n  background: var(--gf-accent);\n  border: 0;\n  border-radius: 7px;\n  color: var(--gf-bg);\n}\n\n.gram-frame-transport-primary .gram-frame-icon {\n  width: 12px;\n  height: 12px;\n}\n\n.gram-frame-transport-primary:hover,\n.gram-frame-transport-primary[aria-pressed=\"true\"] {\n  background: var(--gf-accent-400);\n  color: var(--gf-bg);\n  border: 0;\n}\n\n.gram-frame-transport-time,\n.gram-frame-transport-duration {\n  flex: none;\n  font: 400 12px/1 var(--gf-mono);\n  font-variant-numeric: tabular-nums;\n}\n\n.gram-frame-transport-duration {\n  color: var(--gf-muted);\n}\n\n.gram-frame-transport-track {\n  position: relative;\n  flex: 1 1 180px;\n  min-width: 140px;\n  height: 30px;\n}\n\n/* The scrub track. A native range input, restyled: the rail is painted by the\n   track itself and the played portion by a gradient stop the reflect pass\n   moves, so there is one element to align rather than three. */\n.gram-frame-transport-seek {\n  position: absolute;\n  left: 0;\n  right: 0;\n  top: 13px;\n  width: 100%;\n  height: 4px;\n  margin: 0;\n  padding: 0;\n  appearance: none;\n  -webkit-appearance: none;\n  background: linear-gradient(\n    to right,\n    var(--gf-accent) 0 var(--gf-played, 0%),\n    rgba(247, 247, 250, 0.13) var(--gf-played, 0%) 100%\n  );\n  border-radius: 2px;\n  cursor: pointer;\n}\n\n.gram-frame-transport-seek::-webkit-slider-thumb {\n  appearance: none;\n  -webkit-appearance: none;\n  width: 11px;\n  height: 11px;\n  border: 0;\n  border-radius: 6px;\n  background: var(--gf-accent-100);\n  box-shadow: 0 0 0 3px rgba(145, 132, 217, 0.28);\n  cursor: pointer;\n}\n\n.gram-frame-transport-seek::-moz-range-thumb {\n  width: 11px;\n  height: 11px;\n  border: 0;\n  border-radius: 6px;\n  background: var(--gf-accent-100);\n  box-shadow: 0 0 0 3px rgba(145, 132, 217, 0.28);\n  cursor: pointer;\n}\n\n/* The flags sit over the track and are transparent to the pointer except where\n   a flag actually is, so scrubbing past one still scrubs. */\n.gram-frame-transport-flags {\n  position: absolute;\n  inset: 0;\n  pointer-events: none;\n}\n\n.gram-frame-transport-flag {\n  position: absolute;\n  top: 2px;\n  transform: translateX(-50%);\n  display: flex;\n  flex-direction: column;\n  align-items: center;\n  padding: 0;\n  background: none;\n  border: 0;\n  pointer-events: auto;\n  cursor: pointer;\n}\n\n.gram-frame-transport-flag-plate {\n  padding: 1px 5px;\n  border-radius: 3px;\n  background: var(--gf-text);\n  color: var(--gf-bg);\n  font: 600 9px/1.4 var(--gf-mono);\n  white-space: nowrap;\n}\n\n.gram-frame-transport-flag-stem {\n  width: 1px;\n  height: 9px;\n  background: var(--gf-text);\n}\n\n.gram-frame-transport-divider {\n  flex: none;\n  width: 1px;\n  height: 20px;\n  background: var(--gf-divider);\n}\n\n/* Bookmark is the only outlined-in-accent control on the bar: it is the one\n   thing here that creates something rather than moving the playhead. */\n.gram-frame-transport-bookmark {\n  width: auto;\n  gap: 6px;\n  display: flex;\n  align-items: center;\n  padding: 0 9px;\n  border-color: var(--gf-accent);\n  color: var(--gf-accent-200);\n  font: 500 10.5px var(--gf-ui);\n  white-space: nowrap;\n}\n\n.gram-frame-transport-bookmark:hover {\n  background: rgba(145, 132, 217, 0.14);\n  border-color: var(--gf-accent);\n  color: var(--gf-accent-200);\n}\n\n.gram-frame-transport-saved {\n  height: 26px;\n  padding: 0 8px;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 5px;\n  color: var(--gf-muted);\n  font: 400 10.5px var(--gf-ui);\n  white-space: nowrap;\n  cursor: pointer;\n}\n\n.gram-frame-transport-saved:hover:not(:disabled) {\n  border-color: rgba(247, 247, 250, 0.4);\n  color: var(--gf-text);\n}\n\n.gram-frame-transport-saved:disabled {\n  opacity: 0.5;\n  cursor: default;\n}\n\n/* Opening upward: the bar is the last thing on the component, so a list\n   dropping down would be a list off the bottom of it. */\n.gram-frame-transport-saved-list {\n  position: absolute;\n  z-index: 30;\n  right: 0;\n  bottom: calc(100% + 6px);\n  min-width: 150px;\n  padding: 4px;\n  background: var(--gf-bg);\n  border: 1px solid var(--gf-hairline);\n  border-radius: 8px;\n  box-shadow: var(--gf-shadow-md);\n}\n\n.gram-frame-transport-saved-row {\n  display: flex;\n  align-items: center;\n  gap: 4px;\n}\n\n.gram-frame-transport-saved-jump {\n  flex: 1;\n  padding: 4px 6px;\n  background: transparent;\n  border: 0;\n  border-radius: 4px;\n  color: var(--gf-text);\n  font: 400 11px/1 var(--gf-mono);\n  text-align: left;\n  cursor: pointer;\n}\n\n.gram-frame-transport-saved-jump:hover {\n  background: var(--gf-hover);\n}\n\n.gram-frame-transport-saved-remove {\n  padding: 2px 5px;\n  background: transparent;\n  border: 0;\n  color: var(--gf-muted);\n  font: 400 13px/1 var(--gf-ui);\n  cursor: pointer;\n}\n\n.gram-frame-transport-saved-remove:hover {\n  color: var(--gf-danger-text);\n}\n\n.gram-frame-transport-rate-label {\n  flex: none;\n  font: 400 10px var(--gf-ui);\n  color: var(--gf-muted);\n  white-space: nowrap;\n}\n\n.gram-frame-transport-playback-rate {\n  height: 26px;\n  padding: 0 4px;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 5px;\n  color: var(--gf-text);\n  font: 400 10.5px var(--gf-mono);\n  cursor: pointer;\n}\n\n.gram-frame-transport-playback-rate option {\n  background: var(--gf-bg);\n  color: var(--gf-text);\n}\n\n.gram-frame-transport-volume {\n  flex: none;\n  width: 64px;\n  height: 4px;\n  appearance: none;\n  -webkit-appearance: none;\n  background: rgba(247, 247, 250, 0.13);\n  border-radius: 2px;\n  cursor: pointer;\n}\n\n.gram-frame-transport-volume::-webkit-slider-thumb {\n  appearance: none;\n  -webkit-appearance: none;\n  width: 9px;\n  height: 9px;\n  border: 0;\n  border-radius: 5px;\n  background: var(--gf-secondary);\n}\n\n.gram-frame-transport-volume::-moz-range-thumb {\n  width: 9px;\n  height: 9px;\n  border: 0;\n  border-radius: 5px;\n  background: var(--gf-secondary);\n}\n\n/* The analysed gram is drawn with hard-edged cells rather than the browser's\n   bilinear upscaling. A 0–200 Hz band at 2 Hz per column is 100 pixels wide\n   drawn across 800, and smoothed, each column becomes an 8-pixel gradient:\n   the whole picture reads as a watercolour and the vertical bars a legacy\n   display shows as discrete columns are gone. Pixelated, a column is a\n   column. It applies to the supplied-image instance too, where a PNG is\n   usually near its rendered size and the difference is slight. */\n.gram-frame-spectrogram-image {\n  image-rendering: pixelated;\n}\n\n/* Expand/collapse image toggle — floats at the top-left of the image region,\n   clear of the time-axis labels (left margin is 60px). Landscape grams only. */\n.gram-frame-expand-toggle {\n  position: absolute;\n  top: 22px;   /* just inside the main-panel padding + SVG top margin */\n  left: 80px;  /* clear of the 60px time-axis margin */\n  z-index: 5;  /* above the SVG overlay */\n  width: 26px;\n  height: 26px;\n  padding: 0;\n  display: flex;\n  align-items: center;\n  justify-content: center;\n  font-size: 15px;\n  line-height: 1;\n  color: #e6f2ff;\n  background: rgba(20, 30, 45, 0.55);\n  border: 1px solid rgba(180, 200, 230, 0.5);\n  border-radius: 4px;\n  cursor: pointer;\n  transition: background 0.12s ease, border-color 0.12s ease;\n}\n\n.gram-frame-expand-toggle:hover {\n  background: rgba(40, 60, 90, 0.8);\n  border-color: rgba(200, 220, 255, 0.8);\n}\n\n.gram-frame-expand-toggle:active {\n  transform: translateY(1px);\n}\n\n.gram-frame-expand-toggle[aria-pressed=\"true\"] {\n  background: rgba(60, 100, 60, 0.75);\n  border-color: rgba(150, 220, 150, 0.8);\n}\n\n/* SVG container for drawing the spectrogram and overlays */\n.gram-frame-svg {\n  display: block;\n  width: 100%;\n  height: auto;\n  background: #000;\n  border: 2px solid #333;\n  border-radius: 4px;\n  cursor: crosshair;\n  box-shadow: inset 0 2px 8px rgba(0,0,0,0.8);\n}\n\n/* SVG image element for the spectrogram */\n.gram-frame-image {\n  /* Remove width/height CSS to allow SVG attributes to control positioning */\n}\n\n/* SVG axes styling - white on dark background */\n.gram-frame-axis-line {\n  stroke: #fff;\n  stroke-width: 1;\n  fill: none;\n}\n\n.gram-frame-axis-tick {\n  stroke: #fff;\n  stroke-width: 1;\n}\n\n.gram-frame-axis-tick-major {\n  stroke: #fff;\n  stroke-width: 1;\n}\n\n.gram-frame-axis-tick-minor {\n  stroke: #fff;\n  stroke-width: 1;\n}\n\n.gram-frame-axis-label {\n  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;\n  font-size: 12px;\n  fill: #fff;\n  dominant-baseline: central;\n}\n\n.gram-frame-axis-label-major {\n  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;\n  font-size: 10px;\n  fill: #fff;\n  dominant-baseline: central;\n}\n\n\n\n\n/* Military-style display panel */\n/* ===========================================================================\n * The control row\n *\n * Five columns above the gram: the mode rail, the armed mode's guidance, the\n * cursor readouts, the style panel, and the three annotation tables. They are\n * separated by single hairlines rather than boxed, because five bordered cards\n * of equal weight gave the eye nowhere to land — the readouts are the first\n * read, and everything here is arranged so they win.\n *\n * Dark throughout, and deliberately so: the recognition differential when\n * reading plotted data is higher against a dark ground, which is what the panel\n * is beside. The palette is the design system's, declared once below and used\n * through the variables so a change lands everywhere at once.\n * ======================================================================== */\n\n.gram-frame-container {\n  /* Ground, surface and ink */\n  --gf-bg: #0d0e18;\n  --gf-surface: #171926;\n  --gf-text: #f7f7fa;\n  /* One value for the whole muted tier (~8.5:1 on the surface). Alphas below\n     .60 do not reach 4.5:1 on this ground; do not reintroduce them for text. */\n  --gf-muted: rgba(247, 247, 250, 0.70);\n  --gf-secondary: rgba(247, 247, 250, 0.85);\n\n  /* The non-text tier: rules, hover tints and recesses */\n  --gf-divider: #3a3c4a;\n  --gf-hairline: rgba(247, 247, 250, 0.18);\n  --gf-row-line: rgba(247, 247, 250, 0.07);\n  --gf-hover: rgba(247, 247, 250, 0.06);\n  --gf-row-hover: rgba(247, 247, 250, 0.05);\n  --gf-recess: rgba(0, 0, 0, 0.22);\n  --gf-recess-deep: rgba(0, 0, 0, 0.36);\n\n  /* Accent, and the ramp around it */\n  --gf-accent: #9184d9;\n  --gf-accent-100: #efedfb;\n  --gf-accent-200: #ddd9f6;\n  --gf-accent-400: #aca2e5;\n  --gf-accent-600: #7768c4;\n  --gf-accent-700: #5d4fa3;\n  --gf-accent-800: #433a71;\n  --gf-accent-900: #2b2741;\n  --gf-accent-tint: rgba(145, 132, 217, 0.09);\n\n  /* Destructive, on hover only: nothing here is red at rest */\n  --gf-danger-border: #8d5a5a;\n  --gf-danger-text: #e2b3b3;\n\n  --gf-ui: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n  --gf-mono: ui-monospace, Menlo, Consolas, monospace;\n  --gf-shadow-md: 0 12px 32px rgba(0, 0, 0, 0.5);\n\n  /* The panel's height. The gram is deliberately given as much room as\n     possible, so this is a budget rather than a starting point: a column that\n     needs more room scrolls inside it. */\n  --gf-panel-height: 250px;\n}\n\n/* The control row's own containment context.\n *\n * The panel's responsive behaviour depends on how wide the COMPONENT is, not on\n * how wide the window is: the same page can carry a full-width gram and a\n * half-width one, and a viewport media query would collapse the guidance in\n * both or neither. Scoped to this wrapper rather than the container so the\n * plot area below is outside the containment entirely. */\n.gram-frame-readout {\n  container-type: inline-size;\n  container-name: gramframe-controls;\n  width: 100%;\n  padding: 0;\n  background: transparent;\n}\n\n.gram-frame-unified-layout {\n  display: flex;\n  align-items: stretch;\n  height: var(--gf-panel-height);\n  background: var(--gf-surface);\n  font-family: var(--gf-ui);\n  color: var(--gf-text);\n}\n\n/* Every column but the last is closed by a hairline; the tables run to the\n   panel's own edge. */\n.gram-frame-unified-layout > * {\n  box-sizing: border-box;\n  border-right: 1px solid var(--gf-divider);\n}\n\n.gram-frame-unified-layout > :last-child {\n  border-right: 0;\n}\n\n/* Keyboard focus is one treatment everywhere in the panel — an accent ring,\n   offset so it never reads as a border the control has grown. */\n.gram-frame-unified-layout :focus-visible,\n.gram-frame-symbol-popup :focus-visible,\n.gram-frame-transport :focus-visible {\n  outline: 2px solid var(--gf-accent);\n  outline-offset: 2px;\n}\n\n/* A section kicker: the smallest text in the panel, and the only text set in\n   spaced monospace caps, so it reads as a label rather than as content. */\n.gram-frame-kicker {\n  font: 600 9px/1 var(--gf-mono);\n  letter-spacing: 0.16em;\n  color: var(--gf-muted);\n  text-transform: uppercase;\n}\n\n/* --- Column 1: the mode rail --------------------------------------------- */\n\n.gram-frame-mode-column {\n  flex: 0 0 154px;\n  width: 154px;\n  min-width: 0;\n}\n\n.gram-frame-modes {\n  display: flex;\n  flex-direction: column;\n  gap: 5px;\n  height: 100%;\n  padding: 10px 10px 8px;\n  box-sizing: border-box;\n}\n\n.gram-frame-modes > .gram-frame-kicker {\n  padding: 0 2px 2px;\n}\n\n.gram-frame-mode-list {\n  display: flex;\n  flex-direction: column;\n  gap: 5px;\n}\n\n.gram-frame-mode-spacer {\n  flex: 1;\n}\n\n/* A mode button: glyph, then word. The 2px left border is transparent at rest\n   and accent when armed, so arming changes no geometry — the row does not\n   shift under the pointer as the analyst moves down the rail. */\n.gram-frame-mode-btn {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n  height: 27px;\n  padding: 0 8px;\n  border: 0;\n  border-left: 2px solid transparent;\n  border-radius: 0 4px 4px 0;\n  background: transparent;\n  color: var(--gf-secondary);\n  font: 400 11.5px var(--gf-ui);\n  white-space: nowrap;\n  text-align: left;\n  cursor: pointer;\n}\n\n.gram-frame-mode-btn .gram-frame-icon {\n  width: 15px;\n  height: 15px;\n  flex: none;\n}\n\n.gram-frame-mode-btn-label {\n  overflow: hidden;\n  text-overflow: ellipsis;\n}\n\n.gram-frame-mode-btn:hover:not(:disabled) {\n  background: var(--gf-hover);\n  color: var(--gf-text);\n}\n\n.gram-frame-mode-btn.active {\n  background: var(--gf-accent-900);\n  border-left-color: var(--gf-accent);\n  color: var(--gf-accent-200);\n  font-weight: 500;\n}\n\n.gram-frame-mode-btn:disabled,\n.gram-frame-mode-btn.disabled {\n  opacity: 0.45;\n  cursor: not-allowed;\n}\n\n/* The view controls, at the foot of the rail behind a rule: they act on the\n   view rather than on the armed tool, which is why they are fenced off from\n   the five buttons above and stay put whichever is armed. */\n.gram-frame-mode-commands {\n  display: flex;\n  gap: 4px;\n  padding-top: 6px;\n  border-top: 1px solid var(--gf-divider);\n}\n\n.gram-frame-command-btn {\n  width: 26px;\n  height: 24px;\n  display: grid;\n  place-items: center;\n  padding: 0;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 4px;\n  color: var(--gf-secondary);\n  font: 400 13px var(--gf-ui);\n  cursor: pointer;\n}\n\n.gram-frame-command-btn .gram-frame-icon {\n  width: 14px;\n  height: 14px;\n}\n\n.gram-frame-command-btn:hover:not(:disabled) {\n  border-color: var(--gf-accent);\n  color: var(--gf-accent-200);\n}\n\n.gram-frame-command-btn:disabled {\n  opacity: 0.4;\n  cursor: not-allowed;\n}\n\n/* The word behind a glyph: gone from the page, present in the accessibility\n   tree and to anything selecting the button by name. */\n.gram-frame-visually-hidden {\n  position: absolute;\n  width: 1px;\n  height: 1px;\n  margin: -1px;\n  padding: 0;\n  overflow: hidden;\n  clip: rect(0 0 0 0);\n  clip-path: inset(50%);\n  white-space: nowrap;\n  border: 0;\n}\n\n/* --- Column 2: the armed mode's guidance --------------------------------- */\n\n.gram-frame-guidance-column {\n  flex: 0 0 264px;\n  width: 264px;\n  min-width: 0;\n  display: flex;\n  flex-direction: column;\n  background: var(--gf-recess);\n  box-sizing: border-box;\n}\n\n.gram-frame-guidance-header {\n  display: flex;\n  align-items: center;\n  gap: 7px;\n  flex: none;\n  height: 28px;\n  padding: 0 10px 0 12px;\n  border-bottom: 1px solid var(--gf-divider);\n}\n\n.gram-frame-guidance-title {\n  font: 600 9px/1 var(--gf-mono);\n  letter-spacing: 0.14em;\n  color: var(--gf-accent);\n  text-transform: uppercase;\n  white-space: nowrap;\n  overflow: hidden;\n  text-overflow: ellipsis;\n}\n\n.gram-frame-guidance-hide {\n  margin-left: auto;\n  height: 20px;\n  padding: 0 7px;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 4px;\n  color: var(--gf-muted);\n  font: 400 9.5px var(--gf-ui);\n  white-space: nowrap;\n  cursor: pointer;\n}\n\n.gram-frame-guidance-hide:hover {\n  border-color: rgba(247, 247, 250, 0.4);\n  color: var(--gf-text);\n}\n\n/* The body scrolls rather than growing the row: Pan carries its own four lines\n   plus the four cross-mode gestures, and the panel's height is a budget. */\n.gram-frame-guidance {\n  flex: 1;\n  min-height: 0;\n  overflow-y: auto;\n  display: flex;\n  flex-direction: column;\n  gap: 6px;\n  padding: 8px 12px;\n  box-sizing: border-box;\n}\n\n.gram-frame-guidance h4 {\n  margin: 4px 0 0;\n  font: 600 9px/1 var(--gf-mono);\n  letter-spacing: 0.14em;\n  color: var(--gf-muted);\n  text-transform: uppercase;\n}\n\n.gram-frame-guidance h4:first-child {\n  margin-top: 0;\n}\n\n.gram-frame-guidance h4 .gram-frame-guidance-qualifier {\n  font-weight: 400;\n  letter-spacing: 0;\n  text-transform: none;\n}\n\n/* One line of guidance: the trigger in a fixed track, the outcome beside it.\n   The fixed track is the whole point — it is what lets the gestures of a mode\n   be compared down the column instead of read out of four sentences. */\n.gram-frame-guidance-row {\n  display: flex;\n  gap: 8px;\n  align-items: baseline;\n}\n\n.gram-frame-guidance-trigger {\n  flex: none;\n  width: 76px;\n  font: 500 10px/1.4 var(--gf-ui);\n  color: var(--gf-text);\n}\n\n.gram-frame-guidance-outcome,\n.gram-frame-guidance-note {\n  font: 400 11px/1.4 var(--gf-ui);\n  color: var(--gf-secondary);\n}\n\n.gram-frame-guidance-note {\n  color: var(--gf-muted);\n}\n\n/* Collapsed: the column becomes a 40px rail in the same position, and the\n   ~224px it releases goes to the annotation tables. The space stays dedicated\n   — nothing else ever moves into it. */\n.gram-frame-guidance-column.gram-frame-guidance-collapsed {\n  flex: 0 0 40px;\n  width: 40px;\n  align-items: center;\n  padding: 10px 0;\n  gap: 10px;\n}\n\n.gram-frame-guidance-collapsed .gram-frame-guidance-header,\n.gram-frame-guidance-collapsed .gram-frame-guidance {\n  display: none;\n}\n\n.gram-frame-guidance-rail {\n  display: none;\n  flex-direction: column;\n  align-items: center;\n  gap: 10px;\n}\n\n.gram-frame-guidance-collapsed .gram-frame-guidance-rail {\n  display: flex;\n}\n\n.gram-frame-guidance-reveal {\n  width: 24px;\n  height: 24px;\n  display: grid;\n  place-items: center;\n  padding: 0;\n  background: transparent;\n  border: 1px solid var(--gf-accent-700);\n  border-radius: 4px;\n  color: var(--gf-accent-200);\n  font: 400 11px var(--gf-ui);\n  cursor: pointer;\n}\n\n.gram-frame-guidance-reveal:hover {\n  background: var(--gf-accent-900);\n}\n\n.gram-frame-guidance-rail-label {\n  font: 600 9px/1 var(--gf-mono);\n  letter-spacing: 0.16em;\n  color: var(--gf-muted);\n  text-transform: uppercase;\n  writing-mode: vertical-rl;\n}\n\n/* --- Column 3: the instrument face --------------------------------------- */\n\n.gram-frame-readout-column {\n  flex: 0 0 210px;\n  width: 210px;\n  min-width: 0;\n  display: flex;\n  flex-direction: column;\n  padding: 10px 14px 8px;\n  box-sizing: border-box;\n  /* Recessed, and lit from the top edge: it reads as a separate instrument set\n     into the panel rather than as another card sitting on it. */\n  background: var(--gf-recess-deep);\n  box-shadow: inset 0 1px 0 rgba(0, 0, 0, 0.4);\n}\n\n.gram-frame-readout-kicker {\n  display: flex;\n  align-items: baseline;\n  gap: 6px;\n  padding-bottom: 8px;\n}\n\n.gram-frame-readout-target {\n  font: 500 9.5px/1 var(--gf-ui);\n  letter-spacing: 0;\n  color: var(--gf-accent-200);\n  text-transform: none;\n  overflow: hidden;\n  text-overflow: ellipsis;\n  white-space: nowrap;\n}\n\n.gram-frame-readout-spacer {\n  flex: 1;\n}\n\n.gram-frame-led {\n  display: flex;\n  align-items: baseline;\n  justify-content: space-between;\n  gap: 8px;\n  font-family: var(--gf-mono);\n}\n\n.gram-frame-led-value {\n  font: 400 36px/1 var(--gf-mono);\n  color: var(--gf-text);\n  font-variant-numeric: tabular-nums;\n  letter-spacing: -0.01em;\n  /* The faint bloom is what makes it read as a lit instrument rather than as\n     large text. It is the only glow in the panel, and only the frequency\n     keeps it: the two secondary readings switch it off below. */\n  text-shadow: 0 0 18px rgba(247, 247, 250, 0.2);\n}\n\n.gram-frame-led-accent .gram-frame-led-value {\n  color: var(--gf-accent-200);\n  text-shadow: 0 0 20px rgba(145, 132, 217, 0.35);\n}\n\n.gram-frame-led-unit {\n  font: 400 9.5px/1 var(--gf-mono);\n  letter-spacing: 0.1em;\n  color: var(--gf-muted);\n}\n\n.gram-frame-led-caption {\n  font: 400 9px/1 var(--gf-mono);\n  letter-spacing: 0.14em;\n  color: var(--gf-muted);\n  text-transform: uppercase;\n}\n\n/* The second rank: time and the doppler speed. Half the frequency's size, no\n   bloom, and set in the same grey as the panel's labels rather than in ink,\n   so the frequency is the one reading that is lit. The caption on the left\n   names the row, since at this size the number cannot name itself. */\n.gram-frame-led-secondary {\n  flex: none;\n}\n\n.gram-frame-led-secondary .gram-frame-led-value {\n  font-size: 19px;\n  color: var(--gf-muted);\n  text-shadow: none;\n  margin-left: auto;\n}\n\n/* Time sits directly under the frequency, as the other half of the pointer's\n   coordinate; a small gap rather than a rule, so they read as one reading and\n   its qualifier. */\n.gram-frame-led-secondary:not(.gram-frame-led-inline) {\n  margin-top: 6px;\n}\n\n/* The doppler speed is a derived quantity rather than a coordinate, so it is\n   also fenced off at the foot between two rules. */\n.gram-frame-led-inline {\n  padding: 9px 0;\n  border-top: 1px solid var(--gf-divider);\n  border-bottom: 1px solid var(--gf-divider);\n}\n\n/* --- Column 4: the style panel ------------------------------------------- */\n\n.gram-frame-color-picker {\n  flex: 0 0 222px;\n  width: 222px;\n  min-width: 0;\n  display: flex;\n  flex-direction: column;\n  box-sizing: border-box;\n}\n\n/* Targeting a feature tints the whole column and warms its rules, so \"this\n   changes something that already exists\" is visible from across the panel. */\n.gram-frame-color-picker.gram-frame-style-targeting {\n  border-right-color: var(--gf-accent-700);\n}\n\n.gram-frame-style-tabs {\n  display: flex;\n  align-items: stretch;\n  flex: none;\n  height: 28px;\n  border-bottom: 1px solid var(--gf-divider);\n}\n\n.gram-frame-style-targeting .gram-frame-style-tabs {\n  border-bottom-color: var(--gf-accent-700);\n}\n\n.gram-frame-style-tab {\n  flex: 1;\n  min-width: 0;\n  display: flex;\n  align-items: center;\n  justify-content: center;\n  gap: 5px;\n  padding: 0 6px;\n  background: transparent;\n  border: 0;\n  color: var(--gf-muted);\n  font: 400 10px var(--gf-ui);\n  letter-spacing: 0.03em;\n  white-space: nowrap;\n  overflow: hidden;\n  cursor: pointer;\n}\n\n.gram-frame-style-tab-selected {\n  border-left: 1px solid var(--gf-divider);\n}\n\n.gram-frame-style-targeting .gram-frame-style-tab-selected {\n  border-left-color: var(--gf-accent-700);\n}\n\n.gram-frame-style-tab:hover:not(:disabled) {\n  background: var(--gf-hover);\n  color: var(--gf-text);\n}\n\n.gram-frame-style-tab:disabled {\n  color: rgba(247, 247, 250, 0.4);\n  cursor: not-allowed;\n}\n\n/* The armed tab. The first is underlined in plain ink and the second in\n   accent, matching what each one changes. */\n.gram-frame-style-tab-new.gram-frame-style-tab-armed {\n  background: var(--gf-hover);\n  border-bottom: 2px solid var(--gf-text);\n  color: var(--gf-text);\n  font-weight: 500;\n}\n\n.gram-frame-style-tab-selected.gram-frame-style-tab-armed {\n  background: var(--gf-accent-900);\n  border-bottom: 2px solid var(--gf-accent);\n  color: var(--gf-accent-100);\n  font-weight: 500;\n}\n\n.gram-frame-style-tab-swatch {\n  font-size: 11px;\n  line-height: 1;\n}\n\n.gram-frame-style-body {\n  flex: 1;\n  min-height: 0;\n  overflow-y: auto;\n  display: flex;\n  flex-direction: column;\n  gap: 9px;\n  padding: 10px 12px;\n  box-sizing: border-box;\n}\n\n.gram-frame-style-targeting .gram-frame-style-body {\n  background: var(--gf-accent-tint);\n}\n\n.gram-frame-style-spacer {\n  flex: 1;\n}\n\n.gram-frame-style-row {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n}\n\n.gram-frame-style-row[hidden] {\n  display: none;\n}\n\n.gram-frame-style-group-label {\n  flex: none;\n  width: 46px;\n  font: 400 10.5px var(--gf-ui);\n  color: var(--gf-muted);\n}\n\n/* The label field, edited where the label is read. The dialog it replaces meant\n   leaving the panel to change one word of what the panel is about. */\n.gram-frame-style-label-input {\n  flex: 1;\n  min-width: 0;\n  height: 26px;\n  padding: 0 8px;\n  box-sizing: border-box;\n  background: var(--gf-recess-deep);\n  border: 1px solid var(--gf-accent-600);\n  border-radius: 6px;\n  color: var(--gf-text);\n  font: 400 11.5px var(--gf-mono);\n}\n\n/* The colour slider: the one colour control in the panel. */\n.gram-frame-color-slider {\n  position: relative;\n  flex: none;\n  height: 19px;\n  border-radius: 3px;\n  box-shadow: 0 0 0 1px var(--gf-hairline);\n  overflow: visible;\n}\n\n.gram-frame-color-canvas {\n  display: block;\n  width: 100%;\n  height: 19px;\n  border-radius: 3px;\n  cursor: crosshair;\n}\n\n/* A bar overhanging the strip top and bottom, rather than a blob sitting on\n   it: the colour under the thumb stays visible, which is the one thing the\n   control exists to show. */\n.gram-frame-color-indicator {\n  position: absolute;\n  top: -3px;\n  bottom: -3px;\n  width: 3px;\n  margin-left: -1.5px;\n  border-radius: 2px;\n  background: var(--gf-text);\n  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.5);\n  pointer-events: none;\n}\n\n.gram-frame-symbol-select {\n  display: flex;\n  align-items: center;\n  gap: 6px;\n  height: 26px;\n  padding: 0 8px;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 6px;\n  color: var(--gf-text);\n  font: 400 11px var(--gf-ui);\n  white-space: nowrap;\n  cursor: pointer;\n}\n\n.gram-frame-symbol-select:hover {\n  border-color: rgba(247, 247, 250, 0.4);\n}\n\n.gram-frame-symbol-glyph {\n  font-size: 13px;\n  line-height: 1;\n}\n\n.gram-frame-symbol-caret {\n  color: var(--gf-muted);\n  font-size: 9px;\n}\n\n/* The symbol popup, positioned against the component rather than against the\n   row that opens it — see `placePopup` in SymbolPicker.js. */\n.gram-frame-symbol-popup {\n  position: absolute;\n  z-index: 30;\n  width: 238px;\n  background: var(--gf-bg);\n  border: 1px solid var(--gf-hairline);\n  border-radius: 8px;\n  box-shadow: var(--gf-shadow-md);\n  overflow: hidden;\n}\n\n.gram-frame-symbol-popup-header {\n  display: flex;\n  align-items: center;\n  height: 26px;\n  padding: 0 10px;\n  border-bottom: 1px solid var(--gf-divider);\n}\n\n/* All seven at once, at the size and in the colour they will be drawn in —\n   which is the comparison an analyst is actually making. */\n.gram-frame-symbol-grid {\n  display: grid;\n  grid-template-columns: repeat(4, 1fr);\n  gap: 4px;\n  padding: 8px;\n}\n\n.gram-frame-symbol-cell {\n  height: 32px;\n  display: grid;\n  place-items: center;\n  background: transparent;\n  border: 1px solid var(--gf-divider);\n  border-radius: 6px;\n  color: var(--gf-symbol-tint, var(--gf-text));\n  font: 400 15px var(--gf-ui);\n  cursor: pointer;\n}\n\n.gram-frame-symbol-cell:hover {\n  border-color: rgba(247, 247, 250, 0.4);\n}\n\n.gram-frame-symbol-cell-selected {\n  background: var(--gf-accent-900);\n  border-color: var(--gf-accent);\n}\n\n.gram-frame-symbol-popup-footer {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n  padding: 8px 10px;\n  border-top: 1px solid var(--gf-divider);\n}\n\n.gram-frame-symbol-popup-footer .gram-frame-style-group-label {\n  width: auto;\n}\n\n.gram-frame-symbol-popup-footer .gram-frame-segmented {\n  margin-left: auto;\n}\n\n/* A segmented control: both options on screen, one filled. */\n.gram-frame-segmented {\n  display: flex;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 6px;\n  overflow: hidden;\n}\n\n.gram-frame-segmented-option {\n  height: 24px;\n  padding: 0 10px;\n  background: transparent;\n  border: 0;\n  color: var(--gf-muted);\n  font: 400 10px var(--gf-ui);\n  letter-spacing: 0.04em;\n  text-transform: uppercase;\n  white-space: nowrap;\n  cursor: pointer;\n}\n\n.gram-frame-segmented-option + .gram-frame-segmented-option {\n  border-left: 1px solid var(--gf-hairline);\n}\n\n.gram-frame-segmented-option:hover:not(:disabled) {\n  background: var(--gf-hover);\n}\n\n.gram-frame-segmented-selected {\n  background: var(--gf-accent-900);\n  color: var(--gf-accent-200);\n  font-weight: 500;\n}\n\n.gram-frame-segmented-disabled {\n  opacity: 0.45;\n}\n\n.gram-frame-segmented-disabled .gram-frame-segmented-option {\n  cursor: not-allowed;\n}\n\n.gram-frame-symbol-popup-footer .gram-frame-segmented-option {\n  height: 22px;\n  text-transform: none;\n  letter-spacing: 0;\n  font-size: 10.5px;\n}\n\n.gram-frame-nudge {\n  display: flex;\n  align-items: center;\n  gap: 4px;\n}\n\n.gram-frame-nudge-btn {\n  width: 26px;\n  height: 24px;\n  display: grid;\n  place-items: center;\n  padding: 0;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 4px;\n  color: var(--gf-secondary);\n  font: 400 11px var(--gf-ui);\n  cursor: pointer;\n}\n\n.gram-frame-nudge-btn:hover {\n  border-color: var(--gf-accent);\n  color: var(--gf-accent-200);\n}\n\n.gram-frame-nudge-note {\n  margin-left: 4px;\n  font: 400 10px var(--gf-ui);\n  color: var(--gf-muted);\n  white-space: nowrap;\n}\n\n/* The footer states the target in words, so the tabs are never the only place\n   it is said. */\n.gram-frame-style-footer {\n  display: flex;\n  align-items: center;\n  gap: 6px;\n  flex: none;\n  margin: 0 12px;\n  padding: 8px 0 10px;\n  border-top: 1px dashed var(--gf-hairline);\n}\n\n.gram-frame-style-targeting .gram-frame-style-footer {\n  border-top: 1px solid var(--gf-accent-800);\n}\n\n.gram-frame-style-footer-glyph {\n  font-size: 13px;\n  line-height: 1;\n  opacity: 0.55;\n}\n\n.gram-frame-style-footer-note {\n  font: 400 10px/1.4 var(--gf-ui);\n  color: var(--gf-muted);\n}\n\n.gram-frame-style-targeting .gram-frame-style-footer-note {\n  color: var(--gf-accent-100);\n}\n\n.gram-frame-style-delete {\n  margin-left: auto;\n  height: 20px;\n  padding: 0 8px;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 4px;\n  color: var(--gf-muted);\n  font: 400 9.5px var(--gf-ui);\n  white-space: nowrap;\n  cursor: pointer;\n}\n\n.gram-frame-style-delete:hover {\n  border-color: var(--gf-danger-border);\n  color: var(--gf-danger-text);\n}\n\n/* --- Column 5: the annotation tables ------------------------------------- */\n\n.gram-frame-tables {\n  flex: 1;\n  min-width: 0;\n  display: flex;\n}\n\n.gram-frame-table-column {\n  flex: 1;\n  min-width: 0;\n  display: flex;\n  flex-direction: column;\n  border-right: 1px solid var(--gf-divider);\n}\n\n.gram-frame-table-column:last-child {\n  border-right: 0;\n}\n\n.gram-frame-panel-header {\n  display: flex;\n  align-items: center;\n  gap: 7px;\n  flex: none;\n  height: 28px;\n  padding: 0 10px;\n  box-sizing: border-box;\n  border-bottom: 1px solid var(--gf-divider);\n}\n\n.gram-frame-panel-header h4 {\n  margin: 0;\n  font: 600 10px/1 var(--gf-ui);\n  letter-spacing: 0.1em;\n  color: var(--gf-text);\n  text-transform: uppercase;\n  white-space: nowrap;\n  overflow: hidden;\n  text-overflow: ellipsis;\n}\n\n/* How many there are, hidden at zero: a chip reading \"0\" is noise beside an\n   empty state that already says so. */\n.gram-frame-count-chip {\n  flex: none;\n  padding: 3px 6px;\n  border-radius: 8px;\n  background: var(--gf-accent-900);\n  color: var(--gf-accent-200);\n  font: 500 9.5px/1 var(--gf-mono);\n}\n\n.gram-frame-harmonics-button-container {\n  margin-left: auto;\n  flex-shrink: 0;\n}\n\n.gram-frame-manual-button {\n  height: 20px;\n  padding: 0 8px;\n  background: transparent;\n  border: 1px solid var(--gf-accent-700);\n  border-radius: 4px;\n  color: var(--gf-accent-200);\n  font: 500 9.5px var(--gf-ui);\n  letter-spacing: 0.05em;\n  text-transform: uppercase;\n  white-space: nowrap;\n  cursor: pointer;\n}\n\n.gram-frame-manual-button:hover {\n  background: var(--gf-accent-900);\n}\n\n/*\n * Fixed-height home for one of the three tables.\n *\n * It claims the column's remaining height (flex: 1) but contributes nothing to\n * the layout's intrinsic height, because its only child is absolutely\n * positioned. That is what keeps the panels a constant size however many rows\n * they hold: the tables can no longer push the control row taller (untidy\n * layout) nor steal vertical space from an expanded spectrogram image.\n */\n.gram-frame-table-area {\n  position: relative;\n  flex: 1 1 auto;\n  min-height: 0;\n}\n\n/* The scrollport. `scrollbar-gutter: stable` reserves the scrollbar's width\n   whether or not there is anything to scroll, so the columns do not all shift\n   sideways the moment a table gains its eighth row. It replaces a permanent\n   `overflow-y: scroll`, which reserved the same space by painting a track over\n   an empty table. */\n.gram-frame-table-container {\n  position: absolute;\n  inset: 0;\n  overflow-y: auto;\n  overflow-x: hidden;\n  scrollbar-gutter: stable;\n  scrollbar-width: thin;\n  scrollbar-color: var(--gf-hairline) transparent;\n}\n\n.gram-frame-table-container::-webkit-scrollbar {\n  width: 8px;\n}\n\n.gram-frame-table-container::-webkit-scrollbar-track {\n  background: transparent;\n}\n\n.gram-frame-table-container::-webkit-scrollbar-thumb {\n  background: var(--gf-hairline);\n  border-radius: 4px;\n}\n\n.gram-frame-table-container::-webkit-scrollbar-thumb:hover {\n  background: rgba(247, 247, 250, 0.3);\n}\n\n.gram-frame-table {\n  width: 100%;\n  border-collapse: collapse;\n  table-layout: fixed;\n  font-family: var(--gf-ui);\n}\n\n.gram-frame-table th {\n  position: sticky;\n  top: 0;\n  z-index: 1;\n  padding: 6px 4px 4px;\n  background: var(--gf-surface);\n  font: 600 9.5px/1 var(--gf-mono);\n  letter-spacing: 0.08em;\n  color: var(--gf-muted);\n  text-transform: uppercase;\n  text-align: left;\n  white-space: nowrap;\n}\n\n.gram-frame-table td {\n  padding: 6px 4px;\n  font: 400 11.5px var(--gf-ui);\n  color: var(--gf-text);\n  font-variant-numeric: tabular-nums;\n  border-top: 1px solid var(--gf-row-line);\n  overflow: hidden;\n  text-overflow: ellipsis;\n  white-space: nowrap;\n}\n\n.gram-frame-table th:first-child,\n.gram-frame-table td:first-child {\n  padding-left: 10px;\n}\n\n.gram-frame-table th:last-child,\n.gram-frame-table td:last-child {\n  padding-right: 10px;\n}\n\n/* Numbers right-align so their digits line up down the column; the units and\n   ordinals beside them are quieter than the figure they qualify. */\n.gram-frame-table th:nth-child(3),\n.gram-frame-table th:nth-child(4),\n.gram-frame-cell-numeric {\n  text-align: right;\n}\n\n.gram-frame-table td.gram-frame-cell-numeric {\n  color: var(--gf-secondary);\n}\n\n.gram-frame-cell-unit {\n  font-size: 9.5px;\n  color: var(--gf-muted);\n}\n\n.gram-frame-cell-action {\n  text-align: right;\n}\n\n.gram-frame-table tbody tr {\n  cursor: pointer;\n}\n\n.gram-frame-table tbody tr:hover td {\n  background: var(--gf-row-hover);\n}\n\n/*\n * The selected row is reversed out whole — light ground, dark ink.\n *\n * It used to be an accent border, which collided with the feature colours the\n * rows themselves carry: a green-bordered row holding a green marker said two\n * things at once. Inversion survives any feature colour, and reads at a glance\n * from the far side of the panel.\n */\n.gram-frame-table tbody tr.gram-frame-selected-row td,\n.gram-frame-table tbody tr.gram-frame-selected-row:hover td {\n  background: var(--gf-text);\n  color: var(--gf-bg);\n  font-weight: 500;\n}\n\n.gram-frame-table tbody tr.gram-frame-selected-row .gram-frame-marker-delete-btn,\n.gram-frame-table tbody tr.gram-frame-selected-row .gram-frame-harmonic-delete,\n.gram-frame-table tbody tr.gram-frame-selected-row .gram-frame-sideband-delete {\n  color: #4a4c56;\n}\n\n/* Instructional, not blank: an empty rectangle says only that nothing is\n   there, never what to do about it. */\n.gram-frame-table-empty td {\n  padding: 14px 10px;\n  border-top: 0;\n  font: 400 11px var(--gf-ui);\n  color: var(--gf-muted);\n  white-space: normal;\n  cursor: default;\n}\n\n.gram-frame-table-empty:hover td {\n  background: transparent;\n}\n\n.gram-frame-marker-label-cell,\n.gram-frame-marker-label-text {\n  overflow: hidden;\n  text-overflow: ellipsis;\n  white-space: nowrap;\n}\n\n.gram-frame-marker-color,\n.gram-frame-harmonic-color,\n.gram-frame-sideband-color {\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  width: 20px;\n  height: 16px;\n}\n\n.gram-frame-marker-delete-btn,\n.gram-frame-harmonic-delete,\n.gram-frame-sideband-delete {\n  padding: 0;\n  background: none;\n  border: 0;\n  color: var(--gf-muted);\n  font: 400 13px/1 var(--gf-ui);\n  cursor: pointer;\n}\n\n.gram-frame-marker-delete-btn:hover,\n.gram-frame-harmonic-delete:hover,\n.gram-frame-sideband-delete:hover {\n  color: var(--gf-danger-text);\n}\n\n/* The sidebands column's foot. Sideband sets are rare, so this is the space the\n   panel has going spare — and clearing annotations is not a view control, so it\n   is not in the mode rail beside zoom and fit. */\n.gram-frame-tables-footer {\n  flex: none;\n  padding: 8px 10px;\n  border-top: 1px solid var(--gf-divider);\n  background: var(--gf-recess);\n}\n\n.gram-frame-clear-btn {\n  width: 100%;\n  height: 26px;\n  background: transparent;\n  border: 1px solid var(--gf-hairline);\n  border-radius: 5px;\n  color: var(--gf-secondary);\n  font: 400 10.5px var(--gf-ui);\n  letter-spacing: 0.04em;\n  white-space: nowrap;\n  cursor: pointer;\n}\n\n.gram-frame-clear-btn:hover {\n  border-color: var(--gf-danger-border);\n  color: var(--gf-danger-text);\n}\n\n/* --- Responsive ----------------------------------------------------------\n * The panel is designed for a full-width embed (~1400px). Below that the\n * annotation tables shrink first — they are the elastic column — and past the\n * point where they cannot, the guidance column gives up its width to them. The\n * three fixed columns never shrink: the instrument face and the tool list are\n * what the panel is for.\n * ------------------------------------------------------------------------- */\n@container gramframe-controls (max-width: 1180px) {\n  .gram-frame-guidance-column:not(.gram-frame-guidance-open) {\n    flex: 0 0 40px;\n    width: 40px;\n    align-items: center;\n    padding: 10px 0;\n    gap: 10px;\n  }\n\n  .gram-frame-guidance-column:not(.gram-frame-guidance-open) .gram-frame-guidance-header,\n  .gram-frame-guidance-column:not(.gram-frame-guidance-open) .gram-frame-guidance {\n    display: none;\n  }\n\n  .gram-frame-guidance-column:not(.gram-frame-guidance-open) .gram-frame-guidance-rail {\n    display: flex;\n  }\n}\n\n/* Marker rendering styles */\n.gram-frame-marker-line {\n  opacity: 0.8;\n}\n\n.gram-frame-marker-point {\n  opacity: 0.9;\n}\n\n/*\n * A marker's on-gram label. Legibility comes from the white rounded plate drawn\n * behind it (issue #243) — the geometry and colours are presentation attributes\n * set by plateLabel(), see src/utils/labelPlate.js. Never a click target: the\n * marker underneath is.\n */\n.gram-frame-marker-label {\n  font-family: Arial, sans-serif;\n  font-size: 12px;\n  font-weight: bold;\n  pointer-events: none;\n  user-select: none;\n}\n\n/*\n * The white plate behind any on-gram label, and the group holding the two. Both\n * are transparent to the pointer so the plate never intercepts a click meant\n * for the feature it annotates, or for the gram beneath it.\n */\n.gram-frame-label-plate,\n.gram-frame-label-plated {\n  pointer-events: none;\n}\n\n/*\n * The selected feature, on the gram.\n *\n * Two treatments, for the two kinds of thing a feature is made of. Its geometry\n * gets a halo — a wider, translucent white copy drawn beneath it by\n * src/rendering/selectionHalo.js, which is geometry rather than style and so is\n * not expressible here. Its label gets the same inversion its table row gets:\n * dark plate, light text. A white glow behind a white plate would say nothing,\n * and inverting both places means selection reads as one idea.\n */\n.gram-frame-selection-halo {\n  pointer-events: none;\n}\n\n.gram-frame-selected-label .gram-frame-label-plate {\n  fill: var(--gf-bg);\n}\n\n.gram-frame-selected-label text {\n  fill: var(--gf-text);\n}\n\n/* Storage-failure banner — shown inside the component when a save or clear was\n   refused by browser storage (quota, private browsing). Non-blocking: it sits\n   above the controls, wraps rather than clips, and can be dismissed. */\n.gram-frame-storage-warning {\n  box-sizing: border-box;\n  display: flex;\n  align-items: flex-start;\n  gap: 8px;\n  margin: 0 0 8px 0;\n  padding: 8px 10px;\n  background-color: #fff8e1;\n  border: 1px solid #f0ad4e;\n  border-radius: 4px;\n  color: #663c00;\n  font-family: Arial, Helvetica, sans-serif;\n  font-size: 13px;\n  line-height: 1.4;\n  overflow-wrap: break-word;\n  word-wrap: break-word;\n}\n\n.gram-frame-storage-warning-message {\n  flex: 1 1 auto;\n  min-width: 0;\n}\n\n.gram-frame-storage-warning-dismiss {\n  flex: 0 0 auto;\n  padding: 0 4px;\n  background: none;\n  border: none;\n  color: #663c00;\n  font-size: 16px;\n  line-height: 1;\n  cursor: pointer;\n}\n\n.gram-frame-storage-warning-dismiss:hover {\n  color: #a06000;\n}\n\n/* Legacy-browser compatibility warning — shown in place of the component when\n   the browser lacks a required JS/DOM API. Kept legible even in small\n   containers (min sizing, word wrapping) so it is never clipped to nothing. */\n.gram-frame-compat-warning {\n  box-sizing: border-box;\n  display: block;\n  min-width: 0;\n  max-width: 100%;\n  margin: 10px 0;\n  padding: 16px 20px;\n  background-color: #fff8e1;\n  border: 2px solid #f0ad4e;\n  border-radius: 4px;\n  color: #663c00;\n  font-family: Arial, Helvetica, sans-serif;\n  font-size: 14px;\n  line-height: 1.5;\n  overflow-wrap: break-word;\n  word-wrap: break-word;\n}\n\n.gram-frame-compat-warning-heading {\n  display: block;\n  margin-bottom: 6px;\n  font-size: 15px;\n}\n\n.gram-frame-compat-warning-message {\n  margin: 0;\n}\n\n/* Frequency-rate input UI styles removed - the backend value is preserved */\n\n/* SVG cursor styles removed - using CSS cursor only */\n\n/* SVG Harmonic line styles */\n\n\n.gram-frame-harmonic-line,\n.gram-frame-harmonic-mini-pin,\n.gram-frame-sideband-line,\n.gram-frame-sideband-mini-pin {\n  stroke-width: 2;\n  fill: none;\n  pointer-events: none;\n  stroke-linecap: round;\n}\n\n\n.gram-frame-harmonic-number,\n.gram-frame-sideband-number {\n  font-family: Arial, sans-serif;\n  font-size: 12px;\n  font-weight: bold;\n  pointer-events: none;\n  /*\n   * Legibility comes from the white rounded plate drawn behind the digits\n   * (issue #243), set as presentation attributes by plateLabel() in\n   * src/utils/labelPlate.js. No drop-shadow: it only blurs the plate's edge.\n   */\n}\n\n/* SVG Harmonic Set styles (new system) */\n\n.gram-frame-harmonic-set-line {\n  stroke-width: 2;\n  fill: none;\n  pointer-events: auto !important;\n  /*cursor: grab !important;*/\n  stroke-linecap: round;\n}\n\n.gram-frame-harmonic-set-line:hover {\n  stroke-width: 3;\n  /* cursor: grab !important; */\n}\n\n.gram-frame-harmonic-set-line:active {\n  cursor: grabbing !important;\n}\n\n/* Legacy harmonic styles (for backward compatibility) */\n.gram-frame-harmonic {\n  position: absolute;\n  height: 1px;\n  background-color: rgba(255, 255, 0, 0.7);\n  pointer-events: none;\n}\n\n\n\n/* Debug grid */\n\n/* Canvas boundary overlay */\n\n/* Message display */\n\n/* Error state */\n.gram-frame-error {\n  padding: 10px;\n  background-color: #f8d7da;\n  color: #721c24;\n  border: 1px solid #f5c6cb;\n  border-radius: 4px;\n  margin: 10px 0;\n}\n\n/* The colour/symbol swatch each pin-set row leads with. A fixed box so the\n   first column's width does not depend on which symbol a set happens to\n   carry. */\n.gram-frame-harmonic-symbol-swatch {\n  display: block;\n}\n\n/* Doppler mode styles */\n.gram-frame-doppler-fPlus {\n  pointer-events: auto;\n}\n\n.gram-frame-doppler-fMinus {\n  pointer-events: auto;\n}\n\n.gram-frame-doppler-crosshair {\n  pointer-events: auto;\n}\n\n.gram-frame-doppler-curve {\n  pointer-events: none;\n}\n\n/*\n * The vertical extensions are drawn after the f+/f- dots, so while they were\n * hit-testable they sat on top of the very markers the analyst was aiming at.\n * Doppler hit-testing is done in data space against the marker positions, not\n * by hitting an element, so nothing needs these to be targets.\n */\n.gram-frame-doppler-extension {\n  pointer-events: none;\n}\n\n.gram-frame-doppler-guide {\n  pointer-events: none;\n}\n\n.gram-frame-doppler-label {\n  pointer-events: none;\n  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;\n}\n\n/* Modal dialog styles */\n.gram-frame-modal-overlay {\n  position: fixed;\n  top: 0;\n  left: 0;\n  width: 100%;\n  height: 100%;\n  background: rgba(0, 0, 0, 0.7);\n  display: flex;\n  justify-content: center;\n  align-items: center;\n  z-index: 1000;\n}\n\n.gram-frame-modal {\n  background: linear-gradient(180deg, #3a3a3a 0%, #2a2a2a 50%, #1a1a1a 100%);\n  border: 2px solid #555;\n  border-radius: 8px;\n  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);\n  min-width: 350px;\n  max-width: 500px;\n  color: #ddd;\n}\n\n.gram-frame-modal-header {\n  padding: 15px 20px;\n  border-bottom: 1px solid #444;\n  background: linear-gradient(180deg, #444 0%, #333 100%);\n  border-radius: 6px 6px 0 0;\n}\n\n.gram-frame-modal-header h3 {\n  margin: 0;\n  font-size: 16px;\n  color: #fff;\n  text-align: center;\n}\n\n.gram-frame-modal-body {\n  padding: 20px;\n}\n\n.gram-frame-modal-input-group {\n  display: flex;\n  flex-direction: column;\n  gap: 8px;\n}\n\n.gram-frame-modal-input-group label {\n  font-weight: bold;\n  color: #ccc;\n  font-size: 14px;\n}\n\n.gram-frame-modal-input-group input {\n  padding: 10px 12px;\n  border: 2px solid #555;\n  border-radius: 4px;\n  background: linear-gradient(180deg, #2a2a2a 0%, #1a1a1a 100%);\n  color: #fff;\n  font-size: 14px;\n  font-family: 'Courier New', monospace;\n}\n\n.gram-frame-modal-input-group input:focus {\n  outline: none;\n  border-color: #777;\n  box-shadow: 0 0 4px rgba(119, 119, 119, 0.3);\n}\n\n.gram-frame-modal-error {\n  color: #ff6b6b;\n  font-size: 12px;\n  margin-top: 4px;\n}\n\n/* Supporting note under a modal input (e.g. how to clear a marker label) */\n.gram-frame-modal-hint {\n  color: #999;\n  font-size: 11px;\n}\n\n.gram-frame-modal-footer {\n  padding: 15px 20px;\n  border-top: 1px solid #444;\n  display: flex;\n  justify-content: flex-end;\n  gap: 10px;\n  background: linear-gradient(180deg, #2a2a2a 0%, #1a1a1a 100%);\n  border-radius: 0 0 6px 6px;\n}\n\n.gram-frame-modal-btn {\n  padding: 8px 16px;\n  border: 2px solid #555;\n  border-radius: 4px;\n  cursor: pointer;\n  font-weight: bold;\n  font-size: 12px;\n  transition: all 0.1s ease;\n  min-width: 80px;\n}\n\n.gram-frame-modal-cancel {\n  background: linear-gradient(180deg, #6a4a4a 0%, #4a2a2a 50%, #2a1a1a 100%);\n  color: #ffaaaa;\n}\n\n.gram-frame-modal-cancel:hover {\n  background: linear-gradient(180deg, #7a5a5a 0%, #5a3a3a 50%, #3a2a2a 100%);\n}\n\n.gram-frame-modal-add {\n  background: linear-gradient(180deg, #4a6a4a 0%, #2a4a2a 50%, #1a2a1a 100%);\n  color: #aaffaa;\n}\n\n.gram-frame-modal-add:hover {\n  background: linear-gradient(180deg, #5a7a5a 0%, #3a5a3a 50%, #2a3a2a 100%);\n}\n\n.gram-frame-modal-add:disabled {\n  background: linear-gradient(180deg, #444 0%, #333 50%, #222 100%);\n  color: #666;\n  cursor: not-allowed;\n}\n\n.gram-frame-modal-btn:active:not(:disabled) {\n  transform: translateY(1px);\n}\n\n/* Zoom controls removed - now integrated into pan mode command buttons */\n\n/*\n * The persistent panels' containers: each fills its column and lets its table\n * scroll rather than growing the row.\n */\n.gram-frame-markers-persistent-container,\n.gram-frame-harmonics-persistent-container,\n.gram-frame-sidebands-persistent-container {\n  display: flex;\n  flex-direction: column;\n  flex: 1;\n  min-height: 0;\n}\n\n/* Selected Doppler marker highlighting */\n.gram-frame-selected-doppler-marker {\n  stroke: #4a8a4a !important;\n  stroke-width: 3 !important;\n  filter: drop-shadow(0 0 8px rgba(74, 138, 74, 0.6)) !important;\n}\n\n.gram-frame-selected-doppler-marker[fill] {\n  fill: #4a8a4a !important;\n  stroke: #aaffaa !important;\n}\n\n/* Region zoom (spec 170) --------------------------------------------------- */\n\n/* While Shift is held over the gram, the cursor advertises that a region\n   selection is available (FR-021). `!important` because the active mode writes\n   `style.cursor` on the same element every mousemove, and an inline value would\n   otherwise win whichever ran last. */\n.gram-frame-svg.gram-frame-region-ready {\n  cursor: zoom-in !important;\n}\n\n/* The gram outside the selection, dimmed so the target region reads as the\n   subject (FR-004). One even-odd-filled path: the outer subpath is the\n   selectable area, the inner one the selection. */\n.gram-frame-region-dim {\n  fill: #000;\n  fill-opacity: 0.45;\n  pointer-events: none;\n}\n\n/* The rubber band itself: a plain white outline, which reads cleanly because\n   everything outside the resulting view is dimmed. */\n.gram-frame-region-box {\n  fill: none;\n  stroke: #fff;\n  stroke-width: 1.5;\n  pointer-events: none;\n}\n\n/* What will actually be on screen after the zoom: the selection grown on\n   whichever axis is the looser fit. Dashed and dimmer, so it reads as a\n   consequence of the solid box rather than as a second thing to aim. Hidden\n   when it coincides with the selection. */\n.gram-frame-region-view {\n  fill: none;\n  stroke: #fff;\n  stroke-opacity: 0.65;\n  stroke-width: 1;\n  stroke-dasharray: 5 4;\n  pointer-events: none;\n}\n\n.gram-frame-region-selection {\n  pointer-events: none;\n}\n\n/* Icon buttons (issue #310) ------------------------------------------------ */\n\n/* The glyph inherits the button's colour, so it follows it through hover,\n   active and disabled exactly as a word would. */\n.gram-frame-icon {\n  width: 18px;\n  height: 18px;\n  display: block;\n  color: inherit;\n  pointer-events: none;\n}\n\n.gram-frame-icon-btn {\n  display: flex;\n  align-items: center;\n  justify-content: center;\n}\n\n/* A mode button's height comes from its line of text; a glyph is taller than\n   that, so the padding comes back off to keep Pan's row level with the four\n   word rows below it. */\n.gram-frame-mode-btn.gram-frame-icon-btn {\n  padding: 3px 6px;\n}\n\n/* The word an icon stands for: gone from the page, present in the accessibility\n   tree, and still the button's accessible name. */\n.gram-frame-visually-hidden {\n  position: absolute;\n  width: 1px;\n  height: 1px;\n  margin: -1px;\n  padding: 0;\n  overflow: hidden;\n  clip-path: inset(50%);\n  white-space: nowrap;\n  border: 0;\n}\n";
  document.head.appendChild(style);

  "use strict";
  const VERSION = "0.3.0";
  function getVersion() {
    return VERSION;
  }
  const initialState = {
    version: getVersion(),
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    instanceId: "",
    mode: "pan",
    // 'analysis', 'harmonics', 'sideband', 'doppler', 'pan' — start in pan so a click doesn't immediately place a marker
    previousMode: null,
    // Previous mode for switching back
    frequencyRate: 1,
    // Frequency divider, applied only by utils/coordinates.js; the player carries its own playbackRate
    selectedColor: "#ff6b6b",
    // Currently selected color for new features across all modes
    selectedSymbol: "cross",
    // Currently selected symbol; 'cross' (default) means no drawn symbol shape (feature 161)
    // Whether the NEXT created harmonic set draws its vertical pin lines. Shown
    // as a toggle in the style panel; on by default at the start of a browser
    // session and remembered (sessionStorage) for the rest of it.
    showHarmonicPin: true,
    // EXPERIMENT (temporary): large-symbol size for the NEXT created feature, set
    // from the style panel's toggle when nothing is selected (with a feature
    // selected, the toggle resizes that feature instead). In-memory only, default
    // off, never persisted — it exists to gather feedback on the preferred size.
    largeSymbols: false,
    cursorPosition: null,
    cursors: [],
    // Bumped by every path that mutates an annotation, so the storage listener
    // can tell an annotation change from a cursor move without re-serialising
    // the annotations on each notification (spec 166, AS-4.3).
    annotationRevision: 0,
    // Which annotations this tab has deleted, by id, with when.
    //
    // A deletion is the one annotation change that cannot be represented by the
    // record's contents: "absent" and "deleted" look identical, so a merge that
    // only unions what each tab still holds resurrects everything either tab has
    // ever removed. These are the tombstones that make deletion survive a merge
    // (issue #269). In-memory and persisted, pruned by age on save.
    tombstones: {
      markers: {},
      harmonicSets: {},
      sidebandSets: {},
      // A single curve, so a boolean-with-a-time rather than a map.
      doppler: null
    },
    imageDetails: {
      url: "",
      naturalWidth: 0,
      // Original dimensions of the image
      naturalHeight: 0,
      renderWidth: 0,
      // Base render width (defaults to naturalWidth on load)
      renderHeight: 0
      // Base render height (defaults to naturalHeight on load)
    },
    // Whether the image is currently expanded to fill available space.
    // In-memory only, default false, never persisted (independent of feature 155).
    imageExpanded: false,
    // Whether the per-mode guidance column is collapsed to its 40px rail.
    //
    // Chrome, not annotation: it is remembered per user (localStorage) rather
    // than saved with the gram's markers, so an analyst who works with the rail
    // closed keeps it closed on the next gram as well as the next visit.
    guidanceCollapsed: false,
    // Times an analyst has flagged on the transport's scrub track, oldest first.
    // Only meaningful on an audio-sourced instance; an empty array everywhere
    // else, so every listener sees one shape.
    bookmarks: [],
    config: {
      timeMin: 0,
      timeMax: 0,
      freqMin: 0,
      freqMax: 0
    },
    displayDimensions: {
      // Current display dimensions (responsive)
      width: 0,
      height: 0
    },
    margins: {
      left: 60,
      // Space for time axis labels
      bottom: 50,
      // Space for frequency axis labels  
      right: 15,
      // Small right margin
      top: 15
      // Small top margin
    },
    // Simple zoom state for transform-based zoom
    zoom: {
      level: 1,
      // Current zoom level (1.0 = no zoom, 2.0 = 2x zoom)
      centerX: 0.5,
      // Center point X (0-1 normalized)
      centerY: 0.5
      // Center point Y (0-1 normalized)
    },
    // Read-only projection of the active drag, rebuilt by the drag engine on each
    // transition. Modes never write it; it is always present, reading
    // `active: false` when idle (spec 166, FR-004 / data-model.md §2).
    drag: {
      active: false,
      kind: null,
      mode: null,
      targetId: null,
      targetType: null,
      startPosition: null
    },
    // Which of the style panel's two targets is armed: the defaults for the next
    // created feature, or the selected one. In-memory chrome, never persisted;
    // selecting a feature arms 'selected', clearing or switching mode returns it
    // to 'new'.
    styleTarget: "new",
    // Selection state for keyboard fine control
    selection: {
      selectedType: null,
      // 'marker' | 'harmonicSet' | null
      selectedId: null,
      // ID of selected item
      selectedIndex: null
      // Index in table for display purposes
    },
    // The spectrograph player (spec 168). A core slice rather than a mode's: it
    // describes what the instance is built on, as `imageDetails` does, not how
    // the analyst is interacting with it. Inert on image-backed instances so
    // every listener sees one shape.
    player: {
      active: false,
      ready: false,
      progress: 0,
      source: "",
      duration: 0,
      sampleRate: 0,
      channels: 0,
      playhead: 0,
      playing: false,
      ended: false,
      loop: false,
      playbackRate: 1,
      volume: 1,
      muted: false,
      viewTop: 0,
      windowSeconds: 10,
      // Assigned to the element explicitly rather than inherited, and settable
      // per exercise by `preserve-pitch` (spec 171, FR-021/FR-022).
      preservesPitch: true,
      // The contrast controls, 0..1 over the painted level scale (spec 171,
      // FR-009). View state like zoom: reset on reload, never persisted, never
      // part of an annotation record; {0, 1} is the image as it loaded.
      display: { floor: 0, ceiling: 1 },
      // What the render caps forced, or null on an ordinary load (FR-024).
      degraded: null,
      analysis: {
        fftSize: 1024,
        hopSize: 512,
        freqStart: 0,
        freqEnd: null,
        columns: 0,
        frames: 0,
        // How the analysed grid is turned into a picture. Every default here is
        // the painting the player already did — one frame per row, no background
        // normalisation, the 5th to 99.9th percentile of the whole file onto the
        // colour table, in colour — so a table naming none of them is unaffected.
        frameAverage: 1,
        normalisation: "none",
        normalisationWindow: null,
        levelFloor: 5,
        levelCeiling: 99.9,
        levelSpan: null,
        levelScope: "file",
        colourMap: "colour"
      }
    }
  };
  const globalStateListeners = [];
  function createInitialState(modeStates = {}) {
    const composed = { ...initialState };
    for (const [key, slice] of Object.entries(modeStates)) {
      if (!(key in composed)) {
        composed[key] = slice;
      }
    }
    return JSON.parse(JSON.stringify(composed));
  }
  function deliverToListeners(state, listeners) {
    const recipients = (listeners || []).slice();
    globalStateListeners.forEach((listener) => {
      if (!recipients.includes(listener)) {
        recipients.push(listener);
      }
    });
    if (recipients.length === 0) {
      return;
    }
    const stateCopy = JSON.parse(JSON.stringify(state));
    for (const listener of recipients) {
      try {
        listener(stateCopy);
      } catch (error) {
        console.error("Error in state listener:", error);
      }
    }
  }
  function markAnnotationsChanged(instance) {
    if (instance && instance.state) {
      instance.state.annotationRevision = (instance.state.annotationRevision || 0) + 1;
    }
  }
  function tombstoneBag(instance) {
    const { state } = instance || /** @type {any} */
    {};
    if (!state) {
      return null;
    }
    if (!state.tombstones) {
      state.tombstones = { markers: {}, harmonicSets: {}, sidebandSets: {}, doppler: null };
    }
    return state.tombstones;
  }
  function recordDeletion(instance, collection, id) {
    const bag = tombstoneBag(instance);
    if (bag && id) {
      bag[collection][id] = (/* @__PURE__ */ new Date()).toISOString();
    }
  }
  function recordDopplerDeletion(instance) {
    const bag = tombstoneBag(instance);
    if (bag) {
      bag.doppler = (/* @__PURE__ */ new Date()).toISOString();
    }
  }
  const pendingDispatches = /* @__PURE__ */ new WeakMap();
  function dispatch(instance, options = {}) {
    if (!instance) {
      return;
    }
    const wantsFrame = options.frame === true;
    const pending = pendingDispatches.get(instance);
    if (pending) {
      if (!wantsFrame && pending.tier === "frame") {
        if (pending.frameHandle !== null && typeof cancelAnimationFrame === "function") {
          cancelAnimationFrame(pending.frameHandle);
        }
        pending.tier = "microtask";
        pending.frameHandle = null;
        queueMicrotask(() => flushDispatch(instance));
      }
      return;
    }
    const record = { tier: wantsFrame ? "frame" : "microtask", frameHandle: null };
    pendingDispatches.set(instance, record);
    if (wantsFrame && typeof requestAnimationFrame === "function") {
      record.frameHandle = requestAnimationFrame(() => flushDispatch(instance));
    } else {
      record.tier = "microtask";
      queueMicrotask(() => flushDispatch(instance));
    }
  }
  function flushDispatch(instance) {
    if (!instance) {
      return;
    }
    const pending = pendingDispatches.get(instance);
    if (!pending) {
      return;
    }
    if (pending.frameHandle !== null && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(pending.frameHandle);
    }
    pendingDispatches.delete(instance);
    deliverToListeners(instance.state, instance.stateListeners);
  }
  function addGlobalStateListener(callback) {
    if (!globalStateListeners.includes(callback)) {
      globalStateListeners.push(callback);
      return true;
    }
    return false;
  }
  function removeGlobalStateListener(callback) {
    const index = globalStateListeners.indexOf(callback);
    if (index !== -1) {
      globalStateListeners.splice(index, 1);
      return true;
    }
    return false;
  }
  function getGlobalStateListeners() {
    return [...globalStateListeners];
  }
  function clearGlobalStateListeners() {
    globalStateListeners.length = 0;
  }
  const MODE_ROSTER = [
    // Every mode carries a glyph, drawn beside its word rather than in place of
    // it: in a rail of five stacked tools the shape is what the eye lands on
    // first, and the word is still there to settle it. The rail's own footer
    // (zoom out, zoom in, fit) is the place where a glyph replaces a word.
    { name: "pan", displayName: "Pan", icon: "hand" },
    // "Cross Cursor" on screen, `analysis` in the code and in stored records.
    // The two names have coexisted since before this review; renaming the button
    // is issue #271, not this one.
    { name: "analysis", displayName: "Cross Cursor", icon: "cross-cursor" },
    { name: "harmonics", displayName: "Harmonics", icon: "harmonics" },
    { name: "sideband", displayName: "Sidebands", icon: "sidebands" },
    { name: "doppler", displayName: "Doppler", icon: "doppler" }
  ];
  const MODE_NAMES = MODE_ROSTER.map((entry) => entry.name);
  function getModeDisplayName(mode) {
    const entry = MODE_ROSTER.find((candidate) => candidate.name === mode);
    if (entry) {
      return entry.displayName;
    }
    return typeof mode === "string" && mode.length > 0 ? mode.charAt(0).toUpperCase() + mode.slice(1) : String(mode);
  }
  function getModeIcon(mode) {
    var _a;
    return (_a = MODE_ROSTER.find((candidate) => candidate.name === mode)) == null ? void 0 : _a.icon;
  }
  function createLEDDisplay(label, value, unit, caption) {
    const led = document.createElement("div");
    led.className = "gram-frame-led";
    const labelDiv = document.createElement("div");
    labelDiv.className = "gram-frame-led-label gram-frame-visually-hidden";
    labelDiv.textContent = label;
    led.appendChild(labelDiv);
    if (caption) {
      const captionDiv = document.createElement("div");
      captionDiv.className = "gram-frame-led-caption";
      captionDiv.textContent = caption;
      led.appendChild(captionDiv);
    }
    const valueDiv = document.createElement("div");
    valueDiv.className = "gram-frame-led-value";
    valueDiv.textContent = value;
    led.appendChild(valueDiv);
    if (unit) {
      const unitDiv = document.createElement("div");
      unitDiv.className = "gram-frame-led-unit";
      unitDiv.textContent = unit;
      led.appendChild(unitDiv);
    }
    return led;
  }
  function setLEDValue(led, value) {
    const valueDiv = led.querySelector(".gram-frame-led-value");
    if (valueDiv) {
      valueDiv.textContent = value;
    }
  }
  function updateLEDDisplays(instance, state) {
    if (instance.ui.modeLED) {
      setLEDValue(instance.ui.modeLED, getModeDisplayName(state.mode));
    }
    if (instance.ui.frequencyRateLED) {
      setLEDValue(instance.ui.frequencyRateLED, `${state.frequencyRate}`);
    }
  }
  const COLOR_PALETTE = [
    "#ff0000",
    // Red
    "#ff8000",
    // Orange
    "#ffff00",
    // Yellow
    "#80ff00",
    // Yellow-green
    "#00ff00",
    // Green
    "#00ff80",
    // Green-cyan
    "#00ffff",
    // Cyan
    "#0080ff",
    // Cyan-blue
    "#0000ff",
    // Blue
    "#8000ff",
    // Blue-purple
    "#ff00ff",
    // Purple
    "#ff0080"
    // Purple-red
  ];
  function createColorSlider(instance, onPick) {
    const state = instance.state;
    const container = document.createElement("div");
    container.className = "gram-frame-color-slider";
    const canvas = document.createElement("canvas");
    canvas.width = 140;
    canvas.height = 20;
    canvas.className = "gram-frame-color-canvas";
    container.appendChild(canvas);
    if (!state.selectedColor) {
      state.selectedColor = "#ff6b6b";
    }
    drawColorPalette(canvas);
    const indicator = document.createElement("div");
    indicator.className = "gram-frame-color-indicator";
    container.appendChild(indicator);
    canvas.addEventListener("click", (event) => {
      const rect2 = canvas.getBoundingClientRect();
      const x = event.clientX - rect2.left;
      const scaleX = canvas.width / rect2.width;
      const canvasX = x * scaleX;
      const color = getColorFromPosition(canvasX, canvas.width);
      const apply = instance.interaction.applyColorToSelectedFeature;
      if (!apply || !apply(color)) {
        state.selectedColor = color;
        dispatch(instance);
      }
      updateIndicatorPosition(indicator, canvasX, canvas.width);
      onPick(color);
    });
    const control = {
      setValue(color) {
        updateIndicatorPosition(indicator, getPositionFromColor(color, canvas.width), canvas.width);
      }
    };
    control.setValue(state.selectedColor);
    return { element: container, control };
  }
  function drawColorPalette(canvas) {
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    const width = canvas.width;
    const height = canvas.height;
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    COLOR_PALETTE.forEach((color, index) => {
      gradient.addColorStop(index / (COLOR_PALETTE.length - 1), color);
    });
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
  }
  function getColorFromPosition(x, width) {
    const position = Math.max(0, Math.min(1, x / width));
    const segmentSize = 1 / (COLOR_PALETTE.length - 1);
    const segmentIndex = position / segmentSize;
    const lowerIndex = Math.floor(segmentIndex);
    const upperIndex = Math.min(lowerIndex + 1, COLOR_PALETTE.length - 1);
    const t = segmentIndex - lowerIndex;
    if (lowerIndex === upperIndex) {
      return COLOR_PALETTE[lowerIndex];
    }
    const color1 = hexToRgb(COLOR_PALETTE[lowerIndex]);
    const color2 = hexToRgb(COLOR_PALETTE[upperIndex]);
    const r = Math.round(color1.r * (1 - t) + color2.r * t);
    const g = Math.round(color1.g * (1 - t) + color2.g * t);
    const b = Math.round(color1.b * (1 - t) + color2.b * t);
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  }
  function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return { r, g, b };
  }
  function getPositionFromColor(hexColor, width) {
    const targetRgb = hexToRgb(hexColor);
    let closestIndex = 0;
    let minDistance = Infinity;
    COLOR_PALETTE.forEach((color, index) => {
      const colorRgb = hexToRgb(color);
      const distance = Math.sqrt(
        Math.pow(targetRgb.r - colorRgb.r, 2) + Math.pow(targetRgb.g - colorRgb.g, 2) + Math.pow(targetRgb.b - colorRgb.b, 2)
      );
      if (distance < minDistance) {
        minDistance = distance;
        closestIndex = index;
      }
    });
    const segmentSize = 1 / (COLOR_PALETTE.length - 1);
    const position = closestIndex * segmentSize;
    return position * width;
  }
  function updateIndicatorPosition(indicator, x, width) {
    const percentage = x / width * 100;
    indicator.style.left = `${Math.max(0, Math.min(100, percentage))}%`;
  }
  const SVG_NS$6 = "http://www.w3.org/2000/svg";
  const DEFAULT_SYMBOL = "cross";
  const SYMBOL_CATALOG = ["cross", "circle", "square", "diamond", "triangle", "triangle-down", "star"];
  const SYMBOL_DISPLAY_NAMES = {
    "cross": "Cross (no symbol)",
    "circle": "Circle",
    "square": "Square",
    "diamond": "Diamond",
    "triangle": "Triangle",
    "triangle-down": "Triangle (down)",
    "star": "Star"
  };
  const LARGE_SYMBOL_SCALE = 2;
  function resolveSymbolScale(source) {
    return source && source.largeSymbols ? LARGE_SYMBOL_SCALE : 1;
  }
  function resolveSymbolType(symbolType) {
    return SYMBOL_CATALOG.includes(
      /** @type {SymbolType} */
      symbolType
    ) ? (
      /** @type {SymbolType} */
      symbolType
    ) : DEFAULT_SYMBOL;
  }
  function labelSitsBelowSymbol(symbolType) {
    return resolveSymbolType(symbolType) === "triangle";
  }
  function toPoints(pts) {
    return pts.map(([x, y]) => `${x},${y}`).join(" ");
  }
  function starPoints(cx, cy, outerR, innerR) {
    const pts = [];
    for (let i = 0; i < 10; i++) {
      const r = i % 2 === 0 ? outerR : innerR;
      const angle = -Math.PI / 2 + i * Math.PI / 5;
      pts.push([cx + r * Math.cos(angle), cy + r * Math.sin(angle)]);
    }
    return pts;
  }
  function isSymbolLess(symbolType) {
    return resolveSymbolType(symbolType) === "cross";
  }
  function createSymbolMark(symbolType, cx, cy, size, color) {
    const r = size / 2;
    const resolved = resolveSymbolType(symbolType);
    if (resolved === "cross") {
      return null;
    }
    let el;
    switch (resolved) {
      case "square": {
        el = document.createElementNS(SVG_NS$6, "rect");
        el.setAttribute("x", String(cx - r));
        el.setAttribute("y", String(cy - r));
        el.setAttribute("width", String(2 * r));
        el.setAttribute("height", String(2 * r));
        break;
      }
      case "diamond": {
        el = document.createElementNS(SVG_NS$6, "polygon");
        el.setAttribute("points", toPoints([
          [cx, cy - r],
          [cx + r, cy],
          [cx, cy + r],
          [cx - r, cy]
        ]));
        break;
      }
      case "triangle": {
        el = document.createElementNS(SVG_NS$6, "polygon");
        el.setAttribute("points", toPoints([
          [cx, cy - r],
          [cx + r, cy + r],
          [cx - r, cy + r]
        ]));
        break;
      }
      case "triangle-down": {
        el = document.createElementNS(SVG_NS$6, "polygon");
        el.setAttribute("points", toPoints([
          [cx, cy + r],
          [cx + r, cy - r],
          [cx - r, cy - r]
        ]));
        break;
      }
      case "star": {
        el = document.createElementNS(SVG_NS$6, "polygon");
        el.setAttribute("points", toPoints(starPoints(cx, cy, r, r * 0.5)));
        break;
      }
      case "circle":
      default: {
        el = document.createElementNS(SVG_NS$6, "circle");
        el.setAttribute("cx", String(cx));
        el.setAttribute("cy", String(cy));
        el.setAttribute("r", String(r));
        break;
      }
    }
    el.setAttribute("class", "gram-frame-harmonic-symbol");
    el.setAttribute("data-symbol", resolved);
    el.setAttribute("fill", color);
    return el;
  }
  function createColorIndicator(symbol, color, size = 16) {
    const mark = createSymbolMark(symbol, size / 2, size / 2, size * 0.75, color);
    if (mark) {
      const svg = document.createElementNS(SVG_NS$6, "svg");
      svg.setAttribute("class", "gram-frame-symbol-swatch");
      svg.setAttribute("width", String(size));
      svg.setAttribute("height", String(size));
      svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
      svg.appendChild(mark);
      return svg;
    }
    const div = document.createElement("div");
    div.className = "gram-frame-color-swatch";
    div.style.backgroundColor = color;
    div.style.width = `${size}px`;
    div.style.height = `${size}px`;
    div.style.borderRadius = "3px";
    div.style.border = "1px solid #ccc";
    return div;
  }
  function createSegmented(options, groupLabel, onChange) {
    const element = document.createElement("div");
    element.className = "gram-frame-segmented";
    element.setAttribute("role", "radiogroup");
    element.setAttribute("aria-label", groupLabel);
    const buttons = options.map((option) => {
      const button2 = document.createElement("button");
      button2.type = "button";
      button2.className = "gram-frame-segmented-option";
      button2.setAttribute("role", "radio");
      button2.setAttribute("aria-checked", "false");
      button2.textContent = option.label;
      button2.addEventListener("click", (event) => {
        event.preventDefault();
        if (!button2.disabled) {
          onChange(option.value);
        }
      });
      element.appendChild(button2);
      return button2;
    });
    return {
      element,
      setValue(value) {
        options.forEach((option, index) => {
          const chosen = option.value === value;
          buttons[index].classList.toggle("gram-frame-segmented-selected", chosen);
          buttons[index].setAttribute("aria-checked", chosen ? "true" : "false");
        });
      },
      setEnabled(enabled, reason) {
        element.classList.toggle("gram-frame-segmented-disabled", !enabled);
        element.title = enabled ? "" : reason || "";
        buttons.forEach((button2) => {
          button2.disabled = !enabled;
        });
      }
    };
  }
  function createSymbolSizeTrial(instance) {
    const state = instance.state;
    const segmented = createSegmented(
      [{ value: false, label: "Normal" }, { value: true, label: "Large" }],
      "Symbol size",
      (large) => {
        const apply = instance.interaction.applyLargeSymbolsToSelectedFeature;
        if (!apply || !apply(large)) {
          state.largeSymbols = large;
          dispatch(instance);
        }
        segmented.setValue(large);
        if (instance.interaction.syncStyleControls) {
          instance.interaction.syncStyleControls();
        }
      }
    );
    segmented.element.classList.add("gram-frame-large-symbols-toggle");
    segmented.element.title = `Trial: draw symbols at ${LARGE_SYMBOL_SCALE}× their normal size`;
    segmented.setValue(!!state.largeSymbols);
    return segmented.element;
  }
  const SYMBOL_GLYPHS = {
    "cross": "✕",
    "circle": "●",
    "square": "■",
    "diamond": "◆",
    "triangle": "▲",
    "triangle-down": "▼",
    "star": "★"
  };
  function createSymbolSelect(instance) {
    const state = instance.state;
    if (!state.selectedSymbol) {
      state.selectedSymbol = DEFAULT_SYMBOL;
    }
    const button2 = document.createElement("button");
    button2.type = "button";
    button2.className = "gram-frame-symbol-select";
    button2.title = "Symbol";
    button2.setAttribute("aria-label", "Symbol");
    button2.setAttribute("aria-haspopup", "true");
    button2.setAttribute("aria-expanded", "false");
    const glyph = document.createElement("span");
    glyph.className = "gram-frame-symbol-glyph";
    glyph.style.color = state.selectedColor;
    const name = document.createElement("span");
    name.className = "gram-frame-symbol-name";
    const caret = document.createElement("span");
    caret.className = "gram-frame-symbol-caret";
    caret.textContent = "▾";
    button2.appendChild(glyph);
    button2.appendChild(name);
    button2.appendChild(caret);
    let popup = null;
    const close = () => {
      if (!popup) {
        return;
      }
      popup.remove();
      popup = null;
      button2.setAttribute("aria-expanded", "false");
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("mousedown", onOutsideDown, true);
      button2.focus();
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        close();
      }
    };
    const onOutsideDown = (event) => {
      const target = (
        /** @type {Node|null} */
        event.target
      );
      if (popup && target && !popup.contains(target) && !button2.contains(target)) {
        close();
      }
    };
    button2.addEventListener("click", (event) => {
      event.preventDefault();
      if (popup) {
        close();
        return;
      }
      popup = buildPopup(instance, state, (chosen) => {
        applySymbol(instance, chosen);
        close();
      });
      instance.ui.container.appendChild(popup);
      placePopup(popup, button2, instance.ui.container);
      button2.setAttribute("aria-expanded", "true");
      document.addEventListener("keydown", onKeyDown, true);
      document.addEventListener("mousedown", onOutsideDown, true);
    });
    const control = {
      setValue(symbol) {
        const resolved = SYMBOL_GLYPHS[symbol] ? symbol : DEFAULT_SYMBOL;
        glyph.textContent = SYMBOL_GLYPHS[resolved];
        name.textContent = shortSymbolName(resolved);
        button2.title = SYMBOL_DISPLAY_NAMES[resolved];
        button2.dataset.symbol = resolved;
        if (popup) {
          markChosen(popup, resolved);
        }
      },
      setTint(color) {
        glyph.style.color = color;
        if (popup) {
          popup.style.setProperty("--gf-symbol-tint", color);
        }
      }
    };
    control.setValue(
      /** @type {SymbolType} */
      state.selectedSymbol
    );
    return { element: button2, control };
  }
  function placePopup(popup, button2, container) {
    const anchor = button2.getBoundingClientRect();
    const frame = container.getBoundingClientRect();
    const width = popup.offsetWidth;
    const left = Math.max(0, Math.min(anchor.left - frame.left, frame.width - width));
    popup.style.left = `${left}px`;
    popup.style.top = `${anchor.bottom - frame.top + 6}px`;
  }
  function symbolGlyph(symbol) {
    return SYMBOL_GLYPHS[
      /** @type {SymbolType} */
      symbol
    ] || SYMBOL_GLYPHS[DEFAULT_SYMBOL];
  }
  function shortSymbolName(symbol) {
    return SYMBOL_DISPLAY_NAMES[symbol].split(" (")[0];
  }
  function applySymbol(instance, symbol) {
    const state = instance.state;
    const apply = instance.interaction.applySymbolToSelectedFeature;
    if (!apply || !apply(symbol)) {
      state.selectedSymbol = symbol;
      dispatch(instance);
    }
    if (instance.interaction.syncStyleControls) {
      instance.interaction.syncStyleControls();
    }
  }
  function buildPopup(instance, state, onChoose) {
    const popup = document.createElement("div");
    popup.className = "gram-frame-symbol-popup";
    popup.style.setProperty("--gf-symbol-tint", state.selectedColor);
    const header = document.createElement("div");
    header.className = "gram-frame-symbol-popup-header";
    const kicker = document.createElement("div");
    kicker.className = "gram-frame-kicker";
    kicker.textContent = "Symbol";
    header.appendChild(kicker);
    popup.appendChild(header);
    const grid = document.createElement("div");
    grid.className = "gram-frame-symbol-grid";
    SYMBOL_CATALOG.forEach((symbolId) => {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "gram-frame-symbol-cell";
      cell.dataset.symbol = symbolId;
      cell.title = SYMBOL_DISPLAY_NAMES[symbolId];
      cell.setAttribute("aria-label", SYMBOL_DISPLAY_NAMES[symbolId]);
      cell.textContent = SYMBOL_GLYPHS[symbolId];
      cell.addEventListener("click", (event) => {
        event.preventDefault();
        onChoose(symbolId);
      });
      grid.appendChild(cell);
    });
    popup.appendChild(grid);
    const footer = document.createElement("div");
    footer.className = "gram-frame-symbol-popup-footer";
    const sizeLabel = document.createElement("div");
    sizeLabel.className = "gram-frame-style-group-label";
    sizeLabel.textContent = "Size";
    footer.appendChild(sizeLabel);
    footer.appendChild(createSymbolSizeTrial(instance));
    popup.appendChild(footer);
    markChosen(
      popup,
      /** @type {SymbolType} */
      state.selectedSymbol
    );
    return popup;
  }
  function markChosen(popup, symbol) {
    popup.querySelectorAll(".gram-frame-symbol-cell").forEach((cell) => {
      cell.classList.toggle(
        "gram-frame-symbol-cell-selected",
        /** @type {HTMLElement} */
        cell.dataset.symbol === symbol
      );
    });
  }
  const KEY_PREFIX$1 = "gramframe::";
  const PIN_PREF_KEY = `${KEY_PREFIX$1}pref::harmonicPin`;
  const GUIDANCE_PREF_KEY = `${KEY_PREFIX$1}pref::guidanceCollapsed`;
  function loadPinPreference() {
    try {
      const raw = sessionStorage.getItem(PIN_PREF_KEY);
      if (raw === "false") return false;
      return true;
    } catch (error) {
      console.warn("GramFrame: Could not read the harmonic-pin preference — using the default:", error);
      return true;
    }
  }
  function savePinPreference(showPin) {
    try {
      sessionStorage.setItem(PIN_PREF_KEY, showPin ? "true" : "false");
      return true;
    } catch (error) {
      console.warn("GramFrame: Could not save the harmonic-pin preference:", error);
      return false;
    }
  }
  function loadGuidancePreference() {
    try {
      const raw = localStorage.getItem(GUIDANCE_PREF_KEY);
      return raw === "true" ? true : raw === "false" ? false : null;
    } catch (error) {
      console.warn("GramFrame: Could not read the guidance preference — leaving it automatic:", error);
      return null;
    }
  }
  function saveGuidancePreference(collapsed) {
    try {
      localStorage.setItem(GUIDANCE_PREF_KEY, collapsed ? "true" : "false");
    } catch (error) {
      console.warn("GramFrame: Could not save the guidance preference:", error);
    }
  }
  const WARNING_CLASS = "gram-frame-storage-warning";
  function showStorageWarning(instance, message) {
    if (!instance || !instance.ui.container) {
      return null;
    }
    const existing = (
      /** @type {HTMLElement|null} */
      instance.ui.container.querySelector(`.${WARNING_CLASS}`)
    );
    if (existing) {
      const text2 = existing.querySelector(`.${WARNING_CLASS}-message`);
      if (text2) {
        text2.textContent = message;
      }
      return existing;
    }
    const banner = document.createElement("div");
    banner.className = WARNING_CLASS;
    banner.setAttribute("role", "status");
    banner.setAttribute("aria-live", "polite");
    const text = document.createElement("span");
    text.className = `${WARNING_CLASS}-message`;
    text.textContent = message;
    const dismiss = document.createElement("button");
    dismiss.type = "button";
    dismiss.className = `${WARNING_CLASS}-dismiss`;
    dismiss.textContent = "×";
    dismiss.title = "Dismiss";
    dismiss.setAttribute("aria-label", "Dismiss storage warning");
    dismiss.addEventListener("click", () => banner.remove());
    banner.appendChild(text);
    banner.appendChild(dismiss);
    instance.ui.container.insertBefore(banner, instance.ui.container.firstChild);
    return banner;
  }
  function clearStorageWarning(instance) {
    if (!instance || !instance.ui.container) {
      return;
    }
    const existing = instance.ui.container.querySelector(`.${WARNING_CLASS}`);
    if (existing) {
      existing.remove();
    }
  }
  function createPinToggle(instance) {
    const state = instance.state;
    const segmented = createSegmented(
      [{ value: true, label: "Tall" }, { value: false, label: "Mini" }],
      "Pin style",
      (showPin) => choosePinStyle(instance, showPin, segmented.setValue)
    );
    segmented.element.classList.add("gram-frame-pin-toggle");
    segmented.setValue(state.showHarmonicPin !== false);
    const control = {
      setValue(showPin) {
        segmented.setValue(showPin);
      },
      setEnabled(enabled) {
        segmented.setEnabled(enabled, "Tall pins apply to harmonic and sideband sets only");
      }
    };
    return { element: segmented.element, control };
  }
  function choosePinStyle(instance, showPin, show) {
    const state = instance.state;
    const apply = instance.interaction.applyPinToSelectedFeature;
    if (!apply || !apply(showPin)) {
      state.showHarmonicPin = showPin;
      if (savePinPreference(showPin)) {
        clearStorageWarning(instance);
      } else {
        showStorageWarning(instance, "The pin preference could not be saved — it applies to this page only.");
      }
      dispatch(instance);
    }
    show(showPin);
  }
  function findMarkerOwner(instance) {
    const owner = Object.values(instance.modes || {}).find((mode) => {
      const candidate = (
        /** @type {Partial<MarkerOwner>} */
        mode
      );
      return Array.isArray(candidate == null ? void 0 : candidate.markers) && typeof (candidate == null ? void 0 : candidate.removeMarker) === "function" && typeof (candidate == null ? void 0 : candidate.setMarkerLabel) === "function";
    });
    return (
      /** @type {MarkerOwner|null} */
      owner || null
    );
  }
  function isPinSetOwner(mode) {
    const candidate = (
      /** @type {Partial<PinSetOwner>} */
      mode
    );
    return typeof (candidate == null ? void 0 : candidate.updateSet) === "function" && typeof (candidate == null ? void 0 : candidate.removeSet) === "function" && typeof (candidate == null ? void 0 : candidate.nudgeFreqUpdates) === "function" && Array.isArray(candidate == null ? void 0 : candidate.sets);
  }
  function findPinSetOwner(instance, selectionType) {
    if (!selectionType) {
      return null;
    }
    const owner = Object.values(instance.modes || {}).filter(isPinSetOwner).find((mode) => mode.selectionType === selectionType);
    return owner || null;
  }
  function isPersistentFeatureProvider(mode) {
    const candidate = (
      /** @type {Partial<PersistentFeatureProvider>} */
      mode
    );
    return typeof (candidate == null ? void 0 : candidate.hasPersistentFeatures) === "function" && typeof (candidate == null ? void 0 : candidate.renderPersistentFeatures) === "function";
  }
  function isPanelOwner(mode) {
    const candidate = (
      /** @type {Partial<PanelOwner>} */
      mode
    );
    return typeof (candidate == null ? void 0 : candidate.refreshPanel) === "function";
  }
  function createTableColumn(className, title) {
    const column = document.createElement("div");
    column.className = `gram-frame-table-column ${className}`;
    const header = document.createElement("div");
    header.className = "gram-frame-panel-header";
    const heading = document.createElement("h4");
    heading.textContent = title;
    header.appendChild(heading);
    const count = document.createElement("span");
    count.className = "gram-frame-count-chip";
    count.hidden = true;
    header.appendChild(count);
    column.appendChild(header);
    return column;
  }
  function createAnnotationTables() {
    const tables = document.createElement("div");
    tables.className = "gram-frame-tables";
    const markersContainer = createTableColumn("gram-frame-markers-persistent-container", "Markers");
    const harmonicsContainer = createTableColumn("gram-frame-harmonics-persistent-container", "Harmonics");
    const harmonicsButtons = document.createElement("div");
    harmonicsButtons.className = "gram-frame-harmonics-button-container";
    const harmonicsHeader = harmonicsContainer.querySelector(".gram-frame-panel-header");
    if (harmonicsHeader) {
      harmonicsHeader.classList.add("gram-frame-harmonics-header");
      harmonicsHeader.appendChild(harmonicsButtons);
    }
    const sidebandsContainer = createTableColumn("gram-frame-sidebands-persistent-container", "Sidebands");
    tables.appendChild(markersContainer);
    tables.appendChild(harmonicsContainer);
    tables.appendChild(sidebandsContainer);
    return { tables, markersContainer, harmonicsContainer, sidebandsContainer };
  }
  function refreshTableCounts(instance) {
    const { analysis, harmonics, sidebands } = instance.state;
    const { markersContainer, harmonicsContainer, sidebandsContainer } = instance.ui;
    setCount(markersContainer, analysis ? analysis.markers.length : 0);
    setCount(harmonicsContainer, harmonics ? harmonics.harmonicSets.length : 0);
    setCount(sidebandsContainer, sidebands ? sidebands.sidebandSets.length : 0);
  }
  function setCount(container, count) {
    const chip = container ? container.querySelector(".gram-frame-count-chip") : null;
    if (!(chip instanceof HTMLElement)) {
      return;
    }
    chip.textContent = String(count);
    chip.hidden = count === 0;
  }
  function mountClearAllButton(instance, onClear) {
    const button2 = document.createElement("button");
    button2.type = "button";
    button2.className = "gram-frame-clear-btn";
    button2.textContent = "Clear all annotations";
    button2.title = "Remove every cross, harmonic set and sideband set";
    button2.addEventListener("click", (event) => {
      event.preventDefault();
      onClear();
    });
    const footer = document.createElement("div");
    footer.className = "gram-frame-tables-footer";
    footer.appendChild(button2);
    if (instance.ui.sidebandsContainer) {
      instance.ui.sidebandsContainer.appendChild(footer);
    }
  }
  function refreshPanels(instance) {
    Object.values(instance.modes).filter(isPanelOwner).forEach((mode) => mode.refreshPanel());
    refreshTableCounts(instance);
  }
  function commitAnnotationChange(instance, refreshPanel = null, dispatchOptions = void 0) {
    markAnnotationsChanged(instance);
    if (typeof refreshPanel === "function") {
      refreshPanel();
    }
    if (instance.featureRenderer) {
      instance.featureRenderer.renderAllPersistentFeatures();
    }
    dispatch(instance, dispatchOptions);
  }
  function renderSize(imageDetails) {
    return {
      width: imageDetails.renderWidth || imageDetails.naturalWidth,
      height: imageDetails.renderHeight || imageDetails.naturalHeight
    };
  }
  function getImageBounds(viewport, spectrogramImage = null) {
    const { margins, imageDetails } = viewport;
    const { width, height } = renderSize(imageDetails);
    if (spectrogramImage) {
      return {
        left: parseFloat(spectrogramImage.getAttribute("x") || String(margins.left)),
        top: parseFloat(spectrogramImage.getAttribute("y") || String(margins.top)),
        width: parseFloat(spectrogramImage.getAttribute("width") || String(width)),
        height: parseFloat(spectrogramImage.getAttribute("height") || String(height))
      };
    }
    return { left: margins.left, top: margins.top, width, height };
  }
  function getRenderDimensions(viewport) {
    const { width, height } = renderSize(viewport.imageDetails);
    return { renderWidth: width, renderHeight: height };
  }
  function dataFrequencyRange(viewport) {
    const { freqMin, freqMax } = viewport.config;
    const rate = viewport.frequencyRate || 1;
    return { freqMin: freqMin / rate, freqMax: freqMax / rate };
  }
  function calculateVisibleDataRange(viewport, spectrogramImage = null) {
    const { timeMin, timeMax } = viewport.config;
    const { freqMin, freqMax } = dataFrequencyRange(viewport);
    const { margins, zoom } = viewport;
    const { renderWidth, renderHeight } = getRenderDimensions(viewport);
    const stretched = viewport.imageDetails.timeStretch !== void 0;
    if (zoom.level === 1 && !stretched) {
      return { timeMin, timeMax, freqMin, freqMax };
    }
    const {
      left: imageLeft,
      top: imageTop,
      width: imageWidth,
      height: imageHeight
    } = getImageBounds(viewport, spectrogramImage);
    const visibleLeft = Math.max(0, margins.left - imageLeft);
    const visibleRight = Math.min(imageWidth, margins.left + renderWidth - imageLeft);
    const visibleTop = stretched ? margins.top - imageTop : Math.max(0, margins.top - imageTop);
    const visibleBottom = stretched ? margins.top + renderHeight - imageTop : Math.min(imageHeight, margins.top + renderHeight - imageTop);
    const freqRange = freqMax - freqMin;
    const timeRange = timeMax - timeMin;
    return {
      freqMin: freqMin + visibleLeft / imageWidth * freqRange,
      freqMax: freqMin + visibleRight / imageWidth * freqRange,
      timeMin: timeMax - visibleBottom / imageHeight * timeRange,
      timeMax: timeMax - visibleTop / imageHeight * timeRange
    };
  }
  function screenToSVG(screenX, screenY, svg) {
    const svgRect = svg.getBoundingClientRect();
    const viewBox = svg.viewBox.baseVal;
    if (viewBox && viewBox.width > 0 && viewBox.height > 0) {
      const scaleX = viewBox.width / svgRect.width;
      const scaleY = viewBox.height / svgRect.height;
      return {
        x: screenX * scaleX + viewBox.x,
        y: screenY * scaleY + viewBox.y
      };
    }
    return { x: screenX, y: screenY };
  }
  function svgToImage(svgX, svgY, viewport, spectrogramImage = null) {
    const bounds = getImageBounds(viewport, spectrogramImage);
    const { width, height } = renderSize(viewport.imageDetails);
    return {
      x: (svgX - bounds.left) * (width / bounds.width),
      y: (svgY - bounds.top) * (height / bounds.height)
    };
  }
  function imageToData(imageX, imageY, viewport) {
    const { config, imageDetails, frequencyRate } = viewport;
    const { freqMin, freqMax, timeMin, timeMax } = config;
    const { width, height } = renderSize(imageDetails);
    const rawFreq = freqMin + imageX / width * (freqMax - freqMin);
    const time = timeMax - imageY / height * (timeMax - timeMin);
    return { freq: rawFreq / frequencyRate, time };
  }
  function dataToSVG(dataPoint, viewport, spectrogramImage = null) {
    const { timeMin, timeMax } = viewport.config;
    const { freqMin, freqMax } = dataFrequencyRange(viewport);
    const bounds = getImageBounds(viewport, spectrogramImage);
    const freqRatio = (dataPoint.freq - freqMin) / (freqMax - freqMin);
    const timeRatio = (dataPoint.time - timeMin) / (timeMax - timeMin);
    return {
      x: bounds.left + freqRatio * bounds.width,
      y: bounds.top + (1 - timeRatio) * bounds.height
      // Invert Y
    };
  }
  function nudgeData(dataPoint, dx, dy, viewport, spectrogramImage = null) {
    const svgPoint = dataToSVG(dataPoint, viewport, spectrogramImage);
    const image = svgToImage(svgPoint.x + dx, svgPoint.y + dy, viewport, spectrogramImage);
    const clamped = clampToImage(image.x, image.y, viewport);
    return imageToData(clamped.x, clamped.y, viewport);
  }
  function isWithinImage(svgPoint, viewport, spectrogramImage = null) {
    const bounds = getImageBounds(viewport, spectrogramImage);
    const { width, height } = renderSize(viewport.imageDetails);
    const image = svgToImage(svgPoint.x, svgPoint.y, viewport, spectrogramImage);
    return svgPoint.x >= bounds.left && svgPoint.x <= bounds.left + bounds.width && svgPoint.y >= bounds.top && svgPoint.y <= bounds.top + bounds.height && image.x >= 0 && image.x <= width && image.y >= 0 && image.y <= height;
  }
  function clampToImage(imageX, imageY, viewport) {
    const { width, height } = renderSize(viewport.imageDetails);
    return {
      x: Math.max(0, Math.min(imageX, width)),
      y: Math.max(0, Math.min(imageY, height))
    };
  }
  function screenToData(clientX, clientY, svg, viewport, spectrogramImage = null) {
    const svgRect = svg.getBoundingClientRect();
    const svgPoint = screenToSVG(clientX - svgRect.left, clientY - svgRect.top, svg);
    const image = svgToImage(svgPoint.x, svgPoint.y, viewport, spectrogramImage);
    return {
      svg: svgPoint,
      image,
      data: imageToData(image.x, image.y, viewport)
    };
  }
  let currentFocusedInstance = null;
  const registeredInstances = /* @__PURE__ */ new Set();
  function pruneDisconnectedInstances() {
    for (const instance of Array.from(registeredInstances)) {
      if (!instance.ui || !instance.ui.container || !instance.ui.container.isConnected) {
        registeredInstances.delete(instance);
        if (currentFocusedInstance === instance) {
          currentFocusedInstance = null;
        }
      }
    }
  }
  function registerInstance(instance) {
    pruneDisconnectedInstances();
    registeredInstances.add(instance);
  }
  function unregisterInstance(instance) {
    registeredInstances.delete(instance);
    if (currentFocusedInstance === instance) {
      if (registeredInstances.size > 0) {
        const firstInstance = registeredInstances.values().next().value;
        if (firstInstance) {
          setFocusedInstance(firstInstance);
        }
      } else {
        currentFocusedInstance = null;
      }
    }
  }
  function getRegisteredInstanceCount() {
    pruneDisconnectedInstances();
    return registeredInstances.size;
  }
  function setFocusedInstance(instance) {
    if (currentFocusedInstance && currentFocusedInstance !== instance) {
      removeFocusIndicator(currentFocusedInstance);
    }
    currentFocusedInstance = instance;
    if (instance) {
      addFocusIndicator(instance);
    }
  }
  function getFocusedInstance() {
    pruneDisconnectedInstances();
    return currentFocusedInstance;
  }
  function clearFocusedInstance() {
    if (currentFocusedInstance) {
      removeFocusIndicator(currentFocusedInstance);
    }
    currentFocusedInstance = null;
  }
  function instanceContaining(node) {
    if (!(node instanceof Node)) {
      return null;
    }
    pruneDisconnectedInstances();
    return Array.from(registeredInstances).find(
      (instance) => !!(instance.ui && instance.ui.container && instance.ui.container.contains(node))
    ) || null;
  }
  function isNodeInsideAnyInstance(node) {
    return instanceContaining(node) !== null;
  }
  function addFocusIndicator(instance) {
    if (instance.ui.container) {
      instance.ui.container.classList.add("gram-frame-focused");
    }
  }
  function removeFocusIndicator(instance) {
    if (instance.ui.container) {
      instance.ui.container.classList.remove("gram-frame-focused");
    }
  }
  const HOVER_BRACKETS = [
    "M6 12V6h6",
    "M26 12V6h-6",
    "M6 20v6h6",
    "M26 20v6h-6"
  ];
  const DRAG_BRACKETS = [
    "M9 13V9h4",
    "M23 13V9h-4",
    "M9 19v4h4",
    "M23 19v4h-4"
  ];
  function bracketSvg(shapes, coreWidth, haloWidth) {
    const body = shapes.map((d) => `<path d="${d}"/>`).join("");
    return `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><g fill="none" stroke-linecap="round" stroke-linejoin="round"><g stroke="#000000" stroke-opacity="0.9" stroke-width="${haloWidth}">${body}</g><g stroke="#ffffff" stroke-width="${coreWidth}">${body}</g></g></svg>`;
  }
  function cursorValue(svg) {
    return `url("data:image/svg+xml,${encodeURIComponent(svg)}") 16 16, move`;
  }
  const IDLE_CURSOR = "crosshair";
  const FEATURE_HOVER_CURSOR = cursorValue(bracketSvg(HOVER_BRACKETS, 2, 4.4));
  const FEATURE_DRAG_CURSOR = cursorValue(bracketSvg(DRAG_BRACKETS, 2.6, 5));
  const PAN_IDLE_CURSOR = "grab";
  const PAN_DRAG_CURSOR = "grabbing";
  function featureCursor(phase) {
    if (phase === "drag") return FEATURE_DRAG_CURSOR;
    if (phase === "hover") return FEATURE_HOVER_CURSOR;
    return IDLE_CURSOR;
  }
  const activeDragOwners = /* @__PURE__ */ new WeakMap();
  function hasActiveDrag(instance) {
    const owner = activeDragOwners.get(instance);
    return !!(owner && owner.dragState.isDragging);
  }
  function cancelActiveDrag(instance) {
    const owner = activeDragOwners.get(instance);
    if (owner && owner.dragState.isDragging) {
      owner.cancelDrag();
      return true;
    }
    return false;
  }
  function idleProjection() {
    return {
      active: false,
      kind: null,
      mode: null,
      targetId: null,
      targetType: null,
      startPosition: null
    };
  }
  function publishDragProjection(instance) {
    if (!instance || !instance.state) {
      return;
    }
    const owner = activeDragOwners.get(instance);
    if (!owner || !owner.dragState.isDragging) {
      instance.state.drag = idleProjection();
    } else {
      instance.state.drag = {
        active: true,
        kind: owner.dragState.kind,
        mode: owner.modeName,
        targetId: owner.dragState.draggedTargetId,
        targetType: owner.dragState.draggedTargetType,
        startPosition: owner.dragState.dragStartPosition ? { ...owner.dragState.dragStartPosition } : null
      };
    }
    dispatch(instance);
  }
  class BaseDragHandler {
    /**
     * Create a new BaseDragHandler
     * @param {GramFrame} instance - GramFrame instance
     * @param {DragCallbacks} callbacks - Drag lifecycle callbacks
     * @param {ModeType|null} [modeName] - Mode that owns this handler, for the projection
     */
    constructor(instance, callbacks, modeName = null) {
      this.instance = instance;
      this.callbacks = callbacks;
      this.modeName = modeName;
      this.dragState = {
        isDragging: false,
        kind: null,
        draggedTargetId: null,
        draggedTargetType: null,
        dragStartPosition: null,
        originalData: null
      };
    }
    /**
     * Check if currently dragging
     * @returns {boolean} True if drag operation is active
     */
    isDragging() {
      return this.dragState.isDragging;
    }
    /**
     * The kind of drag in progress, if any.
     * @returns {DragKind|null} Drag kind or null when idle
     */
    dragKind() {
      return this.dragState.isDragging ? this.dragState.kind : null;
    }
    /**
     * Get the current dragged target information.
     *
     * Deliberately not a `DragTarget`: this carries the drag's *start* position
     * and the snapshot taken at that moment, where `DragTarget` carries the
     * current position. See {@link BaseDragHandler#currentTarget} for the latter.
     * @returns {DraggedTargetInfo|null} Drag target info or null if not dragging
     */
    getDraggedTarget() {
      if (!this.dragState.isDragging) return null;
      return {
        kind: this.dragState.kind,
        id: this.dragState.draggedTargetId,
        type: this.dragState.draggedTargetType,
        startPosition: this.dragState.dragStartPosition,
        originalData: this.dragState.originalData
      };
    }
    /**
     * The target descriptor handed back to the mode's callbacks.
     * @param {DataCoordinates|null} position - Current position; null for a
     *   pixel-space (pan) drag, which has no data position
     * @returns {DragTarget} Target descriptor
     */
    currentTarget(position) {
      return {
        // Non-null while a drag is running, which is the only time this is
        // called: `handleMouseMove`, `handleMouseUp` and `cancelDrag` all return
        // early when `isDragging` is false.
        kind: (
          /** @type {DragKind} */
          this.dragState.kind
        ),
        id: this.dragState.draggedTargetId,
        type: this.dragState.draggedTargetType,
        position,
        data: this.dragState.originalData
      };
    }
    /**
     * Handle mouse move events for drag operations
     * @param {DataCoordinates|null} currentPosition - Current mouse position in data coordinates
     * @param {MouseEvent} [event] - Originating event, for drags that work in screen pixels
     */
    handleMouseMove(currentPosition, event) {
      if (!this.dragState.isDragging) return;
      this.callbacks.onDragMove(
        this.currentTarget(currentPosition),
        currentPosition,
        this.dragState.dragStartPosition,
        event
      );
    }
    /**
     * Start a drag operation
     * @param {DataCoordinates|null} position - Position where drag started
     * @param {MouseEvent} [event] - Originating mousedown, passed to the resolver
     * @returns {boolean} True if drag started successfully, false otherwise
     */
    startDrag(position, event) {
      if (this.dragState.isDragging) return false;
      const owner = activeDragOwners.get(this.instance);
      if (owner && owner !== this && owner.dragState.isDragging) return false;
      const target = this.callbacks.resolveTarget(position, event);
      if (!target) return false;
      this.dragState.isDragging = true;
      this.dragState.kind = target.kind || "move";
      this.dragState.draggedTargetId = target.id ?? null;
      this.dragState.draggedTargetType = target.type ?? null;
      this.dragState.dragStartPosition = position ? { ...position } : null;
      this.dragState.originalData = target.data ? { ...target.data } : null;
      activeDragOwners.set(this.instance, this);
      publishDragProjection(this.instance);
      this.applyCursor(this.dragState.kind, "drag");
      this.callbacks.onDragStart(this.currentTarget(position), position, event);
      return true;
    }
    /**
     * End the current drag operation
     * @param {DataCoordinates|null} position - Position where drag ended
     * @param {MouseEvent} [event] - Originating mouseup
     */
    endDrag(position, event) {
      if (!this.dragState.isDragging) return;
      const target = this.currentTarget(position);
      this.callbacks.onDragEnd(target, position, event);
      this.applyCursor(this.dragState.kind, "idle");
      this.clearDragState();
    }
    /**
     * Cancel the current drag operation without applying changes
     */
    cancelDrag() {
      if (!this.dragState.isDragging) return;
      const target = this.currentTarget(this.dragState.dragStartPosition);
      if (this.callbacks.onDragCancel) {
        this.callbacks.onDragCancel(target);
      }
      this.applyCursor(this.dragState.kind, "idle");
      this.clearDragState();
    }
    /**
     * Clear drag bookkeeping and republish the projection.
     */
    clearDragState() {
      this.dragState.isDragging = false;
      this.dragState.kind = null;
      this.dragState.draggedTargetId = null;
      this.dragState.draggedTargetType = null;
      this.dragState.dragStartPosition = null;
      this.dragState.originalData = null;
      if (activeDragOwners.get(this.instance) === this) {
        activeDragOwners.delete(this.instance);
      }
      publishDragProjection(this.instance);
    }
    /**
     * Apply the cursor for a drag kind and phase.
     *
     * The phase is passed as a name rather than as a ready-made CSS value so a
     * mode can decide what "dragging" looks like for its own kind — pan keeps the
     * hand, everything else takes the hollow brackets. Passing the value and
     * having modes sniff it (`fallback === 'grabbing'`) tied every mode's cursor
     * to the exact strings the engine happened to use.
     * @param {DragKind|null} kind - Drag kind, or null when nothing is targeted
     * @param {CursorPhase} phase - Which phase the pointer is in
     */
    applyCursor(kind, phase) {
      if (!this.callbacks.updateCursor) return;
      const style = this.callbacks.cursorFor && this.callbacks.cursorFor(kind, phase) || featureCursor(phase);
      this.callbacks.updateCursor(style);
    }
    /**
     * Update cursor style based on proximity to drag targets.
     *
     * Hover must never change state, so this uses the mode's side-effect-free
     * `resolveHoverTarget` when one is supplied. `resolveTarget` is only a safe
     * fallback for modes whose resolver is pure — a mode whose resolver mints a
     * feature on mousedown (harmonics `create`, doppler `place`) MUST supply
     * `resolveHoverTarget`, or every hover would create a feature.
     *
     * Routed through `applyCursor` like every other transition, so a mode's
     * `cursorFor` opinion covers hover too. Calling `updateCursor` directly here
     * made hover the one transition a mode could not influence.
     * @param {DataCoordinates} position - Current mouse position
     */
    updateCursorForHover(position) {
      if (this.dragState.isDragging) return;
      const resolve = this.callbacks.resolveHoverTarget || this.callbacks.resolveTarget;
      const target = resolve(position);
      this.applyCursor(target ? target.kind || "move" : null, target ? "hover" : "idle");
    }
    /**
     * Reset drag handler state
     */
    reset() {
      this.cancelDrag();
    }
    /**
     * Clean up drag handler resources
     */
    cleanup() {
      this.reset();
    }
  }
  function decimalsForInterval(interval) {
    if (!Number.isFinite(interval) || interval <= 0) {
      return 0;
    }
    for (let decimals = 0; decimals < 3; decimals++) {
      const scaled = interval * Math.pow(10, decimals);
      if (Math.abs(scaled - Math.round(scaled)) < 1e-9) {
        return decimals;
      }
    }
    return 3;
  }
  function formatAtInterval(value, interval) {
    if (!Number.isFinite(interval) || interval <= 0) {
      return String(Math.round(value));
    }
    return value.toFixed(decimalsForInterval(interval));
  }
  function formatFrequencyLabel(frequency, interval = 1) {
    return formatAtInterval(frequency, interval) + "Hz";
  }
  function precisionIntervalFor(span) {
    if (!Number.isFinite(span) || span <= 0) {
      return 1;
    }
    return Math.pow(10, Math.floor(Math.log10(span)) - 1);
  }
  function formatTime(seconds) {
    const sign = seconds < 0 ? "-" : "";
    const magnitude = Math.abs(seconds);
    const minutes = Math.floor(magnitude / 60);
    const remainingSeconds = Math.floor(magnitude % 60);
    const paddedMinutes = minutes.toString().padStart(2, "0");
    const paddedSeconds = remainingSeconds.toString().padStart(2, "0");
    return `${sign}${paddedMinutes}:${paddedSeconds}`;
  }
  function formatAxisTime(seconds, interval) {
    const decimals = decimalsForInterval(interval);
    if (decimals === 0) {
      return formatTime(seconds);
    }
    const sign = seconds < 0 ? "-" : "";
    const magnitude = Math.abs(seconds);
    const minutes = Math.floor(magnitude / 60);
    const remainingSeconds = magnitude % 60;
    const paddedMinutes = minutes.toString().padStart(2, "0");
    const secondsText = remainingSeconds.toFixed(decimals).padStart(decimals + 3, "0");
    return `${sign}${paddedMinutes}:${secondsText}`;
  }
  function renderAxes(instance) {
    if (!instance.ui.axesGroup) {
      return;
    }
    instance.ui.axesGroup.innerHTML = "";
    const viewport = instance.state;
    const { naturalWidth, naturalHeight } = viewport.imageDetails;
    const margins = viewport.margins;
    if (!naturalWidth || !naturalHeight) {
      return;
    }
    const { renderWidth, renderHeight } = getRenderDimensions(viewport);
    const visibleRange = calculateVisibleDataRange(viewport, instance.ui.spectrogramImage);
    renderFrequencyAxis(instance, margins, renderWidth, renderHeight, visibleRange.freqMin, visibleRange.freqMax);
    renderTimeAxis(instance, margins, renderWidth, renderHeight, visibleRange.timeMin, visibleRange.timeMax);
  }
  function renderTimeAxis(instance, margins, _naturalWidth, naturalHeight, timeMin, timeMax) {
    const axisX = margins.left;
    const axisStartY = margins.top;
    const axisEndY = margins.top + naturalHeight;
    const timeRange = timeMax - timeMin;
    const axisLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    axisLine.setAttribute("x1", String(axisX));
    axisLine.setAttribute("y1", String(axisStartY));
    axisLine.setAttribute("x2", String(axisX));
    axisLine.setAttribute("y2", String(axisEndY));
    axisLine.setAttribute("class", "gram-frame-axis-line");
    instance.ui.axesGroup.appendChild(axisLine);
    if (!(timeRange > 0)) {
      return;
    }
    const { majorInterval, minorInterval, majorStart, minorStart, maxTicks } = calculateAxisTicks(timeMin, timeMax, naturalHeight, 40);
    const yFor = (time) => axisEndY - (time - timeMin) / timeRange * naturalHeight;
    const minorCount = Math.floor((timeMax - minorStart) / minorInterval) + 1;
    if (minorCount > 0 && minorCount <= maxTicks) {
      for (let i = 0; i < minorCount; i++) {
        const time = minorStart + i * minorInterval;
        if (time > timeMax) break;
        const offsetFromMajor = Math.abs((time - majorStart) % majorInterval / majorInterval);
        if (offsetFromMajor < 1e-3 || offsetFromMajor > 0.999) continue;
        const y = yFor(time);
        const tick = document.createElementNS("http://www.w3.org/2000/svg", "line");
        tick.setAttribute("x1", String(axisX - 4));
        tick.setAttribute("y1", String(y));
        tick.setAttribute("x2", String(axisX));
        tick.setAttribute("y2", String(y));
        tick.setAttribute("class", "gram-frame-axis-tick-minor");
        instance.ui.axesGroup.appendChild(tick);
      }
    }
    const majorCount = Math.floor((timeMax - majorStart) / majorInterval) + 1;
    if (majorCount <= 0 || majorCount > maxTicks) {
      return;
    }
    for (let i = 0; i < majorCount; i++) {
      const time = majorStart + i * majorInterval;
      if (time > timeMax) break;
      const y = yFor(time);
      const tick = document.createElementNS("http://www.w3.org/2000/svg", "line");
      tick.setAttribute("x1", String(axisX - 8));
      tick.setAttribute("y1", String(y));
      tick.setAttribute("x2", String(axisX));
      tick.setAttribute("y2", String(y));
      tick.setAttribute("class", "gram-frame-axis-tick");
      instance.ui.axesGroup.appendChild(tick);
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", String(axisX - 12));
      label.setAttribute("y", String(y + 4));
      label.setAttribute("text-anchor", "end");
      label.setAttribute("class", "gram-frame-axis-label");
      label.textContent = formatAxisTime(time, majorInterval);
      instance.ui.axesGroup.appendChild(label);
    }
  }
  function calculateAxisTicks(min, max, containerSize, targetSpacing = 80) {
    const range = max - min;
    const targetMajorTicks = Math.max(2, Math.floor(containerSize / targetSpacing));
    const rawMajorInterval = range / (targetMajorTicks - 1);
    function niceNum(value, round) {
      const exponent = Math.floor(Math.log10(value));
      const fraction = value / Math.pow(10, exponent);
      let niceFraction;
      {
        if (fraction <= 1) niceFraction = 1;
        else if (fraction <= 2) niceFraction = 2;
        else if (fraction <= 5) niceFraction = 5;
        else niceFraction = 10;
      }
      return niceFraction * Math.pow(10, exponent);
    }
    const majorInterval = niceNum(rawMajorInterval);
    let minorInterval;
    const majorFraction = majorInterval / Math.pow(10, Math.floor(Math.log10(majorInterval)));
    if (majorFraction === 1) {
      minorInterval = majorInterval / 5;
    } else if (majorFraction === 2) {
      minorInterval = majorInterval / 2;
    } else if (majorFraction === 5) {
      minorInterval = majorInterval / 5;
    } else {
      minorInterval = majorInterval / 2;
    }
    const majorStart = Math.ceil(min / majorInterval) * majorInterval;
    const minorStart = Math.ceil(min / minorInterval) * minorInterval;
    const expectedMajorTicks = Math.ceil(range / majorInterval) + 2;
    const expectedMinorTicks = Math.ceil(range / minorInterval) + 2;
    const maxTicks = Math.max(200, expectedMajorTicks + expectedMinorTicks);
    return {
      majorInterval,
      minorInterval,
      majorStart,
      minorStart,
      expectedMajorTicks,
      expectedMinorTicks,
      maxTicks
    };
  }
  function renderAxisLine(instance, axisConfig) {
    const axisLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    axisLine.setAttribute("x1", String(axisConfig.startX));
    axisLine.setAttribute("y1", String(axisConfig.y));
    axisLine.setAttribute("x2", String(axisConfig.endX));
    axisLine.setAttribute("y2", String(axisConfig.y));
    axisLine.setAttribute("class", "gram-frame-axis-line");
    instance.ui.axesGroup.appendChild(axisLine);
  }
  function renderAxisTicks(instance, tickData, axisConfig) {
    tickData.forEach((tickInfo) => {
      const tick = document.createElementNS("http://www.w3.org/2000/svg", "line");
      tick.setAttribute("x1", String(tickInfo.x));
      tick.setAttribute("y1", String(axisConfig.y));
      tick.setAttribute("x2", String(tickInfo.x));
      tick.setAttribute("y2", String(axisConfig.y + tickInfo.height));
      tick.setAttribute("class", tickInfo.className);
      instance.ui.axesGroup.appendChild(tick);
    });
  }
  function renderAxisLabels(instance, labelData, axisConfig) {
    labelData.forEach((labelInfo) => {
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", String(labelInfo.x));
      label.setAttribute("y", String(axisConfig.y + 25));
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("class", labelInfo.className);
      label.textContent = labelInfo.text;
      instance.ui.axesGroup.appendChild(label);
    });
  }
  function renderFrequencyAxis(instance, margins, naturalWidth, _naturalHeight, freqMin, freqMax) {
    const axisY = margins.top + _naturalHeight;
    const axisStartX = margins.left;
    const axisEndX = margins.left + naturalWidth;
    const displayFreqMin = freqMin;
    const displayFreqMax = freqMax;
    const freqRange = displayFreqMax - displayFreqMin;
    const axisConfig = { y: axisY, startX: axisStartX, endX: axisEndX };
    renderAxisLine(instance, axisConfig);
    const tickCalculation = calculateAxisTicks(displayFreqMin, displayFreqMax, naturalWidth);
    const minorTickData = [];
    const majorTickData = [];
    const labelData = [];
    const numMinorTicks = Math.floor((displayFreqMax - tickCalculation.minorStart) / tickCalculation.minorInterval) + 1;
    if (numMinorTicks <= tickCalculation.maxTicks) {
      for (let i = 0; i < numMinorTicks; i++) {
        const freq = tickCalculation.minorStart + i * tickCalculation.minorInterval;
        if (freq > displayFreqMax) break;
        if (Math.abs(freq % tickCalculation.majorInterval) < 0.01) continue;
        const x = axisStartX + (freq - displayFreqMin) / freqRange * naturalWidth;
        minorTickData.push({ x, height: 4, className: "gram-frame-axis-tick-minor" });
      }
    }
    const numMajorTicks = Math.floor((displayFreqMax - tickCalculation.majorStart) / tickCalculation.majorInterval) + 1;
    if (numMajorTicks <= tickCalculation.maxTicks) {
      for (let i = 0; i < numMajorTicks; i++) {
        const freq = tickCalculation.majorStart + i * tickCalculation.majorInterval;
        if (freq > displayFreqMax) break;
        const x = axisStartX + (freq - displayFreqMin) / freqRange * naturalWidth;
        majorTickData.push({ x, height: 8, className: "gram-frame-axis-tick-major" });
        labelData.push({
          x,
          text: formatFrequencyLabel(freq, tickCalculation.majorInterval),
          className: "gram-frame-axis-label-major"
        });
      }
    } else {
      const tickCount = 5;
      const fallbackInterval = freqRange / (tickCount - 1);
      for (let i = 0; i < tickCount; i++) {
        const freq = displayFreqMin + i * fallbackInterval;
        const x = axisStartX + i / (tickCount - 1) * naturalWidth;
        majorTickData.push({ x, height: 8, className: "gram-frame-axis-tick" });
        labelData.push({
          x,
          text: formatFrequencyLabel(freq, fallbackInterval),
          className: "gram-frame-axis-label"
        });
      }
    }
    renderAxisTicks(instance, minorTickData, axisConfig);
    renderAxisTicks(instance, majorTickData, axisConfig);
    renderAxisLabels(instance, labelData, axisConfig);
  }
  function updateSVGLayout(instance) {
    const viewport = instance.state;
    const { naturalWidth, naturalHeight } = viewport.imageDetails;
    const margins = viewport.margins;
    if (!naturalWidth || !naturalHeight) {
      return;
    }
    const { renderWidth, renderHeight } = getRenderDimensions(viewport);
    const axesWidth = renderWidth;
    const axesHeight = renderHeight;
    const totalWidth = axesWidth + margins.left + margins.right;
    const totalHeight = axesHeight + margins.top + margins.bottom;
    instance.ui.container.style.width = "auto";
    instance.ui.container.style.height = "auto";
    instance.ui.container.style.aspectRatio = "unset";
    instance.ui.svg.style.width = `${totalWidth}px`;
    instance.ui.svg.style.height = `${totalHeight}px`;
    instance.ui.svg.setAttribute("viewBox", `0 0 ${totalWidth} ${totalHeight}`);
    instance.ui.svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    instance.ui.spectrogramImage.setAttribute("x", String(margins.left));
    instance.ui.spectrogramImage.setAttribute("y", String(margins.top));
    instance.ui.spectrogramImage.setAttribute("width", String(axesWidth));
    instance.ui.spectrogramImage.setAttribute("height", String(axesHeight));
    if (instance.ui.imageClipRect) {
      instance.ui.imageClipRect.setAttribute("x", String(margins.left));
      instance.ui.imageClipRect.setAttribute("y", String(margins.top));
      instance.ui.imageClipRect.setAttribute("width", String(axesWidth));
      instance.ui.imageClipRect.setAttribute("height", String(axesHeight));
    }
    if (instance.ui.cursorClipRect) {
      instance.ui.cursorClipRect.setAttribute("x", String(margins.left));
      instance.ui.cursorClipRect.setAttribute("y", String(margins.top));
      instance.ui.cursorClipRect.setAttribute("width", String(axesWidth));
      instance.ui.cursorClipRect.setAttribute("height", String(axesHeight));
    }
    applyZoomTransform(instance);
  }
  function applyZoomTransform(instance) {
    const viewport = instance.state;
    const { level, centerX, centerY } = viewport.zoom;
    const margins = viewport.margins;
    const { renderWidth, renderHeight } = getRenderDimensions(viewport);
    if (!instance.ui.spectrogramImage) {
      return;
    }
    if (viewport.imageDetails.timeStretch !== void 0) {
      applyStretchedTransform(instance, viewport, renderWidth, renderHeight);
      return;
    }
    if (level === 1) {
      instance.ui.spectrogramImage.setAttribute("x", String(margins.left));
      instance.ui.spectrogramImage.setAttribute("y", String(margins.top));
      instance.ui.spectrogramImage.setAttribute("width", String(renderWidth));
      instance.ui.spectrogramImage.setAttribute("height", String(renderHeight));
      instance.ui.spectrogramImage.removeAttribute("transform");
      renderAxes(instance);
      if (instance.featureRenderer) {
        instance.featureRenderer.renderAllPersistentFeatures();
      }
      return;
    }
    const centerImageX = centerX * renderWidth;
    const centerImageY = centerY * renderHeight;
    const zoomedWidth = renderWidth * level;
    const zoomedHeight = renderHeight * level;
    const newX = margins.left + centerImageX - centerImageX * level;
    const newY = margins.top + centerImageY - centerImageY * level;
    instance.ui.spectrogramImage.setAttribute("x", String(newX));
    instance.ui.spectrogramImage.setAttribute("y", String(newY));
    instance.ui.spectrogramImage.setAttribute("width", String(zoomedWidth));
    instance.ui.spectrogramImage.setAttribute("height", String(zoomedHeight));
    renderAxes(instance);
    if (instance.featureRenderer) {
      instance.featureRenderer.renderAllPersistentFeatures();
    }
  }
  function applyStretchedTransform(instance, viewport, renderWidth, renderHeight) {
    const { zoom, margins, config, player, imageDetails } = viewport;
    const { level, centerX } = zoom;
    const stretch = imageDetails.timeStretch || 1;
    const image = instance.ui.spectrogramImage;
    const width = renderWidth * level;
    const height = renderHeight * stretch * level;
    const x = margins.left + centerX * renderWidth - centerX * renderWidth * level;
    const span = config.timeMax - config.timeMin;
    const aboveView = span > 0 ? (config.timeMax - player.viewTop) / span : 1;
    const y = margins.top - aboveView * height;
    image.setAttribute("x", String(x));
    image.setAttribute("y", String(y));
    image.setAttribute("width", String(width));
    image.setAttribute("height", String(height));
    image.removeAttribute("transform");
    if (instance.ui.imageClipRect) {
      instance.ui.imageClipRect.setAttribute("y", String(margins.top));
      instance.ui.imageClipRect.setAttribute("height", String(renderHeight));
    }
    renderAxes(instance);
    if (instance.featureRenderer) {
      instance.featureRenderer.renderAllPersistentFeatures();
    }
  }
  const PLAYER_RENDER_WIDTH = 900;
  const PLAYER_RENDER_HEIGHT = 400;
  function baseRenderSize(instance) {
    if (isPlayerActive(instance)) {
      return { width: PLAYER_RENDER_WIDTH, height: PLAYER_RENDER_HEIGHT };
    }
    const { naturalWidth, naturalHeight } = instance.state.imageDetails;
    return { width: naturalWidth, height: naturalHeight };
  }
  const followHandles = /* @__PURE__ */ new WeakMap();
  function playerOf(instance) {
    return instance.state.player;
  }
  function isPlayerActive(instance) {
    const player = playerOf(instance);
    return !!(player && player.active);
  }
  function isPlaying(instance) {
    return isPlayerActive(instance) && playerOf(instance).playing;
  }
  function visibleWindowSeconds(instance) {
    const { player, zoom } = instance.state;
    return player.windowSeconds / zoom.level;
  }
  function clampViewTop(instance, seconds) {
    const { duration } = playerOf(instance);
    return Math.max(0, Math.min(duration, seconds));
  }
  function revealTime(instance, seconds) {
    if (!isPlayerActive(instance) || isPlaying(instance) || !Number.isFinite(seconds)) {
      return false;
    }
    const player = playerOf(instance);
    const window2 = visibleWindowSeconds(instance);
    if (seconds <= player.viewTop && seconds >= player.viewTop - window2) {
      return false;
    }
    const target = clampViewTop(instance, seconds + window2 / 2);
    if (target === player.viewTop) {
      return false;
    }
    player.viewTop = target;
    applyView(instance);
    dispatch(instance);
    return true;
  }
  function applyView(instance) {
    if (instance.ui.svg) {
      applyZoomTransform(instance);
    }
  }
  function syncViewToPlayhead(instance) {
    const controller = instance.player;
    if (!controller) {
      return;
    }
    const player = playerOf(instance);
    const duration = player.duration;
    const current = controller.audio.currentTime;
    player.playhead = Math.max(0, Math.min(duration, Number.isFinite(current) ? current : 0));
    player.viewTop = clampViewTop(instance, player.playhead);
    applyView(instance);
    dispatch(instance, { frame: true });
  }
  function startFollow(instance) {
    if (followHandles.has(instance) || typeof requestAnimationFrame !== "function") {
      return;
    }
    const step = () => {
      if (!isPlaying(instance)) {
        followHandles.delete(instance);
        return;
      }
      syncViewToPlayhead(instance);
      followHandles.set(instance, requestAnimationFrame(step));
    };
    followHandles.set(instance, requestAnimationFrame(step));
  }
  function stopFollow(instance) {
    const handle = followHandles.get(instance);
    if (handle !== void 0 && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(handle);
    }
    followHandles.delete(instance);
    syncViewToPlayhead(instance);
  }
  function updatePlayingClass(instance) {
    if (instance.ui.container) {
      instance.ui.container.classList.toggle("gram-frame-playing", isPlaying(instance));
    }
  }
  function seekFromTimeAxisClick(instance, event) {
    if (!instance.player || !instance.player.isReady()) {
      return false;
    }
    const state = instance.state;
    const svgRect = instance.ui.svg.getBoundingClientRect();
    const point = screenToSVG(event.clientX - svgRect.left, event.clientY - svgRect.top, instance.ui.svg);
    const { renderHeight } = getRenderDimensions(state);
    const { margins } = state;
    const onAxisBand = point.x >= 0 && point.x < margins.left && point.y >= margins.top && point.y <= margins.top + renderHeight;
    if (!onAxisBand) {
      return false;
    }
    const visible = calculateVisibleDataRange(state, instance.ui.spectrogramImage);
    const fraction = (point.y - margins.top) / renderHeight;
    instance.player.seek(visible.timeMax - fraction * (visible.timeMax - visible.timeMin));
    return true;
  }
  function addBookmark(instance) {
    const { player, bookmarks } = instance.state;
    if (!player.ready) {
      return null;
    }
    const time = player.playhead;
    if (bookmarks.some((existing) => Math.abs(existing.time - time) < 1)) {
      return null;
    }
    const bookmark = {
      id: `bookmark-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      time,
      label: ""
    };
    bookmarks.push(bookmark);
    bookmarks.sort((a, b) => a.time - b.time);
    renumber(bookmarks);
    dispatch(instance);
    return bookmark;
  }
  function removeBookmark(instance, id) {
    const { bookmarks } = instance.state;
    const index = bookmarks.findIndex((bookmark) => bookmark.id === id);
    if (index === -1) {
      return;
    }
    bookmarks.splice(index, 1);
    renumber(bookmarks);
    dispatch(instance);
  }
  function renumber(bookmarks) {
    bookmarks.forEach((bookmark, index) => {
      bookmark.label = String(index + 1);
    });
  }
  const SEEK_STEP_SECONDS = 5;
  const SEEK_STEP_SHIFT_SECONDS = 30;
  function handleTransportKey(instance, event) {
    const controller = instance.player;
    if (!controller || !controller.isReady()) {
      return false;
    }
    const target = event.target;
    const onButton = target instanceof Element && target.tagName === "BUTTON";
    const step = event.shiftKey ? SEEK_STEP_SHIFT_SECONDS : SEEK_STEP_SECONDS;
    const player = instance.state.player;
    const playhead = player.playhead;
    switch (event.key) {
      case " ":
      case "Enter":
        if (onButton) return false;
        controller.toggle().catch((error) => {
          console.warn("GramFrame: playback could not start:", error instanceof Error ? error.message : String(error));
        });
        return true;
      case "k":
      case "K":
        controller.toggle().catch((error) => {
          console.warn("GramFrame: playback could not start:", error instanceof Error ? error.message : String(error));
        });
        return true;
      case "j":
      case "J":
        controller.seek(playhead - step);
        return true;
      case "l":
      case "L":
        controller.seek(playhead + step);
        return true;
      case "Home":
        controller.restart();
        return true;
      case "m":
      case "M":
        controller.setMute(!player.muted);
        return true;
      case "b":
      case "B":
        addBookmark(instance);
        return true;
      default:
        return false;
    }
  }
  const MOVEMENT_INCREMENTS = {
    normal: 1,
    // Arrow keys alone: 1-pixel increments
    fast: 5
    // Shift + Arrow keys: 5-pixel increments
  };
  let globalKeyboardHandler = null;
  let globalMousedownHandler = null;
  let globalFocusinHandler = null;
  let keyboardHandlerInitialized = false;
  function initializeKeyboardControl(instance) {
    registerInstance(instance);
    if (!keyboardHandlerInitialized) {
      globalKeyboardHandler = (event) => handleGlobalKeyboardEvent(event);
      document.addEventListener("keydown", globalKeyboardHandler);
      globalMousedownHandler = (event) => {
        if (!isNodeInsideAnyInstance(event.target)) {
          clearFocusedInstance();
        }
      };
      document.addEventListener("mousedown", globalMousedownHandler);
      globalFocusinHandler = (event) => {
        const owner = instanceContaining(event.target);
        if (owner) {
          setFocusedInstance(owner);
        }
      };
      document.addEventListener("focusin", globalFocusinHandler);
      keyboardHandlerInitialized = true;
    }
  }
  function cleanupKeyboardControl(instance) {
    unregisterInstance(instance);
    if (getRegisteredInstanceCount() === 0) {
      if (globalKeyboardHandler) {
        document.removeEventListener("keydown", globalKeyboardHandler);
        globalKeyboardHandler = null;
      }
      if (globalMousedownHandler) {
        document.removeEventListener("mousedown", globalMousedownHandler);
        globalMousedownHandler = null;
      }
      if (globalFocusinHandler) {
        document.removeEventListener("focusin", globalFocusinHandler);
        globalFocusinHandler = null;
      }
      keyboardHandlerInitialized = false;
    }
  }
  function isEditableTarget(target) {
    if (!(target instanceof Element)) {
      return false;
    }
    const tag = target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
      return true;
    }
    return target instanceof HTMLElement && target.isContentEditable;
  }
  function handleGlobalKeyboardEvent(event) {
    if (isEditableTarget(event.target)) {
      return;
    }
    const focusedInstance = getFocusedInstance();
    if (event.key === "Tab") {
      return;
    }
    if (!focusedInstance) {
      return;
    }
    if (event.key === "Escape") {
      if (cancelActiveDrag(focusedInstance)) {
        event.preventDefault();
      }
      return;
    }
    if (isPlayerActive(focusedInstance) && handleTransportKey(focusedInstance, event)) {
      event.preventDefault();
      return;
    }
    if (!isArrowKey(event.key)) {
      return;
    }
    if (isPlaying(focusedInstance)) {
      return;
    }
    const selection = focusedInstance.state.selection;
    if (!selection || !selection.selectedType || !selection.selectedId) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const increment = event.shiftKey ? MOVEMENT_INCREMENTS.fast : MOVEMENT_INCREMENTS.normal;
    const movement = calculateMovementFromKey(event.key, increment);
    nudgeSelection(focusedInstance, movement);
  }
  function nudgeSelection(instance, movement) {
    const selection = instance.state.selection;
    if (!selection || !selection.selectedType || !selection.selectedId) {
      return;
    }
    if (selection.selectedType === "marker") {
      moveSelectedMarker(instance, selection.selectedId, movement);
      return;
    }
    const owner = findPinSetOwner(instance, selection.selectedType);
    if (owner) {
      moveSelectedPinSet(instance, owner, selection.selectedId, movement);
    }
  }
  function isArrowKey(key) {
    return ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(key);
  }
  function calculateMovementFromKey(key, increment) {
    switch (key) {
      case "ArrowLeft":
        return { dx: -increment, dy: 0 };
      case "ArrowRight":
        return { dx: increment, dy: 0 };
      case "ArrowUp":
        return { dx: 0, dy: -increment };
      case "ArrowDown":
        return { dx: 0, dy: increment };
      default:
        return { dx: 0, dy: 0 };
    }
  }
  function moveSelectedMarker(instance, markerId, movement) {
    const analysis = instance.state.analysis;
    if (!analysis || !analysis.markers) {
      return;
    }
    const marker = analysis.markers.find((m) => m.id === markerId);
    if (!marker) {
      return;
    }
    const newData = nudgeData(
      { freq: marker.freq, time: marker.time },
      movement.dx,
      movement.dy,
      instance.state,
      instance.ui.spectrogramImage
    );
    marker.freq = newData.freq;
    marker.time = newData.time;
    commitAnnotationChange(instance, () => refreshPanels(instance));
  }
  function moveSelectedPinSet(instance, owner, setId, movement) {
    const set = owner.sets.find((candidate) => candidate.id === setId);
    if (!set) {
      return;
    }
    let updates = {};
    const { timeMin, timeMax } = instance.state.config;
    const viewport = instance.state;
    const image = instance.ui.spectrogramImage;
    const svgPointToData = (svgX, svgY) => {
      const imagePoint = svgToImage(svgX, svgY, viewport, image);
      return imageToData(imagePoint.x, imagePoint.y, viewport);
    };
    if (movement.dx !== 0) {
      const reference = dataToSVG(
        { freq: dataFrequencyRange(viewport).freqMin, time: timeMax },
        viewport,
        image
      );
      const before = svgPointToData(reference.x, reference.y);
      const after = svgPointToData(reference.x + movement.dx, reference.y);
      updates = { ...updates, ...owner.nudgeFreqUpdates(set, after.freq - before.freq) };
    }
    if (movement.dy !== 0) {
      const anchorSVG = dataToSVG(
        { freq: dataFrequencyRange(viewport).freqMin, time: set.anchorTime },
        viewport,
        image
      );
      const moved = svgPointToData(anchorSVG.x, anchorSVG.y + movement.dy);
      updates.anchorTime = Math.max(timeMin, Math.min(timeMax, moved.time));
    }
    if (Object.keys(updates).length > 0) {
      owner.updateSet(setId, updates);
    }
  }
  function removeHarmonicSet(instance, id) {
    removePinSet(instance, "harmonicSet", id);
  }
  function removeSidebandSet(instance, id) {
    removePinSet(instance, "sidebandSet", id);
  }
  function removePinSet(instance, selectionType, id) {
    const owner = findPinSetOwner(instance, selectionType);
    if (owner) {
      owner.removeSet(id);
    }
  }
  function getSelectedFeature(instance) {
    const { selection: sel, styleTarget } = instance.state;
    if (styleTarget === "new") {
      return null;
    }
    if (!sel || !sel.selectedType || !sel.selectedId) {
      return null;
    }
    if (sel.selectedType === "marker") {
      const analysis = instance.state.analysis;
      const feature = analysis && analysis.markers ? analysis.markers.find((m) => m.id === sel.selectedId) : null;
      return feature ? { type: "marker", feature } : null;
    }
    const owner = findPinSetOwner(instance, sel.selectedType);
    if (owner) {
      const feature = owner.sets.find((set) => set.id === sel.selectedId);
      return feature ? { type: owner.selectionType, feature } : null;
    }
    return null;
  }
  function getActiveStyle(instance) {
    const selected = getSelectedFeature(instance);
    if (selected) {
      const isPinSet = selected.type !== "marker";
      return {
        color: selected.feature.color,
        symbol: (
          /** @type {SymbolType} */
          selected.feature.symbol || DEFAULT_SYMBOL
        ),
        // A pin set without an explicit `showPin` (legacy/restored) is pinned.
        showPin: isPinSet ? (
          /** @type {PinSet} */
          selected.feature.showPin !== false
        ) : instance.state.showHarmonicPin !== false,
        pinApplies: isPinSet,
        largeSymbols: !!selected.feature.largeSymbols
      };
    }
    const { selectedColor, selectedSymbol, showHarmonicPin, largeSymbols } = instance.state;
    return {
      color: selectedColor,
      symbol: selectedSymbol,
      showPin: showHarmonicPin !== false,
      pinApplies: true,
      largeSymbols: !!largeSymbols
    };
  }
  function refreshFeatureVisuals(instance, _type) {
    if (instance.featureRenderer) {
      instance.featureRenderer.renderAllPersistentFeatures();
    }
    refreshPanels(instance);
    dispatch(instance);
  }
  function applyColorToSelectedFeature(instance, color) {
    const selected = getSelectedFeature(instance);
    if (!selected) {
      return false;
    }
    selected.feature.color = color;
    markAnnotationsChanged(instance);
    refreshFeatureVisuals(instance, selected.type);
    return true;
  }
  function applySymbolToSelectedFeature(instance, symbol) {
    const selected = getSelectedFeature(instance);
    if (!selected) {
      return false;
    }
    selected.feature.symbol = symbol;
    markAnnotationsChanged(instance);
    refreshFeatureVisuals(instance, selected.type);
    return true;
  }
  function applyPinToSelectedFeature(instance, showPin) {
    const selected = getSelectedFeature(instance);
    if (!selected || selected.type === "marker") {
      return false;
    }
    selected.feature.showPin = !!showPin;
    markAnnotationsChanged(instance);
    refreshFeatureVisuals(instance, selected.type);
    return true;
  }
  function applyLargeSymbolsToSelectedFeature(instance, large) {
    const selected = getSelectedFeature(instance);
    if (!selected) {
      return false;
    }
    selected.feature.largeSymbols = large;
    refreshFeatureVisuals(instance, selected.type);
    return true;
  }
  const SVG_NS$5 = "http://www.w3.org/2000/svg";
  const LABEL_PLATE_CLASS = "gram-frame-label-plate";
  const LABEL_PLATE_GROUP_CLASS = "gram-frame-label-plated";
  const LABEL_PLATE_FILL = "#fff";
  const LABEL_TEXT_FILL = "#000";
  const LABEL_PLATE_PADDING_X = 3;
  const LABEL_PLATE_RADIUS = 3;
  const PLATE_ABOVE_RATIO = 0.95;
  const PLATE_BELOW_RATIO = 0.3;
  const FALLBACK_CHAR_WIDTH_RATIO = 0.6;
  function labelPlateExtents(fontSize) {
    return {
      above: roundToHalfPixel(fontSize * PLATE_ABOVE_RATIO),
      below: roundToHalfPixel(fontSize * PLATE_BELOW_RATIO)
    };
  }
  function roundToHalfPixel(value) {
    return Math.round(value * 2) / 2;
  }
  function labelPlateRect({ x, y, textAnchor, width, fontSize }) {
    const { above, below } = labelPlateExtents(fontSize);
    let left = x;
    if (textAnchor === "middle") {
      left = x - width / 2;
    } else if (textAnchor === "end") {
      left = x - width;
    }
    return {
      x: left - LABEL_PLATE_PADDING_X,
      y: y - above,
      width: width + LABEL_PLATE_PADDING_X * 2,
      height: above + below
    };
  }
  let measurementContext;
  function textMeasurementContext() {
    if (measurementContext === void 0) {
      try {
        measurementContext = document.createElement("canvas").getContext("2d");
      } catch {
        measurementContext = null;
      }
    }
    return measurementContext;
  }
  function measureLabelWidth(content, fontSize, font = {}) {
    const { fontFamily = "Arial, sans-serif", fontWeight = "bold" } = font;
    const text = content || "";
    const context = textMeasurementContext();
    if (context) {
      context.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
      const measured = context.measureText(text).width;
      if (measured > 0) {
        return measured;
      }
    }
    return text.length * fontSize * FALLBACK_CHAR_WIDTH_RATIO;
  }
  function plateLabel(text, options = {}) {
    const { fill = LABEL_PLATE_FILL, textFill = LABEL_TEXT_FILL } = options;
    const fontSize = Number(text.getAttribute("font-size"));
    const width = measureLabelWidth(text.textContent || "", fontSize, {
      fontFamily: text.getAttribute("font-family") || void 0,
      fontWeight: text.getAttribute("font-weight") || void 0
    });
    const box = labelPlateRect({
      x: Number(text.getAttribute("x")),
      y: Number(text.getAttribute("y")),
      textAnchor: text.getAttribute("text-anchor") || "start",
      width,
      fontSize
    });
    text.setAttribute("fill", textFill);
    text.removeAttribute("stroke");
    text.removeAttribute("stroke-width");
    text.removeAttribute("paint-order");
    const plate = document.createElementNS(SVG_NS$5, "rect");
    plate.setAttribute("class", LABEL_PLATE_CLASS);
    plate.setAttribute("x", String(box.x));
    plate.setAttribute("y", String(box.y));
    plate.setAttribute("width", String(box.width));
    plate.setAttribute("height", String(box.height));
    plate.setAttribute("rx", String(LABEL_PLATE_RADIUS));
    plate.setAttribute("ry", String(LABEL_PLATE_RADIUS));
    plate.setAttribute("fill", fill);
    const group = (
      /** @type {SVGGElement} */
      document.createElementNS(SVG_NS$5, "g")
    );
    group.setAttribute("class", LABEL_PLATE_GROUP_CLASS);
    group.appendChild(plate);
    group.appendChild(text);
    return group;
  }
  const MAX_MARKER_LABEL_LENGTH = 32;
  const TABLE_LABEL_FULL_LENGTH = 5;
  const TABLE_LABEL_HEAD_LENGTH = 3;
  function normalizeMarkerLabel(raw) {
    if (typeof raw !== "string") {
      return void 0;
    }
    const trimmed = raw.trim();
    if (trimmed === "") {
      return void 0;
    }
    return trimmed.slice(0, MAX_MARKER_LABEL_LENGTH);
  }
  function formatMarkerLabelForTable(label) {
    const normalized = normalizeMarkerLabel(label);
    if (!normalized) {
      return "";
    }
    if (normalized.length <= TABLE_LABEL_FULL_LENGTH) {
      return normalized;
    }
    return `${normalized.slice(0, TABLE_LABEL_HEAD_LENGTH)}..`;
  }
  const QUADRANT_GAP = 5;
  const ABOVE_SYMBOL_GAP = 4;
  const MARKER_LABEL_FONT_SIZE = 12;
  function markerLabelPlacement(symbol, cx, cy, symbolSize) {
    const plate = labelPlateExtents(MARKER_LABEL_FONT_SIZE);
    if (resolveSymbolType(symbol) === "cross") {
      return {
        x: cx + QUADRANT_GAP + LABEL_PLATE_PADDING_X,
        y: cy - QUADRANT_GAP - plate.below,
        textAnchor: "start"
      };
    }
    if (labelSitsBelowSymbol(symbol)) {
      const y = cy + symbolSize / 2 + ABOVE_SYMBOL_GAP + plate.above;
      return { x: cx, y, textAnchor: "middle" };
    }
    return { x: cx, y: cy - symbolSize / 2 - ABOVE_SYMBOL_GAP - plate.below, textAnchor: "middle" };
  }
  function describeSelection(instance) {
    const { selection, analysis, harmonics, sidebands } = instance.state;
    if (!selection || !selection.selectedType || !selection.selectedId) {
      return null;
    }
    const ordinal = (selection.selectedIndex ?? 0) + 1;
    if (selection.selectedType === "marker") {
      const marker = (analysis ? analysis.markers : []).find((candidate) => candidate.id === selection.selectedId);
      if (!marker) {
        return null;
      }
      return {
        label: normalizeMarkerLabel(marker.label) || `Marker ${ordinal}`,
        time: marker.time,
        freq: marker.freq
      };
    }
    if (selection.selectedType === "harmonicSet") {
      const set2 = (harmonics ? harmonics.harmonicSets : []).find((candidate) => candidate.id === selection.selectedId);
      return set2 ? { label: `Harmonics ${ordinal}`, time: set2.anchorTime, freq: set2.spacing } : null;
    }
    const set = (sidebands ? sidebands.sidebandSets : []).find((candidate) => candidate.id === selection.selectedId);
    return set ? { label: `Sidebands ${ordinal}`, time: set.anchorTime, freq: set.fundamentalFreq } : null;
  }
  function createCursorReadout() {
    const column = document.createElement("div");
    column.className = "gram-frame-readout-column";
    const kicker = document.createElement("div");
    kicker.className = "gram-frame-kicker gram-frame-readout-kicker";
    kicker.textContent = "Cursor";
    column.appendChild(kicker);
    const freqLED = createLEDDisplay("Frequency (Hz)", "0.0", "HZ");
    freqLED.classList.add("gram-frame-led-accent");
    column.appendChild(freqLED);
    const timeLED = createLEDDisplay("Time (mm:ss)", formatTime(0), "MM:SS", "Time");
    timeLED.classList.add("gram-frame-led-secondary");
    column.appendChild(timeLED);
    const spacer = document.createElement("div");
    spacer.className = "gram-frame-readout-spacer";
    column.appendChild(spacer);
    const speedLED = createLEDDisplay("Doppler Speed (kts)", "0.0", "KTS", "Doppler");
    speedLED.classList.add("gram-frame-led-secondary", "gram-frame-led-inline");
    column.appendChild(speedLED);
    return { column, timeLED, freqLED, speedLED, kicker };
  }
  function refreshReadoutTarget(instance) {
    const { kicker, timeLED, freqLED } = instance.ui;
    if (!kicker) {
      return;
    }
    const selected = describeSelection(instance);
    kicker.replaceChildren();
    if (!selected) {
      kicker.textContent = "Cursor";
      return;
    }
    const word = document.createElement("span");
    word.textContent = "Selected";
    kicker.appendChild(word);
    const name = document.createElement("span");
    name.className = "gram-frame-readout-target";
    name.textContent = selected.label;
    kicker.appendChild(name);
    if (timeLED) {
      setLEDValue(timeLED, formatTime(selected.time));
    }
    if (freqLED) {
      setLEDValue(freqLED, selected.freq.toFixed(2));
    }
  }
  function describeStyleTarget(instance) {
    const { selection, styleTarget } = instance.state;
    const selectedId = selection ? selection.selectedId : null;
    const selectedType = selection ? selection.selectedType : null;
    if (!selectedType || !selectedId) {
      return { editing: false, selectable: false, name: "", labelled: false, label: "" };
    }
    const ordinal = (selection.selectedIndex ?? 0) + 1;
    const marker = selectedType === "marker" ? findMarker(instance, selectedId) : null;
    const label = marker ? normalizeMarkerLabel(marker.label) || "" : "";
    const family = selectedType === "harmonicSet" ? "Harmonics" : selectedType === "sidebandSet" ? "Sidebands" : "Marker";
    return {
      editing: styleTarget === "selected",
      selectable: true,
      name: label || `${family} ${ordinal}`,
      // Only a marker carries free text today; a pin set is named by what it is.
      labelled: styleTarget === "selected" && !!marker,
      label
    };
  }
  function setStyleTarget(instance, target) {
    instance.state.styleTarget = target;
    if (instance.interaction.syncStyleControls) {
      instance.interaction.syncStyleControls();
    }
    dispatch(instance);
  }
  function renameSelectedMarker(instance, value) {
    const selection = currentSelection(instance);
    if (!selection || selection.selectedType !== "marker" || !selection.selectedId) {
      return;
    }
    const owner = findMarkerOwner(instance);
    if (owner) {
      owner.setMarkerLabel(selection.selectedId, value);
    }
    if (instance.interaction.syncStyleControls) {
      instance.interaction.syncStyleControls();
    }
    refreshReadoutTarget(instance);
  }
  function deleteStyleTarget(instance) {
    const selection = currentSelection(instance);
    if (!selection || !selection.selectedId) {
      return;
    }
    const id = selection.selectedId;
    if (selection.selectedType === "harmonicSet") {
      instance.interaction.removeHarmonicSet(id);
      return;
    }
    if (selection.selectedType === "sidebandSet") {
      instance.interaction.removeSidebandSet(id);
      return;
    }
    const owner = findMarkerOwner(instance);
    if (owner) {
      owner.removeMarker(id);
    }
  }
  function currentSelection(instance) {
    return instance.state.selection;
  }
  function findMarker(instance, id) {
    const owner = findMarkerOwner(instance);
    return owner ? owner.markers.find((marker) => marker.id === id) || null : null;
  }
  function createRow(text, control, className) {
    const row = document.createElement("div");
    row.className = className ? `gram-frame-style-row ${className}` : "gram-frame-style-row";
    const label = document.createElement("div");
    label.className = "gram-frame-style-group-label";
    label.textContent = text;
    row.appendChild(label);
    row.appendChild(control);
    return row;
  }
  function createStylePanel(instance) {
    const container = document.createElement("div");
    container.className = "gram-frame-color-picker gram-frame-style-column";
    const tabs = document.createElement("div");
    tabs.className = "gram-frame-style-tabs";
    const newTab = document.createElement("button");
    newTab.type = "button";
    newTab.className = "gram-frame-style-tab gram-frame-style-tab-new";
    newTab.textContent = "New features";
    newTab.title = "Set the style every feature you add from now on will take";
    newTab.addEventListener("click", (event) => {
      event.preventDefault();
      setStyleTarget(instance, "new");
    });
    const selectedTab = document.createElement("button");
    selectedTab.type = "button";
    selectedTab.className = "gram-frame-style-tab gram-frame-style-tab-selected";
    selectedTab.addEventListener("click", (event) => {
      event.preventDefault();
      if (!selectedTab.disabled) {
        setStyleTarget(instance, "selected");
      }
    });
    tabs.appendChild(newTab);
    tabs.appendChild(selectedTab);
    container.appendChild(tabs);
    const body = document.createElement("div");
    body.className = "gram-frame-style-body";
    container.appendChild(body);
    const labelInput = document.createElement("input");
    labelInput.type = "text";
    labelInput.className = "gram-frame-style-label-input";
    labelInput.maxLength = MAX_MARKER_LABEL_LENGTH;
    labelInput.title = "Optional — clear the field to remove the label";
    labelInput.setAttribute("aria-label", "Marker label");
    labelInput.addEventListener("input", () => renameSelectedMarker(instance, labelInput.value));
    const labelRow = createRow("Label", labelInput, "gram-frame-style-row-label");
    const color = createColorSlider(instance, () => {
      if (instance.interaction.syncStyleControls) {
        instance.interaction.syncStyleControls();
      }
    });
    const symbol = createSymbolSelect(instance);
    const symbolRow = createRow("Symbol", symbol.element, "gram-frame-style-row-symbol");
    const pin = createPinToggle(instance);
    const pinRow = createRow("Pin sets", pin.element);
    const nudge = document.createElement("div");
    nudge.className = "gram-frame-nudge";
    [["←", -1, "Nudge left"], ["→", 1, "Nudge right"]].forEach(([glyph, sign, title]) => {
      const button2 = document.createElement("button");
      button2.type = "button";
      button2.className = "gram-frame-nudge-btn";
      button2.textContent = /** @type {string} */
      glyph;
      button2.title = /** @type {string} */
      title;
      button2.addEventListener("click", (event) => {
        event.preventDefault();
        const step = event.shiftKey ? MOVEMENT_INCREMENTS.fast : MOVEMENT_INCREMENTS.normal;
        nudgeSelection(instance, { dx: (
          /** @type {number} */
          sign * step
        ), dy: 0 });
      });
      nudge.appendChild(button2);
    });
    const nudgeNote = document.createElement("span");
    nudgeNote.className = "gram-frame-nudge-note";
    nudgeNote.textContent = "or arrow keys";
    nudge.appendChild(nudgeNote);
    const nudgeRow = createRow("Nudge", nudge);
    body.appendChild(labelRow);
    body.appendChild(color.element);
    body.appendChild(symbolRow);
    body.appendChild(pinRow);
    body.appendChild(nudgeRow);
    const spacer = document.createElement("div");
    spacer.className = "gram-frame-style-spacer";
    body.appendChild(spacer);
    const footer = document.createElement("div");
    footer.className = "gram-frame-style-footer";
    const footerGlyph = document.createElement("span");
    footerGlyph.className = "gram-frame-style-footer-glyph";
    const footerNote = document.createElement("div");
    footerNote.className = "gram-frame-style-footer-note";
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "gram-frame-style-delete";
    deleteButton.textContent = "Delete";
    deleteButton.title = "Delete the selected feature";
    deleteButton.addEventListener("click", (event) => {
      event.preventDefault();
      deleteStyleTarget(instance);
    });
    footer.appendChild(footerGlyph);
    footer.appendChild(footerNote);
    footer.appendChild(deleteButton);
    container.appendChild(footer);
    instance.interaction.syncStyleControls = () => {
      const style = getActiveStyle(instance);
      color.control.setValue(style.color);
      symbol.control.setValue(style.symbol);
      symbol.control.setTint(style.color);
      pin.control.setValue(style.showPin);
      pin.control.setEnabled(style.pinApplies);
      const target = describeStyleTarget(instance);
      container.classList.toggle("gram-frame-style-targeting", target.editing);
      newTab.classList.toggle("gram-frame-style-tab-armed", !target.editing);
      selectedTab.classList.toggle("gram-frame-style-tab-armed", target.editing);
      selectedTab.disabled = !target.selectable;
      selectedTab.title = target.selectable ? `Restyle ${target.name}` : "Select a row to restyle that feature";
      writeTabFace(
        selectedTab,
        target.selectable ? `Selected: ${target.name}` : "Selected: none",
        target.selectable ? style.color : "",
        symbolGlyph(style.symbol)
      );
      labelRow.hidden = !target.labelled;
      if (target.labelled && document.activeElement !== labelInput) {
        labelInput.value = target.label;
      }
      nudgeRow.hidden = !target.editing;
      footerGlyph.style.color = style.color;
      footerGlyph.textContent = target.editing ? "" : symbolGlyph(style.symbol);
      footerNote.textContent = target.editing ? `changes ${target.name} only` : "applies to every feature you add, in any mode";
      deleteButton.hidden = !target.editing;
    };
    instance.interaction.syncStyleControls();
    return container;
  }
  function writeTabFace(tab, text, color, glyph) {
    tab.replaceChildren();
    if (color) {
      const swatch = document.createElement("span");
      swatch.className = "gram-frame-style-tab-swatch";
      swatch.style.color = color;
      swatch.textContent = glyph;
      tab.appendChild(swatch);
    }
    const word = document.createElement("span");
    word.textContent = text;
    tab.appendChild(word);
  }
  const NAVIGATION_GUIDANCE = [
    { trigger: "Shift + drag", outcome: "a box to zoom into that region" },
    { trigger: "Ctrl + scroll", outcome: "to zoom around the pointer" },
    { trigger: "Scroll", outcome: "to pan when zoomed in" },
    { trigger: "Wheel-button drag", outcome: "to pan when zoomed in" }
  ];
  function withNavigationGuidance(content) {
    const own = resolveGuidance(content).map((section) => ({
      title: section.title,
      qualifier: section.qualifier,
      items: section.lines.map((line2) => line2.trigger === "" ? line2.outcome : { trigger: line2.trigger, outcome: line2.outcome })
    }));
    return {
      sections: [...own, { title: "In every mode", items: [...NAVIGATION_GUIDANCE] }]
    };
  }
  function resolveGuidance(content) {
    if (!content || typeof content !== "object") {
      return [];
    }
    const sections = Array.isArray(content.sections) ? content.sections : [{ title: content.title, qualifier: void 0, items: content.items }];
    return sections.filter((section) => section && typeof section === "object").map((section) => ({
      title: typeof section.title === "string" ? section.title : "",
      qualifier: typeof section.qualifier === "string" ? section.qualifier : "",
      lines: resolveLines(section.items)
    })).filter((section) => section.title !== "" || section.lines.length > 0);
  }
  function resolveLines(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    return items.map((item) => {
      if (typeof item === "string") {
        return { trigger: "", outcome: item };
      }
      if (item && typeof item === "object") {
        return {
          trigger: typeof item.trigger === "string" ? item.trigger : "",
          outcome: typeof item.outcome === "string" ? item.outcome : ""
        };
      }
      return { trigger: "", outcome: "" };
    }).filter((line2) => line2.trigger !== "" || line2.outcome !== "");
  }
  function buildGuidanceRow(line2) {
    const row = document.createElement("div");
    row.className = "gram-frame-guidance-row";
    if (line2.trigger !== "") {
      const trigger = document.createElement("div");
      trigger.className = "gram-frame-guidance-trigger";
      trigger.textContent = line2.trigger;
      row.appendChild(trigger);
    }
    const outcome = document.createElement("div");
    outcome.className = line2.trigger === "" ? "gram-frame-guidance-note" : "gram-frame-guidance-outcome";
    outcome.textContent = line2.outcome;
    row.appendChild(outcome);
    return row;
  }
  function buildGuidanceHeading(section) {
    const title = document.createElement("h4");
    title.textContent = section.title;
    if (section.qualifier !== "") {
      const qualifier = document.createElement("span");
      qualifier.className = "gram-frame-guidance-qualifier";
      qualifier.textContent = ` (${section.qualifier})`;
      title.appendChild(qualifier);
    }
    return title;
  }
  function renderSecureGuidance(container, content) {
    container.replaceChildren();
    resolveGuidance(content).forEach((section) => {
      if (section.title !== "") {
        container.appendChild(buildGuidanceHeading(section));
      }
      section.lines.forEach((line2) => {
        container.appendChild(buildGuidanceRow(line2));
      });
    });
  }
  function updateGuidancePanel(guidancePanel, content) {
    if (!guidancePanel) {
      console.warn("Guidance panel element not found");
      return;
    }
    if (!content) {
      console.warn("No guidance content provided");
      return;
    }
    try {
      renderSecureGuidance(guidancePanel, content);
    } catch (error) {
      console.error("Error updating guidance panel:", error);
      guidancePanel.replaceChildren();
      const errorMsg = document.createElement("p");
      errorMsg.textContent = "Error loading guidance content";
      guidancePanel.appendChild(errorMsg);
    }
  }
  const hasChosen = /* @__PURE__ */ new WeakMap();
  function createGuidanceColumn(instance) {
    const stored = loadGuidancePreference();
    instance.state.guidanceCollapsed = stored === true;
    hasChosen.set(instance, stored !== null);
    const column = document.createElement("div");
    column.className = "gram-frame-guidance-column";
    const header = document.createElement("div");
    header.className = "gram-frame-guidance-header";
    const title = document.createElement("div");
    title.className = "gram-frame-guidance-title";
    const hide = document.createElement("button");
    hide.type = "button";
    hide.className = "gram-frame-guidance-hide";
    hide.textContent = "Hide";
    hide.title = "Hide guidance";
    hide.addEventListener("click", (event) => {
      event.preventDefault();
      setGuidanceCollapsed(instance, true);
    });
    header.appendChild(title);
    header.appendChild(hide);
    const body = document.createElement("div");
    body.className = "gram-frame-guidance";
    const rail = document.createElement("div");
    rail.className = "gram-frame-guidance-rail";
    const reveal = document.createElement("button");
    reveal.type = "button";
    reveal.className = "gram-frame-guidance-reveal";
    reveal.textContent = "›";
    reveal.title = "Show guidance";
    reveal.setAttribute("aria-label", "Show guidance");
    reveal.addEventListener("click", (event) => {
      event.preventDefault();
      setGuidanceCollapsed(instance, false);
    });
    const railLabel = document.createElement("div");
    railLabel.className = "gram-frame-guidance-rail-label";
    railLabel.textContent = "Guidance";
    rail.appendChild(reveal);
    rail.appendChild(railLabel);
    column.appendChild(header);
    column.appendChild(body);
    column.appendChild(rail);
    return { column, body, title };
  }
  function setGuidanceCollapsed(instance, collapsed) {
    instance.state.guidanceCollapsed = collapsed;
    hasChosen.set(instance, true);
    saveGuidancePreference(collapsed);
    applyGuidanceCollapsed(instance);
    dispatch(instance);
  }
  function applyGuidanceCollapsed(instance) {
    const { guidanceColumn } = instance.ui;
    if (!guidanceColumn) {
      return;
    }
    const collapsed = !!instance.state.guidanceCollapsed;
    const chosen = hasChosen.get(instance) === true;
    guidanceColumn.classList.toggle("gram-frame-guidance-collapsed", collapsed);
    guidanceColumn.classList.toggle("gram-frame-guidance-open", chosen && !collapsed);
  }
  function showGuidanceForMode(instance, mode) {
    const { guidanceTitle, guidancePanel } = instance.ui;
    if (guidanceTitle) {
      guidanceTitle.textContent = getModeDisplayName(instance.state.mode);
    }
    if (guidancePanel) {
      updateGuidancePanel(guidancePanel, withNavigationGuidance(mode.getGuidanceText()));
    }
  }
  function createUnifiedLayout(instance) {
    const unifiedLayoutContainer = document.createElement("div");
    unifiedLayoutContainer.className = "gram-frame-unified-layout";
    const modeColumn = document.createElement("div");
    modeColumn.className = "gram-frame-mode-column";
    const guidance = createGuidanceColumn(instance);
    const readout = createCursorReadout();
    const stylePanel = createStylePanel(instance);
    const tables = createAnnotationTables();
    unifiedLayoutContainer.appendChild(modeColumn);
    unifiedLayoutContainer.appendChild(guidance.column);
    unifiedLayoutContainer.appendChild(readout.column);
    unifiedLayoutContainer.appendChild(stylePanel);
    unifiedLayoutContainer.appendChild(tables.tables);
    return {
      unifiedLayoutContainer,
      modeColumn,
      guidanceColumn: guidance.column,
      guidancePanel: guidance.body,
      guidanceTitle: guidance.title,
      readoutColumn: readout.column,
      markersContainer: tables.markersContainer,
      harmonicsContainer: tables.harmonicsContainer,
      sidebandsContainer: tables.sidebandsContainer,
      timeLED: readout.timeLED,
      freqLED: readout.freqLED,
      speedLED: readout.speedLED,
      kicker: readout.kicker,
      colorPicker: stylePanel
    };
  }
  function updateUniversalCursorReadouts(instance, dataCoords) {
    const { selection } = instance.state;
    if (selection && selection.selectedId) {
      return;
    }
    if (instance.ui.timeLED) {
      const timeValue = instance.ui.timeLED.querySelector(".gram-frame-led-value");
      if (timeValue) {
        timeValue.textContent = formatTime(dataCoords.time);
      }
    }
    if (instance.ui.freqLED) {
      const freqValue = instance.ui.freqLED.querySelector(".gram-frame-led-value");
      if (freqValue) {
        freqValue.textContent = dataCoords.freq.toFixed(2);
      }
    }
  }
  function isPowerOfTwo(n) {
    return Number.isInteger(n) && n >= 2 && (n & n - 1) === 0;
  }
  function createFFT(size) {
    if (!isPowerOfTwo(size)) {
      throw new Error(`FFT size must be a power of two, got ${size}`);
    }
    const bits = Math.log2(size);
    const reversed = new Uint32Array(size);
    for (let i = 0; i < size; i++) {
      let r = 0;
      let x = i;
      for (let b = 0; b < bits; b++) {
        r = r << 1 | x & 1;
        x >>= 1;
      }
      reversed[i] = r;
    }
    const half = size / 2;
    const cos = new Float32Array(half);
    const sin = new Float32Array(half);
    for (let k = 0; k < half; k++) {
      const angle = -2 * Math.PI * k / size;
      cos[k] = Math.cos(angle);
      sin[k] = Math.sin(angle);
    }
    function forward(re, im) {
      if (re.length !== size || im.length !== size) {
        throw new Error(`FFT of size ${size} given arrays of length ${re.length}/${im.length}`);
      }
      for (let i = 0; i < size; i++) {
        const j = reversed[i];
        if (j > i) {
          let t = re[i];
          re[i] = re[j];
          re[j] = t;
          t = im[i];
          im[i] = im[j];
          im[j] = t;
        }
      }
      for (let span = 2; span <= size; span <<= 1) {
        const halfSpan = span >> 1;
        const stride = size / span;
        for (let start = 0; start < size; start += span) {
          for (let k = 0; k < halfSpan; k++) {
            const wr = cos[k * stride];
            const wi = sin[k * stride];
            const a = start + k;
            const b = a + halfSpan;
            const xr = re[b] * wr - im[b] * wi;
            const xi = re[b] * wi + im[b] * wr;
            re[b] = re[a] - xr;
            im[b] = im[a] - xi;
            re[a] += xr;
            im[a] += xi;
          }
        }
      }
    }
    return { size, forward };
  }
  const SPLIT_WINDOW_BINS = 25;
  function splitWindowBinsFor(hz, binWidth) {
    return Math.max(1, Math.round(hz / binWidth));
  }
  const SPLIT_GUARD_BINS = 3;
  const SPLIT_REJECT_DB = 3;
  const NORMALISATION_MODES = ["none", "split-window", "per-bin"];
  function powerToDecibels(grid) {
    const db = new Float32Array(grid.length);
    for (let i = 0; i < grid.length; i++) db[i] = 10 * Math.log10(grid[i] + 1e-12);
    return db;
  }
  function splitWindowPass(row, columns, prefix, out, window2, guard) {
    prefix[0] = 0;
    for (let k = 0; k < columns; k++) prefix[k + 1] = prefix[k] + row[k];
    for (let k = 0; k < columns; k++) {
      const outerFrom = Math.max(0, k - window2);
      const outerTo = Math.min(columns - 1, k + window2);
      const innerFrom = Math.max(0, k - guard);
      const innerTo = Math.min(columns - 1, k + guard);
      const count = outerTo - outerFrom + 1 - (innerTo - innerFrom + 1);
      if (count > 0) {
        const sum = prefix[outerTo + 1] - prefix[outerFrom] - (prefix[innerTo + 1] - prefix[innerFrom]);
        out[k] = sum / count;
      } else {
        out[k] = prefix[columns] / columns;
      }
    }
  }
  function splitWindowNormalise(db, frames, columns, windowBins) {
    const window2 = Math.min(windowBins, Math.max(1, Math.floor((columns - 1) / 2)));
    const guard = Math.min(SPLIT_GUARD_BINS, Math.max(0, window2 - 1));
    const out = new Float32Array(db.length);
    const row = new Float32Array(columns);
    const clipped = new Float32Array(columns);
    const background = new Float32Array(columns);
    const prefix = new Float32Array(columns + 1);
    for (let f = 0; f < frames; f++) {
      const start = f * columns;
      for (let k = 0; k < columns; k++) row[k] = db[start + k];
      splitWindowPass(row, columns, prefix, background, window2, guard);
      for (let k = 0; k < columns; k++) {
        clipped[k] = row[k] > background[k] + SPLIT_REJECT_DB ? background[k] : row[k];
      }
      splitWindowPass(clipped, columns, prefix, background, window2, guard);
      for (let k = 0; k < columns; k++) out[start + k] = row[k] - background[k];
    }
    return out;
  }
  function perBinMedians(db, frames, columns) {
    const cap = 4096;
    const stride = Math.max(1, Math.floor(frames / cap));
    const count = Math.floor((frames - 1) / stride) + 1;
    const sample = new Float32Array(count);
    const medians = new Float32Array(columns);
    for (let k = 0; k < columns; k++) {
      for (let f = 0, j = 0; f < frames; f += stride, j++) sample[j] = db[f * columns + k];
      const sorted = Float32Array.from(sample).sort();
      medians[k] = sorted[Math.floor(0.5 * (count - 1))];
    }
    return medians;
  }
  function normaliseDecibels(db, frames, columns, mode, options = {}) {
    if (mode === "split-window") {
      const windowBins = options.windowBins && options.windowBins >= 1 ? Math.floor(options.windowBins) : SPLIT_WINDOW_BINS;
      return splitWindowNormalise(db, frames, columns, windowBins);
    }
    if (mode === "per-bin") {
      const medians = perBinMedians(db, frames, columns);
      const out = new Float32Array(db.length);
      for (let f = 0; f < frames; f++) {
        const start = f * columns;
        for (let k = 0; k < columns; k++) out[start + k] = db[start + k] - medians[k];
      }
      return out;
    }
    return db;
  }
  const COLOUR_MAPS = Object.freeze(["colour", "grey", "inferno", "magma", "viridis", "plasma"]);
  const COLOUR_LUT = buildLut([
    [0, [0, 0, 110]],
    [0.45, [30, 70, 210]],
    [0.68, [225, 215, 40]],
    [0.88, [255, 140, 0]],
    [1, [220, 20, 20]]
  ]);
  const GREY_LUT = buildLut([
    [0, [255, 255, 255]],
    [1, [0, 0, 0]]
  ]);
  const INFERNO_LUT = fromHex(
    "00000401000501010601010802010a02020c02020e03021004031204031405041706041907051b08051d09061f0a07220b07240c08260d08290e092b10092d110a30120a32140b34150b37160b39180c3c190c3e1b0c411c0c431e0c451f0c48210c4a230c4c240c4f260c51280b53290b552b0b572d0b592f0a5b310a5c320a5e340a5f3609613809623909633b09643d09653e0966400a67420a68440a68450a69470b6a490b6a4a0c6b4c0c6b4d0d6c4f0d6c510e6c520e6d540f6d550f6d57106e59106e5a116e5c126e5d126e5f136e61136e62146e64156e65156e67166e69166e6a176e6c186e6d186e6f196e71196e721a6e741a6e751b6e771c6d781c6d7a1d6d7c1d6d7d1e6d7f1e6c801f6c82206c84206b85216b87216b88226a8a226a8c23698d23698f24699025689225689326679526679727669827669a28659b29649d29649f2a63a02a63a22b62a32c61a52c60a62d60a82e5fa92e5eab2f5ead305dae305cb0315bb1325ab3325ab43359b63458b73557b93556ba3655bc3754bd3853bf3952c03a51c13a50c33b4fc43c4ec63d4dc73e4cc83f4bca404acb4149cc4248ce4347cf4446d04545d24644d34743d44842d54a41d74b3fd84c3ed94d3dda4e3cdb503bdd513ade5238df5337e05536e15635e25734e35933e45a31e55c30e65d2fe75e2ee8602de9612bea632aeb6429eb6628ec6726ed6925ee6a24ef6c23ef6e21f06f20f1711ff1731df2741cf3761bf37819f47918f57b17f57d15f67e14f68013f78212f78410f8850ff8870ef8890cf98b0bf98c0af98e09fa9008fa9207fa9407fb9606fb9706fb9906fb9b06fb9d07fc9f07fca108fca309fca50afca60cfca80dfcaa0ffcac11fcae12fcb014fcb216fcb418fbb61afbb81dfbba1ffbbc21fbbe23fac026fac228fac42afac62df9c72ff9c932f9cb35f8cd37f8cf3af7d13df7d340f6d543f6d746f5d949f5db4cf4dd4ff4df53f4e156f3e35af3e55df2e661f2e865f2ea69f1ec6df1ed71f1ef75f1f179f2f27df2f482f3f586f3f68af4f88ef5f992f6fa96f8fb9af9fc9dfafda1fcffa4"
  );
  const MAGMA_LUT = fromHex(
    "00000401000501010601010802010902020b02020d03030f03031204041405041606051806051a07061c08071e0907200a08220b09240c09260d0a290e0b2b100b2d110c2f120d31130d34140e36150e38160f3b180f3d19103f1a10421c10441d11471e114920114b21114e22115024125325125527125829115a2a115c2c115f2d11612f116331116533106734106936106b38106c390f6e3b0f703d0f713f0f72400f74420f75440f764510774710784910784a10794c117a4e117b4f127b51127c52137c54137d56147d57157e59157e5a167e5c167f5d177f5f187f601880621980641a80651a80671b80681c816a1c816b1d816d1d816e1e81701f81721f817320817521817621817822817922827b23827c23827e24828025828125818326818426818627818827818928818b29818c29818e2a81902a81912b81932b80942c80962c80982d80992d809b2e7f9c2e7f9e2f7fa02f7fa1307ea3307ea5317ea6317da8327daa337dab337cad347cae347bb0357bb2357bb3367ab5367ab73779b83779ba3878bc3978bd3977bf3a77c03a76c23b75c43c75c53c74c73d73c83e73ca3e72cc3f71cd4071cf4070d0416fd2426fd3436ed5446dd6456cd8456cd9466bdb476adc4869de4968df4a68e04c67e24d66e34e65e44f64e55064e75263e85362e95462ea5661eb5760ec5860ed5a5fee5b5eef5d5ef05f5ef1605df2625df2645cf3655cf4675cf4695cf56b5cf66c5cf66e5cf7705cf7725cf8745cf8765cf9785df9795df97b5dfa7d5efa7f5efa815ffb835ffb8560fb8761fc8961fc8a62fc8c63fc8e64fc9065fd9266fd9467fd9668fd9869fd9a6afd9b6bfe9d6cfe9f6dfea16efea36ffea571fea772fea973feaa74feac76feae77feb078feb27afeb47bfeb67cfeb77efeb97ffebb81febd82febf84fec185fec287fec488fec68afec88cfeca8dfecc8ffecd90fecf92fed194fed395fed597fed799fed89afdda9cfddc9efddea0fde0a1fde2a3fde3a5fde5a7fde7a9fde9aafdebacfcecaefceeb0fcf0b2fcf2b4fcf4b6fcf6b8fcf7b9fcf9bbfcfbbdfcfdbf"
  );
  const VIRIDIS_LUT = fromHex(
    "44015444025645045745055946075a46085c460a5d460b5e470d60470e6147106347116447136548146748166848176948186a481a6c481b6d481c6e481d6f481f70482071482173482374482475482576482677482878482979472a7a472c7a472d7b472e7c472f7d46307e46327e46337f463480453581453781453882443983443a83443b84433d84433e85423f854240864241864142874144874045884046883f47883f48893e49893e4a893e4c8a3d4d8a3d4e8a3c4f8a3c508b3b518b3b528b3a538b3a548c39558c39568c38588c38598c375a8c375b8d365c8d365d8d355e8d355f8d34608d34618d33628d33638d32648e32658e31668e31678e31688e30698e306a8e2f6b8e2f6c8e2e6d8e2e6e8e2e6f8e2d708e2d718e2c718e2c728e2c738e2b748e2b758e2a768e2a778e2a788e29798e297a8e297b8e287c8e287d8e277e8e277f8e27808e26818e26828e26828e25838e25848e25858e24868e24878e23888e23898e238a8d228b8d228c8d228d8d218e8d218f8d21908d21918c20928c20928c20938c1f948c1f958b1f968b1f978b1f988b1f998a1f9a8a1e9b8a1e9c891e9d891f9e891f9f881fa0881fa1881fa1871fa28720a38620a48621a58521a68522a78522a88423a98324aa8325ab8225ac8226ad8127ad8128ae8029af7f2ab07f2cb17e2db27d2eb37c2fb47c31b57b32b67a34b67935b77937b87838b9773aba763bbb753dbc743fbc7340bd7242be7144bf7046c06f48c16e4ac16d4cc26c4ec36b50c46a52c56954c56856c66758c7655ac8645cc8635ec96260ca6063cb5f65cb5e67cc5c69cd5b6ccd5a6ece5870cf5773d05675d05477d1537ad1517cd2507fd34e81d34d84d44b86d54989d5488bd6468ed64590d74393d74195d84098d83e9bd93c9dd93ba0da39a2da37a5db36a8db34aadc32addc30b0dd2fb2dd2db5de2bb8de29bade28bddf26c0df25c2df23c5e021c8e020cae11fcde11dd0e11cd2e21bd5e21ad8e219dae319dde318dfe318e2e418e5e419e7e419eae51aece51befe51cf1e51df4e61ef6e620f8e621fbe723fde725"
  );
  const PLASMA_LUT = fromHex(
    "0d088710078813078916078a19068c1b068d1d068e20068f2206902406912605912805922a05932c05942e05952f059631059733059735049837049938049a3a049a3c049b3e049c3f049c41049d43039e44039e46039f48039f4903a04b03a14c02a14e02a25002a25102a35302a35502a45601a45801a45901a55b01a55c01a65e01a66001a66100a76300a76400a76600a76700a86900a86a00a86c00a86e00a86f00a87100a87201a87401a87501a87701a87801a87a02a87b02a87d03a87e03a88004a88104a78305a78405a78606a68707a68808a68a09a58b0aa58d0ba58e0ca48f0da4910ea3920fa39410a29511a19613a19814a099159f9a169f9c179e9d189d9e199da01a9ca11b9ba21d9aa31e9aa51f99a62098a72197a82296aa2395ab2494ac2694ad2793ae2892b02991b12a90b22b8fb32c8eb42e8db52f8cb6308bb7318ab83289ba3388bb3488bc3587bd3786be3885bf3984c03a83c13b82c23c81c33d80c43e7fc5407ec6417dc7427cc8437bc9447aca457acb4679cc4778cc4977cd4a76ce4b75cf4c74d04d73d14e72d24f71d35171d45270d5536fd5546ed6556dd7566cd8576bd9586ada5a6ada5b69db5c68dc5d67dd5e66de5f65de6164df6263e06363e16462e26561e26660e3685fe4695ee56a5de56b5de66c5ce76e5be76f5ae87059e97158e97257ea7457eb7556eb7655ec7754ed7953ed7a52ee7b51ef7c51ef7e50f07f4ff0804ef1814df1834cf2844bf3854bf3874af48849f48948f58b47f58c46f68d45f68f44f79044f79143f79342f89441f89540f9973ff9983ef99a3efa9b3dfa9c3cfa9e3bfb9f3afba139fba238fca338fca537fca636fca835fca934fdab33fdac33fdae32fdaf31fdb130fdb22ffdb42ffdb52efeb72dfeb82cfeba2cfebb2bfebd2afebe2afec029fdc229fdc328fdc527fdc627fdc827fdca26fdcb26fccd25fcce25fcd025fcd225fbd324fbd524fbd724fad824fada24f9dc24f9dd25f8df25f8e125f7e225f7e425f6e626f6e826f5e926f5eb27f4ed27f3ee27f3f027f2f227f1f426f1f525f0f724f0f921"
  );
  function fromHex(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < bytes.length; i++) {
      bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
    }
    return bytes;
  }
  const LUTS = {
    colour: COLOUR_LUT,
    grey: GREY_LUT,
    inferno: INFERNO_LUT,
    magma: MAGMA_LUT,
    viridis: VIRIDIS_LUT,
    plasma: PLASMA_LUT
  };
  function lutFor(map) {
    return LUTS[map] || COLOUR_LUT;
  }
  function isDarkForLoud(map) {
    return map === "grey";
  }
  function buildLut(stops) {
    const lut = new Uint8Array(256 * 3);
    for (let i = 0; i < 256; i++) {
      const t = i / 255;
      let s = 0;
      while (s < stops.length - 2 && t > stops[s + 1][0]) s++;
      const [p0, c0] = stops[s];
      const [p1, c1] = stops[s + 1];
      const f = p1 === p0 ? 0 : Math.max(0, Math.min(1, (t - p0) / (p1 - p0)));
      for (let ch = 0; ch < 3; ch++) {
        lut[i * 3 + ch] = Math.round(c0[ch] + (c1[ch] - c0[ch]) * f);
      }
    }
    return lut;
  }
  function levelsToPixels(levels, frames, columns, map = "colour") {
    const lut = lutFor(map);
    const pixels = new Uint8ClampedArray(frames * columns * 4);
    for (let f = 0; f < frames; f++) {
      const y = frames - 1 - f;
      const rowIn = f * columns;
      const rowOut = y * columns * 4;
      for (let k = 0; k < columns; k++) {
        const level = levels[rowIn + k] * 3;
        const p = rowOut + k * 4;
        pixels[p] = lut[level];
        pixels[p + 1] = lut[level + 1];
        pixels[p + 2] = lut[level + 2];
        pixels[p + 3] = 255;
      }
    }
    return pixels;
  }
  const MAX_GRAM_ROWS = 32768;
  const MAX_GRAM_COLUMNS = 4096;
  const LEVEL_SCOPES = ["file", "row"];
  const ROW_SAMPLE_CAP = 1024;
  function fittingHopSize(frames, hopSize) {
    let hop = hopSize;
    while (Math.ceil(frames * hopSize / hop) > MAX_GRAM_ROWS) hop *= 2;
    return hop;
  }
  function fitGramSize(frames, columns, plan) {
    if (columns > MAX_GRAM_COLUMNS) {
      throw new Error(
        `The analysed spectrogram would be ${columns} columns wide, above the ${MAX_GRAM_COLUMNS}-column limit. Lower fft-size (currently ${plan.fftSize}) or narrow freq-start/freq-end.`
      );
    }
    if (frames <= MAX_GRAM_ROWS) {
      return null;
    }
    return { parameter: "hop-size", requested: plan.hopSize, used: fittingHopSize(frames, plan.hopSize) };
  }
  function checkGramSize(frames, columns, plan) {
    if (frames > MAX_GRAM_ROWS) {
      throw new Error(
        `The analysed spectrogram would be ${frames} rows tall, above the ${MAX_GRAM_ROWS}-row limit. Set hop-size to ${fittingHopSize(frames, plan.hopSize)} (or shorten the recording).`
      );
    }
    if (columns > MAX_GRAM_COLUMNS) {
      throw new Error(
        `The analysed spectrogram would be ${columns} columns wide, above the ${MAX_GRAM_COLUMNS}-column limit. Lower fft-size (currently ${plan.fftSize}) or narrow freq-start/freq-end.`
      );
    }
  }
  function percentileRange(db, from, to, floorPercentile, ceilingPercentile, span, sampleCap) {
    const n = to - from;
    const stride = Math.max(1, Math.floor(n / sampleCap));
    const sampleCount = Math.floor((n - 1) / stride) + 1;
    const sample = new Float32Array(sampleCount);
    for (let i = from, j = 0; i < to; i += stride, j++) sample[j] = db[i];
    sample.sort();
    const at = (percentile) => sample[Math.min(sampleCount - 1, Math.max(0, Math.floor(percentile / 100 * (sampleCount - 1))))];
    const floor = at(floorPercentile);
    let ceiling = span !== null && span > 0 ? floor + span : at(ceilingPercentile);
    if (ceiling <= floor) {
      ceiling = floor + 1;
    }
    return { floor, ceiling };
  }
  function writeLevels(db, levels, from, to, range) {
    const scale = 255 / (range.ceiling - range.floor);
    for (let i = from; i < to; i++) {
      const v = (db[i] - range.floor) * scale;
      levels[i] = v <= 0 ? 0 : v >= 255 ? 255 : Math.round(v);
    }
  }
  function decibelsToLevels(db, options = {}) {
    const floorPercentile = options.floorPercentile === void 0 ? 5 : options.floorPercentile;
    const ceilingPercentile = options.ceilingPercentile === void 0 ? 99.9 : options.ceilingPercentile;
    const span = options.levelSpan === void 0 ? null : options.levelSpan;
    const n = db.length;
    const levels = new Uint8Array(n);
    const columns = options.columns || 0;
    if (options.levelScope === "row" && columns > 0) {
      for (let from = 0; from < n; from += columns) {
        const to = Math.min(n, from + columns);
        writeLevels(db, levels, from, to, percentileRange(db, from, to, floorPercentile, ceilingPercentile, span, ROW_SAMPLE_CAP));
      }
      return levels;
    }
    writeLevels(db, levels, 0, n, percentileRange(db, 0, n, floorPercentile, ceilingPercentile, span, 1e6));
    return levels;
  }
  function powerToLevels(grid, options = {}) {
    const db = powerToDecibels(grid);
    const normalisation = options.normalisation || "none";
    const normalised = normalisation === "none" ? db : normaliseDecibels(db, options.frames || 0, options.columns || 0, normalisation, { windowBins: options.windowBins });
    return decibelsToLevels(normalised, options);
  }
  function paintGram(levels, frames, columns, map = "colour") {
    const canvas = document.createElement("canvas");
    canvas.width = columns;
    canvas.height = frames;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error(`Could not create a ${columns}×${frames} canvas to paint the spectrogram`);
    }
    const image = context.createImageData(columns, frames);
    image.data.set(levelsToPixels(levels, frames, columns, map));
    context.putImageData(image, 0, 0);
    const url = canvas.toDataURL("image/png");
    if (!url || !url.startsWith("data:image/png")) {
      throw new Error(`The browser could not encode a ${columns}×${frames} spectrogram image`);
    }
    return url;
  }
  function parseConfigValue(text) {
    if (typeof text !== "string") {
      return null;
    }
    const trimmed = text.trim();
    if (trimmed === "") {
      return null;
    }
    const value = Number(trimmed);
    return Number.isFinite(value) ? value : null;
  }
  function numberParam(params, name) {
    const cell = params.get(name);
    if (!cell) {
      return null;
    }
    const value = parseConfigValue(cell.text);
    if (value === null) {
      console.warn(`GramFrame: Ignoring ${name} in row ${cell.row} — "${cell.text}" is not a single numeric value`);
      return null;
    }
    return value;
  }
  function choiceParam(params, name, choices) {
    const cell = params.get(name);
    if (!cell) return null;
    const value = cell.text.trim().toLowerCase();
    if (!choices.includes(value)) {
      throw new Error(`Invalid ${name}: "${cell.text}" — must be one of ${choices.join(", ")}`);
    }
    return value;
  }
  function positiveParam(params, name, unit) {
    const value = numberParam(params, name);
    if (value !== null && !(value > 0)) {
      throw new Error(`Invalid ${name}: ${value} — must be a number of ${unit} above zero`);
    }
    return value;
  }
  function readParameterRows(configTable) {
    const params = /* @__PURE__ */ new Map();
    configTable.querySelectorAll("tr").forEach((row, index) => {
      var _a, _b;
      try {
        const cells = row.querySelectorAll("td");
        if (cells.length === 2) {
          const name = ((_a = cells[0].textContent) == null ? void 0 : _a.trim()) || "";
          const text = ((_b = cells[1].textContent) == null ? void 0 : _b.trim()) || "";
          if (name) {
            params.set(name, { text, row: index + 1 });
          }
        }
      } catch (error) {
        console.warn(`GramFrame: Error parsing row ${index + 1}:`, error instanceof Error ? error.message : String(error));
      }
    });
    return params;
  }
  function extractImageConfig(instance, imgElement, params) {
    const srcAttribute = imgElement.getAttribute("src");
    if (!srcAttribute || !srcAttribute.trim()) {
      throw new Error("Image element has no src attribute: the spectrogram <img> must point at an image");
    }
    instance.state.imageDetails.url = imgElement.src;
    const timeStart = numberParam(params, "time-start");
    const timeEnd = numberParam(params, "time-end");
    const freqStart = numberParam(params, "freq-start");
    const freqEnd = numberParam(params, "freq-end");
    const config = instance.state.config;
    if (timeStart === null || timeEnd === null) {
      throw new Error("Missing required time configuration: both time-start and time-end must be present with valid numeric values");
    }
    if (timeStart >= timeEnd) {
      throw new Error(`Invalid time range: start (${timeStart}) must be less than end (${timeEnd})`);
    }
    config.timeMin = timeStart;
    config.timeMax = timeEnd;
    if (freqStart === null || freqEnd === null) {
      throw new Error("Missing required frequency configuration: both freq-start and freq-end must be present with valid numeric values");
    }
    if (freqStart >= freqEnd) {
      throw new Error(`Invalid frequency range: start (${freqStart}) must be less than end (${freqEnd})`);
    }
    config.freqMin = freqStart;
    config.freqMax = freqEnd;
  }
  function readPaintingParams(params, player) {
    const frameAverage = numberParam(params, "frame-average");
    if (frameAverage !== null) {
      if (!Number.isInteger(frameAverage) || frameAverage < 1 || frameAverage > 64) {
        throw new Error(`Invalid frame-average: ${frameAverage} — must be a whole number between 1 and 64`);
      }
      player.analysis.frameAverage = frameAverage;
    }
    const normalisation = choiceParam(params, "normalisation", NORMALISATION_MODES);
    if (normalisation !== null) player.analysis.normalisation = normalisation;
    const colourMap = choiceParam(params, "colour-map", COLOUR_MAPS);
    if (colourMap !== null) player.analysis.colourMap = /** @type {import('../audio/colourMap.js').ColourMapName} */
    colourMap;
    const levelScope = choiceParam(params, "level-scope", LEVEL_SCOPES);
    if (levelScope !== null) player.analysis.levelScope = levelScope;
    const normalisationWindow = positiveParam(params, "normalisation-window", "hertz");
    if (normalisationWindow !== null) player.analysis.normalisationWindow = normalisationWindow;
    const levelSpan = positiveParam(params, "level-span", "decibels");
    if (levelSpan !== null) player.analysis.levelSpan = levelSpan;
    const levelFloor = numberParam(params, "level-floor");
    if (levelFloor !== null) {
      player.analysis.levelFloor = levelFloor;
    }
    const levelCeiling = numberParam(params, "level-ceiling");
    if (levelCeiling !== null) {
      player.analysis.levelCeiling = levelCeiling;
    }
    const { levelFloor: floor, levelCeiling: ceiling } = player.analysis;
    if (floor < 0 || ceiling > 100 || floor >= ceiling) {
      throw new Error(`Invalid display percentiles: level-floor ${floor} and level-ceiling ${ceiling} — both must lie in 0..100 with the floor below the ceiling`);
    }
  }
  function extractAudioConfig(instance, audioElement, params) {
    const src = audioElement.getAttribute("src") ? audioElement.src : "";
    if (!src) {
      throw new Error("Audio element has no src attribute");
    }
    const state = instance.state;
    const player = state.player;
    player.active = true;
    player.source = src;
    state.imageDetails.url = src;
    if (params.has("time-start") || params.has("time-end")) {
      console.warn("GramFrame: time-start/time-end are ignored on an audio-sourced gram — the recording defines the time range");
    }
    const fftSize = numberParam(params, "fft-size");
    if (fftSize !== null) {
      if (!isPowerOfTwo(fftSize) || fftSize < 64 || fftSize > 32768) {
        throw new Error(`Invalid fft-size: ${fftSize} — must be a power of two between 64 and 32768`);
      }
      player.analysis.fftSize = fftSize;
    }
    const hopSize = numberParam(params, "hop-size");
    if (hopSize !== null) {
      if (!Number.isInteger(hopSize) || hopSize < 1) {
        throw new Error(`Invalid hop-size: ${hopSize} — must be a whole number of samples, 1 or more`);
      }
      player.analysis.hopSize = hopSize;
    } else {
      player.analysis.hopSize = player.analysis.fftSize / 2;
    }
    const freqStart = numberParam(params, "freq-start");
    if (freqStart !== null) {
      if (freqStart < 0) {
        throw new Error(`Invalid freq-start: ${freqStart} — must not be negative`);
      }
      player.analysis.freqStart = freqStart;
    }
    const freqEnd = numberParam(params, "freq-end");
    if (freqEnd !== null) {
      if (freqEnd <= player.analysis.freqStart) {
        throw new Error(`Invalid frequency range: freq-end (${freqEnd}) must be greater than freq-start (${player.analysis.freqStart})`);
      }
      player.analysis.freqEnd = freqEnd;
    }
    const windowSeconds = numberParam(params, "window-seconds");
    if (windowSeconds !== null) {
      if (!(windowSeconds > 0)) {
        throw new Error(`Invalid window-seconds: ${windowSeconds} — must be greater than 0`);
      }
      player.windowSeconds = windowSeconds;
    }
    readPaintingParams(params, player);
    const preservePitch = params.get("preserve-pitch");
    if (preservePitch) {
      const value = preservePitch.text.trim().toLowerCase();
      if (!["true", "false", "yes", "no"].includes(value)) {
        throw new Error(`Invalid preserve-pitch: "${preservePitch.text}" — must be true or false`);
      }
      player.preservesPitch = value === "true" || value === "yes";
    }
  }
  function extractConfigData(instance) {
    if (!instance.configTable) {
      console.warn("GramFrame: No config table provided for configuration extraction");
      return;
    }
    const params = readParameterRows(instance.configTable);
    const audioElement = instance.configTable.querySelector("audio");
    const imgElement = instance.configTable.querySelector("img");
    if (audioElement) {
      if (imgElement) {
        console.warn("GramFrame: the config table holds both an <audio> and an <img>; the audio is used and the image ignored");
      }
      extractAudioConfig(instance, audioElement, params);
      return;
    }
    if (!imgElement) {
      throw new Error("No image element found in config table: the first row must contain an <img> with the spectrogram");
    }
    extractImageConfig(instance, imgElement, params);
  }
  function createComponentStructure(instanceId) {
    const container = document.createElement("div");
    container.className = "gram-frame-container gram-frame-loading";
    const table = document.createElement("div");
    table.className = "gram-frame-layout";
    container.appendChild(table);
    const modeRow = document.createElement("div");
    modeRow.className = "gram-frame-row";
    table.appendChild(modeRow);
    const modeCell = document.createElement("div");
    modeCell.className = "gram-frame-cell gram-frame-mode-header";
    modeRow.appendChild(modeCell);
    const mainRow = document.createElement("div");
    mainRow.className = "gram-frame-row";
    mainRow.style.height = "100%";
    table.appendChild(mainRow);
    const mainCell = document.createElement("div");
    mainCell.className = "gram-frame-cell gram-frame-main-panel";
    mainRow.appendChild(mainCell);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "gram-frame-svg");
    svg.style.width = "100%";
    svg.style.height = "100%";
    svg.style.display = "block";
    mainCell.appendChild(svg);
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.appendChild(defs);
    const clipPathId = `imageClip-${instanceId || Date.now()}`;
    const clipPath = document.createElementNS("http://www.w3.org/2000/svg", "clipPath");
    clipPath.setAttribute("id", clipPathId);
    defs.appendChild(clipPath);
    const imageClipRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    clipPath.appendChild(imageClipRect);
    const cursorClipPathId = `cursorClip-${instanceId || Date.now()}`;
    const cursorClipPath = document.createElementNS("http://www.w3.org/2000/svg", "clipPath");
    cursorClipPath.setAttribute("id", cursorClipPathId);
    defs.appendChild(cursorClipPath);
    const cursorClipRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    cursorClipPath.appendChild(cursorClipRect);
    const spectrogramImage = document.createElementNS("http://www.w3.org/2000/svg", "image");
    spectrogramImage.setAttribute("class", "gram-frame-spectrogram-image");
    spectrogramImage.setAttribute("clip-path", `url(#${clipPathId})`);
    spectrogramImage.setAttribute("preserveAspectRatio", "none");
    svg.appendChild(spectrogramImage);
    const cursorGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    cursorGroup.setAttribute("class", "gram-frame-cursors");
    cursorGroup.setAttribute("clip-path", `url(#${cursorClipPathId})`);
    svg.appendChild(cursorGroup);
    const axesGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    axesGroup.setAttribute("class", "gram-frame-axes");
    svg.appendChild(axesGroup);
    const readoutPanel = document.createElement("div");
    readoutPanel.className = "gram-frame-readout";
    return {
      container,
      table,
      modeRow,
      modeCell,
      mainRow,
      mainCell,
      readoutPanel,
      svg,
      spectrogramImage,
      cursorGroup,
      axesGroup,
      imageClipRect,
      cursorClipRect
    };
  }
  function replaceConfigTable(instance, container, configTable) {
    if (configTable && configTable.parentNode) {
      configTable.parentNode.replaceChild(container, configTable);
      container.__gramFrameInstance = instance;
    }
  }
  function setupComponentTable(instance, configTable) {
    const domElements = createComponentStructure(instance.instanceId);
    replaceConfigTable(instance, domElements.container, configTable);
    return domElements;
  }
  function setupSpectrogramComponents(instance, configTable) {
    extractConfigData(instance);
    return setupComponentTable(instance, configTable);
  }
  function screenToDataWithZoom(instance, event) {
    const point = screenToData(
      event.clientX,
      event.clientY,
      instance.ui.svg,
      instance.state,
      instance.ui.spectrogramImage
    );
    if (!isWithinImage(point.svg, instance.state, instance.ui.spectrogramImage)) {
      return null;
    }
    return {
      svgCoords: point.svg,
      imageX: point.image.x,
      imageY: point.image.y,
      dataCoords: point.data
    };
  }
  function acceptsOffImageDrag(instance) {
    const mode = instance.currentMode;
    return !!mode && typeof mode.acceptsOffImageDrag === "function" && mode.acceptsOffImageDrag();
  }
  function unboundedDataCoords(instance, event) {
    return screenToData(
      event.clientX,
      event.clientY,
      instance.ui.svg,
      instance.state,
      instance.ui.spectrogramImage
    ).data;
  }
  const SVG_NS$4 = "http://www.w3.org/2000/svg";
  const ICON_BOX = 24;
  const LINE_BOX = 16;
  function handShapes() {
    const fingers = [
      { x: 7.1, y: 4.5, height: 8.5 },
      // index
      { x: 10.2, y: 2.8, height: 10.2 },
      // middle
      { x: 13.3, y: 3.8, height: 9.2 },
      // ring
      { x: 16.4, y: 6.2, height: 6.8 }
      // little
    ];
    const shapes = fingers.map(({ x, y, height }) => rect(x, y, 2.7, height, 1.35));
    const thumb = rect(2.6, 11.4, 2.7, 7.6, 1.35);
    thumb.setAttribute("transform", "rotate(-38 4 15)");
    shapes.push(thumb);
    shapes.push(rect(7.1, 10, 12, 10.6, 4));
    return shapes;
  }
  function fitShapes() {
    return [
      "M4 9V6a2 2 0 0 1 2-2h3",
      "M15 4h3a2 2 0 0 1 2 2v3",
      "M20 15v3a2 2 0 0 1-2 2h-3",
      "M9 20H6a2 2 0 0 1-2-2v-3"
    ].map((d) => {
      const path = document.createElementNS(SVG_NS$4, "path");
      path.setAttribute("d", d);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", "currentColor");
      path.setAttribute("stroke-width", "2.2");
      path.setAttribute("stroke-linecap", "round");
      path.setAttribute("stroke-linejoin", "round");
      return path;
    });
  }
  function rect(x, y, width, height, radius) {
    const shape = document.createElementNS(SVG_NS$4, "rect");
    shape.setAttribute("x", String(x));
    shape.setAttribute("y", String(y));
    shape.setAttribute("width", String(width));
    shape.setAttribute("height", String(height));
    shape.setAttribute("rx", String(radius));
    shape.setAttribute("fill", "currentColor");
    return shape;
  }
  function line(d) {
    const path = document.createElementNS(SVG_NS$4, "path");
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", String(LINE_STROKE));
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    return path;
  }
  function solid(d) {
    const path = document.createElementNS(SVG_NS$4, "path");
    path.setAttribute("d", d);
    path.setAttribute("fill", "currentColor");
    return path;
  }
  function dot(cx, cy, r) {
    const shape = document.createElementNS(SVG_NS$4, "circle");
    shape.setAttribute("cx", String(cx));
    shape.setAttribute("cy", String(cy));
    shape.setAttribute("r", String(r));
    shape.setAttribute("fill", "currentColor");
    return shape;
  }
  const LINE_STROKE = 1.3;
  function crossCursorShapes() {
    const ring = document.createElementNS(SVG_NS$4, "circle");
    ring.setAttribute("cx", "8");
    ring.setAttribute("cy", "8");
    ring.setAttribute("r", "3.4");
    ring.setAttribute("fill", "none");
    ring.setAttribute("stroke", "currentColor");
    ring.setAttribute("stroke-width", String(LINE_STROKE));
    return [ring, line("M8 .8v3.4M8 11.8v3.4M.8 8h3.4M11.8 8h3.4")];
  }
  function harmonicsShapes() {
    return [line("M2 3v10M5.5 5v8M9 2v11M12.5 6v7")];
  }
  function sidebandsShapes() {
    return [line("M8 1.5v13M4.5 5v6M1.5 6.5v3M11.5 5v6M14.5 6.5v3")];
  }
  function dopplerShapes() {
    return [line("M3 14c0-5 10-7 10-12"), dot(3, 14, 1.1), dot(13, 2, 1.1)];
  }
  function bookmarkShapes() {
    const path = line("M4 2h8v12l-4-3.2L4 14z");
    path.setAttribute("stroke-width", "1.4");
    return [path];
  }
  function volumeShapes() {
    return [line("M8 2.5 4.5 5.5H2v5h2.5L8 13.5zM11 5.5a3.4 3.4 0 0 1 0 5M13 3.5a6 6 0 0 1 0 9")];
  }
  function mutedShapes() {
    return [line("M8 2.5 4.5 5.5H2v5h2.5L8 13.5z"), line("M11 6l4 4M15 6l-4 4")];
  }
  function playShapes() {
    return [solid("M4 2.5 13 8l-9 5.5z")];
  }
  function pauseShapes() {
    return [solid("M3.5 2.5h3.2v11H3.5zM9.3 2.5h3.2v11H9.3z")];
  }
  function restartShapes() {
    return [solid("M4 3h1.6v10H4zM13 3v10L6.4 8z")];
  }
  const ICONS = {
    hand: { box: ICON_BOX, build: handShapes },
    fit: { box: ICON_BOX, build: fitShapes },
    "cross-cursor": { box: LINE_BOX, build: crossCursorShapes },
    harmonics: { box: LINE_BOX, build: harmonicsShapes },
    sidebands: { box: LINE_BOX, build: sidebandsShapes },
    doppler: { box: LINE_BOX, build: dopplerShapes },
    bookmark: { box: LINE_BOX, build: bookmarkShapes },
    volume: { box: LINE_BOX, build: volumeShapes },
    muted: { box: LINE_BOX, build: mutedShapes },
    play: { box: LINE_BOX, build: playShapes },
    pause: { box: LINE_BOX, build: pauseShapes },
    restart: { box: LINE_BOX, build: restartShapes }
  };
  function createIcon(name) {
    const entry = name ? ICONS[name] : void 0;
    if (!entry) {
      return null;
    }
    const svg = (
      /** @type {SVGSVGElement} */
      document.createElementNS(SVG_NS$4, "svg")
    );
    svg.setAttribute("class", "gram-frame-icon");
    svg.setAttribute("viewBox", `0 0 ${entry.box} ${entry.box}`);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    entry.build().forEach((shape) => svg.appendChild(shape));
    return svg;
  }
  function createIconLabel(text) {
    const label = document.createElement("span");
    label.className = "gram-frame-visually-hidden";
    label.textContent = text;
    return label;
  }
  function createModeSwitchingUI(modeCell, activeMode, modeSwitchCallback, modes = {}) {
    const modesContainer = document.createElement("div");
    modesContainer.className = "gram-frame-modes";
    const kicker = document.createElement("div");
    kicker.className = "gram-frame-kicker";
    kicker.textContent = "Mode";
    modesContainer.appendChild(kicker);
    const list = document.createElement("div");
    list.className = "gram-frame-mode-list";
    modesContainer.appendChild(list);
    const commandRow = document.createElement("div");
    commandRow.className = "gram-frame-mode-commands";
    const modeTypes = MODE_NAMES;
    const modeButtons = {};
    const commandButtons = {};
    modeTypes.forEach((modeType) => {
      const modeInstance = modes[modeType];
      commandButtons[modeType] = [];
      const button2 = document.createElement("button");
      button2.type = "button";
      button2.className = "gram-frame-mode-btn";
      const displayName = getModeDisplayName(modeType);
      applyModeFace(button2, displayName, getModeIcon(modeType));
      button2.title = displayName;
      button2.dataset.mode = modeType;
      if (modeType === activeMode) {
        button2.classList.add("active");
      }
      if (modeInstance && typeof modeInstance.isEnabled === "function" && !modeInstance.isEnabled()) {
        button2.disabled = true;
        button2.classList.add("disabled");
      }
      button2.addEventListener("click", (event) => {
        event.preventDefault();
        if (!button2.disabled) {
          modeSwitchCallback(modeType);
        }
      });
      modeButtons[modeType] = button2;
      list.appendChild(button2);
      const commandButtonDefs = modeInstance && typeof modeInstance.getCommandButtons === "function" ? modeInstance.getCommandButtons() : [];
      commandButtonDefs.forEach((buttonDef) => {
        const cmdButton = createCommandButton(buttonDef);
        commandRow.appendChild(cmdButton);
        commandButtons[modeType].push(cmdButton);
      });
    });
    const spacer = document.createElement("div");
    spacer.className = "gram-frame-mode-spacer";
    modesContainer.appendChild(spacer);
    modesContainer.appendChild(commandRow);
    modeCell.appendChild(modesContainer);
    return {
      modesContainer,
      modeButtons,
      commandButtons
    };
  }
  function applyModeFace(button2, text, icon) {
    const glyph = createIcon(icon);
    if (glyph) {
      button2.appendChild(glyph);
    }
    const label = document.createElement("span");
    label.className = "gram-frame-mode-btn-label";
    label.textContent = text;
    button2.appendChild(label);
  }
  function applyButtonFace(button2, text, icon) {
    const glyph = createIcon(icon);
    if (!glyph) {
      button2.textContent = text;
      return;
    }
    button2.classList.add("gram-frame-icon-btn");
    button2.appendChild(glyph);
    button2.appendChild(createIconLabel(text));
  }
  function createCommandButton(buttonDef) {
    const button2 = document.createElement("button");
    button2.type = "button";
    button2.className = "gram-frame-command-btn";
    applyButtonFace(button2, buttonDef.label, buttonDef.icon);
    button2.title = buttonDef.title;
    if (buttonDef.isEnabled) {
      button2.disabled = !buttonDef.isEnabled();
    }
    button2.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      buttonDef.action();
    });
    return button2;
  }
  function updateCommandButtonStates(commandButtons, modes) {
    Object.keys(commandButtons).forEach((modeType) => {
      const modeInstance = modes[modeType];
      if (modeInstance && typeof modeInstance.getCommandButtons === "function") {
        const buttonDefs = modeInstance.getCommandButtons();
        const buttons = commandButtons[modeType];
        buttons.forEach((button2, index) => {
          const buttonDef = buttonDefs[index];
          if (buttonDef && buttonDef.isEnabled) {
            button2.disabled = !buttonDef.isEnabled();
          }
        });
      }
    });
  }
  function updateModeButtonStates(modeButtons, modes) {
    Object.keys(modeButtons).forEach((modeType) => {
      const modeInstance = modes[modeType];
      const button2 = modeButtons[modeType];
      if (modeInstance && typeof modeInstance.isEnabled === "function" && button2) {
        const isEnabled = modeInstance.isEnabled();
        button2.disabled = !isEnabled;
        if (isEnabled) {
          button2.classList.remove("disabled");
        } else {
          button2.classList.add("disabled");
        }
      }
    });
  }
  function anchorHoldingPoint(point, anchor, level, newLevel) {
    if (newLevel <= 1) {
      return 0.5;
    }
    return clamp01$1((anchor * (1 - level) + point * (level - newLevel)) / (1 - newLevel));
  }
  function viewCentre(anchor, level) {
    if (level <= 1) {
      return 0.5;
    }
    return anchor + (0.5 - anchor) / level;
  }
  function anchorForCentre(centre, level) {
    if (level <= 1) {
      return 0.5;
    }
    const visibleFraction = 1 / level;
    return clamp01$1((centre - visibleFraction / 2) / (1 - visibleFraction));
  }
  function clamp01$1(value) {
    return Math.max(0, Math.min(1, value));
  }
  const BOTTOM_GAP = 16;
  function isLandscape(instance) {
    const { width, height } = baseRenderSize(instance);
    return width > 0 && height > 0 && width > height;
  }
  function computeAvailableRenderSize(instance) {
    const margins = instance.state.margins;
    const { width: baseWidth, height: baseHeight } = baseRenderSize(instance);
    const cell = instance.ui.mainCell;
    const svg = instance.ui.svg;
    if (!cell || !svg) {
      return { width: baseWidth, height: baseHeight };
    }
    const cellStyle = window.getComputedStyle(cell);
    const padL = parseFloat(cellStyle.paddingLeft) || 0;
    const padR = parseFloat(cellStyle.paddingRight) || 0;
    const svgStyle = window.getComputedStyle(svg);
    const svgBorderX = (parseFloat(svgStyle.borderLeftWidth) || 0) + (parseFloat(svgStyle.borderRightWidth) || 0);
    const width = cell.clientWidth - padL - padR - svgBorderX - margins.left - margins.right;
    const svgRect = svg.getBoundingClientRect();
    const imageTopViewport = svgRect.top + margins.top;
    const transport = isPlayerActive(instance) ? cell.querySelector(".gram-frame-transport") : null;
    const transportHeight = transport instanceof HTMLElement ? transport.offsetHeight + (parseFloat(window.getComputedStyle(transport).marginTop) || 0) : 0;
    const height = window.innerHeight - imageTopViewport - margins.bottom - BOTTOM_GAP - transportHeight;
    return {
      width: Math.max(baseWidth, Math.round(width)),
      height: Math.max(baseHeight, Math.round(height))
    };
  }
  function applyExpandLayout(instance) {
    const imageDetails = instance.state.imageDetails;
    if (instance.state.imageExpanded) {
      const { width, height } = computeAvailableRenderSize(instance);
      imageDetails.renderWidth = width;
      imageDetails.renderHeight = height;
      updateSVGLayout(instance);
      const settled = computeAvailableRenderSize(instance);
      if (Math.abs(settled.width - width) > 1 || Math.abs(settled.height - height) > 1) {
        imageDetails.renderWidth = settled.width;
        imageDetails.renderHeight = settled.height;
      }
    } else {
      const base = baseRenderSize(instance);
      imageDetails.renderWidth = base.width;
      imageDetails.renderHeight = base.height;
    }
    updateSVGLayout(instance);
    renderAxes(instance);
    if (instance.featureRenderer) {
      instance.featureRenderer.renderAllPersistentFeatures();
    }
    dispatch(instance);
  }
  function updateToggleButton(button2, expanded) {
    button2.setAttribute("aria-pressed", expanded ? "true" : "false");
    button2.setAttribute("aria-label", expanded ? "Collapse image" : "Expand image");
    button2.title = expanded ? "Collapse image" : "Expand image";
    button2.textContent = expanded ? "⤢" : "⤡";
  }
  function setImageExpanded(instance, expanded) {
    if (!isLandscape(instance)) {
      return;
    }
    instance.state.imageExpanded = !!expanded;
    const expandedNow = instance.state.imageExpanded;
    applyExpandLayout(instance);
    if (instance.ui.expandToggleButton) {
      updateToggleButton(instance.ui.expandToggleButton, expandedNow);
    }
  }
  function refreshExpandedLayout(instance) {
    if (!instance.state.imageExpanded) {
      return;
    }
    const { width, height } = computeAvailableRenderSize(instance);
    const imageDetails = instance.state.imageDetails;
    imageDetails.renderWidth = width;
    imageDetails.renderHeight = height;
  }
  function createExpandToggle(instance) {
    if (!isLandscape(instance)) {
      return null;
    }
    const button2 = document.createElement("button");
    button2.className = "gram-frame-expand-toggle";
    button2.type = "button";
    updateToggleButton(button2, instance.state.imageExpanded === true);
    button2.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      setImageExpanded(instance, !instance.state.imageExpanded);
    });
    instance.ui.mainCell.appendChild(button2);
    instance.ui.expandToggleButton = button2;
    return button2;
  }
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 10;
  function zoomLevel(instance) {
    return instance.state.zoom.level;
  }
  function isZoomedIn(instance) {
    return zoomLevel(instance) > MIN_ZOOM;
  }
  function zoomIn(instance) {
    zoomAboutViewCentre(instance, Math.min(zoomLevel(instance) * 1.5, MAX_ZOOM));
  }
  function zoomOut(instance) {
    zoomAboutViewCentre(instance, Math.max(zoomLevel(instance) / 1.5, MIN_ZOOM));
  }
  function zoomAboutViewCentre(instance, newLevel) {
    const { zoom, player } = instance.state;
    const centreX = viewCentre(zoom.centerX, zoom.level);
    const centreY = viewCentre(zoom.centerY, zoom.level);
    if (isPlayerActive(instance)) {
      const centreTime = player.viewTop - visibleWindowSeconds(instance) / 2;
      zoom.level = newLevel;
      player.viewTop = clampViewTop(instance, centreTime + visibleWindowSeconds(instance) / 2);
    }
    if (newLevel <= MIN_ZOOM) {
      fitView(instance);
      return;
    }
    const anchorY = isPlayerActive(instance) ? 0.5 : anchorForCentre(centreY, newLevel);
    setZoom(instance, newLevel, anchorForCentre(centreX, newLevel), anchorY);
  }
  function setZoom(instance, level, centerX, centerY) {
    const zoom = instance.state.zoom;
    zoom.level = level;
    zoom.centerX = centerX;
    zoom.centerY = centerY;
    if (instance.ui.svg) {
      applyZoomTransform(instance);
    }
    updateZoomControlStates(instance);
    dispatch(instance, { frame: true });
  }
  function pixelDeltaToNormalizedPan(instance, dxPx, dyPx) {
    const imageDetails = instance.state.imageDetails;
    const { naturalWidth, naturalHeight } = imageDetails;
    const renderWidth = imageDetails.renderWidth || naturalWidth;
    const renderHeight = imageDetails.renderHeight || naturalHeight;
    const origin = screenToSVG(0, 0, instance.ui.svg);
    const shifted = screenToSVG(dxPx, dyPx, instance.ui.svg);
    const svgDeltaX = shifted.x - origin.x;
    const svgDeltaY = shifted.y - origin.y;
    const level = zoomLevel(instance);
    return {
      normalizedDeltaX: -(svgDeltaX / renderWidth) / level,
      normalizedDeltaY: -(svgDeltaY / renderHeight) / level
    };
  }
  function panByNormalized(instance, deltaX, deltaY) {
    const { zoom, player } = instance.state;
    if (isPlayerActive(instance)) {
      player.viewTop = clampViewTop(instance, player.viewTop - deltaY * player.windowSeconds);
      const newCenterX2 = zoom.level > 1 ? Math.max(0, Math.min(1, zoom.centerX + deltaX)) : zoom.centerX;
      setZoom(instance, zoom.level, newCenterX2, zoom.centerY);
      return;
    }
    if (zoom.level <= 1) {
      return;
    }
    const newCenterX = Math.max(0, Math.min(1, zoom.centerX + deltaX));
    const newCenterY = Math.max(0, Math.min(1, zoom.centerY + deltaY));
    setZoom(instance, zoom.level, newCenterX, newCenterY);
  }
  function zoomAtImagePoint(instance, factor, imageX, imageY) {
    const state = instance.state;
    const { zoom, player } = state;
    const currentLevel = zoom.level;
    const newLevel = Math.max(MIN_ZOOM, Math.min(currentLevel * factor, MAX_ZOOM));
    if (newLevel === currentLevel) {
      return;
    }
    const { renderWidth, renderHeight } = getRenderDimensions(state);
    if (isPlayerActive(instance)) {
      const pointerTime = imageToData(imageX, imageY, state).time;
      const fraction = (player.viewTop - pointerTime) / visibleWindowSeconds(instance);
      zoom.level = newLevel;
      player.viewTop = clampViewTop(instance, pointerTime + fraction * visibleWindowSeconds(instance));
      setZoom(instance, newLevel, anchorHoldingPoint(imageX / renderWidth, zoom.centerX, currentLevel, newLevel), 0.5);
      return;
    }
    if (newLevel <= MIN_ZOOM) {
      fitView(instance);
      return;
    }
    setZoom(
      instance,
      newLevel,
      anchorHoldingPoint(imageX / renderWidth, zoom.centerX, currentLevel, newLevel),
      anchorHoldingPoint(imageY / renderHeight, zoom.centerY, currentLevel, newLevel)
    );
  }
  function zoomToRegion(instance, region) {
    const state = instance.state;
    const { zoom, player } = state;
    const { renderWidth, renderHeight } = getRenderDimensions(state);
    if (!(region.width > 0) || !(region.height > 0)) {
      return;
    }
    const centreX = (region.x + region.width / 2) / renderWidth;
    const across = renderWidth / region.width;
    if (isPlayerActive(instance)) {
      const topTime = imageToData(0, region.y, state).time;
      const bottomTime = imageToData(0, region.y + region.height, state).time;
      const seconds = topTime - bottomTime;
      const through = seconds > 0 ? player.windowSeconds / seconds : across;
      const level2 = Math.max(MIN_ZOOM, Math.min(across, through, MAX_ZOOM));
      zoom.level = level2;
      player.viewTop = clampViewTop(instance, (topTime + bottomTime) / 2 + visibleWindowSeconds(instance) / 2);
      setZoom(instance, level2, anchorForCentre(centreX, level2), 0.5);
      return;
    }
    const level = Math.max(MIN_ZOOM, Math.min(across, renderHeight / region.height, MAX_ZOOM));
    const centreY = (region.y + region.height / 2) / renderHeight;
    setZoom(instance, level, anchorForCentre(centreX, level), anchorForCentre(centreY, level));
  }
  function fitView(instance) {
    const { zoom, player } = instance.state;
    if (isPlayerActive(instance)) {
      zoom.level = MIN_ZOOM;
      player.viewTop = clampViewTop(instance, player.viewTop);
    }
    setZoom(instance, MIN_ZOOM, 0.5, 0.5);
  }
  function updateZoomControlStates(instance) {
    if (instance.ui.commandButtons && instance.modes) {
      updateCommandButtonStates(instance.ui.commandButtons, instance.modes);
    }
    if (instance.ui.modeButtons && instance.modes) {
      updateModeButtonStates(instance.ui.modeButtons, instance.modes);
      const { mode, previousMode } = instance.state;
      if (mode === "pan" && instance.modes.pan && !instance.modes.pan.isEnabled() && previousMode) {
        instance._switchMode(previousMode);
      }
    }
  }
  function handleResize(instance) {
    if (instance.ui.svg) {
      refreshExpandedLayout(instance);
      updateSVGLayout(instance);
      renderAxes(instance);
      if (instance.featureRenderer) {
        instance.featureRenderer.renderAllPersistentFeatures();
      }
    }
  }
  function selectionBounds(viewport, spectrogramImage = null) {
    const { renderWidth, renderHeight } = getRenderDimensions(viewport);
    const { margins } = viewport;
    const image = getImageBounds(viewport, spectrogramImage);
    return {
      left: Math.max(margins.left, image.left),
      top: Math.max(margins.top, image.top),
      right: Math.min(margins.left + renderWidth, image.left + image.width),
      bottom: Math.min(margins.top + renderHeight, image.top + image.height)
    };
  }
  function withinBounds(point, bounds) {
    return point.x >= bounds.left && point.x <= bounds.right && point.y >= bounds.top && point.y <= bounds.bottom;
  }
  function selectionRect(bounds, start, current) {
    const x = Math.max(bounds.left, Math.min(bounds.right, current.x));
    const y = Math.max(bounds.top, Math.min(bounds.bottom, current.y));
    const movedX = x - start.x;
    const movedY = y - start.y;
    return {
      x: Math.min(start.x, x),
      y: Math.min(start.y, y),
      width: Math.abs(movedX),
      height: Math.abs(movedY),
      movedX,
      movedY
    };
  }
  function containFactor(viewport, rect2) {
    const { renderWidth, renderHeight } = getRenderDimensions(viewport);
    if (!(rect2.width > 0) || !(rect2.height > 0)) {
      return 1;
    }
    return Math.min(renderWidth / rect2.width, renderHeight / rect2.height);
  }
  function containedView(viewport, bounds, rect2, limits) {
    const { renderWidth, renderHeight } = getRenderDimensions(viewport);
    const level = viewport.zoom.level;
    const capped = Math.max(limits.min, Math.min(level * containFactor(viewport, rect2), limits.max));
    const factor = capped / level;
    const width = renderWidth / factor;
    const height = renderHeight / factor;
    const centreX = rect2.x + rect2.width / 2;
    const centreY = rect2.y + rect2.height / 2;
    return {
      x: slideInside(centreX - width / 2, width, bounds.left, bounds.right),
      y: slideInside(centreY - height / 2, height, bounds.top, bounds.bottom),
      width,
      height
    };
  }
  function slideInside(start, length, min, max) {
    if (length >= max - min) {
      return min + (max - min - length) / 2;
    }
    return Math.max(min, Math.min(start, max - length));
  }
  function rectToRegion(viewport, spectrogramImage, rect2) {
    const topLeft = svgToImage(rect2.x, rect2.y, viewport, spectrogramImage);
    const bottomRight = svgToImage(rect2.x + rect2.width, rect2.y + rect2.height, viewport, spectrogramImage);
    const upper = imageToData(topLeft.x, topLeft.y, viewport);
    const lower = imageToData(bottomRight.x, bottomRight.y, viewport);
    return {
      region: {
        x: topLeft.x,
        y: topLeft.y,
        width: bottomRight.x - topLeft.x,
        height: bottomRight.y - topLeft.y
      },
      freqSpan: lower.freq - upper.freq,
      // Time runs upward: the rectangle's top edge is the later time.
      timeSpan: upper.time - lower.time
    };
  }
  const SVG_NS$3 = "http://www.w3.org/2000/svg";
  const READOUT_FONT_SIZE = 12;
  function regionSpanText(freqSpan, timeSpan) {
    const freq = formatFrequencyLabel(freqSpan, precisionIntervalFor(freqSpan));
    const time = formatAxisTime(timeSpan, precisionIntervalFor(timeSpan));
    return `${freq} × ${time}`;
  }
  function createRegionOverlay() {
    const overlay = (
      /** @type {SVGGElement} */
      document.createElementNS(SVG_NS$3, "g")
    );
    overlay.setAttribute("class", "gram-frame-region-selection");
    const dim = document.createElementNS(SVG_NS$3, "path");
    dim.setAttribute("class", "gram-frame-region-dim");
    dim.setAttribute("fill-rule", "evenodd");
    overlay.appendChild(dim);
    const resulting = document.createElementNS(SVG_NS$3, "rect");
    resulting.setAttribute("class", "gram-frame-region-view");
    overlay.appendChild(resulting);
    const box = document.createElementNS(SVG_NS$3, "rect");
    box.setAttribute("class", "gram-frame-region-box");
    overlay.appendChild(box);
    return overlay;
  }
  function renderRegionOverlay(overlay, view) {
    const { rect: rect2, bounds } = view;
    const outer = `M${bounds.left} ${bounds.top}H${bounds.right}V${bounds.bottom}H${bounds.left}Z`;
    overlay.children[0].setAttribute("d", `${outer}${boxPath(rect2)}`);
    sizeRect(
      /** @type {SVGRectElement} */
      overlay.children[1],
      view.view
    );
    sizeRect(
      /** @type {SVGRectElement} */
      overlay.children[2],
      rect2
    );
    overlay.children[1].setAttribute("visibility", sameRect(rect2, view.view) ? "hidden" : "visible");
    while (overlay.children.length > 3 && overlay.lastChild) {
      overlay.removeChild(overlay.lastChild);
    }
    overlay.appendChild(plateLabel(readoutText(view)));
  }
  function boxPath(rect2) {
    return `M${rect2.x} ${rect2.y}H${rect2.x + rect2.width}V${rect2.y + rect2.height}H${rect2.x}Z`;
  }
  function sizeRect(element, rect2) {
    element.setAttribute("x", String(rect2.x));
    element.setAttribute("y", String(rect2.y));
    element.setAttribute("width", String(rect2.width));
    element.setAttribute("height", String(rect2.height));
  }
  function sameRect(a, b) {
    return Math.abs(a.x - b.x) < 1 && Math.abs(a.y - b.y) < 1 && Math.abs(a.width - b.width) < 1 && Math.abs(a.height - b.height) < 1;
  }
  function readoutText({ rect: rect2, bounds, freqSpan, timeSpan }) {
    const text = (
      /** @type {SVGTextElement} */
      document.createElementNS(SVG_NS$3, "text")
    );
    const above = rect2.y - 6;
    text.setAttribute("class", "gram-frame-region-readout");
    text.setAttribute("x", String(rect2.x + rect2.width / 2));
    text.setAttribute("y", String(above - READOUT_FONT_SIZE < bounds.top ? rect2.y + rect2.height + READOUT_FONT_SIZE + 4 : above));
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", String(READOUT_FONT_SIZE));
    text.setAttribute("font-family", "Arial, sans-serif");
    text.setAttribute("font-weight", "bold");
    text.textContent = regionSpanText(freqSpan, timeSpan);
    return text;
  }
  const CLICK_THRESHOLD_PX = 5;
  const REGION_READY_CLASS = "gram-frame-region-ready";
  const ZOOM_LIMITS = { min: MIN_ZOOM, max: MAX_ZOOM };
  const sessions = /* @__PURE__ */ new WeakMap();
  function viewportOf(instance) {
    return instance.state;
  }
  function svgPointOf(instance, event) {
    const svg = instance.ui.svg;
    const rect2 = svg.getBoundingClientRect();
    return screenToSVG(event.clientX - rect2.left, event.clientY - rect2.top, svg);
  }
  function drawSelection(instance, session) {
    if (!session.overlay) {
      return;
    }
    const bounds = boundsFor(instance);
    const rect2 = selectionRect(bounds, session.start, session.current);
    const { freqSpan, timeSpan } = regionOf(instance, rect2);
    const view = containedView(viewportOf(instance), bounds, rect2, ZOOM_LIMITS);
    renderRegionOverlay(session.overlay, { rect: rect2, view, bounds, freqSpan, timeSpan });
  }
  function boundsFor(instance) {
    return selectionBounds(viewportOf(instance), instance.ui.spectrogramImage);
  }
  function regionOf(instance, rect2) {
    return rectToRegion(viewportOf(instance), instance.ui.spectrogramImage, rect2);
  }
  function teardown(instance, session) {
    if (session.overlay && session.overlay.parentNode) {
      session.overlay.parentNode.removeChild(session.overlay);
    }
    session.overlay = null;
    setRegionHint(instance, false);
  }
  function finishSelection(instance, session) {
    const rect2 = selectionRect(boundsFor(instance), session.start, session.current);
    teardown(instance, session);
    if (Math.abs(rect2.movedX) < CLICK_THRESHOLD_PX && Math.abs(rect2.movedY) < CLICK_THRESHOLD_PX) {
      return;
    }
    zoomToRegion(instance, regionOf(instance, rect2).region);
  }
  function sessionFor(instance) {
    const existing = sessions.get(instance);
    if (existing) {
      return existing;
    }
    const origin = { x: 0, y: 0 };
    const created = {
      handler: new BaseDragHandler(instance, {
        resolveTarget: () => ({ kind: "region", id: null, type: null }),
        onDragStart: () => {
          created.overlay = instance.ui.svg.appendChild(createRegionOverlay());
          setRegionHint(instance, true);
          drawSelection(instance, created);
        },
        onDragMove: () => drawSelection(instance, created),
        onDragEnd: () => finishSelection(instance, created),
        onDragCancel: () => teardown(instance, created)
      }, null),
      start: origin,
      current: origin,
      overlay: null
    };
    sessions.set(instance, created);
    return created;
  }
  function setRegionHint(instance, ready) {
    if (instance.ui.svg) {
      instance.ui.svg.classList.toggle(REGION_READY_CLASS, ready);
    }
  }
  function isSelectingRegion(instance) {
    const session = sessions.get(instance);
    return !!(session && session.handler.isDragging());
  }
  function startRegionSelection(instance, event) {
    const point = svgPointOf(instance, event);
    if (!withinBounds(point, boundsFor(instance))) {
      return false;
    }
    const session = sessionFor(instance);
    session.start = point;
    session.current = point;
    if (!session.handler.startDrag(null, event)) {
      return false;
    }
    event.preventDefault();
    return true;
  }
  function handleRegionPointerMove(instance, event) {
    if (isSelectingRegion(instance)) {
      const session = (
        /** @type {RegionSession} */
        sessions.get(instance)
      );
      session.current = svgPointOf(instance, event);
      drawSelection(instance, session);
      return true;
    }
    setRegionHint(instance, event.shiftKey && !hasActiveDrag(instance) && !isPlaying(instance) && withinBounds(svgPointOf(instance, event), boundsFor(instance)));
    return false;
  }
  function finishRegionSelection(instance, event) {
    if (!isSelectingRegion(instance)) {
      return false;
    }
    const session = (
      /** @type {RegionSession} */
      sessions.get(instance)
    );
    session.current = svgPointOf(instance, event);
    session.handler.endDrag(null, event);
    return true;
  }
  const CLICK_SLOP_PX = 4;
  function isClick(origin, event) {
    return Math.abs(event.clientX - origin.x) <= CLICK_SLOP_PX && Math.abs(event.clientY - origin.y) <= CLICK_SLOP_PX;
  }
  const activeSeeks = /* @__PURE__ */ new WeakMap();
  function isDragSeeking(instance) {
    return activeSeeks.has(instance);
  }
  function startDragSeek(instance, event) {
    const controller = instance.player;
    if (event.button !== 0 || !controller || !controller.isReady() || !controller.playerState.playing) {
      return false;
    }
    if (event.shiftKey) {
      return false;
    }
    if (activeSeeks.has(instance)) {
      return true;
    }
    controller.pause();
    const origin = { x: event.clientX, y: event.clientY };
    const last = { x: event.clientX, y: event.clientY };
    const onMove = (moveEvent) => {
      const { normalizedDeltaX, normalizedDeltaY } = pixelDeltaToNormalizedPan(
        instance,
        moveEvent.clientX - last.x,
        moveEvent.clientY - last.y
      );
      panByNormalized(instance, normalizedDeltaX, normalizedDeltaY);
      last.x = moveEvent.clientX;
      last.y = moveEvent.clientY;
    };
    const onUp = (upEvent) => {
      if (upEvent.button !== 0) {
        return;
      }
      endDragSeek(instance, !isClick(origin, upEvent));
    };
    activeSeeks.set(instance, { origin, last, onMove, onUp });
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    instance.ui.container.classList.add("gram-frame-drag-seek");
    event.preventDefault();
    return true;
  }
  function endDragSeek(instance, resume = true) {
    const seek = activeSeeks.get(instance);
    if (!seek) {
      return false;
    }
    activeSeeks.delete(instance);
    window.removeEventListener("mousemove", seek.onMove);
    window.removeEventListener("mouseup", seek.onUp);
    instance.ui.container.classList.remove("gram-frame-drag-seek");
    const controller = instance.player;
    if (!controller || !resume) {
      return true;
    }
    controller.seek(controller.playerState.viewTop);
    controller.play().catch((error) => {
      console.warn("GramFrame: playback could not resume after the drag:", error instanceof Error ? error.message : String(error));
    });
    return true;
  }
  function resumeFromClick(instance, origin, event) {
    const controller = instance.player;
    if (!controller || !controller.isReady() || controller.playerState.playing) {
      return false;
    }
    if (event.button !== 0 || !origin || !isClick(origin, event)) {
      return false;
    }
    controller.play().catch((error) => {
      console.warn("GramFrame: playback could not start from the click:", error instanceof Error ? error.message : String(error));
    });
    return true;
  }
  function wheelPanHandler(instance) {
    if (!instance.interaction._wheelPanHandler) {
      let previousCursor = "";
      instance.interaction._wheelPanHandler = new BaseDragHandler(instance, {
        resolveTarget: () => isZoomedIn(instance) ? { kind: "pan", id: null, type: null } : null,
        onDragStart: (_target, _position, event) => {
          previousCursor = instance.ui.svg ? instance.ui.svg.style.cursor : "";
          if (event) {
            instance.interaction._wheelPanLast = { x: event.clientX, y: event.clientY };
          }
        },
        onDragMove: (_target, _position, _startPosition, event) => {
          if (!event || !instance.interaction._wheelPanLast) return;
          const dx = event.clientX - instance.interaction._wheelPanLast.x;
          const dy = event.clientY - instance.interaction._wheelPanLast.y;
          const { normalizedDeltaX, normalizedDeltaY } = pixelDeltaToNormalizedPan(instance, dx, dy);
          panByNormalized(instance, normalizedDeltaX, normalizedDeltaY);
          instance.interaction._wheelPanLast = { x: event.clientX, y: event.clientY };
        },
        onDragEnd: () => {
          instance.interaction._wheelPanLast = null;
        },
        onDragCancel: () => {
          instance.interaction._wheelPanLast = null;
        },
        updateCursor: (style) => {
          if (instance.ui.svg) {
            instance.ui.svg.style.cursor = style;
          }
        },
        // The middle-button pan is a pan, so it keeps the hand. On release it
        // restores whatever cursor the mode had, rather than forcing a crosshair.
        cursorFor: (_kind, phase) => phase === "drag" ? PAN_DRAG_CURSOR : previousCursor || IDLE_CURSOR
      }, null);
    }
    return instance.interaction._wheelPanHandler;
  }
  const WHEEL_ZOOM_STEP = 1.2;
  function handleWheel(instance, event) {
    const result = screenToDataWithZoom(instance, event);
    if (!result) {
      return;
    }
    if (event.ctrlKey) {
      const factor = event.deltaY < 0 ? WHEEL_ZOOM_STEP : 1 / WHEEL_ZOOM_STEP;
      zoomAtImagePoint(instance, factor, result.imageX, result.imageY);
      event.preventDefault();
    } else if (isZoomedIn(instance)) {
      const { normalizedDeltaX } = pixelDeltaToNormalizedPan(instance, -event.deltaY, 0);
      panByNormalized(instance, normalizedDeltaX, 0);
      event.preventDefault();
    }
  }
  function setupEventListeners(instance) {
    const registered = [];
    const listen = (target, type, handler, options) => {
      target.addEventListener(type, handler, options);
      registered.push({ target, type, handler, options });
    };
    if (instance.ui.svg) {
      listen(instance.ui.svg, "mousemove", (event) => {
        handleMouseMove(
          instance,
          /** @type {MouseEvent} */
          event
        );
      });
      listen(instance.ui.svg, "mousedown", (event) => {
        handleMouseDown(
          instance,
          /** @type {MouseEvent} */
          event
        );
      });
      listen(instance.ui.svg, "mouseup", (event) => {
        handleMouseUp(
          instance,
          /** @type {MouseEvent} */
          event
        );
      });
      listen(instance.ui.svg, "mouseleave", () => {
        handleMouseLeave(instance);
      });
      listen(instance.ui.svg, "contextmenu", (event) => {
        handleContextMenu(
          instance,
          /** @type {MouseEvent} */
          event
        );
      });
      listen(instance.ui.svg, "wheel", (event) => {
        handleWheel(
          instance,
          /** @type {WheelEvent} */
          event
        );
      }, { passive: false });
    }
    instance.viewport._boundHandleResize = () => {
      if (instance._handleResize) {
        instance._handleResize();
      }
    };
    Object.keys(instance.ui.modeButtons || {}).forEach((mode) => {
      const button2 = instance.ui.modeButtons[mode];
      if (button2) {
        listen(button2, "click", () => {
          instance._switchMode(
            /** @type {ModeType} */
            mode
          );
        });
      }
    });
    listen(window, "resize", instance.viewport._boundHandleResize);
    instance.interaction._registeredListeners = registered;
  }
  function setupResizeObserver(instance) {
    if (typeof ResizeObserver !== "undefined") {
      instance.viewport.resizeObserver = new ResizeObserver((_entries) => {
        if (instance._handleResize) {
          instance._handleResize();
        }
      });
      instance.viewport.resizeObserver.observe(instance.ui.container);
    }
  }
  function handleMouseMove(instance, event) {
    const wheelPan = wheelPanHandler(instance);
    if (wheelPan.isDragging()) {
      wheelPan.handleMouseMove(null, event);
      return;
    }
    if (handleRegionPointerMove(instance, event)) {
      return;
    }
    const { state } = instance;
    const result = screenToDataWithZoom(instance, event);
    if (result) {
      const { svgCoords, imageX, imageY, dataCoords } = result;
      const svgRect = instance.ui.svg.getBoundingClientRect();
      state.cursorPosition = {
        x: event.clientX - svgRect.left,
        y: event.clientY - svgRect.top,
        svgX: svgCoords.x,
        svgY: svgCoords.y,
        imageX,
        imageY,
        freq: dataCoords.freq,
        time: dataCoords.time
      };
      updateUniversalCursorReadouts(instance, dataCoords);
      if (instance.currentMode && typeof instance.currentMode.handleMouseMove === "function") {
        instance.currentMode.handleMouseMove(event, dataCoords);
      }
    } else {
      state.cursorPosition = null;
      if (acceptsOffImageDrag(instance) && instance.currentMode && typeof instance.currentMode.handleMouseMove === "function") {
        instance.currentMode.handleMouseMove(event, unboundedDataCoords(instance, event));
      }
    }
    dispatch(instance, { frame: true });
  }
  function handleMouseDown(instance, event) {
    setFocusedInstance(instance);
    if (event.button === 0 && isPlayerActive(instance) && seekFromTimeAxisClick(instance, event)) {
      event.preventDefault();
      return;
    }
    if (isPlaying(instance)) {
      startDragSeek(instance, event);
      return;
    }
    if (event.button === 1) {
      event.preventDefault();
      wheelPanHandler(instance).startDrag(null, event);
      return;
    }
    if (event.button !== 0) {
      return;
    }
    if (hasActiveDrag(instance)) {
      return;
    }
    if (event.shiftKey && startRegionSelection(instance, event)) {
      return;
    }
    const result = screenToDataWithZoom(instance, event);
    const dataCoords = result ? result.dataCoords : acceptsOffImageDrag(instance) ? unboundedDataCoords(instance, event) : null;
    if (dataCoords) {
      if (instance.currentMode && typeof instance.currentMode.handleMouseDown === "function") {
        instance.currentMode.handleMouseDown(event, dataCoords);
      }
    }
  }
  function handleMouseUp(instance, event) {
    const wheelPan = wheelPanHandler(instance);
    if (wheelPan.isDragging()) {
      if (event.button === 1) {
        wheelPan.endDrag(null, event);
      }
      return;
    }
    if (event.button !== 0) {
      return;
    }
    if (isPlaying(instance) || isDragSeeking(instance)) {
      return;
    }
    if (finishRegionSelection(instance, event)) {
      return;
    }
    const result = screenToDataWithZoom(instance, event);
    const upCoords = result ? result.dataCoords : acceptsOffImageDrag(instance) ? unboundedDataCoords(instance, event) : null;
    if (upCoords) {
      if (instance.currentMode && typeof instance.currentMode.handleMouseUp === "function") {
        instance.currentMode.handleMouseUp(event, upCoords);
      }
    } else if (hasActiveDrag(instance)) {
      cancelActiveDrag(instance);
    }
  }
  function handleMouseLeave(instance) {
    cancelActiveDrag(instance);
    instance.state.cursorPosition = null;
    if (instance.currentMode && typeof instance.currentMode.handleMouseLeave === "function") {
      instance.currentMode.handleMouseLeave();
    }
    dispatch(instance, { frame: true });
  }
  function handleContextMenu(instance, event) {
    if (hasActiveDrag(instance)) {
      event.preventDefault();
      return;
    }
    if (isPlaying(instance)) {
      return;
    }
    const result = screenToDataWithZoom(instance, event);
    if (result) {
      const { dataCoords } = result;
      if (instance.currentMode && typeof instance.currentMode.handleContextMenu === "function") {
        instance.currentMode.handleContextMenu(event, dataCoords);
      }
    }
  }
  function cleanupEventListeners(instance) {
    endDragSeek(instance, false);
    const registered = instance.interaction._registeredListeners || [];
    registered.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    instance.interaction._registeredListeners = [];
    if (instance.viewport.resizeObserver) {
      instance.viewport.resizeObserver.disconnect();
      instance.viewport.resizeObserver = null;
    }
  }
  const HALO_CLASS = "gram-frame-selection-halo";
  const SELECTED_LABEL_CLASS = "gram-frame-selected-label";
  const HALO_COLOR = "rgba(255, 255, 255, 0.6)";
  const HALO_GROWTH = 5;
  const ID_ATTRIBUTES = {
    marker: "data-marker-id",
    harmonicSet: "data-harmonic-set-id",
    sidebandSet: "data-sideband-set-id"
  };
  function applySelectionHalo(instance) {
    const group = instance.ui.cursorGroup;
    if (!group) {
      return;
    }
    clearSelectionHalo(group);
    const selection = instance.state.selection;
    const attribute = selection && selection.selectedType ? ID_ATTRIBUTES[selection.selectedType] : void 0;
    if (!attribute || !selection.selectedId) {
      return;
    }
    const targets = /* @__PURE__ */ new Set();
    group.querySelectorAll(`[${attribute}="${selection.selectedId}"]`).forEach((element) => {
      const target = topLevel(group, element);
      if (target) {
        targets.add(target);
      }
    });
    targets.forEach((target) => decorate(group, target));
  }
  function topLevel(group, element) {
    let node = element;
    while (node.parentNode instanceof Element && node.parentNode !== group) {
      node = node.parentNode;
    }
    return node.parentNode === group ? node : null;
  }
  function clearSelectionHalo(group) {
    group.querySelectorAll(`.${HALO_CLASS}`).forEach((halo) => halo.remove());
    group.querySelectorAll(`.${SELECTED_LABEL_CLASS}`).forEach((label) => {
      label.classList.remove(SELECTED_LABEL_CLASS);
    });
  }
  function decorate(group, target) {
    plates(target).forEach((plate) => plate.classList.add(SELECTED_LABEL_CLASS));
    const halo = buildHalo(target);
    if (halo) {
      group.insertBefore(halo, target);
    }
  }
  function plates(target) {
    const found = Array.from(target.querySelectorAll(".gram-frame-label-plated"));
    return target.classList.contains("gram-frame-label-plated") ? [target, ...found] : found;
  }
  function buildHalo(target) {
    if (target.classList.contains("gram-frame-label-plated")) {
      return null;
    }
    const halo = (
      /** @type {Element} */
      target.cloneNode(true)
    );
    plates(halo).forEach((plate) => plate.remove());
    const parts = [halo, ...Array.from(halo.querySelectorAll("*"))];
    if (parts.length === 1 && halo.tagName === "g" && halo.children.length === 0) {
      return null;
    }
    parts.forEach(recolour);
    halo.setAttribute("class", HALO_CLASS);
    return halo;
  }
  function recolour(element) {
    Array.from(element.attributes).filter((attribute) => attribute.name.startsWith("data-")).forEach((attribute) => element.removeAttribute(attribute.name));
    element.removeAttribute("class");
    element.setAttribute("pointer-events", "none");
    const stroke = element.getAttribute("stroke");
    const fill = element.getAttribute("fill");
    const width = Number(element.getAttribute("stroke-width") || 0);
    if (fill && fill !== "none") {
      element.setAttribute("fill", HALO_COLOR);
    }
    if (stroke === null && fill && fill !== "none") {
      element.setAttribute("stroke", HALO_COLOR);
      element.setAttribute("stroke-width", String(HALO_GROWTH));
    } else if (stroke && stroke !== "none") {
      element.setAttribute("stroke", HALO_COLOR);
      element.setAttribute("stroke-width", String(width + HALO_GROWTH));
    }
    element.setAttribute("opacity", "1");
  }
  function setSelection(instance, type, id, index) {
    setFocusedInstance(instance);
    const state = instance.state;
    const selection = state.selection;
    selection.selectedType = type;
    selection.selectedId = id;
    selection.selectedIndex = index;
    state.styleTarget = "selected";
    updateSelectionVisuals(instance);
    if (instance.interaction.syncStyleControls) {
      instance.interaction.syncStyleControls();
    }
    const selected = describeSelection(instance);
    if (selected) {
      revealTime(instance, selected.time);
    }
    dispatch(instance);
  }
  function toggleSelection(instance, type, id, index) {
    if (isFeatureSelected(instance, type, id)) {
      clearSelection(instance);
    } else {
      setSelection(instance, type, id, index);
    }
  }
  function isFeatureSelected(instance, type, id) {
    const selection = instance.state.selection;
    return selection.selectedType === type && selection.selectedId === id;
  }
  function clearSelection(instance) {
    const state = instance.state;
    const selection = state.selection;
    selection.selectedType = null;
    selection.selectedId = null;
    selection.selectedIndex = null;
    state.styleTarget = "new";
    updateSelectionVisuals(instance);
    if (instance.interaction.syncStyleControls) {
      instance.interaction.syncStyleControls();
    }
    dispatch(instance);
  }
  function updateSelectionVisuals(instance) {
    refreshPanels(instance);
    refreshReadoutTarget(instance);
    applySelectionHalo(instance);
  }
  function setupAllEventListeners(instance) {
    setupEventListeners(instance);
    setupResizeObserver(instance);
    initializeKeyboardControl(instance);
    return {
      removeHarmonicSet: (id) => removeHarmonicSet(instance, id),
      removeSidebandSet: (id) => removeSidebandSet(instance, id),
      setSelection: (type, id, index) => setSelection(instance, type, id, index),
      clearSelection: () => clearSelection(instance),
      toggleSelection: (type, id, index) => toggleSelection(instance, type, id, index),
      isFeatureSelected: (type, id) => isFeatureSelected(instance, type, id),
      updateSelectionVisuals: () => updateSelectionVisuals(instance),
      applyColorToSelectedFeature: (color) => applyColorToSelectedFeature(instance, color),
      applySymbolToSelectedFeature: (symbol) => applySymbolToSelectedFeature(instance, symbol),
      applyPinToSelectedFeature: (showPin) => applyPinToSelectedFeature(instance, showPin),
      applyLargeSymbolsToSelectedFeature: (large) => applyLargeSymbolsToSelectedFeature(instance, large)
    };
  }
  class BaseMode {
    /**
     * Constructor for base mode
     * @param {GramFrame} instance - GramFrame instance
     */
    constructor(instance) {
      this.instance = instance;
      this.dragHandler = null;
      this.uiElements = {};
    }
    /**
     * Activate this mode - called when switching to this mode
     * Override in subclasses to perform mode-specific initialization
     */
    activate() {
    }
    /**
     * Deactivate this mode - called when switching away from this mode
     * Override in subclasses to perform mode-specific cleanup
     */
    deactivate() {
    }
    /**
     * Handle mouse move events
     * @param {MouseEvent} _event - Mouse event (unused in base implementation)
     * @param {DataCoordinates} _dataCoords - Data coordinates {freq, time} (unused in base implementation)
     */
    handleMouseMove(_event, _dataCoords) {
    }
    /**
     * Handle mouse down events
     * @param {MouseEvent} _event - Mouse event (unused in base implementation)
     * @param {DataCoordinates} _dataCoords - Data coordinates {freq, time} (unused in base implementation)
     */
    handleMouseDown(_event, _dataCoords) {
    }
    /**
     * Handle mouse up events
     * @param {MouseEvent} _event - Mouse event (unused in base implementation)
     * @param {DataCoordinates} _dataCoords - Data coordinates {freq, time} (unused in base implementation)
     */
    handleMouseUp(_event, _dataCoords) {
    }
    /**
     * Handle mouse leave events
     */
    handleMouseLeave() {
    }
    /**
     * Handle a right-click within the image.
     * @param {MouseEvent} _event - Context-menu event (unused in base implementation)
     * @param {DataCoordinates} _dataCoords - Data coordinates {freq, time} (unused in base implementation)
     */
    handleContextMenu(_event, _dataCoords) {
    }
    /**
     * Render persistent features for this mode
     * Override in subclasses to render mode-specific persistent features
     */
    renderPersistentFeatures() {
    }
    /**
     * Update LED displays with mode-specific values
     * @param {CursorPosition|null} _coords - Current cursor coordinates, or null
     *   when the pointer is not over the image
     */
    updateLEDs(_coords) {
    }
    /**
     * Whether a drag in this mode keeps working when the pointer is not over the
     * gram itself.
     *
     * `false` for every mode that places or moves a feature: a marker has to land
     * on the gram, so an off-image pointer is a mistake and the drag is cancelled.
     * Panning an audio-sourced gram is the exception — see `PanMode`.
     * @returns {boolean} True when the mode wants pointer events off the image
     */
    acceptsOffImageDrag() {
      return false;
    }
    /**
     * Get guidance content for this mode
     * @returns {Object} Structured guidance content
     */
    getGuidanceText() {
      return {
        title: "Base Mode",
        items: [
          "No specific guidance available"
        ]
      };
    }
    /**
     * Get command buttons for this mode
     * Override in subclasses to provide mode-specific command buttons
     * @returns {Array<CommandButton>} Array of command button definitions
     */
    getCommandButtons() {
      return [];
    }
    /**
     * Check if this mode is currently enabled
     * Override in subclasses to provide mode-specific enable/disable logic
     * @returns {boolean} True if mode is enabled, false if disabled
     */
    isEnabled() {
      return true;
    }
    /**
     * Reset mode-specific state
     * Override in subclasses to clear mode-specific state properties
     */
    resetState() {
    }
    /**
     * Clean up mode-specific state when switching away from this mode
     * Override in subclasses to perform mode-specific state cleanup
     */
    cleanup() {
    }
    /**
     * Create mode-specific UI elements when entering this mode
     * Override in subclasses to create mode-specific UI elements
     * @param {HTMLElement} _readoutPanel - Container for UI elements (unused in base implementation)
     */
    createUI(_readoutPanel) {
      this.uiElements = {};
    }
    /**
     * Destroy mode-specific UI elements when leaving this mode
     * Override in subclasses to clean up mode-specific UI elements
     */
    destroyUI() {
      if (this.uiElements) {
        Object.values(this.uiElements).forEach((element) => {
          if (element && element.parentNode) {
            element.parentNode.removeChild(element);
          }
        });
        this.uiElements = {};
      }
    }
    /**
     * Get initial state for this mode
     * Override in subclasses to provide mode-specific initial state
     * @returns {*} Mode-specific initial state object
     */
    static getInitialState() {
      return {};
    }
    /**
     * Get viewport configuration for coordinate transformations
     * @returns {ViewportConfig} Viewport configuration object
     */
    getViewport() {
      return {
        margins: this.instance.state.margins,
        imageDetails: this.instance.state.imageDetails,
        config: this.instance.state.config,
        zoom: this.instance.state.zoom,
        frequencyRate: this.instance.state.frequencyRate
      };
    }
    /**
     * Update cursor style for drag operations.
     *
     * The style goes on the SVG root, not on the `<image>` inside it. `cursor` is
     * resolved on whatever element the pointer actually hits, and a feature is
     * drawn *over* the image as a sibling of it — a marker circle, a harmonic
     * pin, a Doppler curve. Styling the image therefore left the cursor unchanged
     * at exactly the moment it mattered: over the feature itself, where the hit
     * element inherited the SVG's resting `crosshair` instead. On the root, every
     * descendant inherits the value, so the affordance holds wherever the pointer
     * is inside the component.
     * @param {string} style - A CSS cursor value, as resolved by `utils/cursors.js`
     */
    updateCursorStyle(style) {
      if (this.instance.ui.svg) {
        this.instance.ui.svg.style.cursor = style;
      }
    }
  }
  function revealTableRow(wrapper, headerRow, tbody, index, allowUpward = false) {
    const tr = (
      /** @type {HTMLElement|undefined} */
      tbody.children[index]
    );
    if (!tr) return;
    const bottom = tr.offsetTop + tr.offsetHeight - wrapper.clientHeight;
    if (bottom > wrapper.scrollTop) {
      wrapper.scrollTop = bottom;
      return;
    }
    if (!allowUpward) return;
    const headerCell = (
      /** @type {HTMLElement|null} */
      headerRow.firstElementChild
    );
    const top = tr.offsetTop - (headerCell ? headerCell.offsetHeight : 0);
    if (top < wrapper.scrollTop) {
      wrapper.scrollTop = Math.max(0, top);
    }
  }
  function createDiffingTable(container, spec) {
    const area = document.createElement("div");
    area.className = "gram-frame-table-area";
    const wrapper = document.createElement("div");
    wrapper.className = "gram-frame-table-container";
    const table = document.createElement("table");
    table.className = "gram-frame-table";
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    spec.columns.forEach((column) => {
      const th = document.createElement("th");
      th.textContent = column.label || "";
      if (column.width) {
        th.style.width = column.width;
      }
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    table.appendChild(tbody);
    wrapper.appendChild(table);
    area.appendChild(wrapper);
    container.appendChild(area);
    let currentRows = [];
    let renderedKeys = /* @__PURE__ */ new Set();
    let renderedSelectedKey = null;
    function setCellContent(cell, content) {
      if (content instanceof Node) {
        cell.replaceChildren(content);
      } else if (cell.textContent !== content) {
        cell.textContent = content;
      }
    }
    function applySelection(tr, key) {
      const selected = spec.isSelected ? spec.isSelected(key) : false;
      tr.classList.toggle("gram-frame-selected-row", selected);
    }
    function buildRow(row, index) {
      const key = spec.rowKey(row, index);
      const tr = document.createElement("tr");
      tr.setAttribute(spec.rowAttribute, key);
      if (spec.rowClassName) {
        tr.className = spec.rowClassName;
      }
      applySelection(tr, key);
      spec.cells(row, index).forEach((content, column) => {
        const td = document.createElement("td");
        const className = spec.columns[column] && spec.columns[column].cellClassName;
        if (className) {
          td.className = className;
        }
        setCellContent(td, content);
        tr.appendChild(td);
      });
      return tr;
    }
    function updateRow(tr, row, index) {
      applySelection(tr, spec.rowKey(row, index));
      spec.cells(row, index).forEach((content, column) => {
        const cell = tr.cells[column];
        if (cell) {
          setCellContent(cell, content);
        }
      });
    }
    function rebuildFrom(rows, startIndex) {
      const existing = tbody.querySelectorAll("tr");
      for (let i = startIndex; i < existing.length; i++) {
        existing[i].remove();
      }
      for (let i = startIndex; i < rows.length; i++) {
        tbody.appendChild(buildRow(rows[i], i));
      }
    }
    let emptyRow = null;
    function setEmptyState(empty) {
      if (!spec.emptyMessage) {
        return;
      }
      if (!emptyRow) {
        emptyRow = document.createElement("tr");
        emptyRow.className = "gram-frame-table-empty";
        const cell = document.createElement("td");
        cell.colSpan = spec.columns.length;
        cell.textContent = spec.emptyMessage;
        emptyRow.appendChild(cell);
      }
      if (empty) {
        tbody.appendChild(emptyRow);
      } else if (emptyRow.parentNode) {
        emptyRow.remove();
      }
    }
    function applyDiff() {
      setEmptyState(false);
      const existing = tbody.querySelectorAll("tr");
      for (let index = 0; index < currentRows.length; index++) {
        const tr = (
          /** @type {HTMLTableRowElement} */
          existing[index]
        );
        const key = spec.rowKey(currentRows[index], index);
        if (tr && tr.getAttribute(spec.rowAttribute) === key) {
          updateRow(tr, currentRows[index], index);
        } else {
          rebuildFrom(currentRows, index);
          return;
        }
      }
      for (let i = currentRows.length; i < existing.length; i++) {
        existing[i].remove();
      }
    }
    const rowActions = [];
    if (spec.deleteSelector && spec.onDelete) {
      rowActions.push({ selector: spec.deleteSelector, handler: spec.onDelete });
    }
    if (spec.actions) {
      rowActions.push(...spec.actions);
    }
    function handleClick(event) {
      const target = (
        /** @type {Element|null} */
        event.target
      );
      if (!target) return;
      const tr = (
        /** @type {HTMLTableRowElement|null} */
        target.closest("tr")
      );
      if (!tr || !tbody.contains(tr)) return;
      const key = tr.getAttribute(spec.rowAttribute);
      if (key === null) return;
      const index = Array.prototype.indexOf.call(tbody.children, tr);
      const row = currentRows[index];
      const action = rowActions.find((candidate) => target.closest(candidate.selector));
      if (action) {
        event.preventDefault();
        event.stopPropagation();
        action.handler(key, row, index);
        return;
      }
      if (spec.onSelect) {
        spec.onSelect(key, row, index);
      }
    }
    tbody.addEventListener("click", handleClick);
    return {
      element: table,
      /**
       * Diff `rows` against what is rendered, apply the difference, and keep any
       * newly added or newly selected row in view.
       *
       * Idempotent: calling it twice with equal input performs no DOM writes and
       * no scrolling.
       * @param {any[]} rows - The rows to render
       */
      update(rows) {
        currentRows = rows || [];
        const keys = currentRows.map((row, index) => spec.rowKey(row, index));
        applyDiff();
        setEmptyState(currentRows.length === 0);
        let lastAdded = -1;
        for (let index = 0; index < keys.length; index++) {
          if (!renderedKeys.has(keys[index])) {
            lastAdded = index;
          }
        }
        if (renderedKeys.size > 0 && lastAdded !== -1) {
          revealTableRow(wrapper, headerRow, tbody, lastAdded);
        }
        const isSelected = spec.isSelected;
        const selectedIndex = isSelected ? keys.findIndex((key) => isSelected(key)) : -1;
        const selectedKey = selectedIndex === -1 ? null : keys[selectedIndex];
        if (renderedKeys.size > 0 && selectedKey !== null && selectedKey !== renderedSelectedKey) {
          revealTableRow(wrapper, headerRow, tbody, selectedIndex, true);
        }
        renderedKeys = new Set(keys);
        renderedSelectedKey = selectedKey;
      },
      /**
       * Remove the table and its listener.
       */
      destroy() {
        tbody.removeEventListener("click", handleClick);
        if (area.parentNode) {
          area.parentNode.removeChild(area);
        }
      }
    };
  }
  const DEFAULT_TOLERANCE = {
    // Hit radius in rendered image pixels, applied to both axes
    pixelRadius: 8,
    // Only reached when the viewport cannot be read at all
    fallbackDataTolerance: {
      time: 0.01,
      freq: 1
    }
  };
  function calculateDataTolerance(viewport, spectrogramImage, customTolerance = {}) {
    const config = { ...DEFAULT_TOLERANCE, ...customTolerance };
    if (!viewport || !spectrogramImage) {
      return config.fallbackDataTolerance;
    }
    const { config: dataConfig, imageDetails, zoom } = viewport;
    const { naturalWidth, naturalHeight } = imageDetails;
    const renderWidth = imageDetails.renderWidth || naturalWidth;
    const renderHeight = imageDetails.renderHeight || naturalHeight;
    if (!dataConfig || !renderWidth || !renderHeight) {
      return config.fallbackDataTolerance;
    }
    const timeRange = dataConfig.timeMax - dataConfig.timeMin;
    const { freqMin, freqMax } = dataFrequencyRange(viewport);
    const freqRange = freqMax - freqMin;
    const effectiveZoom = (zoom == null ? void 0 : zoom.level) || 1;
    return {
      time: config.pixelRadius / renderHeight * timeRange / effectiveZoom,
      freq: config.pixelRadius / renderWidth * freqRange / effectiveZoom
    };
  }
  function isWithinDataTolerance(position, targetPosition, tolerance) {
    const timeDiff = Math.abs(position.time - targetPosition.time);
    const freqDiff = Math.abs(position.freq - targetPosition.freq);
    return timeDiff <= tolerance.time && freqDiff <= tolerance.freq;
  }
  function calculateNormalizedDistance(pos1, pos2, tolerance) {
    const timeDiff = Math.abs(pos1.time - pos2.time) / tolerance.time;
    const freqDiff = Math.abs(pos1.freq - pos2.freq) / tolerance.freq;
    return Math.sqrt(timeDiff * timeDiff + freqDiff * freqDiff);
  }
  function isWithinToleranceRadius(position, targetPosition, tolerance) {
    return calculateNormalizedDistance(position, targetPosition, tolerance) <= 1;
  }
  function findClosestTarget(position, targets, tolerance) {
    let closestTarget = null;
    let closestDistance = Infinity;
    for (const target of targets) {
      const distance = calculateNormalizedDistance(position, target.position, tolerance);
      if (distance <= 1 && distance < closestDistance) {
        closestDistance = distance;
        closestTarget = target;
      }
    }
    return closestTarget;
  }
  function getUniformTolerance(viewport, spectrogramImage) {
    return calculateDataTolerance(viewport, spectrogramImage, DEFAULT_TOLERANCE);
  }
  const SVG_NS$2 = "http://www.w3.org/2000/svg";
  const CROSSHAIR_SIZE = 15;
  const MARKER_SYMBOL_SIZE = 14;
  function drawsCrosshair(marker) {
    return isSymbolLess(marker.symbol);
  }
  function markerSymbolSize(marker) {
    return MARKER_SYMBOL_SIZE * resolveSymbolScale(marker);
  }
  function createCrosshair(marker, cx, cy) {
    const arm = (x1, y1, x2, y2) => {
      const line2 = document.createElementNS(SVG_NS$2, "line");
      line2.setAttribute("x1", String(x1));
      line2.setAttribute("y1", String(y1));
      line2.setAttribute("x2", String(x2));
      line2.setAttribute("y2", String(y2));
      line2.setAttribute("stroke", marker.color);
      line2.setAttribute("stroke-width", "2");
      line2.setAttribute("stroke-linecap", "round");
      return line2;
    };
    const circle = document.createElementNS(SVG_NS$2, "circle");
    circle.setAttribute("cx", String(cx));
    circle.setAttribute("cy", String(cy));
    circle.setAttribute("r", "3");
    circle.setAttribute("fill", marker.color);
    circle.setAttribute("stroke", "#fff");
    circle.setAttribute("stroke-width", "1");
    return [
      arm(cx - CROSSHAIR_SIZE, cy, cx + CROSSHAIR_SIZE, cy),
      arm(cx, cy - CROSSHAIR_SIZE, cx, cy + CROSSHAIR_SIZE),
      circle
    ];
  }
  function createMarkerMarks(marker, cx, cy) {
    const symbolMark = createSymbolMark(marker.symbol, cx, cy, markerSymbolSize(marker), marker.color);
    if (!symbolMark) {
      return createCrosshair(marker, cx, cy);
    }
    symbolMark.setAttribute("class", "gram-frame-marker-symbol");
    symbolMark.setAttribute("data-marker-id", marker.id);
    return [symbolMark];
  }
  const SVG_NS$1 = "http://www.w3.org/2000/svg";
  function createMarkerLabel(marker, cx, cy, symbolSize) {
    if (!marker.label) {
      return null;
    }
    const { x, y, textAnchor } = markerLabelPlacement(marker.symbol, cx, cy, symbolSize);
    const text = (
      /** @type {SVGTextElement} */
      document.createElementNS(SVG_NS$1, "text")
    );
    text.setAttribute("class", "gram-frame-marker-label");
    text.setAttribute("data-marker-id", marker.id);
    text.setAttribute("x", String(x));
    text.setAttribute("y", String(y));
    text.setAttribute("text-anchor", textAnchor);
    text.setAttribute("font-size", String(MARKER_LABEL_FONT_SIZE));
    text.setAttribute("font-weight", "bold");
    text.setAttribute("font-family", "Arial, sans-serif");
    text.textContent = marker.label;
    return plateLabel(text);
  }
  function createMarkerDeleteButton() {
    const button2 = document.createElement("button");
    button2.type = "button";
    button2.textContent = "×";
    button2.className = "gram-frame-marker-delete-btn";
    button2.title = "Delete marker";
    return button2;
  }
  function createMarkerLabelCell(marker) {
    const text = document.createElement("span");
    text.className = "gram-frame-marker-label-text";
    text.textContent = formatMarkerLabelForTable(marker.label);
    return text;
  }
  class AnalysisMode extends BaseMode {
    /**
     * Initialize AnalysisMode with drag handler
     * @param {GramFrame} instance - GramFrame instance
     */
    constructor(instance) {
      super(instance);
      this.dragHandler = new BaseDragHandler(instance, {
        // A feature drag always carries a data position. Only the pan drag passes
        // null, and it runs on its own handler in `core/events.js`.
        resolveTarget: (position) => this.findMarkerAtPosition(
          /** @type {DataCoordinates} */
          position
        ),
        onDragStart: (target, position) => this.onMarkerDragStart(
          target,
          /** @type {DataCoordinates} */
          position
        ),
        onDragMove: (target, currentPos, startPos) => this.onMarkerDragUpdate(
          target,
          /** @type {DataCoordinates} */
          currentPos,
          /** @type {DataCoordinates} */
          startPos
        ),
        onDragEnd: (target, position) => this.onMarkerDragEnd(target, position),
        updateCursor: (style) => this.updateCursorStyle(style)
      }, "analysis");
    }
    /**
     * This mode's markers, as the live array state holds.
     *
     * The single reach-in for marker data (spec 167, Story 5): every read below
     * goes through here rather than walking `instance.state.analysis.markers`
     * again. Yields an empty array before the slice exists, which reads the same
     * as "no markers" for every caller.
     * @returns {AnalysisMarker[]} The markers
     */
    get markers() {
      const analysis = this.instance.state.analysis;
      return analysis && analysis.markers || [];
    }
    /**
     * Find one of this mode's markers by id.
     * @param {string|null|undefined} markerId - Marker id to look for
     * @returns {AnalysisMarker|undefined} The marker, or `undefined` if it has gone
     */
    findMarker(markerId) {
      return this.markers.find((m) => m.id === markerId);
    }
    /**
     * Start dragging a marker
     * @param {DragTarget} target - Drag target with id and type
     * @param {DataCoordinates} position - Start position
     */
    onMarkerDragStart(target, position) {
      const markers = this.markers;
      const marker = markers.find((m) => m.id === target.id);
      if (marker) {
        const index = markers.findIndex((m) => m.id === target.id);
        this.instance.interaction.setSelection(
          "marker",
          /** @type {string} */
          target.id,
          index
        );
      }
    }
    /**
     * Update marker position during drag
     * @param {DragTarget} target - Drag target with id and type
     * @param {DataCoordinates} currentPos - Current position
     * @param {DataCoordinates} _startPos - Start position (unused)
     */
    onMarkerDragUpdate(target, currentPos, _startPos) {
      const marker = this.findMarker(target.id);
      if (marker) {
        marker.freq = currentPos.freq;
        marker.time = currentPos.time;
        markAnnotationsChanged(this.instance);
        if (this.instance.featureRenderer) {
          this.instance.featureRenderer.renderAllPersistentFeatures();
        }
        if (!this.updateTableScheduled) {
          this.updateTableScheduled = true;
          requestAnimationFrame(() => {
            this.updateMarkersTable();
            this.updateTableScheduled = false;
          });
        }
        dispatch(this.instance, { frame: true });
      }
    }
    /**
     * End dragging a marker
     * @param {Object} _target - Drag target with id and type (unused)
     * @param {DataCoordinates|null} _position - End position (unused)
     */
    onMarkerDragEnd(_target, _position) {
    }
    /**
     * Get guidance content for analysis mode
     * @returns {Object} Structured guidance content
     */
    getGuidanceText() {
      return {
        items: [
          { trigger: "Click", outcome: "to add a persistent cross" },
          { trigger: "Drag", outcome: "an existing cross to reposition it" },
          { trigger: "Right-click", outcome: "a cross to delete it" },
          { trigger: "Row + ← →", outcome: "to nudge (Shift for larger steps)" }
        ]
      };
    }
    /**
     * Handle mouse move events in analysis mode
     * @param {MouseEvent} _event - Mouse event (unused in current implementation)
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseMove(_event, dataCoords) {
      if (this.dragHandler.isDragging()) {
        this.dragHandler.handleMouseMove(dataCoords);
      } else {
        this.dragHandler.updateCursorForHover(dataCoords);
      }
    }
    /**
     * Handle mouse down events in analysis mode
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseDown(event, dataCoords) {
      if (event.button !== 0) {
        return;
      }
      const dragStarted = this.dragHandler.startDrag(dataCoords);
      if (!dragStarted) {
        this.createMarkerAtPosition(dataCoords);
      }
    }
    /**
     * Handle mouse up events in analysis mode
     * @param {MouseEvent} _event - Mouse event (unused in current implementation)
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseUp(_event, dataCoords) {
      this.dragHandler.endDrag(dataCoords);
    }
    /**
     * Handle mouse leave events in analysis mode
     */
    handleMouseLeave() {
    }
    /**
     * Handle context menu (right-click) events in analysis mode
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleContextMenu(event, dataCoords) {
      event.preventDefault();
      const target = this.findMarkerAtPosition(dataCoords);
      if (target) {
        this.removeMarker(
          /** @type {string} */
          target.id
        );
      }
    }
    // Cursor position updates are now handled universally in main.js
    // No need for mode-specific cursor position management
    /**
     * Create a marker at the specified position
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    createMarkerAtPosition(dataCoords) {
      const { selectedColor, selectedSymbol, largeSymbols } = this.instance.state;
      const color = selectedColor || "#ff6b6b";
      const symbol = selectedSymbol || "cross";
      const marker = {
        id: `marker-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,
        color,
        time: dataCoords.time,
        freq: dataCoords.freq,
        symbol,
        // EXPERIMENT (temporary): symbol size is carried per marker, seeded from
        // the toggle's next-feature default, so both sizes can coexist.
        largeSymbols: !!largeSymbols
      };
      this.addMarker(marker);
    }
    /**
     * Whether this mode currently owns any persistent feature.
     *
     * Half of the `PersistentFeatureProvider` capability. Lived on
     * `FeatureRenderer` as `hasAnalysisFeatures()` until spec 167 moved it onto
     * the mode that owns the state it reads.
     * @returns {boolean} True if at least one marker exists
     */
    hasPersistentFeatures() {
      return this.markers.length > 0;
    }
    /**
     * Render persistent features for analysis mode
     */
    renderPersistentFeatures() {
      if (!this.instance.ui.cursorGroup) {
        return;
      }
      const existingMarkers = this.instance.ui.cursorGroup.querySelectorAll(".gram-frame-analysis-marker");
      existingMarkers.forEach((marker) => marker.remove());
      this.markers.forEach((marker) => this.renderMarker(marker));
    }
    /**
     * Render a single marker as a crosshair
     * @param {AnalysisMarker} marker - Marker object
     */
    renderMarker(marker) {
      if (!this.instance.ui.cursorGroup) {
        return;
      }
      const markerPoint = { freq: marker.freq, time: marker.time };
      const markerSVG = dataToSVG(markerPoint, this.getViewport(), this.instance.ui.spectrogramImage);
      const currentX = markerSVG.x;
      const currentY = markerSVG.y;
      const markerGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      markerGroup.setAttribute("class", "gram-frame-analysis-marker");
      markerGroup.setAttribute("data-marker-id", marker.id);
      const symbolSize = markerSymbolSize(marker);
      for (const mark of createMarkerMarks(marker, currentX, currentY)) {
        markerGroup.appendChild(mark);
      }
      const label = createMarkerLabel(marker, currentX, currentY, symbolSize);
      if (label) {
        markerGroup.appendChild(label);
      }
      this.instance.ui.cursorGroup.appendChild(markerGroup);
    }
    /**
     * Create UI elements for analysis mode
     * @param {HTMLElement} markersContainer - Persistent container for markers table
     */
    createUI(markersContainer) {
      this.uiElements = {};
      this.uiElements.markersContainer = markersContainer;
      this.createMarkersTable(markersContainer);
      this.uiElements.markersTable = markersContainer.querySelector(".gram-frame-table");
      this.instance.ui.colorPicker = this.instance.ui.colorPicker || null;
      this.instance.ui.timeLED = this.instance.ui.timeLED || null;
      this.instance.ui.freqLED = this.instance.ui.freqLED || null;
    }
    /**
     * Create markers table for displaying active markers
     *
     * The table wrapper sits inside a `gram-frame-table-area` element that claims
     * the column's remaining height; the wrapper fills it absolutely and scrolls,
     * so adding markers never grows the surrounding layout (the header row stays
     * pinned via sticky `th`).
     *
     * @param {HTMLElement} markersContainer - Persistent container for markers (already has label)
     */
    createMarkersTable(markersContainer) {
      if (markersContainer.querySelector(".gram-frame-table")) {
        return;
      }
      this.markersTable = createDiffingTable(markersContainer, {
        // The only five-column table in the panel, and it sits in the narrowest
        // of the three columns, so the tracks are deliberately tight. Time and
        // Freq both show five characters ("00:42", "24.71") and are right-aligned
        // and tabular; the units moved out of the headings, which had to carry
        // "Time (mm:ss)" across 23% of a third of the tables' width.
        columns: [
          { label: "", width: "10%", cellClassName: "gram-frame-marker-color" },
          { label: "Label", width: "32%", cellClassName: "gram-frame-marker-label-cell" },
          { label: "Time", width: "24%", cellClassName: "gram-frame-cell-numeric" },
          { label: "Freq", width: "24%", cellClassName: "gram-frame-cell-numeric" },
          { label: "", width: "10%", cellClassName: "gram-frame-cell-action" }
        ],
        emptyMessage: "Click the gram to add a cross",
        rowAttribute: "data-marker-id",
        rowKey: (marker) => marker.id,
        cells: (marker) => [
          // Colour/symbol cell — a shaped symbol shows the colour-coded symbol;
          // the cross (symbol-less) style shows a filled colour rectangle (FR-010).
          createColorIndicator(marker.symbol, marker.color, 20),
          // Label cell — abbreviated so the column keeps its width; the full text
          // stays on the gram and in the edit dialog (feature 231). Also carries
          // the label button, floated top-right.
          createMarkerLabelCell(marker),
          formatTime(marker.time),
          marker.freq.toFixed(2),
          createMarkerDeleteButton()
        ],
        deleteSelector: ".gram-frame-marker-delete-btn",
        onSelect: (markerId, _marker, index) => this.instance.interaction.toggleSelection("marker", markerId, index),
        onDelete: (markerId) => this.removeMarker(markerId),
        isSelected: (markerId) => this.instance.interaction.isFeatureSelected("marker", markerId)
      });
      this.uiElements.markersTable = this.markersTable.element;
      this.updateMarkersTable();
    }
    /**
     * Re-render this mode's persistent panel from current state.
     *
     * The `PanelOwner` capability. `MainUI` used to reach in by name and call
     * `updateMarkersTable` through an `any` cast; it now asks every mode that
     * owns a panel to refresh it (spec 167, FR-006, AS-4.2).
     */
    refreshPanel() {
      this.updateMarkersTable();
    }
    /**
     * Update markers table with current markers
     */
    updateMarkersTable() {
      if (!this.markersTable) return;
      this.markersTable.update(this.markers);
    }
    /**
     * Update LED displays for analysis mode
     * @param {CursorPosition} _coords - Current cursor coordinates
     */
    updateLEDs(_coords) {
    }
    /**
     * Get initial state for analysis mode
     * @returns {AnalysisInitialState} Analysis mode state including markers
     */
    static getInitialState() {
      return {
        analysis: {
          markers: []
        }
      };
    }
    /**
     * Add a new persistent marker
     * @param {AnalysisMarker} marker - Marker object with all properties
     */
    addMarker(marker) {
      const state = this.instance.state;
      if (!state.analysis) {
        state.analysis = { markers: [] };
      }
      state.analysis.markers.push(marker);
      const index = state.analysis.markers.length - 1;
      this.instance.interaction.setSelection("marker", marker.id, index);
      commitAnnotationChange(this.instance, () => this.updateMarkersTable(), { frame: true });
    }
    /**
     * Remove a marker by ID
     * @param {string} markerId - ID of marker to remove
     */
    removeMarker(markerId) {
      const markers = this.markers;
      const index = markers.findIndex((m) => m.id === markerId);
      if (index !== -1) {
        if (this.instance.interaction.isFeatureSelected("marker", markerId)) {
          this.instance.interaction.clearSelection();
        }
        markers.splice(index, 1);
        recordDeletion(this.instance, "markers", markerId);
        commitAnnotationChange(this.instance, () => this.updateMarkersTable(), { frame: true });
      }
    }
    /**
     * Set (or clear) a marker's label and re-render everything that shows it.
     *
     * Passing an empty or whitespace-only label removes it, so "clear the field
     * and save" is how a label is deleted.
     * @param {string} markerId - ID of the marker to update
     * @param {string|undefined} label - New label, or `undefined`/empty to remove it
     */
    setMarkerLabel(markerId, label) {
      const marker = this.findMarker(markerId);
      if (!marker) return;
      const normalized = normalizeMarkerLabel(label);
      if (normalized) {
        marker.label = normalized;
      } else {
        delete marker.label;
      }
      commitAnnotationChange(this.instance, () => this.updateMarkersTable());
    }
    /**
     * Find marker at given position (with tolerance)
     * Returns a drag target object compatible with BaseDragHandler
     * @param {DataCoordinates} position - Position to check
     * @returns {DragTarget|null} Drag target if found, null otherwise
     */
    findMarkerAtPosition(position) {
      const tolerance = getUniformTolerance(this.getViewport(), this.instance.ui.spectrogramImage);
      const marker = this.markers.find((candidate) => {
        if (isWithinToleranceRadius(
          position,
          { freq: candidate.freq, time: candidate.time },
          tolerance
        )) {
          return true;
        }
        if (!drawsCrosshair(candidate)) {
          return false;
        }
        const markerPoint = { freq: candidate.freq, time: candidate.time };
        const markerSVG = dataToSVG(markerPoint, this.getViewport(), this.instance.ui.spectrogramImage);
        const clickSVG = dataToSVG(position, this.getViewport(), this.instance.ui.spectrogramImage);
        const crosshairSize = CROSSHAIR_SIZE;
        const lineThickness = 3;
        const onHorizontalLine = Math.abs(clickSVG.y - markerSVG.y) <= lineThickness && Math.abs(clickSVG.x - markerSVG.x) <= crosshairSize;
        const onVerticalLine = Math.abs(clickSVG.x - markerSVG.x) <= lineThickness && Math.abs(clickSVG.y - markerSVG.y) <= crosshairSize;
        return onHorizontalLine || onVerticalLine;
      });
      if (marker) {
        return {
          kind: "move",
          id: marker.id,
          type: "marker",
          position: { freq: marker.freq, time: marker.time },
          data: marker
        };
      }
      return null;
    }
    /**
     * Update mode-specific LED values based on cursor position
     */
    updateModeSpecificLEDs() {
    }
    /**
     * Clean up analysis mode state
     */
    cleanup() {
    }
    /**
     * Destroy mode-specific UI elements when leaving this mode
     */
    destroyUI() {
    }
    /**
     * Reset analysis mode state
     */
    resetState() {
    }
  }
  const MAX_VISIBLE_PINS = 25;
  const NICE_STEPS = [1, 2, 5, 10, 25, 50, 100, 250, 500, 1e3, 2500, 5e3];
  function countMultiples(minHarmonic, maxHarmonic, step) {
    return Math.floor(maxHarmonic / step) - Math.floor((minHarmonic - 1) / step);
  }
  function chooseSamplingStep(minHarmonic, maxHarmonic, max = MAX_VISIBLE_PINS) {
    for (const step of NICE_STEPS) {
      if (countMultiples(minHarmonic, maxHarmonic, step) <= max) {
        return step;
      }
    }
    return NICE_STEPS[NICE_STEPS.length - 1];
  }
  function sampledHarmonics(minHarmonic, maxHarmonic, max = MAX_VISIBLE_PINS) {
    if (maxHarmonic < minHarmonic) {
      return { step: 1, harmonics: [] };
    }
    const step = chooseSamplingStep(minHarmonic, maxHarmonic, max);
    const first = Math.ceil(minHarmonic / step) * step;
    const harmonics = [];
    for (let h = first; h <= maxHarmonic && harmonics.length < max; h += step) {
      harmonics.push(h);
    }
    return { step, harmonics };
  }
  const MIN_PIN_SPACING = 0.1;
  class PinSetMode extends BaseMode {
    /**
     * Base pixel size (width/height) of a pin's symbol mark. The effective size is
     * this scaled by the "Large" symbol-size experiment toggle — use
     * {@link PinSetMode#symbolSize} rather than reading this directly.
     * @type {number}
     */
    static SYMBOL_SIZE = 10;
    /**
     * Height of a pin line, as a fraction of the *base* (unzoomed) render height.
     *
     * The resulting height is a fixed pixel length, not a span of time: it is
     * derived from the viewport's base render size (which tracks expand, not zoom)
     * rather than from the zoomed image element. Pins therefore keep the same
     * on-screen height at every zoom level, growing/shrinking only when the
     * component itself is resized.
     * @type {number}
     */
    static PIN_HEIGHT_RATIO = 0.2;
    /**
     * Height (px) of a mini-pin: the stub line drawn under each member of a set
     * whose full pin is hidden.
     *
     * Fixed rather than derived, by design (spec: issue #232). It is half the
     * height of a "Large" symbol mark (SYMBOL_SIZE * LARGE_SYMBOL_SCALE = 20px),
     * which is enough to tie each pin to the data beneath it without reinstating
     * the clutter the pin toggle exists to remove.
     * @type {number}
     */
    static MINI_PIN_HEIGHT = 10;
    /**
     * Maximum pin lines rendered per set. At the 0.1 Hz minimum spacing a
     * standard 0–20 kHz config has 200,000 visible members; drawing an SVG line
     * for each — rebuilt on every drag frame — locked the browser (BH-2). Past
     * this cap the drawn lines are a regular sample of the range; well beyond
     * typical screen widths, adjacent pins merge on screen anyway, so the thinning
     * is invisible until the set is already a solid block.
     * @type {number}
     */
    static MAX_PIN_LINES = 1e3;
    /**
     * Font size (px) of a pin's number label. The plate the label sits on is
     * sized from it too, so it also fixes how much room the stack leaves above
     * and below the text (see `utils/labelPlate.js`).
     * @type {number}
     */
    static LABEL_FONT_SIZE = 12;
    /**
     * Vertical gap (px) between the edge of the pin label's plate and its symbol.
     * @type {number}
     */
    static LABEL_GAP = 3;
    /**
     * Minimum padding (px) kept between the top of a pin's label and the top edge
     * of the spectrogram image.
     * @type {number}
     */
    static STACK_TOP_PAD = 1;
    /**
     * Wire up the one drag handler both pin-set drags run through.
     *
     * Moving an existing set (`move`) and creating one by dragging (`create`)
     * differ only in how the target is resolved — a create mints its set on
     * mousedown — and share every subsequent step (spec 166, FR-004).
     * @param {GramFrame} instance - GramFrame instance
     * @param {ModeType} modeName - Mode that owns the drag, for the projection
     */
    constructor(instance, modeName) {
      super(instance);
      this.dragHandler = new BaseDragHandler(instance, {
        // A feature drag always carries a data position. Only the pan drag passes
        // null, and it runs on its own handler in `core/events.js`.
        resolveTarget: (position) => this.resolvePinSetDrag(
          /** @type {DataCoordinates} */
          position
        ),
        // Hover only ever *finds* — resolvePinSetDrag mints a new set when the
        // cursor is over empty gram, which is right for a mousedown and wrong for
        // a hover (a hover that creates features floods the gram with sets).
        resolveHoverTarget: (position) => this.findSetTarget(
          /** @type {DataCoordinates} */
          position
        ),
        onDragStart: (target) => this.onSetDragStart(target),
        onDragMove: (target, currentPos, startPos) => this.onSetDragUpdate(
          target,
          /** @type {DataCoordinates} */
          currentPos,
          /** @type {DataCoordinates} */
          startPos
        ),
        onDragEnd: () => this.onSetDragEnd(),
        onDragCancel: () => this.onSetDragEnd(),
        updateCursor: (style) => this.updateCursorStyle(style)
      }, modeName);
    }
    // ---------------------------------------------------------------------------
    // Subclass contract. Every member below is abstract: the base class calls it
    // and cannot answer it, so a subclass that forgets one fails loudly rather
    // than drawing nothing.
    // ---------------------------------------------------------------------------
    /**
     * The sets this mode owns, live (mutated in place by add/remove).
     * @returns {PinSet[]} This mode's sets
     */
    get sets() {
      throw new Error(`${this.constructor.name} must implement the "sets" getter`);
    }
    /**
     * Selection type used for this mode's sets, as `state.selection.selectedType`.
     * @returns {SelectedFeatureType} Selection type
     */
    get selectionType() {
      throw new Error(`${this.constructor.name} must implement the "selectionType" getter`);
    }
    /**
     * Which stored collection this mode's sets live in, and therefore which
     * tombstone family a deletion belongs to (issue #269).
     *
     * Derived from `selectionType` rather than declared again: the two are the
     * same fact -- `harmonicSet` sets live in `harmonicSets` -- and a subclass
     * that had to state both could state them inconsistently.
     * @returns {'harmonicSets'|'sidebandSets'} Stored collection name
     */
    get tombstoneCollection() {
      return (
        /** @type {'harmonicSets'|'sidebandSets'} */
        `${this.selectionType}s`
      );
    }
    /**
     * Prefix for generated set ids, and the DOM naming stem for this mode's pins.
     * @returns {PinSetClassNames} Class and attribute names for the drawn pins
     */
    get pinNames() {
      throw new Error(`${this.constructor.name} must implement the "pinNames" getter`);
    }
    /**
     * Frequency (Hz, in the raw configured scale) of a set member.
     * @param {PinSet} _set - The set
     * @param {number} _index - Member index
     * @returns {number} Frequency of that member
     */
    freqForIndex(_set, _index) {
      throw new Error(`${this.constructor.name} must implement freqForIndex()`);
    }
    /**
     * Inclusive member-index range of a set within the currently visible span.
     * @param {PinSet} _set - The set
     * @returns {{minIndex: number, maxIndex: number}} Inclusive index range
     */
    visibleIndexRange(_set) {
      throw new Error(`${this.constructor.name} must implement visibleIndexRange()`);
    }
    /**
     * Member index nearest a probe frequency — the only member (±1) that can be
     * within frequency tolerance of it.
     * @param {PinSet} _set - The set
     * @param {number} _freq - Probe frequency
     * @returns {number} Nearest member index
     */
    nearestIndex(_set, _freq) {
      throw new Error(`${this.constructor.name} must implement nearestIndex()`);
    }
    /**
     * Text of a member's number label.
     * @param {number} _index - Member index
     * @returns {string} Label text
     */
    labelTextFor(_index) {
      throw new Error(`${this.constructor.name} must implement labelTextFor()`);
    }
    /**
     * Mint a new set at the mousedown position and return it as a `create`-kind
     * drag target, so the rest of the gesture is an ordinary drag.
     * @param {DataCoordinates} _dataCoords - Position of the mousedown
     * @returns {DragTarget|null} A create-kind target, or null if none can be made
     */
    createSetTarget(_dataCoords) {
      throw new Error(`${this.constructor.name} must implement createSetTarget()`);
    }
    /**
     * The frequency-axis half of a drag: what changes when the pointer moves
     * horizontally. The time-axis half (the anchor) is shared and handled here.
     * @param {PinSet} _set - The set being dragged
     * @param {number} _clickedIndex - Member index the drag grabbed
     * @param {DataCoordinates} _currentPos - Current pointer position
     * @returns {Partial<PinSet>} Updates to apply
     */
    freqUpdatesForDrag(_set, _clickedIndex, _currentPos) {
      throw new Error(`${this.constructor.name} must implement freqUpdatesForDrag()`);
    }
    /**
     * Whether this mode's table shows anything derived from the cursor position,
     * and so has to be re-rendered as the pointer moves.
     *
     * Not abstract: false is the answer for a table of plain feature properties,
     * and a mode says otherwise only when it has a reason to.
     * @returns {boolean} True if the table follows the cursor
     */
    get panelTracksCursor() {
      return false;
    }
    /**
     * Re-render this mode's table from current state.
     */
    updatePanel() {
      throw new Error(`${this.constructor.name} must implement updatePanel()`);
    }
    // ---------------------------------------------------------------------------
    // Pointer handling
    // ---------------------------------------------------------------------------
    /**
     * Handle mouse move events
     * @param {MouseEvent} _event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseMove(_event, dataCoords) {
      if (this.dragHandler && this.dragHandler.isDragging()) {
        this.dragHandler.handleMouseMove(dataCoords);
      } else if (this.dragHandler) {
        this.dragHandler.updateCursorForHover(dataCoords);
      }
      if (this.panelTracksCursor && this.sets.length > 0) {
        this.updatePanel();
      }
    }
    /**
     * Handle mouse down events
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseDown(event, dataCoords) {
      if (event.button !== 0) {
        return;
      }
      if (this.dragHandler) {
        this.dragHandler.startDrag(dataCoords, event);
      }
    }
    /**
     * Handle mouse up events
     * @param {MouseEvent} _event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseUp(_event, dataCoords) {
      if (this.dragHandler) {
        this.dragHandler.endDrag(dataCoords);
      }
    }
    /**
     * Find the set under a position and describe it as a `move` drag target.
     * @param {DataCoordinates} position - Position to check
     * @returns {DragTarget|null} Drag target if found, null otherwise
     */
    findSetTarget(position) {
      const set = this.findSetAt(position);
      if (set) {
        return {
          kind: "move",
          id: set.id,
          type: this.selectionType,
          position,
          data: {
            set,
            clickedIndex: this.nearestIndex(set, position.freq),
            originalAnchorTime: set.anchorTime
          }
        };
      }
      return null;
    }
    /**
     * Resolve what a mousedown starts.
     *
     * Landing on an existing set moves it; landing anywhere else creates one and
     * drags it out from there. The new set is minted here, on mousedown, so the
     * engine has a target id for the whole gesture (contract: drag-engine.md).
     * @param {DataCoordinates} position - Position of the mousedown
     * @returns {DragTarget|null} A move- or create-kind target
     */
    resolvePinSetDrag(position) {
      return this.findSetTarget(position) || this.createSetTarget(position);
    }
    /**
     * Start dragging a set: select it, as clicking its table row would.
     * @param {DragTarget} target - Drag target with id and type
     */
    onSetDragStart(target) {
      const index = this.sets.findIndex((set) => set.id === target.id);
      if (index !== -1) {
        this.instance.interaction.setSelection(
          this.selectionType,
          /** @type {string} */
          target.id,
          index
        );
      }
    }
    /**
     * Update a set during a drag.
     * @param {DragTarget} target - Drag target
     * @param {DataCoordinates} currentPos - Current position
     * @param {DataCoordinates} startPos - Position the drag started from
     */
    onSetDragUpdate(target, currentPos, startPos) {
      this.instance.state.cursorPosition = {
        freq: currentPos.freq,
        time: currentPos.time,
        x: 0,
        y: 0,
        svgX: 0,
        svgY: 0,
        imageX: 0,
        imageY: 0
        // Minimal values for compatibility
      };
      this.applySetDrag(target, currentPos, startPos);
    }
    /**
     * End (or cancel) a set drag.
     */
    onSetDragEnd() {
    }
    /**
     * Apply a set drag — the shared step for both the `move` and `create` kinds,
     * which differ only in how their target was resolved.
     * @param {DragTarget} target - The drag target from the engine
     * @param {DataCoordinates} currentPos - Current pointer position
     * @param {DataCoordinates} startPos - Where the drag began
     */
    applySetDrag(target, currentPos, startPos) {
      if (!target || !currentPos || !startPos) return;
      const setId = target.id;
      if (!setId) return;
      const set = this.sets.find((candidate) => candidate.id === setId);
      if (!set) return;
      const clickedIndex = target.data && target.data.clickedIndex !== void 0 ? target.data.clickedIndex : 1;
      const updates = { ...this.freqUpdatesForDrag(set, clickedIndex, currentPos) };
      const originalAnchorTime = target.data && target.data.originalAnchorTime !== void 0 ? target.data.originalAnchorTime : set.anchorTime;
      const deltaTime = currentPos.time - startPos.time;
      const { timeMin, timeMax } = this.instance.state.config;
      updates.anchorTime = Math.max(timeMin, Math.min(timeMax, originalAnchorTime + deltaTime));
      this.updateSet(setId, updates);
    }
    // ---------------------------------------------------------------------------
    // Set lifecycle
    // ---------------------------------------------------------------------------
    /**
     * Add a set, seeded with this session's style choices, and select it.
     *
     * The subclass supplies only the geometry (`anchorTime`, `spacing`, and for
     * sidebands the fundamental); colour, symbol, pin visibility and symbol size
     * come from the style panel and are the same for every pin set.
     * @param {Partial<PinSet>} geometry - Geometry fields for the new set
     * @returns {PinSet} The created set
     */
    addSet(geometry) {
      const id = `${this.pinNames.idPrefix}-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      const palette = PinSetMode.SET_COLORS;
      const color = this.instance.state.selectedColor || palette[this.sets.length % palette.length];
      const set = (
        /** @type {PinSet} */
        {
          id,
          color,
          // Use selected symbol from global state, defaulting to the symbol-less cross
          symbol: this.instance.state.selectedSymbol || "cross",
          // Use the session's pin-visibility preference (on unless the analyst
          // turned it off via the style panel toggle)
          showPin: this.instance.state.showHarmonicPin !== false,
          // EXPERIMENT (temporary): symbol size is carried per set, seeded from the
          // toggle's next-feature default, so sets at both sizes can coexist.
          largeSymbols: !!this.instance.state.largeSymbols,
          ...geometry
        }
      );
      this.sets.push(set);
      this.instance.interaction.setSelection(this.selectionType, set.id, this.sets.length - 1);
      commitAnnotationChange(this.instance, () => this.updatePanel(), { frame: true });
      return set;
    }
    /**
     * Update an existing set.
     * @param {string} id - Set ID
     * @param {Partial<PinSet>} updates - Properties to update
     */
    updateSet(id, updates) {
      const setIndex = this.sets.findIndex((set) => set.id === id);
      if (setIndex === -1) {
        return;
      }
      Object.assign(this.sets[setIndex], updates);
      commitAnnotationChange(this.instance, () => this.updatePanel(), { frame: true });
    }
    /**
     * Remove a set.
     * @param {string} id - Set ID
     */
    removeSet(id) {
      const setIndex = this.sets.findIndex((set) => set.id === id);
      if (setIndex === -1) {
        return;
      }
      const { selection } = this.instance.state;
      if (selection.selectedType === this.selectionType && selection.selectedId === id) {
        this.instance.interaction.clearSelection();
      }
      this.sets.splice(setIndex, 1);
      recordDeletion(this.instance, this.tombstoneCollection, id);
      commitAnnotationChange(this.instance, () => this.updatePanel());
    }
    /**
     * Nudging a set's spacing with the arrow keys.
     *
     * The floor is `MIN_PIN_SPACING`, the same one `freqUpdatesForDrag` clamps a
     * *drag* to. HarmonicsMode used to override this method for no other reason
     * than to raise its own floor to 1 Hz, so the same set reached 0.1 Hz under
     * the mouse and stopped at 1.0 Hz under the arrow keys -- the drift the
     * August review predicted and the September one found (R9-13). The 1 Hz
     * comment cited a hang; that class of failure is held by `MAX_PIN_LINES`
     * now, which is what makes a full-width drag to the floor safe, and a
     * keypress at a time is gentler than a drag.
     * @param {PinSet} set - The set being nudged
     * @param {number} freqDelta - What the keypress is worth in Hz, signed
     * @returns {Partial<PinSet>} Spacing update
     */
    nudgeFreqUpdates(set, freqDelta) {
      return { spacing: Math.max(MIN_PIN_SPACING, set.spacing + freqDelta) };
    }
    // ---------------------------------------------------------------------------
    // Hit testing
    // ---------------------------------------------------------------------------
    /**
     * Find the set whose drawn geometry contains the given position.
     *
     * Hit-testing follows exactly what is drawn — nothing more, nothing less.
     * Every visible part of a pin grabs it: the line's fixed-pixel span AND the
     * number label + symbol stacked above it. A set with its pin hidden draws
     * mini-pins, so its line region shrinks to that stub — the empty span below,
     * where a full pin would have reached, is blank on screen and blank to the
     * mouse too.
     *
     * Takes the probe position as a parameter rather than reading
     * `state.cursorPosition`: the stored cursor goes stale during pans (wheel-pan
     * suppresses mousemove), and a click tested against the pre-pan time missed
     * the pin and minted a duplicate set on top of it (BH-13).
     *
     * Bounded work per set (BH-2): the range is the VISIBLE one (zoom-aware, the
     * same source the renderer uses), only the member nearest the probe frequency
     * (±1) is line-tested — no other line can be within frequency tolerance — and
     * the stack test walks just the thinned labelled subset.
     *
     * @param {DataCoordinates} position - Probe position {freq, time}
     * @returns {PinSet|null} The set if found, null otherwise
     */
    findSetAt(position) {
      if (!position) return null;
      const { freq, time } = position;
      for (const set of this.sets) {
        if (!(set.spacing > 0)) continue;
        const { minIndex, maxIndex } = this.visibleIndexRange(set);
        if (maxIndex < minIndex) continue;
        const { lineHeight, lineTop } = this.pinLineDimensions(set);
        const stack = this.labelStackBounds(lineTop, set);
        const labelled = this.labelledIndices(minIndex, maxIndex);
        const pinDrawn = set.showPin !== false;
        const lineFrom = pinDrawn ? lineTop : stack.symbolBottom;
        const lineTo = lineFrom + (pinDrawn ? lineHeight : PinSetMode.MINI_PIN_HEIGHT);
        const tolerance = getUniformTolerance(this.getViewport(), this.instance.ui.spectrogramImage);
        const cursorSVG = dataToSVG(
          { freq, time },
          this.getViewport(),
          this.instance.ui.spectrogramImage
        );
        if (cursorSVG.y >= lineFrom && cursorSVG.y <= lineTo) {
          const nearest = this.nearestIndex(set, freq);
          const from = Math.max(minIndex, nearest - 1);
          const to = Math.min(maxIndex, nearest + 1);
          for (let index = from; index <= to; index++) {
            if (Math.abs(freq - this.freqForIndex(set, index)) < tolerance.freq) {
              return set;
            }
          }
        }
        if (cursorSVG.y >= stack.top && cursorSVG.y <= stack.bottom) {
          for (const index of labelled) {
            if (Math.abs(cursorSVG.x - this.pinX(set, index)) <= this.labelStackHalfWidth(set, index)) {
              return set;
            }
          }
        }
      }
      return null;
    }
    // ---------------------------------------------------------------------------
    // Geometry
    // ---------------------------------------------------------------------------
    /**
     * The visible frequency span, as the frequency axis reports it.
     *
     * Viewport-aware: zooming in narrows the span (fewer pins), zooming out /
     * panning widens it. At zoom 1.0 it equals the full data range.
     * @returns {{freqMin: number, freqMax: number}} Visible frequency span
     */
    visibleFrequencySpan() {
      const { freqMin, freqMax } = calculateVisibleDataRange(
        this.instance.state,
        this.instance.ui.spectrogramImage
      );
      return { freqMin, freqMax };
    }
    /**
     * The "major" subset of member indices that receive a number label and symbol,
     * thinned to at most the label limit (default 25) by regular sampling.
     *
     * Every pin line is still drawn (spec 159); this limit governs labels and
     * symbols only. When the visible range already fits under the limit the subset
     * is the whole range, so every drawn pin is labelled (FR-005).
     * @param {number} minIndex - Lowest visible member index
     * @param {number} maxIndex - Highest visible member index
     * @returns {number[]} Ascending member indices to label/symbol
     */
    labelledIndices(minIndex, maxIndex) {
      return sampledHarmonics(minIndex, maxIndex).harmonics;
    }
    /**
     * Calculate pin line dimensions and positions.
     *
     * The height is a fixed pixel length taken from the *base* (unzoomed) render
     * height, so a pin covers the same number of screen pixels no matter how far
     * the user has zoomed in — it is not a span of time that stretches with the
     * image. Only the top is zoom-aware: the pin hangs from the set's anchor
     * time (the original click location), so it tracks the feature while keeping
     * a constant height. The anchor is the symbol/pin junction — the point the
     * analyst aimed at — whichever pin style is on, so pin height never moves
     * where the feature lands (issue #284).
     *
     * @param {PinSet} set - The set being drawn
     * @returns {{lineHeight: number, lineTop: number}} Fixed pixel height and top Y position
     */
    pinLineDimensions(set) {
      const { renderHeight } = getRenderDimensions(this.instance.state);
      const lineHeight = renderHeight * PinSetMode.PIN_HEIGHT_RATIO;
      const anchorPoint = { freq: this.freqForIndex(set, 1), time: set.anchorTime };
      const anchorSVG = dataToSVG(anchorPoint, this.getViewport(), this.instance.ui.spectrogramImage);
      const lineTop = anchorSVG.y;
      return { lineHeight, lineTop };
    }
    /**
     * Compute the SVG x-coordinate of a member's vertical pin line.
     * @param {PinSet} set - The set
     * @param {number} index - Member index
     * @returns {number} SVG x-coordinate of the pin line
     */
    pinX(set, index) {
      const point = { freq: this.freqForIndex(set, index), time: set.anchorTime };
      return dataToSVG(point, this.getViewport(), this.instance.ui.spectrogramImage).x;
    }
    /**
     * Effective pixel size of a set's symbol marks: the base size scaled by that
     * set's own large-symbol flag, so sets at both sizes can share a gram. The
     * whole label/symbol stack layout derives from this, so the label spacing and
     * top-edge clamping follow the set's chosen size.
     * @param {PinSet} set - The set
     * @returns {number} Symbol diameter in px
     */
    symbolSize(set) {
      return PinSetMode.SYMBOL_SIZE * resolveSymbolScale(set);
    }
    /**
     * Compute the shared vertical layout of a pin's label/symbol stack.
     *
     * Ideal (top-to-bottom): label baseline, then symbol, then the pin line top,
     * so the symbol caps the line and the label sits above the symbol. When the
     * stack's top would clip above the spectrogram's top edge, the whole stack
     * (label + symbol) is nudged down by the overflow so it stays legible
     * (spec 159, FR-011).
     *
     * An upward-pointing triangle inverts the label (issue #242): its apex points
     * at the gram above the pin, so a number stacked over it hides exactly the
     * data the set was placed against. That label drops to the symbol's underside
     * instead, over the pin line's top — ink the set already spends there. The
     * symbol keeps capping the line either way, so the pin's anchor never moves.
     *
     * @param {number} lineTop - Top Y position of the pin lines (SVG coords)
     * @param {number} imageTop - Top edge of the spectrogram image in SVG coords
     * @param {PinSet} set - Set being laid out (its symbol size drives the stack)
     * @returns {{symbolCy: number, labelY: number}} Symbol centre and label baseline Y
     */
    labelStackPositions(lineTop, imageTop, set) {
      const r = this.symbolSize(set) / 2;
      const gap = PinSetMode.LABEL_GAP;
      const plate = labelPlateExtents(PinSetMode.LABEL_FONT_SIZE);
      const below = labelSitsBelowSymbol(set.symbol);
      let symbolCy = lineTop - r;
      let labelY = below ? symbolCy + r + gap + plate.above : symbolCy - r - gap - plate.below;
      const stackTop = below ? symbolCy - r : labelY - plate.above;
      const minTop = imageTop + PinSetMode.STACK_TOP_PAD;
      if (stackTop < minTop) {
        const shift = minTop - stackTop;
        symbolCy += shift;
        labelY += shift;
      }
      return { symbolCy, labelY };
    }
    /**
     * Vertical extent (SVG coords) of a pin's label/symbol stack, for hit-testing.
     *
     * Derived from the same {@link PinSetMode#labelStackPositions} layout the
     * renderer uses, so the grab region tracks the drawn stack — including the
     * downward nudge applied near the image's top edge, and the label's drop to
     * the underside of an up-pointing triangle (issue #242): move the text and
     * the hotspot moves with it. The bottom is clamped to the pin line's top so
     * the stack region and the line region always meet with no dead gap between
     * them.
     *
     * `symbolBottom` is reported separately because it, not the region's bottom,
     * is where a mini-pin hangs from — a label drawn below the symbol pushes the
     * region past the stub it would otherwise anchor.
     *
     * @param {number} lineTop - Top Y position of the pin lines (SVG coords)
     * @param {PinSet} set - Set being hit-tested
     * @returns {{top: number, bottom: number, symbolBottom: number}} Stack region and the symbol's underside
     */
    labelStackBounds(lineTop, set) {
      const imageTop = getImageBounds(this.getViewport(), this.instance.ui.spectrogramImage).top;
      const { symbolCy, labelY } = this.labelStackPositions(lineTop, imageTop, set);
      const r = this.symbolSize(set) / 2;
      const below = labelSitsBelowSymbol(set.symbol);
      const symbolBottom = symbolCy + r;
      const plate = labelPlateExtents(PinSetMode.LABEL_FONT_SIZE);
      return {
        // The top of the label's plate — unless the label hangs below, in which
        // case the symbol leads the stack.
        top: below ? symbolCy - r : labelY - plate.above,
        // The plate's underside is the bottom of the stack when the label trails.
        bottom: Math.max(lineTop, below ? labelY + plate.below : symbolBottom),
        symbolBottom
      };
    }
    /**
     * Half-width (SVG px) of a pin's label/symbol stack, for hit-testing.
     *
     * The wider of the symbol mark and the number label, so both are grabbable:
     * a `cross` set has no symbol but still shows its label, and a "Large
     * symbols" set's mark is wider than its text. The label's half-width is the
     * plate's, measured the same way the renderer sizes it, so the grab region
     * covers exactly the white rectangle the analyst is aiming at.
     *
     * @param {PinSet} set - Set being hit-tested
     * @param {number} index - Member index whose label is drawn
     * @returns {number} Half-width in SVG pixels
     */
    labelStackHalfWidth(set, index) {
      const fontSize = PinSetMode.LABEL_FONT_SIZE;
      const plate = labelPlateRect({
        x: 0,
        y: 0,
        textAnchor: "middle",
        width: measureLabelWidth(this.labelTextFor(index), fontSize),
        fontSize
      });
      return Math.max(this.symbolSize(set) / 2, plate.width / 2);
    }
    // ---------------------------------------------------------------------------
    // Rendering
    // ---------------------------------------------------------------------------
    /**
     * Create the SVG line element for one pin.
     * @param {number} index - Member index
     * @param {PinSet} set - The set
     * @param {number} lineX - X position for the line
     * @param {number} lineTop - Top Y position for the line
     * @param {number} lineHeight - Height of the line
     * @returns {SVGLineElement} SVG line element
     */
    createPinLine(index, set, lineX, lineTop, lineHeight) {
      const names = this.pinNames;
      const line2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line2.setAttribute("class", names.lineClass);
      line2.setAttribute(names.setIdAttribute, set.id);
      line2.setAttribute(names.indexAttribute, String(index));
      line2.setAttribute("x1", String(lineX));
      line2.setAttribute("y1", String(lineTop));
      line2.setAttribute("x2", String(lineX));
      line2.setAttribute("y2", String(lineTop + lineHeight));
      line2.setAttribute("stroke", set.color);
      line2.setAttribute("stroke-width", "2");
      line2.setAttribute("stroke-linecap", "round");
      line2.setAttribute("opacity", "0.9");
      return line2;
    }
    /**
     * Create the short stub line drawn under a member when the set's full pin is
     * hidden.
     *
     * Same colour and stroke as a full pin line, so a mini-pin reads as the same
     * feature at a smaller scale; only its class and height differ. The distinct
     * class keeps the two apart for cleanup, hit-testing and tests — a hidden-pin
     * set still draws no full pin line.
     *
     * @param {number} index - Member index
     * @param {PinSet} set - The set
     * @param {number} lineX - X position of the mini-pin
     * @param {number} top - Top Y position of the mini-pin (the symbol's underside)
     * @returns {SVGLineElement} SVG line element
     */
    createMiniPin(index, set, lineX, top) {
      const miniPin = this.createPinLine(index, set, lineX, top, PinSetMode.MINI_PIN_HEIGHT);
      miniPin.setAttribute("class", this.pinNames.miniPinClass);
      return miniPin;
    }
    /**
     * Create the plated text label for a member.
     *
     * Centred horizontally on the pin's line (`text-anchor: middle` at `lineX`) and
     * positioned above the pin's symbol (baseline at `labelY`), so the vertical
     * stack over a pin reads label -> symbol -> line (spec 159, FR-009/FR-010).
     * {@link PinSetMode#labelStackPositions} owns that baseline, so a set whose
     * symbol carries its label underneath needs nothing special here.
     *
     * The characters are drawn black on a white rounded plate rather than in the
     * set's colour: a single colour is only legible over part of a gram, whereas
     * the plate reads over both dark and light backgrounds (issue #243). Set
     * identity is still carried by the pin's line and symbol colour.
     *
     * @param {number} index - Member index
     * @param {PinSet} set - The set
     * @param {number} lineX - X position of the pin line (label is centred on it)
     * @param {number} labelY - Baseline Y position for the label text
     * @returns {SVGGElement} Group holding the plate and its text
     */
    createPinLabel(index, set, lineX, labelY) {
      const names = this.pinNames;
      const label = (
        /** @type {SVGTextElement} */
        document.createElementNS("http://www.w3.org/2000/svg", "text")
      );
      label.setAttribute("class", names.labelClass);
      label.setAttribute(names.setIdAttribute, set.id);
      label.setAttribute(names.indexAttribute, String(index));
      label.setAttribute("x", String(lineX));
      label.setAttribute("y", String(labelY));
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("font-size", String(PinSetMode.LABEL_FONT_SIZE));
      label.setAttribute("font-weight", "bold");
      label.setAttribute("font-family", "Arial, sans-serif");
      label.textContent = this.labelTextFor(index);
      return plateLabel(label);
    }
    /**
     * Create the filled symbol mark drawn between a pin's number label and the top
     * of its line.
     *
     * The vertical position (`symbolCy`) is computed once per set by
     * {@link PinSetMode#labelStackPositions} so the whole label/symbol stack
     * shares a consistent, on-screen layout.
     *
     * @param {PinSet} set - The set
     * @param {number} lineX - X position of the pin line (symbol is centred on it)
     * @param {number} symbolCy - Centre Y position for the symbol
     * @returns {SVGElement|null} SVG symbol element, or null for the `cross` (symbol-less) style
     */
    createPinSymbol(set, lineX, symbolCy) {
      const symbol = createSymbolMark(set.symbol, lineX, symbolCy, this.symbolSize(set), set.color);
      if (!symbol) {
        return null;
      }
      symbol.setAttribute(this.pinNames.setIdAttribute, set.id);
      return symbol;
    }
    /**
     * Whether this mode currently owns any persistent feature.
     *
     * Half of the `PersistentFeatureProvider` capability.
     * @returns {boolean} True if at least one set exists
     */
    hasPersistentFeatures() {
      return this.sets.length > 0;
    }
    /**
     * Render every set this mode owns.
     */
    renderPersistentFeatures() {
      if (!this.instance.ui.cursorGroup) {
        return;
      }
      const names = this.pinNames;
      const existingLines = this.instance.ui.cursorGroup.querySelectorAll(
        `.${names.lineClass}, .${names.miniPinClass}`
      );
      existingLines.forEach((line2) => line2.remove());
      const existingSymbols = this.instance.ui.cursorGroup.querySelectorAll(
        `.gram-frame-harmonic-symbol[${names.setIdAttribute}]`
      );
      existingSymbols.forEach((symbol) => symbol.remove());
      this.sets.forEach((set) => this.renderSet(set));
    }
    /**
     * Render a single set as vertical pin lines.
     *
     * Spec 159: draw a pin line for EVERY member in the visible span (no pins are
     * dropped, even if they merge into a solid block), then draw a number label
     * and symbol only for the thinned "major" subset so the overlay stays
     * readable. Lines are appended first so the labels/symbols paint on top.
     *
     * A set with `showPin === false` draws a mini-pin per member instead of a
     * full-height line: a stub hanging from the symbol's underside, in the set's
     * colour. Labels and symbols are thinned, so without them a pin-less set gave
     * no sign of where the members between the labelled ones actually fell
     * (issue #232); the mini-pins restore that alignment with the data at a
     * fraction of the ink. The label/symbol geometry is unchanged either way, so
     * toggling the pin swaps line lengths without moving anything else.
     *
     * @param {PinSet} set - Set to render
     */
    renderSet(set) {
      if (!this.instance.ui.cursorGroup) {
        return;
      }
      const { minIndex, maxIndex } = this.visibleIndexRange(set);
      if (maxIndex < minIndex) {
        return;
      }
      const { lineHeight, lineTop } = this.pinLineDimensions(set);
      const imageTop = getImageBounds(this.getViewport(), this.instance.ui.spectrogramImage).top;
      const { symbolCy, labelY } = this.labelStackPositions(lineTop, imageTop, set);
      const pinDrawn = set.showPin !== false;
      const visibleCount = maxIndex - minIndex + 1;
      const stride = Math.max(1, Math.ceil(visibleCount / PinSetMode.MAX_PIN_LINES));
      const miniPinTop = symbolCy + this.symbolSize(set) / 2;
      for (let index = minIndex; index <= maxIndex; index += stride) {
        const lineX = this.pinX(set, index);
        const line2 = pinDrawn ? this.createPinLine(index, set, lineX, lineTop, lineHeight) : this.createMiniPin(index, set, lineX, miniPinTop);
        this.instance.ui.cursorGroup.appendChild(line2);
      }
      this.labelledIndices(minIndex, maxIndex).forEach((index) => {
        const lineX = this.pinX(set, index);
        const symbol = this.createPinSymbol(set, lineX, symbolCy);
        const label = this.createPinLabel(index, set, lineX, labelY);
        if (symbol) {
          this.instance.ui.cursorGroup.appendChild(symbol);
        }
        this.instance.ui.cursorGroup.appendChild(label);
      });
    }
    /**
     * Colour palette used when the style panel offers no explicit choice.
     * @type {string[]}
     */
    static SET_COLORS = ["#ff6b6b", "#2ecc71", "#f39c12", "#9b59b6", "#ffc93c", "#ff9ff3", "#45b7d1", "#e67e22"];
  }
  const panelTables$1 = /* @__PURE__ */ new WeakMap();
  function createSymbolSwatch(harmonicSet) {
    return createColorIndicator(harmonicSet.symbol, harmonicSet.color);
  }
  function createColorCellContent$1(harmonicSet) {
    const colorDiv = document.createElement("div");
    colorDiv.className = "gram-frame-harmonic-color";
    colorDiv.style.color = harmonicSet.color;
    colorDiv.appendChild(createSymbolSwatch(harmonicSet));
    return colorDiv;
  }
  function createSpacingCellContent(harmonicSet) {
    const wrapper = document.createElement("span");
    wrapper.textContent = `${harmonicSet.spacing.toFixed(2)} `;
    const unit = document.createElement("span");
    unit.className = "gram-frame-cell-unit";
    unit.textContent = "Hz";
    wrapper.appendChild(unit);
    return wrapper;
  }
  function formatRatio(harmonicSet, instance) {
    const cursor = instance.state.cursorPosition;
    if (cursor && cursor.freq > 0) {
      return (cursor.freq / harmonicSet.spacing).toFixed(3);
    }
    return "5.000";
  }
  function createHarmonicDeleteButton(harmonicSet) {
    const button2 = document.createElement("button");
    button2.className = "gram-frame-harmonic-delete";
    button2.setAttribute("data-harmonic-id", harmonicSet.id);
    button2.title = "Delete harmonic set";
    button2.textContent = "×";
    return button2;
  }
  function createHarmonicPanel(container, instance) {
    const table = createDiffingTable(container, {
      columns: [
        { label: "", width: "14%" },
        // "Hz" rides each value rather than the heading: the unit belongs to the
        // number, and the heading is what an analyst scans down the row of three
        // tables to find the right one.
        { label: "Spacing", width: "40%", cellClassName: "gram-frame-harmonic-spacing" },
        { label: "Ratio", width: "32%", cellClassName: "gram-frame-harmonic-ratio gram-frame-cell-numeric" },
        { label: "", width: "14%", cellClassName: "gram-frame-cell-action" }
      ],
      emptyMessage: "Drag on the gram to add a harmonic set",
      rowAttribute: "data-harmonic-id",
      rowClassName: "gram-frame-harmonic-row",
      rowKey: (harmonicSet) => harmonicSet.id,
      cells: (harmonicSet) => [
        createColorCellContent$1(harmonicSet),
        createSpacingCellContent(harmonicSet),
        formatRatio(harmonicSet, instance),
        createHarmonicDeleteButton(harmonicSet)
      ],
      deleteSelector: ".gram-frame-harmonic-delete",
      onSelect: (harmonicSetId, _harmonicSet, index) => instance.interaction.toggleSelection("harmonicSet", harmonicSetId, index),
      onDelete: (harmonicSetId) => instance.interaction.removeHarmonicSet(harmonicSetId),
      isSelected: (harmonicSetId) => instance.interaction.isFeatureSelected("harmonicSet", harmonicSetId)
    });
    const panel = (
      /** @type {HTMLElement} */
      table.element.parentElement
    );
    panelTables$1.set(panel, table);
    return panel;
  }
  function updateHarmonicPanelContent(panel, instance) {
    if (!panel) {
      return;
    }
    const table = panelTables$1.get(panel);
    if (!table) {
      return;
    }
    table.update(instance.state.harmonics.harmonicSets);
  }
  const MIN_MANUAL_SPACING = 0.1;
  function calculateVisibleTimePeriodCenter(state, instance) {
    const ZOOM_EPSILON = 1e-3;
    if (Math.abs(state.zoom.level - 1) < ZOOM_EPSILON) {
      return (state.config.timeMin + state.config.timeMax) / 2;
    }
    const visibleRange = calculateVisibleDataRange(instance.state, instance.ui.spectrogramImage);
    return (visibleRange.timeMin + visibleRange.timeMax) / 2;
  }
  function showManualHarmonicModal(state, addHarmonicSet, instance) {
    const overlay = document.createElement("div");
    overlay.className = "gram-frame-modal-overlay gram-frame-manual-harmonic-modal";
    const modal = document.createElement("div");
    modal.className = "gram-frame-modal";
    const header = document.createElement("div");
    header.className = "gram-frame-modal-header";
    const heading = document.createElement("h3");
    heading.textContent = "Add Manual Harmonics";
    header.appendChild(heading);
    const body = document.createElement("div");
    body.className = "gram-frame-modal-body";
    const inputGroup = document.createElement("div");
    inputGroup.className = "gram-frame-modal-input-group";
    const inputLabel = document.createElement("label");
    inputLabel.appendChild(document.createTextNode("Harmonic spacing (Hz):"));
    const spacingInput = document.createElement("input");
    spacingInput.type = "number";
    spacingInput.className = "gram-frame-harmonic-spacing-input";
    spacingInput.min = String(MIN_MANUAL_SPACING);
    spacingInput.step = String(MIN_MANUAL_SPACING);
    spacingInput.placeholder = "Enter spacing in Hz";
    inputLabel.appendChild(spacingInput);
    const errorDiv = document.createElement("div");
    errorDiv.className = "gram-frame-modal-error gram-frame-spacing-error";
    errorDiv.style.display = "none";
    errorDiv.textContent = `Please enter a number ≥ ${MIN_MANUAL_SPACING}`;
    inputGroup.appendChild(inputLabel);
    inputGroup.appendChild(errorDiv);
    body.appendChild(inputGroup);
    const footer = document.createElement("div");
    footer.className = "gram-frame-modal-footer";
    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "gram-frame-modal-btn gram-frame-modal-cancel";
    cancelButton.textContent = "Cancel";
    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "gram-frame-modal-btn gram-frame-modal-add";
    addButton.textContent = "Add";
    addButton.disabled = true;
    footer.appendChild(cancelButton);
    footer.appendChild(addButton);
    modal.appendChild(header);
    modal.appendChild(body);
    modal.appendChild(footer);
    overlay.appendChild(modal);
    const opener = (
      /** @type {HTMLElement|null} */
      document.activeElement
    );
    document.body.appendChild(overlay);
    const validateInput = () => {
      const value = parseFloat(spacingInput.value);
      const isValid = !isNaN(value) && value >= MIN_MANUAL_SPACING;
      if (spacingInput.value.trim() === "") {
        errorDiv.style.display = "none";
        addButton.disabled = true;
      } else if (!isValid) {
        errorDiv.style.display = "block";
        addButton.disabled = true;
      } else {
        errorDiv.style.display = "none";
        addButton.disabled = false;
      }
    };
    function closeModal() {
      document.removeEventListener("keydown", onDocumentKeydown, true);
      if (overlay.parentNode) {
        overlay.parentNode.removeChild(overlay);
      }
      if (opener && typeof opener.focus === "function" && opener.isConnected) {
        opener.focus();
      }
    }
    function addHarmonic() {
      const spacing = parseFloat(spacingInput.value);
      if (!isNaN(spacing) && spacing >= MIN_MANUAL_SPACING) {
        let anchorTime;
        if (state.cursorPosition) {
          anchorTime = state.cursorPosition.time;
        } else {
          anchorTime = calculateVisibleTimePeriodCenter(state, instance);
        }
        addHarmonicSet(anchorTime, spacing);
        closeModal();
      }
    }
    function onDocumentKeydown(e) {
      if (e.key === "Escape") {
        e.stopPropagation();
        e.preventDefault();
        closeModal();
      }
    }
    spacingInput.addEventListener("input", validateInput);
    spacingInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !addButton.disabled) {
        addHarmonic();
      }
    });
    document.addEventListener("keydown", onDocumentKeydown, true);
    cancelButton.addEventListener("click", closeModal);
    addButton.addEventListener("click", addHarmonic);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        closeModal();
      }
    });
    spacingInput.focus();
    return overlay;
  }
  class HarmonicsMode extends PinSetMode {
    /**
     * Initialize HarmonicsMode
     * @param {GramFrame} instance - GramFrame instance
     */
    constructor(instance) {
      super(instance, "harmonics");
    }
    /**
     * The harmonic sets, live.
     * @returns {PinSet[]} This mode's sets
     */
    get sets() {
      return this.instance.state.harmonics.harmonicSets;
    }
    /**
     * @returns {SelectedFeatureType} Selection type for a harmonic set
     */
    get selectionType() {
      return "harmonicSet";
    }
    /**
     * DOM naming for harmonic pins. Unchanged from before the pin machinery was
     * shared, so every existing CSS selector, test and helper keeps working.
     * @returns {PinSetClassNames} Class and attribute names
     */
    get pinNames() {
      return {
        idPrefix: "harmonic",
        lineClass: "gram-frame-harmonic-line",
        miniPinClass: "gram-frame-harmonic-mini-pin",
        labelClass: "gram-frame-harmonic-number",
        setIdAttribute: "data-harmonic-set-id",
        indexAttribute: "data-harmonic-number"
      };
    }
    /**
     * Frequency of the nth harmonic: the origin is 0 Hz, so it is a plain
     * multiple of the spacing.
     * @param {PinSet} set - Harmonic set
     * @param {number} index - Harmonic number
     * @returns {number} Frequency in Hz
     */
    freqForIndex(set, index) {
      return index * set.spacing;
    }
    /**
     * Get the inclusive harmonic-number range of a set that falls within the
     * currently visible frequency span.
     *
     * Harmonic numbers start at 1: there is no zeroth harmonic, and a set never
     * draws below its own origin.
     * @param {PinSet} set - Harmonic set
     * @returns {{minIndex: number, maxIndex: number}} Inclusive harmonic range
     */
    visibleIndexRange(set) {
      const { freqMin, freqMax } = this.visibleFrequencySpan();
      return {
        minIndex: Math.max(1, Math.ceil(freqMin / set.spacing)),
        maxIndex: Math.floor(freqMax / set.spacing)
      };
    }
    /**
     * Find which harmonic number a frequency is nearest.
     * @param {PinSet} set - Harmonic set
     * @param {number} freq - Probe frequency
     * @returns {number} Harmonic number (1, 2, 3, ...)
     */
    nearestIndex(set, freq) {
      return Math.max(1, Math.round(freq / set.spacing));
    }
    /**
     * The harmonics table's Ratio column is the cursor frequency over the set's
     * spacing, so it is stale the moment the pointer moves.
     * @returns {boolean} True — this table follows the cursor
     */
    get panelTracksCursor() {
      return true;
    }
    /**
     * @param {number} index - Harmonic number
     * @returns {string} The harmonic number, as drawn
     */
    labelTextFor(index) {
      return String(index);
    }
    /**
     * Mint a new harmonic set at the mousedown position.
     *
     * The initial spacing places the cursor on a sensible harmonic — the 10th
     * when the frequency axis starts above zero, the 5th when it starts at zero —
     * which is what keeps the first drawn set legible.
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     * @returns {DragTarget|null} A create-kind target, or null if a set cannot be made
     */
    createSetTarget(dataCoords) {
      const { freqMin } = this.instance.state.config;
      const clickedIndex = freqMin > 0 ? 10 : 5;
      const initialSpacing = Math.max(dataCoords.freq / clickedIndex, MIN_PIN_SPACING);
      const harmonicSet = this.addHarmonicSet(dataCoords.time, initialSpacing);
      if (!harmonicSet) {
        return null;
      }
      return {
        kind: "create",
        id: harmonicSet.id,
        type: "harmonicSet",
        position: dataCoords,
        data: {
          set: harmonicSet,
          clickedIndex,
          originalAnchorTime: dataCoords.time
        }
      };
    }
    /**
     * Dragging a harmonic keeps that harmonic under the cursor, which is the same
     * as scaling the spacing.
     * @param {PinSet} _set - Harmonic set being dragged
     * @param {number} clickedIndex - Harmonic number the drag grabbed
     * @param {DataCoordinates} currentPos - Current pointer position
     * @returns {Partial<PinSet>} Spacing update
     */
    freqUpdatesForDrag(_set, clickedIndex, currentPos) {
      const spacing = Math.max(currentPos.freq / (clickedIndex || 1), MIN_PIN_SPACING);
      return { spacing };
    }
    /**
     * Get guidance content for harmonics mode
     * @returns {Object} Structured guidance content
     */
    getGuidanceText() {
      return {
        items: [
          { trigger: "Click & drag", outcome: "to generate harmonic lines" },
          { trigger: "Drag", outcome: "existing harmonic lines to adjust spacing intervals" },
          { trigger: "[+ Manual]", outcome: "to add harmonic lines manually" },
          { trigger: "Row + ← →", outcome: "to nudge (Shift for larger steps)" }
        ]
      };
    }
    /**
     * Create UI elements for harmonics mode
     * @param {HTMLElement} harmonicsContainer - Persistent container for harmonics table
     */
    createUI(harmonicsContainer) {
      this.uiElements = {};
      this.uiElements.harmonicsContainer = harmonicsContainer;
      const buttonContainer = harmonicsContainer.querySelector(".gram-frame-harmonics-button-container");
      if (buttonContainer && buttonContainer.querySelector(".gram-frame-manual-button")) {
        this.uiElements.manualButton = /** @type {HTMLElement|null} */
        buttonContainer.querySelector(".gram-frame-manual-button");
        this.uiElements.harmonicPanel = /** @type {HTMLElement|null} */
        harmonicsContainer.querySelector(".gram-frame-harmonic-panel");
        this.instance.ui.harmonicPanel = this.uiElements.harmonicPanel;
        return;
      }
      this.uiElements.manualButton = this.createManualButton();
      if (buttonContainer) {
        buttonContainer.appendChild(this.uiElements.manualButton);
      }
      this.uiElements.harmonicPanel = createHarmonicPanel(harmonicsContainer, this.instance);
      this.instance.ui.harmonicPanel = this.uiElements.harmonicPanel;
      this.instance.ui.colorPicker = this.instance.ui.colorPicker || null;
      this.updatePanel();
    }
    /**
     * Update LED displays for harmonics mode
     * @param {CursorPosition} _coords - Current cursor coordinates
     */
    updateLEDs(_coords) {
      this.updateModeSpecificLEDs();
    }
    /**
     * Update mode-specific LED values and labels based on current state
     */
    updateModeSpecificLEDs() {
      this.updatePanel();
    }
    /**
     * Reset harmonics-specific state
     */
    resetState() {
      this.instance.state.harmonics.baseFrequency = null;
      this.instance.state.harmonics.harmonicData = [];
    }
    /**
     * Clean up harmonics-specific state when switching away from harmonics mode
     */
    cleanup() {
      this.instance.state.harmonics.baseFrequency = null;
      this.instance.state.harmonics.harmonicData = [];
    }
    /**
     * Destroy mode-specific UI elements when leaving this mode
     */
    destroyUI() {
    }
    /**
     * Add a new harmonic set
     * @param {number} anchorTime - Time position in seconds
     * @param {number} spacing - Frequency spacing in Hz
     * @returns {PinSet} The created harmonic set
     */
    addHarmonicSet(anchorTime, spacing) {
      return this.addSet({ anchorTime, spacing });
    }
    /**
     * Update an existing harmonic set
     * @param {string} id - Harmonic set ID
     * @param {Partial<PinSet>} updates - Properties to update
     */
    updateHarmonicSet(id, updates) {
      this.updateSet(id, updates);
    }
    /**
     * Remove a harmonic set
     * @param {string} id - Harmonic set ID
     */
    removeHarmonicSet(id) {
      this.removeSet(id);
    }
    /**
     * Find the harmonic set whose drawn geometry contains the given position.
     * @param {DataCoordinates} position - Probe position {freq, time}
     * @returns {PinSet|null} The harmonic set if found, null otherwise
     */
    findHarmonicSetAt(position) {
      return this.findSetAt(position);
    }
    /**
     * Update harmonic management panel
     */
    updatePanel() {
      if (this.instance.ui.harmonicPanel) {
        updateHarmonicPanelContent(this.instance.ui.harmonicPanel, this.instance);
      }
    }
    /**
     * Create manual harmonic button
     * @returns {HTMLElement} The manual button element
     */
    createManualButton() {
      const button2 = document.createElement("button");
      button2.className = "gram-frame-manual-button";
      button2.textContent = "+ Manual";
      button2.title = "Manually add a set of harmonics at a specific spacing";
      button2.addEventListener("click", () => {
        this.showManualHarmonicModal();
      });
      return button2;
    }
    /**
     * Show manual harmonic modal dialog
     */
    showManualHarmonicModal() {
      showManualHarmonicModal(this.instance.state, this.addHarmonicSet.bind(this), this.instance);
    }
    /**
     * Re-render this mode's persistent panel from current state.
     *
     * The `PanelOwner` capability. `MainUI` used to reach in by name, resolve the
     * panel element on this mode's behalf, and call the panel update through an
     * `any` cast. Resolving the panel reference belongs here — it is this mode's
     * own UI element — so it is absorbed rather than left outside
     * (spec 167, FR-006, AS-4.2).
     */
    refreshPanel() {
      if (!this.instance.ui.harmonicPanel && this.instance.ui.harmonicsContainer) {
        const existingPanel = (
          /** @type {HTMLElement|null} */
          this.instance.ui.harmonicsContainer.querySelector(".gram-frame-harmonic-panel")
        );
        if (existingPanel) {
          this.instance.ui.harmonicPanel = existingPanel;
        }
      }
      this.updatePanel();
    }
    /**
     * Get initial state for harmonics mode
     * @returns {HarmonicsInitialState} Harmonics-specific initial state
     */
    static getInitialState() {
      return {
        harmonics: {
          baseFrequency: null,
          harmonicData: [],
          harmonicSets: []
        }
      };
    }
  }
  const panelTables = /* @__PURE__ */ new WeakMap();
  function createColorCellContent(sidebandSet) {
    const colorDiv = document.createElement("div");
    colorDiv.className = "gram-frame-sideband-color";
    colorDiv.style.color = sidebandSet.color;
    colorDiv.appendChild(createColorIndicator(sidebandSet.symbol, sidebandSet.color));
    return colorDiv;
  }
  function createSidebandDeleteButton(sidebandSet) {
    const button2 = document.createElement("button");
    button2.className = "gram-frame-sideband-delete";
    button2.setAttribute("data-sideband-id", sidebandSet.id);
    button2.title = "Delete sideband set";
    button2.textContent = "×";
    return button2;
  }
  function createSidebandPanel(container, instance) {
    const table = createDiffingTable(container, {
      columns: [
        { label: "", width: "14%" },
        { label: "Freq", width: "36%", cellClassName: "gram-frame-sideband-freq gram-frame-cell-numeric" },
        { label: "Spacing", width: "36%", cellClassName: "gram-frame-sideband-spacing gram-frame-cell-numeric" },
        { label: "", width: "14%", cellClassName: "gram-frame-cell-action" }
      ],
      emptyMessage: "Click to set the sideband origin",
      rowAttribute: "data-sideband-id",
      rowClassName: "gram-frame-sideband-row",
      rowKey: (sidebandSet) => sidebandSet.id,
      cells: (sidebandSet) => [
        createColorCellContent(sidebandSet),
        sidebandSet.fundamentalFreq.toFixed(2),
        sidebandSet.spacing.toFixed(2),
        createSidebandDeleteButton(sidebandSet)
      ],
      deleteSelector: ".gram-frame-sideband-delete",
      onSelect: (sidebandSetId, _sidebandSet, index) => instance.interaction.toggleSelection("sidebandSet", sidebandSetId, index),
      onDelete: (sidebandSetId) => instance.interaction.removeSidebandSet(sidebandSetId),
      isSelected: (sidebandSetId) => instance.interaction.isFeatureSelected("sidebandSet", sidebandSetId)
    });
    const panel = (
      /** @type {HTMLElement} */
      table.element.parentElement
    );
    panel.classList.add("gram-frame-sideband-panel");
    panelTables.set(panel, table);
    return panel;
  }
  function updateSidebandPanelContent(panel, instance) {
    if (!panel) {
      return;
    }
    const table = panelTables.get(panel);
    if (!table) {
      return;
    }
    table.update(instance.state.sidebands.sidebandSets);
  }
  class SidebandMode extends PinSetMode {
    /**
     * Number of sidebands a newly placed set spreads across the frequency axis.
     *
     * The seed spacing is the axis span divided by this, so a set dropped in the
     * middle of the gram shows about this many members — an equal count each side
     * when the fundamental is central, and more on the roomier side when it is
     * not. It is only a starting point: the analyst drags a sideband onto the
     * data immediately afterwards, which is what actually sets the spacing.
     * @type {number}
     */
    static INITIAL_SIDEBAND_COUNT = 8;
    /**
     * Initialize SidebandMode
     * @param {GramFrame} instance - GramFrame instance
     */
    constructor(instance) {
      super(instance, "sideband");
    }
    /**
     * The sideband sets, live.
     * @returns {PinSet[]} This mode's sets
     */
    get sets() {
      return this.instance.state.sidebands.sidebandSets;
    }
    /**
     * @returns {SelectedFeatureType} Selection type for a sideband set
     */
    get selectionType() {
      return "sidebandSet";
    }
    /**
     * DOM naming for sideband pins: its own stem, so a selector, a cleanup pass
     * or a test can never confuse a sideband with a harmonic.
     * @returns {PinSetClassNames} Class and attribute names
     */
    get pinNames() {
      return {
        idPrefix: "sideband",
        lineClass: "gram-frame-sideband-line",
        miniPinClass: "gram-frame-sideband-mini-pin",
        labelClass: "gram-frame-sideband-number",
        setIdAttribute: "data-sideband-set-id",
        indexAttribute: "data-sideband-index"
      };
    }
    /**
     * Frequency of sideband `index`, counted out from the fundamental. Negative
     * indices fall below it, positive ones above; index 0 is the fundamental.
     * @param {PinSet} set - Sideband set
     * @param {number} index - Sideband index
     * @returns {number} Frequency in Hz
     */
    freqForIndex(set, index) {
      return this.fundamentalOf(set) + index * set.spacing;
    }
    /**
     * The inclusive sideband-index range within the currently visible frequency
     * span. Unlike a harmonic set this is not clamped at zero: sidebands below the
     * fundamental are as real as those above it.
     * @param {PinSet} set - Sideband set
     * @returns {{minIndex: number, maxIndex: number}} Inclusive index range
     */
    visibleIndexRange(set) {
      const { freqMin, freqMax } = this.visibleFrequencySpan();
      const fundamental = this.fundamentalOf(set);
      return {
        minIndex: Math.ceil((freqMin - fundamental) / set.spacing),
        maxIndex: Math.floor((freqMax - fundamental) / set.spacing)
      };
    }
    /**
     * Which sideband a probe frequency is nearest.
     * @param {PinSet} set - Sideband set
     * @param {number} freq - Probe frequency
     * @returns {number} Nearest sideband index
     */
    nearestIndex(set, freq) {
      return Math.round((freq - this.fundamentalOf(set)) / set.spacing);
    }
    /**
     * Label a sideband by its signed offset from the fundamental, so the origin
     * is identifiable at a glance: `0` on the fundamental, `+1`/`-1` either side.
     * @param {number} index - Sideband index
     * @returns {string} Label text
     */
    labelTextFor(index) {
      return index > 0 ? `+${index}` : String(index);
    }
    /**
     * The set's fundamental, tolerating a record that somehow lacks one.
     * @param {PinSet} set - Sideband set
     * @returns {number} Fundamental frequency in Hz
     */
    fundamentalOf(set) {
      return set.fundamentalFreq || 0;
    }
    /**
     * Mint a new sideband set at the mousedown position.
     *
     * The click sets the fundamental. The seed spacing spreads roughly
     * {@link SidebandMode.INITIAL_SIDEBAND_COUNT} members across the frequency
     * axis, which puts an equal number either side of a centred fundamental and
     * more on the roomier side of an off-centre one — exactly as the analyst
     * placed it. The drag that follows then sets the real spacing.
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     * @returns {DragTarget|null} A create-kind target, or null if a set cannot be made
     */
    createSetTarget(dataCoords) {
      const { freqMin, freqMax } = dataFrequencyRange(this.getViewport());
      const span = Math.abs(freqMax - freqMin);
      const initialSpacing = Math.max(span / SidebandMode.INITIAL_SIDEBAND_COUNT, MIN_PIN_SPACING);
      const sidebandSet = this.addSidebandSet(dataCoords.time, dataCoords.freq, initialSpacing);
      if (!sidebandSet) {
        return null;
      }
      return {
        kind: "create",
        id: sidebandSet.id,
        type: "sidebandSet",
        position: dataCoords,
        data: {
          set: sidebandSet,
          // The click landed on the fundamental, so the drag that follows moves
          // the origin — which is how the analyst places it precisely.
          clickedIndex: 0,
          originalAnchorTime: dataCoords.time
        }
      };
    }
    /**
     * What a horizontal drag means for a sideband set.
     *
     * Grabbing the fundamental moves the whole set along the frequency axis;
     * grabbing any other sideband holds it under the cursor, which sets the
     * spacing. Dragging a sideband past the fundamental would invert the spacing,
     * so it is floored at the shared minimum rather than allowed to go negative.
     * @param {PinSet} set - The set being dragged
     * @param {number} clickedIndex - Sideband index the drag grabbed
     * @param {DataCoordinates} currentPos - Current pointer position
     * @returns {Partial<PinSet>} Updates to apply
     */
    freqUpdatesForDrag(set, clickedIndex, currentPos) {
      if (clickedIndex === 0) {
        const { freqMin, freqMax } = dataFrequencyRange(this.getViewport());
        const lower = Math.min(freqMin, freqMax);
        const upper = Math.max(freqMin, freqMax);
        return { fundamentalFreq: Math.max(lower, Math.min(upper, currentPos.freq)) };
      }
      const spacing = (currentPos.freq - this.fundamentalOf(set)) / clickedIndex;
      return { spacing: Math.max(spacing, MIN_PIN_SPACING) };
    }
    /**
     * Add a new sideband set
     * @param {number} anchorTime - Time position in seconds
     * @param {number} fundamentalFreq - Fundamental frequency in Hz
     * @param {number} spacing - Frequency spacing between adjacent sidebands in Hz
     * @returns {PinSet} The created sideband set
     */
    addSidebandSet(anchorTime, fundamentalFreq, spacing) {
      return this.addSet({ anchorTime, fundamentalFreq, spacing });
    }
    /**
     * Update an existing sideband set
     * @param {string} id - Sideband set ID
     * @param {Partial<PinSet>} updates - Properties to update
     */
    updateSidebandSet(id, updates) {
      this.updateSet(id, updates);
    }
    /**
     * Remove a sideband set
     * @param {string} id - Sideband set ID
     */
    removeSidebandSet(id) {
      this.removeSet(id);
    }
    /**
     * Find the sideband set whose drawn geometry contains the given position.
     * @param {DataCoordinates} position - Probe position {freq, time}
     * @returns {PinSet|null} The sideband set if found, null otherwise
     */
    findSidebandSetAt(position) {
      return this.findSetAt(position);
    }
    /**
     * Get guidance content for sidebands mode
     * @returns {Object} Structured guidance content
     */
    getGuidanceText() {
      return {
        items: [
          { trigger: "Click & drag", outcome: "to place a sideband set at that frequency" },
          { trigger: "Drag the 0 line", outcome: "to move the fundamental" },
          { trigger: "Drag any other line", outcome: "to adjust sideband spacing" },
          { trigger: "Row + ← →", outcome: "to nudge (Shift for larger steps)" }
        ]
      };
    }
    /**
     * Create UI elements for sidebands mode
     * @param {HTMLElement} sidebandsContainer - Persistent container for the sidebands table
     */
    createUI(sidebandsContainer) {
      this.uiElements = {};
      this.uiElements.sidebandsContainer = sidebandsContainer;
      const existingPanel = (
        /** @type {HTMLElement|null} */
        sidebandsContainer.querySelector(".gram-frame-sideband-panel")
      );
      this.uiElements.sidebandPanel = existingPanel || createSidebandPanel(sidebandsContainer, this.instance);
      this.instance.ui.sidebandPanel = this.uiElements.sidebandPanel;
      this.updatePanel();
    }
    /**
     * Destroy mode-specific UI elements when leaving this mode.
     *
     * The panel and its container are persistent — the sidebands table stays
     * visible in every mode, as the markers and harmonics tables do — so this
     * deliberately does NOT call `super.destroyUI()`.
     */
    destroyUI() {
    }
    /**
     * Update the sidebands table
     */
    updatePanel() {
      if (this.instance.ui.sidebandPanel) {
        updateSidebandPanelContent(this.instance.ui.sidebandPanel, this.instance);
      }
    }
    /**
     * Re-render this mode's persistent panel from current state.
     *
     * The `PanelOwner` capability.
     * @see {@link module:modes/capabilities}
     */
    refreshPanel() {
      if (!this.instance.ui.sidebandPanel && this.instance.ui.sidebandsContainer) {
        const existingPanel = (
          /** @type {HTMLElement|null} */
          this.instance.ui.sidebandsContainer.querySelector(".gram-frame-sideband-panel")
        );
        if (existingPanel) {
          this.instance.ui.sidebandPanel = existingPanel;
        }
      }
      this.updatePanel();
    }
    /**
     * Get initial state for sidebands mode
     * @returns {SidebandsInitialState} Sidebands-specific initial state
     */
    static getInitialState() {
      return {
        sidebands: {
          sidebandSets: []
        }
      };
    }
  }
  const MS_TO_KNOTS = 1.94384;
  const DEFAULT_SPEED_OF_SOUND = 1500;
  function calculateMidpoint(fPlus, fMinus) {
    return {
      time: (fPlus.time + fMinus.time) / 2,
      freq: (fPlus.freq + fMinus.freq) / 2
    };
  }
  function calculateDopplerSpeed(fPlus, fMinus, fZero = null, speedOfSound = DEFAULT_SPEED_OF_SOUND) {
    const f0 = fZero ? fZero.freq : calculateMidpoint(fPlus, fMinus).freq;
    const deltaF = (fPlus.freq - fMinus.freq) / 2;
    const speed = speedOfSound / f0 * deltaF;
    return Math.abs(speed);
  }
  const DopplerDraggedMarker = {
    fPlus: "fPlus",
    fMinus: "fMinus",
    fZero: "fZero"
  };
  class DopplerMode extends BaseMode {
    /**
     * Initialize DopplerMode with drag handler
     * @param {GramFrame} instance - GramFrame instance
     */
    constructor(instance) {
      super(instance);
      this.dragHandler = new BaseDragHandler(instance, {
        // A feature drag always carries a data position. Only the pan drag passes
        // null, and it runs on its own handler in `core/events.js`.
        resolveTarget: (position) => this.resolveDopplerDrag(
          /** @type {DataCoordinates} */
          position
        ),
        // Hover only ever *finds* — resolveDopplerDrag seeds f+ when no markers
        // exist, which is right for a mousedown and wrong for a hover.
        resolveHoverTarget: (position) => this.findDopplerMarkerAtPosition(
          /** @type {DataCoordinates} */
          position
        ),
        onDragStart: (target, position) => this.onMarkerDragStart(
          target,
          /** @type {DataCoordinates} */
          position
        ),
        onDragMove: (target, currentPos, startPos) => this.onMarkerDragUpdate(
          target,
          /** @type {DataCoordinates} */
          currentPos,
          /** @type {DataCoordinates} */
          startPos
        ),
        onDragEnd: (target, position) => this.onMarkerDragEnd(target, position),
        onDragCancel: (target) => this.onMarkerDragCancel(target),
        updateCursor: (style) => this.updateCursorStyle(style)
      }, "doppler");
    }
    /**
     * Find doppler marker at given position
     * Returns a drag target object compatible with BaseDragHandler
     * @param {DataCoordinates} position - Position to check
     * @returns {DragTarget|null} Drag target if found, null otherwise
     */
    findDopplerMarkerAtPosition(position) {
      const doppler = this.instance.state.doppler;
      if (!doppler) return null;
      const tolerance = getUniformTolerance(this.getViewport(), this.instance.ui.spectrogramImage);
      const targets = [];
      for (const markerType of [
        DopplerDraggedMarker.fPlus,
        DopplerDraggedMarker.fMinus,
        DopplerDraggedMarker.fZero
      ]) {
        const markerPosition = doppler[markerType];
        if (!markerPosition) continue;
        if (!isWithinDataTolerance(position, markerPosition, tolerance)) continue;
        targets.push({
          kind: "move",
          id: markerType,
          type: "dopplerMarker",
          position: markerPosition,
          data: { markerType }
        });
      }
      return findClosestTarget(position, targets, tolerance) || targets[0] || null;
    }
    /**
     * Start dragging a doppler marker
     * @param {DragTarget} target - Drag target with id and type
     * @param {DataCoordinates} _position - Start position (unused)
     */
    onMarkerDragStart(target, _position) {
    }
    /**
     * Update doppler marker position during drag
     * @param {DragTarget} target - Drag target
     * @param {DataCoordinates} currentPos - Current position
     * @param {DataCoordinates} _startPos - Start position (unused)
     */
    onMarkerDragUpdate(target, currentPos, _startPos) {
      const doppler = this.instance.state.doppler;
      if (target.kind === "place") {
        this.handlePreviewDrag(currentPos, doppler);
        return;
      }
      this.handleMarkerDrag(currentPos, doppler, target.id);
    }
    /**
     * End dragging a doppler marker
     * @param {DragTarget} target - Drag target
     * @param {DataCoordinates|null} _position - End position (unused)
     */
    onMarkerDragEnd(target, _position) {
      if (target && target.kind === "place") {
        this.completeMarkerPlacement();
      }
    }
    /**
     * Cancel a doppler drag without applying it.
     *
     * Cancel and end used to share one callback, so a cancelled placement —
     * mode switch or Escape mid-gesture — *committed* the half-placed f⁺/f⁻
     * curve the user thought was discarded (BH-9). A cancelled placement now
     * discards the markers it seeded; a cancelled move leaves the marker at its
     * last position, like the other modes.
     * @param {DragTarget} target - Drag target from the engine
     */
    onMarkerDragCancel(target) {
      if (target && target.kind === "place") {
        const doppler = this.instance.state.doppler;
        doppler.fPlus = null;
        doppler.fMinus = null;
        doppler.fZero = null;
        doppler.speed = null;
        doppler.tempFirst = null;
        doppler.previewEnd = null;
        this.updateSpeedLED();
        this.renderDopplerFeatures();
        dispatch(this.instance, { frame: true });
      }
    }
    /**
     * Resolve what a mousedown in doppler mode starts: moving one of the placed
     * markers, or — with nothing placed yet — laying down f+ and dragging out f-.
     * @param {DataCoordinates} position - Position of the mousedown
     * @returns {DragTarget|null} A move- or place-kind target
     */
    resolveDopplerDrag(position) {
      const doppler = this.instance.state.doppler;
      if (doppler.fPlus || doppler.fMinus || doppler.fZero) {
        return this.findDopplerMarkerAtPosition(position);
      }
      return this.startMarkerPlacement(position);
    }
    /**
     * Seed f+ at the mousedown position and return a `place`-kind target, so the
     * rest of the placement is an ordinary drag with f- following the pointer.
     *
     * `tempFirst` and `previewEnd` stay on state.doppler: they are placement
     * geometry the renderer needs, not drag bookkeeping (data-model.md §2).
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     * @returns {DragTarget} A place-kind target
     */
    startMarkerPlacement(dataCoords) {
      const doppler = this.instance.state.doppler;
      doppler.fPlus = { time: dataCoords.time, freq: dataCoords.freq };
      doppler.tempFirst = doppler.fPlus;
      doppler.previewEnd = { time: dataCoords.time, freq: dataCoords.freq };
      this.renderDopplerFeatures();
      return {
        kind: "place",
        id: DopplerDraggedMarker.fMinus,
        type: "dopplerMarker",
        position: dataCoords,
        data: { markerType: DopplerDraggedMarker.fMinus }
      };
    }
    /**
     * Finalise a placement drag: order the markers, derive f₀, and clear the
     * placement geometry.
     */
    completeMarkerPlacement() {
      const doppler = this.instance.state.doppler;
      if (!doppler.tempFirst || !doppler.fPlus || !doppler.fMinus) {
        doppler.tempFirst = null;
        doppler.previewEnd = null;
        return;
      }
      if (doppler.fPlus.time <= doppler.fMinus.time) {
        const temp = doppler.fPlus;
        doppler.fPlus = doppler.fMinus;
        doppler.fMinus = temp;
      }
      doppler.fZero = this.calculateMidpoint(doppler.fPlus, doppler.fMinus);
      if (!doppler.color) {
        doppler.color = this.instance.state.selectedColor || "#ff0000";
      }
      doppler.tempFirst = null;
      doppler.previewEnd = null;
      markAnnotationsChanged(this.instance);
      this.calculateAndUpdateDopplerSpeed();
      this.renderDopplerFeatures();
    }
    /**
     * Get guidance content for doppler mode
     * @returns {Object} Structured guidance content
     */
    getGuidanceText() {
      return {
        items: [
          { trigger: "Click & drag", outcome: "to place f+ and f− in one gesture; the curve previews during the drag" },
          { trigger: "Drag f+ or f−", outcome: "to adjust; f₀ can be dragged independently" },
          { trigger: "f₀ marker", outcome: "is placed automatically at the midpoint" },
          { trigger: "Right-click", outcome: "to reset all doppler markers" }
        ]
      };
    }
    /**
     * Handle preview drag when placing markers
     * @param {DataCoordinates} dataCoords - Data coordinates
     * @param {DopplerState} doppler - Doppler state
     */
    handlePreviewDrag(dataCoords, doppler) {
      doppler.fMinus = {
        time: dataCoords.time,
        freq: dataCoords.freq
      };
      doppler.fZero = this.calculateMidpoint(
        /** @type {DataCoordinates} */
        doppler.fPlus,
        doppler.fMinus
      );
      doppler.previewEnd = doppler.fMinus;
      this.renderDopplerFeatures();
    }
    /**
     * Handle marker dragging
     * @param {DataCoordinates} dataCoords - Data coordinates
     * @param {DopplerState} doppler - Doppler state
     * @param {string|null} markerType - Which marker is being dragged
     */
    handleMarkerDrag(dataCoords, doppler, markerType) {
      const newPoint = {
        time: dataCoords.time,
        freq: dataCoords.freq
      };
      if (markerType === DopplerDraggedMarker.fPlus) {
        doppler.fPlus = newPoint;
      } else if (markerType === DopplerDraggedMarker.fMinus) {
        doppler.fMinus = newPoint;
      } else if (markerType === DopplerDraggedMarker.fZero) {
        doppler.fZero = newPoint;
      }
      markAnnotationsChanged(this.instance);
      this.calculateAndUpdateDopplerSpeed();
      this.renderDopplerFeatures();
      dispatch(this.instance, { frame: true });
    }
    /**
     * Handle mouse move events in doppler mode
     * @param {MouseEvent} _event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseMove(_event, dataCoords) {
      const doppler = this.instance.state.doppler;
      if (this.dragHandler.isDragging()) {
        this.dragHandler.handleMouseMove(dataCoords);
      } else if (doppler.fPlus || doppler.fMinus || doppler.fZero) {
        this.dragHandler.updateCursorForHover(dataCoords);
      }
    }
    /**
     * Handle mouse down events in doppler mode
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseDown(event, dataCoords) {
      if (this.dragHandler.startDrag(dataCoords, event)) {
        dispatch(this.instance, { frame: true });
      }
    }
    /**
     * Handle mouse up events in doppler mode
     * @param {MouseEvent} _event - Mouse event (unused)
     * @param {DataCoordinates} dataCoords - Data coordinates {freq, time}
     */
    handleMouseUp(_event, dataCoords) {
      if (this.dragHandler.isDragging()) {
        this.dragHandler.endDrag(dataCoords);
        dispatch(this.instance, { frame: true });
      }
    }
    /**
     * Create UI elements for doppler mode
     * @param {HTMLElement} _leftColumn - Container for UI elements (unused)
     */
    createUI(_leftColumn) {
      this.uiElements = {};
      this.instance.ui.speedLED = this.instance.ui.speedLED || null;
    }
    /**
     * Update LED displays for doppler mode
     * @param {CursorPosition} _coords - Current cursor coordinates
     */
    updateLEDs(_coords) {
      this.updateModeSpecificLEDs();
    }
    /**
     * Update mode-specific LED values based on current state
     */
    updateModeSpecificLEDs() {
    }
    /**
     * Reset doppler-specific state
     */
    resetState() {
      const doppler = this.instance.state.doppler;
      doppler.fPlus = null;
      doppler.fMinus = null;
      doppler.fZero = null;
      doppler.speed = null;
      doppler.color = null;
      doppler.tempFirst = null;
      doppler.previewEnd = null;
      this.dragHandler.reset();
      recordDopplerDeletion(this.instance);
      markAnnotationsChanged(this.instance);
      dispatch(this.instance, { frame: true });
    }
    /**
     * Clean up doppler-specific state when switching away from doppler mode
     */
    cleanup() {
      const doppler = this.instance.state.doppler;
      doppler.tempFirst = null;
      doppler.previewEnd = null;
      this.dragHandler.reset();
    }
    /**
     * Deactivate doppler mode - hide speed LED
     */
    deactivate() {
    }
    /**
     * Calculate and update Doppler speed
     */
    calculateAndUpdateDopplerSpeed() {
      const doppler = this.instance.state.doppler;
      if (doppler.fPlus && doppler.fMinus && doppler.fZero) {
        const speed = calculateDopplerSpeed(doppler.fPlus, doppler.fMinus, doppler.fZero);
        this.instance.state.doppler.speed = Number.isFinite(speed) ? speed : null;
        this.updateSpeedLED();
        updateLEDDisplays(this.instance, this.instance.state);
        dispatch(this.instance, { frame: true });
      }
    }
    /**
     * Get initial state for doppler mode
     * @returns {DopplerInitialState} Doppler-specific initial state
     */
    static getInitialState() {
      return {
        doppler: {
          fPlus: null,
          // DataCoordinates: { time, frequency }
          fMinus: null,
          // DataCoordinates: { time, frequency }
          fZero: null,
          // DataCoordinates: { time, frequency }
          speed: null,
          // calculated speed in m/s
          color: null,
          // color used for this doppler curve
          // Placement geometry the renderer needs. Drag bookkeeping lives on
          // state.drag, owned by the drag engine.
          tempFirst: null,
          // temporary storage for first marker during placement
          previewEnd: null
          // end point for preview drag
        }
      };
    }
    /**
     * Update the speed LED display with current speed value
     */
    updateSpeedLED() {
      const speed = this.instance.state.doppler.speed;
      if (this.instance.ui.speedLED && speed !== null && Number.isFinite(speed)) {
        const speedInKnots = speed * MS_TO_KNOTS;
        setLEDValue(this.instance.ui.speedLED, speedInKnots.toFixed(1));
      } else if (this.instance.ui.speedLED) {
        setLEDValue(this.instance.ui.speedLED, "0.0");
      }
    }
    /**
     * Calculate midpoint between two markers
     * @param {DataCoordinates} fPlus - f+ marker
     * @param {DataCoordinates} fMinus - f- marker
     * @returns {DataCoordinates} Midpoint coordinates
     */
    calculateMidpoint(fPlus, fMinus) {
      return calculateMidpoint(fPlus, fMinus);
    }
    /**
     * Handle context menu (right-click) events in doppler mode
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} _dataCoords - Data coordinates {freq, time} (unused)
     */
    handleContextMenu(event, _dataCoords) {
      event.preventDefault();
      this.resetState();
      this.updateSpeedLED();
      this.renderDopplerFeatures();
      this.updateCursorStyle(IDLE_CURSOR);
    }
    /**
     * Render all doppler features (markers and curves)
     */
    renderDopplerFeatures() {
      if (!this.instance.ui.cursorGroup) return;
      const existingFeatures = this.instance.ui.cursorGroup.querySelectorAll(".doppler-feature, .gram-frame-doppler-preview, .gram-frame-doppler-curve, .gram-frame-doppler-extension, .gram-frame-doppler-fPlus, .gram-frame-doppler-fMinus, .gram-frame-doppler-crosshair");
      existingFeatures.forEach((element) => element.remove());
      const doppler = this.instance.state.doppler;
      if (doppler.fPlus && doppler.fMinus && doppler.fZero) {
        this.renderMarkers();
        this.renderDopplerCurve();
        if (doppler.tempFirst) {
          const elements = this.instance.ui.cursorGroup.querySelectorAll(".gram-frame-doppler-curve, .gram-frame-doppler-extension");
          elements.forEach((element) => {
            element.setAttribute("opacity", "0.8");
            element.setAttribute("stroke-dasharray", "5,5");
          });
        }
      }
    }
    /**
     * Render doppler markers (f+, f-, f₀) with zoom awareness
     */
    renderMarkers() {
      const doppler = this.instance.state.doppler;
      const color = doppler.color || this.instance.state.selectedColor || "#ff0000";
      const isInDopplerMode = this.instance.state.mode === "doppler";
      const pointerEvents = isInDopplerMode ? "auto" : "none";
      if (doppler.fPlus) {
        const fPlusSVG = dataToSVG(doppler.fPlus, this.getViewport(), this.instance.ui.spectrogramImage);
        const fPlusMarker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        fPlusMarker.setAttribute("class", "gram-frame-doppler-fPlus");
        fPlusMarker.setAttribute("cx", fPlusSVG.x.toString());
        fPlusMarker.setAttribute("cy", fPlusSVG.y.toString());
        fPlusMarker.setAttribute("r", "4");
        fPlusMarker.setAttribute("fill", color);
        fPlusMarker.setAttribute("stroke", "#ffffff");
        fPlusMarker.setAttribute("stroke-width", "1");
        fPlusMarker.setAttribute("pointer-events", pointerEvents);
        this.instance.ui.cursorGroup.appendChild(fPlusMarker);
      }
      if (doppler.fMinus) {
        const fMinusSVG = dataToSVG(doppler.fMinus, this.getViewport(), this.instance.ui.spectrogramImage);
        const fMinusMarker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        fMinusMarker.setAttribute("class", "gram-frame-doppler-fMinus");
        fMinusMarker.setAttribute("cx", fMinusSVG.x.toString());
        fMinusMarker.setAttribute("cy", fMinusSVG.y.toString());
        fMinusMarker.setAttribute("r", "4");
        fMinusMarker.setAttribute("fill", color);
        fMinusMarker.setAttribute("stroke", "#ffffff");
        fMinusMarker.setAttribute("stroke-width", "1");
        fMinusMarker.setAttribute("pointer-events", pointerEvents);
        this.instance.ui.cursorGroup.appendChild(fMinusMarker);
      }
      if (doppler.fZero) {
        const fZeroSVG = dataToSVG(doppler.fZero, this.getViewport(), this.instance.ui.spectrogramImage);
        const hLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
        hLine.setAttribute("class", "gram-frame-doppler-crosshair");
        hLine.setAttribute("x1", (fZeroSVG.x - 8).toString());
        hLine.setAttribute("y1", fZeroSVG.y.toString());
        hLine.setAttribute("x2", (fZeroSVG.x + 8).toString());
        hLine.setAttribute("y2", fZeroSVG.y.toString());
        hLine.setAttribute("stroke", "#00ff00");
        hLine.setAttribute("stroke-width", "2");
        hLine.setAttribute("pointer-events", pointerEvents);
        this.instance.ui.cursorGroup.appendChild(hLine);
        const vLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
        vLine.setAttribute("class", "gram-frame-doppler-crosshair");
        vLine.setAttribute("x1", fZeroSVG.x.toString());
        vLine.setAttribute("y1", (fZeroSVG.y - 8).toString());
        vLine.setAttribute("x2", fZeroSVG.x.toString());
        vLine.setAttribute("y2", (fZeroSVG.y + 8).toString());
        vLine.setAttribute("stroke", "#00ff00");
        vLine.setAttribute("stroke-width", "2");
        vLine.setAttribute("pointer-events", pointerEvents);
        this.instance.ui.cursorGroup.appendChild(vLine);
      }
    }
    /**
     * Render Doppler curve between markers with vertical extensions (zoom-aware)
     */
    renderDopplerCurve() {
      const doppler = this.instance.state.doppler;
      if (!doppler.fPlus || !doppler.fMinus || !doppler.fZero) return;
      const color = doppler.color || this.instance.state.selectedColor || "#ff0000";
      const fPlusSVG = dataToSVG(doppler.fPlus, this.getViewport(), this.instance.ui.spectrogramImage);
      const fMinusSVG = dataToSVG(doppler.fMinus, this.getViewport(), this.instance.ui.spectrogramImage);
      const fZeroSVG = dataToSVG(doppler.fZero, this.getViewport(), this.instance.ui.spectrogramImage);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("class", "gram-frame-doppler-curve");
      const controlPoint1X = fMinusSVG.x;
      const controlPoint1Y = fMinusSVG.y + (fZeroSVG.y - fMinusSVG.y) * 0.7;
      const controlPoint2X = fPlusSVG.x;
      const controlPoint2Y = fPlusSVG.y + (fZeroSVG.y - fPlusSVG.y) * 0.7;
      const pathData = `M ${fMinusSVG.x} ${fMinusSVG.y} C ${controlPoint1X} ${controlPoint1Y} ${controlPoint2X} ${controlPoint2Y} ${fPlusSVG.x} ${fPlusSVG.y}`;
      path.setAttribute("d", pathData);
      path.setAttribute("stroke", color);
      path.setAttribute("stroke-width", "2");
      path.setAttribute("fill", "none");
      this.instance.ui.cursorGroup.appendChild(path);
      const margins = this.instance.state.margins;
      const { naturalHeight } = this.instance.state.imageDetails;
      const renderHeight = this.instance.state.imageDetails.renderHeight || naturalHeight;
      const spectrogramTop = margins.top;
      const spectrogramBottom = margins.top + renderHeight;
      let zoomedTop = spectrogramTop;
      let zoomedBottom = spectrogramBottom;
      if (this.instance.ui.spectrogramImage) {
        const zoomedImageTop = parseFloat(this.instance.ui.spectrogramImage.getAttribute("y") || String(margins.top));
        const zoomedImageHeight = parseFloat(this.instance.ui.spectrogramImage.getAttribute("height") || String(renderHeight));
        zoomedTop = zoomedImageTop;
        zoomedBottom = zoomedImageTop + zoomedImageHeight;
      }
      const clippedTop = Math.max(spectrogramTop, zoomedTop);
      const clippedBottom = Math.min(spectrogramBottom, zoomedBottom);
      if (fPlusSVG.y > clippedTop) {
        const fPlusExtension = document.createElementNS("http://www.w3.org/2000/svg", "line");
        fPlusExtension.setAttribute("class", "gram-frame-doppler-extension");
        fPlusExtension.setAttribute("x1", fPlusSVG.x.toString());
        fPlusExtension.setAttribute("y1", fPlusSVG.y.toString());
        fPlusExtension.setAttribute("x2", fPlusSVG.x.toString());
        fPlusExtension.setAttribute("y2", clippedTop.toString());
        fPlusExtension.setAttribute("stroke", color);
        fPlusExtension.setAttribute("stroke-width", "2");
        this.instance.ui.cursorGroup.appendChild(fPlusExtension);
      }
      if (fMinusSVG.y < clippedBottom) {
        const fMinusExtension = document.createElementNS("http://www.w3.org/2000/svg", "line");
        fMinusExtension.setAttribute("class", "gram-frame-doppler-extension");
        fMinusExtension.setAttribute("x1", fMinusSVG.x.toString());
        fMinusExtension.setAttribute("y1", fMinusSVG.y.toString());
        fMinusExtension.setAttribute("x2", fMinusSVG.x.toString());
        fMinusExtension.setAttribute("y2", clippedBottom.toString());
        fMinusExtension.setAttribute("stroke", color);
        fMinusExtension.setAttribute("stroke-width", "2");
        this.instance.ui.cursorGroup.appendChild(fMinusExtension);
      }
    }
    /**
     * Whether this mode currently owns any persistent feature.
     *
     * Half of the `PersistentFeatureProvider` capability. Lived on
     * `FeatureRenderer` as `hasDopplerFeatures()` until spec 167 moved it onto
     * the mode that owns the state it reads.
     * @returns {boolean} True if any doppler marker has been placed
     */
    hasPersistentFeatures() {
      const doppler = this.instance.state.doppler;
      return !!(doppler && (doppler.fPlus || doppler.fMinus || doppler.fZero));
    }
    /**
     * Render persistent features (for FeatureRenderer)
     */
    renderPersistentFeatures() {
      this.renderDopplerFeatures();
    }
  }
  class PanMode extends BaseMode {
    /**
     * Constructor for pan mode
     * @param {GramFrame} instance - GramFrame instance
     */
    constructor(instance) {
      super(instance);
      this.lastPointer = { x: 0, y: 0 };
      this.pressOrigin = null;
      this.dragHandler = new BaseDragHandler(instance, {
        resolveTarget: () => this.resolvePanDrag(),
        onDragStart: (_target, _position, event) => this.onPanStart(event),
        onDragMove: (_target, _position, _startPosition, event) => this.onPanMove(event),
        onDragEnd: () => this.onPanEnd(),
        onDragCancel: () => this.onPanEnd(),
        updateCursor: (style) => this.updateCursorStyle(style),
        // A pan keeps the hand, rather than the hollow brackets feature drags use:
        // there is no target under the pointer for it to obscure.
        cursorFor: (kind, phase) => {
          if (kind !== "pan") return null;
          return phase === "drag" ? PAN_DRAG_CURSOR : this.idleCursor();
        }
      }, "pan");
    }
    /**
     * Decide whether a mousedown starts a pan. Panning is only meaningful when
     * zoomed in; at zoom 1 the click falls through and does nothing.
     * @returns {DragTarget|null} A pan-kind target, or null to decline
     */
    resolvePanDrag() {
      if (!this.canPan()) {
        return null;
      }
      return { kind: "pan", id: null, type: null };
    }
    /**
     * Whether there is anything to pan: an image zoomed in, or an audio-sourced
     * gram at any zoom — its view is a window onto the recording, so a paused
     * analyst can always scroll back through what has played (spec 168, FR-016).
     * @returns {boolean} True when a drag would move the view
     */
    canPan() {
      return isZoomedIn(this.instance) || isPlayerActive(this.instance);
    }
    /**
     * Panning an audio-sourced gram keeps working off the image.
     *
     * Scrolling back to the very start of a recording *means* putting blank space
     * on screen: the top edge is the playhead, so the first second only reaches
     * it once the whole window below is empty. A pan that stopped the moment the
     * pointer left the gram would strand the analyst partway, with the opening
     * seconds visible but unreachable.
     *
     * Only for the player, and only for panning. On an image-backed gram there is
     * no blank inside the axes to drag from, and every other mode places or moves
     * a feature, which must land on the gram.
     * @returns {boolean} True on an audio-sourced gram
     */
    acceptsOffImageDrag() {
      return isPlayerActive(this.instance);
    }
    /**
     * The cursor pan mode rests at: a grab hand when there is something to pan.
     * @returns {string} Cursor style
     */
    idleCursor() {
      return this.canPan() ? PAN_IDLE_CURSOR : IDLE_CURSOR;
    }
    /**
     * Record where the pan began, in screen pixels.
     * @param {MouseEvent} [event] - Originating mousedown
     */
    onPanStart(event) {
      if (event) {
        this.lastPointer = { x: event.clientX, y: event.clientY };
        event.preventDefault();
      }
    }
    /**
     * Pan the viewport by the pointer delta since the last move.
     * @param {MouseEvent} [event] - Originating mousemove
     */
    onPanMove(event) {
      if (!event || !this.canPan()) {
        return;
      }
      const deltaX = event.clientX - this.lastPointer.x;
      const deltaY = event.clientY - this.lastPointer.y;
      const { normalizedDeltaX, normalizedDeltaY } = pixelDeltaToNormalizedPan(this.instance, deltaX, deltaY);
      panByNormalized(this.instance, normalizedDeltaX, normalizedDeltaY);
      this.lastPointer = { x: event.clientX, y: event.clientY };
    }
    /**
     * Restore the resting cursor when the pan finishes.
     */
    onPanEnd() {
      this.updateCursorStyle(this.idleCursor());
    }
    /**
     * Activate pan mode
     */
    activate() {
      if (this.canPan()) {
        this.updateCursorStyle(PAN_IDLE_CURSOR);
      }
      this.dragHandler.reset();
    }
    /**
     * Deactivate pan mode
     */
    deactivate() {
      this.dragHandler.reset();
      this.updateCursorStyle(IDLE_CURSOR);
    }
    /**
     * Handle mouse down events - start pan drag
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates
     */
    handleMouseDown(event, dataCoords) {
      this.pressOrigin = { x: event.clientX, y: event.clientY };
      this.dragHandler.startDrag(dataCoords, event);
    }
    /**
     * Handle mouse move events - perform pan if dragging
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates
     */
    handleMouseMove(event, dataCoords) {
      this.dragHandler.handleMouseMove(dataCoords, event);
    }
    /**
     * Handle mouse up events - end pan drag
     * @param {MouseEvent} event - Mouse event
     * @param {DataCoordinates} dataCoords - Data coordinates
     */
    handleMouseUp(event, dataCoords) {
      this.dragHandler.endDrag(dataCoords, event);
      const origin = this.pressOrigin;
      this.pressOrigin = null;
      if (origin && isPlayerActive(this.instance)) {
        resumeFromClick(this.instance, origin, event);
      }
    }
    /**
     * Handle mouse leave events
     */
    handleMouseLeave() {
      this.pressOrigin = null;
      this.dragHandler.cancelDrag();
    }
    /**
     * Get guidance content for pan mode.
     *
     * Its own gestures only. The cross-mode ones used to be a second section
     * here, because Pan is the initial mode and the old panel had room for them
     * nowhere else — which meant an analyst who armed Cross Cursor first never
     * learnt that Shift + drag zooms. The guidance column appends them to every
     * mode now (see `utils/guidanceContent.js`).
     * @returns {Object} Structured guidance content
     */
    getGuidanceText() {
      return {
        sections: [
          {
            items: [
              { trigger: "Drag", outcome: "to pan the view when zoomed in" },
              { trigger: "Click", outcome: "on an audio gram, to pause or resume playback" },
              // Named by shape, not by the glyph itself: a character in the
              // guidance would depend on the reader's font, which is the reason
              // the button draws its own (issue #310).
              { trigger: "+ / −", outcome: "to zoom in and out" },
              { trigger: "Fit", outcome: "to bring the whole gram back in one click" },
              `GramFrame v${getVersion()}`
            ]
          }
        ]
      };
    }
    /**
     * Reset pan-specific state
     */
    resetState() {
      this.pressOrigin = null;
      this.dragHandler.reset();
    }
    /**
     * Check if pan mode is enabled.
     *
     * Pan mode is always selectable — it is the initial mode, and staying in it at
     * zoom level 1 is the intended way to avoid accidentally placing markers on a
     * click. Panning itself is still gated on being zoomed in (see handleMouseDown
     * / panByNormalized); at zoom 1 a click simply does nothing.
     * @returns {boolean} Always true
     */
    isEnabled() {
      return true;
    }
    /**
     * Get command buttons for pan mode
     * @returns {Array<CommandButton>} Array of command button definitions
     */
    getCommandButtons() {
      return [
        {
          label: "−",
          title: "Zoom Out",
          action: () => zoomOut(this.instance),
          isEnabled: () => isZoomedIn(this.instance)
        },
        {
          label: "+",
          title: "Zoom In",
          action: () => zoomIn(this.instance),
          isEnabled: () => zoomLevel(this.instance) < 10
        },
        {
          // The exit from a region zoom: one gesture in, one click out (spec 170,
          // FR-014). Disabled at 1x, where the whole gram is already shown (FR-015).
          label: "Fit",
          icon: "fit",
          title: "Fit Whole Gram",
          action: () => fitView(this.instance),
          isEnabled: () => isZoomedIn(this.instance)
        }
      ];
    }
    /**
     * Get initial state for pan mode
     * @returns {Object} Pan mode initial state
     */
    static getInitialState() {
      return {
        // Pan mode doesn't need persistent state
        // Pan position is stored in zoom.centerX/centerY
      };
    }
  }
  const REQUIRED_APIS = [
    {
      // Element.replaceChildren() shipped in Chrome/Edge 86. Its absence on
      // Chrome 84 is the original silent failure this feature guards against
      // (used by src/utils/secureHTML.js and src/components/HarmonicPanel.js).
      name: "Element.prototype.replaceChildren",
      minVersion: 86,
      test: function() {
        return typeof Element !== "undefined" && !!Element.prototype && typeof Element.prototype.replaceChildren === "function";
      }
    },
    {
      // The spectrograph player (spec 168, FR-008) plays through an <audio>
      // element. Present since Chrome 3; listed so a browser without it gets the
      // warning rather than a player that cannot play.
      name: "HTMLAudioElement",
      minVersion: 3,
      test: function() {
        return typeof HTMLAudioElement === "function" || typeof HTMLAudioElement === "object";
      }
    },
    {
      // The player encodes the analysed spectrogram as a PNG through a canvas
      // (spec 168, D6). Present since Chrome 1.
      name: "HTMLCanvasElement.prototype.toDataURL",
      minVersion: 1,
      test: function() {
        return typeof HTMLCanvasElement !== "undefined" && !!HTMLCanvasElement.prototype && typeof HTMLCanvasElement.prototype.toDataURL === "function";
      }
    }
  ];
  const MIN_BROWSER_VERSION = REQUIRED_APIS.reduce(function(max, api) {
    return api.minVersion > max ? api.minVersion : max;
  }, 0);
  function getMissingApis() {
    var missing = [];
    for (var i = 0; i < REQUIRED_APIS.length; i++) {
      var api = REQUIRED_APIS[i];
      var present = false;
      try {
        present = !!api.test();
      } catch (_e) {
        present = false;
      }
      if (!present) {
        missing.push(api.name);
      }
    }
    return missing;
  }
  function isBrowserSupported() {
    return getMissingApis().length === 0;
  }
  var MISSING_CALLABLE_MESSAGE = /is not a function|is not a constructor|doesn't support|does not support|undefined is not a function/i;
  function looksLikeMissingApiError(error) {
    if (!error) {
      return false;
    }
    var err = (
      /** @type {any} */
      error
    );
    var isTypeError = typeof TypeError !== "undefined" && err instanceof TypeError || err.name === "TypeError";
    var message = err.message ? String(err.message) : String(err);
    return !!isTypeError && MISSING_CALLABLE_MESSAGE.test(message);
  }
  function getCompatibilityMessage() {
    return "To view this interactive analysis component, at least version " + MIN_BROWSER_VERSION + " of Chrome or Edge is required. Please update your browser.";
  }
  function createCompatibilityWarningElement() {
    var warning = document.createElement("div");
    warning.className = "gram-frame-compat-warning";
    warning.setAttribute("role", "alert");
    var heading = document.createElement("strong");
    heading.className = "gram-frame-compat-warning-heading";
    heading.textContent = "This interactive component needs a newer browser";
    var message = document.createElement("p");
    message.className = "gram-frame-compat-warning-message";
    message.textContent = getCompatibilityMessage();
    warning.appendChild(heading);
    warning.appendChild(message);
    return warning;
  }
  function showCompatibilityWarning(configTable) {
    if (!configTable || !configTable.parentNode) {
      return null;
    }
    var warning = createCompatibilityWarningElement();
    configTable.parentNode.replaceChild(warning, configTable);
    return warning;
  }
  const MODE_CLASSES = {
    pan: PanMode,
    analysis: AnalysisMode,
    harmonics: HarmonicsMode,
    sideband: SidebandMode,
    doppler: DopplerMode
  };
  class ModeFactory {
    /**
     * Create a mode instance based on mode name
     * @param {ModeType} modeName - Name of the mode
     * @param {GramFrame} instance - GramFrame instance
     * @returns {BaseMode} Mode instance
     * @throws {Error} If mode name is invalid or the mode fails to construct.
     *   The failure is always propagated (spec 165, GF-04): a mode that cannot be
     *   built leaves the component unable to interact, so the caller surfaces the
     *   standard `.gramframe-error-indicator` instead of shipping a silent no-op.
     */
    static createMode(modeName, instance) {
      var _a;
      try {
        const ModeClass = Object.prototype.hasOwnProperty.call(MODE_CLASSES, modeName) ? MODE_CLASSES[modeName] : null;
        if (!ModeClass) {
          throw new Error(`Invalid mode name: ${modeName}. Valid modes are: ${MODE_NAMES.join(", ")}`);
        }
        return new ModeClass(instance);
      } catch (error) {
        console.error(`CRITICAL ERROR: Failed to create mode "${modeName}":`, error);
        console.error("Error details:", {
          message: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : void 0,
          modeName,
          instanceType: (_a = instance == null ? void 0 : instance.constructor) == null ? void 0 : _a.name,
          stateExists: !!(instance == null ? void 0 : instance.state)
        });
        if (looksLikeMissingApiError(error)) {
          throw error;
        }
        const message = `Mode creation failed for "${modeName}": ${error instanceof Error ? error.message : String(error)}`;
        const wrapped = (
          /** @type {any} */
          new Error(message)
        );
        wrapped.cause = error;
        throw wrapped;
      }
    }
    /**
     * Compose the initial-state slices contributed by every registered mode.
     *
     * The single place that knows the mode roster for state purposes, mirroring
     * `createMode`'s role for instantiation. `core/state.js` receives the result
     * rather than importing the mode classes itself, which is what breaks the
     * state ⇄ modes cycle (spec 167, FR-002, ADR-014).
     *
     * Merge order is the roster's, so it cannot drift from the roster the rest
     * of the component uses. The order is immaterial in practice -- each mode
     * contributes a slice named after itself -- but a collision between two
     * modes would resolve by it, and `assertNoCoreKeyCollision` covers the core
     * keys either way.
     * @returns {Partial<GramFrameState>} Merged mode slices
     */
    static getModeInitialStates() {
      const slices = Object.assign({}, ...MODE_NAMES.map((name) => {
        const ModeClass = (
          /** @type {any} */
          MODE_CLASSES[name]
        );
        return typeof ModeClass.getInitialState === "function" ? ModeClass.getInitialState() : {};
      }));
      assertNoCoreKeyCollision(slices);
      return slices;
    }
    /**
     * Get list of available mode names
     * @returns {ModeType[]} Array of mode names
     */
    static getAvailableModes() {
      return [...MODE_NAMES];
    }
    /**
     * Validate if a mode name is supported
     * @param {ModeType} modeName - Mode name to validate
     * @returns {boolean} True if mode is supported
     */
    static isValidMode(modeName) {
      return this.getAvailableModes().includes(modeName);
    }
  }
  function assertNoCoreKeyCollision(slices) {
    const coreKeys = Object.keys(createInitialState());
    const collisions = Object.keys(slices).filter((key) => coreKeys.includes(key));
    if (collisions.length > 0) {
      console.error(
        `GramFrame: mode initial state collides with core state key(s): ${collisions.join(", ")}. The core value wins and the mode's is discarded. Rename the key in the mode that contributes it.`
      );
    }
  }
  class FeatureRenderer {
    /**
     * Create a new FeatureRenderer
     * @param {GramFrame} gramFrameInstance - GramFrame instance
     */
    constructor(gramFrameInstance) {
      this.instance = gramFrameInstance;
    }
    /**
     * Render all persistent features across all modes
     *
     * Modes are discovered by capability, not by name. This file used to name
     * `analysis`, `harmonics` and `doppler` and carry a `hasXFeatures()` predicate
     * for each — eight reads into another mode's state slice. Each predicate now
     * lives on the mode that owns the state it reads, so a fifth mode with
     * persistent features renders here with no edit to this file
     * (spec 167, FR-006, AS-4.2, SC-003).
     */
    renderAllPersistentFeatures() {
      if (!this.instance.ui.cursorGroup) {
        return;
      }
      this.instance.ui.cursorGroup.innerHTML = "";
      Object.values(this.instance.modes).filter(isPersistentFeatureProvider).filter((mode) => mode.hasPersistentFeatures()).forEach((mode) => mode.renderPersistentFeatures());
      applySelectionHalo(this.instance);
    }
  }
  function initializeModeInfrastructure(instance) {
    const modes = {};
    const featureRenderer = new FeatureRenderer(instance);
    ModeFactory.getAvailableModes().forEach((modeName) => {
      modes[modeName] = ModeFactory.createMode(modeName, instance);
    });
    return { modes, featureRenderer };
  }
  function setupModeUI(instance, modes, panelContainers) {
    Object.entries(panelContainers).forEach(([modeName, container]) => {
      if (modes[modeName]) {
        modes[modeName].createUI(container);
      }
    });
    const currentMode = modes[instance.state.mode] || modes["pan"];
    showGuidanceForMode(instance, currentMode);
    return currentMode;
  }
  const MAX_IMAGE_WIDTH = 1200;
  function setupSpectrogramImage(instance, imageUrl) {
    if (!instance.ui.spectrogramImage || !imageUrl) {
      return;
    }
    instance.ui.spectrogramImage.setAttributeNS("http://www.w3.org/1999/xlink", "href", imageUrl);
    instance.state.imageDetails.url = imageUrl;
    const tempImg = new Image();
    tempImg.onload = function() {
      instance.ui.container.classList.remove("gram-frame-loading");
      let imageWidth = tempImg.naturalWidth;
      let imageHeight = tempImg.naturalHeight;
      if (imageWidth > MAX_IMAGE_WIDTH) {
        const scaleFactor = MAX_IMAGE_WIDTH / imageWidth;
        imageWidth = MAX_IMAGE_WIDTH;
        imageHeight = Math.round(imageHeight * scaleFactor);
        console.log(`GramFrame: Scaling down large image from ${tempImg.naturalWidth}x${tempImg.naturalHeight} to ${imageWidth}x${imageHeight} (scale factor: ${scaleFactor.toFixed(3)})`);
      }
      const imageDetails = instance.state.imageDetails;
      imageDetails.naturalWidth = imageWidth;
      imageDetails.naturalHeight = imageHeight;
      imageDetails.renderWidth = imageWidth;
      imageDetails.renderHeight = imageHeight;
      updateSVGLayout(instance);
      renderAxes(instance);
      createExpandToggle(instance);
      dispatch(instance);
    };
    tempImg.onerror = function() {
      console.error(`GramFrame: Failed to load spectrogram image: ${imageUrl}`);
      instance.ui.container.classList.remove("gram-frame-loading");
      instance.ui.container.classList.add("gram-frame-image-error");
    };
    tempImg.src = imageUrl;
  }
  function createUnifiedLayoutStructure(instance, readoutPanel, modeCell) {
    const layout = createUnifiedLayout(instance);
    readoutPanel.appendChild(layout.unifiedLayoutContainer);
    modeCell.appendChild(readoutPanel);
    return layout;
  }
  function setupPersistentContainers(instance, modeColumn) {
    return createModeSwitchingUI(modeColumn, instance.state.mode, (mode) => instance._switchMode(mode));
  }
  function updateModeUIWithCommands(instance, previous, modes, currentMode, modeColumn) {
    modeColumn.removeChild(previous.modesContainer);
    const armed = instance.state.mode;
    const modeUIWithButtons = createModeSwitchingUI(modeColumn, armed, (mode) => instance._switchMode(mode), modes);
    showGuidanceForMode(instance, currentMode);
    applyGuidanceCollapsed(instance);
    return modeUIWithButtons;
  }
  function setupSpectrogramIfAvailable(instance) {
    const { imageDetails, player } = instance.state;
    if (imageDetails.url && !player.active) {
      setupSpectrogramImage(instance, imageDetails.url);
    }
  }
  function createErrorIndicator(errorMsg) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "gramframe-error-indicator";
    errorDiv.style.cssText = `
    position: relative;
    background-color: #ffe6e6;
    border: 2px solid #ff6b6b;
    border-radius: 4px;
    padding: 10px;
    margin: 10px 0;
    color: #d32f2f;
    font-family: monospace;
    font-size: 14px;
  `;
    const strongElement = document.createElement("strong");
    strongElement.textContent = "GramFrame Initialization Error:";
    const errorText = document.createElement("div");
    errorText.textContent = errorMsg;
    const smallElement = document.createElement("small");
    smallElement.textContent = "Check the browser console for detailed error information.";
    errorDiv.appendChild(strongElement);
    errorDiv.appendChild(document.createElement("br"));
    errorDiv.appendChild(errorText);
    errorDiv.appendChild(document.createElement("br"));
    errorDiv.appendChild(smallElement);
    return errorDiv;
  }
  function isDebugEnabled() {
    return typeof window !== "undefined" && /** @type {any} */
    window.GRAMFRAME_DEBUG === true;
  }
  function attachDebugAPI(api) {
    api.__test__forceUpdate = function() {
      this._getInstances().forEach((instance) => {
        dispatch(instance);
        flushDispatch(instance);
      });
    };
    api.__test__flushDispatches = function() {
      this._getInstances().forEach((instance) => {
        flushDispatch(instance);
      });
    };
    api.__test__getInstances = function() {
      return this._getInstances();
    };
    api.__test__getInstance = function(instanceId) {
      return this._getInstances().find((instance) => instance.instanceId === instanceId) || null;
    };
    api.__test__getGlobalStateListeners = function() {
      return getGlobalStateListeners();
    };
    api.__test__clearGlobalStateListeners = function() {
      clearGlobalStateListeners();
    };
  }
  function createGramFrameAPI(GramFrame2) {
    const api = {
      /**
       * Initialize all config tables on the page
       * @returns {GramFrame[]} Array of GramFrame instances
       */
      init() {
        return this.detectAndReplaceConfigTables(document);
      },
      /**
       * Detect and replace all config tables with interactive GramFrame components
       * @param {Document|HTMLElement} [container=document] - Container to search within
       * @returns {GramFrame[]} Array of GramFrame instances created
       */
      detectAndReplaceConfigTables(container = document) {
        const configTables = container.querySelectorAll("table.gram-config");
        const instances = [];
        if (!isBrowserSupported()) {
          configTables.forEach((table) => {
            showCompatibilityWarning(
              /** @type {HTMLElement} */
              table
            );
          });
          return instances;
        }
        configTables.forEach((table, index) => {
          const originalParent = table.parentNode;
          const originalNextSibling = table.nextSibling;
          try {
            const instanceId = `gramframe-${Date.now()}-${index}`;
            const instance = new GramFrame2(
              /** @type {HTMLTableElement} */
              table
            );
            instance.instanceId = instanceId;
            instance.state.instanceId = instanceId;
            instances.push(instance);
          } catch (error) {
            const errorMsg = `Failed to initialize GramFrame for table ${index + 1}: ${error instanceof Error ? error.message : String(error)}`;
            console.error("GramFrame Error:", errorMsg, error);
            this._restoreConfigTable(
              /** @type {HTMLTableElement} */
              table,
              originalParent,
              originalNextSibling
            );
            if (looksLikeMissingApiError(error)) {
              showCompatibilityWarning(
                /** @type {HTMLElement} */
                table
              );
            } else {
              this._addErrorIndicator(
                /** @type {HTMLTableElement} */
                table,
                errorMsg
              );
            }
          }
        });
        this._instances = [...this._getInstances(), ...instances];
        return instances;
      },
      /**
       * The live set of GramFrame instances — the API's single registry.
       *
       * Every API method reads instances through here. Previously some methods
       * walked `.gram-frame-container` elements in the DOM while others read the
       * `_instances` array, so the two could disagree about which instances
       * existed (GF-24). Instances whose container has left the document
       * (destroyed, or replaced by a re-initialization) are dropped on read.
       * @private
       * @returns {GramFrame[]} Live instances
       */
      _getInstances() {
        const live = (this._instances || []).filter(
          (instance) => instance && instance.ui.container && instance.ui.container.isConnected
        );
        this._instances = live;
        return live;
      },
      /**
       * Add a state listener that will be called whenever the component state changes
       * @param {Function} callback - Function to be called with the current state
       * @returns {Function} - Returns the callback function for chaining
       * @example
       * // Basic usage
       * GramFrame.addStateListener(state => {
       *   // State updated: state
       * })
       * 
       * // With error handling
       * GramFrame.addStateListener(state => {
       *   try {
       *     // Process state
       *     updateUI(state.cursorPosition)
       *   } catch (err) {
       *     console.error('Error processing state:', err)
       *   }
       * })
       */
      /**
       * Add a state listener that will be called whenever the component state changes
       * @param {StateListener} callback - Function to be called with the current state
       * @returns {StateListener} Returns the callback function for chaining
       */
      addStateListener(callback) {
        if (typeof callback !== "function") {
          throw new Error("State listener must be a function");
        }
        const isNew = addGlobalStateListener(callback);
        if (isNew) {
          this._getInstances().forEach((instance) => {
            if (instance.state) {
              try {
                const stateCopy = JSON.parse(JSON.stringify(instance.state));
                callback(stateCopy);
              } catch (error) {
                console.error("Error calling state listener with initial state:", error);
              }
            }
          });
        }
        return callback;
      },
      /**
       * Remove a previously added state listener
       * @param {Function} callback - The callback function to remove
       * @returns {boolean} - Returns true if the listener was found and removed, false otherwise
       * @example
       * // Add a listener and store the reference
       * const myListener = GramFrame.addStateListener(state => {
       *   // State updated: state
       * })
       * 
       * // Later, remove the listener
       * GramFrame.removeStateListener(myListener)
       */
      /**
       * Remove a previously added state listener
       * @param {StateListener} callback - The callback function to remove
       * @returns {boolean} Returns true if the listener was found and removed, false otherwise
       */
      removeStateListener(callback) {
        if (typeof callback !== "function") {
          throw new Error("Callback must be a function");
        }
        return removeGlobalStateListener(callback);
      },
      /**
       * The transport of an audio-sourced instance (spec 168, FR-020).
       * @param {number} [index=0] - Which live instance, in page order
       * @returns {PlayerController|null} Its player, or null when the instance is image-backed or absent
       */
      getPlayer(index = 0) {
        const instance = this._getInstances()[index];
        return instance && instance.player ? instance.player : null;
      },
      /**
       * Get the current expand state of the first GramFrame instance.
       * @returns {boolean} True if the image is currently expanded
       */
      getExpandState() {
        const instance = this._getInstances()[0];
        return !!(instance && instance.state && instance.state.imageExpanded);
      },
      /**
       * Programmatically expand or collapse all landscape GramFrame instances.
       * No-op for portrait/square images (mirrors the toggle's landscape gate).
       * @param {boolean} expanded - Desired expand state
       */
      setExpandState(expanded) {
        this._getInstances().forEach((instance) => {
          if (isLandscape(instance)) {
            setImageExpanded(instance, expanded);
          }
        });
      },
      /**
       * Put a config table back where it started after a failed initialization,
       * removing the half-built component container that replaced it.
       *
       * Construction swaps the table for the component container before the mode
       * system is built, so a failure after that point leaves a container that
       * looks like a working component but cannot interact. Restoring the table
       * gives both the compatibility warning and the error indicator a live
       * anchor to attach to, and leaves nothing misleading on the page.
       * @private
       * @param {HTMLTableElement} table - Table that failed to initialize
       * @param {Node|null} originalParent - Parent the table had before construction
       * @param {Node|null} originalNextSibling - Sibling the table sat before
       */
      _restoreConfigTable(table, originalParent, originalNextSibling) {
        if (!originalParent || table.parentNode) {
          return;
        }
        try {
          const replacement = originalNextSibling ? originalNextSibling.previousSibling : originalParent.lastChild;
          if (replacement && replacement instanceof Element && replacement.classList.contains("gram-frame-container")) {
            replacement.remove();
          }
          originalParent.insertBefore(table, originalNextSibling);
        } catch (e) {
          console.error("GramFrame: Failed to restore the config table after an initialization error:", e);
        }
      },
      /**
       * Add error indicator to a table that failed to initialize
       * @private
       * @param {HTMLTableElement} table - Table that failed
       * @param {string} errorMsg - Error message to display
       */
      _addErrorIndicator(table, errorMsg) {
        try {
          table.classList.add("gram-frame-config-error");
          const errorDiv = createErrorIndicator(errorMsg);
          if (table.parentNode) {
            table.parentNode.insertBefore(errorDiv, table.nextSibling);
          }
        } catch (e) {
          console.error("GramFrame: Failed to add error indicator:", e);
        }
      }
    };
    if (isDebugEnabled()) {
      attachDebugAPI(api);
    }
    return api;
  }
  const SCHEMA_VERSION = 1;
  const STUDENT_TTL_MS = 24 * 60 * 60 * 1e3;
  const KEY_PREFIX = "gramframe::";
  const TRAINER_FLAG_SELECTOR = "#gf-persistent, .gf-persistent, [data-gf-persistent]";
  function isAnnotationExpired(savedAt, nowMs) {
    const t = Date.parse(
      /** @type {string} */
      savedAt
    );
    if (Number.isNaN(t)) {
      return true;
    }
    const age = nowMs - t;
    if (age < -3e5) {
      return true;
    }
    return age > STUDENT_TTL_MS;
  }
  function describeUserContext() {
    const flag = document.querySelector(TRAINER_FLAG_SELECTOR);
    if (flag) {
      return {
        context: "trainer",
        matchedBy: "flag",
        reason: `matched the persistence flag on <${describeFlagElement(flag)}>`
      };
    }
    const anchors = document.querySelectorAll("a");
    for (let i = 0; i < anchors.length; i++) {
      const text = anchors[i].textContent;
      if (text && text.trim() === "ANALYSIS") {
        return {
          context: "trainer",
          matchedBy: "legacy-anchor",
          reason: 'matched the legacy "ANALYSIS" anchor (no gf-persistent flag on the page)'
        };
      }
    }
    return {
      context: "student",
      matchedBy: "none",
      reason: 'no gf-persistent flag (id, class or data-attribute) and no "ANALYSIS" anchor was on the page when the component initialised'
    };
  }
  function detectUserContext() {
    return describeUserContext().context;
  }
  function describeFlagElement(el) {
    const parts = [el.tagName.toLowerCase()];
    if (el.id === "gf-persistent") parts.push('id="gf-persistent"');
    if (el.classList.contains("gf-persistent")) parts.push('class="gf-persistent"');
    if (el.hasAttribute("data-gf-persistent")) parts.push("data-gf-persistent");
    return parts.join(" ");
  }
  function getStorage(context) {
    try {
      const storage = context === "trainer" ? localStorage : sessionStorage;
      const testKey = "__gramframe_test__";
      storage.setItem(testKey, "1");
      storage.removeItem(testKey);
      return storage;
    } catch (error) {
      console.warn(`GramFrame: ${context} storage is unavailable — annotations will not persist:`, error);
      return null;
    }
  }
  function buildStorageKey(instanceIndex) {
    const pathname = window.location.pathname;
    if (instanceIndex != null && instanceIndex > 0) {
      return `${KEY_PREFIX}${pathname}::${instanceIndex}`;
    }
    return `${KEY_PREFIX}${pathname}`;
  }
  function hasPersistableAnnotations(state) {
    const hasMarkers = !!(state.analysis && state.analysis.markers && state.analysis.markers.length > 0);
    const hasHarmonics = !!(state.harmonics && state.harmonics.harmonicSets && state.harmonics.harmonicSets.length > 0);
    const hasSidebands = !!(state.sidebands && state.sidebands.sidebandSets && state.sidebands.sidebandSets.length > 0);
    const hasDoppler = !!(state.doppler && (state.doppler.fPlus !== null || state.doppler.fMinus !== null || state.doppler.fZero !== null));
    return hasMarkers || hasHarmonics || hasSidebands || hasDoppler;
  }
  function isFiniteNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }
  function isNonEmptyString(value) {
    return typeof value === "string" && value.length > 0;
  }
  function isValidStoredPoint(point) {
    if (point === null || point === void 0) return true;
    return !!point && isFiniteNumber(point.time) && isFiniteNumber(point.freq);
  }
  function sanitizeStoredAnnotations(data) {
    let dropped = 0;
    let markers = [];
    if (data && data.analysis && Array.isArray(data.analysis.markers)) {
      markers = data.analysis.markers.filter((m) => {
        const valid = !!m && isNonEmptyString(m.id) && isNonEmptyString(m.color) && isFiniteNumber(m.time) && isFiniteNumber(m.freq);
        if (!valid) dropped++;
        return valid;
      }).map((m) => {
        const label = normalizeMarkerLabel(m.label);
        const { label: _rawLabel, ...rest } = m;
        return label ? { ...rest, label } : rest;
      });
    } else if (data && data.analysis && data.analysis.markers != null) {
      dropped++;
    }
    let harmonicSets = [];
    if (data && data.harmonics && Array.isArray(data.harmonics.harmonicSets)) {
      harmonicSets = data.harmonics.harmonicSets.filter((hs) => {
        const valid = !!hs && isNonEmptyString(hs.id) && isNonEmptyString(hs.color) && isFiniteNumber(hs.anchorTime) && // Strictly positive: spacing 0 makes the harmonic range infinite.
        isFiniteNumber(hs.spacing) && hs.spacing > 0;
        if (!valid) dropped++;
        return valid;
      });
    } else if (data && data.harmonics && data.harmonics.harmonicSets != null) {
      dropped++;
    }
    let sidebandSets = [];
    if (data && data.sidebands && Array.isArray(data.sidebands.sidebandSets)) {
      sidebandSets = data.sidebands.sidebandSets.filter((sb) => {
        const valid = !!sb && isNonEmptyString(sb.id) && isNonEmptyString(sb.color) && isFiniteNumber(sb.anchorTime) && isFiniteNumber(sb.fundamentalFreq) && // Strictly positive, for the same reason a harmonic set's is: a spacing
        // of zero makes the sideband index range infinite.
        isFiniteNumber(sb.spacing) && sb.spacing > 0;
        if (!valid) dropped++;
        return valid;
      });
    } else if (data && data.sidebands && data.sidebands.sidebandSets != null) {
      dropped++;
    }
    const rawDoppler = data && data.doppler || {};
    const doppler = { fPlus: null, fMinus: null, fZero: null, color: null };
    for (
      const key of
      /** @type {const} */
      ["fPlus", "fMinus", "fZero"]
    ) {
      if (isValidStoredPoint(rawDoppler[key])) {
        doppler[key] = rawDoppler[key] || null;
      } else {
        dropped++;
      }
    }
    doppler.color = isNonEmptyString(rawDoppler.color) ? rawDoppler.color : null;
    const annotations = {
      version: data && data.version,
      savedAt: data && data.savedAt,
      gram: data && data.gram,
      analysis: { markers },
      harmonics: { harmonicSets },
      sidebands: { sidebandSets },
      doppler,
      // Carried through rather than validated field by field: a tombstone is an
      // id and a time, and a damaged one costs at most one resurrected feature.
      // Dropping the set wholesale would resurrect every deletion in it, which is
      // the failure this exists to prevent (issue #269).
      tombstones: tombstonesOf(data)
    };
    return { annotations, dropped };
  }
  const TOMBSTONE_TTL_MS = 7 * 24 * 60 * 60 * 1e3;
  function tombstonesOf(source) {
    const raw = source && source.tombstones;
    if (!raw || typeof raw !== "object") {
      return { markers: {}, harmonicSets: {}, sidebandSets: {}, doppler: null };
    }
    return {
      markers: raw.markers && typeof raw.markers === "object" ? raw.markers : {},
      harmonicSets: raw.harmonicSets && typeof raw.harmonicSets === "object" ? raw.harmonicSets : {},
      sidebandSets: raw.sidebandSets && typeof raw.sidebandSets === "object" ? raw.sidebandSets : {},
      doppler: isNonEmptyString(raw.doppler) ? raw.doppler : null
    };
  }
  function mergeTombstoneMap(mine, theirs) {
    const merged = { ...theirs };
    for (const [id, at] of Object.entries(mine || {})) {
      merged[id] = merged[id] && merged[id] < at ? merged[id] : at;
    }
    return merged;
  }
  function pruneTombstoneMap(map, now) {
    const kept = {};
    for (const [id, at] of Object.entries(map || {})) {
      const when = Date.parse(at);
      if (!Number.isFinite(when) || now - when < TOMBSTONE_TTL_MS) {
        kept[id] = at;
      }
    }
    return kept;
  }
  function mergeCollection(mine, theirs, tombstones, mineIsNewer) {
    const byId = /* @__PURE__ */ new Map();
    const older = mineIsNewer ? theirs : mine;
    const newer = mineIsNewer ? mine : theirs;
    for (const feature of older || []) {
      if (feature && feature.id) byId.set(feature.id, feature);
    }
    for (const feature of newer || []) {
      if (feature && feature.id) byId.set(feature.id, feature);
    }
    return Array.from(byId.values()).filter((feature) => !(feature.id in tombstones));
  }
  function mergeStoredAnnotations(mine, theirs, now = Date.now()) {
    if (!mine) return theirs;
    if (!theirs) return mine;
    const mineAt = Date.parse(mine.savedAt || "");
    const theirsAt = Date.parse(theirs.savedAt || "");
    const mineIsNewer = !Number.isFinite(theirsAt) || Number.isFinite(mineAt) && mineAt >= theirsAt;
    const myTombs = tombstonesOf(mine);
    const theirTombs = tombstonesOf(theirs);
    const tombstones = {
      markers: pruneTombstoneMap(mergeTombstoneMap(myTombs.markers, theirTombs.markers), now),
      harmonicSets: pruneTombstoneMap(mergeTombstoneMap(myTombs.harmonicSets, theirTombs.harmonicSets), now),
      sidebandSets: pruneTombstoneMap(mergeTombstoneMap(myTombs.sidebandSets, theirTombs.sidebandSets), now),
      doppler: myTombs.doppler && theirTombs.doppler ? myTombs.doppler < theirTombs.doppler ? myTombs.doppler : theirTombs.doppler : myTombs.doppler || theirTombs.doppler
    };
    const newer = mineIsNewer ? mine : theirs;
    const older = mineIsNewer ? theirs : mine;
    const newerDoppler = newer.doppler || null;
    const olderDoppler = older.doppler || null;
    const newerHasCurve = !!(newerDoppler && (newerDoppler.fPlus || newerDoppler.fMinus || newerDoppler.fZero));
    const doppler = tombstones.doppler ? { fPlus: null, fMinus: null, fZero: null, color: null } : newerHasCurve ? newerDoppler : olderDoppler || newerDoppler;
    return {
      version: newer.version,
      savedAt: newer.savedAt,
      gram: newer.gram || older.gram,
      analysis: {
        markers: mergeCollection(
          mine.analysis && mine.analysis.markers,
          theirs.analysis && theirs.analysis.markers,
          tombstones.markers,
          mineIsNewer
        )
      },
      harmonics: {
        harmonicSets: mergeCollection(
          mine.harmonics && mine.harmonics.harmonicSets,
          theirs.harmonics && theirs.harmonics.harmonicSets,
          tombstones.harmonicSets,
          mineIsNewer
        )
      },
      sidebands: {
        sidebandSets: mergeCollection(
          mine.sidebands && mine.sidebands.sidebandSets,
          theirs.sidebands && theirs.sidebands.sidebandSets,
          tombstones.sidebandSets,
          mineIsNewer
        )
      },
      doppler: doppler || { fPlus: null, fMinus: null, fZero: null, color: null },
      tombstones
    };
  }
  function buildGramFingerprint(state) {
    const url = state.imageDetails && state.imageDetails.url || "";
    const config = state.config || { timeMin: 0, timeMax: 0, freqMin: 0, freqMax: 0 };
    return {
      image: url.split("/").pop() || "",
      timeMin: config.timeMin,
      timeMax: config.timeMax,
      freqMin: config.freqMin,
      freqMax: config.freqMax
    };
  }
  function fingerprintMatches(stored, expected) {
    if (!stored) {
      return true;
    }
    return stored.image === expected.image && stored.timeMin === expected.timeMin && stored.timeMax === expected.timeMax && stored.freqMin === expected.freqMin && stored.freqMax === expected.freqMax;
  }
  function saveAnnotations(state, instanceIndex, context) {
    try {
      const storage = getStorage(context || detectUserContext());
      if (!storage) return false;
      if (!hasPersistableAnnotations(state) && !hasTombstones(state)) {
        const key2 = buildStorageKey(instanceIndex);
        storage.removeItem(key2);
        return true;
      }
      const data = snapshotAnnotations(state);
      const key = buildStorageKey(instanceIndex);
      const existing = readMergeableRecord(storage, key, data.gram);
      const merged = existing ? mergeStoredAnnotations(data, existing) : data;
      storage.setItem(key, JSON.stringify(merged));
      return true;
    } catch (error) {
      console.warn("GramFrame: Failed to save annotations — they exist in memory only:", error);
      return false;
    }
  }
  function hasTombstones(state) {
    const tombs = tombstonesOf(state);
    return Object.keys(tombs.markers).length > 0 || Object.keys(tombs.harmonicSets).length > 0 || Object.keys(tombs.sidebandSets).length > 0 || !!tombs.doppler;
  }
  function snapshotAnnotations(state) {
    const data = {
      version: SCHEMA_VERSION,
      savedAt: (/* @__PURE__ */ new Date()).toISOString(),
      // `gram` is an ADDITIVE field (which gram this record belongs to). It
      // MUST NOT trigger a SCHEMA_VERSION bump: legacy records simply lack it
      // and restore without the identity check (BH-6, BH-23).
      gram: buildGramFingerprint(state),
      analysis: {
        markers: (state.analysis && state.analysis.markers || []).map((m) => {
          const label = normalizeMarkerLabel(m.label);
          return {
            id: m.id,
            color: m.color,
            time: m.time,
            freq: m.freq,
            // `symbol` is an ADDITIVE field (feature 161). It MUST NOT trigger a
            // SCHEMA_VERSION bump: legacy records simply lack it and default to
            // 'cross' (no drawn symbol) on restore.
            symbol: m.symbol || "cross",
            // `label` is likewise ADDITIVE (feature 231) and MUST NOT bump
            // SCHEMA_VERSION. Written only when the marker carries one, so an
            // unlabelled marker's record is identical to what it was before
            // labels existed, and restores as unlabelled.
            ...label ? { label } : {}
          };
        })
      },
      harmonics: {
        harmonicSets: (state.harmonics && state.harmonics.harmonicSets || []).map((hs) => ({
          id: hs.id,
          color: hs.color,
          anchorTime: hs.anchorTime,
          spacing: hs.spacing,
          // `symbol` is an ADDITIVE field (feature 157-harmonic-pin-symbols). It
          // MUST NOT trigger a SCHEMA_VERSION bump: the strict version guard in
          // loadAnnotations would otherwise discard all pre-existing v1 records.
          // Legacy records simply lack this key and default to 'cross' (the
          // symbol-less default, feature 161) on restore.
          symbol: hs.symbol || "cross",
          // `showPin` is likewise ADDITIVE (harmonic-pin toggle) and MUST NOT
          // bump SCHEMA_VERSION. Records written before it simply lack the key
          // and restore as `true` (pin shown), matching their original look.
          showPin: hs.showPin !== false
        }))
      },
      // `sidebands` is an ADDITIVE section (issue #241). It MUST NOT trigger a
      // SCHEMA_VERSION bump: the strict version guard in loadAnnotations would
      // otherwise discard every pre-existing v1 record. Records written before
      // sidebands existed simply lack the key and restore with none.
      sidebands: {
        sidebandSets: (state.sidebands && state.sidebands.sidebandSets || []).map((sb) => ({
          id: sb.id,
          color: sb.color,
          anchorTime: sb.anchorTime,
          fundamentalFreq: sb.fundamentalFreq,
          spacing: sb.spacing,
          symbol: sb.symbol || "cross",
          showPin: sb.showPin !== false
        }))
      },
      doppler: {
        fPlus: state.doppler && state.doppler.fPlus ? { time: state.doppler.fPlus.time, freq: state.doppler.fPlus.freq } : null,
        fMinus: state.doppler && state.doppler.fMinus ? { time: state.doppler.fMinus.time, freq: state.doppler.fMinus.freq } : null,
        fZero: state.doppler && state.doppler.fZero ? { time: state.doppler.fZero.time, freq: state.doppler.fZero.freq } : null,
        color: state.doppler && state.doppler.color || null
      },
      // `tombstones` is an ADDITIVE field (issue #269). It MUST NOT trigger a
      // SCHEMA_VERSION bump: records written before multi-tab merging simply
      // lack it and merge as having deleted nothing, which is true of them.
      tombstones: tombstonesOf(state)
    };
    return data;
  }
  function mergeForeignRecord(raw, state) {
    let theirs = null;
    try {
      theirs = JSON.parse(raw);
    } catch (error) {
      console.warn("GramFrame: ignoring an unreadable record from another tab:", error);
      return null;
    }
    if (!theirs || theirs.version !== SCHEMA_VERSION) {
      return null;
    }
    if (theirs.gram && !fingerprintMatches(theirs.gram, buildGramFingerprint(state))) {
      return null;
    }
    return mergeStoredAnnotations(snapshotAnnotations(state), theirs);
  }
  function readMergeableRecord(storage, key, expectedGram) {
    try {
      const raw = storage.getItem(key);
      if (!raw) return null;
      const existing = JSON.parse(raw);
      if (!existing || existing.version !== SCHEMA_VERSION) return null;
      if (expectedGram && !fingerprintMatches(existing.gram, expectedGram)) return null;
      return existing;
    } catch (error) {
      console.warn("GramFrame: could not read the stored record to merge with — saving without merging:", error);
      return null;
    }
  }
  function loadResult(outcome, annotations = null, dropped = 0) {
    return { annotations, outcome, dropped };
  }
  function loadAnnotations(instanceIndex, context, expectedGram) {
    try {
      const resolvedContext = context || detectUserContext();
      const storage = getStorage(resolvedContext);
      if (!storage) return loadResult("none");
      const key = buildStorageKey(instanceIndex);
      const raw = storage.getItem(key);
      if (!raw) return loadResult("none");
      let data;
      try {
        data = JSON.parse(raw);
      } catch (parseError) {
        console.warn("GramFrame: Stored annotations could not be parsed — leaving the record in place:", parseError);
        return loadResult("unreadable");
      }
      if (!data || data.version !== SCHEMA_VERSION) {
        console.warn("GramFrame: Ignoring stored annotations — unrecognised schema version:", data && data.version);
        return loadResult("unknown-version");
      }
      if (resolvedContext === "student" && isAnnotationExpired(data.savedAt, Date.now())) {
        console.info("GramFrame: Discarding student annotations — older than the 24-hour persistence limit");
        storage.removeItem(key);
        return loadResult("expired");
      }
      if (expectedGram && !fingerprintMatches(data.gram, expectedGram)) {
        console.warn("GramFrame: Ignoring stored annotations — they belong to a different spectrogram (image or axis ranges differ).");
        return loadResult("wrong-gram");
      }
      const { annotations, dropped } = sanitizeStoredAnnotations(data);
      if (dropped > 0) {
        console.warn(`GramFrame: Discarded ${dropped} invalid stored annotation entr${dropped === 1 ? "y" : "ies"} — restoring the rest.`);
        return loadResult("partial", annotations, dropped);
      }
      return loadResult("restored", annotations);
    } catch (error) {
      console.warn("GramFrame: Failed to load stored annotations — data discarded:", error);
      return loadResult("unreadable");
    }
  }
  function describeLoadOutcome(outcome, dropped = 0) {
    switch (outcome) {
      case "partial":
        return `${dropped} saved annotation${dropped === 1 ? "" : "s"} could not be restored and ${dropped === 1 ? "was" : "were"} skipped — the rest are shown.`;
      case "unreadable":
        return "Saved annotations could not be read and were not restored — the stored data is damaged. It has been left in browser storage, so nothing has been overwritten yet.";
      case "unknown-version":
        return "Saved annotations were not restored — they were written by a different version of this component. They have been left in browser storage.";
      case "wrong-gram":
        return "Saved annotations were not restored — they belong to a different spectrogram. They have been left in browser storage.";
      case "expired":
        return "Saved annotations were not restored — they were more than 24 hours old and have been discarded.";
      case "none":
      case "restored":
      default:
        return null;
    }
  }
  function clearAnnotations(instanceIndex, context) {
    try {
      const storage = getStorage(context || detectUserContext());
      if (!storage) return false;
      const key = buildStorageKey(instanceIndex);
      storage.removeItem(key);
      return true;
    } catch (error) {
      console.warn("GramFrame: Failed to clear stored annotations:", error);
      return false;
    }
  }
  function sidecarKey(src) {
    const path = src.split("#")[0].split("?")[0];
    return decodeURIComponent(path.split("/").pop() || path);
  }
  function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }
  function loadSidecar(src, doc) {
    const key = sidecarKey(src);
    const registry = (
      /** @type {SidecarRegistry|undefined} */
      /** @type {any} */
      window.GramFrameAudio
    );
    if (registry && typeof registry[key] === "string") {
      return Promise.resolve(base64ToArrayBuffer(registry[key]));
    }
    const sidecarUrl = `${src.split("#")[0]}.js`;
    return new Promise((resolve, reject) => {
      const script = doc.createElement("script");
      script.async = true;
      script.src = sidecarUrl;
      const cleanup = () => {
        script.onload = null;
        script.onerror = null;
        if (script.parentNode) script.parentNode.removeChild(script);
      };
      script.onload = () => {
        cleanup();
        const loaded = (
          /** @type {SidecarRegistry|undefined} */
          /** @type {any} */
          window.GramFrameAudio
        );
        if (loaded && typeof loaded[key] === "string") {
          resolve(base64ToArrayBuffer(loaded[key]));
        } else {
          reject(new Error(
            `${sidecarUrl} loaded but did not register "${key}". Regenerate it with: node scripts/wav2js.mjs <file.wav>`
          ));
        }
      };
      script.onerror = () => {
        cleanup();
        reject(new Error(
          `Could not load ${src} (fetch is unavailable on this page — file:// or a network error) and no sidecar was found at ${sidecarUrl}. For file:// distribution generate one with: node scripts/wav2js.mjs <file.wav>`
        ));
      };
      doc.head.appendChild(script);
    });
  }
  function looksLikeWav(bytes) {
    if (bytes.byteLength < 12) return false;
    const head = new Uint8Array(bytes, 0, 12);
    let text = "";
    for (let i = 0; i < head.length; i++) text += String.fromCharCode(head[i]);
    return text.startsWith("RIFF") && text.slice(8) === "WAVE";
  }
  async function loadAudioBytes(src, options = {}) {
    const doc = options.doc || document;
    let fetched = null;
    try {
      const response = await fetch(src);
      if (response.ok) {
        fetched = await response.arrayBuffer();
        if (looksLikeWav(fetched)) {
          return fetched;
        }
        console.warn(`GramFrame: fetch of ${src} returned ${fetched.byteLength} bytes that are not a WAV; trying the sidecar`);
      } else {
        console.warn(`GramFrame: fetch of ${src} returned ${response.status}; trying the sidecar`);
      }
    } catch (error) {
      console.warn(`GramFrame: fetch of ${src} failed (${error instanceof Error ? error.message : String(error)}); trying the sidecar`);
    }
    try {
      return await loadSidecar(src, doc);
    } catch (sidecarError) {
      if (fetched) {
        return fetched;
      }
      throw sidecarError;
    }
  }
  const FORMAT_PCM = 1;
  const FORMAT_IEEE_FLOAT = 3;
  const FORMAT_EXTENSIBLE = 65534;
  function fourCC(view, offset) {
    return String.fromCharCode(
      view.getUint8(offset),
      view.getUint8(offset + 1),
      view.getUint8(offset + 2),
      view.getUint8(offset + 3)
    );
  }
  function decodeWav(buffer) {
    if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < 12) {
      throw new Error("Not a WAV file: too short to hold a RIFF header");
    }
    const view = new DataView(buffer);
    if (fourCC(view, 0) !== "RIFF" || fourCC(view, 8) !== "WAVE") {
      throw new Error(`Not a WAV file: expected a RIFF/WAVE header, found "${fourCC(view, 0)}"/"${fourCC(view, 8)}"`);
    }
    let format = null;
    let data = null;
    let offset = 12;
    while (offset + 8 <= view.byteLength) {
      const id = fourCC(view, offset);
      const size = view.getUint32(offset + 4, true);
      const body = offset + 8;
      if (id === "fmt ") {
        if (size < 16) {
          throw new Error(`Malformed WAV: "fmt " chunk is ${size} bytes, expected at least 16`);
        }
        let formatTag2 = view.getUint16(body, true);
        const channels2 = view.getUint16(body + 2, true);
        const sampleRate2 = view.getUint32(body + 4, true);
        const bitsPerSample2 = view.getUint16(body + 14, true);
        if (formatTag2 === FORMAT_EXTENSIBLE) {
          if (size < 26) {
            throw new Error("Malformed WAV: WAVE_FORMAT_EXTENSIBLE header is truncated");
          }
          formatTag2 = view.getUint16(body + 24, true);
        }
        format = { formatTag: formatTag2, channels: channels2, sampleRate: sampleRate2, bitsPerSample: bitsPerSample2 };
      } else if (id === "data") {
        const available = view.byteLength - body;
        const length = size === 0 || size === 4294967295 || size > available ? available : size;
        data = { offset: body, length };
      }
      offset = body + size + size % 2;
    }
    if (!format) {
      throw new Error('Malformed WAV: no "fmt " chunk');
    }
    if (!data) {
      throw new Error('Malformed WAV: no "data" chunk');
    }
    if (format.channels < 1) {
      throw new Error("Malformed WAV: channel count is 0");
    }
    if (format.sampleRate < 1) {
      throw new Error("Malformed WAV: sample rate is 0");
    }
    const { formatTag, channels, sampleRate, bitsPerSample } = format;
    const isFloat = formatTag === FORMAT_IEEE_FLOAT;
    if (formatTag !== FORMAT_PCM && !isFloat) {
      throw new Error(`Unsupported WAV format tag ${formatTag}: only PCM (1) and IEEE float (3) are supported`);
    }
    if (isFloat && bitsPerSample !== 32) {
      throw new Error(`Unsupported WAV: ${bitsPerSample}-bit float; only 32-bit float is supported`);
    }
    if (!isFloat && ![8, 16, 24, 32].includes(bitsPerSample)) {
      throw new Error(`Unsupported WAV: ${bitsPerSample}-bit PCM; only 8, 16, 24 and 32-bit PCM are supported`);
    }
    const bytesPerSample = bitsPerSample / 8;
    const frameBytes = bytesPerSample * channels;
    const frameCount = Math.floor(data.length / frameBytes);
    if (frameCount === 0) {
      throw new Error('Malformed WAV: the "data" chunk holds no complete sample frame');
    }
    const samples = new Float32Array(frameCount);
    const scale = 1 / channels;
    let pos = data.offset;
    if (isFloat) {
      for (let i = 0; i < frameCount; i++) {
        let sum = 0;
        for (let c = 0; c < channels; c++) {
          sum += view.getFloat32(pos, true);
          pos += 4;
        }
        samples[i] = sum * scale;
      }
    } else if (bitsPerSample === 16) {
      const k = scale / 32768;
      for (let i = 0; i < frameCount; i++) {
        let sum = 0;
        for (let c = 0; c < channels; c++) {
          sum += view.getInt16(pos, true);
          pos += 2;
        }
        samples[i] = sum * k;
      }
    } else if (bitsPerSample === 8) {
      const k = scale / 128;
      for (let i = 0; i < frameCount; i++) {
        let sum = 0;
        for (let c = 0; c < channels; c++) {
          sum += view.getUint8(pos) - 128;
          pos += 1;
        }
        samples[i] = sum * k;
      }
    } else if (bitsPerSample === 24) {
      const k = scale / 8388608;
      for (let i = 0; i < frameCount; i++) {
        let sum = 0;
        for (let c = 0; c < channels; c++) {
          const raw = view.getUint8(pos) | view.getUint8(pos + 1) << 8 | view.getUint8(pos + 2) << 16;
          sum += raw << 8 >> 8;
          pos += 3;
        }
        samples[i] = sum * k;
      }
    } else {
      const k = scale / 2147483648;
      for (let i = 0; i < frameCount; i++) {
        let sum = 0;
        for (let c = 0; c < channels; c++) {
          sum += view.getInt32(pos, true);
          pos += 4;
        }
        samples[i] = sum * k;
      }
    }
    return { samples, sampleRate, channels, duration: frameCount / sampleRate };
  }
  function planAnalysis(request) {
    const { sampleRate, sampleCount, fftSize, hopSize } = request;
    if (!isPowerOfTwo(fftSize)) {
      throw new Error(`fft-size must be a power of two, got ${fftSize}`);
    }
    if (!Number.isInteger(hopSize) || hopSize < 1) {
      throw new Error(`hop-size must be a positive integer, got ${hopSize}`);
    }
    const frames = Math.floor((sampleCount - fftSize) / hopSize) + 1;
    if (frames < 1) {
      throw new Error(`The recording (${sampleCount} samples) is shorter than one analysis frame (${fftSize} samples)`);
    }
    const nyquist = sampleRate / 2;
    const binWidth = sampleRate / fftSize;
    const requestedEnd = request.freqEnd === null || request.freqEnd === void 0 ? nyquist : request.freqEnd;
    const clamped = requestedEnd > nyquist;
    const freqEndTarget = clamped ? nyquist : requestedEnd;
    if (request.freqStart < 0) {
      throw new Error(`freq-start must not be negative, got ${request.freqStart}`);
    }
    if (request.freqStart >= freqEndTarget) {
      throw new Error(`freq-start (${request.freqStart}) must be below freq-end (${freqEndTarget})`);
    }
    const firstBin = Math.ceil(request.freqStart / binWidth);
    const lastBin = Math.min(fftSize / 2, Math.floor(freqEndTarget / binWidth));
    const columns = lastBin - firstBin + 1;
    if (columns < 1) {
      throw new Error(`The frequency range ${request.freqStart}–${freqEndTarget} Hz holds no whole bin at ${binWidth} Hz per bin; widen it or raise fft-size`);
    }
    return {
      sampleRate,
      fftSize,
      hopSize,
      frames,
      binWidth,
      firstBin,
      lastBin,
      columns,
      freqStart: firstBin * binWidth,
      freqEnd: lastBin * binWidth,
      clamped
    };
  }
  function analyseFrames(samples, plan, grid, scratch, from, to) {
    const { fftSize, hopSize, firstBin, columns } = plan;
    const { fft, window: window2, re, im } = scratch;
    for (let f = from; f < to; f++) {
      const offset = f * hopSize;
      for (let i = 0; i < fftSize; i++) {
        re[i] = samples[offset + i] * window2[i];
        im[i] = 0;
      }
      fft.forward(re, im);
      const row = f * columns;
      for (let k = 0; k < columns; k++) {
        const bin = firstBin + k;
        grid[row + k] = re[bin] * re[bin] + im[bin] * im[bin];
      }
    }
  }
  function makeScratch(plan) {
    const { fftSize } = plan;
    const window2 = new Float32Array(fftSize);
    for (let i = 0; i < fftSize; i++) {
      window2[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (fftSize - 1));
    }
    return {
      fft: createFFT(fftSize),
      window: window2,
      re: new Float32Array(fftSize),
      im: new Float32Array(fftSize)
    };
  }
  async function analyse(samples, plan, options = {}) {
    const sliceMs = options.sliceMs === void 0 ? 12 : options.sliceMs;
    const onProgress = options.onProgress || (() => {
    });
    const yieldToLoop = options.yieldToLoop || (() => new Promise((resolve) => setTimeout(resolve, 0)));
    const now = typeof performance !== "undefined" && performance.now ? () => performance.now() : () => Date.now();
    const grid = new Float32Array(plan.frames * plan.columns);
    const scratch = makeScratch(plan);
    const batch = Math.max(1, Math.round(4096 / plan.fftSize) * 8);
    let frame = 0;
    while (frame < plan.frames) {
      const sliceStart = now();
      do {
        const to = Math.min(plan.frames, frame + batch);
        analyseFrames(samples, plan, grid, scratch, frame, to);
        frame = to;
      } while (frame < plan.frames && now() - sliceStart < sliceMs);
      onProgress(frame / plan.frames);
      if (frame < plan.frames) {
        await yieldToLoop();
      }
    }
    return grid;
  }
  const painted = /* @__PURE__ */ new WeakMap();
  function rememberPaintedLevels(instance, levels, frames, columns, map) {
    painted.set(instance, { levels, frames, columns, map });
  }
  function paintedMap(instance) {
    const kept = painted.get(instance);
    return kept ? kept.map : "colour";
  }
  function repaintGram(instance, map) {
    const kept = painted.get(instance);
    if (!kept) {
      return false;
    }
    const url = paintGram(kept.levels, kept.frames, kept.columns, map);
    kept.map = map;
    instance.ui.spectrogramImage.setAttributeNS("http://www.w3.org/1999/xlink", "href", url);
    return true;
  }
  function averagedRowCount(frames, count) {
    return Math.ceil(frames / Math.max(1, Math.floor(count)));
  }
  function averageFrames(grid, frames, columns, count) {
    const n = Math.max(1, Math.floor(count));
    if (n === 1) {
      return { grid, frames };
    }
    const rows = averagedRowCount(frames, n);
    const out = new Float32Array(rows * columns);
    for (let r = 0; r < rows; r++) {
      const from = r * n;
      const to = Math.min(frames, from + n);
      const rowOut = r * columns;
      for (let f = from; f < to; f++) {
        const rowIn = f * columns;
        for (let k = 0; k < columns; k++) out[rowOut + k] += grid[rowIn + k];
      }
      const divisor = to - from;
      for (let k = 0; k < columns; k++) out[rowOut + k] /= divisor;
    }
    return { grid: out, frames: rows };
  }
  function renderBookmarks(instance, snapshot, flags, list, count) {
    const bookmarks = snapshot.bookmarks || [];
    const duration = snapshot.player.duration;
    count.textContent = `${bookmarks.length} saved`;
    count.disabled = bookmarks.length === 0;
    if (bookmarks.length === 0) {
      list.hidden = true;
      count.setAttribute("aria-expanded", "false");
    }
    flags.replaceChildren();
    list.replaceChildren();
    bookmarks.forEach((mark) => {
      const at = duration > 0 ? mark.time / duration * 100 : 0;
      const flag = document.createElement("button");
      flag.type = "button";
      flag.className = "gram-frame-transport-flag";
      flag.style.left = `${at}%`;
      flag.title = `Jump to ${formatTime(mark.time)}`;
      const plate = document.createElement("span");
      plate.className = "gram-frame-transport-flag-plate";
      plate.textContent = mark.label;
      const stem = document.createElement("span");
      stem.className = "gram-frame-transport-flag-stem";
      flag.appendChild(plate);
      flag.appendChild(stem);
      flag.addEventListener("click", () => {
        var _a;
        return (_a = instance.player) == null ? void 0 : _a.seek(mark.time);
      });
      flags.appendChild(flag);
      const row = document.createElement("div");
      row.className = "gram-frame-transport-saved-row";
      const jump = document.createElement("button");
      jump.type = "button";
      jump.className = "gram-frame-transport-saved-jump";
      jump.textContent = `${mark.label} · ${formatTime(mark.time)}`;
      jump.addEventListener("click", () => {
        var _a;
        return (_a = instance.player) == null ? void 0 : _a.seek(mark.time);
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "gram-frame-transport-saved-remove";
      remove.textContent = "×";
      remove.title = "Remove this bookmark";
      remove.addEventListener("click", () => removeBookmark(instance, mark.id));
      row.appendChild(jump);
      row.appendChild(remove);
      list.appendChild(row);
    });
  }
  const PLAYBACK_RATES = [[0.25, "0.25×"], [0.5, "0.5×"], [1, "1×"], [1.5, "1.5×"], [2, "2×"], [4, "4×"]];
  const ANNOUNCE_INTERVAL_MS = 5e3;
  function button(className, title, icon, text) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = `gram-frame-transport-btn ${className}`;
    el.title = title;
    el.setAttribute("aria-label", title);
    const glyph = createIcon(icon);
    if (glyph) {
      el.appendChild(glyph);
    } else if (text) {
      el.textContent = text;
    }
    return el;
  }
  function setGlyph(el, icon) {
    const glyph = createIcon(icon);
    const existing = el.querySelector("svg");
    if (glyph && existing) {
      existing.replaceWith(glyph);
    }
  }
  function createTransportBar(instance) {
    const controller = instance.player;
    if (!controller) {
      throw new Error("GramFrame: the transport bar needs a player");
    }
    const state = instance.state;
    const player = state.player;
    const bar = document.createElement("div");
    bar.className = "gram-frame-transport";
    bar.setAttribute("role", "group");
    bar.setAttribute("aria-label", "Playback controls");
    const restart = button("gram-frame-transport-restart", "Restart", "restart");
    const play = button("gram-frame-transport-play gram-frame-transport-primary", "Play", "play");
    const elapsed = document.createElement("span");
    elapsed.className = "gram-frame-transport-time";
    const seek = document.createElement("input");
    seek.type = "range";
    seek.className = "gram-frame-transport-seek";
    seek.min = "0";
    seek.max = String(player.duration);
    seek.step = "0.01";
    seek.value = "0";
    seek.title = "Seek";
    seek.setAttribute("aria-label", "Seek");
    const flags = document.createElement("div");
    flags.className = "gram-frame-transport-flags";
    const track = document.createElement("div");
    track.className = "gram-frame-transport-track";
    track.appendChild(seek);
    track.appendChild(flags);
    const duration = document.createElement("span");
    duration.className = "gram-frame-transport-duration";
    const divider = document.createElement("span");
    divider.className = "gram-frame-transport-divider";
    const bookmark = button("gram-frame-transport-bookmark", "Bookmark this moment (B)", "bookmark");
    const bookmarkWord = document.createElement("span");
    bookmarkWord.textContent = "Bookmark";
    bookmark.appendChild(bookmarkWord);
    const saved = document.createElement("button");
    saved.type = "button";
    saved.className = "gram-frame-transport-saved";
    saved.setAttribute("aria-haspopup", "true");
    saved.setAttribute("aria-expanded", "false");
    const savedList = document.createElement("div");
    savedList.className = "gram-frame-transport-saved-list";
    savedList.hidden = true;
    const loop = button("gram-frame-transport-loop", "Loop", void 0, "⟲");
    loop.setAttribute("aria-pressed", "false");
    const rateLabel = document.createElement("span");
    rateLabel.className = "gram-frame-transport-rate-label";
    rateLabel.textContent = "Rate";
    const playbackRate = document.createElement("select");
    playbackRate.className = "gram-frame-transport-playback-rate";
    playbackRate.title = "Playback rate";
    playbackRate.setAttribute("aria-label", "Playback rate");
    PLAYBACK_RATES.forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = label;
      if (value === 1) option.selected = true;
      playbackRate.appendChild(option);
    });
    const span = document.createElement("span");
    span.className = "gram-frame-transport-span";
    span.title = "Visible time span";
    const mute = button("gram-frame-transport-mute", "Mute", "volume");
    mute.setAttribute("aria-pressed", "false");
    const volume = document.createElement("input");
    volume.type = "range";
    volume.className = "gram-frame-transport-volume";
    volume.min = "0";
    volume.max = "1";
    volume.step = "0.01";
    volume.value = "1";
    volume.title = "Volume";
    volume.setAttribute("aria-label", "Volume");
    const status = document.createElement("span");
    status.className = "gram-frame-transport-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    const transportGroup = document.createElement("div");
    transportGroup.className = "gram-frame-transport-group";
    transportGroup.appendChild(restart);
    transportGroup.appendChild(play);
    const bookmarkGroup = document.createElement("div");
    bookmarkGroup.className = "gram-frame-transport-group gram-frame-transport-bookmarks";
    bookmarkGroup.appendChild(bookmark);
    bookmarkGroup.appendChild(saved);
    bookmarkGroup.appendChild(savedList);
    const outputGroup = document.createElement("div");
    outputGroup.className = "gram-frame-transport-group";
    outputGroup.appendChild(mute);
    outputGroup.appendChild(volume);
    [
      transportGroup,
      elapsed,
      track,
      duration,
      divider,
      bookmarkGroup,
      loop,
      rateLabel,
      playbackRate,
      span,
      outputGroup,
      status
    ].forEach((el) => bar.appendChild(el));
    bar.addEventListener("mousedown", () => setFocusedInstance(instance));
    play.addEventListener("click", () => {
      controller.toggle().catch((error) => {
        console.warn("GramFrame: playback could not start:", error instanceof Error ? error.message : String(error));
      });
    });
    restart.addEventListener("click", () => controller.restart());
    let scrubbing = false;
    seek.addEventListener("pointerdown", () => {
      scrubbing = true;
    });
    seek.addEventListener("pointerup", () => {
      scrubbing = false;
    });
    seek.addEventListener("pointercancel", () => {
      scrubbing = false;
    });
    seek.addEventListener("input", () => controller.seek(parseFloat(seek.value)));
    seek.addEventListener("change", () => {
      scrubbing = false;
      controller.seek(parseFloat(seek.value));
    });
    loop.addEventListener("click", () => controller.setLoop(!player.loop));
    playbackRate.addEventListener("change", () => controller.setPlaybackRate(parseFloat(playbackRate.value)));
    mute.addEventListener("click", () => controller.setMute(!player.muted));
    volume.addEventListener("input", () => controller.setVolume(parseFloat(volume.value)));
    bookmark.addEventListener("click", () => addBookmark(instance));
    saved.addEventListener("click", () => {
      savedList.hidden = !savedList.hidden;
      saved.setAttribute("aria-expanded", savedList.hidden ? "false" : "true");
    });
    document.addEventListener("mousedown", (event) => {
      const target = (
        /** @type {Node|null} */
        event.target
      );
      if (!savedList.hidden && target && !bookmarkGroup.contains(target)) {
        savedList.hidden = true;
        saved.setAttribute("aria-expanded", "false");
      }
    }, true);
    let announced = { playing: player.playing, at: 0 };
    const announce = (p) => {
      const now = Date.now();
      const changed = p.playing !== announced.playing;
      if (!changed && (!p.playing || now - announced.at < ANNOUNCE_INTERVAL_MS)) {
        return;
      }
      announced = { playing: p.playing, at: now };
      status.textContent = `${p.playing ? "Playing" : "Paused"} at ${formatTime(p.playhead)} of ${formatTime(p.duration)}`;
    };
    const reflect = (snapshot) => {
      const p = snapshot.player;
      setGlyph(play, p.playing ? "pause" : "play");
      play.title = p.playing ? "Pause" : "Play";
      play.setAttribute("aria-label", play.title);
      play.setAttribute("aria-pressed", p.playing ? "true" : "false");
      if (!scrubbing) {
        seek.max = String(p.duration);
        seek.value = String(p.playhead);
      }
      const played = p.duration > 0 ? p.playhead / p.duration * 100 : 0;
      seek.style.setProperty("--gf-played", `${played}%`);
      elapsed.textContent = formatTime(p.playhead);
      duration.textContent = formatTime(p.duration);
      const visibleSeconds = p.windowSeconds / snapshot.zoom.level;
      span.textContent = `${visibleSeconds.toFixed(1)} s span`;
      loop.setAttribute("aria-pressed", p.loop ? "true" : "false");
      playbackRate.value = String(p.playbackRate);
      mute.setAttribute("aria-pressed", p.muted ? "true" : "false");
      setGlyph(mute, p.muted ? "muted" : "volume");
      mute.title = p.muted ? "Unmute" : "Mute";
      mute.setAttribute("aria-label", mute.title);
      if (document.activeElement !== volume) {
        volume.value = String(p.volume);
      }
      renderBookmarks(instance, snapshot, flags, savedList, saved);
      announce(p);
    };
    reflect(state);
    instance.stateListeners.push(reflect);
    instance.ui.mainCell.appendChild(bar);
    return bar;
  }
  const DEFAULT_DISPLAY_RANGE = { floor: 0, ceiling: 1 };
  const MIN_DISPLAY_SPAN = 0.02;
  function settleDisplayRange(floor, ceiling, moved = "floor") {
    const lo = clamp01(Number.isFinite(floor) ? floor : 0);
    const hi = clamp01(Number.isFinite(ceiling) ? ceiling : 1);
    if (hi - lo >= MIN_DISPLAY_SPAN) {
      return { floor: lo, ceiling: hi };
    }
    if (moved === "floor") {
      const settledFloor = Math.min(lo, 1 - MIN_DISPLAY_SPAN);
      return { floor: settledFloor, ceiling: settledFloor + MIN_DISPLAY_SPAN };
    }
    const settledCeiling = Math.max(hi, MIN_DISPLAY_SPAN);
    return { floor: settledCeiling - MIN_DISPLAY_SPAN, ceiling: settledCeiling };
  }
  function isDefaultDisplayRange(range) {
    return range.floor === DEFAULT_DISPLAY_RANGE.floor && range.ceiling === DEFAULT_DISPLAY_RANGE.ceiling;
  }
  function displayTransfer(range, darkForLoud = false) {
    const { floor, ceiling } = settleDisplayRange(range.floor, range.ceiling);
    const slope = 1 / (ceiling - floor);
    return { slope, intercept: darkForLoud ? 1 - slope * (1 - floor) : -floor * slope };
  }
  function clamp01(value) {
    return Math.max(0, Math.min(1, value));
  }
  const SVG_NS = "http://www.w3.org/2000/svg";
  function applyDisplayRange(instance, range) {
    const image = instance.ui.spectrogramImage;
    if (!image) {
      return;
    }
    if (isDefaultDisplayRange(range)) {
      image.removeAttribute("filter");
      return;
    }
    const { slope, intercept } = displayTransfer(range, isDarkForLoud(paintedMap(instance)));
    const filter = ensureFilter(instance);
    filter.querySelectorAll("feComponentTransfer > *").forEach((func) => {
      func.setAttribute("slope", String(slope));
      func.setAttribute("intercept", String(intercept));
    });
    image.setAttribute("filter", `url(#${filter.getAttribute("id")})`);
  }
  function ensureFilter(instance) {
    const svg = instance.ui.svg;
    const existing = svg.querySelector("filter.gram-frame-display-filter");
    if (existing) {
      return (
        /** @type {SVGFilterElement} */
        existing
      );
    }
    const filter = document.createElementNS(SVG_NS, "filter");
    filter.setAttribute("class", "gram-frame-display-filter");
    filter.setAttribute("id", `gramDisplay-${instance.instanceId}`);
    filter.setAttribute("x", "0%");
    filter.setAttribute("y", "0%");
    filter.setAttribute("width", "100%");
    filter.setAttribute("height", "100%");
    filter.setAttribute("color-interpolation-filters", "sRGB");
    const transfer = document.createElementNS(SVG_NS, "feComponentTransfer");
    ["feFuncR", "feFuncG", "feFuncB"].forEach((name) => {
      const func = document.createElementNS(SVG_NS, name);
      func.setAttribute("type", "linear");
      func.setAttribute("slope", "1");
      func.setAttribute("intercept", "0");
      transfer.appendChild(func);
    });
    filter.appendChild(transfer);
    const defs = svg.querySelector("defs") || svg.insertBefore(document.createElementNS(SVG_NS, "defs"), svg.firstChild);
    defs.appendChild(filter);
    return filter;
  }
  function slider(className, label, value) {
    const wrap = document.createElement("label");
    wrap.className = `gram-frame-display-control ${className}`;
    const text = document.createElement("span");
    text.className = "gram-frame-display-label";
    text.textContent = label;
    const input = document.createElement("input");
    input.type = "range";
    input.min = "0";
    input.max = "1";
    input.step = "0.01";
    input.value = String(value);
    input.className = "gram-frame-display-slider";
    input.setAttribute("aria-label", `Contrast ${label.toLowerCase()}`);
    wrap.appendChild(text);
    wrap.appendChild(input);
    return { wrap, input };
  }
  function createDisplayRangeControls(instance, bar, display) {
    const group = document.createElement("div");
    group.className = "gram-frame-display-range";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Contrast");
    const floor = slider("gram-frame-display-floor", "Floor", display.floor);
    const ceiling = slider("gram-frame-display-ceiling", "Ceiling", display.ceiling);
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "gram-frame-transport-btn gram-frame-display-reset";
    reset.title = "Reset contrast";
    reset.setAttribute("aria-label", "Reset contrast");
    reset.textContent = "Reset";
    [floor.wrap, ceiling.wrap, reset].forEach((el) => group.appendChild(el));
    bar.appendChild(group);
    const setRange = (nextFloor, nextCeiling, moved) => {
      const settled = settleDisplayRange(nextFloor, nextCeiling, moved);
      display.floor = settled.floor;
      display.ceiling = settled.ceiling;
      floor.input.value = String(settled.floor);
      ceiling.input.value = String(settled.ceiling);
      applyDisplayRange(instance, display);
      dispatch(instance, { frame: true });
    };
    group.addEventListener("mousedown", () => setFocusedInstance(instance));
    floor.input.addEventListener("input", () => {
      setRange(parseFloat(floor.input.value), display.ceiling, "floor");
    });
    ceiling.input.addEventListener("input", () => {
      setRange(display.floor, parseFloat(ceiling.input.value), "ceiling");
    });
    reset.addEventListener("click", () => {
      setRange(DEFAULT_DISPLAY_RANGE.floor, DEFAULT_DISPLAY_RANGE.ceiling, "floor");
    });
    return group;
  }
  const LABELS = {
    colour: "Colour",
    grey: "Grey",
    inferno: "Inferno",
    magma: "Magma",
    viridis: "Viridis",
    plasma: "Plasma"
  };
  let groupCounter = 0;
  function createColourMapChoice(instance, bar, analysis, display) {
    const group = document.createElement("div");
    group.className = "gram-frame-colour-map";
    group.setAttribute("role", "radiogroup");
    group.setAttribute("aria-label", "Colour map");
    const name = `gram-frame-colour-map-${++groupCounter}`;
    COLOUR_MAPS.forEach((map) => {
      const label = document.createElement("label");
      label.className = "gram-frame-colour-map-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = name;
      input.value = map;
      input.checked = map === analysis.colourMap;
      const text = document.createElement("span");
      text.textContent = LABELS[map];
      label.appendChild(input);
      label.appendChild(text);
      group.appendChild(label);
      input.addEventListener("change", () => {
        if (!input.checked || analysis.colourMap === map) {
          return;
        }
        analysis.colourMap = map;
        repaintGram(instance, map);
        applyDisplayRange(instance, display);
        dispatch(instance);
      });
    });
    group.addEventListener("mousedown", () => setFocusedInstance(instance));
    bar.appendChild(group);
    return group;
  }
  class PlayerController {
    /**
     * @param {GramFrame} instance - The owning instance
     * @param {HTMLAudioElement} audio - The element to drive
     */
    constructor(instance, audio) {
      this.instance = instance;
      this.audio = audio;
      this.playerState = instance.state.player;
      this._listeners = [];
      this._onVisibility = null;
      this._bind();
    }
    /**
     * Mirror the element's events into state.
     */
    _bind() {
      const { audio } = this;
      const on = (type, handler) => {
        audio.addEventListener(type, handler);
        this._listeners.push({ type, handler });
      };
      on("play", () => {
        const player = this.playerState;
        player.playing = true;
        player.ended = false;
        updatePlayingClass(this.instance);
        startFollow(this.instance);
        dispatch(this.instance);
      });
      on("pause", () => {
        this.playerState.playing = false;
        updatePlayingClass(this.instance);
        stopFollow(this.instance);
        dispatch(this.instance);
      });
      on("ended", () => {
        const player = this.playerState;
        player.playing = false;
        player.ended = true;
        updatePlayingClass(this.instance);
        stopFollow(this.instance);
        dispatch(this.instance);
      });
      on("seeked", () => syncViewToPlayhead(this.instance));
      on("timeupdate", () => {
        if (this.playerState.playing) {
          syncViewToPlayhead(this.instance);
        }
      });
      on("volumechange", () => {
        const player = this.playerState;
        player.volume = audio.volume;
        player.muted = audio.muted;
        dispatch(this.instance);
      });
      on("ratechange", () => {
        this.playerState.playbackRate = audio.playbackRate;
        dispatch(this.instance);
      });
      if (typeof document !== "undefined") {
        this._onVisibility = () => {
          if (document.visibilityState === "visible" && this.playerState.playing) {
            syncViewToPlayhead(this.instance);
          }
        };
        document.addEventListener("visibilitychange", this._onVisibility);
      }
    }
    /**
     * Whether the gram is analysed and the transport may be used.
     * @returns {boolean} True once ready
     */
    isReady() {
      return this.playerState.ready;
    }
    /**
     * Start playback from the playhead.
     *
     * The view snaps to the playhead first (Story 4, AS-4): a paused analyst who
     * panned away resumes where the audio is, not where they were looking. The
     * element's promise is returned as-is, so an autoplay refusal
     * (`NotAllowedError`) rejects rather than failing silently (FR-023).
     * @returns {Promise<void>} Resolves when playback starts
     */
    play() {
      if (!this.isReady()) {
        return Promise.reject(new Error("GramFrame: the recording is still being analysed"));
      }
      this.playerState.ended = false;
      syncViewToPlayhead(this.instance);
      const result = this.audio.play();
      return result && typeof result.then === "function" ? result : Promise.resolve();
    }
    /**
     * Pause playback. The follow loop ends after one final sync.
     */
    pause() {
      this.audio.pause();
    }
    /**
     * Play if paused, pause if playing.
     * @returns {Promise<void>} The `play()` promise, or resolved when pausing
     */
    toggle() {
      if (this.audio.paused) {
        return this.play();
      }
      this.pause();
      return Promise.resolve();
    }
    /**
     * Move the playhead. Reveals rows up to the target and puts the view there,
     * without starting playback (spec edge case "seek while paused").
     * @param {number} seconds - Target time; clamped to the recording
     */
    seek(seconds) {
      if (!this.isReady()) {
        return;
      }
      const duration = this.playerState.duration;
      const target = Math.max(0, Math.min(duration, Number.isFinite(seconds) ? seconds : 0));
      this.playerState.ended = false;
      this.audio.currentTime = target;
      const player = this.playerState;
      player.playhead = target;
      syncViewToPlayhead(this.instance);
    }
    /**
     * Return to the start. Keeps playing if it was playing.
     */
    restart() {
      this.seek(0);
    }
    /**
     * @param {boolean} loop - Whether to restart at the end
     */
    setLoop(loop) {
      this.audio.loop = !!loop;
      this.playerState.loop = !!loop;
      dispatch(this.instance);
    }
    /**
     * @param {number} playbackRate - Playback speed; the gram is never re-analysed (FR-022)
     */
    setPlaybackRate(playbackRate) {
      if (Number.isFinite(playbackRate) && playbackRate > 0) {
        applyPreservesPitch(this.audio, this.playerState.preservesPitch);
        this.audio.playbackRate = playbackRate;
        this.playerState.playbackRate = playbackRate;
        dispatch(this.instance);
      }
    }
    /**
     * @param {number} volume - 0..1
     */
    setVolume(volume) {
      if (Number.isFinite(volume)) {
        const clamped = Math.max(0, Math.min(1, volume));
        this.audio.volume = clamped;
        this.playerState.volume = clamped;
        dispatch(this.instance);
      }
    }
    /**
     * @param {boolean} muted - Whether to silence output; the gram still scrolls (AS-5.5)
     */
    setMute(muted) {
      this.audio.muted = !!muted;
      this.playerState.muted = !!muted;
      dispatch(this.instance);
    }
    /**
     * Pause, detach every listener and drop the element.
     */
    destroy() {
      try {
        this.audio.pause();
      } catch (_e) {
      }
      stopFollow(this.instance);
      this._listeners.forEach(({ type, handler }) => this.audio.removeEventListener(type, handler));
      this._listeners = [];
      if (this._onVisibility) {
        document.removeEventListener("visibilitychange", this._onVisibility);
        this._onVisibility = null;
      }
      this.audio.removeAttribute("src");
      if (this.audio.parentNode) {
        this.audio.parentNode.removeChild(this.audio);
      }
    }
  }
  function applyPreservesPitch(audio, preserve) {
    const element = (
      /** @type {HTMLAudioElement & {mozPreservesPitch?: boolean, webkitPreservesPitch?: boolean}} */
      audio
    );
    element.preservesPitch = preserve;
    if ("mozPreservesPitch" in element) element.mozPreservesPitch = preserve;
    if ("webkitPreservesPitch" in element) element.webkitPreservesPitch = preserve;
  }
  function createTransport(instance) {
    const audio = document.createElement("audio");
    audio.className = "gram-frame-audio-element";
    audio.preload = "auto";
    audio.style.display = "none";
    instance.ui.container.appendChild(audio);
    const controller = new PlayerController(instance, audio);
    applyPreservesPitch(audio, controller.playerState.preservesPitch);
    audio.src = controller.playerState.source;
    instance.player = controller;
    return controller;
  }
  function createDegradedNote(degraded) {
    const note = document.createElement("div");
    note.className = "gram-frame-degraded-note";
    note.setAttribute("role", "note");
    note.textContent = `This recording is too long to render at ${degraded.parameter} ${degraded.requested}; it is drawn at ${degraded.parameter} ${degraded.used}.`;
    return note;
  }
  function setProgress(instance, fraction, stage) {
    instance.state.player.progress = fraction;
    if (instance.ui.mainCell) {
      instance.ui.mainCell.dataset.gramProgress = `${stage} ${Math.round(fraction * 100)}%`;
    }
  }
  function failAudioSetup(instance, error) {
    var _a, _b;
    const message = error instanceof Error ? error.message : String(error);
    console.error(`GramFrame: could not prepare the audio-sourced gram (${(_a = instance.configTable.querySelector("audio")) == null ? void 0 : _a.getAttribute("src")}): ${message}`, error);
    const container = instance.ui.container;
    const parent = container && container.parentNode;
    const next = container ? container.nextSibling : null;
    instance.destroy();
    const table = instance.configTable;
    if (parent) {
      parent.insertBefore(table, next);
      table.classList.add("gram-frame-config-error");
      const source = ((_b = table.querySelector("audio")) == null ? void 0 : _b.getAttribute("src")) || "";
      parent.insertBefore(createErrorIndicator(`Audio-sourced gram failed (${source}): ${message}`), table.nextSibling);
    }
  }
  function planFittingAnalysis(player, decoded) {
    const planAt = (hopSize) => planAnalysis({
      sampleRate: decoded.sampleRate,
      sampleCount: decoded.samples.length,
      fftSize: player.analysis.fftSize,
      hopSize,
      freqStart: player.analysis.freqStart,
      freqEnd: player.analysis.freqEnd
    });
    let plan = planAt(player.analysis.hopSize);
    if (plan.clamped) {
      console.warn(`GramFrame: freq-end ${player.analysis.freqEnd} Hz is above this recording's Nyquist frequency (${decoded.sampleRate / 2} Hz); clamped to ${plan.freqEnd} Hz`);
    }
    const rows = () => averagedRowCount(plan.frames, player.analysis.frameAverage);
    const degraded = fitGramSize(rows(), plan.columns, plan);
    if (degraded) {
      console.warn(`GramFrame: ${rows()} painted rows is above the render limit; ${degraded.parameter} raised from ${degraded.requested} to ${degraded.used}`);
      plan = planAt(degraded.used);
      player.analysis.hopSize = degraded.used;
      player.degraded = degraded;
    }
    checkGramSize(rows(), plan.columns, plan);
    return plan;
  }
  async function setupAudioSource(instance) {
    var _a;
    const state = instance.state;
    const player = state.player;
    const container = instance.ui.container;
    container.classList.add("gram-frame-audio", "gram-frame-analysing");
    setProgress(instance, 0, "Loading audio");
    try {
      const bytes = await loadAudioBytes(player.source);
      setProgress(instance, 0.1, "Decoding audio");
      await new Promise((resolve) => setTimeout(resolve, 0));
      const decoded = decodeWav(bytes);
      player.duration = decoded.duration;
      player.sampleRate = decoded.sampleRate;
      player.channels = decoded.channels;
      setProgress(instance, 0.2, "Analysing audio");
      const plan = planFittingAnalysis(player, decoded);
      const grid = await analyse(decoded.samples, plan, {
        onProgress: (fraction) => setProgress(instance, 0.2 + 0.7 * fraction, "Analysing audio")
      });
      setProgress(instance, 0.9, "Painting spectrogram");
      await new Promise((resolve) => setTimeout(resolve, 0));
      const averaged = averageFrames(grid, plan.frames, plan.columns, player.analysis.frameAverage);
      const levels = powerToLevels(averaged.grid, {
        normalisation: player.analysis.normalisation,
        windowBins: player.analysis.normalisationWindow === null ? void 0 : splitWindowBinsFor(player.analysis.normalisationWindow, plan.binWidth),
        frames: averaged.frames,
        columns: plan.columns,
        floorPercentile: player.analysis.levelFloor,
        ceilingPercentile: player.analysis.levelCeiling,
        levelSpan: player.analysis.levelSpan,
        levelScope: player.analysis.levelScope
      });
      const url = paintGram(levels, averaged.frames, plan.columns, player.analysis.colourMap);
      rememberPaintedLevels(instance, levels, averaged.frames, plan.columns, player.analysis.colourMap);
      if (!container.isConnected) {
        return;
      }
      const imageDetails = state.imageDetails;
      imageDetails.naturalWidth = plan.columns;
      imageDetails.naturalHeight = averaged.frames;
      imageDetails.renderWidth = PLAYER_RENDER_WIDTH;
      imageDetails.renderHeight = PLAYER_RENDER_HEIGHT;
      imageDetails.timeStretch = decoded.duration / player.windowSeconds;
      instance.ui.spectrogramImage.setAttributeNS("http://www.w3.org/1999/xlink", "href", url);
      state.config.timeMin = 0;
      state.config.timeMax = decoded.duration;
      state.config.freqMin = plan.freqStart;
      state.config.freqMax = plan.freqEnd;
      player.analysis.freqStart = plan.freqStart;
      player.analysis.freqEnd = plan.freqEnd;
      player.analysis.columns = plan.columns;
      player.analysis.frames = averaged.frames;
      player.playhead = 0;
      player.viewTop = Math.min(player.windowSeconds, decoded.duration);
      player.progress = 1;
      player.ready = true;
      createTransport(instance);
      const bar = createTransportBar(instance);
      createDisplayRangeControls(instance, bar, player.display);
      createColourMapChoice(instance, bar, player.analysis, player.display);
      if (player.degraded) {
        (_a = bar.parentElement) == null ? void 0 : _a.insertBefore(createDegradedNote(player.degraded), bar);
      }
      container.classList.remove("gram-frame-loading", "gram-frame-analysing");
      delete instance.ui.mainCell.dataset.gramProgress;
      updateSVGLayout(instance);
      createExpandToggle(instance);
      instance._restoreAnnotations();
      refreshPanels(instance);
      if (instance.featureRenderer) {
        instance.featureRenderer.renderAllPersistentFeatures();
      }
      instance._setupStorageSaveListener();
      dispatch(instance);
    } catch (error) {
      if (container.isConnected) {
        failAudioSetup(instance, error);
      }
    }
  }
  class GramFrame {
    /**
     * Every DOM element handle this component owns.
     *
     * Grouped rather than kept as 28 flat fields (spec 167, US5): they share a
     * lifetime — built during construction, torn down together — and reading
     * `instance.ui.svg` says which of the instance's concerns you are reaching
     * into, where `instance.svg` said only that you were reaching.
     * @type {GramFrameUI}
     */
    ui;
    /**
     * Selection, restyling and the transient pointer state behind them.
     * @type {GramFrameInteraction}
     */
    interaction = {
      setSelection: () => {
      },
      clearSelection: () => {
      },
      toggleSelection: () => {
      },
      isFeatureSelected: () => false,
      updateSelectionVisuals: () => {
      },
      applyColorToSelectedFeature: () => false,
      applySymbolToSelectedFeature: () => false,
      applyPinToSelectedFeature: () => false,
      applyLargeSymbolsToSelectedFeature: () => false,
      removeHarmonicSet: () => {
      },
      removeSidebandSet: () => {
      },
      // Replaced by the colour picker when it mounts; a no-op until then, so a
      // caller arriving early does nothing rather than throwing.
      syncStyleControls: () => {
      },
      _registeredListeners: [],
      _wheelPanHandler: null,
      _wheelPanLast: null
    };
    /**
     * How the component watches for size changes.
     * @type {GramFrameViewport}
     */
    viewport = { resizeObserver: null, _boundHandleResize: null };
    /**
     * Where this instance's annotations are saved, and under which context.
     * @type {GramFramePersistence}
     */
    persistence = { _storageInstanceIndex: 0, _isTrainerContext: false, _crossTabHandler: null };
    // Core properties
    /** @type {GramFrameState} */
    state;
    /** @type {HTMLTableElement} */
    configTable;
    /** @type {StateListener[]} */
    stateListeners;
    /** @type {string} */
    instanceId;
    // Mode system
    /** @type {Object<string, BaseMode>} */
    modes;
    /** @type {BaseMode} */
    currentMode;
    /** @type {FeatureRenderer} */
    featureRenderer;
    /**
     * The transport of an audio-sourced instance (spec 168), or null on an
     * image-backed one. A grouped sub-object like `ui` and `interaction`: the
     * audio element, its controller and the follow loop share one lifetime.
     * @type {PlayerController|null}
     */
    player = null;
    /**
     * Creates a new GramFrame instance
     * @param {HTMLTableElement} configTable - Configuration table element to replace
     */
    constructor(configTable) {
      this.configTable = configTable;
      if (!isBrowserSupported()) {
        showCompatibilityWarning(configTable);
        throw new Error("GramFrame: this browser is missing APIs the component requires. A compatibility warning has been shown in place of the component.");
      }
      this.state = createInitialState(ModeFactory.getModeInitialStates());
      this.state.showHarmonicPin = loadPinPreference();
      this.stateListeners = [];
      this.instanceId = "";
      this.persistence._storageInstanceIndex = document.querySelectorAll(".gram-frame-container").length;
      const detectedContext = describeUserContext();
      this.persistence._isTrainerContext = detectedContext.context === "trainer";
      const dom = setupSpectrogramComponents(this, configTable);
      dom.container.dataset.gfContext = detectedContext.context;
      console.info(
        `GramFrame: instance ${this.persistence._storageInstanceIndex} is on a ${detectedContext.context} page (${detectedContext.reason}) — ` + (this.persistence._isTrainerContext ? "annotations persist in localStorage" : "annotations are session-only and expire after 24 hours")
      );
      const layout = createUnifiedLayoutStructure(this, dom.readoutPanel, dom.modeCell);
      const initialModeUI = setupPersistentContainers(this, layout.modeColumn);
      this.ui = {
        container: dom.container,
        table: dom.table,
        modeRow: dom.modeRow,
        mainRow: dom.mainRow,
        readoutPanel: dom.readoutPanel,
        modeCell: dom.modeCell,
        mainCell: dom.mainCell,
        svg: dom.svg,
        spectrogramImage: dom.spectrogramImage,
        cursorGroup: dom.cursorGroup,
        axesGroup: dom.axesGroup,
        imageClipRect: dom.imageClipRect,
        cursorClipRect: dom.cursorClipRect,
        modeColumn: layout.modeColumn,
        guidanceColumn: layout.guidanceColumn,
        guidancePanel: layout.guidancePanel,
        guidanceTitle: layout.guidanceTitle,
        readoutColumn: layout.readoutColumn,
        kicker: layout.kicker,
        markersContainer: layout.markersContainer,
        harmonicsContainer: layout.harmonicsContainer,
        sidebandsContainer: layout.sidebandsContainer,
        timeLED: layout.timeLED,
        freqLED: layout.freqLED,
        speedLED: layout.speedLED,
        colorPicker: layout.colorPicker,
        modesContainer: initialModeUI.modesContainer,
        modeButtons: initialModeUI.modeButtons,
        commandButtons: initialModeUI.commandButtons,
        // Mounted later, or not at all: the harmonics and sidebands panels
        // arrive with their modes' UI, the expand toggle only for a landscape
        // image, and nothing assigns the mode/frequency-rate LEDs at all — every read of
        // them is guarded.
        harmonicPanel: null,
        sidebandPanel: null,
        expandToggleButton: null,
        modeLED: null,
        frequencyRateLED: null
      };
      setupSpectrogramIfAvailable(this);
      const { modes, featureRenderer } = initializeModeInfrastructure(this);
      this.modes = modes;
      this.featureRenderer = featureRenderer;
      this.currentMode = setupModeUI(this, modes, {
        analysis: layout.markersContainer,
        harmonics: layout.harmonicsContainer,
        sideband: layout.sidebandsContainer
      });
      const modeUI = updateModeUIWithCommands(this, initialModeUI, modes, this.currentMode, layout.modeColumn);
      this.ui.modesContainer = modeUI.modesContainer;
      this.ui.modeButtons = modeUI.modeButtons;
      this.ui.commandButtons = modeUI.commandButtons;
      const controls = setupAllEventListeners(this);
      this.interaction.removeHarmonicSet = controls.removeHarmonicSet;
      this.interaction.removeSidebandSet = controls.removeSidebandSet;
      this.interaction.setSelection = controls.setSelection;
      this.interaction.clearSelection = controls.clearSelection;
      this.interaction.toggleSelection = controls.toggleSelection;
      this.interaction.isFeatureSelected = controls.isFeatureSelected;
      this.interaction.updateSelectionVisuals = controls.updateSelectionVisuals;
      this.interaction.applyColorToSelectedFeature = controls.applyColorToSelectedFeature;
      this.interaction.applySymbolToSelectedFeature = controls.applySymbolToSelectedFeature;
      this.interaction.applyPinToSelectedFeature = controls.applyPinToSelectedFeature;
      this.interaction.applyLargeSymbolsToSelectedFeature = controls.applyLargeSymbolsToSelectedFeature;
      mountClearAllButton(this, () => this._clearGram());
      if (this.state.player.active) {
        setupAudioSource(this);
      } else {
        this._restoreAnnotations();
        refreshPanels(this);
        if (this.featureRenderer) {
          this.featureRenderer.renderAllPersistentFeatures();
        }
        this._setupStorageSaveListener();
        this._setupCrossTabListener();
      }
      dispatch(this);
    }
    /**
     * Set zoom level and center point.
     *
     * The one surviving instance-level zoom forwarder. `_zoomIn`, `_zoomOut` and
     * `_zoomReset` were deleted with their last caller when Pan mode's command
     * buttons started calling `core/viewport.js` directly — zoom has one seam,
     * and reaching it through an underscore-prefixed instance method was a second
     * one (spec 167, FR-007, AS-4.3). This remains because the Playwright helper
     * drives zoom through it from the page.
     * @param {number} level - Zoom level (1.0 = no zoom)
     * @param {number} centerX - Center X (0-1 normalized)
     * @param {number} centerY - Center Y (0-1 normalized)
     */
    _setZoom(level, centerX, centerY) {
      setZoom(this, level, centerX, centerY);
    }
    /**
     * Handle resize events
     */
    _handleResize() {
      handleResize(this);
    }
    /**
     * Cancel any feature drag in progress, through the engine — the single owner
     * of the drag record. Writing `state.drag` directly instead left the engine
     * saying *dragging* while the projection said *idle*, and the next publish
     * resurrected the stale drag (M4). One place now, not two (issue #268).
     * @returns {void}
     */
    _cancelAllDrags() {
      Object.values(this.modes || {}).forEach((modeInstance) => {
        if (modeInstance && modeInstance.dragHandler) {
          modeInstance.dragHandler.cancelDrag();
        }
      });
    }
    /**
     * Clear all annotations from state and storage
     */
    _clearGram() {
      var _a, _b, _c;
      this._cancelAllDrags();
      if (this.interaction._wheelPanHandler) {
        this.interaction._wheelPanHandler.cancelDrag();
      }
      if (this.interaction.clearSelection) {
        this.interaction.clearSelection();
      }
      (((_a = this.state.analysis) == null ? void 0 : _a.markers) || []).forEach((marker) => recordDeletion(this, "markers", marker.id));
      (((_b = this.state.harmonics) == null ? void 0 : _b.harmonicSets) || []).forEach((set) => recordDeletion(this, "harmonicSets", set.id));
      (((_c = this.state.sidebands) == null ? void 0 : _c.sidebandSets) || []).forEach((set) => recordDeletion(this, "sidebandSets", set.id));
      recordDopplerDeletion(this);
      const fresh = createInitialState(ModeFactory.getModeInitialStates());
      this.state.analysis = fresh.analysis;
      this.state.harmonics = fresh.harmonics;
      this.state.sidebands = fresh.sidebands;
      this.state.doppler = fresh.doppler;
      this.state.cursors = fresh.cursors;
      if (clearAnnotations(this.persistence._storageInstanceIndex, this._storageContext())) {
        clearStorageWarning(this);
      } else {
        showStorageWarning(this, "Saved annotations could not be removed from browser storage — they may reappear when this page is reloaded.");
      }
      if (this.featureRenderer) {
        this.featureRenderer.renderAllPersistentFeatures();
      }
      if (this.currentMode && typeof this.currentMode.activate === "function") {
        this.currentMode.cleanup();
        this.currentMode.activate();
      }
      refreshPanels(this);
      updateLEDDisplays(this, this.state);
      if (this.ui.speedLED) {
        setLEDValue(this.ui.speedLED, "0.0");
      }
      dispatch(this);
    }
    /**
     * The storage context this instance detected at construction, in the form
     * the storage module takes. Passed into every storage call so save and load
     * can never disagree about which storage to use (M3).
     * @returns {'trainer' | 'student'} This instance's storage context
     */
    _storageContext() {
      return this.persistence._isTrainerContext ? "trainer" : "student";
    }
    /**
     * Restore saved annotations from browser storage into state.
     *
     * A load that does not restore what was stored is reported to the analyst
     * through the same banner a failed *save* uses (R9-01). The two paths were
     * asymmetric: a quota-full save said so in a sentence, while a damaged,
     * superseded or wrongly-fingerprinted record produced an empty gram and a
     * console line nobody reads — and the next save then overwrote the record
     * for good. The banner clears itself as soon as a save succeeds, which is
     * the point at which the analyst has knowingly started again.
     */
    _restoreAnnotations() {
      const { annotations: saved, outcome, dropped } = loadAnnotations(
        this.persistence._storageInstanceIndex,
        this._storageContext(),
        // Refuse records fingerprinted for a different gram (BH-6, BH-23)
        buildGramFingerprint(this.state)
      );
      const message = describeLoadOutcome(outcome, dropped);
      if (message) {
        showStorageWarning(this, message);
      }
      if (!saved) return;
      markAnnotationsChanged(this);
      if (saved.tombstones) {
        this.state.tombstones = saved.tombstones;
      }
      if (saved.analysis && Array.isArray(saved.analysis.markers)) {
        this.state.analysis.markers = saved.analysis.markers.map((m) => ({
          ...m,
          symbol: m.symbol || "cross"
        }));
      }
      if (saved.harmonics && Array.isArray(saved.harmonics.harmonicSets)) {
        this.state.harmonics.harmonicSets = saved.harmonics.harmonicSets.map((hs) => ({
          ...hs,
          symbol: hs.symbol || "cross",
          // Records saved before the pin toggle have no `showPin`; those sets were
          // drawn with pins, so they restore as pinned.
          showPin: hs.showPin !== false
        }));
      }
      if (saved.sidebands && Array.isArray(saved.sidebands.sidebandSets)) {
        this.state.sidebands.sidebandSets = saved.sidebands.sidebandSets.map((sb) => ({
          ...sb,
          symbol: sb.symbol || "cross",
          showPin: sb.showPin !== false
        }));
      }
      if (saved.doppler) {
        this.state.doppler.fPlus = saved.doppler.fPlus || null;
        this.state.doppler.fMinus = saved.doppler.fMinus || null;
        this.state.doppler.fZero = saved.doppler.fZero || null;
        if (saved.doppler.color) {
          this.state.doppler.color = saved.doppler.color;
        }
        this._refreshDopplerSpeed();
      }
    }
    /**
     * Recompute the doppler speed from the curve now in state, and show it.
     *
     * Speed is derived, not persisted, so every path that puts a curve into
     * state without a drag has to do this: a restored curve otherwise read 0.0
     * until a marker was nudged (BH-15). Guarded against f₀ = 0, which divides
     * to Infinity (BH-8). Shared by the restore path and the cross-tab merge,
     * which have exactly the same problem.
     * @returns {void}
     */
    _refreshDopplerSpeed() {
      const { fPlus, fMinus, fZero } = this.state.doppler;
      if (!fPlus || !fMinus || !fZero) {
        this.state.doppler.speed = null;
        return;
      }
      const speed = calculateDopplerSpeed(fPlus, fMinus, fZero);
      this.state.doppler.speed = Number.isFinite(speed) ? speed : null;
      if (this.ui.speedLED && this.state.doppler.speed !== null) {
        setLEDValue(this.ui.speedLED, (this.state.doppler.speed * MS_TO_KNOTS).toFixed(1));
      }
    }
    /**
     * Adopt another tab's save into this tab, live.
     *
     * The `storage` event fires in every *other* tab of the origin when one
     * writes, so this is how the tab that did not save learns about it. Without
     * it, merging on save would still keep both tabs' work in the record -- the
     * data would be safe -- but each screen would show only its own half until
     * someone reloaded, which reads exactly like the loss it replaced.
     *
     * The merge itself is the same one the save path uses, so the two cannot
     * disagree about what a union means. What arrives is treated as another
     * tab's record, not as authority: a foreign gram, an unreadable payload or a
     * different schema version is ignored here for the same reasons the load
     * path refuses it.
     * @returns {void}
     */
    _setupCrossTabListener() {
      const key = buildStorageKey(this.persistence._storageInstanceIndex);
      const onStorage = (event) => {
        if (!event.key || event.key !== key || !event.newValue) {
          return;
        }
        this._adoptForeignRecord(event.newValue);
      };
      window.addEventListener("storage", onStorage);
      this.persistence._crossTabHandler = onStorage;
    }
    /**
     * Merge a record another tab just wrote into this tab's live state.
     * @param {string} raw - The record as stored
     * @returns {boolean} True if anything changed on screen
     */
    _adoptForeignRecord(raw) {
      const merged = mergeForeignRecord(raw, this.state);
      if (!merged) {
        return false;
      }
      const before = JSON.stringify(snapshotAnnotations(this.state));
      this._applyMergedAnnotations(merged);
      if (JSON.stringify(snapshotAnnotations(this.state)) === before) {
        return false;
      }
      if (this.state.selection && this.state.selection.selectedId && !this._selectionStillExists()) {
        this.interaction.clearSelection();
      }
      markAnnotationsChanged(this);
      refreshPanels(this);
      if (this.featureRenderer) {
        this.featureRenderer.renderAllPersistentFeatures();
      }
      dispatch(this);
      return true;
    }
    /**
     * Replace this instance's annotations with a merged record's.
     * @param {StoredAnnotations} merged - The merged record
     * @returns {void}
     */
    _applyMergedAnnotations(merged) {
      var _a, _b, _c;
      this.state.analysis.markers = (((_a = merged.analysis) == null ? void 0 : _a.markers) || []).map((m) => ({
        ...m,
        symbol: m.symbol || "cross"
      }));
      this.state.harmonics.harmonicSets = (((_b = merged.harmonics) == null ? void 0 : _b.harmonicSets) || []).map((hs) => ({
        ...hs,
        symbol: hs.symbol || "cross",
        showPin: hs.showPin !== false
      }));
      this.state.sidebands.sidebandSets = (((_c = merged.sidebands) == null ? void 0 : _c.sidebandSets) || []).map((sb) => ({
        ...sb,
        symbol: sb.symbol || "cross",
        showPin: sb.showPin !== false
      }));
      const doppler = merged.doppler || { fPlus: null, fMinus: null, fZero: null, color: null };
      this.state.doppler.fPlus = doppler.fPlus || null;
      this.state.doppler.fMinus = doppler.fMinus || null;
      this.state.doppler.fZero = doppler.fZero || null;
      this.state.doppler.color = doppler.color || null;
      this._refreshDopplerSpeed();
      if (merged.tombstones) {
        this.state.tombstones = merged.tombstones;
      }
    }
    /**
     * Whether the current selection still names a feature that exists.
     * @returns {boolean} True when the selection is still valid
     */
    _selectionStillExists() {
      const { selectedType, selectedId } = this.state.selection || {};
      if (!selectedType || !selectedId) {
        return true;
      }
      const family = selectedType === "marker" ? this.state.analysis.markers || [] : selectedType === "harmonicSet" ? this.state.harmonics.harmonicSets || [] : this.state.sidebands.sidebandSets || [];
      return family.some((feature) => feature.id === selectedId);
    }
    /**
     * Set up a state listener that saves annotations on relevant state changes
     */
    _setupStorageSaveListener() {
      const computeSignature = (state) => {
        const doppler = state.doppler || {};
        return [
          state.annotationRevision || 0,
          state.analysis && state.analysis.markers ? state.analysis.markers.length : 0,
          state.harmonics && state.harmonics.harmonicSets ? state.harmonics.harmonicSets.length : 0,
          state.sidebands && state.sidebands.sidebandSets ? state.sidebands.sidebandSets.length : 0,
          doppler.fPlus ? `${doppler.fPlus.time}:${doppler.fPlus.freq}` : "-",
          doppler.fMinus ? `${doppler.fMinus.time}:${doppler.fMinus.freq}` : "-",
          doppler.fZero ? `${doppler.fZero.time}:${doppler.fZero.freq}` : "-",
          doppler.color || "-"
        ].join("|");
      };
      let lastSignature = computeSignature(this.state);
      let lastWarnedSignature = "";
      this.stateListeners.push((state) => {
        if (state.drag && state.drag.active) {
          return;
        }
        const signature = computeSignature(state);
        if (signature !== lastSignature) {
          if (saveAnnotations(this.state, this.persistence._storageInstanceIndex, this._storageContext())) {
            lastSignature = signature;
            clearStorageWarning(this);
          } else if (hasPersistableAnnotations(state) && signature !== lastWarnedSignature) {
            lastWarnedSignature = signature;
            showStorageWarning(this, "Annotations could not be saved — they will be lost when this page is reloaded.");
          }
        }
      });
    }
    /**
     * Broadcast this instance's state to its listeners.
     *
     * A test seam, like `_setZoom`: the Playwright suite drives notifications
     * through it from the page. Everything in `src/` — including the drag
     * engine, since ADR-014 broke the state ⇄ modes cycle — calls `dispatch`
     * directly.
     */
    notifyStateListeners() {
      dispatch(this);
    }
    /**
     * Destroy the component and clean up resources
     */
    destroy() {
      flushDispatch(this);
      Object.values(this.modes || {}).forEach((modeInstance) => {
        if (modeInstance && typeof modeInstance.cleanup === "function") {
          modeInstance.cleanup();
        }
      });
      if (this.currentMode && typeof this.currentMode.deactivate === "function") {
        this.currentMode.deactivate();
      }
      cleanupEventListeners(this);
      cleanupKeyboardControl(this);
      if (this.persistence._crossTabHandler) {
        window.removeEventListener("storage", this.persistence._crossTabHandler);
        this.persistence._crossTabHandler = null;
      }
      if (this.player) {
        this.player.destroy();
        this.player = null;
      }
      if (this.ui.container && this.ui.container.parentNode) {
        this.ui.container.parentNode.removeChild(this.ui.container);
      }
    }
    /**
     * Switch between analysis modes
     * @param {ModeType} mode - Target mode
     */
    _switchMode(mode) {
      this.state.previousMode = this.state.mode;
      this.state.mode = mode;
      this._cancelAllDrags();
      if (this.state.selection && this.state.selection.selectedType && this.interaction.clearSelection) {
        this.interaction.clearSelection();
      }
      if (this.ui.modeButtons) {
        Object.keys(this.ui.modeButtons).forEach((m) => {
          const button2 = this.ui.modeButtons[m];
          if (button2) {
            if (m === mode) {
              button2.classList.add("active");
            } else {
              button2.classList.remove("active");
            }
          }
        });
      }
      if (this.ui.container) {
        ModeFactory.getAvailableModes().forEach((modeName) => {
          this.ui.container.classList.remove(`gram-frame-${modeName}-mode`);
        });
        this.ui.container.classList.add(`gram-frame-${mode}-mode`);
      }
      if (this.currentMode) {
        this.currentMode.cleanup();
        this.currentMode.deactivate();
      }
      this.currentMode = this.modes[mode];
      this.currentMode.activate();
      showGuidanceForMode(this, this.currentMode);
      this.currentMode.updateLEDs(this.state.cursorPosition);
      updateLEDDisplays(this, this.state);
      if (this.ui.modeLED) {
        setLEDValue(this.ui.modeLED, getModeDisplayName(mode));
      }
      refreshPanels(this);
      if (this.featureRenderer) {
        this.featureRenderer.renderAllPersistentFeatures();
      }
      dispatch(this);
    }
  }
  const GramFrameAPI = createGramFrameAPI(GramFrame);
  const bootstrap = () => {
    GramFrameAPI.init();
    const stateDisplay = document.getElementById("state-display");
    if (stateDisplay) {
      GramFrameAPI.addStateListener(
        /** @param {any} state */
        (state) => {
          stateDisplay.textContent = JSON.stringify(state, null, 2);
        }
      );
    }
  };
  window.GramFrame = GramFrameAPI;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();
