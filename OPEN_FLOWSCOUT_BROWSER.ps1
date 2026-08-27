# Open FlowScout UI in a real browser window (not a sidebar / empty host).
param(
    [string]$Url = "http://localhost:8000/?fresh=1"
)

$candidates = @(
    @{ Path = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"; Args = @($Url) },
    @{ Path = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"; Args = @($Url) },
    @{ Path = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"; Args = @($Url) },
    @{ Path = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"; Args = @($Url) },
    @{ Path = "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"; Args = @($Url) },
    @{ Path = "$env:ProgramFiles\Mozilla Firefox\firefox.exe"; Args = @("-url", $Url) }
)

foreach ($b in $candidates) {
    if (Test-Path -LiteralPath $b.Path) {
        Start-Process -FilePath $b.Path -ArgumentList $b.Args | Out-Null
        Write-Host "Opened browser: $($b.Path)"
        Write-Host "URL: $Url"
        exit 0
    }
}

# Last resort — Windows URL association
cmd.exe /c start "" "$Url"
Write-Host "Opened via Windows shell: $Url"
exit 0
