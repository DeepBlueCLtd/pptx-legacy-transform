# Open a WAV gram's .glc in the replay tool (issue #199)

A WAV gram page links to its `.glc` config, which names the `.wav` beside it.
In the PowerPoint decks that link launched the legacy replay tool. In a browser
it just shows the `.glc` as text: a browser never hands a `file://` link to a
desktop application. Downloading it is no answer either — the `.glc` names its
`.wav` relative to *itself*, so a copy in Downloads points at nothing.

The `.glc` must be opened **where it is published**, by its full Windows path.

## What the page does

`resources/glc-launch.js` (loaded on topic pages by
`page-templates-fragments/libraries/glc-launch.xml`, bound to
`webhelp.fragment.after.topic.content`) finds every `.glc` link inside a
`wav-stage` section and, **only when the page was opened from a drive or file
share** (`file://`):

1. rewrites the link to `glc:<full path>` (percent-encoded), e.g.
   `Z:\aaac\published\student\main\week-1\gram-03\lofar-2-loop-1.glc`;
2. adds a **Copy path** button and shows the path beneath the link.

Served over `http(s)` there is no Windows path to offer, so the link is left
as published. The published pages must therefore be opened from a **mapped
drive** (or a share) — which is also what the `.wav` lookup needs.

## Per-PC setup (once per student PC)

The `glc:` link needs a handler on the PC. Files are in `client/`:

| File | What it is |
| --- | --- |
| `glc-launch.ps1` | Decodes the link and opens the `.glc` with its associated app (the replay tool). Refuses anything that is not an existing `.glc` file. |
| `glc-protocol.reg` | Registers `glc:` for the **current user** (no admin rights) to run the script above. |

1. Copy `glc-launch.ps1` to `C:\aaac\glc-launch.ps1`. (Another folder is fine;
   then edit the path in `glc-protocol.reg` first, doubling every backslash.)
2. Double-click `glc-protocol.reg` and accept the prompt.
3. Make sure `.glc` files open with the replay tool when double-clicked in
   Explorer (they already do on a PC that runs the PowerPoint decks).
4. Open a WAV gram page from the mapped drive and click **WAV N**. The browser
   asks once whether to open the link with Windows PowerShell — tick *Always
   allow* and accept.

If group policy blocks PowerShell scripts outright, the link will do nothing;
use the fallback below.

## Fallback: no handler installed

Click **Copy path**, press **Win+R**, paste, Enter. Windows opens the `.glc`
from its published location with the replay tool, exactly as double-clicking
it in Explorer would.

## Removing the handler

Delete the registry key `HKEY_CURRENT_USER\Software\Classes\glc` and the script.

`client/` is PC-side install material, not template payload: `theme/sync.py`
does not copy it into `theme/pptx-transform/`.
