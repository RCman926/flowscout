# Install / refresh the FlowScout start-on-login shortcut.
# Safe to re-run. Does not require Administrator.
#
#   powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
#   powershell -ExecutionPolicy Bypass -File .\install_startup.ps1 -Remove

param([switch]$Remove)

$root = $PSScriptRoot
$startup = [Environment]::GetFolderPath("Startup")
$lnkPath = Join-Path $startup "FlowScout.lnk"
$vbs = Join-Path $root "bat\START_FLOWSCOUT_ON_LOGIN.vbs"

if ($Remove) {
    if (Test-Path $lnkPath) {
        Remove-Item $lnkPath -Force
        Write-Host "Removed: $lnkPath"
    } else {
        Write-Host "Nothing to remove - no FlowScout.lnk in Startup."
    }
    exit 0
}

if (-not (Test-Path $vbs)) {
    Write-Host "ERROR: missing $vbs"
    exit 1
}

$w = New-Object -ComObject WScript.Shell
$sc = $w.CreateShortcut($lnkPath)
$sc.TargetPath = $vbs
$sc.WorkingDirectory = (Join-Path $root "bat")
$sc.WindowStyle = 7
$sc.Description = "Start FlowScout server after login (silent)"
$sc.Save()

Write-Host "Installed: $lnkPath"
Write-Host "Target:    $vbs"
Write-Host ""
Write-Host "On next login/reboot the server starts hidden on http://127.0.0.1:8000/"
Write-Host "Open that URL yourself - browser is not auto-launched."
Write-Host "To remove later:  powershell -ExecutionPolicy Bypass -File .\install_startup.ps1 -Remove"
