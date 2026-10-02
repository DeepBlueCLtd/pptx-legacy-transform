# Open a glc: link from a published gram page in the legacy replay tool
# (issue #199). Registered as the handler for the glc: URL scheme by Group
# Policy (HKLM, installed under C:\Program Files\AAAC\), or on a stand-alone
# PC by glc-protocol.reg; see theme/glc-launch/README.md.
#
# The page sends  glc:<percent-encoded full Windows path of the .glc>.
# This decodes it once and asks Windows to open the file, which runs whatever
# application .glc files are associated with - the replay tool. The .glc is
# opened where it is published, so the .wav it names (relative to itself)
# is found beside it.
#
# Any web page can send a glc: link, so this opens nothing but an existing
# .glc file: no other extension, no URL, no command line.
param([string]$Url)

function Fail([string]$message) {
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show(
        $message, 'Open gram in replay tool', 'OK', 'Warning')
    exit 1
}

if (-not $Url -or -not $Url.StartsWith('glc:', [StringComparison]::OrdinalIgnoreCase)) {
    Fail "Not a glc: link:`n$Url"
}
$path = [Uri]::UnescapeDataString($Url.Substring(4)).TrimEnd('/')

if ([IO.Path]::GetExtension($path) -ne '.glc') {
    Fail "Only .glc files can be opened this way:`n$path"
}
if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    Fail "Gram file not found:`n$path"
}

Invoke-Item -LiteralPath $path
