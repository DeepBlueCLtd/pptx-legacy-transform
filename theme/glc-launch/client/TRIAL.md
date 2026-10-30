# Trial plan: opening grams in the legacy replay tool (issue #199)

We will trial the issue #199 fix on a VM, then a candidate PC, to prove a WAV
gram link opens its `.glc` in the legacy replay tool before Group Policy
rollout. Deployment detail is in [../README.md](../README.md).

## How it works

A browser never hands a `file://` link to a desktop app, so the published link
is turned into a custom `glc:` link that Windows routes to a small handler
script.

1. The student opens a gram page from a mapped drive (`file://`).
2. `../resources/glc-launch.js` (in the Oxygen template) rewrites each **WAV N**
   link to `glc:` plus the `.glc`'s full, percent-encoded Windows path, and adds
   a **Copy path** button.
3. The click goes to Windows, which runs the registered handler for `glc:`.
4. `glc-launch.ps1` (this folder) decodes the path, refuses anything that is not an
   existing `.glc`, and opens the file in place.
5. The existing `.glc` file association starts the replay tool, which finds the
   `.wav` beside the `.glc`.

No code changes are needed: the script, `.reg` file and template wiring are all
on `main` (PR #201, docs updated in #202).

## Trial stages

Each stage removes one unknown; move on only when the previous stage passes.

| Stage | Where | Test page | What it proves |
| --- | --- | --- | --- |
| A | Local VM, outside the domain | Plain `.html` with hand-written `glc:` links, opened from `file://` | Registry entry, script and file association work |
| B | Candidate PC (set up by the maintainer) | Same plain `.html` | Same chain under that PC's policies and with the real replay tool |
| C | Candidate PC | A gram page freshly published by Oxygen with the current template, opened from a mapped drive | The page script works out the correct path |

On a VM without the replay tool, associate `.glc` with Notepad: Notepad opening
the `.glc` proves the chain, but not that the `.wav` loads.

For stage C no Oxygen run is needed: the committed builds under
`demo/oxygen-sample/published/` already load `glc-launch.js`. Copy
`published/` to a mapped drive (a `subst` drive letter works too) and open
`instructor/main/week-1/gram-03/gram_03.html` from there. The gh-pages copy
cannot be used: it loads the script, but over `https` the script deliberately
does nothing.

**The sample data opens the replay tool but displays nothing.** The committed
corpus is sanitised: its `.glc` files are stripped down (no `channel`,
`replay_speed` or `displays`, so they fail the GLC schema that ships with the
replay tool) and its `.wav` files are 0.1 s stubs. That proves the launch chain,
not the replay. To check that "the `.wav` loads", use a known-good pair: the
replay tool's own default configuration file with a
`<data_source><filename>good.wav</filename>` element added as its first child,
beside a WAV of at least a few seconds (steady tones show as clear lines).

## Setup steps

The trial uses the per-user route (`glc-protocol.reg`, this folder): no admin rights,
and removed with one command.

1. **Check for a name clash.** In `cmd`, run `assoc .glc`. Any answer other
   than `.glc=glc` is fine. If it is `.glc=glc`, stop: the `.reg` would
   overwrite how `.glc` files open.
   If it answers *File association not found*, `.glc` files do not open with
   the replay tool yet; associate them for the current user first, under a
   ProgID that is **anything but `glc`** (`HKCU\Software\Classes\glc` is the
   URL-scheme key the next steps create, so a `.glc=glc` association would
   collide with it). The replay tool takes the `.glc` path as its argument:

   ```bat
   reg add "HKCU\Software\Classes\.glc" /ve /d "ReplayTool.glc" /f
   reg add "HKCU\Software\Classes\ReplayTool.glc" /ve /d "Replay tool configuration" /f
   reg add "HKCU\Software\Classes\ReplayTool.glc\shell\open\command" /ve /d "\"<replay tool>.exe\" \"%1\"" /f
   ```

   Replace `<replay tool>.exe` with the tool's full path. Check it by
   double-clicking a `.glc` in Explorer before going on.
2. **Copy the script** from this folder to `C:\aaac\glc-launch.ps1`. For another
   folder, edit the last line of the `.reg`, doubling every backslash.
3. **Import the handler.** Double-click `glc-protocol.reg`. It creates
   `HKCU\Software\Classes\glc`, whose open command runs PowerShell with
   `-ExecutionPolicy Bypass` on the script.
4. **Put a test `.glc` and its `.wav` together on a mapped drive** (e.g.
   `net use Z: \\host\share`), mirroring production.
5. **Make the test page:** a plain `.html` with links of the form `glc:` + the
   encoded full path, plus one link to a non-`.glc` file as a negative test:

   ```html
   <a href="glc:Z%3A%5Caaac%5Ctrial%5Cx.glc">Encoded, as the real page sends it</a>
   <a href="glc:C%3A%5CWindows%5Cnotepad.exe">Must be refused (not a .glc)</a>
   ```

If `.reg` files are blocked, the same keys can be added from `cmd`:

```bat
reg add "HKCU\Software\Classes\glc" /ve /d "URL:Gram replay link" /f
reg add "HKCU\Software\Classes\glc" /v "URL Protocol" /d "" /f
reg add "HKCU\Software\Classes\glc\shell\open\command" /ve /d "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File \"C:\aaac\glc-launch.ps1\" \"%1\"" /f
```

## Checks

Test the handler without a browser first, so a failure can be pinned on
Windows or on the browser.

| Check | How | Pass | If it fails |
| --- | --- | --- | --- |
| Handler alone | Win+R, paste a `glc:` link, Enter | Replay tool opens with the `.wav` loaded | Nothing happens: execution policy is likely blocking the script; run `Get-ExecutionPolicy -List`. A warning box: wrong path, shown in the box |
| From the browser | Open the test `.html` from `file://`, click the link | Browser asks "Open Windows PowerShell?"; replay tool opens | Note whether an "Always allow" option is offered for a `file://` page |
| Negative test | Click the non-`.glc` link | Script refuses with a warning box | Stop the trial: the safety check is not working |
| Real page (stage C) | Click **WAV N** on a freshly published gram page | Replay tool opens; **Copy path** shows the full path | Compare the path shown with the file's real location |

Record the `assoc .glc` result and the outcome of each check on issue #199.

## Risks and open questions

- **A VM pass does not guarantee a domain pass.** Group Policy can override
  `-ExecutionPolicy Bypass`; rollout uses HKLM, a signed script under
  `C:\Program Files\AAAC\`, and no Bypass.
- **Browser prompt.** Edge offers *Always allow* on the "Open Windows
  PowerShell?" prompt for a `file://` page (2026-10-30 result), so a student is
  asked once, not on every click. Still unknown: whether the
  `AutoLaunchProtocolsFromOrigins` policy accepts `file://` as an origin, to
  remove even that first prompt.
- **PowerShell may be blocked outright.** If so, reconsider the handler (e.g. a
  `.cmd` adapter) rather than the page script.
- **Accepted risk:** any page or document can send a `glc:` link; the script
  limits this to opening existing `.glc` files, in any folder.
- **Fallback** with no handler: **Copy path**, Win+R, paste, Enter.

## Results

**2026-10-30, stand-alone Windows 11 PC, Edge, the real replay tool run from a
network share** (stages A and B in one: real tool, but no domain policy), using
the per-user route. `assoc .glc` reported no association, so one was added as in
setup step 1.

| Check | Outcome |
| --- | --- |
| Replay tool from `cmd`, `.glc` path as argument | Pass: opens the gram with its `.wav` |
| Handler alone (Win+R) | Pass |
| From the browser | Pass: "Open Windows PowerShell?" asked once; *Always allow* offered for a `file://` page; no prompt after that |
| Negative test | Not recorded; repeat on the domain PC |
| Real page (stage C) | Pass, against a local copy of the committed `demo/oxygen-sample/published/` build: **Copy path** showed the right path and **WAV 1** opened the replay tool. The display was blank, as expected for the sanitised sample data (see *Trial stages*) |

Still to do: the domain PC under Group Policy (HKLM, signed script, no
Bypass).

## Diagnostics

**The replay tool opens but shows nothing.** Validate the `.glc` against the
GLC schema (`.xsd`) installed alongside the replay tool. The `.wav` must also be
long enough to fill at least one FFT.

```powershell
$set = New-Object System.Xml.Schema.XmlSchemaSet
[void]$set.Add($null, '<replay tool folder>\<GLC schema>.xsd')
$st = New-Object System.Xml.XmlReaderSettings
$st.ValidationType = 'Schema'; $st.Schemas = $set
$st.add_ValidationEventHandler({ param($s, $e) $e.Message })
$r = [System.Xml.XmlReader]::Create('Z:\path\to\gram.glc', $st)
while ($r.Read()) {}; $r.Close()   # prints one line per schema error
```

## Rollback

One command removes the trial handler; then delete `C:\aaac\glc-launch.ps1`.

```bat
reg delete "HKCU\Software\Classes\glc" /f
```

If setup step 1 added a `.glc` association, remove it too:

```bat
reg delete "HKCU\Software\Classes\.glc" /f
reg delete "HKCU\Software\Classes\ReplayTool.glc" /f
```
