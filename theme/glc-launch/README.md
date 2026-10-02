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

## Deployment: Group Policy (the approved route)

The `glc:` link needs a handler on each student PC. The approved route
(decision recorded on issue #199) is for the **system administrator to deploy
it centrally by Group Policy** — machine-wide, admin-owned, and removable in
one place. The handler script is `client/glc-launch.ps1`: it decodes the link
and opens the `.glc` with its associated app (the replay tool), refusing
anything that is not an existing `.glc` file. By decision, it does **not**
restrict which folder the `.glc` may be in.

Group Policy Preferences, targeted at the student PCs (security group or OU,
via item-level targeting):

| GPP item | Setting |
| --- | --- |
| **Registry** (Computer Configuration → Preferences → Windows Settings → Registry) | `HKLM\SOFTWARE\Classes\glc` — default value `URL:Gram replay link`; string value `URL Protocol`, empty |
| **Registry** | `HKLM\SOFTWARE\Classes\glc\shell\open\command` — default value `powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -File "C:\Program Files\AAAC\glc-launch.ps1" "%1"` |
| **Files** | `glc-launch.ps1` → `C:\Program Files\AAAC\glc-launch.ps1` (admin-owned, read-only to students) |

Notes for the administrator:

- **Execution policy.** An execution policy set by Group Policy overrides any
  `-ExecutionPolicy` switch on the command line, so the command above carries
  none. Permit the script by **signing it** with the domain code-signing
  certificate (preferred), or by an AppLocker/WDAC rule for its path.
- **Browser prompt.** Edge/Chrome ask "Open Windows PowerShell?" on each click
  unless pre-approved. The `AutoLaunchProtocolsFromOrigins` browser policy can
  pre-approve `glc`; whether it accepts `file://` pages as an origin needs
  testing on one PC first. Otherwise students tick *Always allow* once.
- **Association.** `.glc` files must already open with the replay tool when
  double-clicked in Explorer (they do on a PC that runs the PowerPoint decks).
- **Check.** Open a WAV gram page from the mapped drive and click **WAV N**.
  If the script is blocked by policy the link does nothing — use the fallback
  below.

The accepted residual risks (any page or document can send a `glc:` link; the
caller chooses which `.glc` opens, including one on another machine's share)
are recorded on issue #199.

### Stand-alone PC (outside the domain only)

`client/glc-protocol.reg` registers the same handler for the **current user**
(HKCU, no admin rights), pointing at `C:\aaac\glc-launch.ps1`, and passes
`-ExecutionPolicy Bypass` because a stand-alone PC has no policy permitting the
script. Copy the script there (or edit the path in the `.reg`, doubling every
backslash), then double-click the `.reg`. Not for domain PCs: use Group Policy.

## Fallback: no handler installed

Click **Copy path**, press **Win+R**, paste, Enter. Windows opens the `.glc`
from its published location with the replay tool, exactly as double-clicking
it in Explorer would.

## Removing the handler

- **Group Policy:** remove the GPP items, or set their action to *Delete*; the
  next policy refresh removes the key and the script everywhere.
- **Stand-alone PC:** delete `HKEY_CURRENT_USER\Software\Classes\glc` and the
  script.

`client/` is PC-side install material, not template payload: `theme/sync.py`
does not copy it into `theme/pptx-transform/`.
